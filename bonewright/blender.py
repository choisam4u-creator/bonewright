"""Blender 실행기: bpy 모듈이 있으면 같은 프로세스에서 쓰지 않고(한 번만 import 가능) 항상 자식 프로세스로 돌린다.
우선순위: 설정한 app 경로 → PATH 의 blender → macOS Blender.app → bpy 휠이 깔린 파이썬(python -c)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).parent / "bpy_scripts"


class BlenderError(RuntimeError):
    pass


def find_blender(cfg: dict) -> list[str] | None:
    app = cfg.get("app") or os.environ.get("BW_BLENDER")
    if app and Path(app).exists():
        return [app]
    exe = shutil.which("blender")
    if exe:
        return [exe]
    mac = Path("/Applications/Blender.app/Contents/MacOS/Blender")
    if mac.exists():
        return [str(mac)]
    return None


def has_bpy_module(python: str = sys.executable) -> bool:
    r = subprocess.run([python, "-c", "import bpy"], capture_output=True, text=True)
    return r.returncode == 0


def run_script(name: str, params: dict, cfg: dict, log_dir: Path, mock: bool = False) -> dict:
    """bpy_scripts/<name>.py 를 Blender 로 실행하고 결과 JSON 을 돌려준다."""
    log_dir.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f"bw-{name}-"))
    params = {**params, "result": str(work / "result.json")}
    (work / "params.json").write_text(json.dumps(params, ensure_ascii=False), encoding="utf-8")
    script = SCRIPTS / f"{name}.py"
    boot = f"import sys, runpy; sys.path.insert(0, {str(SCRIPTS)!r}); runpy.run_path({str(script)!r}, run_name='__main__')"
    bl = find_blender(cfg)
    if bl:
        cmd = bl + ["-b", "--python-expr", boot]
    elif has_bpy_module():
        cmd = [sys.executable, "-c", boot]
    else:
        raise BlenderError("Blender 를 찾을 수 없다. Blender.app 을 설치하거나 `pip install bpy==5.2.2`(Python 3.13) 또는 BW_BLENDER 경로를 지정하라")
    env = {**os.environ, "BW_PARAMS": str(work / "params.json")}
    with open(log_dir / f"{name}.log", "w", encoding="utf-8") as log:
        proc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, text=True, timeout=cfg.get("timeout", 600), env=env, cwd=str(work))
    if proc.returncode != 0 or not (work / "result.json").exists():
        tail = (log_dir / f"{name}.log").read_text(encoding="utf-8", errors="replace")[-2000:]
        raise BlenderError(f"{name}: Blender 종료코드 {proc.returncode}\n{tail}")
    return json.loads((work / "result.json").read_text(encoding="utf-8"))
