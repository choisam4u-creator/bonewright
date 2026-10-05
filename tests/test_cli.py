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
