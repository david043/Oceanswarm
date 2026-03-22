"""Pure helpers for relationship context — no DB access."""
from agents.schemas import RelationshipSummary
from db.models import RelationshipModel


_FAMILY_LABELS: dict[str, str] = {
    "parent_of": "your child",
    "child_of":  "your parent",
    "sibling_of": "your sibling",
}


def relationship_label(rel_type: str, sub_role: str | None, strength: float) -> str:
    """Return a human-readable label for a relationship edge."""
    if rel_type == "family":
        return _FAMILY_LABELS.get(sub_role or "", "your family member")
    if rel_type == "mate":
        return "your mate"

    # Dynamic types — label intensity by strength
    _pos: dict[str, str] = {
        "friend":           "friend",
        "enemy":            "frenemy",   # positive end of enemy arc
        "ally":             "ally",
        "rival":            "rival",
        "mentor":           "mentor",
        "leader":           "leader",
        "business_partner": "business partner",
    }
    _neg: dict[str, str] = {
        "friend":           "estranged friend",
        "enemy":            "bitter enemy",
        "ally":             "former ally",
        "rival":            "bitter rival",
        "mentor":           "estranged mentor",
        "leader":           "oppressive leader",
        "business_partner": "business rival",
    }

    if strength >= 80:
        return f"your closest {_pos.get(rel_type, rel_type)}"
    if strength >= 50:
        return f"a trusted {_pos.get(rel_type, rel_type)}"
    if strength >= 20:
        return f"a {_pos.get(rel_type, rel_type)}"
    if strength >= 0:
        return f"a distant {_pos.get(rel_type, rel_type)}"
    if strength >= -30:
        return f"a tense {_pos.get(rel_type, rel_type)}"
    return f"your {_neg.get(rel_type, rel_type)}"


def to_summary(rel: RelationshipModel) -> RelationshipSummary:
    return RelationshipSummary(
        type=rel.type,
        sub_role=rel.sub_role,
        strength=rel.strength,
        label=relationship_label(rel.type, rel.sub_role, rel.strength),
    )


def build_relationship_index(
    rels: list[RelationshipModel],
) -> dict[tuple[str, str], list[RelationshipSummary]]:
    """
    Build a lookup: (from_agent_id, to_agent_id) → [RelationshipSummary, ...]
    from a flat list of RelationshipModel rows.
    """
    index: dict[tuple[str, str], list[RelationshipSummary]] = {}
    for rel in rels:
        key = (rel.from_agent_id, rel.to_agent_id)
        index.setdefault(key, []).append(to_summary(rel))
    return index
