# 클라우드 회차 기록

## 2026-10-06

**한 일**
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main(PR #6 병합분) 빨리감기 병합.
- **이번 회차부터 클라우드에서도 `pip install bpy==5.2.2`(python3.13 venv)가 된다** → 블렌더 시험까지 전부 돌렸다.
- `examples/sample-output/capsule_doll.md`: 인자 없이 `rig_sample.py` 를 돌린 결과(변형 본 73·리그 본 410)를 싣고
  README·README.ko·examples/README 에서 링크. 시험 2개(표 손상 여부, 지금 리깅 결과와 대조 — 후자는 블렌더 필요).
  `test_docs` 의 블렌더 시험 수 대조가 메서드 단위 `@requires_blender` 도 세게 고침.
- kimodo.cpp 빌드 안내를 `docs/GUIDE.md` "Text → motion: building kimodo.cpp (optional)" 로 옮김(원본 저장소
  localai-org/kimodo.cpp, macOS 빌드 명령, 필요한 세 경로, `runs/config.json` 의 `kimodo.root`, 가중치 라이선스).
  `bw motion --text` 오류·`bw doctor` 가 이 절을 가리킨다. 시험 2개. 빌드 명령은 원본 README(preset `release`)와
  10/1 기록(`KIMODO_ENABLE_VULKAN=OFF`)을 합친 것이라 Mac 에서 한 번 따라 해 봐야 한다.
- 진행 로그 영문화: `pipeline._log` 30여 곳과 codex 대기 표시를 `T()` 로. 시험 1개(AST: `_log` 인자에 T() 밖 한글 없음).
  `BW_LANG=en BW_BACKEND=mock` 리깅 출력에서 남은 한글은 Blender 스크립트(analyze)의 suspect 문구 1줄 → 새 백로그.
- `docs/media/ATTRIBUTION.md`: `walk_wave.bvh` 생성 모델(kimodo.cpp)·가중치(SOMA RP v1.1, NVIDIA Open Model License).
  관절 30개 = SOMA 골격으로 확인. PRE-PUBLIC-AUDIT 4절 갱신.
- 백로그 남은 항목 0개 → 새 항목 5개(근거 포함) 추가, 그중 1개(위 ATTRIBUTION) 처리. CHANGELOG 갱신.

**돌린 시험**
- `BW_REQUIRE_BLENDER=1 BW_NO_RENDER=1 python -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release tests.test_docs tests.test_i18n`
  (bpy 5.2.2 LTS, Python 3.13) — **88개 모두 통과, 건너뜀 0**(151초). `BW_SKIP_BLENDER=1` — 88개 중 13개 건너뜀, 나머지 통과.
- `python3 scripts/check_license_boundary.py` — OK(MIT 15개 파일). `python3.11 -m py_compile` 로 고친 파일 3.11 호환 확인.
- 렌더(`BW_NO_RENDER` 없이)는 안 돌렸다: 화면 없는 리눅스에서 렌더러가 죽는다(CI 와 같은 이유).

**Mac에서 확인할 것**
```bash
git fetch && git checkout claude/cloud-work && python3 -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release tests.test_docs tests.test_i18n
BW_LANG=en BW_BACKEND=mock bw rig tests/assets/quaternius_adventurer.glb --no-judge   # 진행 로그 영어인지
BW_LANG=en bw doctor   # kimodo 줄이 GUIDE 절을 가리키는지; GUIDE 의 kimodo 빌드 명령이 실제와 맞는지 한 번 대조
```

## 2026-10-05 (2회차)

**한 일**
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main(PR #5 병합분) 빨리감기 병합.
- Windows: `find_blender` 가 `<ProgramFiles>\Blender Foundation\Blender X.Y\blender.exe` 중 가장 높은 판을 찾는다(시험 2개).
  CI 에 `unit-windows`(windows-latest, Python 3.13, `PYTHONUTF8=1`) 추가 — run 48 에서 통과. README·GUIDE 의 Windows 문구 정정.
- 게이트 거절 사유(`gates.py` preflight·rig_gates·judge_gates 22곳 + fit 단계 1곳) `BW_LANG` 따라 영문화.
  한국어 대조 시험은 `BW_LANG=ko` 고정, 영어 모드에서 한글이 없는지 시험 1개.
- `tests/test_i18n.py`: AST 로 모든 `T()` 호출(60여 곳) — 두 인자 문자열, 영어 쪽 한글 없음, 자리표시자 같음.
  걸린 1곳(팔·다리 중심선 문구) 정리.
- CONTRIBUTING 정정(CI 세 잡, 예시 `Ran 82 … skipped=12`). `tests/test_docs.py` 에 시험 명령 목록 5곳 ↔ `tests/test_*.py`
  대조와 CONTRIBUTING 시험 수 대조 추가.
- 백로그 남은 항목 3개(`examples/sample-output` — Mac 필요, kimodo 안내, 진행 로그) → 새 항목 추가 안 함.
- PR #6 Codex 리뷰(P2 2건) 반영: 사족 발 검출 notes(`bpy_scripts/_quad.py`)도 BW_LANG 따라 영어로. 시각 판정의 자유 문장은
  프롬프트 언어(`--lang`, 기본 ko)로 오므로 번역 대신 영어 화면에서는 '모델 출력, `--lang en` 으로 영어' 라고 밝힘. 시험 1개.

**돌린 시험**
- `LANG=C.UTF-8 python3 -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release tests.test_docs tests.test_i18n`
  — 83개 중 71개 통과, 12개 건너뜀('Blender 없음': 클라우드에 Blender·bpy 없음 — `RigMockTests`).
- GitHub Actions run 48(unit·unit-windows·blender) 통과. 이후 푸시분은 PR 에서 확인.

**Mac에서 확인할 것**
```bash
git fetch && git checkout claude/cloud-work && BW_REQUIRE_BLENDER=1 python3 -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release tests.test_docs tests.test_i18n
BW_LANG=en bw rig 사람아닌.glb   # preflight 로 막히는 메시(예: 치비·사족 아닌 블롭)에서 BLOCKED 아래 거절 사유가 영어인지
```

## 2026-10-05

**한 일**
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main(PR #4 병합분) 빨리감기 병합.
- `bw doctor`: 항목마다 `[필수]`/`[선택]` 표시. Blender 앱이나 bpy 하나만 있으면 종료코드 0 — codex(기본 `bw rig` 의 모델 판정에만 필요)·
  kimodo.cpp 는 선택. 출력도 `BW_LANG` 을 따른다. 시험 3개.
- PR 템플릿 `.github/pull_request_template.md`(시험 목록·라이선스 경계·CHANGELOG 체크, 관절 코드 수정 시 벤치 4종 전후 표).
  CONTRIBUTING 의 시험 명령을 CI 목록과 맞춤.
- 패키지 메타데이터: `[project.urls]`, `license-files`(MIT `LICENSE` + `bpy_scripts/LICENSE` GPL), hatchling ≥ 1.27.
  `python -m build` 로 sdist·wheel 둘 다 두 고지가 실리고 METADATA 에 `License-File`·`Project-URL` 이 뜨는 것 확인. 시험 2개.
- `BLOCKED:` 오류 메시지 영문화: 새 `bonewright/i18n.py`(`T`, `lang`)로 cli·pipeline 문구 약 25곳. `BW_LANG` → 로캘 → 기본 영어.
  게이트 거절 사유(`gates.py`)와 진행 로그는 아직 한국어 — README·README.ko 에 명시, 새 백로그 항목으로.
  기존 오류 시험은 `BW_LANG=ko` 로 고정, 영어 시험 2개(한글이 섞이지 않는지 포함).
- 백로그 남은 항목 2개(`examples/sample-output` — Mac 필요, Windows CI) → 새 항목 5개(근거 포함) 추가.
- PR #5 Codex 리뷰(P2) 반영: `blender.py`·`codex.py` 의 오류(Blender 없음, codex 없음·인증·사용 한도·시간 초과)도 영어로. 영어 시험 1개 추가.

**돌린 시험**
- `LANG=C.UTF-8 python3 -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release tests.test_docs`
  — 72개 중 60개 통과, 12개 건너뜀('Blender 없음': 클라우드에 Blender·bpy 없음 — `RigMockTests`).
- 새 venv 에 `pip install .` → `bw doctor`(영어, bpy 없어 종료코드 1), `bw rig none.glb` 영어·`BW_LANG=ko` 한국어 둘 다 종료코드 2.
- `python -m build` → sdist·wheel 라이선스 파일 확인. `python3 scripts/check_license_boundary.py` — OK(MIT 15개 파일).

**Mac에서 확인할 것**
```bash
git fetch && git checkout claude/cloud-work && BW_REQUIRE_BLENDER=1 python3 -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release tests.test_docs
bw doctor; echo $?; BW_LANG=en bw doctor     # codex 가 있든 없든 Blender 가 있으면 0, [필수]/[선택] 표시
BW_LANG=en bw rig 없는파일.glb; BW_LANG=en bw motion   # 영어 BLOCKED + → 안내, 종료코드 2
```

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
