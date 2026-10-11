# Changelog

All notable changes to this project. Numbers are measured against the original authors' rigs
(`bw bench`), reported as a mean joint error and as a percentage of the character's height.

## [Unreleased]

Proposed next version: **0.3.0** — no new command, but new flags (`bw --version`, `bw doctor --for-issue`) and a
changed default (the model prompt language follows `BW_LANG`); fixes, documentation and examples otherwise. No
benchmark number moves.
See `docs/RELEASING.md` for the release steps.

### Added
- The first line of `bw rig` says how many model calls it may make (`up to 2 model call(s) (fit·judge)`, or
  `0 model calls`), instead of the cost showing up only in `report.md` afterwards.
- `bw doctor` says whether model calls are on (codex, the default: 2 calls per `bw rig`, about $1) or off
  (`BW_BACKEND=mock`), and how to get 0 tokens.
- The guide's "Install and run" now shows `bw status` (it was mentioned by error messages but documented nowhere):
  what a line means, where a failed run's reason is, and that export/demo keep their own state.
- A finished `bw rig` ends with a `next:` line on stderr naming `bw demo`, `bw export` and `bw motion --rig` with its
  run-id filled in, so the README's next step no longer means cutting the id out of the report path. stdout is still
  the one report line.
- `tests/README.md` opens with an English summary (one command, what skips without Blender, the two environment
  switches, the three CI jobs); `tests/test_docs.py` keeps its skip count honest.
- `docs/RELEASING.md`, which this changelog points to, opens with an English summary (who releases, how the version
  number is chosen, the five steps); the detailed notes below it stay in Korean.
- `report.md` (rig and motion) starts with a versions line — bonewright, Blender, Python and OS — because the
  "A rig came out wrong" issue template asks for `report.md` and rigs change between versions. The template also
  asks for `bw --version`.
- The guide's Motion retargeting section has a table of which BVH joint (Mixamo-style and kimodo-style names)
  drives which rig control, and why the mid spine (`Spine`) is not moved on purpose — "unmapped ['Spine']" in the
  motion example read like a failure. `tests/test_docs.py` checks the table against the matching code.
- Both READMEs now say, in one line, that repeated flags (prompt language, rest pose) can be fixed in
  `runs/config.json`, with an example and a link to the guide's Settings table; `tests/test_docs.py` checks that the
  two examples match and use only real keys.
- `python3 examples/rig_sample.py --motion` rigs the procedural capsule doll and retargets a procedural 24-frame wave
  BVH onto it (no download, no licence question). The result, `examples/sample-output/capsule_doll_motion.md`
  (18 of 19 joints mapped), is linked from both READMEs; `tests/test_examples.py` compares it with a fresh run.
- `bw doctor` and the start of `bw rig` warn, in one line, about keys in `runs/config.json` that bonewright does not
  know (usually a typo such as `rig.cross_trimm`), with the nearest real key; they used to be ignored silently. The
  run goes on with the defaults. `docs/GUIDE.md` → "Settings (`runs/config.json`)" lists the keys worth changing,
  their defaults and the prompt-language order; `tests/test_docs.py` checks the table against the built-in defaults.
- An issue template for documentation that is wrong or unclear (where, what it says, what actually happens).
- `docs/GUIDE.md` → "Known gaps and failed attempts": an English digest of the open holes and failed experiments
  recorded in the Korean `docs/ROADMAP.md`, with the numbers. CONTRIBUTING points there; `tests/test_docs.py` checks
  every `GUIDE.md#anchor` link against the guide's headings.
- `bw doctor --for-issue [RUN_ID]` prints one block to paste into a bug report: bonewright, Python and OS
  versions, `BW_*` settings, the `bw doctor` result, and one run's `state.json` with the last 40 lines of its newest
  log (the latest run when no id is given), plus `runs/config.json` as it is (even when broken) with any unknown
  keys named. Home-folder paths are replaced with `~`. The issue templates ask for it.
  CI runs the installed command outside the repository on Linux, Windows and the `bpy` job
  (`scripts/check_issue_report.py`): one `<details>` block, no traceback, and no home-folder path left — with
  `BW_HOME` placed under the home folder so there is a path to replace (`C:\Users\<name>` on Windows).
- `examples/rig_sample.py`: rig a small sample mesh (procedural capsule doll, the CC0 `adventurer`, or any GLB)
  and write a table of deform-bone count, left/right split and names. `--table x.glb` reads a GLB without Blender.
- Blender-dependent tests are marked with `@requires_blender` (`tests/_marks.py`). `BW_SKIP_BLENDER=1` skips them
  for a quick check; `BW_REQUIRE_BLENDER=1` turns a missing Blender into a failure (used by the CI `bpy` job).
- `docs/PRE-PUBLIC-AUDIT.md`: what to look at before the repository goes public (report only, nothing removed).
- Issue templates for install / `bw doctor` problems and feature requests; blank issues now point to the guide and
  SECURITY.md. `bw --version` prints the package version the install template asks for.
- A pull-request template with the CONTRIBUTING checklist (tests, license boundary, CHANGELOG) and a before/after
  table for the four benchmark assets when joint code changes.
- `tests/test_docs.py`: relative links in the README, Korean README, guide and examples README must resolve, and
  every `bw <command> --flag` written in them must exist in the CLI parser. Runs in CI without Blender. The same
  checks cover CONTRIBUTING, SECURITY, RELEASING and the issue / pull-request templates, plus the guide section
  titles the templates quote and the files `ISSUE_TEMPLATE/config.yml` links to.
- Package metadata: project URLs (home, guide, issues, changelog) and both license notices (`LICENSE`, MIT, and
  `bonewright/bpy_scripts/LICENSE`, GPL) are now shipped in the sdist and wheel (`license-files`, hatchling ≥ 1.27).
- CI runs the Blender-free tests on `windows-latest` too. `bw` now finds Blender installed under
  `Program Files\Blender Foundation\Blender X.Y\blender.exe` (newest version wins). No rig has been built on Windows.
- `tests/test_i18n.py`: every `T(Korean, English)` pair in `bonewright/` must have no Hangul on the English side and
  the same f-string placeholders on both. `tests/test_docs.py` also checks that every test-command list (CI,
  CONTRIBUTING, PR template, tests/README, RELEASING) names every test module.
- `examples/sample-output/capsule_dog.md`: a four-legged sample. `make_test_mesh` builds a procedural capsule dog
  (`kind=quadruped`) and `python3 examples/rig_sample.py --preset quadruped` rigs it: gates pass, 110 deform bones
  with front and hind leg chains and paw digits. Linked from the README; a Blender test checks it stays current.
- `examples/sample-output/capsule_doll.md`: what `python3 examples/rig_sample.py` prints (73 deform bones), so the
  table can be seen before installing Blender. A Blender test checks that today's rig still matches it.
- `docs/GUIDE.md` "Text → motion: building kimodo.cpp": the build steps, the three paths bonewright looks for and the
  weight licences. `bw motion --text` and `bw doctor` point there instead of a dated research note.
- CI rigs the bundled sample once more with the installed `bw` from outside the repository (`BW_BACKEND=mock`),
  so a Blender script or prompt missing from the wheel fails the build. `tests/test_docs.py` checks the README
  quickstart: same commands in both languages, real flags and extras, bone counts matching `examples/sample-output/`.

### Changed
- A `bw bench` path that does not exist now says "file or folder" (bench takes folders) and ends with the next
  command: an asset folder already fetched into `bench-assets/`, or the fetch command followed by
  `bw bench bench-assets/samples`.
- `bw motion --bvh` refuses an empty file, or one that does not start with `HIERARCHY` (a web page saved as
  `.bvh`), before creating a run folder or starting Blender, and points at `examples/wave.bvh`. It used to fail
  inside Blender's BVH import, or behind "Blender not found".
- A wrong `--preset` (`bw rig x.glb --preset dog`, also `bw bench` and `bw motion`) now adds which value to use:
  `humanoid` for people, `quadruped` for four-legged animals, `--from-shape` for other body plans.
- A path with spaces typed without quotes (`bw rig my char.glb`) used to get only argparse's "unrecognized
  arguments: char.glb". When the words join into a file that exists, the error now ends with the same command with
  the path quoted, ready to paste.
- `--facing` (`bw rig`, `bw bench`) now says how to choose: look at the imported mesh from Blender's front view
  (numpad 1) — face visible means `neg-y`, back of the head means `pos-y`. A wrong value such as `--facing up` gets
  the same line under argparse's list of choices, which used to be all it printed.
- Two settings that nothing ever read are gone from the defaults: `blender.prefer_module` (bonewright always tries
  the Blender app first and the `bpy` wheel second) and `default_model` (the models are set per role under
  `models`). If your `runs/config.json` still has them, `bw doctor` names them as unknown keys; delete them.
  `tests/test_errors.py` now fails on any default setting the code does not read.
- `bw --help`, `bw doctor` and `BLOCKED:` error messages follow `BW_LANG` (or the locale): English by default,
  Korean for `ko`. So do the gate rejection reasons listed under `BLOCKED:` and the `bw rig` / `bw motion` progress
  log, and the analysis warnings and errors raised inside the Blender scripts (`bpy_scripts/_common.T`, the same
  rule without importing the MIT package), the `bw bench` table and summary, and the `runs/<id>/report.md` lines.
  `tests/test_i18n.py` fails on any bare Korean string anywhere in `bonewright/` (docstrings aside).
- The model prompt language (`bw rig --lang`) now follows the screen language when it is not given: `--lang`, then
  `lang` in `runs/config.json`, then `BW_LANG` / the locale. It used to default to Korean, so English users got the
  visual judge's notes and the fit reasoning in Korean.
- An unexpected error no longer ends in a bare one-line `BLOCKED:`. It names the exception type, points at the
  run's `logs/` folder and the issue templates, and `BW_DEBUG=1` prints the full traceback.
- README first screen rewritten to what it does / install / first run / example output; the long material moved
  to `docs/GUIDE.md`, with a Korean edition in `README.ko.md`.
- `bw doctor` marks each item `[required]` or `[optional]` and exits 0 when Blender or `bpy` is found, even
  without `codex` (only the default model-judged `bw rig` needs it). Its output follows `BW_LANG` too.
- `scripts/fetch_bench_assets.py` downloads five more human and robot assets (coverage 57 → 62 of 66).

### Fixed
- An option typed without its value (`bw rig a.glb --facing`) got only argparse's "expected one argument"; it now
  lists the choices (`--facing auto | neg-y | pos-y`) or a pasteable example (`--size 640`, `--pin spine.004=0,0,1.42`).
- A `--targets` file of the wrong shape (a list, a bone without head/tail, two-number coordinates) went as far as
  Blender; it is now checked first, naming each bad entry and the expected `{"bone": {"head": [x, y, z], ...}}` form.
- `bw doctor` and `bw doctor --for-issue` stopped with `BLOCKED:` on a broken or wrong-typed `runs/config.json` (or
  a `BW_BACKEND` typo), so the issue report could not be made; they now show it as one `[settings]` line, check
  everything else with the defaults, and exit 1.
- `BW_HOME` set to a file made `bw status` report "no runs yet" (exit 0) and `bw doctor` print the file as the work
  folder; every command now stops with that, and `bw status` / `bw doctor` say when `BW_HOME` does not exist yet.
- `runs/config.json` accepted values the command line refuses (`"lang": "fr"`, `"rest_pose": "T"`); they now stop with
  the allowed values (the same choices as `--lang`, `--rest-pose`, `--weights`).
- A `runs/config.json` value of the wrong type (`"max_input_tokens": "lots"`, `"rig": "t"`) surfaced later as an
  unexpected TypeError; the file is now checked against the defaults when it is read, and the error lists each key with
  the expected type, its default and what was found.
- Run ids (`--run-id`, `--rig`, and the run id of `bw export`/`demo`/`status`/`doctor --for-issue`) accepted `../x`
  and `a/b`, so a run could be written outside `runs/` and `bw doctor --for-issue ../..` read files outside it. They
  now take letters, digits and `. _ -` only.
- A typo in `BW_BACKEND` (`Mock`, `moc`) silently ran the paid `codex` path; any value other than `mock` or `codex`
  now stops before any model call or Blender step, naming the nearest value.
- A malformed `--pin` (`--pin foo`, `--pin hand.L=1,2`) exited 1 with a bare line, unlike other input errors; it is
  now an argument error (exit 2) whose `→` line is a pasteable example using your own bone name.
- Without ffmpeg, `bw demo` suggested `brew install ffmpeg` (Korean) or just "install ffmpeg" (English); it now names
  the command for the OS it runs on (brew, winget or apt).
- `bw bench --gt-mesh nope.glb` said "mesh file not found"; it now names `--gt-mesh`.
- `bw rig a.glb --targets a.glb` (the mesh passed by mistake) was told to look for "a broken comma or bracket"; a
  binary file is now called that, with the `--targets runs/<id>/targets.json` it expects.
- `bw rig --from-skeleton --from-shape` accepted both, leaving it unclear which path ran; they are now mutually
  exclusive, and the error says what each one does.
- `BW_NO_RENDER=1 bw demo` looked for Blender before saying it makes no video, so without Blender the real reason
  was hidden behind "Blender not found"; the render switch is now checked first.
- With the `bpy` wheel and no Blender app, every Blender step started a fresh `python -c "import bpy"` probe
  (about 0.7 s each); the answer is now remembered for the rest of the command.
- `bw doctor --for-issue <id>` now includes `export_state.json` / `demo_state.json` when they exist, so a report
  about a failed export carries the export's own status.
- `bw status` lines ended in an unexplained `· in 0`; they now say `input tokens 0`, and a failed or stopped run
  adds where to see why: `bw doctor --for-issue <id>`.
- A failed `bw export` or `bw demo` overwrote the rig run's `state.json`, so `bw status` showed a finished rig as
  "export_rig failed". They now record their own `export_state.json` / `demo_state.json`.
- Without Blender, `bw rig`, `bw motion`, `bw export` and `bw demo` made a `runs/<id>` folder before failing, so
  `bw status` filled up with "analyze failed" runs. Blender is now looked for first (and `bw motion --text` checks
  kimodo.cpp first too); nothing is written until both are there.
- `bw motion --map` with a missing or broken file was only caught after Blender had imported the BVH; it is now
  checked with the other inputs, before Blender and before a run folder is made.
- `bw export <id> --out` with a folder or a non-GLB name (`out.fbx`) only failed after Blender started. A folder now
  gets `<id>.glb` inside it; another extension, or a missing parent folder, stops before Blender with the fix.
- A mistyped command (`bw rigs`, `bw statsu`) got only argparse's "invalid choice"; it now names the nearest command
  and `bw --help`. `bw resume`, which old notes mentioned, says to rerun or reuse `runs/<id>/targets.json`.
- 21 arguments had no help line in `bw <command> --help` (the mesh and `--preset` of `bw rig`, `--size` and
  `--frames` of `bw demo`, every `--run-id` and `--quiet`, ...); each now has one in both languages.
- An empty mesh file, or a `.glb` that is not glTF (another format renamed), got as far as starting Blender — and
  where Blender is missing, "Blender not found" hid the real problem. `bw rig` now refuses both before Blender, with
  what to do.
- `bw rig <folder>` said "mesh file not found" although the folder exists; it now says a folder was given, names a
  mesh inside it and points at `bw bench <folder>` for measuring all of them.
- `bw rig --budget 0` was silently ignored and a negative budget stopped the run only after the Blender analysis;
  it now accepts 1 or more, and `bw rig --help` says it caps model input tokens (default 600,000).
- `bw demo --size 0` / `--frames -1` created a run folder and reached the Blender render before failing, and
  `bw usage --days 0` reported "no model calls in the last 0 days"; all three now accept only whole numbers of 1 or
  more and say what to type instead (e.g. `--size 640`, `--days 30`).
- `bw bench` with no meshes ended with "the following arguments are required: meshes", though the benchmark assets
  are not in the repository. It now adds the command that fetches the four Khronos samples and the folder to pass
  (`python3 scripts/fetch_bench_assets.py --only samples && bw bench bench-assets/samples`).
- `bw rig` with no mesh ended with seven lines of usage and "the following arguments are required: mesh". It now
  adds the README's first command on the character in the repository
  (`bw rig tests/assets/quaternius_adventurer.glb --from-skeleton --no-judge`, no model calls); exit code 2 as before.
- `bw demo` and `bw export` without a run-id ended with argparse's "the following arguments are required: run_id".
  They now say `BLOCKED:` with the latest finished rig as a command to paste (`bw demo rig-…`) and `bw status`, or,
  with no rig yet, to run `bw rig <mesh>` first and where they looked (exit code 2 as before).
- `examples/rig_sample.py` without Blender pointed at `--table x.glb`, a file nobody has. It now ends with
  `python3 examples/rig_sample.py --table adventurer`, which runs as pasted on the character in the repository;
  `tests/test_examples.py` runs that command in both languages.
- README Install (both languages) started at `pip install .` with no clone, although First run uses files inside the
  repository; on macOS Homebrew and recent Linux Python a global `pip install` is refused (PEP 668); and the
  `bw doctor` comment claimed a Rigify check doctor does not make. It now goes clone → venv → `pip install .` →
  `bw doctor` (Blender or bpy, either one), with the Windows venv line.
- `bw status` stopped at the first run whose `state.json` it could not read (a missing key, broken JSON — e.g. a
  sync-conflict copy or a run from an older version) with an "unexpected error, open an issue" message. That run
  now gets its own line saying it was skipped and which folder can be deleted; the other runs are still listed.
- `bw usage` with no model calls printed a JSON of zeros, which could mean "nothing recorded" as well as "nothing
  used". It now adds one line on stderr naming the ledger file (or that it does not exist yet, with `BW_HOME`), that
  the 0-token routes are not recorded, and `--days`; the JSON on stdout is unchanged.
- `bw doctor` printed both Blender and `bpy` as `[required]`, so it read as if both had to be installed; only the
  last line said "either one". Each line now says `[required: one of]`, and once one is found the other is
  `[not needed]` (a missing Blender with `bpy` present reads "the bpy module is used instead").
- `bw bench` on an empty folder or a missing file ended with exit code 0 and "mean Nonecm", and a missing file
  was reported as "Blender not found". Inputs are now checked before Blender starts, a missing Blender stops the
  whole bench once with the install hint, and a bench that measured nothing is `BLOCKED:` (exit 2) with a pointer
  to `report.md` and `scripts/fetch_bench_assets.py`.
- `bw motion` silently ignored `--export`, `--map`, `--legs` and `--no-roll` without `--rig`, so a run could end
  with no GLB and no reason. They are now refused before Blender starts, with the fix (`--rig <run-id>`).
- `bw status` with no runs printed nothing, so a broken install and a different `BW_HOME` looked the same. It now
  says where it looked and suggests `bw rig <mesh>` or setting `BW_HOME` (on stderr; stdout stays empty).
- A bare `bw` ended with argparse's one line `error: the following arguments are required: cmd`. It now prints
  the command list and a next step (`bw doctor`, then the README's first-run command); the exit code is still 2.
- `bw motion --bvh` progress started at `[3/3]`, as if two steps had been skipped. The step numbers now count
  only the steps that run: `[1/1]` for a BVH alone, `[1/3]`…`[3/3]` with `--rig` and `--export`.
- Running `bw rig` (or `motion`, `demo`, `export`, `bench`) without Blender was reported as an unexpected error:
  it pointed at an empty log folder, `BW_DEBUG=1` and the issue templates, and left the run as `running` in
  `bw status`. It is now a plain `BLOCKED:` that names the download page and `bw doctor`, the run is marked
  `failed`, and a `BW_BLENDER` that points at a missing file is named as such. `bw doctor` shows the download page too.
- Piping `bw` into something that stops reading early (`bw doctor | head -1`) printed `BLOCKED: BrokenPipeError`
  and the issue-template hint. It now ends quietly.
- "codex executable not found" now also names the 0-token routes (`--from-skeleton --no-judge`,
  `--from-shape --no-judge`, `BW_BACKEND=mock`), so a first run without codex has somewhere to go.
- The READMEs said `--from-skeleton` costs zero tokens; it skips the fit call, but the visual judge still calls the
  model unless `--no-judge` is given. The READMEs now say so, and "First run" opens with a 0-token command on the
  character in `tests/assets/` (install → first result in three steps, no codex).
- `addon/README.md` still said the bridge add-on was "planned for v0.2"; 0.2.0 shipped without it. It now says it is
  an unscheduled idea, and `tests/test_docs.py` flags a plan dated to a version that is already out.
- `scripts/check_issue_report.py` (CI) had Korean-only option help and failed without saying where to look; the
  help follows `BW_LANG` and a failure now points at `scrub()` in `bonewright/cli.py`.
- CI step names and comments in `.github/workflows/test.yml` were Korean; they are English now, so a contributor can
  read which step failed. `tests/test_release.py` keeps them that way.
- `scripts/bench_score.py`, the source of the benchmark numbers in the READMEs, printed its progress, scores and
  failure list in Korean only and had no option help; it now follows `BW_LANG` (verdicts are fixed codes internally,
  so run ids are `sc_<asset>_skeleton|preset|shape`).
- `scripts/fetch_bench_assets.py` identified itself to asset hosts as `bonewright-bench-fetch/0.2 (+https://github.com/)`;
  the version now comes from the package and the address is the repository's.
- The English guide still had Korean in six places (the ROADMAP section tags under "Known gaps and failed attempts"
  and one command comment). The tags are now English links to the Korean ROADMAP sections; `tests/test_docs.py`
  checks the anchors and that no Korean is left outside link targets.
- `scripts/check_license_boundary.py` (run by CI and the PR checklist) reported in Korean only and did not say how to
  fix a violation; it now follows `BW_LANG` and each line says what to do (move Blender code into
  `bonewright/bpy_scripts/`, restore a missing licence file).
- `python3 scripts/fetch_bench_assets.py --help` and its progress lines were Korean only; they now follow `BW_LANG`
  like `bw` (checked offline by `tests/test_i18n.py`).
- Asset licences were stated in Korean only: `tests/assets/README.md` (the CC0 Adventurer) now leads in English, and
  the `bench-assets/ATTRIBUTION.md` written by `scripts/fetch_bench_assets.py` (sources, licences, what was left out
  and why) is in English. `tests/test_docs.py` checks both.
- `python3 examples/rig_sample.py --motion --preset quadruped` rigged the dog (tens of seconds in Blender) before
  saying `--motion` is humanoid-only; it now stops before rigging. `--motion --table` used to ignore `--motion`
  silently and now says the two do not go together.
- `python3 -m unittest` with no arguments ran zero tests ("NO TESTS RAN", exit 5) because `tests/` was not a package;
  it now discovers the same seven modules as the long command in CONTRIBUTING, and `tests/test_docs.py` checks that.
- `bw doctor --for-issue` listed unknown `runs/config.json` keys twice (in the `bw doctor` part and under the
  settings file); they now appear once, next to the file they come from. Plain `bw doctor` still warns.
- CI uses `actions/checkout@v5` and `actions/setup-python@v6` (Node 24); the Node 20 versions printed a
  deprecation warning and will stop running when GitHub removes Node 20.
- `examples/rig_sample.py` stopped with Korean-only messages (no Blender, missing file, not a GLB) even with
  `BW_LANG=en`; they now follow the screen language like `bw` itself.
- `python3 examples/rig_sample.py --help` (what people type right after an error) was Korean only; the
  description, every option and the result lines now follow `BW_LANG` too.
- The example pages the English README links to were Korean. `examples/README.md` is now English (Korean moved to
  `examples/README.ko.md`), and `rig_sample.py` writes its result documents (and the committed
  `examples/sample-output/*.md`) in English; `tests/test_examples.py` checks there is no Korean left in them.
- **`runs/<id>/report.md` no longer contains your home folder.** The issue template asks for this file as is, but
  it listed the mesh, the rig `.blend`, `targets.json` and the motion files by absolute path. Files inside the run
  folder are now written relative to it (`targets.json`, `02_rigged.blend`), and paths outside it show the home
  folder as `~`.
- **`rig.cross_trim` is on by default; the documentation said otherwise.** The 0.2.0 changelog entry and
  `docs/ROADMAP.md` described the first, ray-based version. The released code uses voxel-geodesic distance and
  has it on (`bonewright/config.py`). Both texts are corrected, and `tests/test_docs.py` now checks every
  "`section.key` … on/off by default" claim in the README, guide and changelog against `config.DEFAULTS`.
- **Input mistakes now stop before Blender starts, and say what to change.** A missing or unsupported mesh,
  a missing `--targets`/`--map`/`--bvh` file, a broken JSON file, or a run id with no rig used to surface as a
  Blender traceback or a bare "file not found". They now raise `Blocked` with a `→` line naming the fix
  (supported formats, `bw status`, the `bw rig ... --run-id` to run first). The usage-limit message pointed at a
  `bw resume` command that does not exist; it now says to rerun, or reuse `runs/<id>/targets.json` with
  `--targets`. `bw status <unknown id>` exits 2 with a hint instead of a traceback. Covered by `tests/test_errors.py`
  (no Blender needed).
- A broken `runs/config.json` (a trailing comma, a list instead of an object) ended as an "unexpected error — open
  an issue". It is now a `BLOCKED:` naming the file, the line and column, and the usual causes.
- **Quadruped judge renders were cropped.** `render_views.py` sized the camera from the character's
  *height*, which is right for a person and wrong for anything longer than it is tall: the wolf
  (2.68 tall, 5.55 long — the tail counts) lost its head and its tail off both edges of the side view, and the model was
  asked to judge bone placement on a picture that did not contain the bones. The camera now sizes from
  the longest of the three bounding-box edges. Humanoids are unaffected — height is already their
  longest edge — so no existing number moves.
- `bw plugin-path` printed `site-packages/plugin`, a folder that does not exist, when bonewright was installed
  with pip: the plugin was never packaged. The wheel now carries it as `bonewright/_plugin/`, and the command
  prefers the repository's `plugin/` when run from a checkout. CI checks the installed path from outside the repo.
- The Codex plugin manifest (`plugin/.codex-plugin/plugin.json`) still said version 0.1.0 and "retargeting comes in
  v0.2". It now matches the package version; `tests/test_release.py` keeps the three version strings in step.
- `--pin` rejects malformed input (empty bone name, more than one `/`, NaN or infinite coordinates) before any
  work starts.
- Documentation audit (2026-09-20): eleven claims that did not match measurements were corrected; the wolf's
  tail is three bones, not one.

## [0.2.0] - 2026-09-20

Summary: humanoid and quadruped Rigify presets, rejection gate, `--from-skeleton`, BVH retargeting, `bw bench`.

### Added
- **Human-only metarig bones are dropped when the source skeleton has no counterpart.** Rigify's `breast.L/R`
  has nothing to map to on a frog, so it floats at human-chest proportions and takes shoulder flesh; the seam
  between it and the upper arm tore at 4.6x over 1.19% of the mesh. Removing it fixes that asset outright
  (4.55x/1.19% → **2.58x/0.0%**) and leaves six control assets untouched. The same idea applied to finger
  segments failed (see Fixed) — fingers are a chain, so their flesh piles onto a distant hand bone, while the
  breast pair hands its flesh to the chest bone right beside it. On a quadruped `pelvis.L/R` behaves the same
  way — Bull's worst seam was exactly `DEF-spine.001` / `DEF-pelvis.L` — and removing it improved or held every
  one of the ten animals (Bull 11.63x → **1.93x**, Cow 11.63 → 2.44, Shiba Inu 7.47 → 2.44, motion pass rate
  7/10 → **9/10**). On a human it is the opposite: those bones sit correctly on the hips and doing the same
  thing pushed cesium_man from 3.72x/0.9% to 5.38x/1.1%, so `pelvis` is only dropped under the quadruped preset.
- **Unweighted vertices are filled from their connected neighbours** instead of from the nearest bone. A
  nearest-bone guess makes one vertex follow a different bone than the flesh around it and the shell cracks;
  copying the weights of the closest vertex *along the mesh* is interpolation, not a guess. Orc: 12 stragglers
  on a weapon, `needs_review` → `ok`. A fill that spreads over 5% of the mesh still fails the gate.
- **`_voxgeo`** — voxel geodesic distance, used to drop influences that only reach a vertex by leaving the
  flesh. Filling the mesh with voxels closes the hairline gaps between the pieces of a segmented mannequin while
  leaving a skeleton's empty chest open, so the resolution itself separates "ignorable gap" from "real cavity"
  (see the note on the ray-based attempt below).
- **`--from-shape`** — builds a skeleton from the mesh's own medial axis when the file has no skeleton and the
  body is not human- or dog-shaped. Every asset the silhouette gate used to refuse now rigs: an insect, a seated
  character, a fox under the humanoid preset, three Khronos test shapes. Shape-rig bones carry role names
  (`thigh.L`, `forearm.R`, `chest`) when the read can classify them.
- **Generic chain rig** — when a source skeleton cannot be mapped onto a preset (a dragon has no legs, a blob has
  four bones), the metarig is copied bone-for-bone and every bone gets a control. 43 CC0 creatures: 40 clean,
  3 needing review, 0 refused — up from 14 rigged.
- **Inside read (`_medial.py`)** — voxel fill, distance transform and maximal-sphere packing find limb tips and
  the path back to the body, whatever the pose. Supplies the arm centreline, crotch and ankle that the
  silhouette could not read. `quat_pp_41j` went from refused to 31.34 cm (5.7% of height).
- Held props (a weapon, a trident) are detected by weight concentration on hand bones and excluded from every
  size and centre measurement, and bound rigidly to one bone.
- `scripts/check_license_boundary.py`, enforced in CI: the MIT core must never import `bpy`.
- `rig.cross_trim` drops influences that reach a vertex through empty space. On a hollow ribcage an arm bone
  reaches across the empty chest and takes the ribs — KayKit skeleton warrior's arm-into-torso leak goes from 11 of
  94 vertices to 0. *Corrected in 0.2.1:* this entry first said "off by default" and described a one-ray test.
  That test cost more than it gained on an ordinary layered game mesh (mannequiny retarget stretch 4.71x off, 7.88x
  on), so before the release it was replaced by a voxel-geodesic test (`bpy_scripts/_voxgeo.py`), and 0.2.0
  shipped with `rig.cross_trim` **on by default**.
- A regression test that retargets a **real** CC0 asset and measures mesh stretch. The procedural test mesh has a
  single shell and never showed the cost above; the real asset fails at 9.34x with the trim on.

### Fixed
- **A nearly-successful voxel-proxy bind was being thrown away over a hair's breadth.** On one asset automatic
  weighting left 3464 of 6994 vertices empty while the voxel proxy left 16 — but transferring those weights back
  to the original mesh left 406 (5.8%), just over the 5% cutoff, so the whole thing was discarded for envelope
  weighting, which hands a single vertex 0.25 of each foot. That cutoff predates the neighbour fill, which now
  interpolates leftovers instead of guessing, so it is 15%. The asset goes from 13.94x/0.89% to **3.37x/0.0%**,
  and of the 406 leftovers 356 bind as whole rigid pieces, 50 interpolate, and none are guessed.

- **Tried and reverted: dropping metarig finger segments the source skeleton never had.** A source rig that stops
  at two thumb joints leaves the metarig's third floating at human-hand proportions, where it grabs flesh (a bunny
  had `DEF-thumb.03.L` owning vertices at weight 1.00). Removing the untargeted tips helped that one asset
  (12.19x → 11.30x) and hurt several others badly: godot_player 1.87x/0.0% → **8.46x/3.17%**, quat_pp_41j
  2.09x → **11.85x**, rigged_figure 1.61x/0.0% → 3.72x/**6.51%**, and the KayKit mage dropped below the
  deform-bone minimum. Hand flesh spread across finger bones is worth more than the floating tip costs.
- **Motion is judged by depth *and* breadth.** The single worst edge ranks assets almost backwards: Bull stretches
  11.63x but on 0.22% of its edges, while frog stretches 4.55x on 1.19%. Results are now split into pass, a
  localised spike, and a real tear.

- **The arm-into-torso check is now calibrated against the author.** Running the same rule over the file's own
  weights shows how much of the "leak" is the body's shape rather than our error: on a chibi whose arms are fused
  to the body the author himself gives 39.2% of chest-midline vertices to arm bones, while on a hollow KayKit
  skeleton the author gives **0%**. The gate now allows what the author allowed and fails anything worse — the
  same trick already used for left/right symmetry. It changed no pass/fail in the benchmark.

- **Tried and reverted: reusing the author's painted weights.** Bone names differ between rigs but the positions
  came from the same skeleton, so each source bone was paired with the DEF bone nearest to it. The leak metric
  loved it (KayKit skeleton warrior 11 of 94 chest vertices → 0). Animating it told a different story: the same
  asset went from 5.78x to **11.25x** mesh stretch under a CMU walk, and cesium_man from 3.72x to **20.7x**.
  Plenty of rigs mark a joint with a **zero-length** bone, which collapses any position-based pairing — a left
  hand ended up weighted to a torso bone. The gates cannot see this; only animating can.

- **The arm-into-torso check could switch itself off.** It samples a narrow band down the middle of the chest
  and skips the verdict when fewer than 30 vertices land there — so a low-poly character could pass by having
  too few samples, and moving a bone could silently disable the check (godot_player went 17/31 → 21 samples →
  no verdict). The band now fills up to 30 samples from the vertices nearest the midline before giving up.
- **Shape-rig limb chains are cut at the neck of the limb**, the point where the mesh's thickness drops most
  steeply, rather than at a fixed fraction of the torso's thickness. The fixed fraction overshoots on bodies
  whose widest point is the belly. Shape-rig retarget stretch on mannequiny: 67.2x → **38.2x** (still unusable
  for motion — see ROADMAP — but the arm no longer starts in the middle of the chest).

- Left-right repair now fires whenever the source rig is symmetric, and averages the two sides instead of copying
  one onto the other.
- Source symmetry is measured about the source rig's own centre line, not about x=0, so a 2 cm armature offset no
  longer inflates the gate's tolerance and hide real errors.
- Benchmark left/right matching used bone names; on files the importer turns 180° it compared our left leg with
  the author's right. Fixed by comparing on coordinate sign — `robot_expressive` 183.15 → 48.39 cm. Historical
  "robot 135–277%" figures in older notes contain this artifact.

### Known limits
- Motion retargeting onto a `--from-shape` rig is not usable: max edge stretch 44x against under 6x on the preset
  path. The arm chain starts inside the chest, so automatic weights give chest vertices to the arm.
- `bpy_scripts/` is GPL-3.0-or-later; the rest is MIT.

[Unreleased]: https://github.com/choisam4u-creator/bonewright/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/choisam4u-creator/bonewright/releases/tag/v0.2.0
