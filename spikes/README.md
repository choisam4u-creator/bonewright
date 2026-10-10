# spikes/

Early throwaway experiments from September 2026, kept because a few of their outputs are still in use.
**This is not part of bonewright.** Nothing here is installed by `pip install`, and the `bw` command never
imports it. The real Blender-side code lives in [`bonewright/bpy_scripts/`](../bonewright/bpy_scripts/).

| File | What it checked | Still used? |
|---|---|---|
| `rigify_headless.py` | Can Rigify be enabled and generate a human and a wolf rig in background mode, then export FBX? (answer: yes) | No — superseded by `bonewright/bpy_scripts/` |
| `render_rig2.py` | Can a headless render show bones? (Armatures are not drawn in final renders, so bones become thin cylinders; one arm is pushed out on purpose) | No |
| `rig_view2.png` | The picture `render_rig2.py` made (procedural cylinders and spheres, no outside asset) | No |
| `answer2.json` | A vision model's answer when shown `rig_view2.png` — it did notice the misplaced arm, which is how the visual judge started | No |
| `prompt.txt` | The text prompt given to the text-to-motion generator | Yes — documents where `walk_wave.bvh` came from |
| `bvh_check.py` | Imports a BVH into Blender and prints bone count, frame range and root travel | No |
| `motion_out/walk_wave.bvh` | A walk-and-wave clip made from `prompt.txt` (60 frames, 30 fps) | **Yes** — the retarget tests in `tests/test_mock.py` and `docs/media/walk-retarget.gif` use it. Do not delete or move it |

Where `walk_wave.bvh` came from and under which licence its model weights are: see
[`docs/media/ATTRIBUTION.md`](../docs/media/ATTRIBUTION.md) → "The motion".

The three `.py` files import `bpy`. Their licence is not settled yet (see the maintainer note in
`docs/test-reports/CLOUD-NOTES.md`); `scripts/check_license_boundary.py` only checks `bonewright/`.

To run one anyway (Blender 4.2+ or 5.x). Each prints one `RESULT {...}` line and writes its file next to the
last argument, so point that at a scratch folder:

```bash
d=$(mktemp -d); blender --background --python spikes/rigify_headless.py -- "$d/x"   # writes $d/rig_test.fbx
d=$(mktemp -d); cp spikes/motion_out/walk_wave.bvh "$d" && blender --background --python spikes/bvh_check.py -- "$d/walk_wave.bvh"
```

`spikes/motion_out/` is in `.gitignore` (generator output is large); `walk_wave.bvh` was added on purpose with
`git add -f`. A new file there will not show up in `git status`.
