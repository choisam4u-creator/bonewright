# Mac 시험 결과 (최신)

- 날짜: 2026-10-01
- 시험한 브랜치: `claude/cloud-work` (커밋 211ba63) → PR #1 squash 병합(main 9cf8c5a)
- 환경: macOS arm64, Blender 5.2.0 LTS (백그라운드 모드), Python 3.13
- 종합: **PASS**

| 명령 | 결과 |
|---|---|
| `python3 -m unittest tests.test_mock tests.test_cli` | PASS (41개 통과, 건너뜀 0, 7분 33초 — 블렌더 시험 포함) |
| `python3 scripts/check_license_boundary.py` | PASS (MIT 영역 14개 파일 bpy 미사용) |
| README.md·README.ko.md·docs/GUIDE.md 상대 링크 점검 | PASS (깨진 링크 0) |
