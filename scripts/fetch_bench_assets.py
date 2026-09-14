#!/usr/bin/env python3
"""벤치마크 자산 내려받기(토큰 0).

자산은 저장소에 커밋하지 않는다 — 라이선스가 재배포를 허용하지 않기 때문이다. 이 스크립트가 원저작자의
공개 배포처에서 직접 받아오고, 받은 자리에 출처·라이선스를 적은 ATTRIBUTION.md 를 남긴다.

**쓰지 않는 자산**: 믹사모/Adobe(약관 17조가 콘텐츠로 AI 시스템 테스트를 금지), 에픽 자체 Fab 콘텐츠
(리스팅이 'AI 사용 허용: 아니요'이고 포맷이 언리얼 전용).
"""
import argparse
import json
import sys
import urllib.request
from pathlib import Path

UA = {"User-Agent": "bonewright-bench-fetch/0.2 (+https://github.com/)"}

KHRONOS = "https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Assets/main/Models/{n}/glTF-Binary/{n}.glb"
# Quaternius, Ultimate Animated Animals (2021-07) — CC0 1.0. 공개 구글 드라이브 폴더의 glTF 하위 폴더.
GDRIVE = "https://drive.usercontent.google.com/download?id={id}&export=download&confirm=t"
ANIMALS = {
    "Alpaca": "13dxCPosR1tVx24LKXr6gN44sIOY4hZgo", "Bull": "1M9gyr2UikIDW_Ynp-OfgiK-JjI7ziPd3",
    "Cow": "1lS3t1Sof0FVne1C1WXfdX48qaHES_pDG", "Deer": "1iGpXKrqYGyZCPGHPPSuDAoKnOXLhXJ0q",
    "Donkey": "1Buic-_4vNtmwN0rtMHcdWw3TEaSPz4iW", "Horse": "1hbtY8kxnXiPdwYGVY7rWRgU0jl_-Q-LG",
    "Husky": "1oYn47mfq9JAdkJJDcUftbhHNsgQ_CWdt", "ShibaInu": "1XWUVbmMbiG9E90OqrumueD_pBdnYdyHZ",
    "Stag": "1URNoFeIFblJXPFOV6qwPrxZr5dLZ3YGx", "Wolf": "1lFQoQ9ln2Z2wGuFFWObj9i5jHqUl_ftG",
}
# Khronos glTF-Sample-Assets — 모델마다 라이선스가 다르다(LICENSE.md 에 원저작자 표기)
SAMPLES = {"Fox": "CC-BY 4.0 (PixelMannen / tomkranis)", "CesiumMan": "CC-BY 4.0 (Cesium)",
           "RiggedFigure": "CC-BY 4.0 (Khronos)", "RiggedSimple": "CC-BY 4.0 (Khronos)"}

ATTRIBUTION = """# 벤치마크 자산 출처와 라이선스

이 폴더는 `scripts/fetch_bench_assets.py` 가 만든 것이다. **저장소에 커밋하지 않는다.**

## quadruped/ — Quaternius, *Ultimate Animated Animals* (2021-07)
- 라이선스: **CC0 1.0 Universal** (팩에 동봉된 License.txt 원문 확인)
- 출처: https://quaternius.com/packs/ultimateanimatedanimals.html
- CC0 라 귀속 의무는 없지만 예의로 남긴다: LowPoly Models by @Quaternius
- 뼈 이름 주의: 이름이 관절보다 한 칸 밀려 있다(BackLeg=고관절, BackUpperLeg=무릎, Back=골반,
  Body 는 아마추어 원점). 좌표로 확인한 값이며 `bonewright/bench.py` 의 QUAD_MAP 에 반영돼 있다.

## samples/ — Khronos glTF-Sample-Assets
- 출처: https://github.com/KhronosGroup/glTF-Sample-Assets
- 모델별 라이선스는 아래와 각 모델 폴더의 LICENSE.md 참고
{samples}

## 일부러 뺀 것
- **믹사모/Adobe**: 약관 17조가 콘텐츠로 AI 시스템을 만들거나 훈련·테스트·개선하는 것을 금지한다.
- **에픽 자체 Fab 콘텐츠**(파라곤, Game Animation Sample 등): 리스팅에 `AI 사용 허용: 아니요`(NoAI)이고
  포맷이 언리얼 전용이라 블렌더로 열 수도 없다. Fab 의 **제3자 CC-BY** 자산은 쓸 수 있다.
"""


def get(url: str, dest: Path) -> int:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return len(data)


def check_skinned(p: Path) -> str:
    """받은 파일에 실제로 뼈대가 들어 있는지 본다(정답 대조 벤치는 원본 뼈대가 있어야 한다)"""
    if p.suffix.lower() != ".gltf":
        return "(glb — 확인 생략)"
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return f"읽기 실패: {e}"
    skins = d.get("skins") or []
    return f"스킨 {len(skins)} · 관절 {sum(len(s.get('joints', [])) for s in skins)}" if skins else "뼈대 없음 ⚠"


def main() -> int:
    ap = argparse.ArgumentParser(description="벤치마크 자산을 원저작자 배포처에서 받는다(재배포 아님)")
    ap.add_argument("--out", default="bench-assets", help="받을 폴더(기본 bench-assets)")
    ap.add_argument("--only", choices=["quadruped", "samples"], help="한 종류만 받기")
    a = ap.parse_args()
    out = Path(a.out)
    total = 0
    if a.only != "samples":
        print("사족 10종 (Quaternius, CC0)")
        for name, fid in ANIMALS.items():
            dest = out / "quadruped" / f"{name}.gltf"
            if dest.exists():
                print(f"  건너뜀 {name} (이미 있음)"); continue
            try:
                n = get(GDRIVE.format(id=fid), dest)
                total += n
                print(f"  받음 {name:10s} {n/1e6:5.1f}MB  {check_skinned(dest)}")
            except Exception as e:
                print(f"  실패 {name}: {e}", file=sys.stderr)
    if a.only != "quadruped":
        print("Khronos 샘플")
        for name in SAMPLES:
            dest = out / "samples" / f"{name}.glb"
            if dest.exists():
                print(f"  건너뜀 {name} (이미 있음)"); continue
            try:
                n = get(KHRONOS.format(n=name), dest)
                total += n
                print(f"  받음 {name:14s} {n/1e6:5.1f}MB")
            except Exception as e:
                print(f"  실패 {name}: {e}", file=sys.stderr)
    out.mkdir(parents=True, exist_ok=True)
    (out / "ATTRIBUTION.md").write_text(
        ATTRIBUTION.format(samples="\n".join(f"- `{k}.glb` — {v}" for k, v in SAMPLES.items())), encoding="utf-8")
    print(f"\n총 {total/1e6:.1f}MB → {out}  (출처·라이선스는 {out}/ATTRIBUTION.md)")
    print("사족 벤치:  bw bench " + str(out / "quadruped") + "/*.gltf --preset quadruped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
