"""사용자에게 보이는 문구의 언어. BW_LANG(ko|en)이 먼저, 없으면 로캘이 ko 로 시작할 때만 한국어, 나머지는 영어.

도움말·`bw doctor`·`BLOCKED:` 오류 메시지·게이트 거절 사유(gates.py)가 이걸 따른다. 모델 프롬프트 언어(`bw rig --lang`)와는 따로다.
진행 로그와 Blender 스크립트 안의 메시지는 아직 한국어뿐이다."""
import os


def lang() -> str:
    v = os.environ.get("BW_LANG") or os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES") or os.environ.get("LANG") or ""
    return "ko" if v.lower().startswith("ko") else "en"


def T(ko: str, en: str) -> str:
    return ko if lang() == "ko" else en
