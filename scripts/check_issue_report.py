"""설치본 `bw doctor --for-issue [RUN_ID]` 점검(CI 용, 블렌더 있어도 없어도 된다).

모의 시험(`tests/test_cli.py`)은 경로 치환 함수만 본다. 여기서는 설치된 `bw` 를 실제로 돌려
  - 종료코드가 0(Blender·bpy 있음) 또는 1(없음)이고 — 2 이상이나 traceback 이면 실패
  - 출력이 `<details>` … `</details>` 한 덩어리이며
  - 홈 폴더(`Path.home()`)·`/Users/<이름>`·`/home/<이름>`·`C:\\Users\\<이름>` 이 하나도 안 남았는지 본다.
CI 는 BW_HOME 을 홈 폴더 아래에 두고 돌린다 — 치환할 경로가 실제로 출력에 들어가야 시험이 된다.

    python scripts/check_issue_report.py [RUN_ID] [--expect-code 0]
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

PRIVATE = re.compile(r"(/Users/|/home/|[A-Za-z]:\\Users\\)[^/\\\s'\"~]")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_id", nargs="?")
    ap.add_argument("--expect-code", type=int, choices=[0, 1], help="종료코드를 이 값으로 못박는다(생략 시 0·1 모두 허용)")
    a = ap.parse_args()
    cmd = ["bw", "doctor", "--for-issue"] + ([a.run_id] if a.run_id else [])
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = p.stdout
    problems = []
    if p.returncode not in ((a.expect_code,) if a.expect_code is not None else (0, 1)):
        problems.append(f"exit code {p.returncode}")
    if "Traceback" in out + p.stderr:
        problems.append("traceback in output")
    if not (out.lstrip().startswith("<details>") and out.rstrip().endswith("</details>")):
        problems.append("output is not one <details> block")
    if a.run_id and f"run `{a.run_id}`" not in out:
        problems.append(f"run {a.run_id} missing")
    home = str(Path.home())
    if len(home) > 1 and home in out:
        problems.append(f"home folder left: {home}")
    problems += [f"private path left: {m.group(0)}…" for m in PRIVATE.finditer(out)]
    print(out)
    print(p.stderr, file=sys.stderr)
    if problems:
        print("FAIL:", "; ".join(problems), file=sys.stderr)
        return 1
    print(f"OK — `{' '.join(cmd)}` exit {p.returncode}, no home paths", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
