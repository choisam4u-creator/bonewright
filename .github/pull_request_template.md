<!--
Thanks for the PR. Fill in what applies and delete what does not.
See CONTRIBUTING.md — the one rule: every claim needs a number you actually measured.
-->

## What changed and why

<!-- One or two sentences. Link the issue if there is one. -->

## Measured

<!--
Numbers, not adjectives: `mannequiny 2.96 cm, 1.6% of height, unchanged`.
If you could not measure something, say so here.
-->

## Checks

- [ ] `python3 -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release tests.test_docs tests.test_i18n`
      — ran with Blender / `bpy`: yes / no (skipped count: __)
- [ ] `python3 scripts/check_license_boundary.py` — new Blender-side code is in `bonewright/bpy_scripts/` (GPL), not in the MIT core
- [ ] `CHANGELOG.md` → `[Unreleased]` updated if users will notice the change
- [ ] Docs updated if a `bw` command or flag changed (`tests/test_docs.py` checks the ones written in the docs)

## Joint code (only if you touched `analyze.py`, `fit_generate.py`, `_medial.py`, `from_skeleton.py` or `gates.py`)

`bw bench` mean joint error, before → after:

| asset | before (cm, % of height) | after (cm, % of height) |
|---|---|---|
| mannequiny | | |
| cesium_man | | |
| robot_expressive | | |
| quat_pp_41j | | |
