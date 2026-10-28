# 행동 강령(CODE_OF_CONDUCT) 결정용 메모

작성: 2026-10-07 클라우드 회차. **결정은 샘님.** 아무것도 저장소 루트에 넣지 않았다.

## 지금 상태

- 루트에 `LICENSE`·`CONTRIBUTING.md`·`SECURITY.md`·이슈/PR 템플릿은 있고 `CODE_OF_CONDUCT.md` 는 없다.
- GitHub *Insights → Community Standards* 점검표는 행동 강령을 한 칸으로 본다. 없어도 공개·기여는 된다.
- 비공개 저장소라 지금은 점검표가 안 보인다(공개 전환 뒤에 보인다).

## 선택지

| 안 | 할 일 | 장점 | 단점 |
|---|---|---|---|
| A. 넣는다(권장) | `docs/drafts/CODE_OF_CONDUCT.md` 를 루트로 옮기고 연락 칸 채우기 | 점검표 완료, 가장 흔한 문안(Contributor Covenant 2.1)이라 설명이 필요 없다 | 신고를 받을 연락처와, 받으면 실제로 처리할 사람이 필요하다 |
| B. 짧은 한 단락 | CONTRIBUTING 끝에 "서로 존중, 문제는 비공개 보안 신고 창구로" 정도 | 관리 부담이 가장 적다 | 점검표에는 '없음'으로 남는다 |
| C. 안 넣는다 | 없음 | — | 처음 보는 기여자가 기준을 알 수 없다 |

## A 를 고르면 정할 것: 연락 칸 `[INSERT CONTACT METHOD]`

초안 39번째 줄(Enforcement 절)에 그대로 남겨 두었다(비워 둔 채 공개하면 안 된다). 후보:

1. 프로젝트 전용 메일 주소(개인 주소를 쓰지 않으려면 새로 만든다)
2. GitHub 비공개 신고 경로: `SECURITY.md` 와 같은 *Security → Report a vulnerability* 는 보안 전용이라 부적합.
   GitHub 의 *Report content*(각 댓글의 … 메뉴)는 GitHub 운영진에게 가므로 프로젝트 연락처를 대신하지 못한다.
3. 저장소 소유자 GitHub 계정으로 연락(공개 프로필에 연락 방법이 있을 때만 성립)

## 초안 출처·라이선스

- `docs/drafts/CODE_OF_CONDUCT.md` = Contributor Covenant 2.1 원문
  (`EthicalSource/contributor_covenant` 저장소 `release` 브랜치 `content/version/2/1/code_of_conduct.md`, 맨 위 설정 머리말 5줄만 뺌).
  원문 라이선스는 CC BY 4.0 이고 끝의 Attribution 절이 출처 표기를 겸한다 — 그 절은 지우지 않는다.
- 한국어 번역은 공식 번역 목록(<https://www.contributor-covenant.org/translations>)에서 받는다. 직접 번역하지 않는다.

## A 로 정했을 때 순서(Mac)

```bash
git mv docs/drafts/CODE_OF_CONDUCT.md CODE_OF_CONDUCT.md   # 그다음 [INSERT CONTACT METHOD] 를 채운다
```

그 뒤 CONTRIBUTING 맨 위에 "This project follows the [Code of Conduct](CODE_OF_CONDUCT.md)." 한 줄과,
`tests/test_docs.py` 의 점검 문서 목록에 `CODE_OF_CONDUCT.md` 를 더한다(클라우드 회차에 맡겨도 된다).
