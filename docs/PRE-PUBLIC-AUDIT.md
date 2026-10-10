# 공개 전 점검 보고 (2026-10-04, 클라우드)

저장소를 공개로 바꾸기 전에 볼 것만 모았다. **아무것도 지우거나 기록을 고치지 않았다** — 무엇을 할지는 샘님이 정한다.
범위: 현재 트리(`main` 27fd528 기준) + `git rev-list --all` 의 커밋 56개(원격 브랜치 `auto-improve/20260924` 포함).

## 한눈에

| 항목 | 현재 트리 | git 기록 | 공개 전 조치 필요? |
|---|---|---|---|
| 비밀 값(API 키·토큰·개인 키) | 없음 | 없음 | 아니오 |
| 비밀 파일(`.env`·`*.pem`·`auth.json`·`runs/config.json` 등) | 없음 | 없음 | 아니오 |
| 개인 절대경로 `/Users/…` | 설명 문구 1곳 + `~/Desktop/…` 1곳 | 문서 3개에 전체 경로(삭제 커밋 d6091c2 이전) | **판단 필요** (아래 2) |
| 커밋 작성자 메일 | — | 커밋 2개에 개인 gmail 주소 | **판단 필요** (아래 3) |
| 라이선스 없는 에셋 | 없음 | 과거에만 있던 이진 파일 없음 | 아니오(표기 보강 1건 권장, 아래 4) |

## 다시 훑음 (2026-10-10, 클라우드 4회차)

기준: `claude/cloud-work` 69f8d08(= `main` 145fe4b + PR #10 분), `git rev-list --all` 커밋 162개. 아래 "재현 명령" 과 같은 방식.
**이번에도 아무것도 지우거나 기록을 고치지 않았다.**

| 항목 | 10/4 → 10/10 | 공개 전 조치 필요? |
|---|---|---|
| 비밀 값·비밀 파일 | 없음 → 없음(무늬에 걸리는 것은 이 문서의 무늬 목록뿐) | 아니오 |
| 개인 절대경로(현재 트리) | 2곳 → 같은 2곳(`docs/reports/2026-09-17-a.html:173`, `2026-09-19-a.html:32`). 27fd528 뒤 새로 든 파일 21개에는 없음 | 2절 그대로 |
| 새 파일의 `/Users/`·`/home/` | — | 아니오: `scrub()`·`check_issue_report.py` 의 무늬와 시험의 가짜 이름(`alice`)뿐 |
| 커밋 메일 | 개인 gmail 2개 → **9개**. 모두 GitHub 웹에서 병합한 커밋(PR #1~#9), 커밋하는 쪽은 `noreply@github.com` | **판단 필요**: 웹 병합 한 번마다 하나씩 는다. 3절 설정을 켜기 전까지 PR #10 병합도 하나를 더한다 |
| 에셋·미디어 | 이진 파일 8개 → 같은 8개, 표기 모두 있음. 새 예시(`examples/sample-output/*.md`)는 절차 생성 메시라 외부 자산 없음 | 아니오 |
| 이름 | — | 참고: 별칭 "샘님" 이 내부 기록 6개(`docs/CLOUD-BACKLOG.md`·`CLOUD-NOTES.md`·`RELEASING.md`·`CODE-OF-CONDUCT-PLAN.md`·`DOCS-SPLIT-PLAN.md`·이 문서)에 있다. 공개 문서(README·GUIDE·examples)에는 없음 |

## 1. 비밀 값

다음 무늬로 현재 트리와 모든 커밋을 찾았고 걸린 것이 없다:
`sk-…`, `ghp_…`, `github_pat_`, `AKIA…`, `-----BEGIN … PRIVATE KEY`, `xoxb-/xoxp-`, `AIza…`,
`api_key = "…"`, `password|secret|bearer|authorization` 뒤 `=`/`:` 값. 파일 이름(`.env`, `.pem`, `.key`, `id_rsa`,
`credentials`, `.p12`, `auth.json`, `config.json`)도 기록 전체에 없다. `runs/` 는 `.gitignore` 에 있다.

## 2. 개인 경로

**현재 트리**
- `docs/reports/2026-09-19-a.html:32` — "개인 절대경로(`/Users/sam/…`) 제거"라는 **설명 문구**. 실제 경로는 아니고 사용자 이름 `sam` 만 드러난다.
- `docs/reports/2026-09-17-a.html:173` — `~/Desktop/Gpt_Codex/bonewright` (홈 아래 폴더 구조).

**git 기록에만 있음** (d6091c2 "개인 경로를 지우고"에서 현재 트리에서는 지워짐)
- `docs/research-20260913.html`, `docs/v0.1-status-20260913.html` — `/Users/sam/Desktop/Gpt_Codex/bonewright/`,
  `/Users/sam/Desktop/Gpt_Codex/blender-anim-codex/vendor/kimodo.cpp/` 등 전체 경로(각 12개 커밋에 남음).

위험도는 낮다(사용자 이름·폴더 구조 정도, 비밀 아님). 선택지:
1. 그대로 공개 — 가장 간단. 현재 트리의 `~/Desktop/…` 한 줄만 `<저장소>` 로 바꾸는 작은 PR 정도.
2. 공개 전 기록 재작성(`git filter-repo --replace-text`) — 커밋 해시가 전부 바뀌고 열린 PR·태그 `v0.2.0` 을 다시 만들어야 한다.
   되돌릴 수 없으니 Mac 총괄이 직접, 백업 뒤에.

## 3. 커밋 작성자 메일

- 49개 커밋은 GitHub noreply 주소, 5개는 `noreply@anthropic.com`(공동 작성 표기).
- **GitHub 웹에서 PR 을 병합한 커밋 2개(9cf8c5a, 27fd528)는 개인 gmail 주소**로 기록됐다. 공개하면 누구나 `git log` 로 본다.
- 앞으로 막는 법: GitHub 설정 → Emails → "Keep my email addresses private" 와 "Block command line pushes that expose my email" 을 켠다.
  이미 들어간 2개는 2번의 기록 재작성(`--mailmap`)으로만 바꿀 수 있다.

## 4. 에셋·미디어 라이선스

| 파일 | 크기 | 출처·라이선스 | 상태 |
|---|---|---|---|
| `tests/assets/quaternius_adventurer.glb` | 1.9 MB | Quaternius "Adventurer", CC0 1.0 — `tests/assets/README.md` | 표기 있음 |
| `docs/media/rig-views.png`, `rig-ik.gif`, `walk-retarget.gif` | 0.2 MB씩 | GDQuest Mannequiny 렌더, CC BY 4.0 — `docs/media/ATTRIBUTION.md` | 표기·변경 내용 있음 |
| `docs/media/quad-views.png`, `quad-demo.gif` | 0.1·0.6 MB | Quaternius Wolf 렌더, CC0 — 같은 파일 | 표기 있음 |
| `spikes/rig_view2.png` | 0.1 MB | `spikes/render_rig2.py` 가 원기둥·구로 절차 생성 | 외부 자산 아님 |
| `spikes/motion_out/walk_wave.bvh` | 46 KB | kimodo.cpp + NVIDIA SOMA RP v1.1 가중치로 생성 | 표기 있음(10/6 보강) |

- 원본 메시(`mannequiny.glb`, `Wolf.gltf`)는 기록 어디에도 커밋된 적이 없다(내려받기 스크립트로만 받음).
- `walk_wave.bvh`: `ATTRIBUTION.md` 는 "이 저장소의 스파이크가 만든 것"이라고만 적었다. `docs/research-20260913.html` 의 기록대로
  SOMA 가중치는 NVIDIA Open Model License(상업 이용 가능)이므로 문제는 없어 보이나, 생성에 쓴 모델과 그 라이선스 이름을
  `ATTRIBUTION.md` 에 한 줄 적어 두면 공개 뒤 질문을 줄인다. (SMPL-X 계열 가중치는 비상업이라 쓰지 않았는지 Mac 에서 확인.)
- 코드 라이선스 경계: `python3 scripts/check_license_boundary.py` OK(MIT 영역 14개 파일이 bpy 미사용, `bonewright/bpy_scripts/` 는 GPL).

## 재현 명령

```bash
git rev-list --all | xargs -n20 git grep -lI "/Users/" | sed 's/^[0-9a-f]*://' | sort | uniq -c
git log --all --format='%ae' | sort | uniq -c
git ls-files | grep -iE '\.(glb|gltf|fbx|obj|blend|bvh|png|jpg|gif|mp4|gguf)$'
```
