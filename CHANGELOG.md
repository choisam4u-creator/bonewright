# Changelog

All notable changes to this project. Numbers are measured against the original authors' rigs
(`bw bench`), reported as a mean joint error and as a percentage of the character's height.

## [Unreleased]

### Added
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

## [0.2.0]
- Humanoid and quadruped Rigify presets, rejection gate, `--from-skeleton`, BVH retargeting, `bw bench`.
