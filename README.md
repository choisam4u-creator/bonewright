# bonewright

Rig and animate Blender characters with Codex. **Python drives the steps, `codex exec` judges, gates verify.**

Status: **v0.2 (alpha).** Humanoid and quadruped Rigify presets. Developed and tested on macOS with Blender 5.2 LTS
and Codex CLI 0.153. **Linux is untested. Windows is unsupported.**

## What it does well, and what it does not

`bw bench` strips a character's original skeleton, re-rigs it, and measures joint positions against what the original
author built. **That "answer" is one artist's rig, not anatomical truth** — read it as regression detection rather than
an absolute score. The numbers below come from the deterministic path (`BW_BACKEND=mock`, 0 tokens); the Codex path is
verified end to end over 8 real runs but is not benchmarked per asset.

| Input | Joint error (% of height) | Verdict |
|---|---|---|
| Human-proportioned T-pose, skinned, arms out | **1.6 – 7.4%** | usable (GDQuest mannequiny 1.6%, Quaternius Adventurer 3.3%) |
| Quadrupeds (`--preset quadruped`) | **13.5%** over 11 animals | experimental — a 1 m animal is off by ~13 cm |
| Robots, chibi, insects, non-T-pose, upper-body-only | 10 – 277% | **rejected before any model call** |

Faces are off by default. Motion retargeting (BVH → rig → GLB) exists and is measured below.

## Rejection gate

The pipeline assumes a human body. When that assumption broke, the result used to come out silently wrong — a robot
came back with a rig off by 277% of its height. The mesh is now checked **before** the model is called, so a bad input
costs **zero tokens** (a rig otherwise costs ~80k input tokens).

A mesh is rejected when: an arm or leg centreline is missing on either side · a joint (crotch / hip / knee / ankle) had
to fall back to a body ratio · the head is over 35% of height (chibi) · left-right asymmetry exceeds 3% of height ·
size is outside 0.3–20 m. A neck-only fallback is a warning, not a rejection.

Across the 17 benchmark assets this separates cleanly: **7 pass (1.6–7.4% error), 9 are rejected (10.1%+), with no
mistakes in either direction.** Override with `--force`.

## Install and run

```bash
pip install .            # installs `bw`
bw doctor                # Blender (app or bpy wheel), Codex login, kimodo.cpp (optional)
bw rig character.glb --preset humanoid
bw motion --text "a person walks forward, stops and waves"   # needs kimodo.cpp (Apple Silicon: Metal)
bw motion --bvh walk.bvh --rig <run-id> --export         # retarget a BVH onto a rig, export deform-only GLB (0 tokens)
bw demo <run-id>         # mp4/gif of the rig moving through IK controls (0 tokens)
bw export <run-id>       # game-ready GLB: deform bones only (73, not 410) + skin, re-imported and checked (0 tokens)
bw bench a.glb b.glb     # compare against the original skeletons (0 tokens)
```

Cost: one `bw rig` makes **2 model calls** — a fit call (~80k input tokens) and a visual judge call (2 images).
Measured runs landed at **$0.86 – $1.10** each. `bw usage` prints the ledger. A rejected mesh costs nothing, and
`--no-judge` skips the second call.

A-pose input rigs as well as T-pose (same asset, arms lowered 30–60°: mannequiny 2.96 cm T vs 2.5–2.8 cm A).
Downstream steps (animation, retargeting) usually expect a T-pose rest, so `--rest-pose t` swings the arms to
horizontal and bakes that as the rest pose before Rigify runs: an A-pose mannequiny normalised this way lands
2.62 cm from the original T-pose skeleton. Characters whose "T" already droops a few degrees are left alone
(threshold 8°).

```bash
bw rig character_apose.glb --rest-pose t     # rest pose becomes T (arms horizontal); default keeps the mesh's own pose
```

When a joint lands wrong, fix it by hand instead of paying for another run:

```bash
bw rig character.glb --pin "spine.004=0,0,1.42"            # pin a joint; pins beat every automatic correction
bw rig character.glb --targets runs/<id>/targets.json      # re-run with edited targets, 0 model calls, 0 tokens
bw rig character.glb --targets runs/<id>/targets.json --pin "shin.L=0.09,0,0.48"
```

## Motion retargeting

`bw motion --bvh file.bvh --rig <run-id> [--bvh-up z] [--export]` moves a BVH clip onto a rig made by `bw rig`
(the rig's preset is read from its run; `--preset` overrides). BVH joints are matched to Rigify controls by name (kimodo `LeftLeg/LeftShin`, Mixamo
`LeftUpLeg/LeftLeg`, CMU and Quaternius animal `BackLeg/FrontUpperLeg` conventions are covered by tests or runs).
Units and frame rate are taken from the file (CMU's 16.7-unit hip height becomes a 0.06 scale); zero-length joints
(CMU hands) take their direction from the first non-thumb child bone.

- **Arms, body:** each bone receives the source joint's world rotation delta. Limbs get a rest-pose correction (a
  common reference frame built from the bone direction and world forward), so an A-pose rig receives the same motion
  as a T-pose rig (0.2 cm difference) and twist comes along. Spine, neck and head take their reference from the
  clip's most typical frame instead of the bind pose — animal rigs are often bound with the head raised, and a pure
  bind-pose delta then makes the character stare at the ground.
- **Legs (`--legs auto`, default):** legs whose source chain ends at a foot tip are driven by Rigify's foot IK: the
  tip follows the BVH tip relative to the hip, scaled by the leg-length ratio, with the clip's lowest foot point taken
  as the floor. Legs whose source chain stops at the wrist (the Quaternius wolf's front legs — the paw is a detached
  IK bone) stay FK. `--legs fk` transfers rotations only.
- Root motion goes to `torso`, scaled by the hip-height ratio. `--bvh-up z` reads BVH files written by Blender itself.

Measured (`BW_BACKEND=mock`, 0 tokens):

| Clip → rig | Hands vs BVH (hip-relative) | Feet: lowest toe / floor · slide during BVH stance | Edge stretch |
|---|---|---|---|
| kimodo walk+wave → mannequiny T rest | 12.0 / 14.1 cm | −0.4 cm · 9.9 cm (BVH itself 8.6) | max 4.8× (a few 2–20 mm edges) |
| same → mannequiny **A-pose rest** | 10.6 / 11.9 cm | −0.9 cm · 9.7 cm | max 3.8× |
| same → Quaternius Adventurer | 13.8 / 13.1 cm | +4.1 cm (FK) | max 2.9× |
| Quaternius wolf Walk → our wolf rig | — | 0.05 cm · 0.7 cm (BVH 0.8) | max 2.6× |
| Quaternius wolf Gallop → our wolf rig | — | 0.0 cm · — | max 2.6× |
| CMU mocap 02_01 walk (120 fps, non-metric units, zero-length hand joints) → mannequiny | 14.9 / 17.9 cm | −0.6 cm · 76.6 cm over 344 frames (BVH 76.5) | max 3.6× |

Hand position error is bounded by proportion differences between the BVH skeleton and the character, not by the
transfer. Every run renders four frames next to the BVH skeleton drawn in red; the wolf walk was also compared frame
by frame against the original Quaternius animation from the side. Remaining gaps: the wolf's front legs are FK only
and its thigh is 1.4× the source's, so front paws swing wider than the original; the tail is not transferred.

`--export` writes `runs/<id>/animated.glb` with **deform bones only** (73 instead of 410 for a Rigify human), the
animation baked; the file is re-imported and hand/foot positions checked at the middle frame (0.0 cm difference).
`bw motion --text "..." --rig <run-id> --export` runs the whole chain text → kimodo.cpp → BVH → rig → GLB (60 frames
in ~50 s on an M4 Pro; kimodo.cpp must be built with `-DKIMODO_ENABLE_VULKAN=OFF` on macOS).

The edge-stretch check caught a real bug: vertices that Bone Heat leaves unweighted (152 hand-tip vertices on the
A-pose mannequiny) stayed at their rest position while the character walked away, turning into 2 m rods. Unweighted
vertices are now bound to the nearest deform bone, and the gate counts filled holes.

## What counts as "the character" in a file

Game files are rarely one clean mesh. When the file has an armature, bonewright takes the skinned meshes **plus parts
rigidly parented to bones** (a robot's arm and head, a low-poly character's separate head), and drops everything else:
furniture and walls in a scene export, the 42-vertex probe sphere many exporters leave at the origin, and anything
parented to a hand or finger bone (weapons, tools). Armour attached to arm bones is skinned but ignored when locating
joints, because it widens the silhouette. Files without an armature are used whole.

## How joints are found

Landmarks come from mesh evidence, not from human body ratios: the crotch is the top of the run of bands where the
silhouette splits left/right, the neck is the narrowest band under the head, the ankle is the top of the foot blob
(the part sticking out in Y), the knee is refined from the leg centreline. Height ratios remain only as last-resort
fallbacks and every use is reported in `landmarks.ratio_fallbacks`, with `landmarks.suspect` listing why a result may
be wrong. Inside/outside tests run against a voxel-remeshed volume copy, because game meshes are overlapping shells
with holes.

Quadrupeds use a separate path: the four foot positions are measured from the mesh (2.6–7.7% error against the
original rigs) and the Rigify wolf metarig's own leg proportions are stretched onto them. Knees and hocks are *not*
measured — they sit inside the body, where the surface cannot see them.

`bw rig` = analyze mesh (0 tokens) → **rejection gate (0 tokens)** → Codex proposes metarig bone targets (1 call) →
Rigify generate + automatic weights → gates (unweighted vertices, weight sums, symmetry, bones outside the mesh box) →
3 test renders → Codex looks at 2 of them (1 call, ~18k input tokens each) → `runs/<id>/report.md`.

## Reproducing the benchmark

Benchmark assets are not committed — their licences do not allow redistribution. Fetch them:

```bash
python3 scripts/fetch_bench_assets.py --out bench-assets
bw bench bench-assets/quadruped/*.gltf --preset quadruped
bw bench bench-assets/samples/*.glb --skin     # also compare skin weights against the original author's
```

`--skin` reports two numbers per asset: how often our dominant bone matches the original's by name (weak — bone
conventions differ), and the distance between the "influence centres" of the two weight sets, which is name-free.
Current baseline: mannequiny 4.1 cm (2.3% of height), typical game characters 10–12 cm (5–8%).

Mixamo/Adobe assets are deliberately excluded: the Adobe terms forbid using their content to test AI systems. Epic's
own Fab content (Paragon, Game Animation Sample) is excluded too — it is tagged NoAI and ships in Unreal-only format.

## License

MIT (this CLI). Anything that runs inside Blender as an add-on must be GPL; bonewright runs Blender headless and ships
no add-on. Rigify (GPL) is used through Blender, not vendored. Model weights for kimodo.cpp keep their own licenses
(SOMA/G1: NVIDIA Open Model License).
