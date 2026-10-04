"""명령줄 입력 검증 회귀 테스트."""
import io
import sys
import unittest
from unittest.mock import patch

from bonewright import cli


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
