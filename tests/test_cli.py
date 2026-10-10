"""명령줄 입력 검증 회귀 테스트."""
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bonewright import blender, cli


class PinInputTests(unittest.TestCase):
    def test_rejects_malformed_pins_before_starting_rig(self):
        for pin in ("=0,0,1", "hand.L=0,0,1/1,0,1/2,0,1",
                    "hand.L=nan,0,1", "hand.L=0,inf,1"):
            with self.subTest(pin=pin), patch.object(sys, "argv", ["bw", "rig", "mesh.glb", "--pin", pin]), \
                    patch.object(cli.pipeline, "rig") as rig, patch("sys.stderr", new_callable=io.StringIO):
                with self.assertRaises(SystemExit):
                    cli.main()
                rig.assert_not_called()

    def test_accepts_finite_head_and_tail(self):
        with patch.object(sys, "argv", ["bw", "rig", "mesh.glb", "--pin", "hand.L=0,0,1/1,0,1"]), \
                patch.object(cli.pipeline, "rig", return_value="report") as rig, \
                patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(cli.main(), 0)
        self.assertEqual(rig.call_args.kwargs["pins"],
                         {"hand.L": {"head": [0.0, 0.0, 1.0], "tail": [1.0, 0.0, 1.0]}})


class PluginPathTests(unittest.TestCase):
    def test_plugin_path_points_at_real_plugin(self):
        out = io.StringIO()
        with patch.object(sys, "argv", ["bw", "plugin-path"]), patch("sys.stdout", out):
            self.assertEqual(cli.main(), 0)
        from pathlib import Path
        self.assertTrue((Path(out.getvalue().strip()) / ".codex-plugin" / "plugin.json").is_file())


class VersionTests(unittest.TestCase):
    def test_version_flag_prints_package_version(self):
        # 설치 문제 이슈 템플릿이 `bw --version` 출력을 요구한다
        out = io.StringIO()
        with patch.object(sys, "argv", ["bw", "--version"]), patch("sys.stdout", out):
            with self.assertRaises(SystemExit) as cm:
                cli.main()
        self.assertEqual(cm.exception.code, 0)
        self.assertEqual(out.getvalue().strip(), f"bonewright {cli.__version__}")


class BareCommandTests(unittest.TestCase):
    """A bare `bw` shows the command list and points at `bw doctor` (exit code stays 2).

    10/10 4회차 실측: argparse 의 `error: the following arguments are required: cmd` 한 줄로 끝났다."""

    def bare(self, lang: str) -> tuple[int, str]:
        import os
        err = io.StringIO()
        with patch.dict(os.environ, {"BW_LANG": lang}), patch.object(sys, "argv", ["bw"]), patch("sys.stderr", err):
            code = cli.main()
        return code, err.getvalue()

    def test_bare_bw_lists_commands_and_first_step(self):
        import re
        for lang in ("en", "ko"):
            with self.subTest(lang=lang):
                code, text = self.bare(lang)
                self.assertEqual(2, code)
                self.assertNotIn("required", text)
                for cmd in ("rig", "motion", "doctor", "status"):
                    self.assertIn(cmd, text)
                self.assertIn("`bw doctor`", text.splitlines()[-1])
                self.assertEqual(lang == "ko", bool(re.search("[가-힣]", text.splitlines()[-1])))


class EmptyStatusTests(unittest.TestCase):
    """`bw status` with no runs says where it looked and what to do (it printed nothing, exit 0).

    10/10 5회차 실측: 빈 출력은 설치가 깨졌는지 BW_HOME 이 다른지 구분이 안 된다."""

    def test_no_runs_names_the_folder_and_next_step(self):
        import os
        import re
        for lang in ("en", "ko"):
            with self.subTest(lang=lang), tempfile.TemporaryDirectory() as t:
                out, err = io.StringIO(), io.StringIO()
                with patch.dict(os.environ, {"BW_LANG": lang}), patch.object(cli, "ROOT", Path(t)), \
                        patch.object(sys, "argv", ["bw", "status"]), patch("sys.stdout", out), patch("sys.stderr", err):
                    self.assertEqual(0, cli.main())
                self.assertEqual("", out.getvalue())          # 실행 목록을 읽는 스크립트에는 여전히 빈 stdout
                self.assertIn(str(Path(t) / "runs"), err.getvalue())
                self.assertIn("`bw rig", err.getvalue()); self.assertIn("BW_HOME", err.getvalue())
                self.assertEqual(lang == "ko", bool(re.search("[가-힣]", err.getvalue())))


class BrokenStateTests(unittest.TestCase):
    """One unreadable state.json is reported on its own line; the other runs are still listed (exit 0).

    10/10 6회차 실측: `{"status":"running"}` 하나로 목록 전체가 `BLOCKED: KeyError: 'step'` 과 이슈 안내로 끝났다."""

    def test_bad_run_does_not_hide_the_others(self):
        import os
        for lang in ("en", "ko"):
            with self.subTest(lang=lang), tempfile.TemporaryDirectory() as t:
                runs = Path(t) / "runs"
                for rid, body in (("a-good", '{"step": "gates", "status": "done"}'), ("b-nokey", '{"status": "running"}'),
                                  ("c-broken", '{"step": '), ("d-list", "[]")):
                    (runs / rid).mkdir(parents=True); (runs / rid / "state.json").write_text(body, encoding="utf-8")
                out, err = io.StringIO(), io.StringIO()
                with patch.dict(os.environ, {"BW_LANG": lang}), patch.object(cli, "ROOT", Path(t)), \
                        patch.object(sys, "argv", ["bw", "status"]), patch("sys.stdout", out), patch("sys.stderr", err):
                    self.assertEqual(0, cli.main())
                lines = out.getvalue().splitlines()
                self.assertEqual(4, len(lines), out.getvalue())
                self.assertEqual("a-good: gates done · in 0", lines[0])
                for line, rid in zip(lines[1:], ("b-nokey", "c-broken", "d-list")):
                    self.assertTrue(line.startswith(rid + ": state.json"), line)
                    self.assertIn(str(runs / rid), line)
                self.assertNotIn("BW_DEBUG", err.getvalue())


class NextStepTests(unittest.TestCase):
    """A finished `bw rig` names the next commands with its run-id (stderr); stdout stays the report path.

    10/10 6회차: README 첫 실행 다음 줄이 `bw demo <run-id>` 인데 id 는 보고서 경로 안에만 있었다."""

    def test_rig_prints_next_commands_with_run_id(self):
        import os
        import re
        for lang in ("en", "ko"):
            with self.subTest(lang=lang), tempfile.TemporaryDirectory() as t:
                report = Path(t) / "runs" / "rig-20261010-120000" / "report.md"
                out, err = io.StringIO(), io.StringIO()
                with patch.dict(os.environ, {"BW_LANG": lang}), patch.object(cli, "ROOT", Path(t)), \
                        patch.object(cli.pipeline, "rig", return_value=report), \
                        patch.object(sys, "argv", ["bw", "rig", "x.glb"]), patch("sys.stdout", out), patch("sys.stderr", err):
                    self.assertEqual(0, cli.main())
                self.assertEqual(1, len(out.getvalue().splitlines()))
                self.assertTrue(out.getvalue().rstrip().endswith(str(report)))
                for cmd in ("demo", "export"):
                    self.assertIn(f"`bw {cmd} rig-20261010-120000`", err.getvalue())
                self.assertIn("--rig rig-20261010-120000`", err.getvalue())
                self.assertEqual(lang == "ko", bool(re.search("[가-힣]", err.getvalue())))
                for cmd in re.findall(r"`(bw [^`]+)`", err.getvalue()):   # 안내한 명령이 실제 argparse 에 맞는지
                    cli.build_parser().parse_args(re.sub(r"<[^>]+>", "w.bvh", cmd).split()[1:])


class EmptyUsageTests(unittest.TestCase):
    """`bw usage` with no model calls says so on stderr and names the ledger; the JSON on stdout is unchanged.

    10/10 5회차 실측: 0 만 든 JSON 은 '기록 안 됨' 인지 '안 썼음' 인지 모른다."""

    def run_usage(self, root: Path, lang: str) -> tuple[str, str]:
        import os
        out, err = io.StringIO(), io.StringIO()
        with patch.dict(os.environ, {"BW_LANG": lang}), patch.object(cli, "ROOT", root), \
                patch.object(sys, "argv", ["bw", "usage"]), patch("sys.stdout", out), patch("sys.stderr", err):
            self.assertEqual(0, cli.main())
        return out.getvalue(), err.getvalue()

    def test_empty_ledger_explains_the_zero(self):
        import json
        import re
        from bonewright import ledger
        for lang in ("en", "ko"):
            with self.subTest(lang=lang), tempfile.TemporaryDirectory() as t:
                out, err = self.run_usage(Path(t), lang)
                self.assertEqual(0, json.loads(out)["total"]["calls"])   # 스크립트가 읽는 stdout 은 JSON 그대로
                self.assertIn(str(ledger.path(Path(t))), err)
                self.assertIn("BW_HOME", err)                             # 장부 파일이 없으면 BW_HOME 을 의심하게
                self.assertIn("--from-skeleton", err); self.assertIn("--days", err)
                self.assertEqual(lang == "ko", bool(re.search("[가-힣]", err)))

    def test_ledger_with_calls_stays_quiet(self):
        import json
        from bonewright import ledger
        with tempfile.TemporaryDirectory() as t:
            ledger.append(Path(t), {"run_id": "r", "backend": "codex", "in": 10, "out": 2})
            out, err = self.run_usage(Path(t), "en")
            self.assertEqual(1, json.loads(out)["total"]["calls"])
            self.assertEqual("", err)


class HelpLanguageTests(unittest.TestCase):
    """bw --help 는 BW_LANG(없으면 로캘)을 따른다. README 는 영문이므로 영어가 기본."""

    def help_text(self, *args: str, lang: str) -> str:
        import os
        out = io.StringIO()
        env = {"BW_LANG": lang, "LANG": "C.UTF-8"}
        with patch.dict(os.environ, env), patch.object(sys, "argv", ["bw", *args, "--help"]), patch("sys.stdout", out):
            with self.assertRaises(SystemExit):
                cli.main()
        return out.getvalue()

    def test_english_help_has_no_hangul(self):
        import re
        for args in ((), ("rig",), ("motion",), ("export",), ("demo",), ("bench",)):
            with self.subTest(args=args):
                text = self.help_text(*args, lang="en")
                self.assertIsNone(re.search("[가-힣]", text), text)

    def test_korean_help_when_asked(self):
        self.assertIn("리깅", self.help_text(lang="ko"))



class ClosedPipeTests(unittest.TestCase):
    @unittest.skipIf(os.name == "nt", "a closed pipe is EINVAL, not EPIPE, on Windows")
    def test_output_flushed_into_a_closed_pipe_ends_quietly(self):
        """Buffered output flushed into an already-closed pipe ends quietly (the case CI hit, without the race).

        10/10 CI: 출력이 버퍼에 있다가 끝날 때 flush 에서 터져 'Exception ignored … BrokenPipeError' 가 났다.
        읽는 쪽을 먼저 닫은 파이프를 stdout 으로 두고 같은 프로세스에서 돌려 경쟁 없이 재현한다."""
        r, w = os.pipe(); os.close(r)
        out = open(w, "w", encoding="utf-8", buffering=1 << 16)
        err = io.StringIO()
        try:
            with tempfile.TemporaryDirectory() as t, patch.object(cli, "ROOT", Path(t)), patch.object(sys, "stdout", out), \
                    patch.object(sys, "argv", ["bw", "status"]), patch("sys.stderr", err):
                (Path(t) / "runs" / "a").mkdir(parents=True)
                (Path(t) / "runs" / "a" / "state.json").write_text('{"step": "done", "status": "ok"}', encoding="utf-8")
                code = cli.main()
        finally:
            try:
                out.close()
            except OSError:
                pass
        self.assertEqual(1, code)
        self.assertEqual("", err.getvalue())

    @unittest.skipIf(os.name == "nt", "a closed pipe is EINVAL, not EPIPE, on Windows")
    def test_reader_closing_early_is_not_an_error(self):
        """`bw doctor | head -1`: the reader closing early is not reported as an error or an issue to open.

        10/10 4회차 실측: `BLOCKED: BrokenPipeError` 와 이슈 템플릿 안내가 나왔다. 이슈 템플릿이 doctor 출력을
        붙이라 해서 `| head`·`| pbcopy` 로 자주 돈다."""
        for argv in (["doctor"], ["status"], ["--version"]):
            with self.subTest(argv=argv), tempfile.TemporaryDirectory() as t:
                env = {**os.environ, "BW_HOME": t, "BW_LANG": "en", "PYTHONPATH": str(Path(__file__).resolve().parent.parent)}
                p = subprocess.Popen([sys.executable, "-c", "import sys; from bonewright.cli import main; sys.exit(main())", *argv],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
                p.stdout.close()          # head 처럼 아무것도 안 읽고 닫는다
                err = p.stderr.read().decode("utf-8", "replace"); p.wait(timeout=60); p.stderr.close()
                # 10/10 CI: doctor 가 끝난 뒤 인터프리터의 마지막 flush 에서 'Exception ignored … BrokenPipeError' 가 났다
                self.assertNotIn("BrokenPipe", err)
                self.assertNotIn("open an issue", err)
                self.assertNotIn("Traceback", err)

if __name__ == "__main__":
    unittest.main()


class DoctorTests(unittest.TestCase):
    """codex·kimodo.cpp 는 선택이다: 없어도 Blender 나 bpy 만 있으면 종료코드 0."""

    def run_doctor(self, blender, bpy, codex, lang="ko"):
        out = io.StringIO()
        with patch.dict("os.environ", {"BW_LANG": lang}), \
                patch.object(cli, "find_blender", return_value=blender), \
                patch.object(cli, "has_bpy_module", return_value=bpy), \
                patch.object(cli.shutil, "which", return_value=codex), \
                patch.object(cli.subprocess, "run") as run, patch("sys.stdout", out):
            run.return_value.stdout = "Blender 5.2.0\n"; run.return_value.stderr = ""
            code = cli.doctor()
        return code, out.getvalue()

    def test_bpy_without_codex_is_ready(self):
        code, text = self.run_doctor(None, True, None)
        self.assertEqual(code, 0)
        self.assertIn("[선택] codex CLI: 없음", text)
        self.assertIn("준비됨", text)

    def test_no_blender_and_no_bpy_fails(self):
        code, text = self.run_doctor(None, False, "/usr/bin/codex")
        self.assertEqual(code, 1)
        self.assertIn("[필수: 둘 중 하나]", text)

    def test_english_output(self):
        code, text = self.run_doctor(["/opt/blender"], False, None, lang="en")
        self.assertEqual(code, 0)
        self.assertIn("[optional] codex CLI: not found", text)
        self.assertNotIn("없음", text)

    def test_blender_and_bpy_are_marked_one_of_on_each_line(self):
        """Blender and bpy each say "one of", and the one not needed is marked so (Korean and English).

        10/10 5회차 실측: 둘 다 `[required]` 로 찍혀 둘 다 깔아야 하는 줄 알았다(마지막 줄에서야 "either one")."""
        for lang, either, unneeded in (("ko", "[필수: 둘 중 하나]", "[필요 없음]"), ("en", "[required: one of]", "[not needed]")):
            with self.subTest(lang=lang, case="neither"):
                code, text = self.run_doctor(None, False, None, lang=lang)
                lines = text.splitlines()
                self.assertEqual(code, 1)
                self.assertTrue(lines[0].startswith(either + " Blender:"), lines[0])
                self.assertTrue(lines[1].startswith(either + " bpy"), lines[1])
                self.assertNotIn(unneeded, text)
            with self.subTest(lang=lang, case="bpy only"):
                code, text = self.run_doctor(None, True, None, lang=lang)
                lines = text.splitlines()
                self.assertEqual(code, 0)
                self.assertTrue(lines[0].startswith(unneeded + " Blender:"), lines[0])
                self.assertTrue(lines[1].startswith(either + " bpy"), lines[1])
            with self.subTest(lang=lang, case="Blender app"):
                code, text = self.run_doctor(["/opt/blender"], False, None, lang=lang)
                self.assertEqual(code, 0)
                self.assertIn(either + " Blender: /opt/blender", text)
                self.assertIn(unneeded + " bpy", text)


class IssueReportTests(unittest.TestCase):
    """`bw doctor --for-issue [RUN_ID]`: 이슈에 붙일 덩어리. 개인 경로는 ~ 로, 실행 하나의 state.json·로그 꼬리를 싣는다."""

    def run_report(self, root, *args, lang="en"):
        out, err = io.StringIO(), io.StringIO()
        with patch.dict("os.environ", {"BW_LANG": lang}), patch.object(cli, "ROOT", root), \
                patch.object(cli, "doctor", side_effect=lambda **kw: print("[required] Blender: /Users/someone/Blender.app") or 0), \
                patch.object(sys, "argv", ["bw", "doctor", "--for-issue", *args]), \
                patch("sys.stdout", out), patch("sys.stderr", err):
            code = cli.main()
        return code, out.getvalue(), err.getvalue()

    def make_run(self, root, rid, log_lines, mtime):
        import os
        d = root / "runs" / rid / "logs"; d.mkdir(parents=True)
        (d.parent / "state.json").write_text('{"step": "rig", "status": "failed", "mesh": "%s/x.glb"}' % Path.home())
        (d / "rig.log").write_text("\n".join(log_lines))
        os.utime(d.parent / "state.json", (mtime, mtime))

    def test_latest_run_log_tail_and_paths_scrubbed(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            self.make_run(root, "old", ["old"], 1000)
            self.make_run(root, "new", [f"line {i}" for i in range(100)], 2000)
            code, out, err = self.run_report(root)
        self.assertEqual(code, 0)
        self.assertIn(f"bonewright {cli.__version__}", out)
        self.assertIn("run `new`", out)
        self.assertIn("line 99", out); self.assertIn("line 60", out); self.assertNotIn("line 59", out)
        self.assertIn('"mesh": "~/x.glb"', out)
        self.assertIn("Blender: ~/Blender.app", out)
        self.assertNotIn("/Users/", out)
        self.assertIn("paste the block", err)

    def test_named_run_and_missing_run(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            self.make_run(root, "a", ["from a"], 1000)
            self.make_run(root, "b", ["from b"], 2000)
            code, out, _ = self.run_report(root, "a")
            self.assertEqual(code, 0); self.assertIn("from a", out); self.assertNotIn("from b", out)
            code, out, err = self.run_report(root, "nope")
            self.assertEqual(code, 2); self.assertIn("bw status", err)

    def test_no_runs(self):
        with tempfile.TemporaryDirectory() as t:
            code, out, _ = self.run_report(Path(t), lang="ko")
        self.assertEqual(code, 0)
        self.assertIn("실행 기록 없음", out)

    def test_settings_file_included_with_unknown_keys(self):
        """The issue report includes the settings file (home as ~) and one line per unknown key.

        설정이 원인인 이슈는 설정 없이 재현이 안 된다 — 내용(홈 경로는 ~)과 모르는 키 한 줄을 싣는다."""
        with tempfile.TemporaryDirectory() as t:
            root = Path(t); (root / "runs").mkdir()
            # json.dumps 로 쓴다: Windows 홈 경로를 문자열에 그대로 끼우면 역슬래시가 JSON 이스케이프로 깨진다(10/9 CI)
            (root / "runs" / "config.json").write_text(json.dumps(
                {"lang": "en", "rig": {"cross_trimm": False}, "kimodo": {"root": str(Path.home() / "kimodo")}}))
            code, out, _ = self.run_report(root)
        self.assertEqual(code, 0)
        self.assertIn("`runs/config.json`", out); self.assertIn('"lang": "en"', out)
        self.assertIn('"root": "~', out); self.assertNotIn(str(Path.home()), out)
        self.assertIn("unknown keys (ignored): rig.cross_trimm (→ rig.cross_trim?)", out)

    def test_unknown_key_warned_once(self):
        """An unknown settings key is warned about once, in the settings section only.

        10/9 설치본 출력: 모르는 키가 doctor 의 경고 줄과 설정 절 줄로 두 번 나왔다 → 설정 절에만 한 번.
        여기서는 doctor 를 가짜로 바꾸지 않는다(가짜 doctor 는 경고를 안 찍어 중복이 안 보인다)."""
        with tempfile.TemporaryDirectory() as t:
            root = Path(t); (root / "runs").mkdir()
            (root / "runs" / "config.json").write_text('{"rig": {"cross_trimm": false}}')
            out, err = io.StringIO(), io.StringIO()
            with patch.dict("os.environ", {"BW_LANG": "en"}), patch.object(cli, "ROOT", root), \
                    patch.object(cli, "find_blender", return_value=None), patch.object(cli, "has_bpy_module", return_value=True), \
                    patch.object(cli.shutil, "which", return_value=None), \
                    patch.object(sys, "argv", ["bw", "doctor", "--for-issue"]), patch("sys.stdout", out), patch("sys.stderr", err):
                self.assertEqual(cli.main(), 0)
            self.assertEqual(out.getvalue().count("rig.cross_trimm (→"), 1, out.getvalue())
            self.assertIn("unknown keys (ignored): rig.cross_trimm", out.getvalue())
            plain = io.StringIO()   # 그냥 `bw doctor` 는 경고 줄을 그대로 찍는다
            with patch.dict("os.environ", {"BW_LANG": "en"}), patch.object(cli, "ROOT", root), \
                    patch.object(cli, "find_blender", return_value=None), patch.object(cli, "has_bpy_module", return_value=True), \
                    patch.object(cli.shutil, "which", return_value=None), patch("sys.stdout", plain):
                cli.doctor()
            self.assertIn("rig.cross_trimm", plain.getvalue())

    def test_no_settings_file_says_defaults(self):
        with tempfile.TemporaryDirectory() as t:
            code, out, _ = self.run_report(Path(t))
        self.assertIn("no runs/config.json", out)

    def test_broken_settings_file_still_shown(self):
        """A broken runs/config.json is still included verbatim and the report does not stop.

        깨진 JSON 도 그대로 싣는다(원인일 수 있다). 보고서 자체는 멈추지 않는다."""
        with tempfile.TemporaryDirectory() as t:
            root = Path(t); (root / "runs").mkdir()
            (root / "runs" / "config.json").write_text('{"lang": "en",}')
            code, out, _ = self.run_report(root)
        self.assertEqual(code, 0); self.assertIn('{"lang": "en",}', out)
        self.assertTrue(out.rstrip().endswith("</details>"))

    def test_scrub_windows_and_other_users(self):
        self.assertEqual(cli.scrub(r"C:\Users\kim\x.glb /home/lee/y /Users/park/z"), r"~\x.glb ~/y ~/z")

    def test_scrub_json_escaped_windows_home(self):
        """A JSON-escaped Windows home (C:\\Users\\<name>) in the settings file is replaced with ~.

        runs/config.json 안의 Windows 경로는 역슬래시가 둘씩(`C:\\\\Users\\\\kim`)이라 홈 치환을 비켜 갔다(10/9 CI)."""
        with patch.object(cli.Path, "home", return_value=cli.Path("C:\\Users\\kim")):
            self.assertEqual(cli.scrub('{"root": "C:\\\\Users\\\\kim\\\\kimodo"}'), '{"root": "~\\\\kimodo"}')
        self.assertEqual(cli.scrub('"D:\\\\Users\\\\lee\\\\x"'), '"~\\\\x"')
        import importlib.util
        spec = importlib.util.spec_from_file_location("cir", cli.Path(__file__).resolve().parent.parent / "scripts" / "check_issue_report.py")
        cir = importlib.util.module_from_spec(spec); spec.loader.exec_module(cir)
        self.assertTrue(cir.PRIVATE.search('"C:\\\\Users\\\\kim\\\\x"'))   # CI 점검도 이 꼴을 잡는다


class FindBlenderWindowsTests(unittest.TestCase):
    """Windows 설치 관리자 경로(`Program Files\\Blender Foundation\\Blender X.Y`)를 찾고, 여러 판이면 가장 높은 것."""

    def env(self, d):
        return {"ProgramFiles": d, "ProgramW6432": "", "ProgramFiles(x86)": ""}

    def test_picks_highest_version_under_program_files(self):
        with tempfile.TemporaryDirectory() as d:
            for ver in ("4.5", "5.2", "5.10"):
                exe = Path(d) / "Blender Foundation" / f"Blender {ver}" / "blender.exe"
                exe.parent.mkdir(parents=True); exe.touch()
            (Path(d) / "Blender Foundation" / "Blender 9.9").mkdir()   # blender.exe 없는 폴더는 무시
            with patch.dict("os.environ", self.env(d)):
                found = blender._windows_blender()
        self.assertIsNotNone(found)
        self.assertEqual(found.parent.name, "Blender 5.10")

    def test_none_when_nothing_installed(self):
        with tempfile.TemporaryDirectory() as d, patch.dict("os.environ", self.env(d)):
            self.assertIsNone(blender._windows_blender())
