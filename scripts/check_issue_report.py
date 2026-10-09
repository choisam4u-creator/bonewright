"""설치본 `bw doctor --for-issue [RUN_ID]` 점검(CI 용, 블렌더 있어도 없어도 된다).

모의 시험(`tests/test_cli.py`)은 경로 치환 함수만 본다. 여기서는 설치된 `bw` 를 실제로 돌려
  - 종료코드가 0(Blender·bpy 있음) 또는 1(없음)이고 — 2 이상이나 traceback 이면 실패
  - 출력이 `<details>` … `</details>` 한 덩어리이며
  - 홈 폴더(`Path.home()`)·`/Users/<이름>`·`/home/<이름>`·`C:\\Users\\<이름>` 이 하나도 안 남았는지 본다.
CI 는 BW_HOME 을 홈 폴더 아래에 두고 돌린다 — 치환할 경로가 실제로 출력에 들어가야 시험이 된다.

    python scripts/check_issue_report.py [RUN_ID] [--expect-code 0] [--expect-config]
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bonewright.i18n import T  # noqa: E402  화면 언어(BW_LANG·로캘)를 따른다

PRIVATE = re.compile(r"(/Users/|/home/|[A-Za-z]:\\{1,2}Users\\{1,2})[^/\\\s'\"~]")


def main() -> int:
    ap = argparse.ArgumentParser(description=T(
        "설치본 `bw doctor --for-issue` 를 돌려 한 덩어리 출력·종료코드·개인 경로 치환을 점검한다(CI 용).",
        "Run the installed `bw doctor --for-issue` and check its single block, exit code and private-path replacement (for CI)."))
    ap.add_argument("run_id", nargs="?", help=T("점검할 실행(생략하면 최근 실행)", "run to include (default: the latest run)"))
    ap.add_argument("--expect-config", action="store_true",
                    help=T("runs/config.json 이 있다 — 그 절과 모르는 키 줄이 실렸는지 본다",
                           "runs/config.json exists — check that its section and the unknown-keys line are there"))
    ap.add_argument("--expect-code", type=int, choices=[0, 1],
                    help=T("종료코드를 이 값으로 못박는다(생략 시 0·1 모두 허용)", "require this exit code (default: 0 or 1)"))
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
    if a.expect_config and not ("`runs/config.json`" in out and "unknown keys (ignored)" in out):
        problems.append("runs/config.json section or its unknown-keys line missing")
    home = str(Path.home())
    if len(home) > 1 and home in out:
        problems.append(f"home folder left: {home}")
    problems += [f"private path left: {m.group(0)}…" for m in PRIVATE.finditer(out)]
    print(out)
    print(p.stderr, file=sys.stderr)
    if problems:
        print("FAIL:", "; ".join(problems), file=sys.stderr)
        print(T("  → 개인 경로가 남았으면 bonewright/cli.py 의 scrub() 이 그 꼴을 `~` 로 바꾸게 고친다. 나머지는 위 출력에서 "
                "bw doctor --for-issue 가 무엇을 찍었는지 본다(BW_DEBUG=1 로 다시 돌리면 traceback 이 나온다)",
                "  → if a private path is left, teach scrub() in bonewright/cli.py to turn that form into `~`. Otherwise read "
                "what bw doctor --for-issue printed above (rerun with BW_DEBUG=1 for the traceback)"), file=sys.stderr)
        return 1
    print(f"OK — `{' '.join(cmd)}` exit {p.returncode}, no home paths", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
