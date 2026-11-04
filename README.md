# Mantle

A workspace for designing a cover around existing hardware. The first demo is one link from the BCN3D Moveo arm.

Guided design maps selected brief attributes to a recipe. It does not call a language model. A written note is saved and does not change the shape.

## Run

Two processes. Python 3.12.

```bash
python3 -m venv worker/.venv
worker/.venv/bin/pip install -r worker/requirements.txt
worker/.venv/bin/uvicorn mantle.api:app --app-dir worker --host 127.0.0.1 --port 43128
```

```bash
cd web
npm install
npm run dev
```

Open http://127.0.0.1:39241

Choose Consumer, Industrial, or Service. Three covers are generated. Export STEP is enabled when the tested poses are clear. Project JSON downloads either way.

```bash
worker/.venv/bin/python -m pytest -q --tb=line
```

Run pytest from `worker/`.

## Read

- [Product](docs/product.md)
- [Decisions](docs/decisions.md)
- [Roadmap](docs/roadmap.md)
- [Moveo provenance](hardware/moveo/PROVENANCE.md)

## Limits

- One rigid link, part 3M1. The cover does not cross a joint.
- The gray mesh is the official STL. Clearance is against a sliced envelope, not every triangle.
- Units are treated as millimeters from the 190.1 mm span. They were not checked against a drawing.
- “No interference found in these tested poses” is the strongest clearance claim.
- STEP was reopened with CadQuery, the same kernel that wrote it. A second CAD application was not available here.
- Revisions live in the worker process. Restarting it clears them.
