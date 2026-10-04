# 릴리스 절차

태그·GitHub 릴리스는 **Mac 총괄(샘님)만** 만든다. 클라우드 회차는 아래 1~3단계 준비까지만 하고 태그는 만들지 않는다.

## 버전 정하기 (0.x 동안)

| 바뀐 것 | 올릴 자리 | 예 |
|---|---|---|
| 고침·문서·예제만, 명령·옵션 그대로 | 셋째 (0.2.0 → 0.2.1) | 오류 메시지, README, `examples/` |
| 새 명령·옵션, 기본값 변경, 결과 숫자(벤치)가 달라지는 변경 | 둘째 (0.2.x → 0.3.0) | `--from-shape`, 가중치 기본값 |

다음 버전 제안은 `CHANGELOG.md` 의 `[Unreleased]` 첫 줄에 적어 둔다.

## 단계

1. **시험** — Mac 에서 블렌더 시험까지 전부 통과:
   ```bash
   BW_REQUIRE_BLENDER=1 python3 -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release
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
