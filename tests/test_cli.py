"""명령줄 입력 검증 회귀 테스트."""
import io
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
        self.assertIn("[필수]", text)

    def test_english_output(self):
        code, text = self.run_doctor(["/opt/blender"], False, None, lang="en")
        self.assertEqual(code, 0)
        self.assertIn("[optional] codex CLI: not found", text)
        self.assertNotIn("없음", text)


class IssueReportTests(unittest.TestCase):
    """`bw doctor --for-issue [RUN_ID]`: 이슈에 붙일 덩어리. 개인 경로는 ~ 로, 실행 하나의 state.json·로그 꼬리를 싣는다."""

    def run_report(self, root, *args, lang="en"):
        out, err = io.StringIO(), io.StringIO()
        with patch.dict("os.environ", {"BW_LANG": lang}), patch.object(cli, "ROOT", root), \
                patch.object(cli, "doctor", side_effect=lambda: print("[required] Blender: /Users/someone/Blender.app") or 0), \
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

    def test_scrub_windows_and_other_users(self):
        self.assertEqual(cli.scrub(r"C:\Users\kim\x.glb /home/lee/y /Users/park/z"), r"~\x.glb ~/y ~/z")


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
