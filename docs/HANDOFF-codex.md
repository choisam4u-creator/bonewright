# Codex 인수인계 — 실제 모델로 확인해야 할 것

작성 2026-09-15. **여기 적힌 것만 실제 Codex 토큰을 쓴다.** 나머지 작업은 전부 `BW_BACKEND=mock`(토큰 0)으로
끝내 두었다. 구독 한도가 리셋된 뒤에 아래를 순서대로 돌리면 된다.

## 왜 필요한가

지금 저장소의 모든 정확도 숫자는 **mock 백엔드**에서 나온 것이다. mock 은 분석 랜드마크에서 기계적으로 목표를
만든다. 실제 Codex 는 렌더 이미지를 보고 판단하므로 결과가 다를 수 있는데, **사족은 실제 모델로 한 번도 안 돌렸다.**
이 프로젝트의 핵심 주장("Codex 가 판단한다")이 사족에서는 검증된 적이 없다는 뜻이다.

## 1순위 — 사족 실제 1건 (필수)

```bash
export BW_HOME=<작업폴더>
bw doctor                        # codex 로그인 상태 먼저 확인
bw rig <자산>/Wolf.gltf --preset quadruped --run-id realq1
```

- 예상 비용: 입력 8만 토큰 안팎, 상한 $1.10 (사람형 real8 기준. 사족은 본이 많아 더 클 수 있다)
- 자산: `python3 scripts/fetch_bench_assets.py --out bench-assets` 로 받은 `bench-assets/quadruped/Wolf.gltf`
- **확인할 것**: `runs/realq1/targets.json` 의 `front_thigh.*` / `front_shin.*` 값이
  mock 결과(`runs/q7-Wolf/targets.json`)보다 정답에 가까운가. 앞다리가 지금 가장 큰 오차(18.2%)이고,
  어깨는 몸 안쪽이라 기하학으로는 못 잡는다 — 모델이 렌더를 보고 더 잘할 가능성이 있는 지점이다.
- 비교 방법(토큰 0): `bw bench bench-assets/quadruped/Wolf.gltf --preset quadruped` 결과와 관절별로 대조.

## 2순위 — 거절 게이트가 실제 흐름에서 도는지

```bash
bw rig bench-assets/samples/Fox.glb --preset humanoid     # 거절돼야 정상(토큰 0 로 중단)
bw rig bench-assets/samples/Fox.glb --preset humanoid --force   # 토큰을 쓴다. 필요할 때만
```

첫 줄은 토큰을 안 쓴다. **거절 메시지가 나오고 모델 호출이 0 회인지** `bw usage` 로 확인하면 된다.

## 3순위 — 사람형 회귀 1건 (여유 있으면)

```bash
bw rig tests/assets/quaternius_adventurer.glb --run-id real9
```

real8(입력 83,949 토큰 · $1.10) 과 비교해 판정이 여전히 통과인지 본다. 거절 게이트·중심선 스냅 변경이
사람형 경로를 건드리지 않았다는 건 mock 벤치로 확인했지만(17종 전 항목 동일), 실제 모델 경로는 미확인이다.

## 하지 말 것

- 벤치마크 전체(28종)를 실제 모델로 돌리지 말 것. 건당 $1 이면 $28 이고, 회귀 탐지는 mock 으로 충분하다.
- 믹사모/Adobe 자산, 에픽 자체 Fab 콘텐츠(NoAI 태그)는 쓰지 말 것. 이유는 `bench-assets/ATTRIBUTION.md`.

## 돌린 뒤 남길 것

`bw usage --days 1` 출력과 `runs/<id>/report.md` 를 `docs/` 에 요약해 남긴다. 토큰·비용은 장부에 자동 기록된다.
