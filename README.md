# bonewright

Rig and animate Blender characters with Codex. **Python drives the steps, `codex exec` judges, gates verify.**

Status: v0.1 (alpha). Humanoid and quadruped Rigify presets. Tested on macOS with Blender 5.2 LTS and Codex CLI 0.153.

```bash
pip install .            # installs `bw`
bw doctor                # Blender (app or bpy wheel), Codex login, kimodo.cpp (optional)
bw rig character.glb --preset humanoid
bw motion --text "a person walks forward, stops and waves"   # needs kimodo.cpp (Apple Silicon: Metal)
```

`bw rig` = analyze mesh (no tokens) → Codex proposes metarig bone targets (1 call) → Rigify generate + automatic weights → gates (unweighted vertices, weight sums, symmetry, bones outside the mesh box) → 3 test renders → Codex looks at 2 of them (1 call, ~18k input tokens each) → `runs/<id>/report.md`.

License: MIT (this CLI). Anything that runs inside Blender as an add-on must be GPL; v0.1 runs headless and ships no add-on. Model weights for kimodo.cpp keep their own licenses (SOMA/G1: NVIDIA Open Model License).
