# 릴리스 절차

태그·GitHub 릴리스는 **Mac 총괄(샘님)만** 만든다. 클라우드 회차는 아래 1~3단계 준비까지만 하고 태그는 만들지 않는다.

## 버전 정하기 (0.x 동안)

| 바뀐 것 | 올릴 자리 | 예 |
|---|---|---|
| 고침·문서·예제만, 명령·옵션 그대로 | 셋째 (0.2.0 → 0.2.1) | 오류 메시지, README, `examples/` |
| 새 명령·옵션, 기본값 변경, 결과 숫자(벤치)가 달라지는 변경 | 둘째 (0.2.x → 0.3.0) | `--from-shape`, 가중치 기본값 |

다음 버전 제안은 `CHANGELOG.md` 의 `[Unreleased]` 첫 줄에 적어 둔다.
`tests.test_release` 가 그 줄의 버전이 지금 버전보다 큰지, 셋째 자리 제안인데 새 플래그·기본값 변경을 적지 않았는지 본다.

### 다음 버전 점검 (2026-10-08, 클라우드)

v0.2.0(9/20) 뒤 `[Unreleased]` 에 쌓인 것을 위 표에 대 보면 **0.3.0** 이다. 10/7 까지는 0.2.1 로 적혀 있었다.

| 쌓인 것 | 표의 칸 |
|---|---|
| `bw --version`, `bw doctor --for-issue [RUN_ID]` | 새 옵션 → 둘째 |
| `bw rig --lang` 생략 시 ko → BW_LANG·로캘(10/8) | 기본값 변경 → 둘째 |
| 화면 문구 영어 기본(BW_LANG), `bw doctor` 종료코드(codex 없어도 0) | 기본 동작 변경 → 둘째 |
| report.md 상대 경로, 입력 오류 `Blocked`, 사족 렌더 카메라, plugin-path, `--pin` 검사 | 고침 → 셋째 |
| GUIDE·README 재구성, 예시 결과 2개, 이슈·PR 템플릿, 시험 추가 | 문서·예제 → 셋째 |

벤치 숫자를 바꾸는 변경은 없다(사족 렌더 카메라는 판정 그림만, 사람은 그대로). 태그 전에 Mac 에서 할 일:
1단계 시험 → 2단계 세 곳을 `0.3.0` 으로 → 3단계 `## [0.3.0] - 날짜`, 맨 아래 `[0.3.0]: …/compare/v0.2.0...v0.3.0`
와 `[Unreleased]: …/compare/v0.3.0...HEAD`. 0.2.1 로 내기로 하면 CHANGELOG 첫 줄만 바꾸면 된다(시험이 "새 플래그"
문구를 보고 실패하므로 그 줄의 이유도 같이 고친다).

## 단계

1. **시험** — Mac 에서 블렌더 시험까지 전부 통과:
   ```bash
   BW_REQUIRE_BLENDER=1 python3 -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release tests.test_docs tests.test_i18n
   python3 scripts/check_license_boundary.py
   ```
   결과는 `docs/test-reports/latest.md` 에 남긴다.
2. **버전 문자열 세 곳** — 같은 값으로 바꾼다. `tests.test_release` 가 셋이 다르면 실패한다.
   - `pyproject.toml` 의 `version`
   - `bonewright/__init__.py` 의 `__version__`
   - `plugin/.codex-plugin/plugin.json` 의 `version`
3. **CHANGELOG** — `## [Unreleased]` 아래 내용을 `## [X.Y.Z] - YYYY-MM-DD` 로 옮기고, 빈 `[Unreleased]` 를 맨 위에 남긴다.
   맨 아래 링크도 고친다:
   ```
   [Unreleased]: https://github.com/choisam4u-creator/bonewright/compare/vX.Y.Z...HEAD
   [X.Y.Z]: https://github.com/choisam4u-creator/bonewright/compare/v이전...vX.Y.Z
   ```
4. **PR → main 병합** 뒤 main 에서 주석 달린 태그(Mac):
   ```bash
   git checkout main && git pull && git tag -a vX.Y.Z -m "bonewright vX.Y.Z" && git push origin vX.Y.Z
   ```
   태그 메시지는 v0.2.0 처럼 벤치 숫자와 주요 기능 몇 줄을 적는다(`git show v0.2.0`).
5. **GitHub 릴리스** — 본문은 CHANGELOG 의 그 절을 그대로 붙인다. 저장소가 비공개인 동안은 릴리스도 비공개다.

## 공개 전환 전에

`docs/PRE-PUBLIC-AUDIT.md` 의 "판단 필요" 항목(기록 속 개인 경로, 병합 커밋의 개인 메일)을 먼저 정한다.
기록을 다시 쓰기로 하면 태그도 다시 만들어야 하므로 **기록 정리 → 태그** 순서로 한다.
