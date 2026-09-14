# bonewright

Rig and animate Blender characters with Codex. **Python drives the steps, `codex exec` judges, gates verify.**

Status: v0.2 (alpha). Humanoid and quadruped Rigify presets. Tested on macOS with Blender 5.2 LTS and Codex CLI 0.153,
on procedural test meshes and on CC0 game characters (Quaternius, T-pose, skinned, with fingers and props).

```bash
pip install .            # installs `bw`
bw doctor                # Blender (app or bpy wheel), Codex login, kimodo.cpp (optional)
bw rig character.glb --preset humanoid
bw motion --text "a person walks forward, stops and waves"   # needs kimodo.cpp (Apple Silicon: Metal)
bw demo <run-id>         # mp4/gif of the rig moving through IK controls (no tokens)
```

When a joint lands wrong, fix it by hand instead of paying for another run:

```bash
bw rig character.glb --pin "spine.004=0,0,1.42"            # pin a joint; pins beat every automatic correction
bw rig character.glb --targets runs/<id>/targets.json      # re-run with edited targets, 0 model calls, 0 tokens
bw rig character.glb --targets runs/<id>/targets.json --pin "shin.L=0.09,0,0.48"
```

Landmarks come from mesh evidence, not from human body ratios: the crotch is the top of the run of bands where the
silhouette splits left/right, the neck is the narrowest band under the head, the ankle is the top of the foot blob
(the part sticking out in Y), the knee is refined from the leg centreline. Height ratios remain only as last-resort
fallbacks and every use is reported in `landmarks.ratio_fallbacks`, with `landmarks.suspect` listing why a result may
be wrong (missing arm/leg centreline, neck not found, chibi proportions). Inside/outside tests run against a
voxel-remeshed volume copy, because game meshes are overlapping shells with holes.

`bw rig` = analyze mesh (no tokens) → Codex proposes metarig bone targets (1 call) → Rigify generate + automatic weights → gates (unweighted vertices, weight sums, symmetry, bones outside the mesh box) → 3 test renders → Codex looks at 2 of them (1 call, ~18k input tokens each) → `runs/<id>/report.md`.

License: MIT (this CLI). Anything that runs inside Blender as an add-on must be GPL; v0.1 runs headless and ships no add-on. Model weights for kimodo.cpp keep their own licenses (SOMA/G1: NVIDIA Open Model License).
