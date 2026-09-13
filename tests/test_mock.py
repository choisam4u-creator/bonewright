"""mock 백엔드 + 절차적 휴머노이드로 rig 파이프라인 전체를 검증한다. Blender(app 또는 bpy 휠) 필요, Codex 토큰 0."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bonewright import blender, gates, pipeline  # noqa: E402


@unittest.skipUnless(blender.find_blender({}) or blender.has_bpy_module(), "Blender 없음")
class RigMockTests(unittest.TestCase):
    def setUp(self):
        os.environ["BW_BACKEND"] = "mock"
        self.tmp = Path(tempfile.mkdtemp(prefix="bw-test-"))
        self.mesh = self.tmp / "test_humanoid.glb"
        r = blender.run_script("make_test_mesh", {"out": str(self.mesh)}, {}, self.tmp / "logs")
        self.assertGreater(r["verts"], 500)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_rig_pipeline_passes_gates(self):
        out = pipeline.rig(self.tmp, str(self.mesh), "humanoid", run_id="t1", quiet=True)
        self.assertTrue(out.exists())
        st = json.loads((self.tmp / "runs/t1/rig_stats.json").read_text())["stats"]
        self.assertGreaterEqual(st["deform_bones"], 60)
        self.assertEqual(0, st["unweighted_verts"])
        self.assertEqual("auto", st["weight_method"], st)
        self.assertEqual([], st["bones_outside_bbox"])
        state = json.loads((self.tmp / "runs/t1/state.json").read_text())
        self.assertEqual("ok", state["status"], (self.tmp / "runs/t1/report.md").read_text())
        for v in ("front", "side", "iso"):
            self.assertTrue((self.tmp / f"runs/t1/view_{v}.png").exists())
        self.assertIn("targets", json.loads((self.tmp / "runs/t1/fit.json").read_text()))
        self.assertEqual(0, st["deform_outside_mesh"], st.get("deform_outside_mesh_bones"))   # 변형 본 끝점이 메시 표면 밖에 없어야 한다
        # 데모 영상(짧게): IK 컨트롤이 존재하고 mp4 가 만들어진다
        video = pipeline.demo(self.tmp, "t1", quiet=True, size=128, frames=16)
        self.assertTrue(video.exists(), video)   # ffmpeg 있으면 demo.mp4, 없으면 PNG 프레임 폴더
        self.assertTrue((self.tmp / "runs/t1/demo_frames/f_0016.png").exists())

    def test_bad_elbow_is_snapped_to_axis(self):
        """모델이 팔꿈치를 팔 중심선에서 15cm 아래로 찍어도 중심선으로 되돌리고(axis_snapped) 변형 본이 메시 밖에 남지 않는다."""
        pipeline.rig(self.tmp, str(self.mesh), "humanoid", run_id="t2", quiet=True, no_judge=True)
        run = self.tmp / "runs/t2"
        a = json.loads((run / "analysis.json").read_text()); fit = json.loads((run / "fit.json").read_text())
        for side in ("L", "R"):
            el = fit["targets"][f"forearm.{side}"]["head"]; bad = [el[0], el[1], el[2] - 0.15]
            fit["targets"][f"upper_arm.{side}"]["tail"] = bad; fit["targets"][f"forearm.{side}"]["head"] = bad
        g = blender.run_script("fit_generate", {"blend": str(run / "01_analyzed.blend"), "out_blend": str(run / "02_bad.blend"), "preset": "humanoid",
                                                "targets": fit["targets"], "landmarks": a["landmarks"], "stats": a["stats"], "face": False}, {}, run / "logs")
        st = g["stats"]
        self.assertEqual(["forearm.L", "forearm.R"], st["axis_snapped"], st)
        self.assertEqual(0, st["deform_outside_mesh"], st.get("deform_outside_mesh_bones"))

    def test_real_shape_cc0_character(self):
        """CC0 게임 캐릭터(스킨 메시+아마추어+가방+손가락, T 포즈)를 mock 으로 리깅: 아마추어를 버리고 REST 자세로 굽고, 대리 메시 가중치가 붙고, 변형 본이 메시 안에 있어야 한다."""
        asset = Path(__file__).parent / "assets" / "quaternius_adventurer.glb"
        if not asset.exists():
            self.skipTest("tests/assets/quaternius_adventurer.glb 없음")
        pipeline.rig(self.tmp, str(asset), "humanoid", run_id="t3", quiet=True, no_judge=True)
        a = json.loads((self.tmp / "runs/t3/analysis.json").read_text())
        self.assertEqual(1, a["stats"]["import"]["had_armature"]); self.assertIn("Icosphere", a["stats"]["import"]["meshes_dropped"])
        self.assertEqual("T", a["landmarks"]["pose_guess"]); self.assertGreaterEqual(len(a["landmarks"]["arm_axis_L"]), 6)
        st = json.loads((self.tmp / "runs/t3/rig_stats.json").read_text())["stats"]
        self.assertEqual("auto_proxy", st["weight_method"], st); self.assertEqual(0, st["unweighted_verts"])
        self.assertLessEqual(st["deform_outside_mesh"], 2, st.get("deform_outside_mesh_bones"))
        self.assertEqual("ok", json.loads((self.tmp / "runs/t3/state.json").read_text())["status"])

    def test_motion_bvh_import(self):
        bvh = self.tmp / "tiny.bvh"
        bvh.write_text("HIERARCHY\nROOT Hips\n{\n OFFSET 0 0 0\n CHANNELS 6 Xposition Yposition Zposition Zrotation Xrotation Yrotation\n JOINT Spine\n {\n  OFFSET 0 0.5 0\n  CHANNELS 3 Zrotation Xrotation Yrotation\n  End Site\n  {\n   OFFSET 0 0.3 0\n  }\n }\n}\nMOTION\nFrames: 3\nFrame Time: 0.033333\n0 1 0 0 0 0 0 0 0\n0.5 1 0 0 0 0 10 0 0\n1.0 1 0 0 0 0 20 0 0\n")
        out = pipeline.motion(self.tmp, bvh=str(bvh), run_id="m1", quiet=True)
        self.assertTrue(out.exists())
        rep = out.read_text()
        self.assertIn("bones 2", rep)


class GateTests(unittest.TestCase):
    def test_rig_gates(self):
        g = {"max_unweighted_ratio": 0.0, "weight_sum_min": 0.98, "weight_sum_max": 1.02, "symmetry_max_error": 0.03, "deform_bones_min": 60, "max_bones_outside_bbox": 0}
        good = {"unweighted_verts": 0, "weight_sum_min": 1.0, "weight_sum_max": 1.0, "deform_bones": 160, "bones_outside_bbox": [], "symmetry_max_error": 0.0}
        self.assertEqual([], gates.rig_gates(good, g, 1000))
        bad = {**good, "unweighted_verts": 5, "bones_outside_bbox": ["DEF-hand.L"], "symmetry_max_error": 0.1}
        self.assertEqual(3, len(gates.rig_gates(bad, g, 1000)))
        self.assertEqual(1, len(gates.judge_gates({"bones_outside_mesh": ["left hand"], "proportions_ok": True})))

    def test_weight_leak_gate(self):
        """팔 본이 몸통으로 샌 정점이 기준(0.5%)을 넘으면 게이트가 잡는다. 복셀 대리 메시가 팔·몸통을 붙이면 생기는 위험."""
        g = {"max_unweighted_ratio": 0.0, "weight_sum_min": 0.98, "weight_sum_max": 1.02, "symmetry_max_error": 0.03,
             "deform_bones_min": 60, "max_bones_outside_bbox": 0, "max_weight_leak_ratio": 0.005}
        base = {"unweighted_verts": 0, "weight_sum_min": 1.0, "weight_sum_max": 1.0, "deform_bones": 160,
                "bones_outside_bbox": [], "symmetry_max_error": 0.0, "weight_leak_torso_verts": 200}
        self.assertEqual([], gates.rig_gates({**base, "weight_leak_arm_torso": 0}, g, 1000))
        self.assertEqual([], gates.rig_gates({**base, "weight_leak_arm_torso": 1}, g, 1000))   # 0.5% 는 통과
        fails = gates.rig_gates({**base, "weight_leak_arm_torso": 10}, g, 1000)                # 5% 는 실패
        self.assertEqual(1, len(fails)); self.assertIn("샌 정점 10/200", fails[0])
        self.assertEqual([], gates.rig_gates({**base, "weight_leak_torso_verts": 0, "weight_leak_arm_torso": 0}, g, 1000))


if __name__ == "__main__":
    unittest.main()
