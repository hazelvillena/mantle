"""Rule-based design assistant. Selected attributes map to recipe choices."""

from mantle.schema import Applied, Decisions, Proposal

# Later rows win when two attributes set the same decision.
EFFECTS: dict[str, dict[str, str]] = {
    "quiet-silhouette": {"profile": "rounded", "fullness": "close", "taper": "toward-end"},
    "smooth-transitions": {"profile": "rounded", "seam": "shadow"},
    "concealed-mechanics": {
        "fullness": "generous",
        "end-coverage": "standard",
        "access-panel": "none",
    },
    "paneled": {"profile": "faceted", "panel-layout": "lengthwise-split", "seam": "shadow"},
    "exposed-mechanism": {"fullness": "close", "end-coverage": "short"},
    "easy-access": {"access-panel": "side", "seam": "open", "panel-layout": "lengthwise-split"},
    "approachable": {"profile": "oval", "fullness": "balanced"},
    "rounded-transitions": {"profile": "rounded", "seam": "shadow"},
    "maintenance-panel": {"access-panel": "side", "profile": "rounded"},
}

ATTRIBUTE_ORDER = list(EFFECTS)
LABELS = {
    "quiet-silhouette": "Quiet silhouette",
    "smooth-transitions": "Smooth transitions",
    "concealed-mechanics": "Concealed mechanics",
    "paneled": "Purposeful panels",
    "exposed-mechanism": "Exposed mechanism",
    "easy-access": "Easy access",
    "approachable": "Approachable proportions",
    "rounded-transitions": "Rounded transitions",
    "maintenance-panel": "Maintenance panel",
}

PROFILE_CYCLE = ["rounded", "oval", "faceted"]
LAYOUT_CYCLE = ["lengthwise-split", "band-and-body", "single-shell"]
FULLNESS_CYCLE = ["close", "balanced", "generous"]
TAPER_CYCLE = ["none", "toward-end", "toward-base"]


def _next(options: list[str], value: str) -> str:
    return options[(options.index(value) + 1) % len(options)]


def apply_attributes(attributes: list[str]) -> tuple[Decisions, list[Applied]]:
    values: dict[str, str] = {}
    sources: dict[str, str] = {}
    unknown = [item for item in attributes if item not in EFFECTS]
    if unknown:
        known = ", ".join(LABELS.values())
        raise ValueError(f"Unknown brief attribute. Supported attributes: {known}.")
    for attribute in ATTRIBUTE_ORDER:
        if attribute not in attributes:
            continue
        for decision, value in EFFECTS[attribute].items():
            values[decision] = value
            sources[decision] = LABELS[attribute]
    decisions = Decisions.model_validate(values)
    applied = [
        Applied(decision=decision, value=value, source=sources[decision])
        for decision, value in decisions.model_dump(by_alias=True).items()
        if decision in sources
    ]
    return decisions, applied


def propose(attributes: list[str], locks: list[str]) -> list[Proposal]:
    primary, applied = apply_attributes(attributes)
    dumped = primary.model_dump(by_alias=True)
    seam_locked = "seam-layout" in locks

    second = dict(dumped)
    second["profile"] = _next(PROFILE_CYCLE, dumped["profile"])
    if not seam_locked:
        second["panel-layout"] = _next(LAYOUT_CYCLE, dumped["panel-layout"])

    third = dict(dumped)
    third["fullness"] = _next(FULLNESS_CYCLE, dumped["fullness"])
    third["taper"] = _next(TAPER_CYCLE, dumped["taper"])
    third["end-coverage"] = "long" if dumped["end-coverage"] != "long" else "short"

    proposals = [
        Proposal(
            name="Matched brief",
            rationale="Each selected attribute sets a recipe choice. The written note is not one of them.",
            decisions=primary,
            applied=applied,
            locks=locks,
        ),
        Proposal(
            name="Another construction",
            rationale="A different profile and, unless the seam layout is locked, a different panel split.",
            decisions=Decisions.model_validate(second),
            applied=applied,
            locks=locks,
        ),
        Proposal(
            name="Longer reach",
            rationale="A fuller or slimmer body, with the cover pushed toward the neighboring joint.",
            decisions=Decisions.model_validate(third),
            applied=applied,
            locks=locks,
        ),
    ]
    keys = [item.decisions.geometry_key() for item in proposals]
    if len(set(keys)) < 3:
        raise RuntimeError("Guided design failed to produce three different shapes.")
    return proposals


def step_slimmer(decisions: Decisions) -> tuple[Decisions, str]:
    order = FULLNESS_CYCLE
    if decisions.fullness == "close":
        return decisions, "Fullness is already as close as this recipe allows."
    updated = decisions.model_copy(
        update={"fullness": order[order.index(decisions.fullness) - 1]}
    )
    return updated, f"Fullness moved from {decisions.fullness} to {updated.fullness}."


def step_reduce_end_coverage(decisions: Decisions) -> tuple[Decisions, str]:
    order = ["short", "standard", "long"]
    if decisions.end_coverage == "short":
        return decisions, "End coverage is already as short as this recipe allows."
    updated = decisions.model_copy(
        update={"end_coverage": order[order.index(decisions.end_coverage) - 1]}
    )
    return (
        updated,
        f"End coverage moved from {decisions.end_coverage} to {updated.end_coverage}.",
    )
