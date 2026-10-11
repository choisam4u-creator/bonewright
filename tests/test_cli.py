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

    def test_bad_pin_is_an_input_error_with_a_pasteable_example(self):
        """A malformed --pin exits 2 like other input errors and gives a `→` example with the user's own bone name.

        10/11 10회차 실측: `--pin foo`·`--pin hand.L=1,2` 가 종료 1 에 `→` 없는 한 줄이었다(`--size 0` 은 종료 2)."""
        import re
        for lang, word in (("en", "e.g."), ("ko", "예")):
            for pin, bone in (("hand.L=1,2", "hand.L"), ("=0,0,1", "spine.004"), ("foo", "foo")):
                err = io.StringIO()
                with self.subTest(lang=lang, pin=pin), patch.dict(os.environ, {"BW_LANG": lang}), \
                        patch.object(sys, "argv", ["bw", "rig", "mesh.glb", "--pin", pin]), \
                        patch.object(cli.pipeline, "rig", side_effect=AssertionError("rig 를 부르면 안 된다")), patch("sys.stderr", err):
                    with self.assertRaises(SystemExit) as cm:
                        cli.main()
                    self.assertEqual(2, cm.exception.code)
                    m = re.search(rf"→ {word} (--pin \S+)", err.getvalue())
                    self.assertIsNotNone(m, err.getvalue())
                    self.assertTrue(m.group(1).startswith(f"--pin {bone}="))
                    # 예로 준 값은 그대로 받아들여진다
                    ns = cli.build_parser().parse_args(["rig", "mesh.glb", *m.group(1).split()])
                    self.assertIn(bone, dict(ns.pin))

    def test_accepts_finite_head_and_tail(self):
        with patch.object(sys, "argv", ["bw", "rig", "mesh.glb", "--pin", "hand.L=0,0,1/1,0,1"]), \
                patch.object(cli.pipeline, "rig", return_value="runs/r/report.md") as rig, \
                patch("sys.stdout", new_callable=io.StringIO), patch("sys.stderr", new_callable=io.StringIO):
            self.assertEqual(cli.main(), 0)
        self.assertEqual(rig.call_args.kwargs["pins"],
                         {"hand.L": {"head": [0.0, 0.0, 1.0], "tail": [1.0, 0.0, 1.0]}})


class EmptyHomeFirstCommandTests(unittest.TestCase):
    """With no runs yet, `bw status` and `bw demo`/`bw export` without an id give the README's first command as pasted.

    10/11 9회차 실측: 빈 BW_HOME 의 `bw status` 는 "start with `bw rig <mesh>`" 자리표시였고,
    7회차에 고친 인자 없는 `bw rig` 의 안내(저장소 캐릭터로 그대로 도는 명령)와 달랐다."""

    def test_first_command_runs_as_pasted(self):
        import re
        repo = Path(__file__).resolve().parents[1]
        readme = (repo / "README.md").read_text(encoding="utf-8")
        for lang in ("en", "ko"):
            for argv in (["bw", "status"], ["bw", "demo"], ["bw", "export"]):
                with self.subTest(lang=lang, argv=argv), tempfile.TemporaryDirectory() as d:
                    err = io.StringIO()
                    with patch.dict(os.environ, {"BW_LANG": lang}), patch.object(cli, "ROOT", Path(d)), \
                            patch.object(sys, "argv", argv), patch("sys.stderr", err), patch("sys.stdout", io.StringIO()):
                        cli.main()
                    cmd = re.search(r"`(bw rig (\S+\.glb)[^`]*)`", err.getvalue())
                    self.assertIsNotNone(cmd, err.getvalue())
                    self.assertIn(cmd[1], readme)
                    self.assertTrue((repo / cmd[2]).is_file(), cmd[2])
                    with patch.object(sys, "argv", cmd[1].split()), patch.object(cli.pipeline, "rig", return_value="runs/r/report.md") as rig, \
                            patch("sys.stdout", io.StringIO()), patch("sys.stderr", io.StringIO()):
                        self.assertEqual(0, cli.main())
                    self.assertTrue(rig.call_args.kwargs["from_skeleton"]); self.assertTrue(rig.call_args.kwargs["no_judge"])


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

    def test_bare_rig_ends_with_a_command_that_parses(self):
        """`bw rig` with no mesh ends with the README's first command, which parses and names a real file.

        10/10 7회차 실측: 사용법 7줄 + "required: mesh" 로 끝났다. 안내한 명령을 그대로 cli 에 넣어 본다."""
        import re
        for lang in ("en", "ko"):
            err = io.StringIO()
            with self.subTest(lang=lang), patch.dict(os.environ, {"BW_LANG": lang}), \
                    patch.object(sys, "argv", ["bw", "rig"]), patch("sys.stderr", err):
                with self.assertRaises(SystemExit) as cm:
                    cli.main()
                self.assertEqual(2, cm.exception.code)
                last = err.getvalue().splitlines()[-1]
                self.assertEqual(lang == "ko", bool(re.search("[가-힣]", last)), last)
                cmd = re.search(r"bw rig (\S+\.glb)[^(]*", last)
                self.assertIsNotNone(cmd, last)
                self.assertTrue((Path(__file__).resolve().parents[1] / cmd[1]).is_file(), cmd[1])
                readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
                self.assertIn(cmd[0].strip(), readme)
                with patch.object(sys, "argv", cmd[0].split()), patch.object(cli.pipeline, "rig", return_value="runs/r/report.md") as rig, \
                        patch("sys.stdout", io.StringIO()), patch("sys.stderr", io.StringIO()):
                    self.assertEqual(0, cli.main())
                self.assertTrue(rig.call_args.kwargs["from_skeleton"]); self.assertTrue(rig.call_args.kwargs["no_judge"])

    def test_bare_bench_points_at_fetch_script(self):
        """`bw bench` with no meshes ends with the fetch command and a folder to pass, both of which parse.

        10/10 7회차 실측: "required: meshes" 로 끝났다. 자산은 저장소에 없어 첫 사용자는 무엇을 넣을지 모른다."""
        import re
        root = Path(__file__).resolve().parents[1]
        for lang in ("en", "ko"):
            err = io.StringIO()
            with self.subTest(lang=lang), patch.dict(os.environ, {"BW_LANG": lang}), \
                    patch.object(sys, "argv", ["bw", "bench"]), patch("sys.stderr", err):
                with self.assertRaises(SystemExit) as cm:
                    cli.main()
                self.assertEqual(2, cm.exception.code)
                last = err.getvalue().splitlines()[-1]
                fetch, run = re.search(r"(python3 scripts/fetch_bench_assets\.py[^&]*)&& (bw bench \S+)$", last).groups()
                r = subprocess.run([sys.executable, *fetch.split()[1:], "--help"], cwd=root, capture_output=True, text=True, timeout=60)
                self.assertEqual(0, r.returncode, r.stderr)
                only = fetch.split()[fetch.split().index("--only") + 1]
                self.assertIn(only, r.stdout)
                self.assertTrue(run.endswith(f"/{only}"), run)   # 받은 하위 폴더를 그대로 넘긴다
                self.assertIn(run.split()[2].split("/")[0], r.stdout)   # --out 기본값(bench-assets)과 같은 폴더
                with patch.object(sys, "argv", run.split()), patch.object(cli.bench, "run", return_value="r.md"), \
                        patch("sys.stdout", io.StringIO()):
                    self.assertEqual(0, cli.main())


class PositiveNumberTests(unittest.TestCase):
    """`bw demo --size 0`·`--frames -1` 은 리그가 있으면 실행 폴더를 만들고 렌더까지 간 뒤 실패했고, `bw usage --days 0` 은
    빈 결과로 종료 0 이었다(10/10 7회차). 파서에서 1 이상만 받고, 그대로 고쳐 칠 수 있는 예를 준다."""

    def run_cli(self, argv, lang):
        err = io.StringIO()
        with patch.dict(os.environ, {"BW_LANG": lang}), patch.object(sys, "argv", ["bw", *argv]), \
             patch.object(cli.pipeline, "demo", side_effect=AssertionError("demo 를 부르면 안 된다")), \
             patch.object(cli.pipeline, "rig", side_effect=AssertionError("rig 를 부르면 안 된다")), \
             patch.object(cli, "summarize", side_effect=AssertionError("usage 를 세면 안 된다")), \
             patch("sys.stderr", err), patch("sys.stdout", new_callable=io.StringIO):
            with self.assertRaises(SystemExit) as cm:
                cli.main()
        self.assertEqual(2, cm.exception.code)
        return err.getvalue()

    def test_zero_and_negative_are_refused_with_an_example(self):
        for argv, example in ((["demo", "r1", "--size", "0"], "--size 640"), (["demo", "r1", "--frames", "-1"], "--frames 96"),
                              (["usage", "--days", "0"], "--days 30"), (["usage", "--days", "x"], "--days 30"),
                              (["rig", "m.glb", "--budget", "0"], "--budget 600000"), (["rig", "m.glb", "--budget", "-1"], "--budget 600000")):
            with self.subTest(argv=argv):
                en = self.run_cli(argv, "en")
                self.assertIn("must be a whole number of 1 or more", en); self.assertIn(f"e.g. {example}", en)
                self.assertIn("1 이상 정수", self.run_cli(argv, "ko"))
                # 안내한 예는 그대로 받아들여진다
                ns = cli.build_parser().parse_args([argv[0], *{"demo": ["r1"], "rig": ["m.glb"]}.get(argv[0], []), *example.split()])
                self.assertGreater(getattr(ns, example.split()[0].lstrip("-")), 0)


class BudgetHelpTests(unittest.TestCase):
    def test_budget_help_says_what_it_caps(self):
        """`bw rig --help` says what --budget caps (input tokens) and its default.

        `--budget` 는 `bw rig --help` 에 설명이 없었다 — 무엇의 상한인지(입력 토큰)와 기본값을 두 언어로."""
        from bonewright import config
        default = f"{config.DEFAULTS['budget']['max_input_tokens']:,}"
        for lang, word in (("en", "input tokens"), ("ko", "입력 토큰")):
            with self.subTest(lang=lang), patch.dict(os.environ, {"BW_LANG": lang}):
                rig = [a for a in cli.build_parser()._subparsers._group_actions[0].choices["rig"]._actions if "--budget" in a.option_strings][0]
                self.assertIn(word, rig.help); self.assertIn(default, rig.help)


class ArgumentHelpTests(unittest.TestCase):
    def test_every_argument_has_help_in_both_languages(self):
        """Every argument of every subcommand has a help line, and the English one has no Korean.

        10/10 8회차까지 21개(`bw rig` 의 mesh·--preset·--run-id·--budget·--quiet, `bw demo --size` 등)가 빈 칸이었다."""
        import re
        for lang in ("en", "ko"):
            with patch.dict(os.environ, {"BW_LANG": lang}):
                sub = cli.build_parser()._subparsers._group_actions[0]
                for name, sp in sub.choices.items():
                    for act in sp._actions:
                        with self.subTest(lang=lang, cmd=name, arg=act.dest):
                            self.assertTrue(act.help)
                            if lang == "en":
                                self.assertIsNone(re.search(r"[가-힣]", act.help), act.help)


class BadCommandTests(unittest.TestCase):
    def run_cli(self, word, lang):
        err = io.StringIO()
        with patch.dict(os.environ, {"BW_LANG": lang}), patch.object(sys, "argv", ["bw", word]), patch("sys.stderr", err):
            with self.assertRaises(SystemExit) as cm:
                cli.main()
        self.assertEqual(2, cm.exception.code)
        return err.getvalue()

    def test_typo_suggests_the_nearest_command(self):
        """A mistyped subcommand names the nearest real one, and the suggestion parses.

        argparse 기본 "invalid choice" 만 나오던 것(10/10 8회차 `bw resume nope`)."""
        import re
        for word, want in (("rigs", "rig"), ("statsu", "status"), ("exprot", "export")):
            with self.subTest(word=word):
                en = self.run_cli(word, "en")
                self.assertIn(f"did you mean `bw {want}`?", en)
                self.assertIn(f"혹시 `bw {want}`?", self.run_cli(word, "ko"))
                self.assertIsNone(re.search(r"[가-힣]", en))
        self.assertIn("all commands: `bw --help`", self.run_cli("xyz", "en"))

    def test_resume_explains_what_replaced_it(self):
        """`bw resume` (in old docs) says to rerun or reuse targets.json; the suggested command parses."""
        en = self.run_cli("resume", "en")
        self.assertIn("there is no `bw resume`", en)
        ns = cli.build_parser().parse_args(["rig", "m.glb", "--targets", "runs/r1/targets.json"])
        self.assertEqual("runs/r1/targets.json", ns.targets)
        self.assertIn("`bw rig <mesh> --targets runs/<id>/targets.json`", en)


class HelpDefaultTests(unittest.TestCase):
    def test_numbers_in_help_are_the_real_defaults(self):
        """A "default N" written into a help line equals the argument's real default (or config's, for --budget).

        10/10 8회차에 도움말 21개를 쓰며 숫자를 손으로 적었다 — 기본값이 바뀌면 도움말이 거짓말을 한다."""
        import os, re
        from bonewright import config
        real = {"--budget": config.DEFAULTS["budget"]["max_input_tokens"]}
        seen = 0
        for lang, word in (("en", "default"), ("ko", "기본")):
            with patch.dict(os.environ, {"BW_LANG": lang}):
                for name, sp in cli.build_parser()._subparsers._group_actions[0].choices.items():
                    for act in sp._actions:
                        for num in re.findall(rf"{word} ([\d,]+)", act.help or ""):
                            seen += 1
                            flag = (act.option_strings or [act.dest])[0]
                            with self.subTest(lang=lang, cmd=name, arg=flag):
                                self.assertEqual(real.get(flag, act.default), int(num.replace(",", "")))
        self.assertGreaterEqual(seen, 8)


class SkeletonSourceTests(unittest.TestCase):
    def test_from_skeleton_and_from_shape_are_exclusive(self):
        """`bw rig --from-skeleton --from-shape` stops at the parser (exit 2) and says what each does; rig is not called."""
        import os
        for lang, want in (("en", "pick one"), ("ko", "하나만 준다")):
            err = io.StringIO()
            with self.subTest(lang=lang), patch.dict(os.environ, {"BW_LANG": lang}), \
                    patch.object(sys, "argv", ["bw", "rig", "m.glb", "--from-skeleton", "--from-shape"]), \
                    patch.object(cli.pipeline, "rig", side_effect=AssertionError("rig 를 부르면 안 된다")), patch("sys.stderr", err):
                with self.assertRaises(SystemExit) as cm:
                    cli.main()
                self.assertEqual(2, cm.exception.code)
                self.assertIn(want, err.getvalue())
        self.assertTrue(cli.build_parser().parse_args(["rig", "m.glb", "--from-shape"]).from_shape)   # 하나만은 그대로 된다


class FacingHelpTests(unittest.TestCase):
    """`--facing` says how to choose neg-y / pos-y (help and the invalid-choice error only listed the values).

    10/11 9회차 실측: `bw rig x.glb --facing up` → 선택지 나열만, 도움말은 "-Y 로 맞춤" 뿐."""

    def test_help_and_bad_value_say_how_to_pick(self):
        import os
        for lang, want in (("en", "numpad 1"), ("ko", "숫자패드 1")):
            for cmd in ("rig", "bench"):
                err = io.StringIO()
                with self.subTest(lang=lang, cmd=cmd), patch.dict(os.environ, {"BW_LANG": lang}), \
                        patch.object(sys, "argv", ["bw", cmd, "m.glb", "--facing", "up"]), \
                        patch.object(cli.pipeline, "rig", side_effect=AssertionError("rig 를 부르면 안 된다")), patch("sys.stderr", err):
                    with self.assertRaises(SystemExit) as cm:
                        cli.main()
                    self.assertEqual(2, cm.exception.code)
                    self.assertIn("invalid choice", err.getvalue())
                    self.assertIn(want, err.getvalue()); self.assertIn("neg-y", err.getvalue().splitlines()[-1])
                    sp = cli.build_parser()._subparsers._group_actions[0].choices[cmd]
                    facing = next(a for a in sp._actions if "--facing" in a.option_strings)
                    self.assertIn(want, facing.help); self.assertIn("pos-y", facing.help)
        self.assertEqual("pos-y", cli.build_parser().parse_args(["rig", "m.glb", "--facing", "pos-y"]).facing)   # 맞는 값은 그대로


class PresetChoiceTests(unittest.TestCase):
    """A wrong `--preset` (dog) says which value four-legged animals take (it only listed the choices).

    10/11 10회차 실측: `bw rig x.glb --preset dog` → "invalid choice: 'dog'" 뿐."""

    def test_bad_preset_names_quadruped(self):
        import os
        for lang, want in (("en", "four-legged"), ("ko", "네 발")):
            for argv in (["rig", "m.glb"], ["bench", "m.glb"], ["motion", "--bvh", "m.bvh"]):
                err = io.StringIO()
                with self.subTest(lang=lang, cmd=argv[0]), patch.dict(os.environ, {"BW_LANG": lang}), \
                        patch.object(sys, "argv", ["bw", *argv, "--preset", "dog"]), patch("sys.stderr", err):
                    with self.assertRaises(SystemExit) as cm:
                        cli.main()
                    self.assertEqual(2, cm.exception.code)
                    last = err.getvalue().strip().splitlines()[-1]
                    self.assertIn(want, last); self.assertIn("quadruped", last)


class UnquotedPathTests(unittest.TestCase):
    """A path with spaces given without quotes gets the quoted command back (argparse only said "unrecognized arguments").

    10/11 10회차 실측: `bw rig my char.glb` → 종료 2·사용법·"unrecognized arguments: char.glb" 뿐."""

    def test_quoted_command_is_suggested_and_parses(self):
        import os
        import shlex
        for lang, want in (("en", "quote a path"), ("ko", "따옴표로 감싼다")):
            for argv, field, value in ((["rig", "my", "char.glb", "--no-judge"], "mesh", "my char.glb"),
                                       (["motion", "--bvh", "my", "wave.bvh", "--rig", "r1"], "bvh", "my wave.bvh")):
                with self.subTest(lang=lang, cmd=argv[0]), tempfile.TemporaryDirectory() as t:
                    (Path(t) / value).write_bytes(b"x")
                    err, cwd = io.StringIO(), os.getcwd()
                    os.chdir(t)
                    try:
                        with patch.dict(os.environ, {"BW_LANG": lang}), patch.object(sys, "argv", ["bw", *argv]), patch("sys.stderr", err):
                            with self.assertRaises(SystemExit) as cm:
                                cli.main()
                    finally:
                        os.chdir(cwd)
                    self.assertEqual(2, cm.exception.code)
                    last = err.getvalue().strip().splitlines()[-1]
                    self.assertIn(want, last)
                    cmd = shlex.split(last.split(": ", 1)[1])
                    self.assertEqual("bw", cmd[0])
                    self.assertEqual(value, getattr(cli.build_parser().parse_args(cmd[1:]), field))   # 그대로 붙여 넣으면 된다

    def test_no_hint_when_nothing_joins_into_a_file(self):
        import os
        err = io.StringIO()
        with patch.dict(os.environ, {"BW_LANG": "en"}), patch.object(sys, "argv", ["bw", "rig", "nothing", "here"]), patch("sys.stderr", err):
            with self.assertRaises(SystemExit):
                cli.main()
        self.assertNotIn("quote", err.getvalue())


class RunIdTests(unittest.TestCase):
    def test_run_ids_cannot_leave_runs_folder(self):
        """Every run-id argument refuses path separators and '..' (exit 2, with an example); normal ids still parse.

        10/11 11회차: `--run-id ../escape` 가 runs/ 밖에 폴더를 만들 수 있었고 `bw doctor --for-issue ../..` 는 runs/ 밖을 읽었다."""
        bad_cmds = [["rig", "m.glb", "--run-id", "{}"], ["motion", "--bvh", "w.bvh", "--run-id", "{}"], ["motion", "--bvh", "w.bvh", "--rig", "{}"],
                    ["bench", "a.glb", "--run-id", "{}"], ["export", "{}"], ["demo", "{}"], ["status", "{}"], ["doctor", "--for-issue", "{}"]]
        for cmd in bad_cmds:
            for rid in ("../escape", "a/b", "a\\b", "..", "has space"):
                err = io.StringIO()
                with self.subTest(cmd=cmd[0], rid=rid), patch.dict(os.environ, {"BW_LANG": "en"}), patch("sys.stderr", err):
                    with self.assertRaises(SystemExit) as cm:
                        cli.build_parser().parse_args([c.format(rid) for c in cmd])
                    self.assertEqual(2, cm.exception.code)
                    self.assertIn("→ e.g. hero-v2", err.getvalue())
        for rid in ("rig-20261010-101500", "hero-v2_1.0", "sc_wolf_skeleton", "캐릭터1"):
            self.assertEqual(rid, cli.build_parser().parse_args(["export", rid]).run_id)
        self.assertEqual("", cli.build_parser().parse_args(["doctor", "--for-issue"]).for_issue)


class HomeFolderTests(unittest.TestCase):
    def run_cli(self, home, *argv):
        err = io.StringIO()
        with patch.dict(os.environ, {"BW_LANG": "en", "BW_HOME": str(home)}), patch.object(cli, "ROOT", Path(home)), \
                patch.object(sys, "argv", ["bw", *argv]), patch("sys.stderr", err), patch("sys.stdout", io.StringIO()), \
                patch.object(cli.pipeline, "rig", side_effect=AssertionError("rig 를 부르면 안 된다")):
            code = cli.main()
        return code, err.getvalue()

    def test_bw_home_that_is_a_file_or_missing(self):
        """BW_HOME pointing at a file stops every command (exit 2); a missing BW_HOME is named by `bw status`.

        10/11 11회차: 파일이어도 `bw status` 가 "no runs yet (looked in <file>/runs)" 로 종료 0 이었다."""
        with tempfile.TemporaryDirectory() as t:
            f = Path(t) / "afile"; f.write_text("x")
            for argv in (["status"], ["rig", "m.glb"]):
                with self.subTest(argv=argv):
                    code, err = self.run_cli(f, *argv)
                    self.assertEqual(2, code); self.assertIn("BW_HOME is a file, not a folder", err)
            code, err = self.run_cli(Path(t) / "nope", "status")
            self.assertEqual(0, code); self.assertIn("BW_HOME does not exist", err)
            code, err = self.run_cli(Path(t), "status")
            self.assertNotIn("BW_HOME", err.split("no runs yet")[0])   # 있는 폴더면 조용하다


class MissingValueTests(unittest.TestCase):
    def test_option_without_value_gets_choices_or_an_example(self):
        """An option typed without its value lists its choices or a pasteable example (exit 2), and that example parses."""
        import os, re
        cases = ((["rig", "a.glb", "--facing"], "--facing pos-y"), (["rig", "a.glb", "--preset"], "--preset quadruped"),
                 (["rig", "a.glb", "--pin"], "--pin spine.004=0,0,1.42"), (["demo", "r1", "--size"], "--size 640"),
                 (["usage", "--days"], "--days 7"), (["rig", "a.glb", "--run-id"], "--run-id hero-v2"),
                 (["export", "r1", "--out"], "--out hero.glb"), (["motion", "--bvh"], "--bvh examples/wave.bvh"),
                 (["rig", "a.glb", "--targets"], "--targets runs/<id>/targets.json"), (["bench", "a.glb", "--gt-mesh"], "--gt-mesh original_tpose.glb"))
        for lang in ("en", "ko"):
            for argv, want in cases:
                err = io.StringIO()
                with self.subTest(lang=lang, argv=argv), patch.dict(os.environ, {"BW_LANG": lang}), patch("sys.stderr", err):
                    with self.assertRaises(SystemExit) as cm:
                        cli.build_parser().parse_args(argv)
                    self.assertEqual(2, cm.exception.code)
                    self.assertIn(want, err.getvalue())
                    cli.build_parser().parse_args(argv[:-1] + want.split())   # 안내한 값은 그대로 받아들여진다


class InterruptTests(unittest.TestCase):
    def test_ctrl_c_is_one_line_and_marks_the_run(self):
        """Ctrl-C during `bw rig` prints one line (no traceback), exits 130 and marks the run `interrupted`, not `running`."""
        import json, os
        with tempfile.TemporaryDirectory() as t:
            def fake_rig(root, *a, **k):
                from bonewright.config import DEFAULTS
                r = cli.pipeline.Run(Path(t), "r1", DEFAULTS, quiet=True)
                r.state("weights", "running")
                raise KeyboardInterrupt
            err = io.StringIO()
            with patch.dict(os.environ, {"BW_LANG": "en"}), patch.object(cli, "ROOT", Path(t)), \
                    patch.object(sys, "argv", ["bw", "rig", "m.glb"]), patch.object(cli.pipeline, "rig", fake_rig), \
                    patch.object(cli.pipeline.Run, "current", None), patch("sys.stderr", err):
                self.assertEqual(130, cli.main())
            state = json.loads((Path(t) / "runs" / "r1" / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(("weights", "interrupted"), (state["step"], state["status"]))
        self.assertIn("stopped (r1, step weights)", err.getvalue()); self.assertNotIn("Traceback", err.getvalue())


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
                self.assertEqual("a-good: gates done · " + ("input tokens 0" if lang == "en" else "입력 토큰 0"), lines[0])
                for line, rid in zip(lines[1:], ("b-nokey", "c-broken", "d-list")):
                    self.assertTrue(line.startswith(rid + ": state.json"), line)
                    self.assertIn(str(runs / rid), line)
                self.assertNotIn("BW_DEBUG", err.getvalue())


class StatusLineTests(unittest.TestCase):
    def test_failed_run_says_where_to_look(self):
        """A failed run's status line names the token count plainly and points at `bw doctor --for-issue <id>`, which parses.

        10/10 8회차: 목록 줄의 `· in 0` 이 무엇인지 안 보였고, 실패한 실행의 이유를 볼 곳이 없었다."""
        import os
        with tempfile.TemporaryDirectory() as t:
            runs = Path(t) / "runs"
            for rid, body in (("ok1", '{"step": "final", "status": "ok", "input_tokens": 1234}'),
                              ("bad1", '{"step": "analyze", "status": "failed", "input_tokens": 0}')):
                (runs / rid).mkdir(parents=True); (runs / rid / "state.json").write_text(body, encoding="utf-8")
            out = io.StringIO()
            with patch.dict(os.environ, {"BW_LANG": "en"}), patch.object(cli, "ROOT", Path(t)), \
                    patch.object(sys, "argv", ["bw", "status"]), patch("sys.stdout", out), patch("sys.stderr", io.StringIO()):
                self.assertEqual(0, cli.main())
        lines = out.getvalue().splitlines()
        self.assertEqual("bad1: analyze failed · input tokens 0  → why: `bw doctor --for-issue bad1`", lines[0])
        self.assertEqual("ok1: final ok · input tokens 1,234", lines[1])
        ns = cli.build_parser().parse_args(["doctor", "--for-issue", "bad1"])
        self.assertEqual("doctor", ns.cmd)


class StaleRunTests(unittest.TestCase):
    def test_running_with_a_dead_process_is_shown_as_stopped(self):
        """A run left `running` by a process that no longer exists is shown as stopped, with where to look."""
        import os
        with tempfile.TemporaryDirectory() as t:
            runs = Path(t) / "runs"
            for rid, pid in (("dead", 4_000_000), ("live", os.getpid())):
                (runs / rid).mkdir(parents=True)
                (runs / rid / "state.json").write_text(f'{{"step": "weights", "status": "running", "pid": {pid}}}', encoding="utf-8")
            out = io.StringIO()
            with patch.dict(os.environ, {"BW_LANG": "en"}), patch.object(cli, "ROOT", Path(t)), \
                    patch.object(sys, "argv", ["bw", "status"]), patch("sys.stdout", out), patch("sys.stderr", io.StringIO()):
                cli.main()
        lines = out.getvalue().splitlines()
        if os.name == "nt":   # Windows 는 pid 를 보지 않는다(os.kill 이 프로세스를 끝낸다)
            self.assertIn("dead: weights running", lines[0]); return
        self.assertEqual("dead: weights stopped (process gone) · input tokens 0  → why: `bw doctor --for-issue dead`", lines[0])
        self.assertEqual("live: weights running · input tokens 0", lines[1])


class StatusGuideTests(unittest.TestCase):
    def test_guide_example_line_is_what_bw_status_prints(self):
        """The `bw status` example line in docs/GUIDE.md is exactly what the command prints for that state."""
        import os, re
        guide = (Path(__file__).resolve().parents[1] / "docs" / "GUIDE.md").read_text(encoding="utf-8")
        m = re.search(r"`((rig-\d{8}-\d{6}): (\w+) (\w+) · input tokens ([\d,]+))`", guide)
        self.assertIsNotNone(m, "GUIDE 에 bw status 예시 줄이 없다")
        line, rid, step, status, tokens = m.groups()
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / "runs" / rid).mkdir(parents=True)
            (Path(t) / "runs" / rid / "state.json").write_text(
                f'{{"step": "{step}", "status": "{status}", "input_tokens": {tokens.replace(",", "")}}}', encoding="utf-8")
            out = io.StringIO()
            with patch.dict(os.environ, {"BW_LANG": "en"}), patch.object(cli, "ROOT", Path(t)), \
                    patch.object(sys, "argv", ["bw", "status"]), patch("sys.stdout", out), patch("sys.stderr", io.StringIO()):
                cli.main()
        self.assertEqual(line, out.getvalue().strip())


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

    def test_bad_settings_are_reported_not_fatal(self):
        """A settings problem (wrong type, BW_BACKEND typo) is one `[settings]` line; doctor still checks the rest and exits 1.

        10/11 11회차: 설정 검사를 넣자 `bw doctor`·`--for-issue` 가 그 설정 때문에 통째로 BLOCKED 로 끝나 신고 덩어리를 못 만들었다."""
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / "runs").mkdir(); (Path(t) / "runs" / "config.json").write_text('{"rig": {"cross_trim": "yes"}}', encoding="utf-8")
            with patch.object(cli, "ROOT", Path(t)):
                code, text = self.run_doctor(None, True, None, lang="en")
            self.assertEqual(1, code)
            self.assertIn("[settings] other commands will stop on this", text); self.assertIn("rig.cross_trim", text)
            self.assertIn("bpy module: found", text)   # 나머지 점검은 그대로
            with patch.object(cli, "ROOT", Path(t)), patch.dict("os.environ", {"BW_BACKEND": "moc"}):
                (Path(t) / "runs" / "config.json").unlink()
                code, text = self.run_doctor(None, True, None, lang="en")
            self.assertEqual(1, code); self.assertIn("BW_BACKEND='moc'", text)

    def test_says_which_model_path_is_active(self):
        """doctor says whether model calls are on (codex, the default, paid) or off (BW_BACKEND=mock)."""
        import os
        env = {k: v for k, v in os.environ.items() if k != "BW_BACKEND"}
        with patch.dict("os.environ", env, clear=True):
            _, text = self.run_doctor(None, True, None, lang="en")
        self.assertIn("model calls: codex (default)", text); self.assertIn("--no-judge", text)
        with patch.dict("os.environ", {"BW_BACKEND": "mock"}):
            _, text = self.run_doctor(None, True, None, lang="en")
        self.assertIn("model calls: none — BW_BACKEND=mock", text)

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

    def test_export_state_is_included(self):
        """A failed `bw export` writes export_state.json; the issue block carries it next to state.json, home scrubbed."""
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            self.make_run(root, "r1", ["rig ok"], 1000)
            (root / "runs" / "r1" / "export_state.json").write_text('{"step": "export_rig", "status": "failed", "out": "%s/a.glb"}' % Path.home())
            code, out, _ = self.run_report(root, "r1")
        self.assertEqual(0, code)
        self.assertIn("`export_state.json`", out); self.assertIn('"step": "export_rig"', out)
        self.assertIn('"out": "~/a.glb"', out)

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
