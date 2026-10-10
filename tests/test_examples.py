"""examples/rig_sample.py 의 표 부분(블렌더 불필요). 리깅 부분은 RigMockTests 가 같은 경로를 이미 본다."""
import json
import re
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))
import rig_sample  # noqa: E402
from tests._marks import requires_blender  # noqa: E402

SAMPLE = ROOT / "examples" / "sample-output" / "capsule_doll.md"
DOG = ROOT / "examples" / "sample-output" / "capsule_dog.md"
MOTION = ROOT / "examples" / "sample-output" / "capsule_doll_motion.md"


def motion_rows(md: str) -> list[str]:
    """리타겟 예시에서 요약 줄과 '옮긴 본' 표 줄만(오차 숫자는 싣지 않는다)."""
    return [ln for ln in md.splitlines() if ln.startswith("- BVH joints") or (ln.startswith("| `") and "` |" in ln)]


def table_part(md: str) -> str:
    """결과 문서에서 'Deform bones in the exported GLB' 표 부분만."""
    return md.split("## Deform bones in the exported GLB", 1)[1].strip()


def tiny_glb(names):
    doc = {"asset": {"version": "2.0"}, "nodes": [{"name": n} for n in names], "skins": [{"joints": list(range(len(names)))}]}
    js = json.dumps(doc).encode(); js += b" " * (-len(js) % 4)
    return b"glTF" + struct.pack("<II", 2, 20 + len(js)) + struct.pack("<II", len(js), 0x4E4F534A) + js


class ExampleTableTests(unittest.TestCase):
    def test_reads_skin_joints_in_order(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.glb"; p.write_bytes(tiny_glb(["DEF-spine", "DEF-upper_arm.L", "DEF-upper_arm.R"]))
            self.assertEqual(["DEF-spine", "DEF-upper_arm.L", "DEF-upper_arm.R"], rig_sample.glb_skin_bones(p))
            t = rig_sample.bone_table(rig_sample.glb_skin_bones(p))
            self.assertIn("3 bones · left 1 · right 1 · center 1", t)
            self.assertIn("| upper_arm | 2 |", t)

    def test_not_a_glb_says_what_to_do(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.glb"; p.write_text("{}")
            with self.assertRaisesRegex(ValueError, r"\.glb"):
                rig_sample.glb_skin_bones(p)

    def test_cc0_asset_has_62_source_bones(self):
        asset = ROOT / "tests" / "assets" / "quaternius_adventurer.glb"
        if not asset.exists():
            self.skipTest("자산 없음")
        names = rig_sample.glb_skin_bones(asset)
        self.assertEqual(62, len(names)); self.assertIn("UpperArm.L", names)



class ExampleMessageTests(unittest.TestCase):
    """예제는 공개 뒤 첫 사용자가 가장 먼저 돌리는 파일이다 — 막힐 때 문구가 화면 언어(BW_LANG)를 따르는지."""

    def _no_blender_message(self, lang):
        from unittest import mock
        from bonewright import blender
        with mock.patch.dict("os.environ", {"BW_LANG": lang}), \
             mock.patch.object(blender, "find_blender", return_value=None), \
             mock.patch.object(blender, "has_bpy_module", return_value=False):
            with self.assertRaises(SystemExit) as cm:
                rig_sample.rig_and_table(None, "x", "humanoid")
        return str(cm.exception.code)

    def test_no_blender_follows_screen_language(self):
        en, ko = self._no_blender_message("en"), self._no_blender_message("ko")
        self.assertIn("Blender not found", en); self.assertIn("pip install bpy==5.2.2", en)
        self.assertIsNone(re.search(r"[가-힣]", en), en)
        self.assertIn("Blender 가 없다", ko)

    def test_missing_file_follows_screen_language(self):
        from unittest import mock
        with mock.patch.dict("os.environ", {"BW_LANG": "en"}), mock.patch.object(sys, "argv", ["rig_sample.py", "no/such.glb"]):
            with self.assertRaises(SystemExit) as cm:
                rig_sample.main()
        self.assertIn("file not found", str(cm.exception.code))

    def test_motion_on_quadruped_stops_before_rigging(self):
        """`--motion --preset quadruped` is refused before rigging starts.

        `--motion --preset quadruped` 는 리깅(블렌더 수십 초)을 하기 전에 멈춘다 — 10/9 까지는 다 리깅한 뒤 거절했다."""
        from unittest import mock
        for argv in (["--motion", "--preset", "quadruped"], ["--motion", "--table", "adventurer"]):
            with self.subTest(argv=argv), mock.patch.dict("os.environ", {"BW_LANG": "en"}), \
                 mock.patch.object(sys, "argv", ["rig_sample.py", *argv]), \
                 mock.patch.object(rig_sample, "rig_and_table", side_effect=AssertionError("rigged before refusing")):
                with self.assertRaises(SystemExit) as cm:
                    rig_sample.main()
                self.assertIn("--motion", str(cm.exception.code))

    def test_help_follows_screen_language(self):
        """rig_sample.py --help follows the screen language (no Hangul in English).

        `--help` 는 오류 다음에 사용자가 치는 것 — 영어 화면에 한글이 없고 한국어 화면은 한국어."""
        import contextlib, io
        from unittest import mock
        out = {}
        for lang in ("en", "ko"):
            buf = io.StringIO()
            with mock.patch.dict("os.environ", {"BW_LANG": lang}), mock.patch.object(sys, "argv", ["rig_sample.py", "--help"]), \
                 contextlib.redirect_stdout(buf), self.assertRaises(SystemExit):
                rig_sample.main()
            out[lang] = buf.getvalue()
        self.assertIsNone(re.search(r"[가-힣]", out["en"]), out["en"])
        for opt in ("--preset", "--table", "--motion", "pip install bpy==5.2.2"):
            self.assertIn(opt, out["en"]); self.assertIn(opt, out["ko"])
        self.assertIn("절차적 캡슐 인형", out["ko"])


class SampleOutputTests(unittest.TestCase):
    def test_sample_table_is_what_bone_table_prints(self):
        """The checked-in sample table is exactly what the bone table code prints.

        실어 둔 예시 표가 손으로 고쳐지지 않았는지: 표 안의 본 이름으로 표를 다시 만들면 같아야 한다."""
        for doc, count in ((SAMPLE, 73), (DOG, 110)):
            with self.subTest(doc=doc.name):
                part = table_part(doc.read_text(encoding="utf-8"))
                names = [n for row in part.splitlines() if row.startswith("| ") and "`" in row
                         for n in re.findall(r"`([^`]+)`", row)]
                self.assertEqual(count, len(names))
                self.assertEqual(part, rig_sample.bone_table(names).strip())

    def test_dog_sample_has_four_legs(self):
        """The quadruped sample has front/back leg chains and toes on both sides.

        사족 예시가 사람 리그로 잘못 나오지 않았는지: 앞다리·뒷다리 체인과 앞발·뒷발 발가락이 좌우로 있다."""
        names = set(re.findall(r"`(DEF-[^`]+)`", table_part(DOG.read_text(encoding="utf-8"))))
        for s in ("L", "R"):
            for bone in ("thigh", "shin", "foot", "front_thigh", "front_shin", "front_foot", "f_index.01", "r_index.01"):
                self.assertIn(f"DEF-{bone}.{s}", names)
        self.assertFalse({n for n in names if "upper_arm" in n or "forearm" in n})

    def test_wave_bvh_maps_like_the_motion_sample(self):
        """The procedural wave BVH maps like the motion sample and is reproducible.

        절차 BVH 의 관절 이름 매핑(블렌더 불필요)이 리타겟 예시의 '옮긴 본' 표와 같고, 파일은 매번 같다."""
        from bonewright.retarget import bvh_mapping
        mapping = bvh_mapping([j[1] for j in rig_sample.WAVE_JOINTS])
        rows = [f"| `{a}` | `{b}` |" for a, b in sorted(mapping.items())]
        self.assertEqual(rows, [r for r in motion_rows(MOTION.read_text(encoding="utf-8")) if r.startswith("|")])
        with tempfile.TemporaryDirectory() as d:
            a, b = rig_sample.wave_bvh(Path(d) / "a.bvh"), rig_sample.wave_bvh(Path(d) / "b.bvh")
            self.assertEqual(a.read_bytes(), b.read_bytes())
            self.assertIn("Frames: 24", a.read_text())

    def test_sample_output_is_english(self):
        """Sample output documents linked from the English README contain no Hangul.

        영어 README 가 링크하는 예시 문서 — 첫 클릭에서 한국어 페이지를 만나지 않게(주석 포함 한글 없음)."""
        for doc in (SAMPLE, DOG, MOTION, ROOT / "examples" / "README.md"):
            with self.subTest(doc=doc.name):
                text = doc.read_text(encoding="utf-8").replace("[한국어](README.ko.md)", "")   # 언어 바꾸는 링크는 둔다
                self.assertEqual([], re.findall(r"[가-힣]+", text))

    def test_motion_sample_has_no_absolute_path(self):
        text = MOTION.read_text(encoding="utf-8")
        for bad in ("/home/", "/Users/", "C:\\"):
            self.assertNotIn(bad, text)

    @requires_blender
    def test_capsule_doll_still_retargets_like_the_sample(self):
        """Retargeting the capsule doll still matches the motion sample (summary and moved bones).

        리타겟이 바뀌면 예시가 낡는다 — 지금 결과의 요약 줄(프레임·옮긴 본 수)과 옮긴 본 표가 예시와 같은지."""
        rig_sample.rig_and_table(None, "capsule_doll_mcheck", "humanoid")
        now = rig_sample.motion_and_report("capsule_doll_mcheck").read_text(encoding="utf-8")
        self.assertEqual(motion_rows(MOTION.read_text(encoding="utf-8")), motion_rows(now),
                         "다시 만든다: BW_NO_RENDER=1 python3 examples/rig_sample.py --motion → examples/sample-output/")

    @requires_blender
    def test_capsule_doll_still_rigs_like_the_sample(self):
        """Rigging the capsule doll still matches the sample (gate line and deform bone table).

        리그가 바뀌면 예시가 낡는다 — 지금 리깅 결과의 관문 줄과 변형 본 표가 예시와 같은지."""
        out = rig_sample.rig_and_table(None, "capsule_doll_check", "humanoid")
        now, sample = out.read_text(encoding="utf-8"), SAMPLE.read_text(encoding="utf-8")
        gate = [ln for ln in sample.splitlines() if ln.startswith("- gates:")]
        self.assertEqual(gate, [ln for ln in now.splitlines() if ln.startswith("- gates:")],
                         "다시 만든다: BW_NO_RENDER=1 python3 examples/rig_sample.py → examples/sample-output/")
        self.assertEqual(table_part(sample), table_part(now))

    @requires_blender
    def test_capsule_dog_still_rigs_like_the_sample(self):
        out = rig_sample.rig_and_table(None, "capsule_dog_check", "quadruped")
        now, sample = out.read_text(encoding="utf-8"), DOG.read_text(encoding="utf-8")
        gate = [ln for ln in sample.splitlines() if ln.startswith("- gates:")]
        self.assertEqual(gate, [ln for ln in now.splitlines() if ln.startswith("- gates:")],
                         "다시 만든다: BW_NO_RENDER=1 python3 examples/rig_sample.py --preset quadruped → examples/sample-output/")
        self.assertEqual(table_part(sample), table_part(now))


if __name__ == "__main__":
    unittest.main()
