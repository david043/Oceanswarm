"""Tests for the relationships system."""
import pytest

from agents.relationships import build_relationship_index, relationship_label, to_summary
from db.models import RelationshipModel


# ---------------------------------------------------------------------------
# relationship_label
# ---------------------------------------------------------------------------

def test_family_parent_of():
    assert relationship_label("family", "parent_of", 80) == "your child"


def test_family_child_of():
    assert relationship_label("family", "child_of", 80) == "your parent"


def test_family_sibling_of():
    assert relationship_label("family", "sibling_of", 80) == "your sibling"


def test_family_unknown_sub_role():
    assert relationship_label("family", None, 80) == "your family member"


def test_mate_label():
    assert relationship_label("mate", None, 90) == "your mate"


def test_friend_high_strength():
    label = relationship_label("friend", None, 85)
    assert "closest" in label and "friend" in label


def test_friend_medium_strength():
    label = relationship_label("friend", None, 60)
    assert "trusted" in label and "friend" in label


def test_friend_low_strength():
    label = relationship_label("friend", None, 25)
    assert "friend" in label


def test_friend_very_low_strength():
    label = relationship_label("friend", None, 5)
    assert "distant" in label


def test_friend_negative_tense():
    label = relationship_label("friend", None, -20)
    assert "tense" in label


def test_friend_very_negative():
    label = relationship_label("friend", None, -60)
    assert "estranged" in label


def test_enemy_very_negative():
    label = relationship_label("enemy", None, -80)
    assert "bitter" in label


def test_business_partner_label():
    label = relationship_label("business_partner", None, 50)
    assert "business partner" in label


# ---------------------------------------------------------------------------
# to_summary
# ---------------------------------------------------------------------------

def _make_rel(**kwargs) -> RelationshipModel:
    defaults = dict(
        id="r1",
        from_agent_id="a1",
        to_agent_id="a2",
        type="friend",
        sub_role=None,
        strength=50.0,
        is_family=False,
        interaction_count=0,
    )
    defaults.update(kwargs)
    return RelationshipModel(**defaults)


def test_to_summary_fields():
    rel = _make_rel(type="ally", strength=40.0)
    summary = to_summary(rel)
    assert summary.type == "ally"
    assert summary.strength == 40.0
    assert summary.sub_role is None
    assert isinstance(summary.label, str)
    assert len(summary.label) > 0


def test_to_summary_family():
    rel = _make_rel(type="family", sub_role="child_of", strength=70.0, is_family=True)
    summary = to_summary(rel)
    assert summary.label == "your parent"


# ---------------------------------------------------------------------------
# build_relationship_index
# ---------------------------------------------------------------------------

def test_build_index_empty():
    assert build_relationship_index([]) == {}


def test_build_index_single():
    rel = _make_rel(from_agent_id="a1", to_agent_id="a2", type="friend", strength=30.0)
    index = build_relationship_index([rel])
    assert ("a1", "a2") in index
    assert len(index[("a1", "a2")]) == 1
    assert index[("a1", "a2")][0].type == "friend"


def test_build_index_multiple_types_same_pair():
    rel1 = _make_rel(id="r1", from_agent_id="a1", to_agent_id="a2", type="friend", strength=50.0)
    rel2 = _make_rel(id="r2", from_agent_id="a1", to_agent_id="a2", type="business_partner", strength=30.0)
    index = build_relationship_index([rel1, rel2])
    assert len(index[("a1", "a2")]) == 2


def test_build_index_different_pairs():
    rel1 = _make_rel(id="r1", from_agent_id="a1", to_agent_id="a2", type="friend", strength=50.0)
    rel2 = _make_rel(id="r2", from_agent_id="a2", to_agent_id="a1", type="rival", strength=20.0)
    index = build_relationship_index([rel1, rel2])
    assert ("a1", "a2") in index
    assert ("a2", "a1") in index


def test_build_index_directed_not_bidirectional():
    """Relationship from a1→a2 should not appear under a2→a1."""
    rel = _make_rel(from_agent_id="a1", to_agent_id="a2", type="friend", strength=50.0)
    index = build_relationship_index([rel])
    assert ("a2", "a1") not in index


# ---------------------------------------------------------------------------
# Strength delta constants
# ---------------------------------------------------------------------------

def test_fight_delta_is_negative():
    from db.relationships import INTERACTION_STRENGTH_DELTA
    assert INTERACTION_STRENGTH_DELTA["fight"] < 0


def test_help_delta_is_positive():
    from db.relationships import INTERACTION_STRENGTH_DELTA
    assert INTERACTION_STRENGTH_DELTA["help"] > 0


def test_trade_delta_is_positive():
    from db.relationships import INTERACTION_STRENGTH_DELTA
    assert INTERACTION_STRENGTH_DELTA["trade"] > 0
