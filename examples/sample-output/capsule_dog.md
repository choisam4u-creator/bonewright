<!-- Made with `BW_NO_RENDER=1 python3 examples/rig_sample.py --preset quadruped` (bpy 5.2.2 LTS, BW_BACKEND=mock, 2026-10-07).
     The input is a four-legged capsule dog (0.92 m tall) built by make_test_mesh(kind=quadruped), so there is no licence question.
     report.md also warns about "4 bones crossing a gap between parts" (hind-leg DEF-shin) — the gates still pass.
     The quadruped rig is Rigify's wolf metarig, so the front (f_*) and hind (r_*) paws have toe bones.
     tests/test_examples.py compares this table with a fresh rig — when the rig changes, regenerate with the same command. -->
# capsule_dog: `capsule_dog.glb` → rig result

- gates: **ok** · rig bones 527 (deform 110) · unweighted vertices 0
- no skin bones in the input file

## Deform bones in the exported GLB

- 110 bones · left 43 · right 43 · center 24

| part | count | names |
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
