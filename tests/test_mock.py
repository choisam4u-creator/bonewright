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
from bonewright import bench, blender, gates, pipeline  # noqa: E402


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
        # v0.2 부터 다리(발목)도 중심선으로 스냅되므로 팔꿈치가 목록에 들어 있는지만 본다
        self.assertIn("forearm.L", st["axis_snapped"], st); self.assertIn("forearm.R", st["axis_snapped"], st)
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

    def test_pin_and_targets_reuse(self):
        """--targets 는 모델을 부르지 않고(토큰 0) 같은 리그를 다시 만든다. --pin 은 모든 보정을 이기고 그 좌표에 정확히 놓인다."""
        pipeline.rig(self.tmp, str(self.mesh), "humanoid", run_id="t4", quiet=True, no_judge=True)
        targets = json.loads((self.tmp / "runs/t4/targets.json").read_text())
        self.assertIn("shin.L", targets)
        # 재사용: 모델 호출 0회
        pipeline.rig(self.tmp, str(self.mesh), "humanoid", run_id="t5", quiet=True, no_judge=True,
                     targets_file=str(self.tmp / "runs/t4/targets.json"))
        self.assertIsNone(json.loads((self.tmp / "runs/t5/fit.json").read_text())["confidence"])
        self.assertEqual(0, json.loads((self.tmp / "runs/t5/state.json").read_text())["input_tokens"])
        # 고정: 무릎을 안쪽으로 5cm 옮겨 고정하면 그 자리에 정확히 온다
        knee = list(targets["shin.L"]["head"]); knee[0] -= 0.05
        pipeline.rig(self.tmp, str(self.mesh), "humanoid", run_id="t6", quiet=True, no_judge=True,
                     targets_file=str(self.tmp / "runs/t4/targets.json"), pins={"shin.L": {"head": knee}})
        st = json.loads((self.tmp / "runs/t6/rig_stats.json").read_text())["stats"]
        self.assertEqual(["shin.L"], st["pin_applied"], st)
        got = blender.run_script("dump_bones", {"blend": str(self.tmp / "runs/t6/02_rigged.blend"), "names": ["DEF-shin.L"]},
                                 {}, self.tmp / "logs")["bones"]["DEF-shin.L"]["head"]
        for want, real in zip(knee, got):
            self.assertAlmostEqual(want, real, places=3, msg=f"고정 좌표 {knee} → 실제 {got}")
        self.assertGreater(st["symmetry_max_error"], 0.03)   # 한쪽만 고정했으니 대칭 게이트가 잡아야 한다

    def test_bench_against_original_rig(self):
        """원본 뼈대가 든 CC0 캐릭터로 관절 오차를 잰다. 숫자가 나빠지면(회귀) 여기서 걸린다.
        기준선(2026-09-15): 평균 6.59cm · 골반 0.89cm · 목 1.76cm."""
        asset = Path(__file__).parent / "assets" / "quaternius_adventurer.glb"
        if not asset.exists():
            self.skipTest("tests/assets/quaternius_adventurer.glb 없음")
        bench.run(self.tmp, [str(asset)], run_id="bench-t", quiet=True)
        d = json.loads((self.tmp / "runs/bench-t/bench.json").read_text())
        r = d["results"][0]
        self.assertEqual(17, r["matched"], r)          # 관절 17개가 이름으로 짝지어져야 한다
        self.assertLess(r["mean_cm"], 8.0, r)          # 기준선 6.59cm + 여유
        errs = {j["joint"]: j["error_cm"] for j in r["joints"]}
        self.assertLess(errs["DEF-spine"], 3.0, errs)      # 골반
        self.assertLess(errs["DEF-spine.004"], 4.0, errs)  # 목

    def test_motion_bvh_import(self):
        bvh = self.tmp / "tiny.bvh"
        bvh.write_text("HIERARCHY\nROOT Hips\n{\n OFFSET 0 0 0\n CHANNELS 6 Xposition Yposition Zposition Zrotation Xrotation Yrotation\n JOINT Spine\n {\n  OFFSET 0 0.5 0\n  CHANNELS 3 Zrotation Xrotation Yrotation\n  End Site\n  {\n   OFFSET 0 0.3 0\n  }\n }\n}\nMOTION\nFrames: 3\nFrame Time: 0.033333\n0 1 0 0 0 0 0 0 0\n0.5 1 0 0 0 0 10 0 0\n1.0 1 0 0 0 0 20 0 0\n")
        out = pipeline.motion(self.tmp, bvh=str(bvh), run_id="m1", quiet=True)
        self.assertTrue(out.exists())
        rep = out.read_text()
        self.assertIn("bones 2", rep)


class BenchMappingTests(unittest.TestCase):
    """뼈대 이름 규약이 달라도 관절이 짝지어져야 한다(Blender 불필요)."""

    def test_name_conventions(self):
        cases = {"mixamorig:LeftForeArm": ("forearm", "L"), "LeftUpLeg": ("upleg", "L"), "UpperArm.L": ("upperarm", "L"),
                 "thigh_r": ("thigh", "R"), "Wrist.L": ("wrist", "L"), "Hips": ("hips", None), "calf_l": ("calf", "L")}
        for name, want in cases.items():
            self.assertEqual(want, bench._norm(name), name)
        # 접두사가 붙은 규약(3ds Max Biped, VRM)도 핵심 이름으로 환원된다
        for name in ("Bip01_L_UpperArm", "J_Bip_L_UpperArm"):
            core, side = bench._norm(name)
            self.assertIn("upperarm", bench._cores(core), name); self.assertEqual("L", side, name)

    def test_compare_matches_mixamo(self):
        gt = {"mixamorig:Hips": {"head": [0, 0, 1.0]}, "mixamorig:LeftArm": {"head": [0.2, 0, 1.4]},
              "mixamorig:LeftForeArm": {"head": [0.45, 0, 1.4]}, "mixamorig:LeftUpLeg": {"head": [0.1, 0, 0.95]}}
        ours = {"DEF-spine": {"head": [0, 0, 1.05]}, "DEF-upper_arm.L": {"head": [0.2, 0, 1.4]},
                "DEF-forearm.L": {"head": [0.5, 0, 1.4]}, "DEF-thigh.L": {"head": [0.1, 0, 0.95]},
                "DEF-upper_arm.R": {"head": [-0.2, 0, 1.4]}}   # 정답에 오른팔이 없는 경우
        rows = {r["joint"]: r for r in bench.compare(ours, gt, 1.8)}
        self.assertAlmostEqual(5.0, rows["DEF-spine"]["error_cm"], places=1)      # 5cm
        self.assertAlmostEqual(0.0, rows["DEF-upper_arm.L"]["error_cm"], places=1)
        self.assertAlmostEqual(5.0, rows["DEF-forearm.L"]["error_cm"], places=1)
        self.assertIsNone(rows["DEF-upper_arm.R"]["gt"])                           # 오른쪽 정답이 없으면 매칭 실패로 표시


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
             "deform_bones_min": 60, "max_bones_outside_bbox": 0, "max_weight_leak_ratio": 0.005, "max_deform_outside_mesh": 0}
        base = {"unweighted_verts": 0, "weight_sum_min": 1.0, "weight_sum_max": 1.0, "deform_bones": 160,
                "bones_outside_bbox": [], "symmetry_max_error": 0.0, "weight_leak_torso_verts": 200}
        self.assertEqual([], gates.rig_gates({**base, "weight_leak_arm_torso": 0}, g, 1000))
        self.assertEqual([], gates.rig_gates({**base, "weight_leak_arm_torso": 1}, g, 1000))   # 0.5% 는 통과
        fails = gates.rig_gates({**base, "weight_leak_arm_torso": 10}, g, 1000)                # 5% 는 실패
        self.assertEqual(1, len(fails)); self.assertIn("샌 정점 10/200", fails[0])
        self.assertEqual([], gates.rig_gates({**base, "weight_leak_torso_verts": 0, "weight_leak_arm_torso": 0}, g, 1000))


if __name__ == "__main__":
    unittest.main()
