"""Inference-time constrained decoding for Flan-T5 quadruple generation.

Restricts tokens inside ``[C] ... [O]`` spans to valid category names of the selected domain
(derived strictly from the training inventory, with zero test leakage) and tokens inside
``[S] ...`` spans to the three sentiment labels (positive, negative, neutral). Aspect ``[A]``
and opinion ``[O]`` spans remain completely unconstrained free text.
"""
from __future__ import annotations

from typing import Iterable, Sequence

TERMINAL = None


def _find_last_subseq(seq: Sequence[int], sub: Sequence[int]) -> int:
    """Index of the most recent occurrence of `sub` inside `seq`, or -1."""
    m = len(sub)
    if m == 0 or len(seq) < m:
        return -1
    for i in range(len(seq) - m, -1, -1):
        if list(seq[i:i + m]) == list(sub):
            return i
    return -1


def _build_trie(sequences: Iterable[Sequence[int]], mark_terminal: bool = False) -> dict:
    root: dict = {}
    for toks in sequences:
        node = root
        for tok in toks:
            node = node.setdefault(int(tok), {})
        if mark_terminal:
            node[TERMINAL] = True
    return root


def _walk_trie(root: dict, prefix: Sequence[int]) -> dict | None:
    node = root
    for tok in prefix:
        if not isinstance(node, dict) or int(tok) not in node:
            return None
        node = node[int(tok)]
    return node if isinstance(node, dict) else None


class DomainCategoryConstraint:
    """Prefix-allowed-tokens constraint restricting categories to one domain without retraining."""

    def __init__(self, tokenizer, categories: Iterable[str], vocab_size: int):
        self.c_marker = tokenizer.encode("[C]", add_special_tokens=False)
        self.o_marker = tokenizer.encode("[O]", add_special_tokens=False)
        self.s_marker = tokenizer.encode("[S]", add_special_tokens=False)
        self.all_tokens = list(range(int(vocab_size)))

        cat_seqs: list[list[int]] = []
        self.categories = sorted(set(categories))
        for cat in self.categories:
            full = tokenizer.encode(f"[C] {cat} [O]", add_special_tokens=False)
            if full[:len(self.c_marker)] != self.c_marker or full[-len(self.o_marker):] != self.o_marker:
                raise ValueError(f"Unexpected marker tokenization for category {cat!r}: {full}")
            cat_seqs.append(full[len(self.c_marker):])
        self.cat_trie = _build_trie(cat_seqs, mark_terminal=False)

        sent_seqs: list[list[int]] = []
        for word in ("positive", "negative", "neutral"):
            full = tokenizer.encode(f"[S] {word}", add_special_tokens=False)
            if full[:len(self.s_marker)] != self.s_marker:
                raise ValueError(f"Unexpected sentiment tokenization for {word!r}: {full}")
            sent_seqs.append(full[len(self.s_marker):])
        self.sent_trie = _build_trie(sent_seqs, mark_terminal=True)

    def allowed_tokens(self, seq: Sequence[int]) -> list[int]:
        last_c = _find_last_subseq(seq, self.c_marker)
        if last_c >= 0:
            tail = seq[last_c + len(self.c_marker):]
            if _find_last_subseq(tail, self.o_marker) == -1:
                node = _walk_trie(self.cat_trie, tail)
                if node:
                    choices = sorted(k for k in node.keys() if k is not TERMINAL)
                    if choices:
                        return choices
                return self.all_tokens

        last_s = _find_last_subseq(seq, self.s_marker)
        if last_s >= 0 and last_s > last_c:
            tail_s = seq[last_s + len(self.s_marker):]
            node_s = _walk_trie(self.sent_trie, tail_s)
            if node_s is not None and TERMINAL not in node_s:
                choices = sorted(k for k in node_s.keys() if k is not TERMINAL)
                if choices:
                    return choices

        return self.all_tokens

    def prefix_allowed_tokens_fn(self, batch_id: int, input_ids) -> list[int]:
        seq = input_ids.tolist() if hasattr(input_ids, "tolist") else list(input_ids)
        return self.allowed_tokens(seq)
