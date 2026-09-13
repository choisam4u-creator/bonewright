---
name: bonewright
description: Rig a character mesh in Blender (Rigify humanoid/quadruped) and verify it with gates and image checks; generate motion from text with kimodo.cpp. Use when the user asks to rig, skin, auto-rig, animate or "make this character move" in Blender.
---

# Bonewright for Codex

The pipeline is driven by Python, not by you. You run the `bw` CLI, read its report, and explain it. Never re-implement steps with ad-hoc bpy code.

## Setup (once)
- `bw doctor` must show a Blender (app or `bpy` wheel) and a logged-in Codex CLI. If not, tell the user exactly what is missing and stop.
- `BW_HOME` points at the workspace (a folder with `runs/`). Default: current folder.

## Commands
- Rig: `bw rig <mesh.glb|fbx|obj|blend> --preset humanoid|quadruped [--lang en] [--no-judge]`
  Steps: analyze (no tokens) → fit (1 model call) → Rigify generate + auto weights (no tokens) → gates (no tokens) → render 3 views (no tokens) → judge (1 model call with 2 images). About 40k input tokens per rig.
- Motion: `bw motion --text "a person walks then waves"` (needs kimodo.cpp build, ~50 s per 60 frames on Apple Silicon) or `bw motion --bvh file.bvh`.
- `bw status`, `bw usage --days 7`.

## How to report
Read `runs/<id>/report.md` and say: gates PASS/FAIL with the exact failing checks, what the judge saw, the rig file path, and tokens used. If status is `needs_review`, list the failing gates first and propose one concrete fix (e.g. "raise weight_sum_max" is NOT a fix; "the mesh has disconnected hands, join them" is).

## Do not
- Do not publish, delete or overwrite the user's original mesh.
- Do not loop on judge calls: at most one re-run per user request.
- Do not bypass gates by editing config thresholds without telling the user.
