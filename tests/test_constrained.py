import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from absa.constants import DOMAINS  # noqa: E402
from absa.constrained import DomainCategoryConstraint  # noqa: E402
from absa.data import category_to_text, load_sentences, quads_of  # noqa: E402


@pytest.fixture(scope="module")
def flan_tokenizer():
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained("google/flan-t5-base")


def test_domain_category_constraint_covers_all_train_categories(flan_tokenizer):
    for d in DOMAINS:
        cats = {category_to_text(q.category) for s in load_sentences([d], "Train") for q in quads_of(s)}
        constraint = DomainCategoryConstraint(flan_tokenizer, cats, flan_tokenizer.vocab_size)
        assert len(constraint.categories) == len(cats)

        # Simulate decoder right after "[A] battery [C]"
        prefix = flan_tokenizer.encode("[A] battery [C]", add_special_tokens=False)
        allowed = constraint.allowed_tokens(prefix)
        assert len(allowed) < 200  # strictly narrowed, never full 32k vocab
        for cat in cats:
            cat_tokens = flan_tokenizer.encode(f"[C] {cat} [O]", add_special_tokens=False)[len(constraint.c_marker):]
            seq = list(prefix)
            for tok in cat_tokens:
                step_allowed = constraint.allowed_tokens(seq)
                assert tok in step_allowed, f"Token {tok} missing for {d}/{cat}"
                seq.append(tok)
            # After [O], aspect/opinion generation is unconstrained again
            assert len(constraint.allowed_tokens(seq)) == flan_tokenizer.vocab_size


def test_sentiment_constraint_only_allows_valid_labels(flan_tokenizer):
    constraint = DomainCategoryConstraint(flan_tokenizer, ["food - quality"], flan_tokenizer.vocab_size)
    prefix = flan_tokenizer.encode("[A] pizza [C] food - quality [O] tasty [S]", add_special_tokens=False)
    allowed_first = constraint.allowed_tokens(prefix)
    decoded_first = {flan_tokenizer.decode([t]).strip().lower() for t in allowed_first}
    assert decoded_first == {"positive", "negative", "neutral"}
