# 예제

[English](README.md)

`rig_sample.py` — 작은 메시를 넣고 리깅 결과(본 개수·이름 표)를 재현한다. 모델 호출 0회(`BW_BACKEND=mock`), 토큰 0.

```bash
python3 examples/rig_sample.py                 # 절차적 캡슐 인형을 만들어 리깅 (자산 파일 없음)
python3 examples/rig_sample.py --preset quadruped   # 절차적 네 발 캡슐 개를 만들어 사족 리깅 (자산 파일 없음)
python3 examples/rig_sample.py adventurer      # tests/assets 의 CC0 캐릭터(1.9MB, Quaternius)
python3 examples/rig_sample.py --table adventurer   # 리깅 없이 GLB 안의 스킨 본 표만 (블렌더 불필요)
python3 examples/rig_sample.py --motion        # 캡슐 인형 리깅 뒤 절차 생성 BVH(손 흔들기 24프레임)를 리타겟
python3 examples/rig_sample.py --preset quadruped --motion   # 캡슐 개 리깅 뒤 절차 생성 네 발 걷기(24프레임)를 리타겟
```

리깅에는 Blender 5.2 LTS 또는 `pip install bpy==5.2.2`(파이썬 3.13)가 필요하다. 결과는 `examples/out/`(git 제외)에
남고, 표는 `examples/out/<이름>.md` 로 쓴다(결과 문서는 화면 언어와 상관없이 영어 — 실어 둔 예시와 늘 같게). 표는 내보낸 `rigged.glb` 의 변형 본을 순수 파이썬으로 읽어 만든다.

결과가 어떻게 생겼는지는 [sample-output/capsule_doll.md](sample-output/capsule_doll.md)(인자 없이 돌린 결과, 변형 본 73개)에서
먼저 볼 수 있다. 네 발 짐승은 [sample-output/capsule_dog.md](sample-output/capsule_dog.md)(`--preset quadruped`, 변형 본 110개 —
Rigify 늑대 메타리그라 앞발·뒷발 발가락 본까지 있다). 동작 리타겟(`bw motion --bvh`)은
[sample-output/capsule_doll_motion.md](sample-output/capsule_doll_motion.md)(`--motion`, BVH 관절 19개 중 18개를 옮김 —
`Spine` 은 척추 중간이라 따로 옮기지 않는다 — [Motion retargeting](../docs/GUIDE.md#motion-retargeting) 의 관절 표). `tests/test_examples.py` 가 세 예시와 지금 결과를 대조한다.
같은 손 흔들기를 [`wave.bvh`](wave.bvh) 로 실어 두었다 — 내 리그에도 그대로 넣을 수 있다:
`bw motion --bvh examples/wave.bvh --rig <run-id>`(`bw rig` 끝의 `next:` 줄이 id 를 채워 보여 준다).
네 발 리그에는 [`dog_walk.bvh`](dog_walk.bvh)(`rig_sample.dog_walk_bvh` 가 만든 1초 속보 — 캡슐 개 결과는
[sample-output/capsule_dog_motion.md](sample-output/capsule_dog_motion.md), 관절 20개를 다 옮김)를 쓴다:
`bw motion --bvh examples/dog_walk.bvh --rig <run-id>`(사족 리그의 `next:` 줄이 이것을 준다).

## 무거운 자산

벤치마크용 캐릭터·동물(수십 MB, 라이선스가 재배포를 막는 것 포함)은 저장소에 넣지 않는다. 원배포처에서 받는다:

```bash
python3 scripts/fetch_bench_assets.py --help
python3 examples/rig_sample.py <받은 파일>.glb [--preset quadruped]
```

## 입력 예: `--table adventurer` (원본 파일에 든 스킨 본)

리깅할 때 이 원본 뼈대는 버리고 Rigify 리그를 새로 만든다(`--from-skeleton` 을 주면 이 관절 위치를 쓴다).

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
