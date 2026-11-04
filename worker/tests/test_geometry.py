import cadquery as cq

from mantle.checks import check_build, point_inside
from mantle.guided import apply_attributes, propose, step_slimmer
from mantle.hardware import load_hardware
from mantle.jobs import build_revision
from mantle.recipe import build_parts, envelope_solid, keep_out_solid
from mantle.schema import Decisions


def test_containment_is_not_missed():
    outer = cq.Workplane("XY").box(10, 10, 10).val()
    inner = cq.Workplane("XY").box(4, 4, 4).val()
    assert point_inside(outer, (0, 0, 0))
    common = cq.Workplane().add(outer).intersect(cq.Workplane().add(inner))
    assert common.val().Volume() > 50


def test_short_is_clear_and_long_hits_extended_only():
    hardware = load_hardware()
    short = Decisions.model_validate({"end-coverage": "short", "panel-layout": "lengthwise-split"})
    long = Decisions.model_validate({"end-coverage": "long", "fullness": "generous"})
    for decisions, extended_clear in ((short, True), (long, False)):
        parts = build_parts(hardware, decisions)
        report = check_build(parts, hardware, envelope_solid(hardware), keep_out_solid(hardware))
        poses = {item["pose"]: item["clear"] for item in report["poses"]}
        assert poses["extended"] is extended_clear
        assert poses["folded"] is True
        assert all(solid.Volume() > 500 for solid in parts.values())


def test_panels_are_separate_and_clear_the_envelope():
    hardware = load_hardware()
    parts = build_parts(hardware, Decisions())
    assert set(parts) == {"panel-a", "panel-b"}
    report = check_build(parts, hardware, envelope_solid(hardware), keep_out_solid(hardware))
    assert report["blocksExport"] is False
    assert "No interference found" in report["summary"]


def test_step_reopens_with_the_same_solids():
    hardware = load_hardware()
    record = build_revision(Decisions(), [], [], "", None, "test", "Matched brief")
    from pathlib import Path

    step = Path(__file__).resolve().parents[1] / "data" / record["id"] / "cover.step"
    opened = cq.importers.importStep(str(step))
    solids = opened.solids().vals()
    assert len(solids) == 2
    exported = sum(solid.Volume() for solid in solids)
    source = sum(solid.Volume() for solid in build_parts(hardware, Decisions()).values())
    assert abs(exported - source) / source < 0.01


def test_guided_briefs_differ_and_slimmer_steps_once():
    consumer, _ = apply_attributes(
        ["quiet-silhouette", "smooth-transitions", "concealed-mechanics"]
    )
    industrial, applied = apply_attributes(["paneled", "exposed-mechanism", "easy-access"])
    assert consumer.geometry_key() != industrial.geometry_key()
    assert any(item.source == "Exposed mechanism" for item in applied)
    closer, note = step_slimmer(consumer)
    assert closer.fullness == "balanced"
    assert "generous" in note
    proposals = propose(["approachable", "rounded-transitions", "maintenance-panel"], ["seam-layout"])
    layouts = {item.decisions.panel_layout for item in proposals}
    assert layouts == {"lengthwise-split"}
    assert len({item.decisions.geometry_key() for item in proposals}) == 3


def test_lock_rejects_a_new_split():
    parent = build_revision(
        Decisions(),
        ["seam-layout"],
        [],
        "",
        None,
        "locked",
        "Matched brief",
    )
    changed = Decisions.model_validate({"panel-layout": "single-shell"})
    try:
        build_revision(changed, ["seam-layout"], [], "", parent["id"], "edit", "edit")
    except PermissionError as error:
        assert "panel split" in str(error)
    else:
        raise AssertionError("lock did not hold")
