"""Decoder-only quadruple generator (Qwen2.5 + LoRA) and in-context prompting with the same output format."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Sequence

import numpy as np
import torch
from torch.optim import AdamW
from torch.optim.lr_scheduler import LambdaLR
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer

from ..data import SSEP, CategoryVocab, linearize, quads_of, write_jsonl
from ..utils import free_memory, get_device, save_json, set_seed, sync
from .generator import score_outputs

SYSTEM = "You extract aspect-based sentiment quadruples from review sentences."
INSTRUCTION = ("Extract every aspect-based sentiment quadruple from the review sentence. Write each one as "
               "[A] aspect [C] category [O] opinion [S] sentiment, where sentiment is positive, negative or neutral, "
               "and separate quadruples with [SSEP]. Write null when the aspect or the opinion is not stated "
               "explicitly. Answer on one line with the quadruples only.")


def llm_dtype() -> torch.dtype:
    if torch.cuda.is_available():
        return torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    return torch.float32


def user_turn(text: str, domain: str | None = None) -> str:
    return (f"Domain: {domain.lower()}\n" if domain else "") + f"Sentence: {text}"


def chat_prompt(tokenizer, text: str, examples: Sequence[tuple[str, str]] = (), categories: Sequence[str] = (),
                domain: str | None = None) -> str:
    """Chat-formatted prompt ending where the assistant's answer starts."""
    system = f"{SYSTEM}\n\n{INSTRUCTION}"
    if categories:
        system += "\n\nUse one of these categories: " + "; ".join(categories) + "."
    messages = [{"role": "system", "content": system}]
    for ex_text, ex_answer in examples:
        messages += [{"role": "user", "content": user_turn(ex_text, domain)},
                     {"role": "assistant", "content": ex_answer}]
    messages.append({"role": "user", "content": user_turn(text, domain)})
    return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)


def clean_output(text: str) -> str:
    """Keep the lines that contain quadruples; quadruples written on separate lines are joined with [SSEP]."""
    lines = [line.strip() for line in str(text).splitlines() if "[A]" in line]
    return f" {SSEP} ".join(lines) if lines else str(text).strip()


def load_tokenizer(name: str | Path):
    tokenizer = AutoTokenizer.from_pretrained(name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    return tokenizer


def load_causal_lm(name: str | Path, adapter: str | Path | None = None, device: torch.device | None = None):
    """Base model in bf16/fp16, optionally with a LoRA adapter merged in."""
    device = device or get_device()
    tokenizer = load_tokenizer(adapter or name)
    model = AutoModelForCausalLM.from_pretrained(name, dtype=llm_dtype())
    if adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, adapter).merge_and_unload()
    return tokenizer, model.to(device).eval()


class PromptTargetDataset(Dataset):
    """Prompt tokens are masked out of the loss; only the answer and the end-of-turn token are learned."""

    def __init__(self, sentences: Sequence[dict], tokenizer, max_len: int, with_domain: bool = False):
        self.items = []
        end = tokenizer.eos_token
        for s in sentences:
            prompt = tokenizer(chat_prompt(tokenizer, s["text"], domain=s["domain"] if with_domain else None),
                               add_special_tokens=False)["input_ids"]
            answer = tokenizer(linearize(quads_of(s)) + end, add_special_tokens=False)["input_ids"]
            ids = (prompt + answer)[:max_len]
            labels = ([-100] * len(prompt) + answer)[:max_len]
            self.items.append((ids, labels))

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        return self.items[i]


def make_collate(pad_id: int):
    def collate(batch):
        n = max(len(ids) for ids, _ in batch)
        input_ids = torch.full((len(batch), n), pad_id, dtype=torch.long)
        attention = torch.zeros((len(batch), n), dtype=torch.long)
        labels = torch.full((len(batch), n), -100, dtype=torch.long)
        for i, (ids, lab) in enumerate(batch):
            input_ids[i, :len(ids)] = torch.tensor(ids)
            attention[i, :len(ids)] = 1
            labels[i, :len(lab)] = torch.tensor(lab)
        return {"input_ids": input_ids, "attention_mask": attention, "labels": labels}
    return collate


@torch.no_grad()
def generate(model, tokenizer, prompts: Sequence[str], max_new_tokens: int = 200, batch_size: int = 32,
             **generate_kwargs) -> tuple[list[str], float]:
    """Greedy (or configured) decoding with left padding; returns outputs and mean milliseconds per prompt."""
    device = next(model.parameters()).device
    model.eval()
    tokenizer.padding_side = "left"
    order = np.argsort([-len(p) for p in prompts])
    outputs: list[str] = [""] * len(prompts)
    elapsed = 0.0
    kwargs = {"do_sample": False, "temperature": None, "top_p": None, "top_k": None, "use_cache": True,
              **generate_kwargs}
    for start in range(0, len(prompts), batch_size):
        idx = order[start:start + batch_size]
        enc = tokenizer([prompts[i] for i in idx], return_tensors="pt", padding=True,
                        add_special_tokens=False).to(device)
        sync()
        t0 = time.perf_counter()
        out = model.generate(**enc, max_new_tokens=max_new_tokens, pad_token_id=tokenizer.pad_token_id, **kwargs)
        sync()
        elapsed += time.perf_counter() - t0
        texts = tokenizer.batch_decode(out[:, enc["input_ids"].shape[1]:], skip_special_tokens=True)
        for i, text in zip(idx, texts):
            outputs[i] = text.strip()
    tokenizer.padding_side = "right"
    return outputs, elapsed / max(1, len(prompts)) * 1000


def add_lora(model, cfg: dict):
    from peft import LoraConfig, TaskType, get_peft_model
    lora = cfg["lora"]
    model = get_peft_model(model, LoraConfig(task_type=TaskType.CAUSAL_LM, r=lora["r"], lora_alpha=lora["alpha"],
                                             lora_dropout=lora["dropout"], target_modules=lora["target_modules"]))
    for p in model.parameters():
        if p.requires_grad:
            p.data = p.data.float()
    return model


def train_llm_generator(train_sents: Sequence[dict], dev_sents: Sequence[dict], test_sents: Sequence[dict],
                        vocab: CategoryVocab, cfg: dict, seed: int, run_dir: Path, save_model: bool = False) -> dict:
    """LoRA fine-tuning; keeps the adapter from the epoch with the best Dev ACOS F1, then scores the test set."""
    from peft import get_peft_model_state_dict, set_peft_model_state_dict
    set_seed(seed)
    device, dtype = get_device(), llm_dtype()
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    tokenizer = load_tokenizer(cfg["model_name"])
    tokenizer.padding_side = "right"
    base = AutoModelForCausalLM.from_pretrained(cfg["model_name"], dtype=dtype)
    if cfg.get("gradient_checkpointing"):
        base.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        base.enable_input_require_grads()
    model = add_lora(base, cfg).to(device)
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())

    tagged = cfg.get("domain_in_prompt", False)
    loader = DataLoader(PromptTargetDataset(train_sents, tokenizer, cfg["max_len"], tagged), batch_size=cfg["batch_size"],
                        shuffle=True, collate_fn=make_collate(tokenizer.pad_token_id),
                        generator=torch.Generator().manual_seed(seed))
    accum = cfg.get("grad_accum", 1)
    optimizer = AdamW([p for p in model.parameters() if p.requires_grad], lr=cfg["lr"],
                      weight_decay=cfg.get("weight_decay", 0.0))
    total = max(1, (len(loader) // accum) * cfg["epochs"])
    warm = int(cfg.get("warmup_ratio", 0.03) * total)
    scheduler = LambdaLR(optimizer, lambda s: s / max(1, warm) if s < warm else max(0.0, (total - s) / max(1, total - warm)))

    dev_prompts = [chat_prompt(tokenizer, s["text"], domain=s["domain"] if tagged else None) for s in dev_sents]
    max_new, eval_bs = cfg.get("max_new_tokens", 200), cfg.get("eval_batch_size", 32)
    log, best, stale = [], {"f1": -1.0, "epoch": 0, "state": None}, 0
    t_start = time.time()
    for epoch in range(1, cfg["epochs"] + 1):
        model.train()
        t0, running = time.time(), 0.0
        optimizer.zero_grad(set_to_none=True)
        for step, batch in enumerate(loader, 1):
            batch = {k: v.to(device) for k, v in batch.items()}
            with torch.autocast(device_type=device.type, dtype=dtype, enabled=device.type == "cuda"):
                loss = model(**batch).loss / accum
            loss.backward()
            running += loss.item() * accum
            if step % accum == 0 or step == len(loader):
                torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], 1.0)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad(set_to_none=True)
        entry = {"epoch": epoch, "train_loss": running / len(loader), "seconds": round(time.time() - t0, 1)}
        if epoch >= cfg.get("eval_from_epoch", 1) or epoch == cfg["epochs"]:
            with torch.autocast(device_type=device.type, dtype=dtype, enabled=device.type == "cuda"):
                outputs, _ = generate(model, tokenizer, dev_prompts, max_new, eval_bs)
            entry["dev_acos_f1"] = score_outputs(dev_sents, outputs, vocab)["ACOS"]["f1"]
            if entry["dev_acos_f1"] > best["f1"]:
                best = {"f1": entry["dev_acos_f1"], "epoch": epoch,
                        "state": {k: v.detach().cpu().clone() for k, v in get_peft_model_state_dict(model).items()}}
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
    set_peft_model_state_dict(model, best["state"])
    if save_model:
        model.save_pretrained(run_dir / "model")
        tokenizer.save_pretrained(run_dir / "model")
        save_json({"base_model": cfg["model_name"], "domain_in_prompt": tagged,
                   "max_new_tokens": max_new}, run_dir / "model" / "absa_config.json")

    with torch.autocast(device_type=device.type, dtype=dtype, enabled=device.type == "cuda"):
        outputs, ms = generate(model, tokenizer, [chat_prompt(tokenizer, s["text"], domain=s["domain"] if tagged else None)
                                                  for s in test_sents], max_new, eval_bs)
    write_jsonl(({"id": s["id"], "domain": s["domain"], "output": o} for s, o in zip(test_sents, outputs)),
                run_dir / "test_predictions.jsonl")
    by_domain = {}
    for d in sorted({s["domain"] for s in test_sents}):
        idx = [i for i, s in enumerate(test_sents) if s["domain"] == d]
        by_domain[d] = score_outputs([test_sents[i] for i in idx], [outputs[i] for i in idx], vocab)
    result = {"seed": seed, "best_epoch": best["epoch"], "dev_acos_f1": best["f1"], "train_size": len(train_sents),
              "train_seconds": round(train_seconds, 1), "ms_per_sentence": round(ms, 2),
              "parameters": total_params, "trainable_parameters": trainable, "log": log,
              "test": score_outputs(test_sents, outputs, vocab), "test_by_domain": by_domain}
    save_json(result, run_dir / "metrics.json")
    del model, base, best
    free_memory()
    return result
