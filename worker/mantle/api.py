import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from mantle.hardware import STL_PATH, load_hardware
from mantle.jobs import explore, get_build, part_path, project_document, revise, step_path
from mantle.schema import Decisions

ROOT = Path(__file__).resolve().parents[2]
LANGUAGE = ROOT / "design" / "language.json"
BRIEFS = ROOT / "design" / "briefs.json"

app = FastAPI(title="Mantle")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ExploreRequest(BaseModel):
    attributes: list[str] = Field(default_factory=list)
    locks: list[str] = Field(default_factory=list)
    brief: str = ""


class BuildRequest(BaseModel):
    decisions: Decisions
    locks: list[str] = Field(default_factory=list)
    attributes: list[str] = Field(default_factory=list)
    brief: str = ""
    parentId: str | None = None
    summary: str = "Direct edit"


class ActionRequest(BaseModel):
    action: str


@app.get("/api/health")
def health():
    return {"ok": True, "mode": "guided-design"}


@app.get("/api/hardware")
def hardware():
    return load_hardware()


@app.get("/api/hardware/mesh.stl")
def hardware_mesh():
    return FileResponse(STL_PATH, media_type="model/stl", filename="3M1.stl")


@app.get("/api/language")
def language():
    return json.loads(LANGUAGE.read_text())


@app.get("/api/briefs")
def briefs():
    return json.loads(BRIEFS.read_text())


@app.post("/api/explore")
def explore_route(body: ExploreRequest):
    try:
        return {"mode": "guided-design", "alternatives": explore(body.attributes, body.locks, body.brief)}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/api/builds")
def create_build(body: BuildRequest):
    from mantle.jobs import build_revision
    import mantle.jobs as jobs

    try:
        with jobs._LOCK:
            record = build_revision(
                body.decisions,
                body.locks,
                body.attributes,
                body.brief,
                body.parentId,
                body.summary,
                "Direct edit",
            )
    except PermissionError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return record


@app.post("/api/builds/{build_id}/actions")
def act(build_id: str, body: ActionRequest):
    try:
        return revise(build_id, body.action)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="That revision is not in this session.") from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except PermissionError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.get("/api/builds/{build_id}")
def read_build(build_id: str):
    try:
        return get_build(build_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="That revision is not in this session.") from error


@app.get("/api/builds/{build_id}/parts/{name}.stl")
def part_mesh(build_id: str, name: str):
    try:
        return FileResponse(part_path(build_id, name), media_type="model/stl")
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Mesh not found.") from error


@app.get("/api/builds/{build_id}/cover.step")
def step_file(build_id: str):
    try:
        return FileResponse(step_path(build_id), media_type="application/step", filename="mantle-cover.step")
    except PermissionError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except KeyError as error:
        raise HTTPException(status_code=404, detail="STEP not found.") from error


@app.get("/api/builds/{build_id}/project.json")
def project_file(build_id: str):
    try:
        return project_document(build_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="That revision is not in this session.") from error
