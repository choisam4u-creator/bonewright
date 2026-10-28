<!-- Made with `BW_NO_RENDER=1 python3 examples/rig_sample.py --motion` (bpy 5.2.2 LTS, BW_BACKEND=mock, 2026-10-09).
     The BVH is a 24-frame hand wave written by rig_sample.wave_bvh, so there is no licence question. Error numbers vary
     slightly between machines and are left out. tests/test_examples.py compares the mapped-joint table and frame count
     with a fresh run. `Spine` is not mapped on purpose: the mid spine is carried by `chest` (see docs/GUIDE.md). -->
# capsule_doll: procedural BVH (hand wave) → retarget result

- BVH joints 19 · frames 24 · mapped 18 · unmapped BVH joints 1

## Mapped joints

| BVH joint | rig control |
|---|---|
| `Chest` | `chest` |
| `Head` | `head` |
| `Hips` | `torso` |
| `LeftArm` | `upper_arm_fk.L` |
| `LeftFoot` | `foot_fk.L` |
| `LeftForeArm` | `forearm_fk.L` |
| `LeftHand` | `hand_fk.L` |
| `LeftLeg` | `shin_fk.L` |
| `LeftShoulder` | `shoulder.L` |
| `LeftUpLeg` | `thigh_fk.L` |
| `Neck` | `neck` |
| `RightArm` | `upper_arm_fk.R` |
| `RightFoot` | `foot_fk.R` |
| `RightForeArm` | `forearm_fk.R` |
| `RightHand` | `hand_fk.R` |
| `RightLeg` | `shin_fk.R` |
| `RightShoulder` | `shoulder.R` |
| `RightUpLeg` | `thigh_fk.R` |

## report.md excerpt

- source: bvh: examples/out/wave.bvh
- armature: wave · bones 19 · frames [1, 24] · fps 24 · root move 0.005 m
- retarget → `capsule_doll`: mapped 18 bones, unmapped ['Spine']
- legs: auto · IK ['foot_ik.L', 'foot_ik.R'] · FK(no foot joint in source) []
