<!-- 생성: `BW_NO_RENDER=1 python3 examples/rig_sample.py --preset quadruped` (bpy 5.2.2 LTS, BW_BACKEND=mock, 2026-10-07).
     입력은 make_test_mesh(kind=quadruped)가 절차적으로 만든 네 발 캡슐 개(키 0.92m)라 라이선스 문제가 없다.
     report.md 에는 "조각 사이 빈틈을 지나는 본 4"(뒷다리 DEF-shin) 경고가 같이 나온다 — 관문은 통과.
     사족 리그는 Rigify 늑대 메타리그라 앞발(f_*)·뒷발(r_*)에 발가락 본이 있다.
     tests/test_examples.py 가 이 표와 지금 리깅 결과를 대조한다 — 리그가 바뀌면 같은 명령으로 다시 만든다. -->
# capsule_dog: `capsule_dog.glb` → 리깅 결과

- 관문: **ok** · 리그 본 527(변형 110) · 가중치 없는 정점 0
- 입력 파일에 스킨 본 없음

## 내보낸 GLB 의 변형 본

- 본 110개 · 왼쪽 43 · 오른쪽 43 · 가운데 24

| 부위 | 개수 | 이름 |
|---|---:|---|
| spine | 12 | `DEF-spine`, `DEF-spine.001`, `DEF-spine.002`, `DEF-spine.003`, `DEF-spine.004`, `DEF-spine.005`, `DEF-spine.006`, `DEF-spine.007`, `DEF-spine.008`, `DEF-spine.009`, `DEF-spine.010`, `DEF-spine.011` |
| thigh | 4 | `DEF-thigh.L`, `DEF-thigh.L.001`, `DEF-thigh.R`, `DEF-thigh.R.001` |
| shin | 4 | `DEF-shin.L`, `DEF-shin.L.001`, `DEF-shin.R`, `DEF-shin.R.001` |
| foot | 4 | `DEF-foot.L`, `DEF-foot.L.001`, `DEF-foot.R`, `DEF-foot.R.001` |
| toe | 2 | `DEF-toe.L`, `DEF-toe.R` |
| r_index | 6 | `DEF-r_index.01.L`, `DEF-r_index.02.L`, `DEF-r_index.03.L`, `DEF-r_index.01.R`, `DEF-r_index.02.R`, `DEF-r_index.03.R` |
| r_palm | 8 | `DEF-r_palm.01.L`, `DEF-r_palm.02.L`, `DEF-r_palm.03.L`, `DEF-r_palm.04.L`, `DEF-r_palm.01.R`, `DEF-r_palm.02.R`, `DEF-r_palm.03.R`, `DEF-r_palm.04.R` |
| r_middle | 6 | `DEF-r_middle.01.L`, `DEF-r_middle.02.L`, `DEF-r_middle.03.L`, `DEF-r_middle.01.R`, `DEF-r_middle.02.R`, `DEF-r_middle.03.R` |
| r_ring | 6 | `DEF-r_ring.01.L`, `DEF-r_ring.02.L`, `DEF-r_ring.03.L`, `DEF-r_ring.01.R`, `DEF-r_ring.02.R`, `DEF-r_ring.03.R` |
| r_pinky | 6 | `DEF-r_pinky.01.L`, `DEF-r_pinky.02.L`, `DEF-r_pinky.03.L`, `DEF-r_pinky.01.R`, `DEF-r_pinky.02.R`, `DEF-r_pinky.03.R` |
| pelvis | 2 | `DEF-pelvis.L`, `DEF-pelvis.R` |
| breast | 2 | `DEF-breast.L`, `DEF-breast.R` |
| front_thigh | 4 | `DEF-front_thigh.L`, `DEF-front_thigh.L.001`, `DEF-front_thigh.R`, `DEF-front_thigh.R.001` |
| front_shin | 4 | `DEF-front_shin.L`, `DEF-front_shin.L.001`, `DEF-front_shin.R`, `DEF-front_shin.R.001` |
| front_foot | 4 | `DEF-front_foot.L`, `DEF-front_foot.L.001`, `DEF-front_foot.R`, `DEF-front_foot.R.001` |
| front_toe | 2 | `DEF-front_toe.L`, `DEF-front_toe.R` |
| f_index | 6 | `DEF-f_index.01.L`, `DEF-f_index.02.L`, `DEF-f_index.03.L`, `DEF-f_index.01.R`, `DEF-f_index.02.R`, `DEF-f_index.03.R` |
| f_palm | 8 | `DEF-f_palm.01.L`, `DEF-f_palm.02.L`, `DEF-f_palm.03.L`, `DEF-f_palm.04.L`, `DEF-f_palm.01.R`, `DEF-f_palm.02.R`, `DEF-f_palm.03.R`, `DEF-f_palm.04.R` |
| f_middle | 6 | `DEF-f_middle.01.L`, `DEF-f_middle.02.L`, `DEF-f_middle.03.L`, `DEF-f_middle.01.R`, `DEF-f_middle.02.R`, `DEF-f_middle.03.R` |
| f_ring | 6 | `DEF-f_ring.01.L`, `DEF-f_ring.02.L`, `DEF-f_ring.03.L`, `DEF-f_ring.01.R`, `DEF-f_ring.02.R`, `DEF-f_ring.03.R` |
| f_pinky | 6 | `DEF-f_pinky.01.L`, `DEF-f_pinky.02.L`, `DEF-f_pinky.03.L`, `DEF-f_pinky.01.R`, `DEF-f_pinky.02.R`, `DEF-f_pinky.03.R` |
| shoulder | 2 | `DEF-shoulder.L`, `DEF-shoulder.R` |
