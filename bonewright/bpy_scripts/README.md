# `bpy_scripts/` — GPL-3.0-or-later

Everything in this directory `import bpy` and runs inside Blender. The Blender Foundation's position is that
Python code using the `bpy` API is a derivative work of Blender and must be GPL-compatible, so this directory
is licensed **GPL-3.0-or-later** (`LICENSE` in this folder), not MIT like the rest of the repository.

The split is deliberate and matches `addon/README.md`:

| part | license | why |
|---|---|---|
| `bonewright/` (CLI, pipeline, gates, bench, retarget mapping) | MIT | plain Python, never imports `bpy` |
| `bonewright/bpy_scripts/` | GPL-3.0-or-later | imports `bpy`, executed by Blender |
| `addon/` (planned bridge add-on) | GPL-3.0-or-later | same reason |

The CLI talks to these scripts by running `Blender -b --python-expr …` in a child process and reading a JSON
result file — a process boundary, not a library link.

This note is a reading of the Blender Foundation's published position, not legal advice.
