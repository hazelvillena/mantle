"""Geometric checks. A missing result is never stored as a pass."""

from __future__ import annotations

import cadquery as cq
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.gp import gp_Pnt
from OCP.TopAbs import TopAbs_IN

from mantle.bounds import INTERFERENCE_MM3, MIN_CLEARANCE_MM, MIN_SOLID_MM3, POSES

METHOD_VOLUME = "opencascade-common-volume"
METHOD_DISTANCE = "opencascade-min-distance"


def _common_volume(left: cq.Shape, right: cq.Shape) -> float:
    common = cq.Workplane().add(left).intersect(cq.Workplane().add(right))
    return sum(solid.Volume() for solid in common.solids().vals())


def _distance(left: cq.Shape, right: cq.Shape) -> float | None:
    tool = BRepExtrema_DistShapeShape(left.wrapped, right.wrapped)
    tool.Perform()
    if not tool.IsDone():
        return None
    return float(tool.Value())


def _pose(shape: cq.Shape, pivot: list[float], degrees: float) -> cq.Shape:
    if abs(degrees) < 1e-6:
        return shape
    origin = (pivot[0], pivot[1], pivot[2])
    axis = (pivot[0] + 1, pivot[1], pivot[2])
    return shape.rotate(origin, axis, degrees)


def point_inside(shape: cq.Shape, point: tuple[float, float, float]) -> bool:
    classifier = BRepClass3d_SolidClassifier(shape.wrapped, gp_Pnt(*point), 1e-6)
    return classifier.State() == TopAbs_IN


def check_build(parts: dict[str, cq.Shape], hardware: dict, envelope: cq.Shape, keep_out: cq.Shape) -> dict:
    findings = []
    for name, solid in parts.items():
        if solid.ShapeType() != "Solid" or not solid.isValid() or solid.Volume() < MIN_SOLID_MM3:
            findings.append(
                {
                    "id": f"solid-{name}",
                    "severity": "failed",
                    "pose": None,
                    "parts": [name],
                    "method": "opencascade-solid-validity",
                    "threshold": MIN_SOLID_MM3,
                    "measured": None if solid.Volume() != solid.Volume() else round(solid.Volume(), 2),
                    "quality": "exact-brep",
                    "message": f"{name} is not a closed solid with usable volume.",
                }
            )

    names = list(parts)
    for index, left in enumerate(names):
        for right in names[index + 1 :]:
            volume = _common_volume(parts[left], parts[right])
            if volume > INTERFERENCE_MM3:
                findings.append(
                    {
                        "id": f"parts-{left}-{right}",
                        "severity": "interference",
                        "pose": "link",
                        "parts": [left, right],
                        "method": METHOD_VOLUME,
                        "threshold": INTERFERENCE_MM3,
                        "measured": round(volume, 2),
                        "quality": "exact-brep",
                        "message": f"{left} intersects {right}. Widen the seam or remove the access panel, then check again.",
                    }
                )

    overlap = sum(_common_volume(solid, envelope) for solid in parts.values())
    if overlap > INTERFERENCE_MM3:
        findings.append(
            {
                "id": "fills-hardware",
                "severity": "interference",
                "pose": "link",
                "parts": [*names, "envelope"],
                "method": METHOD_VOLUME,
                "threshold": INTERFERENCE_MM3,
                "measured": round(overlap, 2),
                "quality": "envelope",
                "message": "The cover occupies the hardware envelope. Increase the gap before treating this as a sleeve.",
            }
        )
    distances = [_distance(solid, envelope) for solid in parts.values()]
    gap = None if any(item is None for item in distances) else min(distances)
    if gap is None:
        findings.append(
            {
                "id": "gap-unknown",
                "severity": "failed",
                "pose": "link",
                "parts": [*names, "envelope"],
                "method": METHOD_DISTANCE,
                "threshold": MIN_CLEARANCE_MM,
                "measured": None,
                "quality": "envelope",
                "message": "The gap to the hardware envelope could not be measured. This is not a pass.",
            }
        )
    elif gap < MIN_CLEARANCE_MM:
        findings.append(
            {
                "id": "gap-small",
                "severity": "interference",
                "pose": "link",
                "parts": [*names, "envelope"],
                "method": METHOD_DISTANCE,
                "threshold": MIN_CLEARANCE_MM,
                "measured": round(gap, 3),
                "quality": "envelope",
                "message": f"The cover comes within {gap:.2f} mm of the hardware envelope. The prepared minimum is {MIN_CLEARANCE_MM:.1f} mm.",
            }
        )

    pose_results = []
    for pose in POSES:
        volume = 0.0
        for solid in parts.values():
            posed = _pose(solid, hardware["pivot"], pose["degrees"])
            volume += _common_volume(posed, keep_out)
        hit = volume > INTERFERENCE_MM3
        pose_results.append(
            {
                "pose": pose["id"],
                "label": pose["label"],
                "degrees": pose["degrees"],
                "interferenceMm3": round(volume, 2),
                "clear": not hit,
            }
        )
        if hit:
            findings.append(
                {
                    "id": f"keep-out-{pose['id']}",
                    "severity": "interference",
                    "pose": pose["id"],
                    "parts": [*names, hardware["keepOut"]["id"]],
                    "method": METHOD_VOLUME,
                    "threshold": INTERFERENCE_MM3,
                    "measured": round(volume, 2),
                    "quality": "prepared-keep-out",
                    "message": (
                        f"This cover intersects the neighboring joint in the {pose['label'].lower()} pose. "
                        "Reduce the end coverage and check again."
                    ),
                }
            )
        else:
            pose_results[-1]["message"] = f"No interference found in the {pose['label'].lower()} pose."

    blocking = [item for item in findings if item["severity"] in {"interference", "failed"}]
    return {
        "coverage": "Extended and folded poses, against the sliced envelope and one prepared keep-out.",
        "quality": "Envelope and keep-out. Not a triangle-accurate clash with the STL, and not a full sweep.",
        "poses": pose_results,
        "findings": findings,
        "blocksExport": bool(blocking),
        "summary": (
            blocking[0]["message"]
            if blocking
            else "No interference found in these tested poses."
        ),
    }

