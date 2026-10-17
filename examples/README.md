# Examples

[한국어](README.ko.md)

`rig_sample.py` — feed in a small mesh and reproduce the rig (bone count and name table). Zero model calls
(`BW_BACKEND=mock`), zero tokens.

```bash
python3 examples/rig_sample.py                 # build a procedural capsule doll and rig it (no asset file)
python3 examples/rig_sample.py --preset quadruped   # build a procedural four-legged capsule dog and rig it as a quadruped
python3 examples/rig_sample.py adventurer      # the CC0 character in tests/assets (1.9 MB, Quaternius)
python3 examples/rig_sample.py --table adventurer   # just the skin bone table inside a GLB, no rigging (no Blender needed)
python3 examples/rig_sample.py --motion        # rig the capsule doll, then retarget a procedural BVH (24-frame hand wave)
python3 examples/rig_sample.py --preset quadruped --motion   # rig the capsule dog, then retarget a procedural four-legged walk
```

Rigging needs Blender 5.2 LTS or `pip install bpy==5.2.2` (Python 3.13). Results stay in `examples/out/` (ignored by
git) and the table is written to `examples/out/<name>.md`. The table is read in pure Python from the deform bones of the
exported `rigged.glb`. Result documents are always in English, whatever `BW_LANG` says, so they match the samples
below; `--help` and error messages follow `BW_LANG`.

See what a result looks like first in [sample-output/capsule_doll.md](sample-output/capsule_doll.md) (no arguments,
73 deform bones). For four legs, [sample-output/capsule_dog.md](sample-output/capsule_dog.md) (`--preset quadruped`,
110 deform bones — Rigify's wolf metarig, so the front and hind paws have toe bones). Motion retargeting
(`bw motion --bvh`) is in [sample-output/capsule_doll_motion.md](sample-output/capsule_doll_motion.md) (`--motion`,
18 of 19 BVH joints mapped — `Spine` is the mid spine and is not mapped on its own; see
[Motion retargeting](../docs/GUIDE.md#motion-retargeting)). `tests/test_examples.py` compares all three with a fresh run.
The same wave is committed as [`wave.bvh`](wave.bvh), so a rig of your own can take it as is:
`bw motion --bvh examples/wave.bvh --rig <run-id>` (`bw rig` prints this on its `next:` line with the id filled in).
For a four-legged rig there is [`dog_walk.bvh`](dog_walk.bvh), a one-second trot made by `rig_sample.dog_walk_bvh`
(its result on the capsule dog: [sample-output/capsule_dog_motion.md](sample-output/capsule_dog_motion.md), all 20 joints mapped):
`bw motion --bvh examples/dog_walk.bvh --rig <run-id>` (a quadruped rig's `next:` line gives this one).

## Heavy assets

Benchmark characters and animals (tens of MB, some under licences that forbid redistribution) are not in the
repository. Download them from where they are published:

```bash
python3 scripts/fetch_bench_assets.py --help
python3 examples/rig_sample.py <downloaded file>.glb [--preset quadruped]
```

## Input example: `--table adventurer` (skin bones already in the source file)

Rigging throws this source skeleton away and builds a new Rigify rig (`--from-skeleton` uses these joint positions
instead).

- 62 bones · left 27 · right 27 · center 8

| part | count | names |
|---|---:|---|
| Root | 1 | `Root` |
| Body | 1 | `Body` |
| Hips | 1 | `Hips` |
| Abdomen | 1 | `Abdomen` |
| Torso | 1 | `Torso` |
| Chest | 1 | `Chest` |
| Neck | 1 | `Neck` |
| Head | 1 | `Head` |
| Shoulder | 2 | `Shoulder.L`, `Shoulder.R` |
| UpperArm | 2 | `UpperArm.L`, `UpperArm.R` |
| LowerArm | 2 | `LowerArm.L`, `LowerArm.R` |
| Wrist | 2 | `Wrist.L`, `Wrist.R` |
| Index | 8 | `Index1.L`, `Index2.L`, `Index3.L`, `Index4.L`, `Index1.R`, `Index2.R`, `Index3.R`, `Index4.R` |
| Middle | 8 | `Middle1.L`, `Middle2.L`, `Middle3.L`, `Middle4.L`, `Middle1.R`, `Middle2.R`, `Middle3.R`, `Middle4.R` |
| Ring | 8 | `Ring1.L`, `Ring2.L`, `Ring3.L`, `Ring4.L`, `Ring1.R`, `Ring2.R`, `Ring3.R`, `Ring4.R` |
| Pinky | 8 | `Pinky1.L`, `Pinky2.L`, `Pinky3.L`, `Pinky4.L`, `Pinky1.R`, `Pinky2.R`, `Pinky3.R`, `Pinky4.R` |
| Thumb | 6 | `Thumb1.L`, `Thumb2.L`, `Thumb3.L`, `Thumb1.R`, `Thumb2.R`, `Thumb3.R` |
| UpperLeg | 2 | `UpperLeg.L`, `UpperLeg.R` |
| LowerLeg | 2 | `LowerLeg.L`, `LowerLeg.R` |
| Foot | 2 | `Foot.L`, `Foot.R` |
| PT | 2 | `PT.L`, `PT.R` |
