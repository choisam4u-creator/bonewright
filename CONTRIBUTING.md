# Contributing

Thanks for looking. This project is small and opinionated; the rules below are what keep it honest.

## The one rule that matters

**Claims in the README and in commit messages must be backed by a number you actually measured.**
Not "improves accuracy" — `mannequiny 2.96 cm, 1.6% of height, unchanged`. If you could not measure it, say
you could not measure it. Failed attempts belong in `docs/ROADMAP.md` with the number that killed them; several
sections of that file exist only to stop the next person repeating an experiment that did not work.

## Before you open a PR

```bash
python3 -m unittest tests.test_mock          # Blender-dependent tests skip automatically
python3 scripts/check_license_boundary.py    # MIT core must not import bpy
```

The full suite needs Blender 5.2 (or the `bpy` wheel) and takes about six minutes. Without Blender you get the
pure-Python tests, which is what CI runs.

If you touched anything in `analyze.py`, `fit_generate.py`, `_medial.py`, `from_skeleton.py` or `gates.py`, also
run the benchmark on at least `mannequiny`, `cesium_man`, `robot_expressive` and `quat_pp_41j` and paste the
before/after numbers into the PR. Those four catch most regressions. `scripts/fetch_bench_assets.py` downloads
the CC0 assets; they are never committed.

## License boundary

`bonewright/` is MIT. `bonewright/bpy_scripts/` is GPL-3.0-or-later because it imports `bpy`. CI fails if MIT
code imports a Blender module. Put new Blender-side code in `bpy_scripts/`, and keep the MIT side talking to it
through the JSON contract in `blender.run_script`.

## Style

- Comments and commit messages are written in Korean in this repository; English is fine in PRs and issues.
- A comment should say **why**, and cite the measurement that made the code look like that. Avoid restating the code.
- No new tuning constant without a sentence saying what it was fitted on.

## What to work on

`docs/ROADMAP.md` ends with the open holes and what has already failed. The largest one today: motion retargeting
onto a `--from-shape` rig tears the mesh (max edge stretch 44x vs under 6x on the preset path) because the arm
chain starts inside the chest.
