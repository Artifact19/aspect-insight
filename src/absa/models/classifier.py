"""Encoder classifier for aspect-level sentiment: [CLS] target [SEP] sentence (aspect marked) [SEP] -> label."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Sequence

import numpy as np
import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import LambdaLR
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from ..constants import ID2LABEL, LABEL2ID
from ..metrics import classification_scores, macro_f1
from ..utils import amp_dtype, free_memory, get_device, save_json, set_seed, sync

INPUT_KEYS = ("input_ids", "attention_mask", "token_type_ids")


class PairDataset(Dataset):
    def __init__(self, rows: Sequence[dict], tokenizer, max_len: int, use_markers: bool):
        sentences = [r["marked_sentence"] if use_markers else r["sentence"] for r in rows]
        enc = tokenizer([r["target"] for r in rows], sentences, truncation=True, max_length=max_len)
        self.features = {k: enc[k] for k in INPUT_KEYS if k in enc}
        self.labels = [r["label"] for r in rows]

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, i):
        item = {k: v[i] for k, v in self.features.items()}
        item["labels"] = self.labels[i]
        return item


def make_collate(tokenizer):
    def collate(batch):
        labels = torch.tensor([b.pop("labels") for b in batch], dtype=torch.long)
        out = tokenizer.pad(batch, return_tensors="pt")
        out["labels"] = labels
        return out
    return collate


def _inputs(batch, device):
    return {k: batch[k].to(device) for k in INPUT_KEYS if k in batch}


def load_classifier(path: str | Path, device: torch.device | None = None):
    device = device or get_device()
    tokenizer = AutoTokenizer.from_pretrained(path, use_fast=False)
    model = AutoModelForSequenceClassification.from_pretrained(path).float().to(device).eval()
    return tokenizer, model


@torch.no_grad()
def predict_proba(model, tokenizer, rows: Sequence[dict], max_len: int = 128, use_markers: bool = True,
                  batch_size: int = 32) -> tuple[np.ndarray, float]:
    """Class probabilities for each row and the mean forward-pass time in milliseconds per pair."""
    device = next(model.parameters()).device
    model.eval()
    loader = DataLoader(PairDataset(rows, tokenizer, max_len, use_markers), batch_size=batch_size, shuffle=False,
                        collate_fn=make_collate(tokenizer))
    probs, elapsed = [], 0.0
    for batch in loader:
        sync()
        t0 = time.perf_counter()
        logits = model(**_inputs(batch, device)).logits
        sync()
        elapsed += time.perf_counter() - t0
        probs.append(torch.softmax(logits.float(), dim=-1).cpu().numpy())
    return np.concatenate(probs), elapsed / max(1, len(rows)) * 1000


def train_classifier(train_rows: Sequence[dict], dev_rows: Sequence[dict], test_rows: Sequence[dict],
                     loss_fn: nn.Module, cfg: dict, seed: int, run_dir: Path, save_model: bool = False) -> dict:
    """Fine-tune an encoder, keep the epoch with the best Dev macro-F1, and write predictions and metrics to run_dir."""
    set_seed(seed)
    device, dtype = get_device(), amp_dtype()
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(cfg["model_name"], use_fast=False)
    model = AutoModelForSequenceClassification.from_pretrained(
        cfg["model_name"], num_labels=3, id2label=ID2LABEL, label2id=LABEL2ID).float().to(device)
    loss_fn = loss_fn.to(device)
    max_len, markers = cfg.get("max_len", 128), cfg.get("use_markers", True)

    generator = torch.Generator().manual_seed(seed)
    train_loader = DataLoader(PairDataset(train_rows, tokenizer, max_len, markers), batch_size=cfg["batch_size"],
                              shuffle=True, collate_fn=make_collate(tokenizer), generator=generator)
    optimizer = AdamW(model.parameters(), lr=cfg["lr"], weight_decay=cfg.get("weight_decay", 0.01), eps=1e-6)
    total = len(train_loader) * cfg["epochs"]
    warm = int(cfg.get("warmup_ratio", 0.1) * total)
    scheduler = LambdaLR(optimizer, lambda s: s / max(1, warm) if s < warm else max(0.0, (total - s) / max(1, total - warm)))
    scaler = torch.amp.GradScaler("cuda", enabled=dtype == torch.float16)

    y_dev = np.array([r["label"] for r in dev_rows])
    log, best = [], {"f1": -1.0, "epoch": 0, "state": None}
    t_start = time.time()
    for epoch in range(1, cfg["epochs"] + 1):
        model.train()
        t0, running = time.time(), 0.0
        for batch in train_loader:
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device.type, dtype=dtype or torch.float32, enabled=dtype is not None):
                logits = model(**_inputs(batch, device)).logits
            loss = loss_fn(logits.float(), batch["labels"].to(device))
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(optimizer)
            scaler.update()
            scheduler.step()
            running += loss.item()
        dev_probs, _ = predict_proba(model, tokenizer, dev_rows, max_len, markers)
        dev_f1 = macro_f1(y_dev, dev_probs.argmax(1))
        log.append({"epoch": epoch, "train_loss": running / len(train_loader), "dev_macro_f1": dev_f1,
                    "seconds": round(time.time() - t0, 1)})
        print(f"    epoch {epoch}: loss {log[-1]['train_loss']:.4f} | dev macro-F1 {dev_f1:.4f} | {log[-1]['seconds']}s")
        if dev_f1 > best["f1"]:
            best = {"f1": dev_f1, "epoch": epoch,
                    "state": {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}}
    train_seconds = time.time() - t_start
    model.load_state_dict(best["state"])

    dev_probs, _ = predict_proba(model, tokenizer, dev_rows, max_len, markers)
    test_probs, ms_per_pair = predict_proba(model, tokenizer, test_rows, max_len, markers)
    np.save(run_dir / "dev_probs.npy", dev_probs.astype(np.float32))
    np.save(run_dir / "test_probs.npy", test_probs.astype(np.float32))
    if save_model:
        model.half().save_pretrained(run_dir / "model")
        tokenizer.save_pretrained(run_dir / "model")

    result = {
        "seed": seed, "best_epoch": best["epoch"], "dev_macro_f1": best["f1"], "train_size": len(train_rows),
        "train_seconds": round(train_seconds, 1), "ms_per_pair": round(ms_per_pair, 3),
        "parameters": sum(p.numel() for p in model.parameters()), "log": log,
        "test": classification_scores([r["label"] for r in test_rows], test_probs.argmax(1)),
    }
    save_json(result, run_dir / "metrics.json")
    del model, best
    free_memory()
    return result
