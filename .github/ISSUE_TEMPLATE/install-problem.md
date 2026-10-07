---
name: Install or `bw doctor` problem
about: bw will not start, cannot find Blender / bpy / codex, or stops with BLOCKED before rigging anything
labels: install
---

**What `bw doctor --for-issue` prints**, in full (versions, OS, Blender or the `bpy` wheel, the codex CLI and its
login, kimodo.cpp, the working folder, and the latest run's state and log tail; home paths are already shown as `~`).
Check it once for anything private before pasting.

```
paste here
```

**Your setup.**
- OS and CPU (e.g. macOS 15 arm64, Ubuntu 24.04 x86_64, Windows 11 — Windows is untested):
- `python3 --version`:
- `bw --version`:
- How you installed: `pip install .` / `pip install ".[headless]"` / editable / other:
- Blender: Blender.app (which version) / `bpy` wheel (which version) / `BW_BLENDER` set to:

**The command and its full output**, including the `BLOCKED:` line and the `→` hint under it. If the message was not
clear, rerun with `BW_DEBUG=1` in front of the command and paste the traceback too.

**What you already tried** (the `→` hint, reinstalling, another Blender version).
