from absa.inference import check_direction, check_numbers, comparison_facts, entity, highlight_spans, summarize, summary_facts, topic


def quad(sentiment, category, aspect, confidence=0.9, agrees=True):
    return {"sentiment": sentiment, "category_text": category, "aspect": aspect, "opinion": "x",
            "confidence": confidence, "agrees": agrees}


SENTENCES = [
    {"review": 0, "text": "Battery dies fast.", "quads": [quad("negative", "battery - operation performance", "battery")]},
    {"review": 1, "text": "Battery is cheap junk.", "quads": [quad("negative", "battery - quality", "battery", 0.6)]},
    {"review": 2, "text": "Love the screen.", "quads": [quad("positive", "display - general", "screen")]},
]


def test_topics_are_grouped_by_main_entity():
    s = summarize(SENTENCES)
    battery = next(e for e in s["entities"] if e["name"] == "battery")
    assert battery["negative"] == 2 and set(battery["subtopics"]) == {"operation performance", "quality"}
    assert battery["examples"]["negative"][0] == "Battery dies fast."
    assert entity("fans&cooling - general") == "fans and cooling"
    assert topic("battery - operation performance") == "battery performance"


def test_check_numbers_flags_invented_claims():
    facts = summary_facts(summarize(SENTENCES), "Shop", "Laptop")
    assert check_numbers("Battery has 2 complaints.", facts) == []
    assert "9" in check_numbers("Battery has 9 complaints.", facts)
    assert "2 out of 3" in check_numbers("2 out of 3 customers complain.", facts)


def test_comparison_uses_shares_so_different_sizes_compare_fairly():
    a = summarize(SENTENCES)
    b = summarize(SENTENCES[2:])
    facts = comparison_facts(a, b, "A", "B")
    assert facts[0] == "A: 3 reviews with 3 opinions, 67% of them negative."
    assert "A has a higher share of negative opinions than B: 67% vs 0%." in facts
    assert "The biggest difference is battery: complaints in 67% of A reviews vs 0% of B reviews." in facts
    assert check_numbers("A has a higher share of negative opinions, 67% vs 0%.", facts) == []
    assert check_numbers("A has 0 vs 3 negative opinions.", facts) != []
    same = comparison_facts(a, a, "A", "B")
    assert any("similar share of negative opinions" in f for f in same)


def test_numbers_must_belong_to_the_topic_they_are_written_next_to():
    facts = ["Praise at X: display: 5 positive mentions (about screen); keyboard: 2 positive mentions.",
             "The biggest difference in complaints is about service: 2 at A vs 24 at B."]
    assert check_numbers("The display has 5 positive mentions and the keyboard 2.", facts) == []
    assert "keyboard 5" in check_numbers("Customers praise the display and keyboard, with 5 positive mentions each.", facts)
    assert check_numbers("A has 2 complaints about service, while B has 24.", facts) == []
    assert check_numbers("They praise the display and keyboard, with 5 and 2 positive mentions respectively.", facts) == []
    assert check_numbers("They praise the display and keyboard, with 2 and 5 positive mentions respectively.", facts) != []


def test_highlights_join_each_count_to_its_topic():
    facts = summary_facts(summarize(SENTENCES), "Shop", "Laptop")
    text = "Customers love the display. Shop should fix battery first, with 2 complaints. That is 3 in total."
    spans = {text[s["start"]:s["end"]]: s["kind"] for s in highlight_spans(text, facts)}
    assert spans["display"] == "praise"
    assert spans["battery first, with 2 complaints"] == "complaint"
    assert spans["Shop"] == "label"
    assert not any(t.strip().startswith("3") for t in spans)


def test_direction_of_more_complaints_is_checked():
    a = summarize(SENTENCES)
    b = summarize(SENTENCES[2:])
    facts = comparison_facts(a, b, "Alpha", "Beta")
    assert check_direction("Alpha has a higher share of negative opinions than Beta.", facts) == []
    assert check_direction("Beta receives more complaints than Alpha.", facts) == ["Beta has more complaints"]
    assert check_direction("Alpha has fewer complaints than Beta.", facts) == ["Alpha has fewer complaints"]
    same = comparison_facts(summarize(SENTENCES), summarize(SENTENCES), "Alpha", "Beta")
    assert check_direction("Beta has more complaints than Alpha.", same) == ["Beta has more complaints"]


def test_shares_round_half_up_and_clauses_are_checked_separately():
    from absa.inference import percent
    assert percent(2, 16) == 13
    facts = ["A: 16 reviews with 24 opinions, 38% of them negative.",
             "B: 16 reviews with 26 opinions, 38% of them negative.",
             "The biggest difference is service: complaints in 25% of B reviews vs 13% of A reviews."]
    text = "A and B both have 38% negative opinions, but B has more complaints about service (25%) than A (13%)."
    assert check_numbers(text, facts) == []
