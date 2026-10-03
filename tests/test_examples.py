"""examples/rig_sample.py 의 표 부분(블렌더 불필요). 리깅 부분은 RigMockTests 가 같은 경로를 이미 본다."""
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))
import rig_sample  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
