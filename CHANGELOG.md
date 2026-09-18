# Changelog

All notable changes to this project. Numbers are measured against the original authors' rigs
(`bw bench`), reported as a mean joint error and as a percentage of the character's height.

## [Unreleased]

### Added
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
- Influences whose straight line from the vertex to the bone leaves the mesh are dropped. Automatic weights
  judge by distance alone, so on a hollow ribcage an arm bone reaches across the empty chest and takes the ribs.
  KayKit skeleton warrior: arm-into-torso leak 11 of 94 vertices → 0.

### Fixed
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
