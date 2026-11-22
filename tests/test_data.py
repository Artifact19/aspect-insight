from absa.data import (NULL, CategoryVocab, Quad, build_pairs, linearize, load_pairs, load_sentences, mark_aspect,
                       parse, quads_of, target_text)

VOCAB = CategoryVocab(["Food#Quality", "Service#General", "BATTERY#OPERATION_PERFORMANCE"])


def test_linearize_parse_roundtrip():
    quads = [Quad("battery life", "BATTERY#OPERATION_PERFORMANCE", "stellar", "POS"),
             Quad(NULL, "Service#General", "rude", "NEG"),
             Quad("salmon", "Food#Quality", NULL, "NEU")]
    parsed, malformed = parse(linearize(quads), VOCAB)
    assert malformed == 0
    assert [q.key() for q in parsed] == [q.key() for q in quads]


def test_parse_counts_malformed_segments_and_deduplicates():
    text = ("[A] food [C] food - quality [O] great [S] positive [SSEP] garbage [SSEP] "
            "[A] food [C] food - quality [O] great [S] positive [SSEP] [A] x [C] y [O] z [S] unsure")
    parsed, malformed = parse(text, VOCAB)
    assert len(parsed) == 1 and parsed[0].category == "Food#Quality"
    assert malformed == 2


def test_parse_empty_output():
    assert parse("", VOCAB) == ([], 0)


def test_mark_aspect_uses_span_then_search():
    assert mark_aspect("the battery is great", "battery", (1, 2)) == "the <t> battery </t> is great"
    assert mark_aspect("the battery is great", "battery", (0, 1)) == "the <t> battery </t> is great"
    assert mark_aspect("it is great", NULL) == "it is great"


def test_target_text_format():
    assert target_text("salmon", "Food#Quality") == "salmon (Food - Quality)"
    assert target_text(NULL, "Food#Quality") == "Food - Quality"


def test_laptop_restaurant_pair_counts():
    sizes = {split: len(load_pairs(["Laptop", "Restaurant"], split)) for split in ("Train", "Dev", "Test")}
    assert sizes == {"Train": 10082, "Dev": 1365, "Test": 2739}


def test_every_sentence_has_quads_and_pairs_are_consistent():
    sentences = load_sentences(["Hotel"], "Dev")
    pairs = build_pairs(sentences)
    assert all(s["quads"] for s in sentences)
    assert len(pairs) == sum(len(quads_of(s)) for s in sentences)
    assert {p["label"] for p in pairs} <= {0, 1, 2}
