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


def table_part(md: str) -> str:
    """결과 문서에서 '내보낸 GLB 의 변형 본' 표 부분만."""
    return md.split("## 내보낸 GLB 의 변형 본", 1)[1].strip()


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
            self.assertIn("본 3개 · 왼쪽 1 · 오른쪽 1 · 가운데 1", t)
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



class SampleOutputTests(unittest.TestCase):
    def test_sample_table_is_what_bone_table_prints(self):
        """실어 둔 예시 표가 손으로 고쳐지지 않았는지: 표 안의 본 이름으로 표를 다시 만들면 같아야 한다."""
        part = table_part(SAMPLE.read_text(encoding="utf-8"))
        names = [n for row in part.splitlines() if row.startswith("| ") and "`" in row
                 for n in re.findall(r"`([^`]+)`", row)]
        self.assertEqual(73, len(names))
        self.assertEqual(part, rig_sample.bone_table(names).strip())

    @requires_blender
    def test_capsule_doll_still_rigs_like_the_sample(self):
        """리그가 바뀌면 예시가 낡는다 — 지금 리깅 결과의 관문 줄과 변형 본 표가 예시와 같은지."""
        out = rig_sample.rig_and_table(None, "capsule_doll_check", "humanoid")
        now, sample = out.read_text(encoding="utf-8"), SAMPLE.read_text(encoding="utf-8")
        gate = [ln for ln in sample.splitlines() if ln.startswith("- 관문:")]
        self.assertEqual(gate, [ln for ln in now.splitlines() if ln.startswith("- 관문:")],
                         "다시 만든다: BW_NO_RENDER=1 python3 examples/rig_sample.py → examples/sample-output/")
        self.assertEqual(table_part(sample), table_part(now))


if __name__ == "__main__":
    unittest.main()
