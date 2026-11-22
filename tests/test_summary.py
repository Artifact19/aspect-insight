from absa.inference import check_numbers, comparison_facts, entity, summarize, summary_facts, topic


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


def test_comparison_facts_are_computed_not_generated():
    a = summarize(SENTENCES)
    b = summarize(SENTENCES[2:])
    facts = comparison_facts(a, b, "A", "B")
    assert "A has more negative opinions: 2 vs 0." in facts
    assert any("biggest difference in complaints is about battery: 2 at A vs 0 at B" in f for f in facts)
    assert check_numbers("A has 2 vs 0 negative opinions.", facts) == []
    assert check_numbers("A has 0 vs 3 negative opinions.", facts) != []
    same = comparison_facts(a, a, "A", "B")
    assert any("same number of negative opinions" in f for f in same)


def test_numbers_must_belong_to_the_topic_they_are_written_next_to():
    facts = ["Praise at X: display: 5 positive mentions (about screen); keyboard: 2 positive mentions.",
             "The biggest difference in complaints is about service: 2 at A vs 24 at B."]
    assert check_numbers("The display has 5 positive mentions and the keyboard 2.", facts) == []
    assert "keyboard 5" in check_numbers("Customers praise the display and keyboard, with 5 positive mentions each.", facts)
    assert check_numbers("A has 2 complaints about service, while B has 24.", facts) == []
    assert check_numbers("They praise the display and keyboard, with 5 and 2 positive mentions respectively.", facts) == []
    assert check_numbers("They praise the display and keyboard, with 2 and 5 positive mentions respectively.", facts) != []
