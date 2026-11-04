"""Build a revision, write meshes, and keep the result tied to that revision."""

from __future__ import annotations

import json
import threading
import time
import uuid
from pathlib import Path

import cadquery as cq

from mantle.bounds import PREVIEW_ANGULAR_RAD, PREVIEW_LINEAR_MM, RECIPE_ID, RECIPE_VERSION
from mantle.checks import check_build
from mantle.guided import propose, step_reduce_end_coverage, step_slimmer
from mantle.hardware import HARDWARE_VERSION, load_hardware
from mantle.recipe import build_parts, envelope_solid, keep_out_solid
from mantle.schema import Decisions

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "worker" / "data"
_LOCK = threading.Lock()
_BUILDS: dict[str, dict] = {}


def _part_url(build_id: str, name: str) -> str:
    return f"/api/builds/{build_id}/parts/{name}.stl"


def _write_stl(shape: cq.Shape, path: Path) -> None:
    # Relative deflection grows with edge length and facets the sleeve.
    shape.exportStl(
        str(path),
        tolerance=PREVIEW_LINEAR_MM,
        angularTolerance=PREVIEW_ANGULAR_RAD,
        ascii=False,
        relative=False,
    )


def _write_step(parts: dict, path: Path) -> None:
    compound = cq.Compound.makeCompound(list(parts.values()))
    cq.exporters.export(compound, str(path), exportType="STEP")


def build_revision(
    decisions: Decisions,
    locks: list[str],
    attributes: list[str],
    brief: str,
    parent_id: str | None,
    summary: str,
    name: str,
) -> dict:
    if "seam-layout" in locks and parent_id:
        parent = _BUILDS.get(parent_id)
        if parent and parent["decisions"].get("panel-layout") != decisions.panel_layout:
            raise PermissionError(
                "Seam layout is locked. That keeps the panel split, not the seam's position in space. Unlock it to change the split."
            )

    hardware = load_hardware()
    started = time.perf_counter()
    parts = build_parts(hardware, decisions)
    envelope = envelope_solid(hardware)
    keep_out = keep_out_solid(hardware)
    report = check_build(parts, hardware, envelope, keep_out)
    build_id = uuid.uuid4().hex[:12]
    folder = DATA / build_id
    folder.mkdir(parents=True, exist_ok=True)
    for part_name, solid in parts.items():
        _write_stl(solid, folder / f"{part_name}.stl")
    _write_step(parts, folder / "cover.step")
    elapsed = round((time.perf_counter() - started) * 1000)
    record = {
        "id": build_id,
        "name": name,
        "parentId": parent_id,
        "hardwareVersion": HARDWARE_VERSION,
        "recipeId": RECIPE_ID,
        "recipeVersion": RECIPE_VERSION,
        "decisions": decisions.model_dump(by_alias=True),
        "locks": locks,
        "attributes": attributes,
        "brief": brief,
        "summary": summary,
        "parts": [
            {"name": part_name, "url": _part_url(build_id, part_name)}
            for part_name in parts
        ],
        "check": {**report, "buildId": build_id},
        "elapsedMs": elapsed,
        "exportStep": f"/api/builds/{build_id}/cover.step",
        "project": f"/api/builds/{build_id}/project.json",
    }
    (folder / "record.json").write_text(json.dumps(record, indent=2))
    _BUILDS[build_id] = record
    return record


def explore(attributes: list[str], locks: list[str], brief: str) -> list[dict]:
    proposals = propose(attributes, locks)
    results = []
    with _LOCK:
        for proposal in proposals:
            try:
                record = build_revision(
                    proposal.decisions,
                    locks,
                    attributes,
                    brief,
                    None,
                    proposal.rationale,
                    proposal.name,
                )
                results.append(
                    {
                        "ok": True,
                        "name": proposal.name,
                        "rationale": proposal.rationale,
                        "applied": [item.model_dump() for item in proposal.applied],
                        "build": record,
                    }
                )
            except Exception as error:  # noqa: BLE001 — one failed alternative must not drop the others
                results.append(
                    {
                        "ok": False,
                        "name": proposal.name,
                        "rationale": proposal.rationale,
                        "applied": [item.model_dump() for item in proposal.applied],
                        "error": str(error),
                    }
                )
    return results


def revise(build_id: str, action: str) -> dict:
    current = get_build(build_id)
    decisions = Decisions.model_validate(current["decisions"])
    locks = list(current["locks"])
    if action == "preserve-seam-layout":
        if "seam-layout" not in locks:
            locks.append("seam-layout")
        summary = "Seam layout locked. The panel split stays. Its position in space can still change."
        updated = decisions
    elif action == "slimmer":
        updated, summary = step_slimmer(decisions)
        if updated.fullness == decisions.fullness:
            return {"ok": True, "changed": False, "summary": summary, "build": current}
    elif action == "reduce-end-coverage":
        updated, summary = step_reduce_end_coverage(decisions)
        if updated.end_coverage == decisions.end_coverage:
            return {"ok": True, "changed": False, "summary": summary, "build": current}
    else:
        raise ValueError(
            "Supported actions are Slimmer, Preserve seam layout, and Reduce end coverage."
        )
    with _LOCK:
        record = build_revision(
            updated,
            locks,
            current["attributes"],
            current["brief"],
            build_id,
            summary,
            current["name"],
        )
    if action == "reduce-end-coverage":
        summary = f"{summary} Rechecked this revision. {record['check']['summary']}"
        record["summary"] = summary
        (DATA / record["id"] / "record.json").write_text(json.dumps(record, indent=2))
    return {"ok": True, "changed": True, "summary": summary, "build": record}


def get_build(build_id: str) -> dict:
    record = _BUILDS.get(build_id)
    if record is None:
        raise KeyError(build_id)
    return record


def part_path(build_id: str, name: str) -> Path:
    path = DATA / build_id / f"{name}.stl"
    if not path.is_file():
        raise KeyError(name)
    return path


def step_path(build_id: str) -> Path:
    record = get_build(build_id)
    if record["check"]["blocksExport"]:
        raise PermissionError(record["check"]["summary"])
    path = DATA / build_id / "cover.step"
    if not path.is_file():
        raise KeyError(build_id)
    return path


def project_document(build_id: str) -> dict:
    record = get_build(build_id)
    hardware = load_hardware()
    return {
        "modelVersion": hardware["version"],
        "recipeId": record["recipeId"],
        "recipeVersion": record["recipeVersion"],
        "decisions": record["decisions"],
        "locks": record["locks"],
        "attributes": record["attributes"],
        "brief": record["brief"],
        "revisionId": record["id"],
        "parentId": record["parentId"],
        "summary": record["summary"],
        "checkSummary": record["check"]["summary"],
        "assumptions": hardware["assumptions"],
        "attribution": hardware["attribution"],
    }
