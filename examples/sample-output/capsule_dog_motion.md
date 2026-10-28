<!-- Made with `BW_NO_RENDER=1 python3 examples/rig_sample.py --preset quadruped --motion` (bpy 5.2.2 LTS, BW_BACKEND=mock, 2026-10-17).
     The BVH is a 24-frame four-legged trot written by rig_sample.dog_walk_bvh (committed as examples/dog_walk.bvh), so
     there is no licence question. Error numbers vary slightly between machines and are left out (on this machine: mean
     bone direction error 8.52°, feet on the floor like the BVH). tests/test_examples.py compares the mapped-joint table
     and frame count with a fresh run. -->
# capsule_dog: procedural BVH (four-legged walk) → retarget result

- BVH joints 20 · frames 24 · mapped 20 · unmapped BVH joints 0

## Mapped joints

| BVH joint | rig control |
|---|---|
| `Chest` | `chest` |
| `Head` | `head` |
| `Hips` | `torso` |
| `LeftFoot` | `foot_fk.L` |
| `LeftLowerArm` | `front_shin_fk.L` |
| `LeftLowerLeg` | `shin_fk.L` |
| `LeftUpperArm` | `front_thigh_fk.L` |
| `LeftUpperLeg` | `thigh_fk.L` |
| `LeftWrist` | `front_foot_fk.L` |
| `Neck` | `neck` |
| `RightFoot` | `foot_fk.R` |
| `RightLowerArm` | `front_shin_fk.R` |
| `RightLowerLeg` | `shin_fk.R` |
| `RightUpperArm` | `front_thigh_fk.R` |
| `RightUpperLeg` | `thigh_fk.R` |
| `RightWrist` | `front_foot_fk.R` |
| `Tail1` | `spine.003` |
| `Tail2` | `spine.002` |
| `Tail3` | `spine.001` |
| `Tail4` | `spine` |

## report.md excerpt

- source: bvh: examples/out/dog_walk.bvh
- armature: dog_walk · bones 20 · frames [1, 24] · fps 24 · root move 0.767 m
- retarget → `capsule_dog`: mapped 20 bones, unmapped []
- legs: auto · IK ['foot_ik.L', 'front_foot_ik.L', 'foot_ik.R', 'front_foot_ik.R'] · FK(no foot joint in source) []
