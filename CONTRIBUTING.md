# Contributing

Thanks for looking. This project is small and opinionated; the rules below are what keep it honest.

## The one rule that matters

**Claims in the README and in commit messages must be backed by a number you actually measured.**
Not "improves accuracy" — `mannequiny 2.96 cm, 1.6% of height, unchanged`. If you could not measure it, say
you could not measure it. Failed attempts belong in `docs/ROADMAP.md` with the number that killed them; several
sections of that file exist only to stop the next person repeating an experiment that did not work. It is in Korean;
[Known gaps and failed attempts](docs/GUIDE.md#known-gaps-and-failed-attempts) in the guide is the English digest —
add a line there too when you record a new failure.

## Before you open a PR

```bash
python3 -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release tests.test_docs tests.test_i18n
                                             # the same list CI runs; Blender-dependent tests skip automatically
python3 -m unittest                          # short form: discovers the same seven modules
python3 scripts/check_license_boundary.py    # MIT core must not import bpy
```

The PR template (`.github/pull_request_template.md`) has a checklist for these and a table for the benchmark below.

The full suite needs Blender 5.2 (or the `bpy` wheel) and takes about six minutes. Without Blender you get only the
pure-Python tests (CI's `unit` jobs); CI's `blender` job installs the `bpy` wheel and runs everything.

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
- Issues: pick a template — *A rig came out wrong*, *Install or `bw doctor` problem*, *The documentation is wrong or
  unclear*, or *Feature request*. Usage
  questions go to [docs/GUIDE.md](docs/GUIDE.md) first; security reports go through [SECURITY.md](SECURITY.md).
- A comment should say **why**, and cite the measurement that made the code look like that. Avoid restating the code.
- No new tuning constant without a sentence saying what it was fitted on.

## What to work on

`docs/ROADMAP.md` ends with the open holes and what has already failed ([English digest](docs/GUIDE.md#known-gaps-and-failed-attempts)). The largest one today: motion retargeting
onto a `--from-shape` rig tears the mesh (max edge stretch 44x vs under 6x on the preset path) because the arm
chain starts inside the chest.

## What CI actually runs

Three jobs. `unit` (Linux, Python 3.11 and 3.13) and `unit-windows` install nothing but this package and run the
tests that do not need Blender — a green tick there means the Python imports and the license boundary holds,
nothing more. `blender` installs the `bpy` wheel and runs **every** test, including rig generation, skinning and
retargeting. If you change anything that touches weights,
that second job is the one that matters.

Locally, the command above runs the whole suite if Blender (or the `bpy` wheel) is on the machine, and quietly
skips the Blender half if it is not — so check the skip count before trusting a local pass:

```
Ran 199 tests ... OK (skipped=15)   ← the fifteen that matter did not run
```

Set `BW_REQUIRE_BLENDER=1` to make a missing Blender a failure instead of a skip.

A new test's docstring starts with one English line — `unittest -v` prints it next to the test name in the CI
log. A longer explanation (Korean is fine) goes after a blank line. `tests/test_docs.py` checks this.
