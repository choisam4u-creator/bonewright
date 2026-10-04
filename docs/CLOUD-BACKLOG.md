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
- [ ] `examples/` 결과 예시 커밋: `examples/out/` 이 git 제외라 처음 보는 사람이 표 모양을 모른다 → Mac 에서 만든 `capsule_doll.md` 1개를 `examples/sample-output/` 에 싣고 README 에서 링크(라이선스: 절차 생성 메시라 문제 없음) — 근거: 공개 준비 '예제' 조건
