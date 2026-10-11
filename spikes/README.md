# spikes/

Early throwaway experiments from September 2026, kept because a few of their outputs are still in use.
**This is not part of bonewright.** Nothing here is installed by `pip install`, and the `bw` command never
imports it. The real Blender-side code lives in [`bonewright/bpy_scripts/`](../bonewright/bpy_scripts/).

| File | What it is | Still used? |
|---|---|---|
| `rig_view2.png` | A headless render of a test rig (procedural cylinders and spheres, no outside asset; one arm pushed out on purpose) | No |
| `answer2.json` | A vision model's answer when shown `rig_view2.png` — it did notice the misplaced arm, which is how the visual judge started | No |
| `prompt.txt` | The text prompt given to the text-to-motion generator | Yes — documents where `walk_wave.bvh` came from |
| `motion_out/walk_wave.bvh` | A walk-and-wave clip made from `prompt.txt` (60 frames, 30 fps) | **Yes** — the retarget tests in `tests/test_mock.py` and `docs/media/walk-retarget.gif` use it. Do not delete or move it |

Where `walk_wave.bvh` came from and under which licence its model weights are: see
[`docs/media/ATTRIBUTION.md`](../docs/media/ATTRIBUTION.md) → "The motion".

The three experiment scripts (`rigify_headless.py`, `render_rig2.py`, `bvh_check.py`) were deleted on 2026-10-11:
they imported `bpy`, which would have made them GPL inside a folder the licence lists as MIT, and nothing used them.
They remain in the git history. `scripts/check_license_boundary.py` now checks every `.py` outside
`bonewright/bpy_scripts/`, so a new one would be caught.

`spikes/motion_out/` is in `.gitignore` (generator output is large); `walk_wave.bvh` was added on purpose with
`git add -f`. A new file there will not show up in `git status`.
