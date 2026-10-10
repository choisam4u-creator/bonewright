# 클라우드 회차 할 일

위에서부터 한 회차에 1~2개씩 한다. 끝나면 [x].

- [x] README(43KB) 첫 화면을 30초 안에 이해되게 재구성(무엇을 해 주나/설치/첫 실행/결과 예시), 긴 내용은 docs/로, 한국어는 README.ko.md
- [x] 블렌더 없이 도는 시험과 블렌더가 필요한 시험을 표시로 나누기, pip install bpy 헤드리스가 되면 통합 시험 일부를 CI에
- [x] examples/: 작은 샘플 메시로 입력→리깅 결과(본 개수·이름 표) 재현 스크립트, 무거운 에셋은 다운로드 스크립트로
- [x] 공개 API 타입 힌트, 오류 메시지에 "무엇을 바꾸면 되는지" 포함
- [x] 공개 전 점검: 비밀 값·개인 경로·라이선스 없는 에셋이 저장소나 git 기록에 있는지 목록 보고(지우지 말고 보고만) → docs/PRE-PUBLIC-AUDIT.md
- [x] CHANGELOG와 다음 버전 태그 준비 → docs/RELEASING.md, 제안 0.2.1(태그는 Mac)

## 2026-10-04 추가 (공개 준비 기준: 문서·시험·라이선스·예제·오류 메시지·이슈 템플릿)

- [x] 설치본 `bw plugin-path` 가 없는 폴더를 가리킴 고치기 — 근거: pip 설치 시 `site-packages/plugin` 출력(실측), 플러그인이 휠에 안 실렸다
- [x] 이슈 템플릿 보강: 설치·`bw doctor` 문제 템플릿, 기능 요청 템플릿, `config.yml` 에 질문은 Discussions/README 로 안내 — 근거: 현재 `rig-problem.md` 1종뿐이고, 공개 뒤 가장 흔할 문의는 Blender·bpy·codex 설치 문제다
- [x] 예상 못 한 오류의 추적 경로: `cli.py` 마지막 `except Exception` 이 "BLOCKED: 메시지" 한 줄만 남겨 원인을 못 찾는다 → `BW_DEBUG=1` 이면 트레이스백, 기본은 로그 폴더(`runs/<id>/logs`)와 이슈 템플릿 안내 — 근거: `bonewright/cli.py` 의 포괄 except
- [x] 영어 사용자 안내: CLI 도움말·오류 메시지가 한국어뿐(`--lang en` 은 모델 프롬프트만 바꿈) → 최소한 README(영문)에 명시, 가능하면 `bw --help` 영문화 — 근거: README.md 는 영문인데 첫 실행 화면은 한국어
- [x] 문서 상대 링크·명령 자동 점검 시험(`tests/test_docs.py`): README·README.ko·GUIDE·examples/README 의 상대 링크와 문서에 적힌 `bw <명령> --옵션` 이 실제 argparse 에 있는지 — 근거: 10/1 Mac 이 손으로 점검했고, 9/20 문서 검증에서 틀린 주장 11건이 나왔다
- [x] `examples/` 결과 예시 커밋: `examples/out/` 이 git 제외라 처음 보는 사람이 표 모양을 모른다 → (10/6 클라우드 bpy 5.2.2 로 생성) `capsule_doll.md` 1개를 `examples/sample-output/` 에 싣고 README 에서 링크(라이선스: 절차 생성 메시라 문제 없음) — 근거: 공개 준비 '예제' 조건

## 2026-10-04(2회차) 추가 (공개 준비 기준)

- [x] `bw doctor` 가 codex 없으면 실패(종료코드 1)로 끝남 → `BW_BACKEND=mock`·`--from-skeleton`·`--from-shape` 은 codex 없이 되므로 "codex: 없음(선택: 모델 판정 경로에만 필요)"로 나누고 필수/선택을 표시 — 근거: `cli.py` `doctor()` 의 `ok &= bool(codex)`, README 는 mock 경로를 토큰 0 으로 안내
- [x] PR 템플릿 `.github/pull_request_template.md`: CONTRIBUTING 의 "측정한 숫자" 규칙, 라이선스 경계 검사, 관절 코드 수정 시 벤치 4종 전후 숫자 칸 — 근거: `.github/` 에 PR 템플릿 없음, CONTRIBUTING 이 요구하는 항목을 PR 마다 손으로 기억해야 한다
- [x] 패키지 메타데이터: `pyproject.toml` 에 `[project.urls]`(Homepage·Issues·Changelog)·`license-files`(LICENSE, bpy_scripts 의 GPL 고지) 추가, `python -m build` 로 sdist·wheel 에 LICENSE 가 실리는지 시험 — 근거: 현재 urls·license-files 없음, 공개 뒤 PyPI 페이지·배포본에 라이선스 고지가 빠질 수 있다
- [x] `BLOCKED:` 오류 메시지·`bw doctor` 출력 영문화(BW_LANG 따라) — 근거: 10/4 `bw --help` 만 영문화했고 README 에 "오류 메시지는 한국어뿐"이라 적었다. 영어 사용자가 처음 보는 실패 화면이 읽히지 않는다
- [x] Windows 에서 블렌더 없는 시험이 도는지 CI 에 `windows-latest` unit 잡 추가(실패하면 README 에 알려진 문제로 기록) → 10/5 run 48 통과 — 근거: README "Windows is untested", `blender.py` 가 macOS 경로만 찾고 Windows `Program Files\Blender Foundation` 경로가 없다

## 2026-10-05 추가 (공개 준비 기준)

- [x] 게이트 거절 사유(`gates.py` `preflight`·`rig_gates`·`judge_gates`, 문구 22곳) 영문화 — 근거: 10/5 `BLOCKED:` 첫 줄·고칠 방법은 영어가 됐지만 그 아래 `- ` 로 나열되는 거절 이유가 한국어뿐이라 영어 사용자는 왜 막혔는지 모른다(README 에 한계로 적어 둠). 시험 `tests/test_mock.py` 의 "샌 정점" 대조는 BW_LANG=ko 로 고정해야 한다
- [x] `T(한국어, 영어)` 짝 점검 시험: AST 로 `bonewright/` 의 모든 `T(...)` 호출을 찾아 두 번째 인자에 한글이 없고 `{}` 자리표시자 이름이 양쪽에 같은지 확인 — 근거: 10/5 문구 40여 곳을 손으로 옮겼고, 앞으로 한쪽만 고치면 영어 모드에 한국어가 섞이거나 경로가 빠진다(지금은 경로 몇 개만 시험)
- [x] CONTRIBUTING 정정: "Without Blender you get the pure-Python tests, which is what CI runs"(CI 는 `bpy` 잡도 돈다)와 예시 출력 "Ran 37 tests … skipped=10"(10/5 실측 72개·건너뜀 12)이 낡았다 → 고치고, `tests/test_docs.py` 에 CONTRIBUTING·PR 템플릿의 시험 명령 목록이 `.github/workflows/test.yml` 과 같은지 대조 추가 — 근거: 시험 모듈이 늘 때마다 세 곳이 따로 놀았다(10/5 에 CONTRIBUTING 을 손으로 맞춤)
- [x] kimodo.cpp 빌드 안내를 `docs/GUIDE.md` 로 옮기기 — 근거: `bw motion --text` 오류와 doctor 가 `docs/research-20260913.html` 7절을 가리키는데, 그 파일은 날짜 붙은 한국어 연구 노트이고 `PRE-PUBLIC-AUDIT.md` 가 개인 경로가 든 문서로 꼽았다. 공개 뒤 영어 사용자가 따라 할 빌드 절차가 없다
- [x] 진행 로그(`pipeline._log`, 37곳) 영문화 여부 결정 후 처리 → 10/6 T() 로 둘 다 둠(오류 문구와 같은 방식, 시험이 짝을 점검) — 근거: 오류·도움말은 영어가 됐지만 `bw rig` 진행 출력 `[1/6] import …` 뒤 설명이 한국어라 첫 실행 화면 대부분이 한국어다. 숫자·본 이름 위주로 짧게 바꿀지, T() 로 둘 다 둘지 정한다

## 2026-10-06 추가 (공개 준비 기준)

- [x] `walk_wave.bvh` 생성 모델·가중치 라이선스를 `docs/media/ATTRIBUTION.md` 에 적기 — 근거: `PRE-PUBLIC-AUDIT.md` 4절 "표기 보강 권장". 파일의 관절 30개는 SOMA 골격(SMPL-X 는 22개)이라 비상업 가중치를 안 썼음을 파일로 확인할 수 있다
- [x] Blender 스크립트 안 메시지 영문화(`bpy_scripts/` 21개 파일에 한글, 예: analyze 의 `목 추정 실패; 인체 비율 폴백`) — 근거: 10/6 `BW_LANG=en BW_BACKEND=mock bw rig` 첫 화면에서 남은 한국어는 이 `⚠ analysis is doubtful: …` 한 줄뿐이다. bpy_scripts 는 GPL 쪽이라 `bonewright.i18n` 을 못 가져오므로 `BW_LANG` 환경 변수를 직접 읽는 작은 함수를 따로 둔다
- [x] 설치본 시험: 저장소 밖 새 venv 에 `pip install .` 한 `bw` 가 `bpy_scripts`·`prompts` 를 찾아 `BW_BACKEND=mock bw rig` 를 끝까지 도는지 CI blender 잡에 한 단계 추가 — 근거: 10/4 `bw plugin-path` 가 설치본에서만 틀렸고(휠에 안 실림), 지금 blender 잡은 저장소 안에서 시험만 돈다. 클라우드에서도 `pip install bpy==5.2.2`(파이썬 3.13)가 된다(10/6 실측)
- [x] `docs/` 의 날짜 붙은 한국어 HTML 20여 개(연구·현황·벤치 노트)를 공개 문서와 나누는 안: `docs/notes/` 로 옮길 목록과 그 안의 개인 경로·내부 링크 표 → 10/6 `docs/DOCS-SPLIT-PLAN.md`(옮기지 않음) — 근거: 공개 저장소의 `docs/` 를 처음 열면 GUIDE 보다 이 파일들이 먼저 보이고, `PRE-PUBLIC-AUDIT.md` 2절의 개인 경로도 이 묶음에 있다. 옮기기 전 목록·안만(샘님 결정)
- [x] 첫 실행 30초 시험: README 의 Quickstart 명령(설치 → `bw doctor` → mock 리깅)을 그대로 뽑아 도는지 `tests/test_docs.py` 에서 명령 목록을 대조하고, 결과 표 예시(`examples/sample-output/`)와 README 숫자(본 73·410)가 같은지 — 근거: README 첫 화면은 공개 뒤 가장 많이 읽히고, 숫자가 리그 변경 때 따로 놀 수 있다
- [x] 버그 신고 재현 묶음: `bw report <run-id>`(또는 `bw doctor --for-issue`)가 버전·OS·Blender·`state.json`·마지막 로그 꼬리를 개인 경로를 `~` 로 바꿔 한 덩어리로 찍기 → 10/7 `bw doctor --for-issue [RUN_ID]` — 근거: 이슈 템플릿 3종이 이 값들을 손으로 모으라고 하고, 10/4 포괄 except 가 로그 폴더만 안내한다

## 2026-10-06(2회차) 추가 (공개 준비 기준)

- [x] `bw bench`·`bw report`(보고서 md)·mock·codex 진행 문구의 T() 밖 한국어 36곳 영문화(bench 17·pipeline 12·codex 2·gates 2·mock 2·manifest 1) → 10/7 처리, gates 2곳은 한글 범위 비교라 예외 — 근거: 10/6 AST 집계. 화면 진행 로그와 Blender 스크립트는 영어가 됐지만 `bw bench` 표와 `runs/<id>/report.md` 본문이 아직 한국어라 영어 사용자가 결과 보고서를 못 읽는다. 끝나면 `test_i18n` 의 "T() 밖 한글 금지"를 `bonewright/` 전체로 넓힌다
- [x] 문서 점검 범위 넓히기(10/7, GUIDE 절 제목·config.yml 링크 대조 포함): `tests/test_docs.py` 의 상대 링크·`bw` 명령 점검에 CONTRIBUTING·SECURITY·`.github/ISSUE_TEMPLATE/*`·PR 템플릿·`docs/RELEASING.md` 추가 — 근거: 지금은 README·README.ko·GUIDE·examples/README 4개만 본다. 이슈 템플릿은 `docs/GUIDE.md` 절 제목("Which flag do I want?")과 `--from-skeleton` 등 옵션을 적어 두었고, 공개 뒤 신고자가 처음 따라 하는 문서다
- [x] `ROADMAP.md`(한국어 55KB) 영문 요약(10/7 GUIDE "Known gaps and failed attempts" 7줄, 앵커 시험): CONTRIBUTING(영문)이 "실패한 시도는 ROADMAP 에, 남은 구멍은 ROADMAP 끝에"라고 두 번 가리키는데 영어 사용자가 읽을 수 없다 → GUIDE 에 "Known gaps and failed attempts" 절(숫자 포함 10줄 안팎)을 두고 CONTRIBUTING 이 그 절을 가리키게 — 근거: 10/6 `docs/DOCS-SPLIT-PLAN.md` 의 "그대로 둘 것" 표
- [x] (10/7: `capsule_dog.md`, 변형 본 110, 관문 ok) 사족 예시 결과: `examples/sample-output/` 에 사람(캡슐 인형)만 있다 → `make_test_mesh` 로 절차 생성한 네 발 메시가 되는지 보고, 되면 `rig_sample.py --preset quadruped` 결과 표를 싣고 README 의 "Rigs humans and four-legged animals" 옆에서 링크 — 근거: README 첫 줄이 사족을 내세우지만 처음 보는 사람이 확인할 예시는 사람 것뿐이다(라이선스: 절차 생성이면 문제 없음)
- [x] (10/7: `docs/CODE-OF-CONDUCT-PLAN.md` + `docs/drafts/CODE_OF_CONDUCT.md` 원문, 결정 대기) `CODE_OF_CONDUCT.md` 여부 결정용 메모 — 근거: 저장소 루트에 CONTRIBUTING·SECURITY·LICENSE 는 있고 행동 강령은 없다. GitHub 커뮤니티 프로필 점검 항목이며, 넣을지(Contributor Covenant 2.1 원문)·연락처를 무엇으로 할지는 샘님 결정이라 안과 문안만 준비(연락처 칸 비움)


## 2026-10-07 추가 (공개 준비 기준)

- [x] `rig.cross_trim` 기본값 문서 정정(10/7: CHANGELOG 0.2.0 절·ROADMAP 정정, `test_docs.DefaultClaimTests`): `config.py` 는 `True`(복셀 측지 판정, 9/19 4408cda)인데 CHANGELOG 0.2.0 절·ROADMAP 은 "기본 끔"(광선 판정, 35758da)이라 적었다 → ROADMAP 끝에 정정 한 줄, CHANGELOG `[Unreleased]` 에 "0.2.0 표기 정정", 가능하면 문서의 `**off by default**`·`on by default` 주장을 `config.DEFAULTS` 와 대조하는 시험 — 근거: 10/7 GUIDE 영문 요약을 쓰다가 발견(GUIDE 에는 실제 값으로 적음)
- [x] (10/7: `pipeline._shown`, rig·motion 보고서) `runs/<id>/report.md` 의 절대 경로를 실행 폴더 기준 상대 경로로(`- rig:`·`- targets:` 줄 등) — 근거: 이슈 템플릿 'A rig came out wrong' 이 report.md 를 그대로 붙이라고 하는데 그 안에 홈 폴더 경로(사용자 이름)가 든다. `bw doctor --for-issue` 는 `~` 로 바꾸지만 report.md 는 손으로 붙인다
- [x] (10/8: 생략 시 runs/config.json → BW_LANG·로캘, `test_i18n.PromptLangTests`) 모델 프롬프트 언어 기본값: `config.py` 의 `"lang": "ko"` 라 영어 사용자도 판정 문장(judge notes·reasoning)을 한국어로 받는다(`gates._model_text` 가 "--lang en 으로 다시 돌려라" 안내만 붙임) → `--lang` 생략 시 BW_LANG(로캘) 을 따르게 할지 결정 후 처리(프롬프트 en 판 존재 확인 포함) — 근거: 10/5~10/7 화면 문구는 전부 영어 기본이 됐는데 모델 출력만 남았다
- [x] (10/8: `scripts/check_issue_report.py`, unit·unit-windows·blender 잡, 결과는 다음 CI 에서) CI 에 `bw doctor --for-issue` 한 단계(설치본·저장소 밖, unit·unit-windows·blender 잡): 종료코드와 출력에 `/home/runner` 가 안 남는지(`~` 치환) — 근거: 10/7 새 명령은 모의 시험(경로 치환·로그 꼬리)만 있고, Windows 홈 경로 치환(`C:\Users\…`)은 실제로 돌려 보지 않았다
- [x] (10/8: 0.3.0 제안, RELEASING '다음 버전 점검' 표, `test_release.ProposedVersionTests`) `docs/RELEASING.md` 0.2.1 절차 점검: 10/7 까지 `[Unreleased]` 에 새 플래그(`--for-issue`)·영문화·문서 시험이 쌓였다 → 버전 제안(0.2.1 vs 0.3.0, 새 플래그가 있으므로)과 CHANGELOG 문구 정리안만(태그·릴리스는 Mac/샘님) — 근거: CHANGELOG 첫 줄이 "fixes, documentation and examples only" 라 적었는데 10/7 에 새 플래그가 들어갔다


## 2026-10-08 추가 (공개 준비 기준)

- [x] (10/8: `config._read_user_config`, `test_errors.test_broken_settings_file`) 깨진 `runs/config.json`(끝 쉼표·목록) → 줄·칸을 짚는 `BLOCKED:` — 근거: 10/8 실측, `{"lang": "en",}` 한 글자에 "예상 못 한 오류 — 이슈를 열어라"가 떴다. 사용자가 고칠 수 있는 입력 실수인데 이슈 신고로 안내했다
- [x] (10/8 2회차: GUIDE 표·예시, `test_docs.SettingsTableTests`) `docs/GUIDE.md` 에 "Settings (`runs/config.json`)" 절: 사용자가 바꿀 만한 키(`lang`·`rig.*`·`blender.app`·`budget`·`kimodo.root`)와 기본값 표, 우선순위(`--lang` > config > `BW_LANG`), `test_docs` 로 표 값과 `config.DEFAULTS` 대조 — 근거: config.json 은 GUIDE 에서 kimodo 한 곳(497줄)만 나오고, 10/8 프롬프트 언어 우선순위에 config 가 끼었는데 적힌 곳이 CHANGELOG 뿐이다
- [x] (10/8 2회차: `config.unknown_keys`·`unknown_keys_line`, `test_errors.test_unknown_settings_key_warns`) `runs/config.json` 의 모르는 키(오타) 경고: `config._merge` 가 `{"rig": {"cross_trimm": false}}` 를 조용히 받아 기본값으로 돈다 → `bw doctor` 와 `bw rig` 시작 줄에 "모르는 설정 키" 한 줄(멈추지는 않음) — 근거: 10/8 코드 읽기. 설정이 안 먹은 줄 모르고 결과가 이상하다는 이슈가 될 수 있다
- [x] (10/8 2회차: run 37717221862 네 잡 모두 초록. Windows 출력에 `BW_HOME=~\bw-home`·`work folder (ROOT): ~\bw-home` — 치환이 실제로 돈다. 고칠 것 없음) 10/8 CI 새 단계 결과 확인: `check_issue_report.py` 가 unit·unit-windows·blender 잡에서 초록인지(특히 Windows 의 `C:\Users\runneradmin` 치환, git-bash 경로), 빨가면 고친다 — 근거: Windows 홈 경로 치환은 아직 한 번도 실제로 돈 적이 없다(문자열 시험만)
- [x] (10/9: `rig_sample.py --motion`·`wave_bvh`, `sample-output/capsule_doll_motion.md` 19관절 중 18개·24프레임, 두 README 링크, `test_examples` 매핑 대조·블렌더 대조) 리타겟 예시 결과: `examples/sample-output/` 에 리깅 표만 있다 → 절차 생성 짧은 BVH(시험의 3프레임 BVH 처럼, 라이선스 문제 없음)로 캡슐 인형에 `bw motion --bvh` 를 돌린 결과(매핑된 본 수·프레임 수·report.md 발췌)를 싣고 README "Motion retargeting" 옆에서 링크, 블렌더 시험으로 현재와 대조 — 근거: README 가 리타겟을 두 번째 기능으로 내세우는데 처음 보는 사람이 확인할 예시가 없다
- [x] (10/8 2회차: `.github/ISSUE_TEMPLATE/docs-problem.md`, `test_docs.IssueTemplateTests`) 문서 오류 신고 길: 이슈 템플릿 3종(rig·install·feature)에 "문서가 틀렸다" 칸이 없다 → `docs-problem.md` 템플릿(어느 파일·어느 줄·실제로 본 것) 또는 `config.yml` 에 안내 한 줄, `test_docs` 의 템플릿 점검에 포함 — 근거: 9/20·10/7 문서 감사에서 실제와 다른 주장이 11개·1개 나왔다. 공개 뒤 가장 흔한 첫 기여가 문서 지적이다


## 2026-10-08 2회차 추가 (공개 준비 기준)

- [x] (10/9: Blender 없음·파일 없음·GLB 아님·`--table`·`--motion` 문구 `T()`, `test_examples.ExampleMessageTests`) 예제 스크립트 오류 문구 영어: `examples/rig_sample.py` 는 Blender 가 없을 때 `BW_LANG=en` 에서도 한국어 한 줄("Blender 가 없다 — …")로 끝난다 → `T()` 로 두 언어, `test_examples` 에 "Blender 없음" 문구가 화면 언어를 따르는지 시험 — 근거: 10/8 2회차에 bpy 없는 3.11 로 돌려 봄(종료 1, 한국어). 공개 뒤 첫 사용자가 가장 먼저 돌리는 파일이다
- [x] (10/9: `cli.config_section` — 깨진 JSON 도 그대로, 4000자 상한, 모르는 키 한 줄. CI unit 잡이 홈 경로 든 설정을 두고 `check_issue_report.py --expect-config`) `bw doctor --for-issue` 에 `runs/config.json` 싣기: 지금 덩어리엔 `BW_*` 환경 변수만 있고 설정 파일은 없다 → 있으면 내용(홈 경로 `~` 치환)과 모르는 키 경고 한 줄을 넣고 `check_issue_report.py` 로 확인 — 근거: 10/8 2회차에 설정 절·오타 경고를 넣었는데, 설정이 원인인 리깅 이슈는 설정 없이 재현이 안 된다
- [x] (10/9: DEFAULTS 에서 삭제. 같은 점검으로 `default_model` 도 안 읽혀 삭제, `test_errors.test_every_default_setting_is_read`, CHANGELOG Changed) `blender.prefer_module` 설정이 어디서도 읽히지 않는다(`grep` 결과 `config.py` 한 곳) → bpy 모듈·앱 중 무엇을 먼저 쓸지 실제로 반영하거나 DEFAULTS 에서 빼고 CHANGELOG 한 줄 — 근거: 10/8 2회차 Settings 표를 쓰다 발견. 표에 넣으면 문서가 거짓말을 한다(그래서 뺐다)
- [x] (10/9 2회차: checkout@v5·setup-python@v6, `test_release.WorkflowActionTests`, 네 잡 결과는 푸시 뒤 CI) CI 액션 버전: 10/8 run 37717221862 Windows 로그에 "Node.js 20 is deprecated … actions/checkout@v4, actions/setup-python@v5 … forced to run on Node.js 24" 경고 → 두 액션을 Node 24 판 메이저로 올리고 네 잡 초록 확인 — 근거: 강제 전환이 끝나면 공개 직후 CI 가 경고 없이 깨질 수 있다
- [x] (10/9 2회차: 두 README "Settings/설정" 문단·예시 JSON·GUIDE 앵커 링크, `test_docs.FirstRunTests.test_settings_line_matches_between_languages`) README·README.ko 첫 화면에 설정 파일 한 줄: 프롬프트 언어·쉬는 자세를 `runs/config.json` 으로 고정할 수 있다는 것과 GUIDE "Settings" 링크, 두 README 짝 시험(`FirstRunTests` 처럼) — 근거: README 에 `config.json` 이 한 번도 안 나온다. 영어 사용자가 매번 `--lang en` 을 붙여야 하는 줄 안다


## 2026-10-09 추가 (공개 준비 기준)

- [x] (10/9 2회차: 표 수·블렌더 칸·"15개 건너뜀"·CI 세 잡, test_examples 를 블렌더 묶음/나머지로 나눔, `test_docs.TestListTests.test_tests_readme_table_is_current`) `tests/README.md` 표의 시험 수가 낡았다(예: `test_examples` 3 → 지금 12, `test_cli` 15 → 18, 블렌더 건너뜀 "13개" → 15) → 표를 고치고, CONTRIBUTING 예시처럼 묶음별 수를 실제 `unittest` 로더 수와 대조하는 `test_docs` 시험 — 근거: 10/9 회차에 시험 9개를 더하며 CONTRIBUTING 은 시험이 잡아 줬지만 tests/README 는 아무도 안 잡았다. 기여자가 처음 여는 시험 안내서다
- [x] (10/9 2회차: `doctor(warn_unknown=False)` 로 설정 절에만, 진짜 doctor 로 도는 `test_cli.IssueReportTests.test_unknown_key_warned_once`, `check_issue_report.py --expect-config` 그대로) `bw doctor --for-issue` 에 모르는 설정 키 경고가 두 번 나온다(`bw doctor` 출력의 ⚠ 줄 + 10/9 설정 절의 "unknown keys" 줄) → 한 번만(설정 절 쪽을 남기고 doctor 출력에서 빼거나 반대), `check_issue_report.py --expect-config` 유지 — 근거: 10/9 설치본으로 돌려 본 출력에서 확인. 붙여 넣는 덩어리가 길어지고 읽는 사람이 서로 다른 문제로 볼 수 있다
- [x] `examples/rig_sample.py --help` 와 머리 docstring 이 한국어뿐이다 → argparse 설명·도움말을 `T()` 로 두 언어(문구 언어 시험은 `ExampleMessageTests` 에 추가) — 근거: 10/9 오류 문구는 두 언어가 됐지만 `--help`(사용자가 오류 다음에 치는 것)는 아직 한국어
- [x] 영어 README 가 링크하는 예시 문서가 한국어다: `examples/README.md`, `sample-output/*.md`(머리글 "리깅 결과"·"옮긴 본"·"report.md 발췌") → 예시 문서 머리글을 영어(또는 두 언어)로 바꾸고 `rig_sample.py` 가 쓰는 문구와 `test_examples` 의 대조(`table_part`·`motion_rows`)를 함께 고친다 — 근거: 10/9 README.md 에 리타겟 예시 링크를 넣으며 확인. 영어 사용자가 첫 클릭에서 한국어 페이지를 만난다
- [x] GUIDE "Motion retargeting" 절에 BVH 관절 이름 기대치와 새 예시 링크: 10/9 예시에서 `Spine` 은 옮기지 않았다(척추 중간은 `chest` 하나가 받는 `FK_TARGET` 규칙) → 어떤 이름(Mixamo·kimodo 식)이 무엇에 붙는지 짧은 표와 `examples/sample-output/capsule_doll_motion.md` 링크, `test_docs` 의 상대 링크 점검 포함 — 근거: "못 옮긴 BVH 본 1개" 를 처음 보는 사람은 실패로 읽는다. 이유가 문서 어디에도 없다


## 2026-10-09 3회차 추가 (공개 준비 기준)

- [x] (10/9 3회차: `tests/__init__.py`, `test_docs.TestListTests.test_bare_unittest_discovers_every_test` — 파일을 빼면 실패 확인) 시험: 인자 없는 `python3 -m unittest` 가 시험 0개를 돌리고 종료 5("NO TESTS RAN")로 끝난다(`tests/` 가 패키지가 아니라 발견이 안 된다) → `tests/__init__.py` 등으로 인자 없는 명령도 7개 묶음 전부를 돌게 하고, CONTRIBUTING·tests/README 의 긴 명령 옆에 짧은 형태를 적고, `test_docs` 로 발견 수와 로더 수 대조 — 근거: 10/9 3회차 실측. 기여자가 가장 먼저 치는 명령이 "시험 없음"으로 끝난다
- [x] (10/9 3회차: 거절을 `rig_and_table` 앞으로, `--motion --table` 도 막음, `ExampleMessageTests.test_motion_on_quadruped_stops_before_rigging` — 옛 코드에서 실패 확인) 예제 오류 순서: `rig_sample.py --motion --preset quadruped` 는 사족 리깅(블렌더 수십 초)을 다 끝낸 뒤에야 "--motion 은 사람 프리셋에서만" 으로 멈춘다 → 리깅 전에 인자 조합을 막고(argparse `p.error` 처럼), Blender 없이 도는 시험 — 근거: 10/9 3회차 코드 읽기(`main()` 에서 거절이 `rig_and_table` 뒤에 있다). 기다린 뒤 거절은 첫 사용자에게 가장 나쁜 경험이다
- [x] (10/9 3회차: tests/assets/README 영어 먼저·한국어 뒤, ATTRIBUTION·자산별 라이선스 문구 영어, `test_docs.AssetLicenceTests`) 라이선스 표기 영어: `tests/assets/README.md`(CC0 Adventurer 의 출처·라이선스)와 `fetch_bench_assets.py` 가 쓰는 `bench-assets/README.md` 의 라이선스 줄이 한국어뿐이다 → 영어(두 언어)로, 라이선스·출처 URL 이 빠지지 않았는지 시험 — 근거: 10/9 3회차 실측(한글 32단어). 공개 저장소에서 자산 라이선스는 영어 사용자가 가장 먼저 확인하는 것이다
- [x] (10/9 3회차: 설명·옵션·진행·실패·합계 문구 `T()`, `test_i18n.FetchScriptLanguageTests` — 내려받기 가짜, 옛 코드에서 실패 확인) `scripts/fetch_bench_assets.py --help`·진행 문구가 한국어뿐이다("벤치마크 자산을 원저작자 배포처에서 받는다") → `T()` 로 두 언어, 영어 화면에 한글이 없는지 시험 — 근거: 10/9 3회차 실측. 두 README·examples/README 가 이 명령을 안내한다
- [x] (10/9 3회차: `pipeline.versions_line`, Blender 쪽 `_common.done` 이 `blender` 버전을 결과에, rig·motion report.md 둘째 줄, rig-problem 템플릿에 `bw --version`, `test_errors` 1개·`RigMockTests` 단언 2개) 이슈 재현 정보: `rig-problem` 템플릿은 `report.md` 를 붙이라는데 `report.md` 에 bonewright·Blender 버전이 없다(`bw doctor --for-issue` 는 BLOCKED 일 때만 안내) → `report.md` 머리에 버전 한 줄(`bw --version` 과 같은 값)과 템플릿에 `bw --version` 칸, 시험 — 근거: 10/9 3회차 템플릿·`pipeline.py` 읽기. 리그 결과는 버전마다 달라 버전 없는 신고는 재현이 안 된다


## 2026-10-09 3회차 둘째 묶음 (공개 준비 기준)

- [x] (10/9 3회차: `USER_SCRIPTS`, T() 44곳이 짝 점검에 들어감, `test_user_scripts_have_no_bare_hangul`, 자리표시자 하나를 지우면 실패 확인) 시험: `test_i18n` 의 `T(한국어, 영어)` 짝 점검(영어 쪽 한글·자리표시자 대조, AST)이 `bonewright/` 만 본다 → 이번 회차에 `T()` 를 넣은 `examples/rig_sample.py`·`scripts/fetch_bench_assets.py` 도 같은 점검에 넣는다 — 근거: 10/9 3회차에 두 파일에 `T()` 30여 개를 넣었는데 자리표시자 대조는 하나도 안 걸린다(`PKG.rglob` 만)
- [x] (10/9 3회차: `problems(root)`·`main()`, 위반·파일 없음 줄에 →, `test_errors.LicenseBoundaryTests`, T() 짝 점검 대상. CI 단계 이름의 한국어는 그대로 — 아래 새 항목) 오류 메시지: CONTRIBUTING 이 PR 전에 돌리라는 `scripts/check_license_boundary.py` 의 출력("라이선스 경계 OK — MIT 영역 …", 위반 줄)이 한국어뿐이다 → `T()` 두 언어, 위반 줄에 고칠 방법(→ bpy 를 쓰는 코드는 `bpy_scripts/` 로) — 근거: 10/9 3회차 실측. 영어 기여자가 처음 보는 CI 실패 문구다
- [x] (10/9 3회차: 꼬리표 5개를 영어 글자 + `ROADMAP.md#한국어-앵커` 링크로, 주석 영어, `test_docs` 앵커·한글 시험 2개) 문서: `docs/GUIDE.md`(영어)에 한글 6곳 — "Known gaps" 의 ROADMAP 절 꼬리표 `[막힌 곳: …]`·`[실패: …]` 5개와 276줄 명령 주석 → 꼬리표는 영어 설명 + 한국어 절 이름(검색용)으로, 주석은 영어로, GUIDE 에 꼬리표 밖 한글이 없는지 시험 — 근거: 10/9 3회차 실측(한글 25단어)
- [x] (10/9 3회차: 인용 블록 영어 요약, `test_release.ReleasingSummaryTests`) 문서: 영어 CHANGELOG 가 "See `docs/RELEASING.md`" 로 가리키는 릴리스 절차가 한국어뿐이다(한글 277단어) → 맨 위에 영어 요약(단계 목록·누가 하는지) — 근거: 10/9 3회차 실측. 공개 뒤 기여자가 "언제 릴리스되나" 를 찾는 문서다
- [x] (10/9 3회차: `__version__`·`REPO_URL`, `test_release.VersionTests.test_fetch_script_user_agent_follows_version` — pyproject Homepage 와 대조) 릴리스: `fetch_bench_assets.py` 의 User-Agent 가 `bonewright-bench-fetch/0.2 (+https://github.com/)` 로 버전·주소가 손으로 박혀 있다 → `bonewright.__version__` 과 저장소 주소로, `test_release` 의 버전 일치 점검에 포함 — 근거: 10/9 3회차 코드 읽기. 0.3.0 에서 버전이 어긋나고, 원배포처가 문의할 주소가 없다


## 2026-10-09 3회차 셋째 묶음 (공개 준비 기준)

- [x] (10/9 3회차: 판정·단계를 영어 코드 + `label()`, 옵션 도움말, `test_i18n.BenchScoreLanguageTests` — 리깅 가짜) `scripts/bench_score.py`(README·GUIDE 가 벤치 숫자의 출처로 안내)의 출력이 한국어다(한글 317단어, `--help` 는 설명 없음) → 진행·표·오류 문구 `T()`, 옵션 도움말, `test_i18n.USER_SCRIPTS` 에 추가 — 근거: 10/9 3회차 실측. 영어 사용자가 README 숫자를 재현하려고 처음 돌리는 스크립트다
- [x] (10/9 3회차: `test_docs.ExamplesReadmePairTests` — 첫 실행에서 한국어판에 GUIDE 링크가 빠진 것을 잡아 고침) `examples/README.md`(영어)와 `README.ko.md` 가 갈라질 수 있다 → 두 파일의 코드 블록 명령과 링크 목록이 같은지 보는 짝 시험(`FirstRunTests` 처럼) — 근거: 10/9 3회차에 한 파일을 둘로 나눴다. 명령을 한쪽만 고치면 아무 시험도 안 걸린다
- [x] (10/9 3회차: 단계 이름 13개·주석·스크립트 문구 영어, 명령은 그대로, `test_release.WorkflowActionTests.test_workflow_is_english`) CI(`.github/workflows/test.yml`) 단계 이름·주석이 한국어다(단계 이름 13개) → 단계 이름을 영어로(주석은 두 언어 또는 영어), 공개 뒤 PR 기여자가 보는 Actions 화면 — 근거: 10/9 3회차 `check_license_boundary` 고칠 때 확인. 실패한 단계 이름을 영어 기여자가 못 읽는다
- [x] (10/9 3회차: 실패 문구는 이미 영어였고 도움말만 한국어 → 도움말 T(), FAIL 아래 → 줄, `test_i18n.IssueReportCheckTests`) `scripts/check_issue_report.py`(CI 가 `bw doctor --for-issue` 출력에서 개인 경로를 찾는 점검)의 실패 문구가 한국어다(한글 71단어) → `T()` 와 고칠 방법(→), `USER_SCRIPTS` 에 추가 — 근거: 10/9 3회차 실측. CI 실패 시 영어 기여자가 처음 보는 문구다
- [x] (10/9 3회차: 인용 블록 영어 요약·표 머리글 두 언어, `test_tests_readme_table_is_current` 가 요약의 건너뜀 수와 한글 없음까지) `tests/README.md`(CONTRIBUTING 다음으로 기여자가 여는 시험 안내)가 한국어뿐이다(한글 340단어) → 맨 위 영어 요약(세 명령·블렌더 시험 표시법·CI 세 잡)과 표 머리글 영어, `test_docs` 표 대조는 유지 — 근거: 10/9 3회차 실측


## 2026-10-09 3회차 넷째 묶음 (공개 준비 기준)

- [ ] (10/9 3회차: 샘님 결정 필요로 건너뜀 — CLOUD-NOTES) 라이선스: `spikes/` 의 `bvh_check.py`·`render_rig2.py`·`rigify_headless.py` 가 `import bpy` 인데 `LICENSE` 는 "bonewright/bpy_scripts/ 말고 전부 MIT" 라 적었다 → (샘님 확인) `LICENSE`·`bonewright/bpy_scripts/README.md` 표에 `spikes/` 를 GPL 로 적거나 스파이크를 정리, `check_license_boundary.py` 가 `bonewright/` 밖(`examples/`·`scripts/`·`spikes/`)의 bpy import 도 보게 — 근거: 10/9 3회차 `grep -l "import bpy" spikes/*.py` 3개. 지금 검사는 `bonewright/` 만 본다
- [x] (10/9 3회차: 시점 없는 계획으로, `bpy_scripts/README` 의 "planned" 와 일치, `test_docs.StaleVersionClaimTests` — 옛 문서에서 실패 확인) 문서: `addon/README.md` 가 "v0.1 runs headless … add-on is planned for v0.2" 라 적었는데 0.2.0 이 나왔고 add-on 은 없다 → 지금 상태(계획만, 시점 미정)로 고치고 `bpy_scripts/README.md` 표의 "planned" 와 맞춤, 버전 언급이 현재 버전보다 과거면 걸리는 시험 — 근거: 10/9 3회차 실측
- [x] (10/10 4회차: 65개에 영어 첫 줄 + 빈 줄 + 한국어 설명, `test_docs.TestListTests.test_verbose_test_names_are_english` — 고치기 전 65개로 실패 확인, CONTRIBUTING 에 규칙 두 줄, 시험 수 157) 시험 출력: CI 는 `-v` 로 돌아 시험 이름 옆에 docstring 첫 줄을 찍는데 155개 중 65개가 한국어다 → 영어 기여자가 CI 로그에서 어떤 시험이 깨졌는지 읽게(첫 줄 영어 + 둘째 줄부터 한국어 설명, 또는 `-v` 대신 이름만) — 근거: 10/9 3회차 `shortDescription()` 집계
- [x] (10/10 4회차: `spikes/README.md` 영어 — 파일별 확인한 것·지금 쓰는지 표, `walk_wave.bvh` 는 시험·GIF 가 써서 지우면 안 됨, `.gitignore` 에 걸린 폴더라는 것, 라이선스는 미정이라고만 적음, `test_docs.DOCS` 링크 점검 대상) `spikes/` 에 설명이 없다(README 없음, 패키지에도 안 실림) → 무엇을 확인하려던 실험인지·지금 쓰는지·지워도 되는지 한 장(영어), 링크 점검 대상에 포함 — 근거: 10/9 3회차. 공개 뒤 처음 보는 사람은 `spikes/` 를 본체로 오해할 수 있다
- [x] (10/10 4회차: "다시 훑음" 절 — 비밀 없음·개인 경로 같은 2곳·새 파일 21개 깨끗·에셋 8개 표기 있음, **웹 병합 커밋의 개인 메일 2 → 9개**(샘님 판단), 별칭이 내부 기록 6개에) `docs/PRE-PUBLIC-AUDIT.md` 의 기준이 `main 27fd528` 이다 → 10/9 까지 새로 든 파일(examples 두 언어 README·sample-output·tests/assets/README·bench-assets ATTRIBUTION 문구)을 같은 방식(개인 경로·메일·자산 출처)으로 다시 훑고 기준 커밋을 갱신, 결과만 적는다(기록 정리 결정은 샘님) — 근거: 10/9 3회차 실측


## 2026-10-10 4회차 (공개 준비 기준, 사용자 체감 우선)

- [x] (10/10 4회차: `blender.BlenderMissing` → cli 가 `BLOCKED:` 로, 다운로드 주소·`bw doctor`, 실패한 단계를 state.json 에 `failed`, BW_BLENDER 가 없는 파일이면 그 경로를 짚음, codex 없음에 토큰 0 경로 셋, `test_errors.MissingToolTests` 3개 — 옛 코드에서 3개 실패 확인, CHANGELOG, 시험 수 160) 오류 메시지: Blender 없이 `bw rig` 를 치면 '예상 못 한 오류' 로 빠져 빈 로그 폴더·`BW_DEBUG=1`·이슈 템플릿을 안내하고, `bw status` 는 그 실행을 계속 `running` 이라 한다 → 설치로 고치는 오류는 `BLOCKED:` + 설치 주소 + `bw doctor`, 실행은 `failed` — 근거: 10/10 4회차에 설치 직후 상태(Blender·codex 없음)로 `bw rig`·`motion`·`status` 를 직접 돌림. 새 사용자가 가장 먼저 만나는 오류다
- [x] (10/10 4회차: `cli.main` 이 BrokenPipeError 를 받으면 stdout 을 devnull 로 돌리고 1 로 끝냄, `test_cli.ClosedPipeTests` — 읽기 전에 닫는 실제 파이프, 옛 코드에서 실패 확인, Windows 는 EINVAL 이라 건너뜀, 시험 수 162 → CI unit(3.11)에서 끝날 때 flush 의 BrokenPipe 가 드러나 main() 에서 flush 까지 받게 고침, 경쟁 없는 같은 프로세스 시험 추가, 163) 오류 메시지: `bw doctor | head -1`·`bw status | head` 처럼 출력을 잘라 읽으면 `BLOCKED: BrokenPipeError` 와 이슈 신고 안내가 나온다(종료 코드 2) → 파이프가 닫히면 조용히 끝낸다(파이썬 문서의 SIGPIPE 처리 방식), 시험 — 근거: 10/10 4회차 실측. 문서·이슈 템플릿이 `bw doctor` 출력을 붙이라 해서 사람들이 `| head`·`| pbcopy` 로 자주 돌린다
- [x] (10/10 4회차: 두 README 첫 실행 맨 위 `bw rig tests/assets/quaternius_adventurer.glb --from-skeleton --no-judge` — codex 없는 bpy 5.2.2 에서 실제로 돌려 관문 pass·report 확인. 고치다 드러난 것: `--from-skeleton` 은 맞춤 호출만 건너뛰고 시각 판정은 모델을 부르는데 README 는 '토큰 0' 이라 적었다 → README 두 언어와 codex 없음 문구에 `--no-judge` 를 함께, GUIDE·`--help` 의 같은 주장은 샘님 결정(CLOUD-NOTES). `FirstRunTests.test_first_command_needs_no_model` — 옛 README 에서 실패 확인, 시험 수 161) 첫 실행 단계 수: README "First run" 의 첫 명령 `bw rig character.glb` 는 codex 설치·로그인·약 $1 이 있어야 결과가 나온다(설치 → 첫 결과 최소 5단계: pip·Blender·npm codex·codex login·bw rig). 저장소에 이미 있는 `tests/assets/quaternius_adventurer.glb` 로 `--from-skeleton`(토큰 0)이면 3단계 → 두 README 첫 실행 맨 위에 "먼저 이것으로 확인" 한 줄, 그 명령이 실제 argparse·파일과 맞는지 `FirstRunTests` 에 — 근거: 10/10 4회차 실측(codex 없는 상태에서 README 대로 따라 함)
- [x] (10/10 5회차: `cli._main` 이 인자 없으면 도움말을 stderr 로 + "처음이면 `bw doctor` → README 첫 실행 첫 명령(모델 호출 없음)" 한 줄, 종료 2, `test_cli.BareCommandTests` 두 언어 — 옛 코드에서 실패 확인, CHANGELOG, 시험 수 166) 첫 화면: 인자 없이 `bw` 만 치면 argparse 의 `error: the following arguments are required: cmd` 한 줄로 끝난다 → 명령 목록(도움말)과 "처음이면 `bw doctor`" 한 줄을 보여 주고 종료 코드 2 유지, 두 언어 시험 — 근거: 10/10 4회차 실측. 설치 직후 사람들이 가장 먼저 치는 것이다
- [x] (10/10 5회차: 실제로 도는 단계 목록으로 번호를 셈 — BVH 만 `[1/1]`, `--rig --export` 면 `[1/3]`…`[3/3]`, `test_errors.MotionStepNumberTests` 2개 — Blender 가짜, 옛 코드에서 `[3/3]`·`[5/5]` 로 실패 확인, CHANGELOG, 시험 수 165) 진행 로그: `bw motion --bvh` 는 `[3/3]` 부터 시작한다(`[1/3]`·`[2/3]` 은 `--text` 일 때만) → BVH 를 줬을 때는 단계 번호 없이 또는 `[1/2]·[2/2]` 로, 시험 — 근거: 10/10 4회차 실측. 첫 줄이 3/3 이면 앞 단계가 빠졌다고 오해한다


## 2026-10-10 5회차 (공개 준비 기준, 사용자 체감 우선 — 빈 BW_HOME·Blender 없음 상태로 `bw` 명령을 직접 돌려 찾음)

- [x] (10/10 5회차: stderr 에 찾은 폴더·`bw rig <메시>`·BW_HOME 한 줄, stdout 은 빈 채로(목록을 읽는 스크립트용), 종료 0 유지, `test_cli.EmptyStatusTests` 두 언어 — 옛 코드에서 실패 확인, CHANGELOG, 시험 수 167) 첫 화면: 실행이 하나도 없을 때 `bw status` 는 아무것도 찍지 않고 종료 0 이다 → "아직 실행이 없다(찾은 곳: `<BW_HOME>/runs`) → `bw rig …`" 한 줄, BW_HOME 을 잘못 잡았는지도 알 수 있게, 두 언어 시험 — 근거: 10/10 5회차 실측. 빈 출력은 설치가 깨졌는지 BW_HOME 이 다른지 구분이 안 된다
- [x] (10/10 5회차: `bench.run` 이 실행 폴더·Blender 전에 빈 목록·없는 파일·형식(`need_file`)을 `BLOCKED:`, `BlenderMissing` 은 자산마다 삼키지 않고 설치 안내 한 번, 하나도 못 쟀으면 report.md 를 남기고 `BLOCKED:`(종료 2), 안내마다 `fetch_bench_assets.py`, `test_errors.BenchInputTests` 3개 — 옛 코드에서 실패 확인, CHANGELOG, 시험 수 171) 오류 메시지: `bw bench 빈폴더` 는 종료 0 에 "measured 0/0 · mean Nonecm", `bw bench 없는파일.glb` 는 파일 없음 대신 "nope: Blender not found"(설치 주소 없음)에 종료 0 → 메시를 하나도 못 찾으면·파일이 없으면 Blender 전에 `BLOCKED:`(→ 고칠 방법), Blender 없음은 한 번만 설치 안내로, 하나도 못 쟀으면 종료 0 이 아니게 — 근거: 10/10 5회차 실측. README·GUIDE 가 벤치 숫자를 재현하라고 안내하는 명령이다
- [x] (10/10 5회차: `pipeline.motion` 이 실행 폴더·Blender 전에 `BLOCKED:` — 빠진 옵션 이름을 모두 짚고 `--rig <run-id>`·`bw status` 안내, `--preset`·`--bvh-up` 은 위 축 판단에 쓰여 그대로 허용, `test_errors.MotionRigOnlyFlagTests` 4가지 — 옛 코드에서 4개 실패 확인, CHANGELOG, 시험 수 168) 입력 확인: `bw motion --bvh x.bvh --export`(또는 `--map`·`--legs ik`·`--no-roll`)를 `--rig` 없이 주면 아무 말 없이 무시된다(내보내기는 `rig_run` 일 때만) → Blender 전에 "`--export` 는 `--rig <run-id>` 와 함께" 로 거절, 시험 — 근거: 10/10 5회차 코드 읽기(`pipeline.motion` 의 `if rig_run:` 안에서만 쓰임). 기다린 끝에 GLB 가 없으면 원인을 못 찾는다
- [x] (10/10 6회차: Blender·bpy 줄마다 `[필수: 둘 중 하나]`/`[required: one of]`, 찾은 쪽이 있으면 다른 쪽은 `[필요 없음]`/`[not needed]`(bpy 만 있으면 Blender 줄에 "bpy 모듈을 대신 쓴다"), `DoctorTests.test_blender_and_bpy_are_marked_one_of_on_each_line` 두 언어·세 경우 — 옛 코드에서 6개 실패 확인, CHANGELOG, 시험 수 172) `bw doctor`: Blender 와 bpy 둘 다 `[required]` 로 찍혀 둘 다 깔아야 하는 줄 안다(마지막 줄에서야 "either one") → 표시를 "[required: one of]" 처럼 둘 중 하나임을 줄마다, 하나라도 있으면 없는 쪽은 `[not needed]`, 두 언어 시험 — 근거: 10/10 5회차 실측 출력. 설치 문제 이슈 템플릿이 붙이라는 출력이다
- [x] (10/10 6회차: 호출이 없으면 stderr 에 장부 경로(없으면 "아직 없음"+BW_HOME), 토큰 0 경로는 장부에 안 남는다는 것, `--days 30`, stdout JSON 그대로, 호출이 있으면 조용히, `test_cli.EmptyUsageTests` 두 언어 — 옛 코드에서 실패 확인, CHANGELOG, 시험 수 174) `bw usage`: 장부가 비면 0 만 든 JSON 을 찍는다 → stdout JSON 은 그대로 두고 stderr 에 "최근 N일 모델 호출 없음(장부: `<BW_HOME>/runs/ledger…`) — 토큰 0 경로만 썼다면 정상" 한 줄, 시험 — 근거: 10/10 5회차 실측. GUIDE 가 비용 확인 명령으로 안내하는데 0 이 '기록 안 됨' 인지 '안 썼음' 인지 모른다

## 2026-10-10 6회차 (공개 준비 기준, 사용자 체감 우선 — 빈 BW_HOME 에서 `bw`·`examples/` 를 직접 돌리고 README 설치 절을 처음부터 따라 함)

- [x] (10/10 6회차: 그 실행만 "state.json 을 읽지 못함(오류) — 이 실행만 건너뜀, 필요 없으면 <폴더> 를 지워도 된다" 한 줄, 키 없음·깨진 JSON·목록 JSON 셋, 종료 0, `test_cli.BrokenStateTests` 두 언어 — 옛 코드에서 실패 확인, CHANGELOG, 시험 수 175) `bw status`: 실행 하나의 state.json 이 읽히지 않으면(키 없음·깨진 JSON) 목록 전체가 `BLOCKED: KeyError: 'step'` 과 '이슈를 열라' 안내로 끝난다 → 그 실행만 "state.json 을 읽지 못함(→ 지워도 되는 폴더 경로)" 한 줄, 나머지는 그대로, 종료 0, 시험 — 근거: 10/10 6회차 실측(`runs/r1/state.json` 에 `{"status":"running"}` 만). 동기화 폴더(iCloud·Dropbox)의 충돌 사본이나 옛 버전 실행 하나가 목록 전체를 막는다
- [x] (10/10 6회차: 끝에 stderr "다음: `bw demo <id>` · `bw export <id>` · `bw motion --bvh <파일.bvh> --rig <id>`", stdout 은 보고서 한 줄 그대로, 안내한 명령이 실제 argparse 에 맞는지까지 `test_cli.NextStepTests` 두 언어 — 옛 코드에서 실패 확인, 두 README 의 `bw demo` 주석, CHANGELOG, 시험 수 176) 첫 결과 다음 단계: `bw rig` 가 끝나면 `report: <경로>` 한 줄뿐이라 README 다음 줄 `bw demo <run-id>` 의 run-id 를 경로에서 오려 내야 한다 → 끝에 "다음: `bw demo <id>` · `bw export <id>` · `bw motion --bvh … --rig <id>`" 한 줄(stderr), 두 언어 시험 — 근거: 10/10 6회차 코드 읽기(`cli._main` 마지막 줄)와 README "First run" 셋째·넷째 줄
- [x] (10/10 6회차: 두 README 설치 절을 `git clone … && cd bonewright` → `python3 -m venv .venv && source .venv/bin/activate` → `pip install .` → `bw doctor`("Blender 나 bpy 중 하나")로, Windows venv 한 줄, headless 는 Python 3.13 명시, `FirstRunTests.test_install_starts_from_nothing` — clone 주소가 pyproject Homepage 와 같은지까지, 옛 README 에서 실패 확인, CHANGELOG, 시험 수 177. Mac 에서 빈 폴더로 한 번 따라 해 볼 것) README 설치 절: `pip install .` 앞에 저장소를 받는 줄이 없고(첫 실행 첫 명령도 저장소 안 `tests/assets/` 를 쓴다), macOS Homebrew Python 은 venv 없이 `pip install` 을 PEP 668(externally-managed-environment)로 거절하며, `bw doctor` 주석은 "Rigify 를 확인" 이라 하지만 doctor 는 Rigify 를 보지 않는다 → 두 README 에 clone·venv 줄, 주석을 실제 확인 항목으로, `test_docs` 가 설치 절 첫 명령이 clone 인지 지키게 — 근거: 10/10 6회차 README 설치 절을 빈 상태에서 따라 함, `cli.doctor` 코드
- [x] (10/10 7회차: 두 언어 안내 끝을 `python3 examples/rig_sample.py --table adventurer` 로, `ExampleMessageTests.test_no_blender_hint_runs_as_pasted` 가 그 명령을 그대로 돌림 — 옛 코드에서 실패 확인) `examples/rig_sample.py`: Blender 없을 때 안내가 "For the bone table alone: --table x.glb" 로 자리표시 파일을 준다 → 저장소에 있는 `tests/assets/quaternius_adventurer.glb` 로 그대로 붙여 넣어 도는 명령을, 시험 — 근거: 10/10 6회차 실측(`--table tests/assets/quaternius_adventurer.glb` 는 Blender 없이 표가 나옴)
- [x] (10/10 7회차: run_id 를 nargs="?" 로, 없으면 02_rigged.blend 가 있는 가장 최근 실행으로 `bw demo <id>`·`bw status`, 없으면 `bw rig <메시>`·찾은 곳 — `test_errors.MissingRunIdTests` 2개, 옛 코드에서 실패 확인) `bw demo`·`bw export` 를 run-id 없이 치면 argparse 의 "the following arguments are required: run_id" 로 끝난다 → `BLOCKED:` + 가장 최근 실행 id 를 넣은 명령과 `bw status`, 시험 — 근거: 10/10 6회차 실측. README 첫 실행이 `bw demo <run-id>` 를 자리표시 그대로 보여 준다

## 2026-10-10 7회차 (공개 준비 기준, 사용자 체감 우선 — 빈 BW_HOME·Blender 없음에서 `bw` 하위 명령을 인자 없이·틀린 값으로 쳐 봄)

- [x] (10/10 7회차: rig 하위 파서의 `error` 에 "required: mesh" 일 때만 한 줄을 붙이는 `_hint_on_missing`, `BareCommandTests.test_bare_rig_ends_with_a_command_that_parses` 가 안내한 명령을 README 와 대조하고 cli 에 그대로 넣어 봄 — 옛 코드에서 실패 확인) 인자 없는 `bw rig`: argparse 사용법 7줄 + "the following arguments are required: mesh" 로 끝난다 → 저장소 캐릭터로 그대로 도는 첫 명령(`bw rig tests/assets/quaternius_adventurer.glb --from-skeleton --no-judge`)과 README 첫 실행 안내, 종료 2 유지, 두 언어 시험 — 근거: 10/10 7회차 실측. 설치 직후 `bw rig` 만 쳐 보는 사람이 가장 먼저 보는 화면이다
- [x] (10/10 8회차: `cli.positive_int`, `test_cli.PositiveNumberTests` — 옛 코드에서 4개 실패 확인) `bw demo --size 0`·`--frames -1`: 값 검사가 없어 리그가 있으면 실행 폴더를 만들고 Blender 렌더까지 간 뒤 실패한다 → argparse 에서 양의 정수만 받고 `--size 640` 같은 예를 주는 한 줄, 시험 — 근거: 10/10 7회차 코드 읽기(`pipeline.demo` 가 `size`·`frames` 를 그대로 `render_demo` 에 넘김, `cli` 는 `type=int` 뿐)
- [x] (10/10 7회차: 그 시험이 stderr 도 가로채고 보고서 경로를 실제 모양(`runs/r/report.md`)으로 — 블렌더 없는 `python3 -m unittest` 출력이 점·s 와 요약 3줄만 남는 것을 확인. 전체 시험 안에서 전체 시험을 다시 돌리는 시험은 무거워 두지 않았다; Blender 시험의 출력은 Mac 에서 볼 것) 단위 시험이 진짜 stderr 에 "next: `bw demo ` …"(id 빈칸) 한 줄을 흘린다 → `test_cli.PinInputTests.test_accepts_finite_head_and_tail` 에서 stderr 도 가로채고, 시험 출력이 점(.)만 남는지 — 근거: 10/10 7회차 `python3 -m unittest` 출력. CI 로그에서 실제 오류처럼 읽히고 빈 id 는 버그로 보인다
- [x] (10/10 8회차: 같은 `positive_int`, 예는 `--days 30`, 같은 시험) `bw usage --days 0`·음수: "no model calls in the last 0 days" 로 0 을 그대로 받는다 → 1 이상만, 예를 준 한 줄 오류, 시험 — 근거: 10/10 7회차 실측(종료 0, 빈 JSON)
- [x] (10/10 7회차: 같은 `_hint_on_missing` 으로 `fetch_bench_assets.py --only samples && bw bench bench-assets/samples`, `BareCommandTests.test_bare_bench_points_at_fetch_script` 가 받기 스크립트 `--help`·`--only` 값·기본 폴더와 대조하고 bw 쪽을 cli 에 넣어 봄 — 옛 코드에서 실패 확인) 인자 없는 `bw bench`: argparse "required: meshes" 로 끝난다 → 벤치 자산 받는 명령(`python3 scripts/fetch_bench_assets.py`)과 폴더를 통째로 줄 수 있다는 안내, 시험 — 근거: 10/10 7회차 실측. 5회차에 빈 폴더·없는 파일은 고쳤지만 인자 없음은 argparse 그대로다


## 2026-10-10 8회차 추가 (공개 준비 기준 — 하위 명령을 틀린 값으로 쳐 본 실측)

- [x] (10/10 8회차: `positive_int`·`metavar TOKENS`·도움말, `pipeline` 은 `is not None`, `test_cli.BudgetHelpTests`·`PositiveNumberTests` 확장 — 옛 코드에서 실패 확인) `bw rig --budget 0`·`-1`: `pipeline.rig` 가 `if budget:` 라 0 은 말없이 무시되고, 음수는 Blender 분석을 다 한 뒤 첫 모델 호출에서 "예산 상한 도달" 로 멈춘다. `--help` 에 설명도 없다 → 1 이상만(8회차 `positive_int`), 무엇의 상한인지(입력 토큰, 기본 600,000) 도움말 한 줄, 시험 — 근거: 10/10 8회차 코드 읽기(`pipeline.py:189`, `config.DEFAULTS["budget"]`)
- [x] (10/10 8회차: `need_file` 의 폴더 분기·`many`, 안의 첫 메시 예, `test_errors.test_folder_instead_of_mesh` — 옛 코드에서 실패 확인) `bw rig .`(폴더)이 "mesh file not found: ." 라 한다 — 폴더는 있다 → 폴더면 "메시 파일 하나를 준다, 여럿이면 `bw bench <폴더>`" 와 그 폴더 안 첫 메시로 친 명령 한 줄, 시험 — 근거: 10/10 8회차 실측(종료 2, 거짓 안내)
- [x] (10/10 8회차: `pipeline.need_mesh_bytes`, `test_errors.test_empty_or_fake_glb_stops_before_blender` — 옛 코드에서 실패 확인) 0바이트·glTF 가 아닌 `.glb` 를 `bw rig` 에 주면 Blender 를 띄운 뒤에야 실패한다(Blender 없는 곳에선 "Blender not found" 로 원인이 가려진다) → Blender 전에 파일 크기 0·GLB 머리(`glTF`) 를 보고 `BLOCKED:` + 다시 내보내라는 안내, 시험 — 근거: 10/10 8회차 실측(`touch broken.glb; bw rig broken.glb` → "Blender not found")
- [x] (10/10 8회차: 21개 모두 두 언어, `test_cli.ArgumentHelpTests` — 옛 코드에서 40곳 실패) 하위 명령 도움말이 비어 있는 인자 21개(`bw rig` 의 `mesh`·`--preset`·`--run-id`·`--budget`·`--quiet`, `bw demo` 의 `--size`·`--frames`, `bw usage --days` 등) → 두 언어 한 줄씩, 모든 하위 명령의 모든 인자에 help 가 있는지 보는 시험 — 근거: 10/10 8회차 파서 집계(rig 5·motion 4·export 2·demo 4·bench 4·status 1·usage 1)
- [x] (10/10 8회차: `cli._hint_on_bad_command` — difflib, `resume` 은 무엇이 대신하는지, `test_cli.BadCommandTests` 2개 — 옛 코드에서 실패) 틀린 하위 명령(`bw resume`·`bw run` 등)에 argparse 기본 "invalid choice" 만 나온다 → 가장 가까운 명령(`difflib`)과 `bw --help` 를 붙인 한 줄(종료 2 유지), 두 언어 시험 — 근거: 10/10 8회차 실측(`bw resume nope` → 선택지 나열만). README 옛 판에 `bw resume` 이 있었다(`test_checker_catches_mistakes`)


## 2026-10-10 8회차 둘째 묶음 (공개 준비 기준 — 실측)

- [x] (10/10 8회차: 폴더 → `<id>.glb`, 다른 확장자·없는 부모 폴더는 Blender 전 BLOCKED, `test_errors.test_export_out_is_checked_before_blender` — 옛 코드에서 실패) `bw export <id> --out <폴더>`·`--out x.fbx`: 출력 경로 검사가 없어 Blender 를 띄운 뒤에야 실패한다 → 폴더면 그 안 `<id>.glb` 로, `.glb` 가 아니면 Blender 전에 `BLOCKED:` + `--out runs/<id>/rigged.glb` 예, 시험 — 근거: 10/10 8회차 실측(Blender 없는 곳에선 "Blender not found" 로 가려짐)
- [x] (10/10 8회차: `pipeline.load_bone_map` 을 입력 확인 단계로, `test_errors.test_missing_map_stops_before_blender` — 옛 코드에서 실패) `bw motion --map nope.json`: 없는 매핑 파일이 BVH 를 Blender 로 가져온 뒤에야 걸린다 → `--bvh`·`--rig` 처럼 Blender 전에 `need_file`, 시험 — 근거: 10/10 8회차 실측(`--map nope.json` → "⚙ blender import_bvh" 뒤 Blender 단계)
- [x] (10/10 8회차: `blender.require` 를 네 곳의 `Run(...)` 앞에, motion 의 kimodo 확인도 그 앞으로, `MissingToolTests` 2개 — 옛 코드에서 실패, bpy 5.2.2 로 192개 통과) Blender 가 없을 때 `bw rig`·`bw motion` 이 실행 폴더(`runs/rig-…`, `runs/motion-…`)를 먼저 만들고 실패해 `bw status` 에 "analyze failed"·"import_bvh failed" 가 쌓인다 → Blender 를 찾을 수 있는지 실행 폴더를 만들기 전에 보고, 시험 — 근거: 10/10 8회차 실측(이 컨테이너 `bw status` 에 실패 실행 3개)
- [x] (10/10 8회차: `Run(state_file=…)` — export_state.json·demo_state.json, `test_errors.test_failed_export_keeps_the_rig_status`) 이미 리깅된 실행에 `bw export` 가 실패하면 그 실행의 `bw status` 가 "export_rig failed" 로 바뀌어 리그까지 실패한 것처럼 보인다 → 내보내기 실패는 리그 상태를 덮지 않게(따로 기록), 시험 — 근거: 10/10 8회차 실측(`runs/r1` 에 `02_rigged.blend` 를 두고 `bw export r1` → status "r1: export_rig failed")
- [x] (10/10 8회차: "input tokens N"·실패/예산/한도 줄 끝에 `bw doctor --for-issue <id>`(로그 꼬리를 보여 주는 명령 — `bw status <id>` 는 같은 줄만 찍어 쓸모가 없다), `test_cli.StatusLineTests`) `bw status` 목록 줄의 `· in 0` 이 무엇인지 안 보인다(입력 토큰) → "tokens in 0" 처럼 단위를 붙이고, 실패 줄 끝에 `bw status <id>` 로 이유를 보라는 안내, 시험 — 근거: 10/10 8회차 실측
