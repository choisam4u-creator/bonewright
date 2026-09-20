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
# Quaternius, Ultimate Monsters (50 Models) — CC0. poly.pizza 가 모델별 GLB 를 직접 준다.
# 사람·개과 체형이 **아닌** 몸을 일부러 모았다: 날개 달린 악마(관절 129), 다리 없는 유령, 문어,
# 물고기, 새, 관절 4개짜리 블롭. 일반 리그(`--from-skeleton`)가 이 43종 전부를 리깅하는지 재는 데 쓴다
POLY = "https://static.poly.pizza/{id}.glb"
MONSTERS = {
    "alien": "b048d82a-7fc2-4631-b859-4bde0ed19b59", "alien_blob": "0bb74be9-e9d1-4321-aedb-a9eccecb04a1",
    "alpaking": "acb0f155-4a8a-4084-a2a8-9c17cbff7d21", "alpaking_evolved": "c50fd18d-9441-491b-b2c0-835e6a8757e3",
    "armabee": "de63aaf6-9170-47f7-933d-439af68826a6", "armabee_evolved": "fb7d7a9e-5584-4e0b-a1bf-251fc9946696",
    "birb_blob": "05dac745-bdd0-4169-9e64-f497ca21f69a", "bluedemon": "6fbb8914-bd11-45e1-a906-51ace2ca5d2d",
    "bunny": "084b5ebe-c3eb-4e64-9b17-06e2d1e3da5d", "cactoro": "e88090e2-46af-430b-91e5-ad5520de4939",
    "cactoro_blob": "625862f9-590e-4fbd-88bc-9056047885dd", "cat_blob": "7ccb71fe-dabb-4a6f-a98a-8992bb5e6bc7",
    "chicken_blob": "a0001762-9352-48c3-9abd-be91e42db114", "demon": "46b52ba4-5d2a-4fc8-85cc-3e980f199141",
    "demon_flying": "c2e39eb4-4b8e-4d31-b014-d637bf4e15c6", "dino": "1c1ae302-b948-4de4-961a-44f762b722cf",
    "dragon": "90ed3740-d8c4-4910-88ce-ac2ed426022d", "dragon_fly": "ae5b8510-1fa5-4d53-b943-a4f3b88fb629",
    "fish_blob": "f7d91eb6-da8e-405d-a647-18ff54b97752", "frog": "9018566d-c4e9-4f20-9c99-964622a6e674",
    "ghost": "810f60a2-6e45-4c4e-a0d5-da91cd7288bd", "ghost_skull": "0716bf8e-1894-4a90-8d10-34868975a239",
    "glub_evolved": "27590c4e-41ee-41b5-aaaa-581de0031605", "goleling": "51bf31d7-1aee-4a51-acb1-d667843af205",
    "goleling_evolved": "d6308fbf-fa2e-4cfe-b235-def7ede1ab90", "greenspiky_blob": "cd25a048-719e-4ec4-bbf5-a266776fe129",
    "monkroose": "54ca5c4d-aa20-40ff-a510-25c1c6a48ee9", "mushnub_blob": "55c64684-49a4-4fcc-b393-113126add89b",
    "mushnub_evolved": "84bc88a5-22d8-44e6-af9b-58f8465eb238", "mushroomking": "798301fb-b950-460c-9c67-526621ad8500",
    "ninja_blob": "42162a27-0aaa-40be-b50e-919776021a11", "orc": "52a479b3-a635-4a23-92cb-6697eaa5eed5",
    "orc_blob": "3076c5f7-9bdf-4c27-8083-f280ee6cd64b", "pigeon_blob_eyes": "2ad33f9e-e0d5-4a11-821b-7aafe8d13dd3",
    "pink_blob": "3ddbff73-430c-4ca0-bb25-11211683fbb9", "squidle": "cbe8419d-59d4-4ee8-92f1-8bccb25af378",
    "tribal_flying": "1b4759ca-2c00-4718-90f6-2f84bc8e44f9", "wizard_blob": "d206c071-7934-40eb-9091-35ebdf93c317",
    "yeti": "40a831b3-686a-4af8-b189-a13b38a3c26a", "yeti_blob": "085b078d-b72a-4d8e-a030-000d36c58447",
}
# KayKit, Character Pack: Skeletons 1.0 — CC0(저장소 LICENSE.txt). 살이 없는 뼈 캐릭터 표본
KAYKIT_BASE = ("https://raw.githubusercontent.com/KayKit-Game-Assets/KayKit-Character-Pack-Skeletons-1.0/"
               "main/addons/kaykit_character_pack_skeletons/Characters/gltf/{n}.glb")
KAYKIT = ["Skeleton_Warrior", "Skeleton_Mage", "Skeleton_Minion"]
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
    ap.add_argument("--only", choices=["quadruped", "samples", "monsters"], help="한 종류만 받기")
    a = ap.parse_args()
    out = Path(a.out)
    total = 0
    if a.only in (None, "quadruped"):
        print("사족 10종 (Quaternius, CC0)")
        for name, fid in ANIMALS.items():
            dest = out / "quadruped" / f"{name}.gltf"
            if dest.exists() and dest.stat().st_size > 1024:   # 0바이트·잘린 파일은 다시 받는다
                print(f"  건너뜀 {name} (이미 있음)"); continue
            try:
                n = get(GDRIVE.format(id=fid), dest)
                total += n
                print(f"  받음 {name:10s} {n/1e6:5.1f}MB  {check_skinned(dest)}")
            except Exception as e:
                print(f"  실패 {name}: {e}", file=sys.stderr)
    if a.only in (None, "samples"):
        print("Khronos 샘플")
        for name in SAMPLES:
            dest = out / "samples" / f"{name}.glb"
            if dest.exists() and dest.stat().st_size > 1024:   # 0바이트·잘린 파일은 다시 받는다
                print(f"  건너뜀 {name} (이미 있음)"); continue
            try:
                n = get(KHRONOS.format(n=name), dest)
                total += n
                print(f"  받음 {name:14s} {n/1e6:5.1f}MB")
            except Exception as e:
                print(f"  실패 {name}: {e}", file=sys.stderr)
    if a.only in (None, "monsters"):
        print("비인간·괴물 43종 (Quaternius Ultimate Monsters + KayKit Skeletons, 둘 다 CC0)")
        for name, fid in sorted(MONSTERS.items()):
            dest = out / "monsters" / f"{name}.glb"
            if dest.exists() and dest.stat().st_size > 1024:   # 0바이트·잘린 파일은 다시 받는다
                print(f"  건너뜀 {name} (이미 있음)"); continue
            try:
                n = get(POLY.format(id=fid), dest)
                total += n
                print(f"  받음 {name:20s} {n/1e6:5.1f}MB  {check_skinned(dest)}")
            except Exception as e:
                print(f"  실패 {name}: {e}", file=sys.stderr)
        for name in KAYKIT:
            dest = out / "monsters" / f"kaykit_{name.lower()}.glb"
            if dest.exists() and dest.stat().st_size > 1024:   # 0바이트·잘린 파일은 다시 받는다
                print(f"  건너뜀 {name} (이미 있음)"); continue
            try:
                n = get(KAYKIT_BASE.format(n=name), dest)
                total += n
                print(f"  받음 {name:20s} {n/1e6:5.1f}MB  {check_skinned(dest)}")
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
