<!-- 생성: `BW_NO_RENDER=1 python3 examples/rig_sample.py --motion` (bpy 5.2.2 LTS, BW_BACKEND=mock, 2026-10-09).
     BVH 는 rig_sample.wave_bvh 가 절차적으로 쓴 손 흔들기 24프레임이라 라이선스 문제가 없다. 오차 숫자는 기계마다
     조금씩 달라 싣지 않는다. tests/test_examples.py 가 옮긴 본 표·프레임 수를 지금 결과와 대조한다. -->
# capsule_doll: 절차 생성 BVH(손 흔들기) → 리타겟 결과

- BVH 관절 19개 · 프레임 24 · 옮긴 본 18개 · 못 옮긴 BVH 본 1개

## 옮긴 본

| BVH 관절 | 리그 컨트롤 |
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

## report.md 발췌

- source: bvh: examples/out/wave.bvh
- armature: wave · bones 19 · frames [1, 24] · fps 24 · root move 0.005 m
- retarget → `capsule_doll`: mapped 18 bones, unmapped ['Spine']
- legs: auto · IK ['foot_ik.L', 'foot_ik.R'] · FK(no foot joint in source) []
