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
| Quadrupeds (`--preset quadruped`) | **5.6%** over 11 animals (wolf 3.2%, horse 3.5%, worst cow 7.4%) | usable for dogs/hoofed animals |
| Robots, stylised, animals **that ship with a skeleton** | joints taken from the file | `--from-skeleton`, 0 tokens, no silhouette guess |
| The same shapes with **no** skeleton | 10 – 277% | **rejected before any model call**, with an editable `targets_draft.json` |

Faces are off by default. Motion retargeting (BVH → rig → GLB) exists and is measured below.

## Rejection gate

The pipeline assumes a human body. When that assumption broke, the result used to come out silently wrong — a robot
came back with a rig off by 277% of its height. The mesh is now checked **before** the model is called, so a bad input
costs **zero tokens** (a rig otherwise costs ~80k input tokens).

A mesh is rejected when: an arm or leg centreline is missing on either side · a joint (crotch / hip / knee / ankle) had
to fall back to a body ratio · the head is over 35% of height (chibi) · left-right asymmetry exceeds 3% of height ·
size is outside 0.3–20 m. A neck-only fallback is a warning, not a rejection.

A rejection is not a dead end. The run directory keeps `targets_draft.json` — the metarig scaled to this mesh — so
you can drag the joints where they belong and re-run with `--targets`, still at zero tokens. If the file has a
skeleton the message says so and points at `--from-skeleton` first.

Across the benchmark assets this separates **7 pass (1.6–7.4% error) from 9 rejected (10.1%+)**, re-verified after
every change to the importer and the fitter. There is now one honest miss: once the 90° turn described below was
corrected, `quat_pp_41j` dropped from 89 cm to 35 cm (6.3% of height) and would have been usable, yet it is still
rejected because its crotch and ankle came from body ratios. The gate keeps the safer answer — and that file ships
with a skeleton, so `--from-skeleton` rigs it anyway. Override with `--force`.
What gets rejected, and why, is worth knowing: two robots, an insect, a quadruped fed to the humanoid preset, a
character sitting in a furnished room, a 6 cm test cube, and three Khronos test rigs that have no limbs to find.

## Already rigged? Use its own skeleton

The rejection gate above turns away anything the silhouette cannot read — robots, stylised characters, animals in a
pose. Most of those files are not unrigged: the author already placed the joints. `--from-skeleton` reads that
skeleton and maps it onto the Rigify metarig, so you get the **controls** (IK/FK, motion retargeting, deform-only
export) without guessing at anatomy, and without a model call.

```bash
bw rig robot.glb --from-skeleton              # 0 tokens, silhouette gate skipped
bw rig wolf.gltf --preset quadruped --from-skeleton
```

Name conventions are the same dictionary the benchmark uses (Mixamo, Biped, VRM, Quaternius, Godot). Verified on
`.glb`, `.gltf` and `.fbx` — the same character exported as FBX rigs to the same result and passes the same gates. Beyond straight
name matching it handles what real files actually do wrong:

- **Sides come from coordinates, not names.** Importing flips many files 180°, which puts the author's `Left` bone on
  our −X. Trusting the name crosses the arms.
- **Chain ends missing.** Some rigs stop at the elbow and let one bone run to the foot (Quaternius animals), or have
  no wrist at all (three.js RobotExpressive stops at `Palm`). The previous bone's *tail* is that joint.
- **Curved chains.** The back and tail of an animal are not straight lines, so the spine is resampled along the source
  chain's own path rather than interpolated end to end. Rigify also requires the tail chain to start exactly where the
  pelvis does; otherwise generation fails outright with `Cannot connect chain - disjoint`.
- **Half-rigged files.** If only one side exists it is mirrored about the skeleton's own midline — not about x = 0,
  which is wrong when the file bundles a chair or a prop and shifts the mesh centre.
- **A missing limb is refused.** If both legs (or both arms) are absent there is nothing to infer from, and the run
  stops at 0 tokens rather than leaving those bones at metarig defaults, poking through the mesh.

Run over every benchmark asset (25 files, 0 tokens):

| Preset | Gates pass | Needs review | Refused at 0 tokens |
|---|---|---|---|
| Quadruped (10 animals) | **8** — wolf, horse, cow, bull, deer, donkey, husky, stag | 2 — alpaca, shiba inu (one bone of 110 outside) | 0 |
| Humanoid (15 files) | **8** | 2 — robot, chibi (arm weight reaching the chest centre) | 5 — insect, upper-body-only, two limbless test rigs, an animal fed to the humanoid preset |

Cow and bull are worth singling out: they are the two worst assets for the silhouette path (7.4%), because a thick
body breaks the hip-over-back ratio. Reading their own skeleton sidesteps the ratio entirely.

A model built from separate parts gets one more thing: when automatic weights leave a **whole** disconnected island
empty, that island is bound to a single nearest bone rather than filled vertex by vertex. That is what a rigid part
wants — the robot's 40 stray vertices and the chibi's 130 (a head modelled as its own mesh) stop counting as holes,
because they are not holes. An island that is only *partly* empty is still a hole and still counted.

`needs_review` here is usually the asset, not the rig. The robot's arms and legs are floating boxes with real gaps, so
some bones legitimately cross empty space; those are now counted separately from bones that stick out of the body,
because a bone bridging a gap still skins correctly while a bone with a loose end does not.

## Install and run

```bash
pip install .            # installs `bw`
bw doctor                # Blender (app or bpy wheel), Codex login, kimodo.cpp (optional)
bw rig character.glb --preset humanoid
bw rig already_rigged.glb --from-skeleton   # use the file's own skeleton, no model call (0 tokens)
bw motion --text "a person walks forward, stops and waves"   # needs kimodo.cpp (Apple Silicon: Metal)
bw motion --bvh walk.bvh --rig <run-id> --export         # retarget a BVH onto a rig, export deform-only GLB (0 tokens)
bw demo <run-id>         # mp4/gif of the rig moving through IK controls (0 tokens)
bw export <run-id>       # game-ready GLB: deform bones only (73, not 410) + skin, re-imported and checked (0 tokens)
bw bench a.glb b.glb     # compare against the original skeletons (0 tokens)
```

Cost: one `bw rig` makes **2 model calls** — a fit call (~80k input tokens) and a visual judge call (2 images).
Measured runs landed at **$0.86 – $1.10** each. `bw usage` prints the ledger. A rejected mesh costs nothing, and
`--no-judge` skips the second call.

A-pose input rigs as well as T-pose. `--rest-pose t` bakes a T-pose rest, which downstream animation usually expects.
Measured on one asset posed at several arm angles, against its own original T-pose skeleton:

| Arms lowered | Joint error | How it is handled |
|---|---|---|
| 30° / 45° | 2.74 / 2.62 cm (1.5%) | arms swung after fitting, using the fitted metarig |
| 60° | 3.19 cm (1.8%) | mesh straightened **before** analysis, then re-measured |
| 75° | 6.12 cm (3.4%) | same (was 10.19 cm when analysed in the A-pose) |
| 90° (arms flat against the body) | — | **rejected**: no arm centreline can be found, so nothing can be straightened |

Below 50° the arms are swung after fitting; above it the mesh is straightened first, because an arm lying against the
torso makes joint detection unreliable. Characters whose "T" already droops a few degrees are left alone (8°).

```bash
bw rig character_apose.glb --rest-pose t     # rest pose becomes T (arms horizontal); default keeps the mesh's own pose
```

When a joint lands wrong, fix it by hand instead of paying for another run:

```bash
bw rig character.glb --pin "spine.004=0,0,1.42"            # pin a joint; pins beat every automatic correction
bw rig character.glb --targets runs/<id>/targets.json      # re-run with edited targets, 0 model calls, 0 tokens
bw rig character.glb --targets runs/<id>/targets.json --pin "shin.L=0.09,0,0.48"
```

Weights get one cleanup pass before the 4-influence trim: a bone more than 2.5× farther from a vertex than that
vertex's nearest deform bone is dropped from it. Automatic weights hand arm bones a share of chest-centre vertices on
bodies whose shoulders sit close in; a natural blend at an elbow or shoulder keeps both bones because their distances
are comparable. Measured effect on skinning agreement with the original rigs: mannequiny 0.600 → 0.605, cesium_man
side agreement 0.997 → 0.998, Quaternius Adventurer unchanged.

## Motion retargeting

`bw motion --bvh file.bvh --rig <run-id> [--export]` moves a BVH clip onto a rig made by `bw rig`
(the rig's preset is read from its run; `--preset` overrides). BVH joints are matched to Rigify controls by name (kimodo `LeftLeg/LeftShin`, Mixamo
`LeftUpLeg/LeftLeg`, CMU and Quaternius animal `BackLeg/FrontUpperLeg` conventions are covered by tests or runs).
Units and frame rate are taken from the file (CMU's 16.7-unit hip height becomes a 0.06 scale); zero-length joints
(CMU hands) take their direction from the first non-thumb child bone.

The **up axis is detected** from the file, because getting it wrong fails silently rather than loudly: the standard
says Y, Blender exports Z, and feeding a Z-up clip as Y-up moved the wolf's feet a metre off the floor while every
step still ran to completion (bone direction error 2.8° → 14.9°). Detection reads the rest hierarchy and picks the
axis on which the head sits above the feet; with no recognisable head or feet it falls back to the standard Y.
`--bvh-up y|z` overrides it.

- **Arms, body:** each bone receives the source joint's world rotation delta. Limbs get a rest-pose correction (a
  common reference frame built from the bone direction and world forward), so an A-pose rig receives the same motion
  as a T-pose rig (0.2 cm difference) and twist comes along. Spine, neck and head take their reference from the
  clip's most typical frame instead of the bind pose — animal rigs are often bound with the head raised, and a pure
  bind-pose delta then makes the character stare at the ground.
- **Tail (quadrupeds):** the wolf metarig's tail chain is numbered backwards from the pelvis (`spine.003` → `spine`),
  and source rigs carry anywhere from two to eight tail joints, so they are spread evenly over the four controls.
  Without this every `Tail*` joint collided on one control and the tail stayed frozen.
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
parented to a hand or finger bone (weapons, tools). An attached part is treated as **decoration** when the skinned mesh
already has geometry around its bone (antlers, shoulder armour, a separate head on a body that already has a neck):
it is skinned but ignored when locating joints and measuring height — a stag's antlers would otherwise add 30% to its
height and push every leg joint. A part whose bone region is empty in the skinned mesh (a robot's arms and legs) is
structural and takes part in everything. Files without an armature are used whole.

## Which way the character faces

Importing has to put the character upright, on the floor, facing −Y, with left at +X. Front-to-back is read from the
mesh (feet point forward; for quadrupeds the head decides). **Left-to-right cannot be read from a silhouette** — a
T-pose's arm span and a body's depth are both just "the wide axis". When the file has a skeleton, the answer is in it:
the axis on which left/right bone pairs are furthest apart is the lateral one, and if that is Y the character is
turned 90°. One benchmark asset was built this way and had been rigged sideways ever since — bones crossed in an X
through the legs, 89 cm mean joint error, the worst asset in the set. With the turn corrected it passes every gate.

## How joints are found

Landmarks come from mesh evidence, not from human body ratios: the crotch is the top of the run of bands where the
silhouette splits left/right, the neck is the narrowest band under the head, the ankle is the top of the foot blob
(the part sticking out in Y), the knee is refined from the leg centreline. Height ratios remain only as last-resort
fallbacks and every use is reported in `landmarks.ratio_fallbacks`, with `landmarks.suspect` listing why a result may
be wrong. Inside/outside tests run against a voxel-remeshed volume copy, because game meshes are overlapping shells
with holes.

Quadrupeds use a separate path. The four foot positions and two more things are measured from the mesh: the **back
height** above each leg (hip = 0.80 of it, shoulder = 0.635, both ±0.06 across the 11 reference animals — twice as
consistent as any ratio of total height) and the **front leg's backward lean**, which splits dog-type legs (lean
0.089–0.133, elbow high at 24% of the leg) from hoofed ones (−0.05–0.066, elbow at 50%) with no overlap. Joints in
between are placed at ratios measured from the reference rigs — the knee at 27.4% ± 1.9 of hip-to-toe is the most
consistent quantity in the whole dataset. What is *not* measured is the pelvis bone's height: reference rigs put it
anywhere from 0.44 to 0.88 of body height, so that part is convention, not anatomy.

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

`--skin` reports, per asset and **per body region**, the distance between the "influence centres" of the two weight
sets (name-free), plus the weaker name-agreement number. Current baseline: mannequiny 4.1 cm (2.3% of height),
Quaternius UAL 9.2 cm (5.0%), cesium_man 10.6 cm (7.0%). Read these as a floor, not a score: reference rigs that draw
every bone as a zero-length marker at the joint (the whole Quaternius family) make any distance-to-bone measure
pessimistic, and one of them parents the foot to the root rather than the shin, which no reconstruction can repair.

Weights themselves are engine-ready: automatic weighting binds up to 9–10 bones to a single vertex, which glTF and
most engines silently truncate to 4, so bonewright keeps the largest 4 and renormalises (measured cost: 0.05 cm).

Mixamo/Adobe assets are deliberately excluded: the Adobe terms forbid using their content to test AI systems. Epic's
own Fab content (Paragon, Game Animation Sample) is excluded too — it is tagged NoAI and ships in Unreal-only format.

## License

MIT (this CLI). Anything that runs inside Blender as an add-on must be GPL; bonewright runs Blender headless and ships
no add-on. Rigify (GPL) is used through Blender, not vendored. Model weights for kimodo.cpp keep their own licenses
(SOMA/G1: NVIDIA Open Model License).
