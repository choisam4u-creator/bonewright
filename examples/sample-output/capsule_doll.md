<!-- Made with `BW_NO_RENDER=1 python3 examples/rig_sample.py` (bpy 5.2.2 LTS, BW_BACKEND=mock, 2026-10-06).
     The input is a capsule doll built by make_test_mesh, so there is no licence question.
     tests/test_examples.py compares this table with a fresh rig — when the rig changes, regenerate with the same command. -->
# capsule_doll: `capsule_doll.glb` → rig result

- gates: **ok** · rig bones 410 (deform 73) · unweighted vertices 0
- no skin bones in the input file

## Deform bones in the exported GLB

- 73 bones · left 29 · right 29 · center 15

| part | count | names |
|---|---:|---|
| thigh | 4 | `DEF-thigh.L`, `DEF-thigh.L.001`, `DEF-thigh.R`, `DEF-thigh.R.001` |
| shin | 4 | `DEF-shin.L`, `DEF-shin.L.001`, `DEF-shin.R`, `DEF-shin.R.001` |
| foot | 2 | `DEF-foot.L`, `DEF-foot.R` |
| toe | 2 | `DEF-toe.L`, `DEF-toe.R` |
| pelvis | 2 | `DEF-pelvis.L`, `DEF-pelvis.R` |
| breast | 2 | `DEF-breast.L`, `DEF-breast.R` |
| shoulder | 2 | `DEF-shoulder.L`, `DEF-shoulder.R` |
| upper_arm | 4 | `DEF-upper_arm.L`, `DEF-upper_arm.L.001`, `DEF-upper_arm.R`, `DEF-upper_arm.R.001` |
| forearm | 4 | `DEF-forearm.L`, `DEF-forearm.L.001`, `DEF-forearm.R`, `DEF-forearm.R.001` |
| hand | 2 | `DEF-hand.L`, `DEF-hand.R` |
| f_index | 6 | `DEF-f_index.01.L`, `DEF-f_index.02.L`, `DEF-f_index.03.L`, `DEF-f_index.01.R`, `DEF-f_index.02.R`, `DEF-f_index.03.R` |
| palm | 8 | `DEF-palm.01.L`, `DEF-palm.02.L`, `DEF-palm.03.L`, `DEF-palm.04.L`, `DEF-palm.01.R`, `DEF-palm.02.R`, `DEF-palm.03.R`, `DEF-palm.04.R` |
| thumb | 6 | `DEF-thumb.01.L`, `DEF-thumb.02.L`, `DEF-thumb.03.L`, `DEF-thumb.01.R`, `DEF-thumb.02.R`, `DEF-thumb.03.R` |
| f_middle | 6 | `DEF-f_middle.01.L`, `DEF-f_middle.02.L`, `DEF-f_middle.03.L`, `DEF-f_middle.01.R`, `DEF-f_middle.02.R`, `DEF-f_middle.03.R` |
| f_ring | 6 | `DEF-f_ring.01.L`, `DEF-f_ring.02.L`, `DEF-f_ring.03.L`, `DEF-f_ring.01.R`, `DEF-f_ring.02.R`, `DEF-f_ring.03.R` |
| f_pinky | 6 | `DEF-f_pinky.01.L`, `DEF-f_pinky.02.L`, `DEF-f_pinky.03.L`, `DEF-f_pinky.01.R`, `DEF-f_pinky.02.R`, `DEF-f_pinky.03.R` |
| spine | 7 | `DEF-spine`, `DEF-spine.001`, `DEF-spine.002`, `DEF-spine.003`, `DEF-spine.004`, `DEF-spine.005`, `DEF-spine.006` |
