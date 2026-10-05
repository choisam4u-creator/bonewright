# 시험

| 묶음 | 블렌더 | 시험 수 | 무엇을 보나 |
|---|---|---|---|
| `tests.test_mock` 의 `RigMockTests` | **필요** (`@requires_blender`) | 12 | 리그 생성·스키닝·리타겟·GLB 내보내기 전체 |
| `tests.test_mock` 의 나머지(`BenchMappingTests`·`GateTests`·`RetargetMappingTests`·`QuadTailMappingTests`·`BvhUpAxisTests`·`FromSkeletonTests`·`MedialShapeTests`) | 불필요 | 28 | 이름 매핑·관문 판정(거절 사유 언어 포함)·BVH 축·순수 기하 |
| `tests.test_cli` | 불필요 | 11 | 명령줄 입력 검증, `bw plugin-path`, `bw --version`, 도움말 언어(`BW_LANG`), `bw doctor` 필수/선택, Windows Blender 경로 찾기 |
| `tests.test_examples` | 불필요 | 3 | `examples/rig_sample.py` 의 GLB 본 표 |
| `tests.test_errors` | 불필요 | 15 | 잘못된 입력이 Blender 호출 전에 막히고 메시지에 고칠 방법(→)이 있는지, 예상 못 한 오류에 로그 위치·`BW_DEBUG` 안내 |
| `tests.test_release` | 불필요 | 4 | 버전 문자열 3곳 일치, CHANGELOG 절·링크(`docs/RELEASING.md`), 패키지 메타데이터 |
| `tests.test_docs` | 불필요 | 3 | README·README.ko·GUIDE·examples/README 의 상대 링크가 있는 파일인지, 문서의 `bw <명령> --옵션` 이 실제 argparse 에 있는지 |
| `tests.test_i18n` | 불필요 | 4 | `bonewright/` 의 모든 `T(한국어, 영어)` 호출: 영어 쪽에 한글이 없고 f-문자열 자리표시자가 양쪽에 같은지(AST) |

```bash
python3 -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release tests.test_docs tests.test_i18n                    # 블렌더 있으면 전부, 없으면 12개 건너뜀
BW_SKIP_BLENDER=1 python3 -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release tests.test_docs tests.test_i18n  # 빠른 확인(블렌더 시험 건너뜀)
BW_REQUIRE_BLENDER=1 python3 -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release tests.test_docs tests.test_i18n  # 블렌더 없으면 실패(CI blender 잡)
```

새 시험이 Blender(`blender.run_script`·`pipeline.rig` 등)를 부르면 클래스에 `@requires_blender`(`tests/_marks.py`)를 붙인다.
CI(`.github/workflows/test.yml`)는 `unit`(블렌더 없음)과 `blender`(`pip install bpy==5.2.2`, 헤드리스, 렌더 끔) 두 잡으로 돈다.
