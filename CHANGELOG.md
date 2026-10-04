# Changelog

All notable changes to this project. Numbers are measured against the original authors' rigs
(`bw bench`), reported as a mean joint error and as a percentage of the character's height.

## [Unreleased]

Proposed next version: **0.2.1** — fixes, documentation and examples only; no new command, and the only new flag is `bw --version`.
See `docs/RELEASING.md` for the release steps.

### Added
- `examples/rig_sample.py`: rig a small sample mesh (procedural capsule doll, the CC0 `adventurer`, or any GLB)
  and write a table of deform-bone count, left/right split and names. `--table x.glb` reads a GLB without Blender.
- Blender-dependent tests are marked with `@requires_blender` (`tests/_marks.py`). `BW_SKIP_BLENDER=1` skips them
  for a quick check; `BW_REQUIRE_BLENDER=1` turns a missing Blender into a failure (used by the CI `bpy` job).
- `docs/PRE-PUBLIC-AUDIT.md`: what to look at before the repository goes public (report only, nothing removed).
- Issue templates for install / `bw doctor` problems and feature requests; blank issues now point to the guide and
  SECURITY.md. `bw --version` prints the package version the install template asks for.

### Changed
- `bw --help` follows `BW_LANG` (or the locale): English by default, Korean for `ko`. Error messages and
  `bw doctor` stay Korean for now; the README says so.
- An unexpected error no longer ends in a bare one-line `BLOCKED:`. It names the exception type, points at the
  run's `logs/` folder and the issue templates, and `BW_DEBUG=1` prints the full traceback.
- README first screen rewritten to what it does / install / first run / example output; the long material moved
  to `docs/GUIDE.md`, with a Korean edition in `README.ko.md`.
- `scripts/fetch_bench_assets.py` downloads five more human and robot assets (coverage 57 → 62 of 66).

### Fixed
- **Input mistakes now stop before Blender starts, and say what to change.** A missing or unsupported mesh,
  a missing `--targets`/`--map`/`--bvh` file, a broken JSON file, or a run id with no rig used to surface as a
  Blender traceback or a bare "file not found". They now raise `Blocked` with a `→` line naming the fix
  (supported formats, `bw status`, the `bw rig ... --run-id` to run first). The usage-limit message pointed at a
  `bw resume` command that does not exist; it now says to rerun, or reuse `runs/<id>/targets.json` with
  `--targets`. `bw status <unknown id>` exits 2 with a hint instead of a traceback. Covered by `tests/test_errors.py`
  (no Blender needed).
- **Quadruped judge renders were cropped.** `render_views.py` sized the camera from the character's
  *height*, which is right for a person and wrong for anything longer than it is tall: the wolf
  (2.68 tall, 5.55 long — the tail counts) lost its head and its tail off both edges of the side view, and the model was
  asked to judge bone placement on a picture that did not contain the bones. The camera now sizes from
  the longest of the three bounding-box edges. Humanoids are unaffected — height is already their
  longest edge — so no existing number moves.
- `bw plugin-path` printed `site-packages/plugin`, a folder that does not exist, when bonewright was installed
  with pip: the plugin was never packaged. The wheel now carries it as `bonewright/_plugin/`, and the command
  prefers the repository's `plugin/` when run from a checkout. CI checks the installed path from outside the repo.
- The Codex plugin manifest (`plugin/.codex-plugin/plugin.json`) still said version 0.1.0 and "retargeting comes in
  v0.2". It now matches the package version; `tests/test_release.py` keeps the three version strings in step.
- `--pin` rejects malformed input (empty bone name, more than one `/`, NaN or infinite coordinates) before any
  work starts.
- Documentation audit (2026-09-20): eleven claims that did not match measurements were corrected; the wolf's
  tail is three bones, not one.

## [0.2.0] - 2026-09-20

Summary: humanoid and quadruped Rigify presets, rejection gate, `--from-skeleton`, BVH retargeting, `bw bench`.

### Added
- **Human-only metarig bones are dropped when the source skeleton has no counterpart.** Rigify's `breast.L/R`
  has nothing to map to on a frog, so it floats at human-chest proportions and takes shoulder flesh; the seam
  between it and the upper arm tore at 4.6x over 1.19% of the mesh. Removing it fixes that asset outright
  (4.55x/1.19% → **2.58x/0.0%**) and leaves six control assets untouched. The same idea applied to finger
  segments failed (see Fixed) — fingers are a chain, so their flesh piles onto a distant hand bone, while the
  breast pair hands its flesh to the chest bone right beside it. On a quadruped `pelvis.L/R` behaves the same
  way — Bull's worst seam was exactly `DEF-spine.001` / `DEF-pelvis.L` — and removing it improved or held every
  one of the ten animals (Bull 11.63x → **1.93x**, Cow 11.63 → 2.44, Shiba Inu 7.47 → 2.44, motion pass rate
  7/10 → **9/10**). On a human it is the opposite: those bones sit correctly on the hips and doing the same
  thing pushed cesium_man from 3.72x/0.9% to 5.38x/1.1%, so `pelvis` is only dropped under the quadruped preset.
- **Unweighted vertices are filled from their connected neighbours** instead of from the nearest bone. A
  nearest-bone guess makes one vertex follow a different bone than the flesh around it and the shell cracks;
  copying the weights of the closest vertex *along the mesh* is interpolation, not a guess. Orc: 12 stragglers
  on a weapon, `needs_review` → `ok`. A fill that spreads over 5% of the mesh still fails the gate.
- **`_voxgeo`** — voxel geodesic distance, used to drop influences that only reach a vertex by leaving the
  flesh. Filling the mesh with voxels closes the hairline gaps between the pieces of a segmented mannequin while
  leaving a skeleton's empty chest open, so the resolution itself separates "ignorable gap" from "real cavity"
  (see the note on the ray-based attempt below).
- **`--from-shape`** — builds a skeleton from the mesh's own medial axis when the file has no skeleton and the
  body is not human- or dog-shaped. Every asset the silhouette gate used to refuse now rigs: an insect, a seated
  character, a fox under the humanoid preset, three Khronos test shapes. Shape-rig bones carry role names
  (`thigh.L`, `forearm.R`, `chest`) when the read can classify them.
- **Generic chain rig** — when a source skeleton cannot be mapped onto a preset (a dragon has no legs, a blob has
  four bones), the metarig is copied bone-for-bone and every bone gets a control. 43 CC0 creatures: 40 clean,
  3 needing review, 0 refused — up from 14 rigged.
- **Inside read (`_medial.py`)** — voxel fill, distance transform and maximal-sphere packing find limb tips and
  the path back to the body, whatever the pose. Supplies the arm centreline, crotch and ankle that the
  silhouette could not read. `quat_pp_41j` went from refused to 31.34 cm (5.7% of height).
- Held props (a weapon, a trident) are detected by weight concentration on hand bones and excluded from every
  size and centre measurement, and bound rigidly to one bone.
- `scripts/check_license_boundary.py`, enforced in CI: the MIT core must never import `bpy`.
- `rig.cross_trim` (**off by default**) drops influences whose straight line from the vertex to the bone leaves
  the mesh. On a hollow ribcage an arm bone reaches across the empty chest and takes the ribs — KayKit skeleton
  warrior's arm-into-torso leak goes from 11 of 94 vertices to 0. On an ordinary layered game mesh it costs more
  than it gains (mannequiny retarget stretch 4.71x off, 7.88x on, with no leak either way), so it stays off.
- A regression test that retargets a **real** CC0 asset and measures mesh stretch. The procedural test mesh has a
  single shell and never showed the cost above; the real asset fails at 9.34x with the trim on.

### Fixed
- **A nearly-successful voxel-proxy bind was being thrown away over a hair's breadth.** On one asset automatic
  weighting left 3464 of 6994 vertices empty while the voxel proxy left 16 — but transferring those weights back
  to the original mesh left 406 (5.8%), just over the 5% cutoff, so the whole thing was discarded for envelope
  weighting, which hands a single vertex 0.25 of each foot. That cutoff predates the neighbour fill, which now
  interpolates leftovers instead of guessing, so it is 15%. The asset goes from 13.94x/0.89% to **3.37x/0.0%**,
  and of the 406 leftovers 356 bind as whole rigid pieces, 50 interpolate, and none are guessed.

- **Tried and reverted: dropping metarig finger segments the source skeleton never had.** A source rig that stops
  at two thumb joints leaves the metarig's third floating at human-hand proportions, where it grabs flesh (a bunny
  had `DEF-thumb.03.L` owning vertices at weight 1.00). Removing the untargeted tips helped that one asset
  (12.19x → 11.30x) and hurt several others badly: godot_player 1.87x/0.0% → **8.46x/3.17%**, quat_pp_41j
  2.09x → **11.85x**, rigged_figure 1.61x/0.0% → 3.72x/**6.51%**, and the KayKit mage dropped below the
  deform-bone minimum. Hand flesh spread across finger bones is worth more than the floating tip costs.
- **Motion is judged by depth *and* breadth.** The single worst edge ranks assets almost backwards: Bull stretches
  11.63x but on 0.22% of its edges, while frog stretches 4.55x on 1.19%. Results are now split into pass, a
  localised spike, and a real tear.

- **The arm-into-torso check is now calibrated against the author.** Running the same rule over the file's own
  weights shows how much of the "leak" is the body's shape rather than our error: on a chibi whose arms are fused
  to the body the author himself gives 39.2% of chest-midline vertices to arm bones, while on a hollow KayKit
  skeleton the author gives **0%**. The gate now allows what the author allowed and fails anything worse — the
  same trick already used for left/right symmetry. It changed no pass/fail in the benchmark.

- **Tried and reverted: reusing the author's painted weights.** Bone names differ between rigs but the positions
  came from the same skeleton, so each source bone was paired with the DEF bone nearest to it. The leak metric
  loved it (KayKit skeleton warrior 11 of 94 chest vertices → 0). Animating it told a different story: the same
  asset went from 5.78x to **11.25x** mesh stretch under a CMU walk, and cesium_man from 3.72x to **20.7x**.
  Plenty of rigs mark a joint with a **zero-length** bone, which collapses any position-based pairing — a left
  hand ended up weighted to a torso bone. The gates cannot see this; only animating can.

- **The arm-into-torso check could switch itself off.** It samples a narrow band down the middle of the chest
  and skips the verdict when fewer than 30 vertices land there — so a low-poly character could pass by having
  too few samples, and moving a bone could silently disable the check (godot_player went 17/31 → 21 samples →
  no verdict). The band now fills up to 30 samples from the vertices nearest the midline before giving up.
- **Shape-rig limb chains are cut at the neck of the limb**, the point where the mesh's thickness drops most
  steeply, rather than at a fixed fraction of the torso's thickness. The fixed fraction overshoots on bodies
  whose widest point is the belly. Shape-rig retarget stretch on mannequiny: 67.2x → **38.2x** (still unusable
  for motion — see ROADMAP — but the arm no longer starts in the middle of the chest).

- Left-right repair now fires whenever the source rig is symmetric, and averages the two sides instead of copying
  one onto the other.
- Source symmetry is measured about the source rig's own centre line, not about x=0, so a 2 cm armature offset no
  longer inflates the gate's tolerance and hide real errors.
- Benchmark left/right matching used bone names; on files the importer turns 180° it compared our left leg with
  the author's right. Fixed by comparing on coordinate sign — `robot_expressive` 183.15 → 48.39 cm. Historical
  "robot 135–277%" figures in older notes contain this artifact.

### Known limits
- Motion retargeting onto a `--from-shape` rig is not usable: max edge stretch 44x against under 6x on the preset
  path. The arm chain starts inside the chest, so automatic weights give chest vertices to the arm.
- `bpy_scripts/` is GPL-3.0-or-later; the rest is MIT.

[Unreleased]: https://github.com/choisam4u-creator/bonewright/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/choisam4u-creator/bonewright/releases/tag/v0.2.0
