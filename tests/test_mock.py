"""mock 백엔드 + 절차적 휴머노이드로 rig 파이프라인 전체를 검증한다. Blender(app 또는 bpy 휠) 필요, Codex 토큰 0."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bonewright import bench, blender, gates, pipeline  # noqa: E402
from tests._marks import requires_blender  # noqa: E402


@requires_blender
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
        rep = (self.tmp / "runs/t1/report.md").read_text()
        self.assertNotIn(str((self.tmp / "runs/t1").resolve()), rep)   # 실행 폴더 안 파일은 상대 경로(이슈에 그대로 붙인다)
        self.assertIn("- targets: `targets.json`", rep)
        # 렌더는 사람이 볼 그림이라 `BW_NO_RENDER=1` 로 끌 수 있다(화면 없는 CI 서버에서 렌더러가 죽는다).
        # 꺼져 있으면 그림이 없는 게 정상이고, 켜져 있으면 세 장이 다 나와야 한다
        if os.environ.get("BW_NO_RENDER") != "1":
            for v in ("front", "side", "iso"):
                self.assertTrue((self.tmp / f"runs/t1/view_{v}.png").exists())
        self.assertIn("targets", json.loads((self.tmp / "runs/t1/fit.json").read_text()))
        self.assertEqual(0, st["deform_outside_mesh"], st.get("deform_outside_mesh_bones"))   # 변형 본 끝점이 메시 표면 밖에 없어야 한다
        # 데모 영상(짧게): IK 컨트롤이 존재하고 mp4 가 만들어진다
        if os.environ.get("BW_NO_RENDER") != "1":       # 데모는 그림이 목적이라 렌더가 꺼지면 건너뛴다
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
        self.assertNotIn(str((self.tmp / "runs/m3").resolve()), rep)

    def test_human_only_bones_go_when_the_source_has_no_counterpart(self):
        """원본 뼈대에 대응 관절이 없는 **사람 전용 본**은 지운다 — 떠 있으면 살을 가져간다.

        `breast.L/R` 은 어느 게임 리그에도 없어서 항상 사라진다(사람·네발 모두).
        `pelvis.L/R` 은 **네발일 때만** 지운다 — 사람 몸에서는 제 자리에 앉아 엉덩이 살을 맡는다
        (사람에게도 지웠더니 cesium_man 리타겟이 3.72 → 5.38배로 나빠졌다). 그래서 사람 리그에서
        사라지는 건 가슴 한 쌍뿐이고, 이 숫자가 2 를 넘으면 골반까지 지운 것이다."""
        asset = ROOT / "tests/assets/quaternius_adventurer.glb"
        if not asset.exists():
            self.skipTest("CC0 자산 없음")
        pipeline.rig(self.tmp, str(asset), "humanoid", run_id="hb1", quiet=True, no_judge=True, from_skeleton=True)
        st = json.loads((self.tmp / "runs/hb1/rig_stats.json").read_text())["stats"]
        self.assertEqual(st["removed_extra_bones"], 2, st)

    def test_user_bone_map_overrides_and_reports_typos(self):
        """`--map` 은 자동 매핑 위에 덮어쓰고, **BVH 에 없는 이름은 세어서 알려 준다**.

        이름으로 짝짓는 자동 매핑은 이름 없는 리그(`Limb3_2`)에 아무것도 못 붙인다 — 벤치 66종 중
        34종이 그래서 동작을 못 받았다. 오타를 조용히 넘기면 사용자는 "왜 안 붙지"만 반복한다."""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "m.json"
            f.write_text(json.dumps({"LeftArm": "Limb3_2", "Typo": "Limb9_1"}), encoding="utf-8")
            out, applied, unknown = pipeline.apply_bone_map(
                {"LeftArm": "upper_arm.L", "Hips": "torso"}, f, ["LeftArm", "Hips"])
            self.assertEqual(out["LeftArm"], "Limb3_2")    # 사용자 값이 이긴다
            self.assertEqual(out["Hips"], "torso")         # 안 적은 건 자동 매핑 그대로
            self.assertEqual((applied, unknown), (1, ["Typo"]))
            f.write_text(json.dumps(["nope"]), encoding="utf-8")
            with self.assertRaises(pipeline.Blocked):      # 모양이 틀리면 조용히 넘기지 않는다
                pipeline.apply_bone_map({}, f, [])

    def test_model_gaps_are_filled_from_landmarks(self):
        """모델이 자신 없어 **빼고 답한 본**은 랜드마크 배치로 메운다.

        빼는 것 자체는 옳다 — 실제 실행에서 "다리 중심선이 발목까지 안 와서 shin·foot 을 제외했다"
        고 답했다. 문제는 그러면 그 본이 **메타리그 기본값**으로 남는다는 것이다. mannequiny 실측:
        관절 평균 오차 5.96cm(발 24.71cm) → 메우면 3.21cm(발 6.67cm)."""
        from unittest import mock as _m
        base = [{"name": n, "head": [0, 0, 0], "tail": [0, 0, 1]}
                for n in ("spine", "shin.L", "shin.R", "foot.L", "foot.R", "hand.L")]
        model = {"hand.L": {"head": [9, 9, 9], "tail": [9, 9, 9]}}     # 모델은 하나만 답했다
        with _m.patch("bonewright.mock.mock_backend", return_value={"targets": base}):
            out, filled = pipeline.fill_missing_targets(model, {})
        self.assertEqual(filled, ["foot.L", "foot.R", "shin.L", "shin.R", "spine"])
        self.assertEqual(out["hand.L"]["head"], [9, 9, 9])             # 모델 답은 덮이지 않는다
        self.assertEqual(out["foot.R"]["tail"], [0, 0, 1])             # 뺀 본은 메워진다
        self.assertEqual(len(out), 6)

        with _m.patch("bonewright.mock.mock_backend", side_effect=RuntimeError("boom")):
            out2, filled2 = pipeline.fill_missing_targets(model, {})   # 메우기가 실패해도
        self.assertEqual((out2, filled2), (model, []))                 # 모델 답 그대로 간다

    def test_real_asset_survives_retarget_without_tearing(self):
        """**실제 자산**으로 리타겟 후 메시 늘어남을 잰다.

        절차 생성 테스트 메시는 껍질이 하나라 가중치 손해를 못 잡는다. 실제 게임 메시는 옷·머리카락이
        겹친 여러 껍질이라, 가중치를 건드리는 변경이 여기서만 드러난다(cross_trim 을 켰을 때
        mannequiny 가 4.71 → 7.88배로 나빠진 걸 이 종류의 검사만 잡았다)."""
        asset = ROOT / "tests/assets/quaternius_adventurer.glb"
        if not asset.exists():
            self.skipTest("CC0 자산 없음")
        pipeline.rig(self.tmp, str(asset), "humanoid", run_id="rt1", quiet=True, no_judge=True)
        pipeline.motion(self.tmp, bvh=str(ROOT / "spikes/motion_out/walk_wave.bvh"), run_id="rm1", quiet=True, rig_run="rt1")
        rt = json.loads((self.tmp / "runs/rm1/retarget.json").read_text())
        self.assertLess(rt["stretch"]["max_edge_ratio"], 6.0, rt["stretch"])
        self.assertLess(rt["stretch"]["edges_over_2x"], rt["stretch"]["edges"] * 0.01, rt["stretch"])

    def test_shape_rig_follows_the_mesh_when_there_is_no_skeleton(self):
        """--from-shape: 메시 속 중심선에서 뼈대를 직접 만든다. 해부학 이름은 없지만 모든 정점이 붙고
        본이 메시 안에 있어야 한다(사람·개과 비율을 못 쓰는 곤충·괴물을 위한 길)"""
        out = pipeline.rig(self.tmp, str(self.mesh), "humanoid", run_id="shape1", quiet=True, from_shape=True, no_judge=True)
        self.assertTrue(out.exists())
        st = json.loads((self.tmp / "runs/shape1/rig_stats.json").read_text())["stats"]
        self.assertGreaterEqual(st["deform_bones"], 6, st)          # 팔다리마다 사슬이 생겨야 한다
        self.assertEqual(st["deform_bones"], st["generic_source_bones"], "만든 본이 전부 변형 본이 되어야 한다")
        self.assertEqual(0, st["unweighted_verts"], st)
        self.assertEqual([], st["bones_outside_bbox"], st)
        state = json.loads((self.tmp / "runs/shape1/state.json").read_text())
        self.assertIn(state["status"], ("ok", "needs_review"), (self.tmp / "runs/shape1/report.md").read_text())

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

    def test_rig_name_conventions(self):
        """리깅 도구마다 뼈 이름 규약이 다르다. --from-skeleton 이 통하려면 이게 다 잡혀야 한다.
        DAZ 는 구분자 없이 l/r 을 앞에 붙이고(lShldr), Character Creator 는 CC_Base_L_ 접두사를 쓴다"""
        want = {c: b for b, cs in bench.JOINT_MAP.items() for c in cs}
        suites = {
            "Unreal": ["pelvis", "neck_01", "head", "clavicle_l", "upperarm_l", "lowerarm_l", "hand_l", "thigh_l", "calf_l", "foot_l"],
            "DAZ": ["hip", "neck", "head", "lCollar", "lShldr", "lForeArm", "lHand", "lThigh", "lShin", "lFoot"],
            "Unity": ["Hips", "Neck", "Head", "LeftShoulder", "LeftUpperArm", "LeftLowerArm", "LeftHand", "LeftUpperLeg", "LeftLowerLeg", "LeftFoot"],
            "Rigify": ["DEF-spine", "DEF-shoulder.L", "DEF-upper_arm.L", "DEF-forearm.L", "DEF-hand.L", "DEF-thigh.L", "DEF-shin.L", "DEF-foot.L"],
            "CharacterCreator": ["CC_Base_Hip", "CC_Base_NeckTwist01", "CC_Base_Head", "CC_Base_L_Clavicle", "CC_Base_L_Upperarm",
                                 "CC_Base_L_Forearm", "CC_Base_L_Hand", "CC_Base_L_Thigh", "CC_Base_L_Calf", "CC_Base_L_Foot"],
            "Mixamo": ["mixamorig:Hips", "mixamorig:LeftArm", "mixamorig:LeftForeArm", "mixamorig:LeftUpLeg", "mixamorig:LeftLeg", "mixamorig:LeftFoot"],
        }
        for suite, names in suites.items():
            for n in names:
                core, side = bench._norm(n)
                base = next((want[c] for c in bench._cores(core) if c in want), None)
                self.assertIsNotNone(base, f"{suite}: {n} 을 못 찾았다")
        # 'leg' 의 l 을 좌우 표시로 잘못 떼면 안 된다
        self.assertEqual(("leg", None), bench._norm("leg"))
        self.assertEqual(("lowerleg", None), bench._norm("lowerleg"))

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


@patch.dict(os.environ, {"BW_LANG": "ko"})   # 거절 사유 문구를 한국어로 대조한다
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
        # 저폴리: 몸통 표본이 63개뿐이면 정점 하나는 잡음이다(비율로는 1.6%) — 실패로 세지 않는다
        self.assertEqual([], gates.rig_gates({**base, "weight_leak_torso_verts": 63, "weight_leak_arm_torso": 1}, g, 1000))
        self.assertTrue(gates.rig_gates({**base, "weight_leak_torso_verts": 63, "weight_leak_arm_torso": 5}, g, 1000))
        # 표본이 30개 미만이면 비율을 판단할 수 없다 → 검사를 건너뛴다(cesium_man 몸통 한가운데 정점 12개)
        self.assertEqual([], gates.rig_gates({**base, "weight_leak_torso_verts": 12, "weight_leak_arm_torso": 3}, g, 1000))
        fails = gates.rig_gates({**base, "weight_leak_arm_torso": 10}, g, 1000)                # 5% 는 실패
        self.assertEqual(1, len(fails)); self.assertIn("샌 정점 10/200", fails[0])
        self.assertEqual([], gates.rig_gates({**base, "weight_leak_torso_verts": 0, "weight_leak_arm_torso": 0}, g, 1000))

    def test_reasons_follow_bw_lang(self):
        """BW_LANG=en 이면 거절 사유(preflight·rig_gates·judge_gates)에 한글이 하나도 없다."""
        g = {"max_unweighted_ratio": 0.0, "weight_sum_min": 0.98, "weight_sum_max": 1.02, "symmetry_max_error": 0.03,
             "deform_bones_min": 60, "max_bones_outside_bbox": 0, "max_weight_leak_ratio": 0.005, "max_deform_outside_mesh": 0}
        bad = {"unweighted_verts": 5, "filled_from_neighbor": 100, "weight_sum_min": 0.5, "weight_sum_max": 1.0, "deform_bones": 10,
               "bones_outside_bbox": ["DEF-hand.L"], "symmetry_max_error": 0.1, "deform_outside_mesh": 2,
               "weight_leak_torso_verts": 200, "weight_leak_arm_torso": 50}
        land = {"height": 0.1, "ratio_fallbacks": ["knee", "neck"], "chibi": True, "head_ratio": 0.3, "symmetry_error": 0.5,
                "medial": {"supplied": ["arm_axis_L"], "consistent": False}}
        with patch.dict(os.environ, {"BW_LANG": "en"}):
            block, warn = gates.preflight(land, {}, "humanoid", {})
            quad, qwarn = gates.preflight({"height": 1.0}, {}, "quadruped", {})
            texts = (block + warn + quad + qwarn + gates.rig_gates(bad, g, 1000, source_leak=0.01)
                     + gates.rig_gates({**bad, "generic_source_bones": 20}, g, 1000)
                     + gates.judge_gates({"bones_outside_mesh": ["x"], "proportions_ok": False, "notes": "n"}))
        self.assertGreaterEqual(len(block), 6, block)
        self.assertGreaterEqual(len(texts), 20, texts)
        hangul = [t for t in texts if any("\uac00" <= c <= "\ud7a3" for c in t)]
        self.assertEqual([], hangul)

    def test_model_text_in_english_mode_is_labelled(self):
        """시각 판정의 자유 문장은 프롬프트 언어(기본 ko)로 온다. 영어 화면이면 모델 출력이라고 밝히고 --lang en 을 안내한다."""
        judge = {"bones_outside_mesh": ["왼손"], "proportions_ok": False, "notes": "팔이 너무 길다"}
        with patch.dict(os.environ, {"BW_LANG": "en"}):
            fails = gates.judge_gates(judge)
            plain = gates.judge_gates({"bones_outside_mesh": ["left hand"]})
        self.assertEqual(2, len(fails))
        for f in fails:
            self.assertIn("model output in the prompt language; run with --lang en", f)
        self.assertEqual(["visual judge: bones outside the mesh left hand"], plain)
        self.assertEqual("시각 판정: 비율 이상 — 팔이 너무 길다", gates.judge_gates(judge)[1])   # 클래스가 BW_LANG=ko


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


class QuadTailMappingTests(unittest.TestCase):
    """사족 꼬리: 늑대 메타리그 꼬리 사슬은 골반 쪽부터 spine.003 → .002 → .001 → spine 이다(번호가 거꾸로).
    원본 마디 수가 제각각이라 길이 비례로 나눠 준다 — 안 하면 Tail1~8 이 전부 같은 컨트롤로 몰려 꼬리가 안 움직인다"""

    def test_tail_chain_is_spread_over_four_controls(self):
        from bonewright.retarget import bvh_mapping
        names = ["Back", "Torso", "Torso3", "Neck1", "Head", "BackLeg.L", "BackUpperLeg.L", "BackLowerLeg.L",
                 "BackLeg.R", "BackUpperLeg.R", "BackLowerLeg.R"] + [f"Tail{i}" for i in range(1, 9)]
        m = bvh_mapping(names, "quadruped")
        tail = {k: v for k, v in m.items() if k.startswith("Tail")}
        self.assertEqual(4, len(tail), "꼬리 컨트롤 4개가 모두 쓰여야 한다")
        self.assertEqual("spine.003", m["Tail1"])          # 밑동이 골반 쪽
        self.assertEqual(["spine.003", "spine.002", "spine.001", "spine"],
                         [m[k] for k in sorted(tail, key=lambda n: int(n[4:]))])   # 번호 순 = 밑동→끝
        self.assertEqual(len(set(m.values())), len(m), "같은 컨트롤에 둘이 붙으면 안 된다")

    def test_short_tail_maps_from_the_base(self):
        """마디가 4개보다 적은 꼬리는 밑동부터 순서대로 채운다(가운데를 비우면 사슬이 끊겨 보인다)"""
        from bonewright.retarget import bvh_mapping
        m = bvh_mapping(["Back", "Tail1", "Tail2"], "quadruped")
        self.assertEqual("spine.003", m["Tail1"]); self.assertEqual("spine.002", m["Tail2"])


class BvhUpAxisTests(unittest.TestCase):
    """BVH 위 축 자동 판단. 틀리면 조용히 망가진다 — 늑대 걷기에서 방향 오차 2.75° → 14.9°, 발이 바닥에서 1m 떴다"""

    def _write(self, up):
        """머리가 위, 발이 아래인 최소 BVH. up='z' 면 블렌더 규약(Z 가 위)"""
        def off(fwd, height):
            return f"{0.0} {height if up == 'y' else fwd} {fwd if up == 'y' else height}"
        txt = f"""HIERARCHY
ROOT Hips
{{
OFFSET {off(0, 1.0)}
CHANNELS 6 Xposition Yposition Zposition Xrotation Yrotation Zrotation
JOINT Neck
{{
OFFSET {off(0, 0.5)}
CHANNELS 3 Xrotation Yrotation Zrotation
JOINT Head
{{
OFFSET {off(0, 0.2)}
CHANNELS 3 Xrotation Yrotation Zrotation
End Site
{{
OFFSET {off(0, 0.2)}
}}
}}
}}
JOINT LeftFoot
{{
OFFSET {off(0, -0.9)}
CHANNELS 3 Xrotation Yrotation Zrotation
End Site
{{
OFFSET {off(0.1, -0.1)}
}}
}}
}}
MOTION
Frames: 1
Frame Time: 0.0333
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
"""
        f = Path(tempfile.mkdtemp(prefix="bw-bvh-")) / "t.bvh"
        f.write_text(txt, encoding="utf-8")
        return str(f)

    def test_detects_both_conventions(self):
        from bonewright.retarget import detect_bvh_up
        for up in ("y", "z"):
            self.assertEqual(up, detect_bvh_up(self._write(up)), f"{up} 위 축을 못 알아봤다")

    def test_unknown_names_fall_back_to_standard(self):
        """머리·발을 못 찾으면 BVH 규약대로 y 를 쓴다(추측으로 망가뜨리지 않는다)"""
        from bonewright.retarget import detect_bvh_up
        path = self._write("z")
        txt = Path(path).read_text(encoding="utf-8").replace("Head", "Bone9").replace("Neck", "Bone8").replace("LeftFoot", "Bone7")
        Path(path).write_text(txt, encoding="utf-8")
        self.assertEqual("y", detect_bvh_up(path))


class FromSkeletonTests(unittest.TestCase):
    """원본 뼈대를 그대로 받는 경로(--from-skeleton, Blender 불필요).
    자산으로 확인한 실패들이 다시 나오지 않게 고정한다"""

    def _humanoid(self, flip=False):
        """간단한 사람형 뼈대. flip=True 면 가져오기가 180° 돌린 상황(원본 Left 가 우리 -X 로 간다)"""
        s = -1 if flip else 1
        return {"Hips": {"head": [0, 0, 1.0], "tail": [0, 0, 1.2], "parent": None},
                "Spine": {"head": [0, 0, 1.2], "tail": [0, 0, 1.4], "parent": "Hips"},
                "Neck": {"head": [0, 0, 1.5], "tail": [0, 0, 1.6], "parent": "Spine"},
                "Head": {"head": [0, 0, 1.6], "tail": [0, 0, 1.75], "parent": "Neck"},
                "UpperArm.L": {"head": [0.2 * s, 0, 1.45], "tail": [0.45 * s, 0, 1.45], "parent": "Neck"},
                "LowerArm.L": {"head": [0.45 * s, 0, 1.45], "tail": [0.7 * s, 0, 1.45], "parent": "UpperArm.L"},
                "UpperArm.R": {"head": [-0.2 * s, 0, 1.45], "tail": [-0.45 * s, 0, 1.45], "parent": "Neck"},
                "LowerArm.R": {"head": [-0.45 * s, 0, 1.45], "tail": [-0.7 * s, 0, 1.45], "parent": "UpperArm.R"},
                "UpperLeg.L": {"head": [0.1 * s, 0, 0.95], "tail": [0.1 * s, 0, 0.5], "parent": "Hips"},
                "LowerLeg.L": {"head": [0.1 * s, 0, 0.5], "tail": [0.1 * s, 0, 0.1], "parent": "UpperLeg.L"},
                "Foot.L": {"head": [0.1 * s, 0, 0.1], "tail": [0.1 * s, -0.1, 0.0], "parent": "LowerLeg.L"},
                "UpperLeg.R": {"head": [-0.1 * s, 0, 0.95], "tail": [-0.1 * s, 0, 0.5], "parent": "Hips"},
                "LowerLeg.R": {"head": [-0.1 * s, 0, 0.5], "tail": [-0.1 * s, 0, 0.1], "parent": "UpperLeg.R"},
                "Foot.R": {"head": [-0.1 * s, 0, 0.1], "tail": [-0.1 * s, -0.1, 0.0], "parent": "LowerLeg.R"}}

    def test_sides_follow_coordinates_not_names(self):
        """가져오기가 메시를 180° 돌리면 원본 'Left' 가 우리 -X 로 온다. 이름만 믿으면 팔이 교차한다"""
        from bonewright.from_skeleton import targets_from_skeleton
        for flip in (False, True):
            tg, _ = targets_from_skeleton(self._humanoid(flip), "humanoid", 1.8)
            self.assertGreater(tg["upper_arm.L"]["head"][0], 0, f"flip={flip}: 왼팔은 +X 여야 한다")
            self.assertLess(tg["upper_arm.R"]["head"][0], 0, f"flip={flip}: 오른팔은 -X 여야 한다")
            self.assertGreater(tg["thigh.L"]["head"][0], 0, f"flip={flip}")

    def test_missing_wrist_uses_previous_bone_tail(self):
        """손목 관절이 없는 뼈대(로봇)는 팔뚝 본의 tail 이 곧 손목이다 — 기본 자리에 남으면 몸을 가로지른다"""
        from bonewright.from_skeleton import targets_from_skeleton
        tg, info = targets_from_skeleton(self._humanoid(), "humanoid", 1.8)
        self.assertAlmostEqual(0.7, tg["hand.L"]["head"][0], places=3)   # LowerArm.L 의 tail
        self.assertAlmostEqual(0.7, tg["forearm.L"]["tail"][0], places=3)
        self.assertEqual([], info["limbs_absent"])

    def test_palm_counts_as_wrist(self):
        """손목 이름 없이 손바닥만 있는 리그(three.js RobotExpressive)도 손이 제자리에 와야 한다"""
        j = self._humanoid()
        j["Palm1.L"] = {"head": [0.8, 0, 1.45], "tail": [0.9, 0, 1.45], "parent": "LowerArm.L"}
        j["Palm1.R"] = {"head": [-0.8, 0, 1.45], "tail": [-0.9, 0, 1.45], "parent": "LowerArm.R"}
        from bonewright.from_skeleton import targets_from_skeleton
        tg, _ = targets_from_skeleton(j, "humanoid", 1.8)
        self.assertAlmostEqual(0.8, tg["hand.L"]["head"][0], places=3)

    def test_half_rigged_source_is_mirrored(self):
        """한쪽만 리깅한 자산은 몸 한가운데를 기준으로 비춰 채운다(안 그러면 반대쪽이 기본 자리에 남는다)"""
        from bonewright.from_skeleton import targets_from_skeleton
        j = {k: v for k, v in self._humanoid().items() if not k.endswith(".R")}
        tg, info = targets_from_skeleton(j, "humanoid", 1.8)
        self.assertIn("upper_arm.R", tg)
        self.assertAlmostEqual(-tg["upper_arm.L"]["head"][0], tg["upper_arm.R"]["head"][0], places=4)
        self.assertIn("upper_arm.R", info["mirrored"])

    def test_absent_limb_is_reported(self):
        """팔다리가 통째로 없는 뼈대(반쪽 자산)는 채울 근거가 없다 → 파이프라인이 0 토큰으로 막을 수 있게 알린다"""
        from bonewright.from_skeleton import targets_from_skeleton
        j = {k: v for k, v in self._humanoid().items() if "Leg" not in k and "Foot" not in k}
        _, info = targets_from_skeleton(j, "humanoid", 1.8)
        self.assertEqual(["thigh"], info["limbs_absent"])

    def test_quadruped_chain_follows_source_spine(self):
        """사족: 등·꼬리는 휘어 있다. 양 끝만 이으면 본이 몸 밖으로 나가고, 꼬리 사슬은 골반과 같은 점에서 시작해야
        Rigify 가 'disjoint' 로 실패하지 않는다(늑대로 확인)"""
        from bonewright.from_skeleton import targets_from_skeleton
        j = {"Body": {"head": [0, -0.8, 0.5], "tail": [0, -0.8, 0.6], "parent": None},
             "Back": {"head": [0, 0, 2.0], "tail": [0, -0.4, 1.95], "parent": "Body"},
             "Torso": {"head": [0, -0.7, 1.9], "tail": [0, -1.1, 1.87], "parent": "Back"},
             "Torso2": {"head": [0, -1.1, 1.87], "tail": [0, -1.7, 1.83], "parent": "Torso"},
             "Neck1": {"head": [0, -1.95, 1.88], "tail": [0, -2.2, 1.95], "parent": "Torso2"},
             "Head": {"head": [0, -2.7, 2.12], "tail": [0, -3.0, 2.03], "parent": "Neck1"},
             "Tail1": {"head": [0, 0.0, 1.88], "tail": [0, 0.2, 1.99], "parent": "Back"},
             "Tail2": {"head": [0, 0.2, 1.99], "tail": [0, 0.9, 1.94], "parent": "Tail1"},
             "FrontUpperLeg.L": {"head": [0.33, -1.76, 1.47], "tail": [0.33, -1.65, 1.13], "parent": "Torso2"},
             "FrontLowerLeg.L": {"head": [0.33, -1.65, 1.13], "tail": [0.33, -1.73, 0.28], "parent": "FrontUpperLeg.L"},
             "FrontUpperLeg.R": {"head": [-0.33, -1.76, 1.47], "tail": [-0.33, -1.65, 1.13], "parent": "Torso2"},
             "FrontLowerLeg.R": {"head": [-0.33, -1.65, 1.13], "tail": [-0.33, -1.73, 0.28], "parent": "FrontUpperLeg.R"},
             "BackLeg.L": {"head": [0.34, -0.2, 1.77], "tail": [0.34, -0.45, 1.35], "parent": "Back"},
             "BackUpperLeg.L": {"head": [0.34, -0.45, 1.35], "tail": [0.34, 0.43, 0.83], "parent": "BackLeg.L"},
             "BackLowerLeg.L": {"head": [0.34, 0.43, 0.83], "tail": [0.34, 0.09, 0.2], "parent": "BackUpperLeg.L"},
             "BackLeg.R": {"head": [-0.34, -0.2, 1.77], "tail": [-0.34, -0.45, 1.35], "parent": "Back"},
             "BackUpperLeg.R": {"head": [-0.34, -0.45, 1.35], "tail": [-0.34, 0.43, 0.83], "parent": "BackLeg.R"},
             "BackLowerLeg.R": {"head": [-0.34, 0.43, 0.83], "tail": [-0.34, 0.09, 0.2], "parent": "BackUpperLeg.R"}}
        tg, info = targets_from_skeleton(j, "quadruped", 2.2)
        self.assertEqual([], info["limbs_absent"])
        # 등 사슬: 골반에서 시작해 목 밑에서 끝나고, 마디가 서로 붙어 있어야 한다
        back = ["spine.004", "spine.005", "spine.006", "spine.007", "spine.008"]
        self.assertEqual([0, 0, 2.0], tg["spine.004"]["head"])
        for a, b in zip(back, back[1:]):
            self.assertEqual(tg[a]["tail"], tg[b]["head"], f"{a}→{b} 가 끊겼다")
        self.assertAlmostEqual(-1.95, tg["spine.008"]["tail"][1], places=2)   # 목 밑
        # 꼬리 사슬은 골반과 같은 점에서 시작한다(Rigify 요구)
        self.assertEqual(tg["spine.004"]["head"], tg["spine.003"]["head"])
        # 앞발: 원본에 발 관절이 없으니 마지막 본의 tail 을 쓴다(방향 외삽이면 공중에 뜬다)
        self.assertAlmostEqual(0.28, tg["front_shin.L"]["tail"][2], places=2)
        # 사족 앞다리 좌우도 좌표 부호로 정한다
        self.assertGreater(tg["front_thigh.L"]["head"][0], 0)
        self.assertLess(tg["front_thigh.R"]["head"][0], 0)
        # 발바닥은 바닥(z=0)에 닿아야 한다. 동물 뼈대는 발목 아래 본이 없어서 비율로 이으면 짐승이 공중에 뜬다
        for n in ("toe.L", "toe.R", "front_toe.L", "front_toe.R"):
            self.assertAlmostEqual(0.0, tg[n]["head"][2], places=6, msg=n)
            self.assertAlmostEqual(0.0, tg[n]["tail"][2], places=6, msg=n)
        self.assertAlmostEqual(0.0, tg["foot.L"]["tail"][2], places=6)


@patch.dict(os.environ, {"BW_LANG": "ko"})
class MedialShapeTests(unittest.TestCase):
    """메시 속 중심선 읽기(_medial)의 순수 기하 부분. Blender 없이 돈다"""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(ROOT / "bonewright" / "bpy_scripts"))
        import _medial
        cls.M = _medial

    @staticmethod
    def _tip(pts, r=0.05):
        """[(x,y,z)…] 를 끝점 구조로. path 는 '끝 → 몸통' 순서다(read_shape 와 같다)"""
        path = [[p[0], p[1], p[2], r] for p in pts]
        return {"p": list(pts[0]), "r": r, "branch": 1.0, "path": path}

    def test_resample_is_evenly_spaced(self):
        pts = [[0, 0, 0], [0, 0, 1], [0, 0, 3]]
        out = self.M.resample(pts, 5)
        self.assertEqual(len(out), 5)
        gaps = [((out[i + 1][2] - out[i][2]) ** 2) ** 0.5 for i in range(4)]
        self.assertLess(max(gaps) - min(gaps), 0.05, f"간격이 고르지 않다: {gaps}")

    def test_classify_assigns_roles_by_coordinate_not_name(self):
        """좌우는 x 부호로 정한다 — 가져오기가 메시를 180° 돌려도 팔다리가 교차하지 않는다"""
        shape = {"root": [0, 0, 0.9, 0.1], "tips": [
            self._tip([(0.15, 0, 0.02), (0.15, 0, 0.5), (0, 0, 0.9)]),     # 왼발(+x)
            self._tip([(-0.15, 0, 0.02), (-0.15, 0, 0.5), (0, 0, 0.9)]),   # 오른발(-x)
            self._tip([(0.7, 0, 1.4), (0.3, 0, 1.4), (0, 0, 1.2)]),        # 왼손
            self._tip([(-0.7, 0, 1.4), (-0.3, 0, 1.4), (0, 0, 1.2)]),      # 오른손
            self._tip([(0.0, 0, 1.75), (0, 0, 1.5), (0, 0, 1.2)]),         # 머리
        ]}
        roles = self.M.classify(shape, height=1.8, ground=0.0)
        self.assertEqual(set(roles), {"foot.L", "foot.R", "hand.L", "hand.R", "head"})
        self.assertGreater(roles["foot.L"]["p"][0], 0)
        self.assertLess(roles["foot.R"]["p"][0], 0)
        self.assertGreater(roles["hand.L"]["p"][0], 0)
        self.assertAlmostEqual(roles["head"]["p"][2], 1.75, places=3)

    def test_crotch_is_where_the_two_legs_meet(self):
        L = self._tip([(0.15, 0, 0.02), (0.15, 0, 0.4), (0.06, 0, 0.9), (0.0, 0, 1.0)], r=0.05)
        R = self._tip([(-0.15, 0, 0.02), (-0.15, 0, 0.4), (-0.06, 0, 0.9), (0.0, 0, 1.0)], r=0.05)
        cz = self.M.crotch_from(L, R)
        self.assertIsNotNone(cz)
        self.assertAlmostEqual(cz, 0.9, delta=0.12)

    def test_ankle_is_the_corner_and_a_straight_leg_has_none(self):
        bent = self._tip([(0.15, -0.2, 0.02), (0.15, 0.0, 0.02), (0.15, 0.0, 0.45), (0.15, 0.0, 0.9)])
        p = self.M.ankle_from(bent, ground=0.0, height=1.8)
        self.assertIsNotNone(p, "다리→발 모서리를 못 찾았다")
        self.assertLess(p[2], 1.8 * 0.25)
        straight = self._tip([(0.15, 0, 0.02), (0.15, 0, 0.45), (0.15, 0, 0.9)])
        self.assertIsNone(self.M.ankle_from(straight, ground=0.0, height=1.8),
                          "곧은 다리에 없는 모서리를 지어내면 안 된다")

    def test_arm_axis_keeps_only_what_is_outside_the_torso(self):
        arm = self._tip([(0.8, 0, 1.4), (0.6, 0, 1.4), (0.4, 0, 1.4), (0.2, 0, 1.4), (0.05, 0, 1.3), (0, 0, 1.0)])
        ax = self.M.arm_axis(arm, torso_hw=0.15, samples=6)
        self.assertEqual(len(ax), 6)
        self.assertTrue(all(abs(p[0]) > 0.15 - 1e-6 for p in ax), f"몸통 안쪽 표본이 남았다: {ax}")
        self.assertLess(ax[0][0], ax[-1][0], "어깨 쪽에서 손끝 쪽 순서여야 한다")
        self.assertEqual(self.M.arm_axis(self._tip([(0.05, 0, 1.3), (0, 0, 1.0)]), torso_hw=0.15), [])

    def test_classify_quadruped_finds_four_paws_head_and_tail(self):
        """네 발·머리·꼬리. 머리와 꼬리는 이름이 아니라 **경로 굵기**로 가른다(꼬리가 가늘다)"""
        def paw(x, y):
            return self._tip([(x, y, 0.02), (x, y, 0.3), (x * 0.5, y, 0.6)], r=0.03)
        shape = {"root": [0, 0, 0.6, 0.15], "tips": [
            paw(0.2, 0.5), paw(-0.2, 0.5),      # 앞발
            paw(0.2, -0.5), paw(-0.2, -0.5),    # 뒷발
            self._tip([(0, 1.1, 0.75), (0, 0.8, 0.7), (0, 0.4, 0.65)], r=0.12),   # 머리(굵다)
            self._tip([(0, -1.1, 0.7), (0, -0.8, 0.65), (0, -0.4, 0.62)], r=0.02),  # 꼬리(가늘다)
        ]}
        roles = self.M.classify(shape, height=0.9, ground=0.0, quad=True)
        self.assertEqual(set(roles), {"front.L", "front.R", "hind.L", "hind.R", "head", "tail"})
        self.assertGreater(roles["head"]["p"][1], roles["tail"]["p"][1], "머리와 꼬리가 뒤바뀌었다")
        self.assertGreater(roles["front.L"]["p"][1], roles["hind.L"]["p"][1], "앞뒤 다리가 뒤바뀌었다")
        self.assertGreater(roles["front.L"]["p"][0], 0)
        self.assertLess(roles["front.R"]["p"][0], 0)

    def test_inconsistent_read_supplies_values_but_does_not_clear_the_gate(self):
        """좌우가 어긋난 읽기(견갑을 손으로 잡은 경우)는 값만 보태고 통과시키지는 않는다"""
        good = {"foot.L": self._tip([(0.2, 0, 0.02)]), "foot.R": self._tip([(-0.2, 0, 0.02)]),
                "hand.L": self._tip([(0.7, 0, 1.4)]), "hand.R": self._tip([(-0.7, 0, 1.4)]),
                "head": self._tip([(0, 0, 1.75)])}
        self.assertTrue(self.M.consistent(good, 1.8))
        bad = dict(good, **{"hand.R": self._tip([(-0.5, 0, 1.96)])})   # 높이가 56cm 어긋난다
        self.assertFalse(self.M.consistent(bad, 1.8))
        self.assertFalse(self.M.consistent({k: v for k, v in good.items() if k != "hand.R"}, 1.8))
        land = {"height": 1.8, "arm_axis_L": [[1, 0, 1, 0.1]], "arm_axis_R": [[-1, 0, 1, 0.1]],
                "leg_axis_L": [[0.1, 0, 0.5, 0.1]], "leg_axis_R": [[-0.1, 0, 0.5, 0.1]],
                "ratio_fallbacks": [], "symmetry_error": 0.0,
                "medial": {"supplied": ["arm_axis_L", "arm_axis_R"], "consistent": False}}
        block, _w = gates.preflight(land, {}, "humanoid", {"min_height_m": 0.3, "max_height_m": 20.0,
                                                           "max_symmetry_error_ratio": 0.03})
        self.assertTrue(any("좌우로 어긋난다" in b for b in block), block)

    def test_medial_evidence_is_reported_by_the_gate(self):
        """속에서 채운 값은 막지 않되, 어디서 왔는지 경고로 남긴다"""
        land = {"height": 1.8, "arm_axis_L": [[1, 0, 1, 0.1]], "arm_axis_R": [[-1, 0, 1, 0.1]],
                "leg_axis_L": [[0.1, 0, 0.5, 0.1]], "leg_axis_R": [[-0.1, 0, 0.5, 0.1]],
                "ratio_fallbacks": [], "symmetry_error": 0.0,
                "medial": {"supplied": ["ankle_z", "crotch_z"]}}
        block, warn = gates.preflight(land, {}, "humanoid", {"min_height_m": 0.3, "max_height_m": 20.0,
                                                             "max_symmetry_error_ratio": 0.03})
        self.assertEqual(block, [])
        self.assertTrue(any("메시 속" in w for w in warn), warn)
