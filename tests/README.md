# 시험

| 묶음 | 블렌더 | 시험 수 | 무엇을 보나 |
|---|---|---|---|
| `tests.test_mock` 의 `RigMockTests` | **필요** (`@requires_blender`) | 12 | 리그 생성·스키닝·리타겟·GLB 내보내기 전체 |
| `tests.test_mock` 의 나머지(`BenchMappingTests`·`GateTests`·`RetargetMappingTests`·`QuadTailMappingTests`·`BvhUpAxisTests`·`FromSkeletonTests`·`MedialShapeTests`) | 불필요 | 29 | 이름 매핑·관문 판정(거절 사유 언어 포함)·BVH 축·순수 기하 |
| `tests.test_cli` | 불필요 | 20 | 명령줄 입력 검증, `bw plugin-path`, `bw --version`, 도움말 언어(`BW_LANG`), `bw doctor` 필수/선택, `bw doctor --for-issue`(최근 실행·로그 꼬리·설정 파일·개인 경로 `~`), Windows Blender 경로 찾기 |
| `tests.test_examples` 의 `SampleOutputTests` | **필요** (`@requires_blender`, 일부) | 7 | `examples/sample-output/` 의 리깅·리타겟 예시가 지금 결과와 같은지(블렌더 3개), 표가 손으로 고쳐지지 않았는지·절차 BVH 매핑(블렌더 불필요 4개) |
| `tests.test_examples` 의 나머지(`ExampleTableTests`·`ExampleMessageTests`) | 불필요 | 5 | `examples/rig_sample.py` 의 GLB 본 표, 막힐 때 문구가 화면 언어를 따르는지 |
| `tests.test_errors` | 불필요 | 25 | 잘못된 입력이 Blender 호출 전에 막히고 메시지에 고칠 방법(→)이 있는지, 깨진 `runs/config.json`·모르는 설정 키, 예상 못 한 오류에 로그 위치·`BW_DEBUG` 안내, 영어 오류 문구, `report.md` 경로(심볼릭 링크 홈 포함) |
| `tests.test_release` | 불필요 | 6 | 버전 문자열 3곳 일치, CHANGELOG 절·링크(`docs/RELEASING.md`)·다음 버전 제안, 패키지 메타데이터, CI 액션이 Node 24 판인지 |
| `tests.test_docs` | 불필요 | 22 | README·README.ko·GUIDE·examples/README·CONTRIBUTING·SECURITY·RELEASING·이슈/PR 템플릿의 상대 링크가 있는 파일인지, 문서의 `bw <명령> --옵션` 이 실제 argparse 에 있는지, 시험 명령 목록(CI·CONTRIBUTING·PR 템플릿·RELEASING·이 파일)이 `tests/test_*.py` 전부인지, CONTRIBUTING 의 시험 수 예시와 이 표의 시험 수, README 첫 화면(설치·첫 실행 명령·설정 예시가 영문·한국어판에서 같고 실제 명령·`pip` 추가 묶음·설정 키와 맞는지, 본 410·변형 73 이 `examples/sample-output/` 과 같은지), 템플릿이 가리키는 GUIDE 절 제목·`GUIDE.md#앵커`·`config.yml` 링크 파일이 있는지, GUIDE Settings 표가 기본 설정과 같은지 |
| `tests.test_i18n` | 불필요 | 10 | `bonewright/` 의 모든 `T(한국어, 영어)` 호출: 영어 쪽에 한글이 없고 f-문자열 자리표시자가 양쪽에 같은지(AST), 진행 로그·본체(`bonewright/` 전체)·Blender 스크립트(`bpy_scripts/`)에 T() 밖 한국어 문자열이 없는지, 모델 프롬프트 언어 |

```bash
python3 -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release tests.test_docs tests.test_i18n                    # 블렌더 있으면 전부, 없으면 15개 건너뜀
BW_SKIP_BLENDER=1 python3 -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release tests.test_docs tests.test_i18n  # 빠른 확인(블렌더 시험 건너뜀)
BW_REQUIRE_BLENDER=1 python3 -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release tests.test_docs tests.test_i18n  # 블렌더 없으면 실패(CI blender 잡)
```

새 시험이 Blender(`blender.run_script`·`pipeline.rig` 등)를 부르면 클래스에 `@requires_blender`(`tests/_marks.py`)를 붙인다.
CI(`.github/workflows/test.yml`)는 `unit`(블렌더 없음, 리눅스 3.11·3.13), `unit-windows`(블렌더 없음), `blender`(`pip install bpy==5.2.2`, 헤드리스, 렌더 끔) 세 잡으로 돈다.
`blender` 잡은 시험 뒤 저장소 밖에서 설치본 `bw` 로 `BW_BACKEND=mock bw rig` 를 끝까지 한 번 돈다(휠에 `bpy_scripts`·`prompts` 가 실렸는지).
