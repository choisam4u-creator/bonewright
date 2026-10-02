# 클라우드 회차 기록

## 2026-10-02

**한 일**
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main 병합(latest.md 들어옴, 충돌 없음).
- 백로그 2번: 블렌더 필요 시험 표시를 `tests/_marks.py`의 `@requires_blender`로 통일.
  `BW_SKIP_BLENDER=1`(빠른 확인), `BW_REQUIRE_BLENDER=1`(없으면 실패) 추가. `tests/README.md`에 구분 표.
- CI: bpy 헤드리스 잡은 이미 있었음. 두 잡 모두 `tests.test_cli`도 돌리고, blender 잡엔 `BW_REQUIRE_BLENDER=1`을 걸어
  bpy가 안 올라오면 건너뛰지 않고 실패하게 함.

**돌린 시험**
- `python3 -m unittest tests.test_mock tests.test_cli` — 41개 중 29개 통과, 12개 건너뜀('Blender 없음': 클라우드에 Blender·bpy 없음).
- `BW_SKIP_BLENDER=1` → 12개 건너뜀 확인, `BW_REQUIRE_BLENDER=1` → 블렌더 없어 실패하는 것 확인.
- `python3 scripts/check_license_boundary.py` — OK.
- CI blender 잡 실제 결과는 이 푸시의 Actions에서 확인 필요(클라우드에서 bpy 설치 안 함).

**Mac에서 확인할 것**
```bash
git fetch && git checkout claude/cloud-work && BW_REQUIRE_BLENDER=1 python3 -m unittest tests.test_mock tests.test_cli  # 41개 통과, 건너뜀 0
BW_SKIP_BLENDER=1 python3 -m unittest tests.test_mock tests.test_cli  # 1초 안에 29개 통과, 12개 건너뜀
```

## 2026-09-26

**한 일**
- `docs/test-reports/latest.md` 없음 → FAIL 확인 불가, 백로그로 진행.
- `docs/CLOUD-BACKLOG.md` 새로 만듦.
- README 재구성: 44.7KB 원문을 `docs/GUIDE.md`로 옮김(링크 경로만 고침). 새 `README.md`(3.4KB)는
  무엇을 해 주나/설치/첫 실행/결과 예시/라이선스 요약만. 한국어판 `README.ko.md` 추가.

**돌린 시험**
- `python3 -m unittest tests.test_mock tests.test_cli` — 41개 중 29개 통과, 12개 건너뜀('Blender 없음': 클라우드에 Blender·bpy 없음).
- `python3 scripts/check_license_boundary.py` — OK.

**Mac에서 확인할 것**
```bash
git fetch && git checkout claude/cloud-work && python3 -m unittest tests.test_mock tests.test_cli
open README.md docs/GUIDE.md   # 이미지·링크가 깨지지 않았는지 GitHub 미리보기로 확인
```
