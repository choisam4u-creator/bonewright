"""시험 표시. 블렌더가 필요한 시험에는 `@requires_blender` 를 붙인다.

- 기본: Blender(앱 또는 `bpy` 휠)가 없으면 건너뛴다.
- `BW_SKIP_BLENDER=1`: 있어도 건너뛴다(빠른 확인용, Mac 에서 7분 → 1초).
- `BW_REQUIRE_BLENDER=1`: 없으면 **실패**한다. CI 의 blender 잡이 몰래 건너뛰고 초록불이 되는 것을 막는다.
"""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bonewright import blender  # noqa: E402


def blender_available():
    return bool(blender.find_blender({}) or blender.has_bpy_module())


def requires_blender(obj):
    obj._requires_blender = True   # tests/test_docs.py 가 CONTRIBUTING 의 건너뜀 수를 대조할 때 센다
    if os.environ.get("BW_SKIP_BLENDER") == "1":
        return unittest.skip("BW_SKIP_BLENDER=1")(obj)
    if blender_available():
        return obj
    if os.environ.get("BW_REQUIRE_BLENDER") == "1":
        raise RuntimeError("BW_REQUIRE_BLENDER=1 인데 Blender 가 없다 — `pip install bpy==5.2.2`(파이썬 3.13) "
                           "또는 BW_BLENDER 환경 변수에 블렌더 실행 파일 경로를 넣는다")
    return unittest.skip("Blender 없음")(obj)
