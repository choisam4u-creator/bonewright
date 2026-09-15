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
        # 정점당 영향 본은 glTF·엔진 표준인 4개 이하, 가중치 합은 1
        self.assertLessEqual(st["max_influences"], 4, st)
        self.assertAlmostEqual(1.0, st["weight_sum_min"], places=2)
        self.assertAlmostEqual(1.0, st["weight_sum_max"], places=2)
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
        # 게임용 GLB: 변형 본만(컨트롤 400여 개 제외), 다시 읽어 본 위치 일치. 정점은 glTF 가 UV·법선 경계에서 쪼개므로 원본 이상
        glb = pipeline.export_rig(self.tmp, "t1", quiet=True)
        ex = json.loads((self.tmp / "runs/t1/export.json").read_text())
        self.assertTrue(glb.exists()); self.assertLess(ex["bones"], 120, ex); self.assertGreaterEqual(ex["bones"], 60, ex)
        self.assertEqual(0.0, ex["max_diff_cm"], ex); self.assertGreaterEqual(ex["verts"], ex["verts_in_source"], ex)
        st = json.loads((self.tmp / "runs/t1/rig_stats.json").read_text()); self.assertEqual("humanoid", st["preset"])

    def test_retarget_bvh_and_export(self):
        """BVH 를 리그에 옮기고 GLB 로 내보낸다: 본 방향 오차 0, 메시 모서리 늘어남 6배 미만, 발이 바닥 아래로 안 감, 다시 읽은 GLB 의 손발 위치 일치"""
        pipeline.rig(self.tmp, str(self.mesh), "humanoid", run_id="t3", quiet=True, no_judge=True)
        out = pipeline.motion(self.tmp, bvh=str(ROOT / "spikes/motion_out/walk_wave.bvh"), run_id="m3", quiet=True, rig_run="t3", export="auto")
        self.assertTrue(out.exists())
        rt = json.loads((self.tmp / "runs/m3/retarget.json").read_text())
        self.assertEqual(18, len(rt["mapped"]), rt["mapped"])
        # 팔은 FK 라 방향이 정확히 맞고, 다리는 기본 auto(발 IK)라 비율에 맞춰 굽히므로 몇 도 어긋난다
        for k in ("DEF-hand.L", "DEF-hand.R", "DEF-upper_arm.L", "DEF-forearm.L"):
            self.assertEqual(0.0, rt["dir_deg"][k]["mean_deg"], rt["dir_deg"])
        self.assertLess(rt["mean_dir_deg"], 8.0, rt["dir_deg"])
        self.assertEqual(["foot_ik.L", "foot_ik.R"], sorted(rt["ik_legs"]), rt)
        self.assertLess(rt["stretch"]["max_edge_ratio"], 6.0, rt["stretch"])
        self.assertEqual(0, rt["foot_contact"]["frames_below_floor"], rt["foot_contact"])
        self.assertLess(rt["mean_end_cm"], 25.0, rt["end_cm"])   # 절차적 메시는 BVH 뼈대와 비율이 달라 위치 오차가 남는다(상한만 본다)
        self.assertTrue((self.tmp / "runs/m3/animated.glb").exists())
        rep = (self.tmp / "runs/m3/report.md").read_text()
        self.assertIn("re-import check", rep); self.assertIn("'DEF-hand.L': 0.0", rep, rep)

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
        기준선(2026-09-15, 광선 기반 가랑이 검출 뒤): 평균 6.08cm · 골반 4.35cm · 목 1.60cm.
        골반은 이 자산에서만 0.89 → 4.35cm 로 나빠졌지만 허벅지 8.3 → 4.75, 무릎 6.82 → 4.53 으로
        전체 평균은 6.56 → 6.08 로 내려갔고, 다른 자산은 골반이 12.8 → 1.7cm, 34.1 → 1.3cm 로 좋아졌다."""
        asset = Path(__file__).parent / "assets" / "quaternius_adventurer.glb"
        if not asset.exists():
            self.skipTest("tests/assets/quaternius_adventurer.glb 없음")
        bench.run(self.tmp, [str(asset)], run_id="bench-t", quiet=True)
        d = json.loads((self.tmp / "runs/bench-t/bench.json").read_text())
        r = d["results"][0]
        self.assertEqual(17, r["matched"], r)          # 관절 17개가 이름으로 짝지어져야 한다
        self.assertLess(r["mean_cm"], 7.0, r)          # 기준선 6.08cm + 여유
        errs = {j["joint"]: j["error_cm"] for j in r["joints"]}
        self.assertLess(errs["DEF-spine"], 6.0, errs)      # 골반(관습 차이 포함)
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

    def test_preflight_rejects_non_human(self):
        """거절 게이트: 사람 전제가 깨진 메시는 모델을 부르기 전에 막는다(토큰 0).
        기준값은 자산 17종의 분석 신호와 정답 대조 오차를 맞춰 고른 것이라, 경계가 바뀌면 여기서 걸린다"""
        from bonewright.gates import preflight
        from bonewright.config import DEFAULTS
        g = DEFAULTS["gates"]
        ok = {"height": 1.8, "arm_axis_L": [1], "arm_axis_R": [1], "leg_axis_L": [1], "leg_axis_R": [1],
              "ratio_fallbacks": [], "chibi": False, "symmetry_error": 0.0}
        self.assertEqual([], preflight(ok, {}, "humanoid", g)[0])          # 멀쩡한 사람형은 통과
        # 목 폴백만 있는 경우는 경고로 끝낸다(quaternius_ual 은 오차 7.4% 로 쓸 만했다)
        neck = dict(ok, ratio_fallbacks=["neck"])
        block, warn = preflight(neck, {}, "humanoid", g)
        self.assertEqual([], block); self.assertTrue(warn)
        for name, bad in (("팔 없음", dict(ok, arm_axis_L=None)),                 # 로봇·곤충·여우
                          ("다리 없음", dict(ok, leg_axis_R=[])),
                          ("관절 폴백", dict(ok, ratio_fallbacks=["ankle", "neck"])),   # godot_player 26%
                          ("치비", dict(ok, chibi=True, head_ratio=0.42)),            # platformer 28%
                          ("비대칭", dict(ok, symmetry_error=0.185)),                  # quat_pp_41j 16%
                          ("크기 이상", dict(ok, height=0.06))):                       # rigged_mesh 38%
            self.assertTrue(preflight(bad, {}, "humanoid", g)[0], name)
        # 사족은 발 네 개를 못 찾으면 막고, 찾으면 실험 단계라고 경고만 한다
        self.assertTrue(preflight({"height": 1.0, "quad": {"ok": False, "notes": ["X"]}}, {}, "quadruped", g)[0])
        qb, qw = preflight({"height": 1.0, "quad": {"ok": True}}, {}, "quadruped", g)
        self.assertEqual([], qb); self.assertTrue(qw)

    def test_compare_matches_quaternius_animals(self):
        """Quaternius 동물 규약은 이름이 관절보다 한 칸씩 밀려 있다(BackLeg=고관절, BackUpperLeg=무릎).
        이름만 보면 BackUpperLeg 를 넓적다리로 붙이기 쉬운데, 실제 본 좌표로 확인한 대응을 지킨다"""
        gt = {"Back": {"head": [0, -0.6, 1.98]}, "BackLeg.L": {"head": [0.34, -0.6, 1.76]},
              "BackUpperLeg.L": {"head": [0.34, -0.36, 1.34]}, "BackLowerLeg.L": {"head": [0.35, -1.24, 0.82]},
              "FrontUpperLeg.L": {"head": [0.33, 0.94, 1.46]}, "FrontLowerLeg.L": {"head": [0.33, 0.84, 1.12]},
              "Body": {"head": [0, 0, 0.47]}}
        ours = {"DEF-spine.004": {"head": [0, -0.6, 1.98]}, "DEF-thigh.L": {"head": [0.34, -0.6, 1.76]},
                "DEF-shin.L": {"head": [0.34, -0.36, 1.34]}, "DEF-foot.L": {"head": [0.35, -1.24, 0.82]},
                "DEF-front_thigh.L": {"head": [0.33, 0.94, 1.46]}, "DEF-front_shin.L": {"head": [0.33, 0.84, 1.12]},
                "DEF-front_foot.L": {"head": [0.33, 0.84, 0.10]}}
        rows = {r["joint"]: r for r in bench.compare(ours, gt, 2.1, preset="quadruped")}
        # 사족 골반은 DEF-spine.004 다(늑대 메타리그의 'spine' 은 꼬리 밑동이고, Rigify 가 DEF 번호를 한 칸 민다)
        for name in ("DEF-spine.004", "DEF-thigh.L", "DEF-shin.L", "DEF-foot.L", "DEF-front_thigh.L", "DEF-front_shin.L"):
            self.assertEqual(0.0, rows[name]["error_cm"], name)   # 같은 좌표를 줬으니 오차 0 이어야 옳게 붙은 것이다
        self.assertIsNone(rows["DEF-front_foot.L"]["gt"])          # 이 규약엔 앞발 본이 없다 → 매칭 없이 남는다

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


class RetargetMappingTests(unittest.TestCase):
    """BVH 관절 이름 → Rigify FK 컨트롤 매핑(Blender 없이 돈다)"""

    def test_kimodo_names(self):
        from bonewright.retarget import bvh_mapping
        names = ["Hips", "Spine1", "Spine2", "Chest", "Neck1", "Neck2", "Head", "Jaw", "LeftEye", "LeftShoulder", "LeftArm",
                 "LeftForeArm", "LeftHand", "LeftHandThumbEnd", "LeftHandMiddleEnd", "LeftLeg", "LeftShin", "LeftFoot", "LeftToeBase",
                 "RightLeg", "RightShin", "RightFoot"]
        m = bvh_mapping(names)
        self.assertEqual(m["Hips"], "torso"); self.assertEqual(m["Chest"], "chest")
        self.assertEqual(m["Neck1"], "neck"); self.assertEqual(m["Head"], "head")
        self.assertEqual(m["LeftArm"], "upper_arm_fk.L"); self.assertEqual(m["LeftForeArm"], "forearm_fk.L"); self.assertEqual(m["LeftHand"], "hand_fk.L")
        # kimodo: Leg 가 허벅지, Shin 이 정강이
        self.assertEqual(m["LeftLeg"], "thigh_fk.L"); self.assertEqual(m["LeftShin"], "shin_fk.L"); self.assertEqual(m["RightFoot"], "foot_fk.R")
        for n in ("Jaw", "LeftEye", "LeftHandThumbEnd", "LeftHandMiddleEnd", "LeftToeBase", "Neck2", "Spine1"):
            self.assertNotIn(n, m)

    def test_mixamo_names(self):
        from bonewright.retarget import bvh_mapping
        names = ["mixamorig:Hips", "mixamorig:Spine", "mixamorig:Spine1", "mixamorig:Spine2", "mixamorig:Neck", "mixamorig:Head",
                 "mixamorig:LeftShoulder", "mixamorig:LeftArm", "mixamorig:LeftForeArm", "mixamorig:LeftHand",
                 "mixamorig:LeftUpLeg", "mixamorig:LeftLeg", "mixamorig:LeftFoot", "mixamorig:LeftToeBase"]
        m = bvh_mapping(names)
        # Mixamo: UpLeg 가 허벅지, Leg 가 정강이(Shin 이 없다)
        self.assertEqual(m["mixamorig:LeftUpLeg"], "thigh_fk.L"); self.assertEqual(m["mixamorig:LeftLeg"], "shin_fk.L")
        self.assertEqual(m["mixamorig:Hips"], "torso"); self.assertEqual(m["mixamorig:Spine2"], "chest")
        self.assertEqual(m["mixamorig:Neck"], "neck"); self.assertEqual(m["mixamorig:LeftFoot"], "foot_fk.L")
        self.assertEqual(len(set(m.values())), len(m), "같은 컨트롤에 둘이 붙으면 안 된다")
