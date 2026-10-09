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

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bonewright.i18n import T  # noqa: E402  화면 언어(BW_LANG·로캘)를 따른다

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
# 예전에 손으로 모아 두었던 사람·로봇 자산. 2026-09-20 에 배포처를 다시 확인해 스크립트로 옮겼다.
# 저마다 라이선스가 다르니 아래 표기를 지운 채로 재배포하지 않는다.
CHARACTERS = {
    # 이름: (내려받을 URL, 확장자, 라이선스 — 확인한 근거)
    "mannequiny": ("https://raw.githubusercontent.com/godotengine/godot-demo-projects/master/"
                   "3d/ragdoll_physics/characters/mannequiny.glb", "glb",
                   "CC BY 4.0 · © 2020 GDQuest and contributors — checked against mannequiny.LICENSE.md in the same folder"),
    "godot_player": ("https://raw.githubusercontent.com/godotengine/godot-demo-projects/master/"
                     "3d/platformer/player/player.glb", "glb",
                     "MIT · licence of the godot-demo-projects repository (no asset-specific licence file)"),
    "robot_expressive": ("https://raw.githubusercontent.com/mrdoob/three.js/dev/"
                         "examples/models/gltf/RobotExpressive/RobotExpressive.glb", "glb",
                         "CC0 1.0 · by Tomás Laulhé (Quaternius), modified by Don McCurdy — checked against the model folder's README.md"),
    "rigged_mesh": ("https://raw.githubusercontent.com/BabylonJS/Assets/master/"
                    "meshes/Demos/retargeting/riggedMesh.glb", "glb",
                    "CC BY 4.0 · licence of the BabylonJS/Assets repository"),
    # .gltf 는 버퍼가 밖에 있다 — .bin 을 **원래 이름 그대로** 옆에 둬야 열린다
    "quaternius_ual": ("https://raw.githubusercontent.com/J-Ponzo/gltf-universal-animation-library/main/"
                       "glTF/AnimationLibrary_Godot_Standard.gltf", "gltf",
                       "CC0 1.0 · Quaternius, Universal Animation Library — checked against both the mirror repository's licence "
                       "and quaternius.com/packs/universalanimationlibrary.html"),
}
UAL_BIN = ("https://raw.githubusercontent.com/J-Ponzo/gltf-universal-animation-library/main/"
           "glTF/AnimationLibrary_Godot_Standard.bin")

# **아직 스크립트로 못 받는 4종.** 처음 모을 때 출처를 적어 두지 않아 어디서 받았는지 복원하지 못했다.
# 지문(키·관절 수)만 남긴다 — 같은 파일을 다시 찾으면 여기에 URL 을 채우면 된다.
# 지문(원본 뼈 수·관절 좌표 비율)과 이미 탈락시킨 후보는 docs/bench-unresolved-fingerprints.json 에 있다.
# 후보를 찾으면 `bw bench 후보.glb` 로 돌려 그 파일과 대조하면 1분이면 판정된다.
UNRESOLVED = {
    "kira": "23 source bones · 6 matched · 0.8233 m tall · seated upper-body rig in a room with 30 pieces of furniture · recorded as CC0",
    "alien_bug": "30 source bones · 1 matched · 0.5714 m tall · six-legged insect · recorded as CC0",
    "quat_pp_41j": "41 source bones · 17 matched · 5.5353 m tall · Quaternius character · the asset that used to rig lying on its side",
    "quat_pp_43j": "43 source bones · 15 matched · 2.2239 m tall · Quaternius character · T-pose",
}

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

ATTRIBUTION = """# Benchmark assets: sources and licences

This folder was made by `scripts/fetch_bench_assets.py`. **Do not commit it to the repository.**

## quadruped/ — Quaternius, *Ultimate Animated Animals* (2021-07)
- Licence: **CC0 1.0 Universal** (checked against the License.txt shipped in the pack)
- Source: https://quaternius.com/packs/ultimateanimatedanimals.html
- CC0 needs no attribution; kept as a courtesy: LowPoly Models by @Quaternius
- Bone names are shifted one joint (BackLeg = hip, BackUpperLeg = knee, Back = pelvis, Body = armature origin).
  Checked by coordinates and reflected in QUAD_MAP in `bonewright/bench.py`.

## samples/ — Khronos glTF-Sample-Assets
- Source: https://github.com/KhronosGroup/glTF-Sample-Assets
- Per-model licences below and in each model folder's LICENSE.md
{samples}

## characters/ — five humans and robots (each under its own licence)
{characters}

## Four assets this script cannot download yet
The benchmark scores 66 assets; this script fetches 62. The sources of the four below were not written down when
they were first collected and could not be recovered. If you find the same file again, fill its URL into `CHARACTERS`.

**How to check a candidate**: `docs/bench-unresolved-fingerprints.json` in the repository holds each one's source
bone count and joint-coordinate ratios. Run the candidate with `bw bench candidate.glb` and compare `gt_bones` and
the coordinates. The five recovered assets matched to the decimal this way; the six poly.pizza candidates tried on
2026-09-20 all failed (reasons in the same file).
{unresolved}

## Left out on purpose
- **Mixamo / Adobe**: section 17 of the terms forbids using the content to build, train, test or improve AI systems.
- **Epic's own Fab content** (Paragon, Game Animation Sample, ...): listed as `AI usage allowed: No` (NoAI), and in
  an Unreal-only format that Blender cannot open. **Third-party CC-BY** assets on Fab can be used.
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
        return T("(glb — 확인 생략)", "(glb — not checked)")
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return T(f"읽기 실패: {e}", f"could not read: {e}")
    skins = d.get("skins") or []
    joints = sum(len(s.get("joints", [])) for s in skins)
    return T(f"스킨 {len(skins)} · 관절 {joints}", f"skins {len(skins)} · joints {joints}") if skins else T("뼈대 없음 ⚠", "no skeleton ⚠")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=T("벤치마크 자산을 원저작자 배포처에서 받는다(재배포 아님). 출처·라이선스는 <out>/ATTRIBUTION.md 에 남는다.",
                      "Download the benchmark assets from where their authors publish them (not redistributed). "
                      "Sources and licences are written to <out>/ATTRIBUTION.md."))
    ap.add_argument("--out", default="bench-assets", help=T("받을 폴더(기본 bench-assets)", "folder to download into (default bench-assets)"))
    ap.add_argument("--only", choices=["quadruped", "samples", "monsters", "characters"],
                    help=T("한 종류만 받기", "download one group only"))
    a = ap.parse_args()
    out = Path(a.out)
    total = 0
    if a.only in (None, "quadruped"):
        print(T("사족 10종 (Quaternius, CC0)", "10 quadrupeds (Quaternius, CC0)"))
        for name, fid in ANIMALS.items():
            dest = out / "quadruped" / f"{name}.gltf"
            if dest.exists() and dest.stat().st_size > 1024:   # 0바이트·잘린 파일은 다시 받는다
                print(T(f"  건너뜀 {name} (이미 있음)", f"  skip {name} (already there)")); continue
            try:
                n = get(GDRIVE.format(id=fid), dest)
                total += n
                print(T("  받음 ", "  got ") + f"{name:10s} {n/1e6:5.1f}MB  {check_skinned(dest)}")
            except Exception as e:
                print(T(f"  실패 {name}: {e}", f"  failed {name}: {e}"), file=sys.stderr)
    if a.only in (None, "samples"):
        print(T("Khronos 샘플", "Khronos samples"))
        for name in SAMPLES:
            dest = out / "samples" / f"{name}.glb"
            if dest.exists() and dest.stat().st_size > 1024:   # 0바이트·잘린 파일은 다시 받는다
                print(T(f"  건너뜀 {name} (이미 있음)", f"  skip {name} (already there)")); continue
            try:
                n = get(KHRONOS.format(n=name), dest)
                total += n
                print(T("  받음 ", "  got ") + f"{name:14s} {n/1e6:5.1f}MB")
            except Exception as e:
                print(T(f"  실패 {name}: {e}", f"  failed {name}: {e}"), file=sys.stderr)
    if a.only in (None, "monsters"):
        print(T("비인간·괴물 43종 (Quaternius Ultimate Monsters + KayKit Skeletons, 둘 다 CC0)",
                "43 non-humans and monsters (Quaternius Ultimate Monsters + KayKit Skeletons, both CC0)"))
        for name, fid in sorted(MONSTERS.items()):
            dest = out / "monsters" / f"{name}.glb"
            if dest.exists() and dest.stat().st_size > 1024:   # 0바이트·잘린 파일은 다시 받는다
                print(T(f"  건너뜀 {name} (이미 있음)", f"  skip {name} (already there)")); continue
            try:
                n = get(POLY.format(id=fid), dest)
                total += n
                print(T("  받음 ", "  got ") + f"{name:20s} {n/1e6:5.1f}MB  {check_skinned(dest)}")
            except Exception as e:
                print(T(f"  실패 {name}: {e}", f"  failed {name}: {e}"), file=sys.stderr)
        for name in KAYKIT:
            dest = out / "monsters" / f"kaykit_{name.lower()}.glb"
            if dest.exists() and dest.stat().st_size > 1024:   # 0바이트·잘린 파일은 다시 받는다
                print(T(f"  건너뜀 {name} (이미 있음)", f"  skip {name} (already there)")); continue
            try:
                n = get(KAYKIT_BASE.format(n=name), dest)
                total += n
                print(T("  받음 ", "  got ") + f"{name:20s} {n/1e6:5.1f}MB  {check_skinned(dest)}")
            except Exception as e:
                print(T(f"  실패 {name}: {e}", f"  failed {name}: {e}"), file=sys.stderr)
    if a.only in (None, "characters"):
        print(T("사람·로봇 5종 (라이선스 제각각 — ATTRIBUTION.md 참고)", "5 humans and robots (licences differ — see ATTRIBUTION.md)"))
        for name, (url, ext, lic) in CHARACTERS.items():
            dest = out / "characters" / f"{name}.{ext}"
            if dest.exists() and dest.stat().st_size > 1024:   # 0바이트·잘린 파일은 다시 받는다
                print(T(f"  건너뜀 {name} (이미 있음)", f"  skip {name} (already there)")); continue
            try:
                n = get(url, dest)
                total += n
                if name == "quaternius_ual":   # 외부 버퍼를 원래 이름으로 같이 받는다
                    total += get(UAL_BIN, dest.parent / "AnimationLibrary_Godot_Standard.bin")
                print(T("  받음 ", "  got ") + f"{name:18s} {n/1e6:5.1f}MB  {check_skinned(dest)}")
            except Exception as e:
                print(T(f"  실패 {name}: {e}", f"  failed {name}: {e}"), file=sys.stderr)
        print(T(f"  ⚠ 아직 못 받는 자산 {len(UNRESOLVED)}종: {', '.join(UNRESOLVED)} — 출처 기록이 없다",
                f"  ⚠ {len(UNRESOLVED)} assets cannot be downloaded yet: {', '.join(UNRESOLVED)} — no record of their source"))
    out.mkdir(parents=True, exist_ok=True)
    (out / "ATTRIBUTION.md").write_text(
        ATTRIBUTION.format(
            samples="\n".join(f"- `{k}.glb` — {v}" for k, v in SAMPLES.items()),
            characters="\n".join(f"- `{k}.{e}` — {lic}\n  - source: {u}" for k, (u, e, lic) in CHARACTERS.items()),
            unresolved="\n".join(f"- `{k}` — {v}" for k, v in UNRESOLVED.items())), encoding="utf-8")
    print(T(f"\n총 {total/1e6:.1f}MB → {out}  (출처·라이선스는 {out}/ATTRIBUTION.md)",
            f"\ntotal {total/1e6:.1f}MB → {out}  (sources and licences in {out}/ATTRIBUTION.md)"))
    print(T("사족 벤치:  ", "quadruped bench:  ") + "bw bench " + str(out / "quadruped") + "/*.gltf --preset quadruped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
