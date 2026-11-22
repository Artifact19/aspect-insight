from absa.analysis import error_taxonomy, majority_vote, recall_by_group
from absa.data import NULL, Quad

GOLD = [[Quad("food", "Food#Quality", "great", "POS"), Quad("staff", "Service#General", "rude", "NEG"),
         Quad("view", "Ambience#General", "nice", "POS"), Quad(NULL, "Restaurant#Prices", "pricey", "NEG")]]


def test_error_taxonomy_attributes_single_element_errors():
    pred = [[Quad("food", "Food#Quality", "great", "POS"),          # correct
             Quad("staff", "Food#Quality", "rude", "NEG"),           # wrong category
             Quad("view", "Ambience#General", "nice", "NEG"),        # wrong sentiment
             Quad("wine", "Drinks#Quality", "good", "POS")]]         # spurious
    e = error_taxonomy(GOLD, pred)
    assert e["missed_by_type"]["category"] == 1
    assert e["missed_by_type"]["sentiment"] == 1
    assert e["missed_by_type"]["aspect missed"] == 1
    assert e["missed_total"] == 3 and e["spurious"] == 1


def test_recall_by_group():
    pred = [[Quad("food", "Food#Quality", "great", "POS")]]
    r = recall_by_group(GOLD, pred)
    assert r["explicit aspect"] == {"recall": 1 / 3, "n": 3}
    assert r["implicit aspect"] == {"recall": 0.0, "n": 1}


def test_majority_vote():
    a, b = Quad("food", "Food#Quality", "great", "POS"), Quad("staff", "Service#General", "rude", "NEG")
    assert majority_vote([[a, b], [a], [a, b, b]], 2) == [a, b]
    assert majority_vote([[a, b], [a], [a]], 2) == [a]
