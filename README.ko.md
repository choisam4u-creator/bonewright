# bonewright

**캐릭터 메시(`.glb` / `.gltf`)를 넣으면 애니메이션할 수 있는 블렌더 리그를 돌려준다** — Rigify 컨트롤,
모든 버텍스의 스킨 웨이트, 그리고 결과를 믿으면 안 될 때 알려 주는 통과/거부 게이트.
파이썬이 단계를 돌리고, `codex exec`가 판정하고, 게이트가 검증한다. [English](README.md)

<p align="center">
  <img src="docs/media/rig-views.png" width="860" alt="메시를 투과해 정면·측면·3/4에서 본 Rigify 리그">
</p>

## 무엇을 해 주나

- 뼈대 없는 메시(T·A 포즈)로 **사람과 네발짐승을 리깅**한다. 파일에 이미 뼈대가 있으면 그것을 쓴다.
  결과 예시: [캡슐 인형](examples/sample-output/capsule_doll.md)(변형 본 73개)·[네 발 캡슐 개](examples/sample-output/capsule_dog.md)(110개), 둘 다 절차 생성.
- 팔다리가 있는 **그 밖의 모든 것**(곤충, 괴물)은 메시 모양에서 뽑은 본 체인으로 리깅한다.
- 제대로 리깅할 수 없는 메시는 망가진 리그를 주는 대신 **거부**한다(`--force`로 무시 가능).
- BVH 동작을 새 리그에 **리타깃**하고, 게임용 GLB로 **내보낸다**.

## 설치

파이썬 3와 Blender 5.2 LTS(또는 `bpy` 휠)가 필요하다. CLI 자체는 의존성이 없다.

```bash
git clone https://github.com/choisam4u-creator/bonewright && cd bonewright
python3 -m venv .venv && source .venv/bin/activate   # Homebrew·리눅스 파이썬은 전역 pip install 을 거절한다(PEP 668)
pip install .                 # Blender.app 대신 bpy 휠을 쓰려면: pip install ".[headless]" (Python 3.13)
bw doctor                     # Blender 나 bpy 중 하나가 잡히는지 확인하고, 선택 항목을 표시
```

Windows 에서는 둘째 줄이 `py -m venv .venv` 다음 `.venv\Scripts\activate` 다. 새 터미널에서는 `bw` 전에 venv 를 다시
켠다.

## 첫 실행

먼저 저장소에 든 캐릭터로 확인해 본다 — 모델·codex 없이, 토큰 0:

```bash
bw rig tests/assets/quaternius_adventurer.glb --from-skeleton --no-judge   # 파일에 든 뼈대를 그대로 쓴다
bw rig character.glb          # 내 메시; 결과는 runs/<run-id>/ 에 (보고서 경로가 출력됨)
bw demo <run-id>              # IK 컨트롤로 움직이는 mp4/gif (run-id 를 넣은 이 명령이 `bw rig` 끝 "다음:" 줄에 나온다)
bw export <run-id>            # 변형 본만 남긴 GLB + 스킨, 다시 불러와 검사
```

| 파일 | 명령 |
|---|---|
| 사람·개 비율, 뼈대 없음 | `bw rig x.glb` (동물은 `--preset quadruped`) |
| 이미 뼈대가 있음 | `bw rig x.glb --from-skeleton` (맞춤 호출 없음, `--no-judge` 를 더하면 토큰 0) |
| 뼈대 없고 맞는 프리셋도 없음 | `bw rig x.glb --from-shape` |

`bw rig` 한 번은 모델 호출 2회(약 1달러)다: 맞춤(fit)과 시각 판정(judge). `--from-skeleton`·`--from-shape` 는 맞춤 호출을,
`--no-judge` 는 판정을, `BW_BACKEND=mock` 은 둘 다 건너뛴다. 그래서 앞의 둘 중 하나에 `--no-judge` 를 붙이면 codex 가 아예 필요 없다.

**언어.** `bw --help` 는 로캘이 `ko_*` 이거나 `BW_LANG=ko` 면 한국어, 아니면 영어다. `bw doctor` 출력과 `BLOCKED:` 오류 메시지도 같다. `BLOCKED:` 아래 나열되는 게이트 거절 사유와 `bw rig`·`bw motion` 진행 로그와 Blender 스크립트 안에서 나온 분석 경고·오류, `bw bench` 표와 실행 보고서(`report.md`)도 같다.

**설정.** 같은 옵션을 매번 붙이기 싫으면 프로젝트 폴더의 `runs/config.json` 에 적어 둔다. 예를 들어
`{"lang": "en", "rig": {"rest_pose": "t"}}` 는 모델 프롬프트 언어를 고정하고 매번 T자 쉬는 자세로 굽는다.
명령줄 옵션이 파일보다 앞선다. 키와 기본값: [안내서 → Settings](docs/GUIDE.md#settings-runsconfigjson).

## 결과 예시

<table>
<tr><th width="50%">자체 IK 컨트롤로 움직인 리그</th><th width="50%">같은 리그에 BVH 걷기를 입힘</th></tr>
<tr>
<td><img src="docs/media/rig-ik.gif" width="320" alt="두 손을 들고 무릎을 올리고 도는 캐릭터"></td>
<td><img src="docs/media/walk-retarget.gif" width="320" alt="BVH에서 리타깃한 걷기"></td>
</tr>
</table>

`bw rig mannequiny.glb`: 버텍스 7,136개 → 본 410개(변형 본 73개), 모든 버텍스에 웨이트, 게이트 전부 통과.
벤치마크에서 **66개 중 63개**가 게이트를 전부 통과했고, 걸을 수 있는 29개 중 **25개**가 걷기 리타깃을
깨끗하게 받았다(`python3 scripts/bench_score.py`).
리타깃을 내려받는 것 없이 직접 확인하려면 [리타깃 결과 예시](examples/sample-output/capsule_doll_motion.md)를 본다
(`python3 examples/rig_sample.py --motion`: 절차 생성 손 흔들기 BVH 24프레임, 관절 19개 중 18개를 옮김).

상태: **v0.2(알파)**. macOS에서 개발, Linux는 CI에서 시험을 돌린다, Windows는 CI에서 블렌더 없는 시험만 돌고 손으로 써 본 적은 없다.

## 더 보기

- **[전체 안내서](docs/GUIDE.md)**(영어) — 모든 옵션, 관절을 찾는 방법, 거부 게이트, 동작 리타깃,
  벤치마크와 그 숫자가 뜻하는 것과 뜻하지 않는 것.
- [examples/](examples/README.ko.md) — 메시 → 리그(본 개수·이름 표)를 토큰 0으로 재현. [결과 예시](examples/sample-output/capsule_doll.md)를 먼저 볼 수 있다.
- [CHANGELOG.md](CHANGELOG.md) · [CONTRIBUTING.md](CONTRIBUTING.md) · [SECURITY.md](SECURITY.md)

## 라이선스

**MIT, 단 `bonewright/bpy_scripts/`는 GPL-3.0-or-later**(`import bpy`하는 코드는 Blender의 파생 저작물이다.
`scripts/check_license_boundary.py`가 CI에서 경계를 강제한다). `docs/media/`의 렌더 이미지는 다른 사람의
메시(CC BY 4.0, CC0)에서 나왔다 — [docs/media/ATTRIBUTION.md](docs/media/ATTRIBUTION.md) 참고.
