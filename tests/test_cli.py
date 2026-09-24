"""명령줄 입력 검증 회귀 테스트."""
import io
import sys
import unittest
from unittest.mock import patch

from bonewright import cli


class PinInputTests(unittest.TestCase):
    def test_rejects_malformed_pins_before_starting_rig(self):
        for pin in ("=0,0,1", "hand.L=0,0,1/1,0,1/2,0,1",
                    "hand.L=nan,0,1", "hand.L=0,inf,1"):
            with self.subTest(pin=pin), patch.object(sys, "argv", ["bw", "rig", "mesh.glb", "--pin", pin]), \
                    patch.object(cli.pipeline, "rig") as rig, patch("sys.stderr", new_callable=io.StringIO):
                with self.assertRaises(SystemExit):
                    cli.main()
                rig.assert_not_called()

    def test_accepts_finite_head_and_tail(self):
        with patch.object(sys, "argv", ["bw", "rig", "mesh.glb", "--pin", "hand.L=0,0,1/1,0,1"]), \
                patch.object(cli.pipeline, "rig", return_value="report") as rig, \
                patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(cli.main(), 0)
        self.assertEqual(rig.call_args.kwargs["pins"],
                         {"hand.L": {"head": [0.0, 0.0, 1.0], "tail": [1.0, 0.0, 1.0]}})


if __name__ == "__main__":
    unittest.main()
