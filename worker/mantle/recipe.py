"""One sleeve recipe. Stations come from the hardware envelope."""

from __future__ import annotations

import math

import cadquery as cq

from mantle.bounds import END_MM, FULLNESS_MM, GAP_MM, SEAM_MM, TAPER, WALL_MM
from mantle.hardware import radius_at
from mantle.schema import Decisions

BIG = 900.0


def _plane(y: float, center_x: float, center_z: float) -> cq.Workplane:
    # File +Y is the link axis. This plane's local Y is file +Z, so center()
    # takes file X with a flipped sign. See the bounding-box test.
    plane = cq.Plane(origin=(0, y, 0), xDir=(-1, 0, 0), normal=(0, 1, 0))
    return cq.Workplane(plane).center(-center_x, center_z)


def _loft(stations: list[tuple[float, float, float]], profile: str, center) -> cq.Workplane:
    center_x, center_z = center
    workplane = None
    previous = None
    for y, rx, rz in stations:
        if workplane is None:
            workplane = _plane(y, center_x, center_z)
        else:
            workplane = workplane.workplane(offset=y - previous)
        if profile == "oval":
            workplane = workplane.ellipse(max(rx, 1), max(rz, 1))
        elif profile == "faceted":
            # Vertices sit outside the clearance circle so the flats do not cut the envelope.
            radius = max(rx, rz, 1)
            workplane = workplane.polygon(8, 2 * radius / math.cos(math.pi / 8))
        else:
            workplane = workplane.circle(max(rx, rz, 1))
        previous = y
    return workplane.loft(combine=True)


def _stations(hardware: dict, decisions: Decisions, clearance: float, outer: bool) -> list[tuple[float, float, float]]:
    y0, y1 = hardware["span"]
    extra = END_MM[decisions.end_coverage]
    start = y0 - extra
    end = y1 + extra
    if outer:
        # Keep the inner void longer than the sleeve so the ends stay open.
        pass
    else:
        start -= 1.5
        end += 1.5
    count = 7
    samples = [start + (end - start) * step / (count - 1) for step in range(count)]
    taper_start, taper_end = TAPER[decisions.taper]
    fullness = FULLNESS_MM[decisions.fullness] if outer else 0.0
    built = []
    for y in samples:
        span = end - start
        mix = 0 if span == 0 else (y - start) / span
        scale = taper_start + (taper_end - taper_start) * mix if outer else 1
        rx, rz = radius_at(hardware, min(max(y, y0), y1))
        grow = GAP_MM + (WALL_MM + fullness if outer else 0)
        rx = (rx + grow) * scale
        rz = (rz + grow) * scale
        if outer:
            rx = max(rx, radius_at(hardware, min(max(y, y0), y1))[0] + GAP_MM + WALL_MM)
            rz = max(rz, radius_at(hardware, min(max(y, y0), y1))[1] + GAP_MM + WALL_MM)
        built.append((y, rx, rz))
    return built


def _remove_above(shape: cq.Workplane, z: float) -> cq.Workplane:
    cutter = cq.Workplane("XY").box(BIG, BIG, BIG).translate((0, 0, z + BIG / 2))
    return shape.cut(cutter)


def _remove_below(shape: cq.Workplane, z: float) -> cq.Workplane:
    cutter = cq.Workplane("XY").box(BIG, BIG, BIG).translate((0, 0, z - BIG / 2))
    return shape.cut(cutter)


def _remove_beyond(shape: cq.Workplane, y: float) -> cq.Workplane:
    cutter = cq.Workplane("XY").box(BIG, BIG, BIG).translate((0, y + BIG / 2, 0))
    return shape.cut(cutter)


def _remove_before(shape: cq.Workplane, y: float) -> cq.Workplane:
    cutter = cq.Workplane("XY").box(BIG, BIG, BIG).translate((0, y - BIG / 2, 0))
    return shape.cut(cutter)


def _only_solids(shape: cq.Workplane) -> list[cq.Shape]:
    return [solid for solid in shape.solids().vals() if solid.Volume() > 1]


def _access(panel: cq.Shape, decisions: Decisions) -> tuple[cq.Shape, cq.Shape | None]:
    if decisions.access_panel == "none":
        return panel, None
    box = panel.BoundingBox()
    length = box.ymax - box.ymin
    y = box.ymax - length * 0.22 if decisions.access_panel == "end" else box.ymin + length * 0.55
    lid_box = cq.Workplane("XY").box(32, 46, 24).translate(((box.xmin + box.xmax) / 2, y, box.zmax - 7))
    hole = cq.Workplane("XY").box(32 + SEAM_MM[decisions.seam] * 2, 46 + SEAM_MM[decisions.seam] * 2, 28).translate(
        ((box.xmin + box.xmax) / 2, y, box.zmax - 7)
    )
    host = cq.Workplane().add(panel)
    lid = host.intersect(lid_box)
    opened = host.cut(hole)
    lid_solids = _only_solids(lid)
    opened_solids = _only_solids(opened)
    if not lid_solids or not opened_solids:
        raise RuntimeError("The access panel did not land on the cover. Try another layout.")
    # A small lift keeps the lid from sharing faces with the opening.
    lifted = lid_solids[0].translate((0, 0, 0.8))
    return opened_solids[0], lifted


def build_parts(hardware: dict, decisions: Decisions) -> dict[str, cq.Shape]:
    center = (hardware["center"][0], hardware["center"][2])
    outer = _loft(_stations(hardware, decisions, GAP_MM, True), decisions.profile, center)
    inner = _loft(_stations(hardware, decisions, 0, False), decisions.profile, center)
    shell = outer.cut(inner)
    solids = _only_solids(shell)
    if len(solids) != 1:
        raise RuntimeError("The sleeve did not resolve to a single solid.")
    body = cq.Workplane().add(solids[0])
    center_z = hardware["center"][2]
    gap = SEAM_MM[decisions.seam]

    parts: dict[str, cq.Shape] = {}
    if decisions.panel_layout == "single-shell":
        parts["shell"] = solids[0]
    elif decisions.panel_layout == "band-and-body":
        y0, y1 = hardware["span"]
        seam = y0 + (y1 - y0) * 0.72
        band = _only_solids(_remove_before(body, seam + gap / 2))
        main = _only_solids(_remove_beyond(body, seam - gap / 2))
        if len(band) != 1 or len(main) != 1:
            raise RuntimeError("The band split did not produce two solids.")
        panel, lid = _access(main[0], decisions)
        parts["body"] = panel
        parts["band"] = band[0]
        if lid is not None:
            parts["access-panel"] = lid
    else:
        lower = _only_solids(_remove_above(body, center_z - gap / 2))
        upper = _only_solids(_remove_below(body, center_z + gap / 2))
        if len(lower) != 1 or len(upper) != 1:
            raise RuntimeError("The lengthwise split did not produce two solids.")
        parts["panel-b"] = lower[0]
        panel, lid = _access(upper[0], decisions)
        parts["panel-a"] = panel
        if lid is not None:
            parts["access-panel"] = lid

    if decisions.panel_layout == "single-shell" and decisions.access_panel != "none":
        panel, lid = _access(parts.pop("shell"), decisions)
        parts["shell"] = panel
        if lid is not None:
            parts["access-panel"] = lid
    return parts


def envelope_solid(hardware: dict) -> cq.Shape:
    """Conservative hardware volume used for clearance, not the triangle mesh."""
    y0, y1 = hardware["span"]
    samples = []
    for step in range(5):
        y = y0 + (y1 - y0) * step / 4
        rx, rz = radius_at(hardware, y)
        samples.append((y, max(rx - 0.4, 1), max(rz - 0.4, 1)))
    center = (hardware["center"][0], hardware["center"][2])
    return _loft(samples, "oval", center).val()


def keep_out_solid(hardware: dict) -> cq.Shape:
    keep = hardware["keepOut"]
    size = keep["size"]
    center = keep["center"]
    return cq.Workplane("XY").box(*size).translate(tuple(center)).val()
