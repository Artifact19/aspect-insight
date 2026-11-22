"""Sequence-to-sequence quadruple generator (Flan-T5): review sentence -> linearised quadruples."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Sequence

import numpy as np
import torch
from torch.optim import AdamW
from torch.optim.lr_scheduler import LambdaLR
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

from ..data import CategoryVocab, linearize, parse, quads_of, write_jsonl
from ..metrics import extraction_scores
from ..utils import free_memory, get_device, save_json, set_seed, sync

DEFAULT_PREFIX = "extract quadruples: "


def source_text(sentence: dict | str, prefix: str = DEFAULT_PREFIX, with_domain: bool = False,
                domain: str | None = None) -> str:
    """Model input; with_domain names the review domain, e.g. "extract quadruples (laptop): ..."."""
    text = sentence["text"] if isinstance(sentence, dict) else sentence
    domain = domain or (sentence.get("domain") if isinstance(sentence, dict) else None)
    if with_domain and domain:
        prefix = f"{prefix.rstrip().rstrip(':')} ({domain.lower()}): "
    return prefix + text


def generator_dtype() -> torch.dtype | None:
    """bf16 where supported; T5 is numerically unstable in fp16, so older GPUs train in fp32."""
    if torch.cuda.is_available() and torch.cuda.is_bf16_supported():
        return torch.bfloat16
    return None


class Seq2SeqDataset(Dataset):
    def __init__(self, sentences: Sequence[dict], tokenizer, prefix: str, max_source_len: int, max_target_len: int,
                 with_domain: bool = False):
        self.sources = tokenizer([source_text(s, prefix, with_domain) for s in sentences], truncation=True,
                                 max_length=max_source_len)["input_ids"]
        self.targets = tokenizer(text_target=[linearize(quads_of(s)) for s in sentences], truncation=True,
                                 max_length=max_target_len)["input_ids"]

    def __len__(self):
        return len(self.sources)

    def __getitem__(self, i):
        return self.sources[i], self.targets[i]


def make_collate(pad_id: int):
    def collate(batch):
        src_len = max(len(s) for s, _ in batch)
        tgt_len = max(len(t) for _, t in batch)
        input_ids = torch.full((len(batch), src_len), pad_id, dtype=torch.long)
        attention = torch.zeros((len(batch), src_len), dtype=torch.long)
        labels = torch.full((len(batch), tgt_len), -100, dtype=torch.long)
        for i, (s, t) in enumerate(batch):
            input_ids[i, :len(s)] = torch.tensor(s)
            attention[i, :len(s)] = 1
            labels[i, :len(t)] = torch.tensor(t)
        return {"input_ids": input_ids, "attention_mask": attention, "labels": labels}
    return collate


def load_generator(path: str | Path, device: torch.device | None = None):
    device = device or get_device()
    tokenizer = AutoTokenizer.from_pretrained(path)
    model = AutoModelForSeq2SeqLM.from_pretrained(path).float().to(device).eval()
    return tokenizer, model


@torch.no_grad()
def generate(model, tokenizer, sources: Sequence[str], max_source_len: int = 192, max_new_tokens: int = 256,
             batch_size: int = 32, **generate_kwargs) -> tuple[list[str], float]:
    """Generate one output per source; returns the outputs and the mean milliseconds per sentence."""
    device, dtype = next(model.parameters()).device, generator_dtype()
    model.eval()
    order = np.argsort([-len(s) for s in sources])
    outputs: list[str] = [""] * len(sources)
    elapsed = 0.0
    for start in range(0, len(sources), batch_size):
        idx = order[start:start + batch_size]
        enc = tokenizer([sources[i] for i in idx], padding=True, truncation=True, max_length=max_source_len,
                        return_tensors="pt").to(device)
        sync()
        t0 = time.perf_counter()
        with torch.autocast(device_type=device.type, dtype=dtype or torch.float32, enabled=dtype is not None):
            out = model.generate(**enc, max_new_tokens=max_new_tokens, **generate_kwargs)
        sync()
        elapsed += time.perf_counter() - t0
        for i, text in zip(idx, tokenizer.batch_decode(out, skip_special_tokens=True)):
            outputs[i] = text.strip()
    return outputs, elapsed / max(1, len(sources)) * 1000


def score_outputs(sentences: Sequence[dict], outputs: Sequence[str], vocab: CategoryVocab) -> dict:
    parsed = [parse(o, vocab) for o in outputs]
    scores = extraction_scores([quads_of(s) for s in sentences], [p[0] for p in parsed])
    scores["malformed_segments"] = sum(p[1] for p in parsed)
    return scores


def train_generator(train_sents: Sequence[dict], dev_sents: Sequence[dict], test_sents: Sequence[dict],
                    vocab: CategoryVocab, cfg: dict, seed: int, run_dir: Path, save_model: bool = False) -> dict:
    """Fine-tune a seq2seq model, keep the epoch with the best Dev ACOS F1, write test predictions and metrics."""
    set_seed(seed)
    device, dtype = get_device(), generator_dtype()
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    prefix, max_src, max_tgt = cfg.get("source_prefix", DEFAULT_PREFIX), cfg["max_source_len"], cfg["max_target_len"]
    gen_kwargs = {"num_beams": cfg.get("num_beams", 1), "do_sample": False}
    tagged = cfg.get("domain_in_source", False)

    tokenizer = AutoTokenizer.from_pretrained(cfg["model_name"])
    model = AutoModelForSeq2SeqLM.from_pretrained(cfg["model_name"]).float().to(device)
    loader = DataLoader(Seq2SeqDataset(train_sents, tokenizer, prefix, max_src, max_tgt, tagged),
                        batch_size=cfg["batch_size"],
                        shuffle=True, collate_fn=make_collate(tokenizer.pad_token_id),
                        generator=torch.Generator().manual_seed(seed))
    accum = cfg.get("grad_accum", 1)
    optimizer = AdamW(model.parameters(), lr=cfg["lr"], weight_decay=cfg.get("weight_decay", 0.01))
    total = (len(loader) // accum) * cfg["epochs"]
    warm = int(cfg.get("warmup_ratio", 0.06) * total)
    scheduler = LambdaLR(optimizer, lambda s: s / max(1, warm) if s < warm else max(0.0, (total - s) / max(1, total - warm)))

    dev_sources = [source_text(s, prefix, tagged) for s in dev_sents]
    log, best, stale = [], {"f1": -1.0, "epoch": 0, "state": None}, 0
    t_start = time.time()
    for epoch in range(1, cfg["epochs"] + 1):
        model.train()
        t0, running = time.time(), 0.0
        optimizer.zero_grad(set_to_none=True)
        for step, batch in enumerate(loader, 1):
            batch = {k: v.to(device) for k, v in batch.items()}
            with torch.autocast(device_type=device.type, dtype=dtype or torch.float32, enabled=dtype is not None):
                loss = model(**batch).loss / accum
            loss.backward()
            running += loss.item() * accum
            if step % accum == 0 or step == len(loader):
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad(set_to_none=True)
        entry = {"epoch": epoch, "train_loss": running / len(loader), "seconds": round(time.time() - t0, 1)}
        if epoch >= cfg.get("eval_from_epoch", 1) or epoch == cfg["epochs"]:
            outputs, _ = generate(model, tokenizer, dev_sources, max_src, max_tgt, cfg.get("eval_batch_size", 64),
                                  **gen_kwargs)
            entry["dev_acos_f1"] = score_outputs(dev_sents, outputs, vocab)["ACOS"]["f1"]
            if entry["dev_acos_f1"] > best["f1"]:
                best = {"f1": entry["dev_acos_f1"], "epoch": epoch,
                        "state": {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}}
                stale = 0
            else:
                stale += 1
        log.append(entry)
        print(f"    epoch {epoch}: loss {entry['train_loss']:.4f}"
              + (f" | dev ACOS F1 {entry['dev_acos_f1']:.4f}" if "dev_acos_f1" in entry else "")
              + f" | {entry['seconds']}s")
        if stale >= cfg.get("patience", 99):
            print(f"    no Dev improvement for {stale} evaluations, stopping")
            break
    train_seconds = time.time() - t_start
    model.load_state_dict(best["state"])

    outputs, ms = generate(model, tokenizer, [source_text(s, prefix, tagged) for s in test_sents], max_src, max_tgt,
                           cfg.get("eval_batch_size", 64), **gen_kwargs)
    write_jsonl(({"id": s["id"], "domain": s["domain"], "output": o} for s, o in zip(test_sents, outputs)),
                run_dir / "test_predictions.jsonl")
    if save_model:
        model.save_pretrained(run_dir / "model")
        tokenizer.save_pretrained(run_dir / "model")
        save_json({"source_prefix": prefix, "domain_in_source": tagged, "max_source_len": max_src,
                   "max_new_tokens": max_tgt}, run_dir / "model" / "absa_config.json")

    by_domain = {}
    for d in sorted({s["domain"] for s in test_sents}):
        idx = [i for i, s in enumerate(test_sents) if s["domain"] == d]
        by_domain[d] = score_outputs([test_sents[i] for i in idx], [outputs[i] for i in idx], vocab)
    result = {"seed": seed, "best_epoch": best["epoch"], "dev_acos_f1": best["f1"], "train_size": len(train_sents),
              "train_seconds": round(train_seconds, 1), "ms_per_sentence": round(ms, 2),
              "parameters": sum(p.numel() for p in model.parameters()), "log": log,
              "test": score_outputs(test_sents, outputs, vocab), "test_by_domain": by_domain}
    save_json(result, run_dir / "metrics.json")
    del model, best
    free_memory()
    return result
