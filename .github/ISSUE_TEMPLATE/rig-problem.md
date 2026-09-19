---
name: A rig came out wrong
about: Bones in the wrong place, weights leaking, a mesh that tears when animated
labels: rig
---

**The model.** A link to it, or which benchmark asset it is. Without a file nobody can reproduce this — if the model
cannot be shared, say so and attach the numbers below instead.

**The command**, exactly as run (including `--preset`, `--from-skeleton` / `--from-shape`, `BW_BACKEND`).

**What the run said.** Paste `runs/<id>/report.md` — it carries the gate verdicts, the weighting method that was
used, and the joint numbers. `runs/<id>/rig_stats.json` has the rest.

**What you expected instead**, and a render or screenshot if the problem is visual.

**If it only goes wrong when animated**, please include the retarget numbers (`runs/<id>/retarget.json` →
`stretch`), because gates only look at a character standing still and will happily pass a rig that tears.
