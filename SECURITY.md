# Security

## Reporting

Open a **private** security advisory through GitHub's *Security → Report a vulnerability* tab. Please do not open a
public issue for anything exploitable.

## What this project does on your machine

Being clear about this matters more than a disclosure address, because the tool takes untrusted input (3D model
files) and runs a large binary (Blender) over it.

- **It runs Blender as a child process** and hands it a script plus a JSON file of parameters. It does not install an
  add-on, and it does not evaluate anything from the model file as code.
- **Model files are parsed by Blender's own importers.** A malicious `.glb`/`.fbx` is therefore a Blender problem,
  not a bonewright one — keep Blender updated, and treat models from strangers the way you would any other binary.
- **The Codex path sends data to a model.** `bw rig` without `BW_BACKEND=mock` sends mesh measurements (bounding
  boxes, silhouette bands, bone names) to `codex exec`. It does **not** send the mesh itself. Set `BW_BACKEND=mock`
  to keep everything local; every step except `fit` and `judge` is deterministic and never calls out.
- **It writes only under `BW_HOME`** (runs, renders, logs) and the output paths you pass.
- **No telemetry**, no network access outside the Codex call above and `scripts/fetch_bench_assets.py`, which
  downloads benchmark models from their original hosts when you ask it to.

## Supported versions

This is a v0.1 research project. Fixes land on `main`; there are no maintained release branches.
