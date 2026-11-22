from absa.data import parse
from absa.experiments import expand
from absa.models.llm import clean_output
from absa.retrieval import TfidfIndex


def test_retrieval_ranks_similar_text_first():
    index = TfidfIndex(["the battery life is great", "screen is too dim", "great food and service", "battery died"])
    top = index.search(["battery is bad", "the food was cold"], 2)
    assert set(top[0]) == {0, 3}
    assert top[1][0] == 2


def test_clean_output_joins_quadruples_on_separate_lines():
    raw = "Here you go:\n[A] food [C] food - quality [O] great [S] positive\n[A] staff [C] service - general [O] rude [S] negative"
    quads, malformed = parse(clean_output(raw))
    assert len(quads) == 2 and malformed == 0


def test_expand_experiments():
    assert len(expand({"per_domain": True})) == 5
    runs = expand({"leave_one_out": True})
    assert all(test[0] not in train for _, train, test in runs)
    assert expand({"train": ["Laptop"], "test": ["Hotel"]}) == [("model", ["Laptop"], ["Hotel"])]


def test_english_filter_rejects_script_switching():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from generate_neutral import dataset_style, is_english
    assert is_english("the screen resolution is 1920x1080 , which is standard .")
    assert is_english("It’s fine — nothing more")
    assert not is_english("The food is decent , nothing特别值得一提")
    assert dataset_style("The room didn't have a view, but it was fine.", False) == \
        "The room didn ' t have a view , but it was fine ."
