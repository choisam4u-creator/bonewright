"""오류 메시지 회귀 테스트: Blender 를 부르기 전에 막히고, 메시지에 '무엇을 바꾸면 되는지'(→)가 들어 있어야 한다. 블렌더 불필요."""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bonewright import cli, pipeline


class InputErrorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        lang = patch.dict(os.environ, {"BW_LANG": "ko"}); lang.start(); self.addCleanup(lang.stop)   # 문구 대조는 한국어로

    def tearDown(self):
        self.tmp.cleanup()

    def blocked(self, fn, *args, **kw) -> str:
        with patch.object(pipeline, "run_script", side_effect=AssertionError("Blender 를 부르면 안 된다")):
            with self.assertRaises(pipeline.Blocked) as cm:
                fn(*args, **kw)
        msg = str(cm.exception)
        self.assertIn("→", msg, msg)
        return msg

    def test_missing_mesh(self):
        msg = self.blocked(pipeline.rig, self.root, str(self.root / "없음.glb"), quiet=True)
        self.assertIn("메시 파일이 없다", msg)
        self.assertFalse((self.root / "runs").exists(), "빈 실행 폴더를 남기면 안 된다")

    def test_broken_settings_file(self):
        """runs/config.json 의 끝 쉼표가 '예상 못 한 오류 — 이슈를 열어라'로 끝나던 것(10/8 발견) → 줄·칸을 짚는 Blocked."""
        (self.root / "runs").mkdir()
        cfg = self.root / "runs" / "config.json"
        cfg.write_text('{"lang": "en",}', encoding="utf-8")
        msg = self.blocked(pipeline.rig, self.root, str(self.root / "a.glb"), quiet=True)
        self.assertIn("설정 파일이 JSON 이 아니다", msg)
        self.assertRegex(msg, r"1줄 1[45]칸")   # 끝 쉼표 위치: Python 3.11 은 15, 3.13 은 14
        cfg.write_text('["en"]', encoding="utf-8")
        self.assertIn("객체여야 한다", self.blocked(pipeline.rig, self.root, str(self.root / "a.glb"), quiet=True))

    def test_unknown_settings_key_warns(self):
        """runs/config.json 의 오타 키(`rig.cross_trimm`)를 조용히 받아 기본값으로 돌던 것(10/8 2회차) → 경고 한 줄, 멈추지는 않는다."""
        from bonewright import config
        (self.root / "runs").mkdir()
        cfg = self.root / "runs" / "config.json"
        cfg.write_text('{"lang": "en", "rig": {"cross_trimm": false, "face": true}, "blendr": {}, "models": {"fit": {"effort": "low"}}}', encoding="utf-8")
        self.assertEqual(config.unknown_keys(self.root), ["rig.cross_trimm (→ rig.cross_trim?)", "blendr (→ blender?)"])
        self.assertIn("rig.cross_trimm", config.unknown_keys_line(self.root))
        self.assertTrue(config.load(self.root)["rig"]["face"])   # 아는 키는 그대로 먹는다
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.blocked(pipeline.rig, self.root, str(self.root / "a.glb"))   # 메시가 없어 막혀도 경고는 먼저 나온다
        self.assertIn("rig.cross_trimm", err.getvalue())
        cfg.write_text('{"lang": "en", "rig": {"cross_trim": false}}', encoding="utf-8")
        self.assertIsNone(config.unknown_keys_line(self.root))
        cfg.write_text('{"lang": "en",}', encoding="utf-8")
        self.assertEqual(config.unknown_keys(self.root), [])   # 깨진 파일은 load 의 Blocked 가 맡는다

    def test_unsupported_mesh_format(self):
        f = self.root / "char.stl"; f.write_bytes(b"solid x")
        msg = self.blocked(pipeline.rig, self.root, str(f), quiet=True)
        self.assertIn(".glb", msg)

    def test_missing_targets_file(self):
        f = self.root / "char.glb"; f.write_bytes(b"glTF")
        msg = self.blocked(pipeline.rig, self.root, str(f), quiet=True, targets_file=str(self.root / "t.json"))
        self.assertIn("--targets", msg)

    def test_export_and_demo_without_rig(self):
        for fn in (pipeline.export_rig, pipeline.demo):
            with self.subTest(fn=fn.__name__):
                msg = self.blocked(fn, self.root, "rig-없는것", quiet=True)
                self.assertIn("bw rig", msg)
                self.assertIn("bw status", msg)

    def test_motion_without_source_or_missing_bvh(self):
        self.assertIn("--bvh", self.blocked(pipeline.motion, self.root, quiet=True))
        self.assertIn("BVH 파일이 없다", self.blocked(pipeline.motion, self.root, bvh=str(self.root / "w.bvh"), quiet=True))

    def test_bad_targets_json_leaves_no_run(self):
        f = self.root / "char.glb"; f.write_bytes(b"glTF")
        t = self.root / "t.json"; t.write_text("{oops", encoding="utf-8")
        self.assertIn("JSON", self.blocked(pipeline.rig, self.root, str(f), quiet=True, run_id="keep", targets_file=str(t)))
        self.assertFalse((self.root / "runs" / "keep").exists(), "형식 오류로 실행 폴더를 만들면 안 된다")

    def test_motion_missing_rig_checked_before_import(self):
        b = self.root / "w.bvh"; b.write_text("HIERARCHY", encoding="utf-8")
        msg = self.blocked(pipeline.motion, self.root, bvh=str(b), rig_run="없는리그", run_id="m1", quiet=True)
        self.assertIn("bw rig", msg)
        self.assertFalse((self.root / "runs" / "m1").exists(), "리그 확인 전에 동작 실행 폴더를 만들면 안 된다")

    def test_bad_bone_map(self):
        bad = self.root / "map.json"; bad.write_text("{oops", encoding="utf-8")
        self.assertIn("JSON", self.blocked(pipeline.apply_bone_map, {}, bad, []))
        wrong = self.root / "map2.json"; wrong.write_text(json.dumps(["LeftArm"]), encoding="utf-8")
        self.assertIn("LeftArm", self.blocked(pipeline.apply_bone_map, {}, wrong, []))

    def test_status_unknown_run(self):
        err = io.StringIO()
        with patch.object(cli, "ROOT", self.root), patch.object(sys, "argv", ["bw", "status", "nope"]), patch("sys.stderr", err):
            self.assertEqual(cli.main(), 2)
        self.assertIn("→", err.getvalue())


class UnexpectedErrorTests(unittest.TestCase):
    """포괄 except: 한 줄 메시지 대신 오류 종류·로그 위치·BW_DEBUG 안내가 나와야 한다."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        lang = patch.dict(os.environ, {"BW_LANG": "ko"}); lang.start(); self.addCleanup(lang.stop)   # 문구 대조는 한국어로

    def tearDown(self):
        self.tmp.cleanup()

    def run_bw(self, env: dict) -> str:
        def boom(root, *a, **kw):
            (root / "runs" / "rig-x" / "logs").mkdir(parents=True)
            return {}["없는 키"]
        err = io.StringIO()
        with patch.object(cli, "ROOT", self.root), patch.object(cli.pipeline, "rig", side_effect=boom), \
                patch.object(sys, "argv", ["bw", "rig", "m.glb"]), patch("sys.stderr", err), patch.dict("os.environ", env):
            self.assertEqual(cli.main(), 2)
        return err.getvalue()

    def test_default_points_at_logs_and_debug(self):
        with patch.dict(os.environ):
            os.environ.pop("BW_DEBUG", None)
            out = self.run_bw({})
        self.assertIn("BLOCKED: KeyError", out)
        self.assertIn(str(self.root / "runs" / "rig-x" / "logs"), out)
        self.assertIn("BW_DEBUG=1", out)
        self.assertNotIn("Traceback", out)

    def test_early_commands_also_reported(self):
        # bw status 처럼 파이프라인 전에 끝나는 명령도 같은 안내를 거친다(Codex 리뷰 #4 지적)
        d = self.root / "runs" / "rig-bad"; d.mkdir(parents=True)
        (d / "state.json").write_text("{잘림", encoding="utf-8")
        err = io.StringIO()
        with patch.object(cli, "ROOT", self.root), patch.object(sys, "argv", ["bw", "status", "rig-bad"]), \
                patch("sys.stderr", err), patch.dict(os.environ):
            os.environ.pop("BW_DEBUG", None)
            self.assertEqual(cli.main(), 2)
        self.assertIn("BLOCKED: JSONDecodeError", err.getvalue())
        self.assertIn("BW_DEBUG=1", err.getvalue())

    def test_debug_prints_traceback(self):
        out = self.run_bw({"BW_DEBUG": "1"})
        self.assertIn("Traceback", out)
        self.assertIn("KeyError", out)


class EnglishErrorTests(unittest.TestCase):
    """BW_LANG=en(또는 ko 가 아닌 로캘)이면 BLOCKED 메시지도 영어, 고칠 방법(→)은 그대로."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        lang = patch.dict(os.environ, {"BW_LANG": "en"}); lang.start(); self.addCleanup(lang.stop)
        self.addCleanup(self.tmp.cleanup)

    def blocked(self, fn, *args, **kw) -> str:
        with patch.object(pipeline, "run_script", side_effect=AssertionError("Blender 를 부르면 안 된다")):
            with self.assertRaises(pipeline.Blocked) as cm:
                fn(*args, **kw)
        msg = str(cm.exception)
        self.assertIn("→", msg, msg)
        self.assertNotRegex(msg, "[가-힣]", "영어 모드에 한국어가 섞였다")
        return msg

    def test_input_errors_in_english(self):
        self.assertIn("mesh file not found", self.blocked(pipeline.rig, self.root, str(self.root / "none.glb"), quiet=True))
        f = self.root / "char.stl"; f.write_bytes(b"solid x")
        self.assertIn("cannot read mesh format", self.blocked(pipeline.rig, self.root, str(f), quiet=True))
        self.assertIn("no rig result", self.blocked(pipeline.export_rig, self.root, "rig-none", quiet=True))
        self.assertIn("no motion source", self.blocked(pipeline.motion, self.root, quiet=True))
        bad = self.root / "map.json"; bad.write_text("{oops", encoding="utf-8")
        self.assertIn("not JSON", self.blocked(pipeline.apply_bone_map, {}, bad, []))

    def test_status_and_pin_in_english(self):
        err = io.StringIO()
        with patch.object(cli, "ROOT", self.root), patch.object(sys, "argv", ["bw", "status", "nope"]), patch("sys.stderr", err):
            self.assertEqual(cli.main(), 2)
        self.assertIn("no such run", err.getvalue())
        with patch.object(sys, "argv", ["bw", "rig", "m.glb", "--pin", "hand.L=a,b,c"]), patch.object(cli.pipeline, "rig") as rig:
            with self.assertRaises(SystemExit) as cm:
                cli.main()
        self.assertIn("coordinate error", str(cm.exception.code))
        rig.assert_not_called()

    def test_missing_blender_and_codex_in_english(self):
        # 파이프라인 밖(blender.py·codex.py)에서 올라오는 오류도 영어여야 한다(Codex 리뷰 PR #5)
        from bonewright import blender, codex
        with patch.object(blender, "find_blender", return_value=None), patch.object(blender, "has_bpy_module", return_value=False):
            with self.assertRaises(blender.BlenderError) as cm:
                blender.run_script("analyze", {}, {}, self.root / "logs")
        self.assertIn("Blender not found", str(cm.exception))
        self.assertNotRegex(str(cm.exception), "[가-힣]")
        with patch.object(codex.subprocess, "Popen", side_effect=FileNotFoundError("codex")), patch.dict(os.environ, {"BW_BACKEND": "codex"}):
            with self.assertRaises(codex.CodexError) as cm:
                codex.run_step("fit", "prompt", {}, {}, {"model": "m"}, {}, self.root / "logs")
        self.assertIn("codex executable not found", str(cm.exception))
        self.assertNotRegex(str(cm.exception), "[가-힣]")


class ReportPathTests(unittest.TestCase):
    """report.md 는 이슈에 그대로 붙인다(템플릿 'A rig came out wrong'). 실행 폴더 안 파일은 상대 경로로,
    밖의 파일은 홈 폴더를 `~` 로 적어 사용자 이름이 들어가지 않게 한다."""

    def test_inside_run_dir_is_relative(self):
        with tempfile.TemporaryDirectory() as d:
            run = Path(d) / "runs" / "r1"
            self.assertEqual("02_rigged.blend", pipeline._shown(run / "02_rigged.blend", run))
            self.assertEqual("motion/motion.bvh", pipeline._shown(str(run / "motion" / "motion.bvh"), run))

    def test_outside_run_dir_hides_home(self):
        with tempfile.TemporaryDirectory() as d, patch.object(Path, "home", return_value=Path(d) / "alice"):
            run = Path(d) / "work" / "runs" / "r1"
            mesh = Path(d) / "alice" / "models" / "hero.glb"
            self.assertEqual("~" + os.sep + os.path.join("models", "hero.glb"), pipeline._shown(mesh, run))
            self.assertEqual(str(Path(d) / "alicex.glb"), pipeline._shown(Path(d) / "alicex.glb", run))   # 이름이 겹칠 뿐인 형제 경로는 그대로


class KimodoPathTests(unittest.TestCase):
    """kimodo.cpp 원본이 빌드 폴더(build-release → build/release)와 텍스트 인코더(구성품 폴더 → GGUF 한 파일)를 바꿨다.
    옛 Mac 빌드와 지금 원본 안내대로 만든 것 둘 다 찾아야 한다."""
    K = {"text_bundle": "generated/llm2vec-text-bundle"}

    def test_nothing_built(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual((None, None), pipeline.kimodo_paths(Path(d), self.K))

    def test_old_layout(self):
        with tempfile.TemporaryDirectory() as d:
            k = Path(d); (k / "build-release").mkdir(); (k / "build-release" / "kmd-generate").write_text("")
            (k / "generated" / "llm2vec-text-bundle").mkdir(parents=True)
            self.assertEqual((k / "build-release" / "kmd-generate", k / "generated" / "llm2vec-text-bundle"),
                             pipeline.kimodo_paths(k, self.K))

    def test_current_upstream_layout_prefers_q8(self):
        with tempfile.TemporaryDirectory() as d:
            k = Path(d); (k / "build" / "release").mkdir(parents=True); (k / "build" / "release" / "kmd-generate").write_text("")
            (k / "models").mkdir(); (k / "models" / "kimodo-soma-rp-v1.1-f32.gguf").write_text("")   # 움직임 모델은 텍스트가 아니다
            t = k / "text"; t.mkdir()
            for name in ("tokenizer.gguf", "Llama-3-Kimodo-BF16.gguf", "Llama-3-Kimodo-Q8_0.gguf"):
                (t / name).write_text("")
            self.assertEqual((k / "build" / "release" / "kmd-generate", t / "Llama-3-Kimodo-Q8_0.gguf"),
                             pipeline.kimodo_paths(k, self.K))

    def test_missing_text_encoder_says_how_to_get_it(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {"BW_LANG": "en"}):
            root = Path(d); k = root / "vendor" / "kimodo.cpp" / "build" / "release"; k.mkdir(parents=True)
            (k / "kmd-generate").write_text("")
            with self.assertRaisesRegex(pipeline.Blocked, r"download_gguf_weights\.sh"):
                pipeline.motion(root, text="a person walks", quiet=True)


if __name__ == "__main__":
    unittest.main()
