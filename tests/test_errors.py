"""오류 메시지 회귀 테스트: Blender 를 부르기 전에 막히고, 메시지에 '무엇을 바꾸면 되는지'(→)가 들어 있어야 한다. 블렌더 불필요."""
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

    def test_debug_prints_traceback(self):
        out = self.run_bw({"BW_DEBUG": "1"})
        self.assertIn("Traceback", out)
        self.assertIn("KeyError", out)


if __name__ == "__main__":
    unittest.main()
