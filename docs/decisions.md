# Decisions

Short log. Add a line when a choice would be costly to reverse.

## 2026-11-03

- **This file set is the spec we edit.** `docs/product.md` is the living scope. The long handoff stays in chat. We do not keep a second full copy in the repo.
- **Guided design only.** No model, no key, no local weights. The design record is shaped so a later model can write the same fields.
- **One link, two panels.** The cover stays on one rigid Moveo segment. A cover across a joint is out until this path works.
- **Seam lock means layout.** Locking keeps the panel split category. It does not promise the seam stays in the same place in space.
- **Moveo is the source to try, not a proven import.** Pin a commit, keep the MIT notice, and confirm units before any cover is treated as real. If conversion blocks us, say what failed and name another licensed model. A stand-in arm is allowed only with a visible label, and it cannot quietly become the reference.
- **Stack to test in Phase 0, not a vow.** React, TypeScript, Three.js, a Python CAD worker, CadQuery for solids and STEP. Use the CAD kernel for the first interference checks. Add another collision library only if containment or gap checks fail there.
- **Millimeters in the model.** One conversion into the viewer. Do not sprinkle unit factors through recipes.
- **Look follows a working export.** The workspace should be quiet, black and white, and centered on the model. We do not polish a screen that cannot generate and export.
- **Phase 0 uses the official 3M1 STL plus a sliced envelope.** SolidWorks files are not imported. Checks use the envelope and one prepared keep-out. They do not clash the raw triangles.
- **CadQuery 2.6.1 builds the sleeve and the STEP file.** The browser only displays meshes. Interference is an OpenCascade common-volume test.
- **The workspace is custom HTML, not a component kit.** The layout is the product surface. Primitives are plain buttons and fields.
- **The on-screen cover is a display mesh of the STEP solid.** It uses a 0.1 mm absolute deflection so long edges stay smooth. The viewer welds those vertices and shades the surface, keeping creases at the cut edges.
- **Rhino 8 read one exported STEP.** The file is the Longer reach cover after Reduce end coverage, with the seam layout still locked. Rhino reported millimeters, 2 solids, and an overall size of 148.877 × 198.1 × 148.893 mm. CadQuery wrote the file. Rhino only read it.
