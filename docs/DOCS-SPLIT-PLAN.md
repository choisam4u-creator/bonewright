# docs/ 정리 안: 공개 문서와 작업 노트 나누기 (2026-10-06, 클라우드)

**안만 적었다. 파일은 하나도 옮기지 않았다** — 옮길지·어디로 옮길지·공개 저장소에 남길지는 샘님이 정한다.
범위: `main` d865979 기준 `docs/` 전부.

## 왜

공개 저장소의 `docs/` 를 열면 날짜 붙은 한국어 HTML 17개와 `reports/` 9개가 `GUIDE.md` 보다 많이 보인다.
처음 온 사람이 읽을 문서(GUIDE·RELEASING)와 개발 중 남긴 기록(연구·현황·벤치 노트)이 한 폴더에 섞였다.
`PRE-PUBLIC-AUDIT.md` 2절의 현재 트리 개인 경로 2곳도 모두 이 기록 쪽(`docs/reports/`)에 있다.

## 그대로 둘 것 (공개 문서·코드가 가리키는 파일)

| 파일 | 누가 가리키나 | 비고 |
|---|---|---|
| `GUIDE.md` | README·README.ko·오류 메시지·`bw doctor` | 영문, 공개 문서의 중심 |
| `RELEASING.md` | CHANGELOG·`tests/test_release.py` | |
| `ROADMAP.md` | CONTRIBUTING(2곳)·GUIDE·`pipeline.py`·`bpy_scripts/fit_generate.py` 주석 | **한국어 55KB**. 공개 문서로 남기려면 영문 요약이 필요(새 백로그 후보) |
| `bench-unresolved-fingerprints.json` | GUIDE·`scripts/fetch_bench_assets.py` | 데이터 파일 |
| `media/` | README·ATTRIBUTION | 그림·라이선스 표기 |

## `docs/notes/` 로 옮길 후보 (작업 기록)

옮겨도 깨지는 링크는 **노트끼리의 언급뿐**이다(아래 "가리키는 곳" 열). README·GUIDE·코드·시험은 이 파일들을 가리키지 않는다(10/6 `grep` 확인).
HTML 안의 상대 `href` 는 26개 파일 모두 0개 — 바깥 링크(https)만 있으므로 옮겨도 HTML 안 링크는 안 깨진다.

| 파일 | 크기 | 내용(제목) | 가리키는 곳 | 개인 경로 |
|---|---|---|---|---|
| `research-20260913.html` | 19KB | Blender 리깅·애니메이션 × Codex 자료조사 | PRE-PUBLIC-AUDIT·CLOUD-BACKLOG(문구) | 현재 없음, **git 기록에 `/Users/…`** |
| `research-autorig-sources-20260914.html` | 51KB | 자동 리깅 도구·소스 조사 | v0.1·v0.2 status(본문 `<code>`) | 없음 |
| `research-free-rigged-assets-20260915.html` | 47KB | 무료 리깅 자산 조사 | — | 없음 |
| `unimate-analysis-20260914.html` | 7KB | UniMate 분석 | — | 없음 |
| `epic-fab-assets-20260915.html` | 12KB | 에픽(Fab) 자산 사용 가능 여부 | — | 없음 |
| `v0.1-status-20260913.html` | 18KB | v0.1 상태 | PRE-PUBLIC-AUDIT | 현재 없음, **git 기록에 `/Users/…`** |
| `v0.2-status-20260914.html` | 11KB | v0.2 상태 | — | 없음 |
| `status-20260915.html` | 14KB | 골반 진단 + 오픈소스 완성도 | ROADMAP 685행(문구) | 없음 |
| `bench-20260915.html` | 5KB | 정답 대조 벤치마크 | — | 없음 |
| `bench-assets-20260915.html` | 7KB | 벤치마크 17종 | — | 없음 |
| `bench-quadruped-20260915.html` | 14KB | 사족 벤치마크 기준선 | — | 없음 |
| `bench-baseline-20260915.md` | 3KB | 벤치 기준선 | research-free-rigged-assets(본문 2곳) | 없음 |
| `gate-and-release-20260915.html` | 10KB | 거절 게이트 + 공개 준비 | — | 없음 |
| `pelvis-fix-20260915.html` | 6KB | 골반 높이 수정 | — | 없음 |
| `quad-hock-20260915.html` | 12KB | 사족 뒷발목 수정 | — | 없음 |
| `quad-landmarks-20260915.html` | 15KB | 사족 관절 찾기 | — | 없음 |
| `quad-pelvis-20260915.html` | 13KB | 사족 골반 오차 수정 | — | 없음 |
| `retarget-20260915.html` | 10KB | BVH 리타게팅 | — | 없음 |
| `reports/2026-09-17-a.html` | 17KB | 진행 보고 | — | **173행 저장소 경로를 `<저장소>`로 바꾼다** |
| `reports/2026-09-17-b·c`, `09-18-a·b`, `09-19-b`, `09-20-audit`, `09-20-status` (7개) | 7~13KB | 진행 보고·문서 검증 | — | 없음 |
| `reports/2026-09-19-a.html` | 9KB | 오픈소스 준비 | — | **32행 개인 경로 설명 문구(사용자 이름이 드러남)** |
| `auto-improve/2026-09-24.md` | 1KB | 3일 개선 기록 | PRE-PUBLIC-AUDIT | 없음 |

## 내부 운영 파일 (공개 여부를 따로 정할 것)

| 파일 | 성격 | 안 |
|---|---|---|
| `CLOUD-BACKLOG.md` | 클라우드 회차 할 일 | 공개해도 무해하나 독자에게 의미 없음 → `docs/notes/` 또는 공개 전 삭제 |
| `PRE-PUBLIC-AUDIT.md`, 이 파일 | 공개 전 점검 | 공개 직전 역할이 끝남 → `docs/notes/` |
| `test-reports/latest.md`, `CLOUD-NOTES.md` | Mac·클라우드 시험 기록 | **`RELEASING.md` 21행이 `latest.md` 를 가리킨다** → 옮기면 그 줄도 고쳐야 한다. 그대로 두는 것을 권함 |

## 옮길 때 같이 고칠 것 (옮기기로 정하면)

1. `git mv docs/*-2026091*.html docs/bench-baseline-20260915.md docs/reports docs/auto-improve docs/notes/` (한 커밋)
2. 문구 안 경로: ROADMAP 685행 `docs/status-20260915.html`, v0.1·v0.2 status 의 `docs/research-autorig-…`,
   PRE-PUBLIC-AUDIT 의 경로들, CLOUD-BACKLOG 10/6 항목 문구 → `docs/notes/…`
3. `docs/notes/README.md` 한 장: "개발 중 기록(한국어), 숫자는 그 날짜 기준이라 지금과 다를 수 있다. 현재 문서는 GUIDE."
4. 개인 경로 2곳(`reports/2026-09-17-a.html:173`, `reports/2026-09-19-a.html:32`)은 옮기는 김에 `<저장소>`·`/Users/<이름>/…` 로
5. `python3 -m unittest tests.test_docs` — 공개 문서 상대 링크 점검이 계속 통과하는지

## 다른 선택지

- **공개 저장소에서 아예 빼기**: 노트를 별도 비공개 저장소(또는 위키)로. `docs/` 가 가장 깔끔해지지만, git 기록에는 남으므로
  개인 경로 문제(PRE-PUBLIC-AUDIT 2절)는 기록 재작성 없이는 그대로다.
- **그대로 두고 `docs/README.md` 로 안내만**: 가장 싸다. "공개 문서는 GUIDE·RELEASING·ROADMAP, 나머지는 날짜별 작업 기록" 한 장.
