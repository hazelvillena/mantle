# Mantle

Living scope. Condensed from the 3 Nov 2026 handoff (v2.1). Edit this file as the product changes.

Help designers turn a design language into editable physical parts around existing engineering. Guided design explores and revises. A live model is a later layer, not this release.

Robotics is the first demo, not the product limit. Do not build other hardware yet.

## The story

1. Open one prepared robot-arm link.
2. Read what can be designed around it.
3. Pick brief attributes. A written note can be saved; it does not generate geometry.
4. Get three covers that differ in shape or construction.
5. Pick one, lock the seam layout, apply Slimmer.
6. See the change. The lock stays.
7. Show the machinery and the geometric findings.
8. Export STEP for the cover, plus a project file this app can reopen.

## In

- One curated machine. First candidate: [BCN3D Moveo](https://github.com/BCN3D/BCN3D-Moveo) (MIT). One rigid link. A cover with two panels. No cover across a joint.
- Guided design. Selected attributes choose a recipe and parameters. The screen shows which attributes were applied.
- Decisions: profile, fullness, taper, end coverage, panel layout, seam, access panel, finish. Some change geometry. Finish is appearance only and is not a material proof.
- Example starting points, not a fixed catalog: Consumer, Industrial, Service. Text is editable. See `design/briefs.json`.
- Locks are enforced in code. The first lock is the seam **layout**, not the seam’s exact position in space.
- Checks on the current design and a small, named pose set. A part inside another solid counts as interference. A bounding-box overlap is only a candidate.
- Export STEP from the same CAD build the user sees. Also save project JSON (model, recipe, decisions, locks, revision). STEP is blocked when geometry is invalid or a required check is stale, failed, or shows prohibited interference. JSON still saves.
- Desktop workspace, black and white: brief and alternatives on the left, the model in the center, decisions on the right. Usable with a keyboard. It must not break on a narrow screen.

## Out

Live language models, image input, arbitrary CAD upload, a whole-robot skin, mechanical redesign, robot control, safety or manufacturing claims, login, teams, billing.

## One record

Controls, generation, checks, and export share one versioned design state.

| Record | Holds |
| --- | --- |
| Hardware | Source, units, frames, envelope, keep-outs, poses, verified vs assumed |
| Language | Decisions, defaults, which locks exist |
| Revision | Parent, decisions, locks, brief, what changed |
| Build | Solids and preview for that revision |
| Check | Findings for that build. Any geometry edit invalidates them |

A future model must return this same state. Reject unknown fields, hardware edits, and changes to locked decisions. A late result cannot overwrite a newer edit.

## Rules

- No API key. Do not describe Guided design as a live model.
- Free-text requests say that language interpretation is not connected, and name what is supported.
- “Slimmer” and “Preserve seam layout” change or lock real decisions.
- Do not invent measurements. Recheck before calling a problem fixed.
- Say “No interference found in these tested poses.” Do not say the robot is safe or clear through its whole motion.
- Failed jobs keep the previous revision and label it as previous.
- Do not ship a canned mesh, a fake check, or a picture in place of generated geometry.
- Mechanical reference quality is labeled. Approximations are written down.

## Status

The local workspace covers one Moveo forearm. Guided design, three alternatives, Slimmer, and the seam-layout lock are in. A long cover clashes with the prepared joint in the extended pose. Reduce end coverage changes that decision, rebuilds, and rechecks before the clash is treated as cleared. STEP stays blocked while a clash stands. Live models and a second machine are out.
