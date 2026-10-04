# 클라우드 회차 기록

## 2026-10-04 (2회차)

**한 일**
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main(PR #3 병합분) 빨리감기 병합.
- 이슈 템플릿: `install-problem.md`(설치·`bw doctor`), `feature-request.md` 추가, `config.yml` 은 빈 이슈를 끄고
  사용 질문 → `docs/GUIDE.md`, 보안 → `SECURITY.md` 로 안내(Discussions 는 켜져 있는지 몰라 링크 안 함). `bw --version` 추가.
- 예상 못 한 오류: 포괄 `except` 가 이제 오류 종류(`KeyError: ...`)·실행의 `logs/` 폴더·`BW_DEBUG=1`(트레이스백)·이슈 템플릿을 알림.
- 영어 사용자: `bw --help` 를 `BW_LANG`(없으면 로캘)에 따라 — `ko*` 면 한국어, 아니면 영어. 오류 메시지·`bw doctor` 는
  아직 한국어뿐임을 README·README.ko 에 적음(영문화는 새 백로그 항목).
- `tests/test_docs.py`: README·README.ko·GUIDE·examples/README 상대 링크 31개, 문서 속 `bw` 명령 57개를 실제 파서와 대조. CI 두 잡에 포함.
  이 과정에서 `cli.build_parser()` 로 파서 생성을 분리.
- 백로그 남은 항목 1개(`examples/sample-output` — Mac 결과물이 필요해 클라우드에서 못 함) → 새 항목 5개(근거 포함) 추가.

**돌린 시험**
- `python3 -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release tests.test_docs`
  — 64개 중 52개 통과, 12개 건너뜀('Blender 없음': 클라우드에 Blender·bpy 없음 — `RigMockTests`).
- 새 venv 에 `pip install .` → `bw --version`, 영어 `bw --help`, `bw rig 없는파일.glb` 종료코드 2 확인.
- `python3 scripts/check_license_boundary.py` — OK.

**Mac에서 확인할 것**
```bash
git fetch && git checkout claude/cloud-work && BW_REQUIRE_BLENDER=1 python3 -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release tests.test_docs
bw --help; BW_LANG=ko bw --help; bw --version     # 한국어 로캘 Mac 이면 첫 줄도 한국어가 맞다
python3 examples/rig_sample.py && mkdir -p examples/sample-output && cp examples/out/capsule_doll.md examples/sample-output/   # 백로그 남은 항목용
```

## 2026-10-04

**한 일**
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main(PR #2 병합분) 빨리감기 병합.
- 백로그 4번: 오류 메시지에 고칠 방법(`→` 줄). 메시·`--targets`·`--map`·`--bvh`·리그 run-id 를 Blender 호출 **전에** 확인
  (`pipeline.need_file`/`need_rig`). 없는 명령 `bw resume` 안내를 재실행·`--targets` 재사용으로 고침. `bw status <없는 id>` 종료코드 2.
  타입 힌트 보강. `tests/test_errors.py`(7개).
- 백로그 5번: `docs/PRE-PUBLIC-AUDIT.md` — 비밀 값 없음. 개인 경로는 git 기록(문서 2개, d6091c2 이전)에만,
  **GitHub 웹 병합 커밋 2개에 개인 gmail 주소**. 에셋 라이선스 표기는 다 있음(`walk_wave.bvh` 생성 모델 표기 보강 권장). 지운 것 없음.
- 백로그 6번: CHANGELOG 정리(0.2.0 에 실린 내용을 `[0.2.0] - 2026-09-20` 로 옮기고 Unreleased 채움, 비교 링크),
  `docs/RELEASING.md`, `tests/test_release.py`(버전 3곳 일치). plugin.json 0.1.0 → 0.2.0. 다음 버전 제안 **0.2.1**, 태그 안 만듦.
- 추가 1건: pip 설치본에서 `bw plugin-path` 가 없는 `site-packages/plugin` 을 가리키던 버그 → 휠에 `bonewright/_plugin` 으로 실음. CI 에서 확인.
- 백로그 남은 항목 0 → 공개 준비 기준 새 항목 5개(근거 포함) 추가.

**돌린 시험**
- `python3 -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release` — 54개 중 42개 통과,
  12개 건너뜀('Blender 없음': 클라우드에 Blender·bpy 없음 — `RigMockTests` 의 리그·스키닝·리타겟 시험).
- 새 venv 에 `pip install .` → 저장소 밖에서 `bw plugin-path` 가 `.../bonewright/_plugin` (`.codex-plugin/plugin.json` 있음) 확인.
- `python3 scripts/check_license_boundary.py` — OK. 워크플로 YAML 구문 확인.

**Mac에서 확인할 것**
```bash
git fetch && git checkout claude/cloud-work && BW_REQUIRE_BLENDER=1 python3 -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release
bw rig 없는파일.glb; bw export 없는id; bw status 없는id   # 셋 다 Blender 없이 바로 BLOCKED + "→" 안내
```
그리고 `docs/PRE-PUBLIC-AUDIT.md` 의 "판단 필요" 2건(기록 속 개인 경로, 병합 커밋 개인 메일)은 샘님 결정.

## 2026-10-03

**한 일**
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. main이 앞서 있지 않아 병합 없음.
- 백로그 3번: `examples/rig_sample.py` — 캡슐 인형(기본)·`adventurer`(CC0)·임의 GLB를 mock으로 리깅하고
  내보낸 `rigged.glb`의 변형 본을 순수 파이썬으로 읽어 개수·좌우·부위별 이름 표를 `examples/out/<이름>.md`로 쓴다.
  `--table x.glb`는 블렌더 없이 표만. 무거운 자산은 기존 `scripts/fetch_bench_assets.py` 안내. `examples/out/`은 git 제외.
- `tests/test_examples.py`(블렌더 불필요 3개) 추가, CI 두 잡에 포함. README·README.ko에 링크.

**돌린 시험**
- `python3 -m unittest tests.test_mock tests.test_cli tests.test_examples` — 44개 중 32개 통과, 12개 건너뜀('Blender 없음': 클라우드에 Blender·bpy 없음).
- `python3 examples/rig_sample.py --table adventurer` — 원본 스킨 본 62개 표 확인. 리깅 경로는 블렌더가 없어 못 돌림.
- `python3 scripts/check_license_boundary.py` — OK.

**Mac에서 확인할 것**
```bash
git fetch && git checkout claude/cloud-work && python3 examples/rig_sample.py && python3 examples/rig_sample.py adventurer
cat examples/out/capsule_doll.md examples/out/adventurer.md   # 관문 ok, 변형 본 60~120개, 이름 표가 말이 되는지
```

## 2026-10-02

**한 일**
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main 병합(latest.md 들어옴, 충돌 없음).
- 백로그 2번: 블렌더 필요 시험 표시를 `tests/_marks.py`의 `@requires_blender`로 통일.
  `BW_SKIP_BLENDER=1`(빠른 확인), `BW_REQUIRE_BLENDER=1`(없으면 실패) 추가. `tests/README.md`에 구분 표.
- CI: bpy 헤드리스 잡은 이미 있었음. 두 잡 모두 `tests.test_cli`도 돌리고, blender 잡엔 `BW_REQUIRE_BLENDER=1`을 걸어
  bpy가 안 올라오면 건너뛰지 않고 실패하게 함.

**돌린 시험**
- `python3 -m unittest tests.test_mock tests.test_cli` — 41개 중 29개 통과, 12개 건너뜀('Blender 없음': 클라우드에 Blender·bpy 없음).
- `BW_SKIP_BLENDER=1` → 12개 건너뜀 확인, `BW_REQUIRE_BLENDER=1` → 블렌더 없어 실패하는 것 확인.
- `python3 scripts/check_license_boundary.py` — OK.
- CI blender 잡 실제 결과는 이 푸시의 Actions에서 확인 필요(클라우드에서 bpy 설치 안 함).

**Mac에서 확인할 것**
```bash
git fetch && git checkout claude/cloud-work && BW_REQUIRE_BLENDER=1 python3 -m unittest tests.test_mock tests.test_cli  # 41개 통과, 건너뜀 0
BW_SKIP_BLENDER=1 python3 -m unittest tests.test_mock tests.test_cli  # 1초 안에 29개 통과, 12개 건너뜀
```

## 2026-09-26

**한 일**
- `docs/test-reports/latest.md` 없음 → FAIL 확인 불가, 백로그로 진행.
- `docs/CLOUD-BACKLOG.md` 새로 만듦.
- README 재구성: 44.7KB 원문을 `docs/GUIDE.md`로 옮김(링크 경로만 고침). 새 `README.md`(3.4KB)는
  무엇을 해 주나/설치/첫 실행/결과 예시/라이선스 요약만. 한국어판 `README.ko.md` 추가.

**돌린 시험**
- `python3 -m unittest tests.test_mock tests.test_cli` — 41개 중 29개 통과, 12개 건너뜀('Blender 없음': 클라우드에 Blender·bpy 없음).
- `python3 scripts/check_license_boundary.py` — OK.

**Mac에서 확인할 것**
```bash
git fetch && git checkout claude/cloud-work && python3 -m unittest tests.test_mock tests.test_cli
open README.md docs/GUIDE.md   # 이미지·링크가 깨지지 않았는지 GitHub 미리보기로 확인
```
