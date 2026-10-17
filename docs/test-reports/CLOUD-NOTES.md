# 클라우드 회차 기록

**Mac 에서 돌릴 것 (블렌더 필요, 10/17 23회차 기준)**
```bash
git fetch && git checkout claude/cloud-work && git pull && BW_REQUIRE_BLENDER=1 python3 -m unittest      # 303개, 건너뜀 0
python3 examples/rig_sample.py --preset quadruped && bw rig examples/out/capsule_dog.glb --preset quadruped --run-id dog --no-judge   # next: 끝에 "front legs move like arms"
bw motion --bvh examples/wave.bvh --rig dog; bw motion --bvh examples/wave.bvh --rig dog --preset humanoid   # ⚠ upright·사람 리그 명령 / BLOCKED + --preset 뺀 명령
```

## 2026-10-17 (23회차)

**한 일** (커밋마다 `claude/cloud-work` 에 푸시, PR #10 에 얹힘)
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main(145fe4b)은 이미 들어 있어 병합 없음.
- 남은 [ ] 가 0개라 bpy 5.2.2 venv(편집 설치)로 저장소 밖 임시 폴더에서 개 리그(capsule_dog)·사람 리그(adventurer) + wave.bvh 를 쳐 보고 **새 항목 3개** 추가, 3개 모두 처리(22회차 "다음 후보" 의 사족 쪽):
  - **리그와 다른 `--preset`**: 개 리그에 `bw motion … --preset humanoid` → 말없이 팔다리 6개가 안 움직이고, ⚠ 는 "이름을 못 알아본 BVH 본: LeftArm…" + 리그에 없는 `upper_arm_fk.L` 로 `--map` 을 쓰라 했다(틀린 진단). → Blender 전에 `BLOCKED:` + `--preset` 을 뺀 같은 명령.
  - **사람 BVH 를 네 발 리그에**(개 리그 `next:` 가 권한 그대로): 앞다리가 손을 흔드는데(39.12°·32.36cm) 말없이 "done" → BVH 쉬는 자세가 서 있는 몸이면 ⚠ 두 줄 + 최근 사람 리그로 바꾼 같은 명령(없으면 첫 리깅)·report 한 줄. 안내 명령 `--rig hero` 는 18본·4.86°·10.33cm. 이 일로 `bvh_rest_joints` 가 부모 OFFSET 을 더하지 않던 잠복 버그(머리 y 0.1, 실제 0.55)도 고침 — 위 축 자동 판단은 국소 OFFSET 방향 덕에 우연히 맞아 왔다.
  - **네 발 리그의 `next:`**(`bw rig`·`bw status <id>`·`bw export`·`bw demo`): 사람 손 흔들기 샘플에 "앞다리가 팔처럼 움직인다, 네 발 BVH 가 있으면 그 경로로" 한 마디.
- CHANGELOG Fixed 3줄, GUIDE 두 줄(리타겟 절), tests/README·CONTRIBUTING 시험 수. 사용자 체감: 안내 명령을 그대로 쳤는데 결과가 말없이 이상하던 두 길이 이제 말하고 다음 명령을 준다. 설치~첫 결과 단계 수는 그대로.

**돌린 시험**
- `python3 -m unittest`(3.11, 블렌더 없음): 303개 중 16개 건너뜀, 나머지 통과(커밋마다).
- bpy 5.2.2 venv(Python 3.13) `BW_REQUIRE_BLENDER=1 BW_NO_RENDER=1 python -m unittest`: **303개 모두 통과, 건너뜀 0**(136초). 라이선스 경계 검사 OK.
- 새 시험 8개(`RigPresetMismatchTests` 2·`UprightOnQuadTests` 3·`BvhRestPoseTests` 2·`QuadNextNoteTests` 1)는 고치기 전 코드에서 실패 확인(`test_same_or_unknown_preset_goes_on` 은 회귀 방지라 옛 코드에서도 통과). 세 고침 모두 bpy 설치본 `bw` 로 실제 문구·숫자 확인.
- 못 돌린 것: 실제 렌더(화면 없는 리눅스). 진짜 네 발 모캡 BVH(Quaternius 늑대)로 `bvh_upright` 가 False 인지는 합성 개 BVH 로만 봤다 — Mac 의 bench-assets 늑대 클립으로 한 번 보면 좋다(⚠ 가 안 나와야 한다).
- CI: PR #10 헤드(aee360c)에서도 잡 전부 1~3초 만에 단계 없이 끝남(run 38994361934·38994357915: unit 3.13·windows·blender failure, 3.11 cancelled). blender 잡이 pending 으로 머물다 이렇게 끝나는 이유: 러너가 안 붙음(비공개 저장소의 Actions 사용량·결제 한도로 추정, Settings → Billing) — 코드와 무관.

**완료 수·추가 수**: 완료 3 · 추가 3 (완료 ≥ 추가) · 남은 [ ] 0.

**막힌 것 / 다음**
- 다음 후보: `--map` 에 쓸 리그 컨트롤 목록을 Blender 전에 보는 길(rig_stats.json 에 컨트롤 이름), 네 발 샘플 BVH(절차 생성 걷기)를 저장소에 실어 개 리그 `next:` 가 그대로 도는 동작을 권하기, UE 이름(`spine_01`~`05`)의 척추 가운데.
- 지시문의 "4회차부터·3회차(커밋 24)" 는 옛 문구로 보여 기록대로 23회차로 적었다. 이 세션의 지정 브랜치(`claude/cloud-work-ph50b3`)가 아니라 지시문대로 `claude/cloud-work` 에 푸시했다(지난 회차들과 같음).

## 2026-10-16 (22회차)

**한 일** (커밋마다 `claude/cloud-work` 에 푸시, PR #10 에 얹힘)
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main(145fe4b)은 이미 들어 있어 병합 없음.
- 남은 [ ] 가 0개라 bpy 5.2.2 venv(편집 설치)로 저장소 밖 임시 폴더에서 rig(사람·개) → motion 을 **이름 규약만 바꾼 wave.bvh**(Mixamo·UE·SMPL·Biovision·모르는 이름)와 개 리그로 쳐 보고 **새 항목 3개** 추가, 3개 모두 처리:
  - **관절 이름 BVH(SMPL·자세 추정 도구: `L_Hip`/`L_Knee`/`L_Shoulder`/`L_Elbow`)**: 팔다리 9개가 말없이 안 움직이고 "done"(본 10개, 손발 오차 30.88cm). `Hip` 이 골반, `Shoulder` 가 쇄골로 읽혔다 → 무릎·팔꿈치가 있는 쪽은 Hip=허벅지·Shoulder=위팔(사족은 앞다리). 18본·10.33cm(Mixamo 이름 파일과 같음). GUIDE 관절 표에 열.
  - **Biovision 원래 이름(`LeftUpArm`/`LeftLowArm`/`LeftLowLeg`)**: 두 팔·정강이 6개가 안 움직임(31.4cm) → Mixamo 이름처럼(10.33cm). 벤치 정답 이름표(`JOINT_MAP`)는 손대지 않음.
  - **모르는 이름의 팔다리 본**: "BVH 본 3개 못 옮김" 숫자뿐 → retarget 줄에 못 옮긴 본 이름, ⚠ 로 움직이지 않는 컨트롤·그쪽의 못 알아본 본·그대로 칠 `… --map bones.json` 과 파일 꼴. 안내대로 하면 20.86 → 10.33cm. 개 리그의 "None°·Nonecm" → "재지 않음". 21회차 "다음 후보".
- CHANGELOG Fixed 3줄, GUIDE 두 문장·표 열, tests/README·CONTRIBUTING 시험 수. 사용자 체감: 흔한 BVH 두 규약이 **말없이 망가지던** 것이 그대로 돌고, 그 밖의 규약은 다음 할 일을 말한다. 설치~첫 결과 단계 수는 그대로.

**돌린 시험**
- `python3 -m unittest`(3.11, 블렌더 없음): 295개 중 16개 건너뜀, 나머지 통과(커밋마다).
- bpy 5.2.2 venv(Python 3.13) `BW_REQUIRE_BLENDER=1 BW_NO_RENDER=1 python -m unittest`: **295개 모두 통과, 건너뜀 0**(147초). 라이선스 경계 검사 OK.
- 새·바뀐 시험은 고치기 전 코드로 되돌려 모두 실패 확인. 세 고침 모두 bpy 설치본 `bw motion` 으로 고치기 전·후 숫자를 실제로 잼(위 숫자).
- 못 돌린 것: 실제 렌더(화면 없는 리눅스). 진짜 SMPL·Biovision 모캡 파일이 아니라 wave.bvh 의 이름만 바꾼 파일로 쟀다 — 실제 파일의 축·단위 차이는 Mac 에서 한 번 보면 좋다.
- CI: PR #10 헤드에서 21회차와 같이 잡 전부 1~3초 만에 단계 없이 끝남(blender 잡도 pending 으로 머물다 같은 식) — 러너가 안 붙는 것(비공개 저장소의 Actions 사용량·결제 한도로 추정, 샘님이 Settings → Billing 에서 확인). 코드와 무관.

**완료 수·추가 수**: 완료 3 · 추가 3 (완료 ≥ 추가) · 남은 [ ] 0.

**막힌 것 / 다음**
- 다음 후보: 사람 BVH(wave.bvh)를 사족 리그에 줄 때 — 개 리그의 `bw rig` `next:` 가 사람 손 흔들기를 권한다(앞다리가 팔처럼 움직임, 사족 샘플 BVH 가 저장소에 없다), UE 이름(`spine_01`·`ball_l`)의 척추 가운데·발볼, `--map` 에 쓸 리그 컨트롤 목록을 Blender 전에 보는 길.
- 지시문의 "4회차부터·3회차(커밋 24)" 는 옛 문구로 보여 기록대로 22회차로 적었다. 이 세션의 지정 브랜치(`claude/cloud-work-lctk51`)가 아니라 지시문대로 `claude/cloud-work` 에 푸시했다(지난 회차들과 같음).

## 2026-10-16 (21회차)

**한 일** (커밋마다 `claude/cloud-work` 에 푸시, PR #10 에 얹힘)
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main(145fe4b)은 이미 들어 있어 병합 없음.
- 남은 [ ] 가 0개라 bpy 5.2.2 venv(편집 설치)로 저장소 밖 임시 폴더에서 rig → motion(`--map` 여러 꼴) → bench 를 쳐 보고 **새 항목 5개** 추가, 5개 모두 처리:
  - **`--map` 예가 왼팔을 멈춤**(이번 회차의 큰 것): 안내·도움말의 예 `{"LeftArm": "upper_arm.L"}` 를 그대로 쓰면 컨트롤이 `upper_arm_fk.L` 이라 Blender 쪽에서 말없이 빠지고, 자동으로 붙던 LeftArm 까지 잃었다(왼손 오차 8.5 → 33.6cm, 로그는 "applied 1"). 예를 컨트롤 이름으로, 리그에 없는 본은 가까운 컨트롤과 함께 ⚠ 로그·report, GUIDE 한 문장.
  - **리그가 하나도 없을 때 `bw motion` 의 `next:`**: "`bw status` 의 리그 id + `--rig <id>`" → 첫 리깅 `--run-id first-rig` 다음 같은 명령 `--rig first-rig`. 두 명령을 `&&` 로 이어 retargeted.blend 까지 확인. 20회차 "다음 후보".
  - **`bw bench <빈 폴더>`**: 받기 명령만 → 없는 경로 안내와 같은 다음 명령(메시가 든 받아 둔 폴더, 없으면 `… && bw bench bench-assets/samples`).
  - **JSON 이 아닌 `--map`**(작은따옴표·끝 쉼표): 그대로 쓸 JSON 한 줄, 아니면 틀린 줄. BOM 파일(메모장)도 읽음. 20회차 "다음 후보".
  - **모양이 틀린 `--map`**: 틀린 항목(`"LeftArm": 3`)이나 최상위 형(list)을 댐.
- CHANGELOG Fixed 4줄, tests/README·CONTRIBUTING 시험 수. 사용자 체감: 셋은 "막힌 자리에서 그대로 칠 다음 명령", 하나(`--map` 예)는 문서·안내를 따랐는데 결과가 조용히 나빠지던 것. 설치~첫 결과 단계 수는 그대로.

**돌린 시험**
- `python3 -m unittest`(3.11, 블렌더 없음): 291개 중 16개 건너뜀, 나머지 통과(커밋마다).
- bpy 5.2.2 venv(Python 3.13) `BW_REQUIRE_BLENDER=1 BW_NO_RENDER=1 python -m unittest`: **291개 모두 통과, 건너뜀 0**(132초). 처음엔 BW_HOME 을 없는 폴더로 줘서 `ClosedPipeTests` 1개가 "BW_HOME does not exist" 경고로 실패 — 폴더를 만들고 다시 돌려 통과(환경 탓, 코드 무관). 라이선스 경계 검사 OK.
- 새·바뀐 시험은 고치기 전 코드로 되돌려 모두 실패 확인. `--map` ⚠ 문구·고친 매핑(18본, 왼손 오차 원래대로)·`bench` 빈 폴더·`--map` 오류 문구는 bpy 설치본 `bw` 로 실제로 찍어 봄.
- 못 돌린 것: 실제 렌더(화면 없는 리눅스). `retarget_bvh.py` 의 `_near`(가까운 컨트롤)는 사람 프리셋에서만 실측 — 사족·모양 리그 이름은 difflib 쪽이라 Mac 에서 한 번 보면 좋다.
- CI: PR #10 헤드(96dc055)에서도 **잡 전부 1~3초 만에 단계 없이 끝남**(run 38839408572·38839404453, unit 3.11·windows·blender failure, 3.13 cancelled) — 17~20회차와 같고 코드와 무관, 러너가 안 붙는 것(비공개 저장소의 Actions 사용량·결제 한도로 추정, 샘님이 Settings → Billing 에서 확인). blender 잡이 pending 으로 머무는 이유도 같다.

**완료 수·추가 수**: 완료 5 · 추가 5 (완료 ≥ 추가) · 남은 [ ] 0.

**막힌 것 / 다음**
- 같은 시각에 다른 클라우드 세션(session_01WREwVC…)이 `claude/cloud-work` 에 시험 수 문서 맞춤 커밋(eafae7d)을 올려 푸시가 한 번 거절됨 → 내 미푸시 커밋을 그 위로 rebase 해 해결. 회차가 겹쳐 돌면 시험 수 문서가 서로 엇갈릴 수 있다 — 스케줄이 둘 걸려 있는지 샘님 확인.
- 다음 후보: `--map` 의 리그 쪽 이름을 미리(Blender 전에) 볼 길(리그의 컨트롤 목록을 rig_stats.json 에 남기기), `bw motion` 이 사족 리그에 사람 BVH 를 줄 때의 안내, `--map` 에 쓸 BVH 본 이름을 보여 주는 길(`import:` 줄에 못 옮긴 본 이름).
- 지시문의 "4회차부터·3회차(커밋 24)" 는 옛 문구로 보여 기록대로 21회차로 적었다.

## 2026-10-15 (20회차)

**한 일** (커밋마다 `claude/cloud-work` 와 이 세션 브랜치 `claude/cloud-work-cpva99` 에 푸시, PR #10 에 얹힘)
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main(145fe4b)은 이미 들어 있어 병합 없음.
- 남은 [ ] 가 0개라 bpy 5.2.2 venv(편집 설치)로 저장소 밖 임시 폴더에서 rig → demo(BW_NO_RENDER) → motion → status 와 틀린 입력을 쳐 보고 **새 항목 4개** 추가, 4개 모두 처리:
  - **`BW_NO_RENDER=1 bw demo r1`**: "BW_NO_RENDER 를 지우고 다시" → 그 값만 뺀 같은 명령(`env -u BW_NO_RENDER bw demo r1`, Windows `Remove-Item Env:BW_NO_RENDER; …`) + 화면 없이 되는 `bw export r1`. 19회차 "다음 후보".
  - **리그가 없을 때 `bw motion`(출처 없음)**: `--rig <rig run-id>` 자리표시 → `--rig` 없이 도는 샘플 명령 + 첫 리깅 명령. 그 샘플 명령이 빈 BW_HOME 에서 끝까지 돎.
  - **`--rig` 없는 `--export`·`--map`·`--legs`·`--no-roll`**: 리그가 있어도 자리표시 → 지금 명령 + `--rig <최근 리그>`(없으면 첫 리깅 명령). 안내 명령이 animated.glb 까지 돎.
  - **`bw status <오타 id>`**: "목록을 보라" → 가까운 실행(없으면 최근 실행)을 `bw status <id>` 로.
- CHANGELOG Fixed 4줄, tests/README·CONTRIBUTING 시험 수. 사용자 체감: 넷 모두 "막힌 자리에서 그대로 칠 다음 명령". 설치~첫 결과 단계 수는 그대로.

**돌린 시험**
- `python3 -m unittest`(3.11, 블렌더 없음): 285개 중 16개 건너뜀, 나머지 통과(커밋마다).
- bpy 5.2.2 venv(Python 3.13) `BW_REQUIRE_BLENDER=1 BW_NO_RENDER=1 python -m unittest`: **285개 모두 통과, 건너뜀 0**(196초). 라이선스 경계 검사 OK.
- 새·바뀐 시험은 고치기 전 코드로 되돌려 모두 실패 확인. 네 안내 문구는 bpy 설치본 `bw` 로 실제로 찍어 봄.
- 못 돌린 것: `env -u BW_NO_RENDER bw demo r1` 의 실제 렌더(화면 없는 리눅스) → Mac 둘째 줄. Windows `Remove-Item` 꼴은 문자열 시험만.
- CI: blender 잡은 pending/queued 로 보이다가 **잡 4개 모두 2~3초 만에 단계 없이 끝남**(run 38749718252 등) — 17~19회차와 같고 코드와 무관, 러너가 안 붙는 것(비공개 저장소의 Actions 사용량·결제 한도로 추정, 샘님이 Settings → Billing 에서 확인).

**완료 수·추가 수**: 완료 4 · 추가 4 (완료 ≥ 추가) · 남은 [ ] 0.

**막힌 것 / 다음**
- 남은 [ ] 가 0 — 다음 회차는 다시 실측으로 새 항목부터. 후보: 리그 없이 돌린 `bw motion` 의 `next:` 가 리그가 하나도 없을 때도 `--rig <id>` 자리표시(첫 리깅 명령으로), `bw bench <빈 폴더>` 의 자산 받기 안내 뒤에 `&& bw bench bench-assets/samples` 가 없다, `--map` 이 JSON 아닐 때 "e.g." 뿐.
- 지시문의 "4회차부터·3회차(커밋 24)" 는 옛 문구로 보여 기록대로 20회차로 적었다.

## 2026-10-15 (19회차)

**한 일** (커밋마다 `claude/cloud-work` 와 이 세션 브랜치 `claude/cloud-work-lfnlci` 에 푸시, PR #10 에 얹힘)
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main(145fe4b)은 이미 들어 있어 병합 없음.
- 남은 [ ] 가 0개라 bpy 5.2.2 venv 에 `pip install -e .` 로 저장소 밖 임시 폴더에서 rig → export → demo → motion → status → 예제를 쳐 보고 **새 항목 5개** 추가, 5개 모두 처리:
  - **`bw export`·`bw demo` 끝**: stdout 이 GLB·영상 경로인데 `report:` → `GLB:`·`video:`(ffmpeg 없으면 `frames:`), 끝에 run-id 를 채운 `next:`(영상·GLB·동작 입힌 GLB, 이미 있으면 경로). 18회차 "다음 후보".
  - **리그 자리에 동작 실행 id**(`bw export motion-…`·`--rig motion-…`): "리깅을 마치지 못했다 → 그 id 로 리깅"(따르면 동작 실행을 덮어씀) → "`bw motion` 실행이다" + 최근 리그로 바꾼 같은 명령.
  - **`bw status` 목록**: 줄마다 `rig ·`/`motion ·`/`bench ·`.
  - **`bw status <id>`**: 목록 한 줄과 같던 출력에 report·만든 파일·아직 안 친 다음 명령.
  - **`examples/rig_sample.py --preset quadruped --motion`**: 설명뿐 → `--motion` 뺀 꼴·(사람 메시면) `--preset` 뺀 꼴. 두 안내 명령 모두 bpy 로 끝까지 돎.
- CHANGELOG Changed 3줄·Fixed 2줄, GUIDE `bw status` 두 곳, tests/README·CONTRIBUTING 시험 수.
- 사용자 체감: 다섯 모두 "결과·막힌 자리에서 그대로 칠 다음 명령". 설치~첫 결과 단계 수는 그대로(README 첫 실행 4줄이 이제 각 줄 끝에서 다음 줄을 알려 준다).

**돌린 시험**
- `python3 -m unittest`(3.11, 블렌더 없음): 282개 중 16개 건너뜀, 나머지 통과(커밋마다).
- bpy 5.2.2 venv(Python 3.13) `BW_REQUIRE_BLENDER=1 BW_NO_RENDER=1 python -m unittest`: **282개 모두 통과, 건너뜀 0**(141초).
- 새 시험 5개는 옛 `bonewright/`·예제로 되돌려 모두 실패 확인. 라이선스 경계 검사는 `bonewright/` 에 bpy import 를 더하지 않아 그대로.
- 못 돌린 것: 렌더(`bw demo` 실제 영상) — 화면 없는 리눅스라 BW_NO_RENDER=1 → Mac 둘째 줄.
- CI: blender 잡은 pending 이 아니라 **잡 4개 모두 2~3초 만에 단계 없이 끝남**(run 38670081109 등, 잡 로그 404 = 러너가 안 붙음). 17·18회차와 같고 코드와 무관 — 비공개 저장소의 Actions 사용량·결제 한도로 추정, 샘님이 Settings → Billing 에서 확인.

**완료 수·추가 수**: 완료 5 · 추가 5 (완료 ≥ 추가) · 남은 [ ] 0.

**막힌 것 / 다음**
- 남은 [ ] 가 0 — 다음 회차는 다시 실측으로 새 항목부터. 후보: `bw demo` 를 BW_NO_RENDER=1 에서 막을 때 그대로 칠 명령(`env -u BW_NO_RENDER bw demo <id>`·Windows), 예제가 저장소 밖에서 돌려도 결과를 저장소의 `examples/out/` 에 쓰는 것(돌린 폴더가 아님).
- 지시문의 "4회차부터·3회차(커밋 24)" 는 옛 문구로 보여 기록대로 19회차로 적었다.

## 2026-10-14 (18회차)

**한 일** (커밋마다 `claude/cloud-work` 와 이 세션 브랜치 `claude/cloud-work-d8vbuo` 에 푸시, PR #10 에 얹힘)
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main(145fe4b)은 이미 들어 있어 병합 없음.
- 남은 [ ] 가 0개라 bpy 5.2.2 venv 와 `pip install .` 설치본으로 저장소 밖 임시 폴더에서 README 첫 실행·rig·export·motion·demo·예제를 쳐 보고 **새 항목 5개** 추가, 5개 모두 처리:
  - **codex 없는 `bw rig hero.glb`**: "뼈대가 있으면 이것, 없으면 저것" → 분석이 찾은 대로 고른 같은 명령 한 줄(`--from-skeleton --no-judge` 또는 `--from-shape --no-judge`).
  - **Rigify 생성 실패**(사람 뼈대에 `--preset quadruped`): 트레이스백 40줄 + "이슈를 열어라" → `BLOCKED:` + Rigify 가 말한 본 + 원본 관절을 더 많이 알아보는 프리셋으로 바꾼 같은 명령(humanoid 61개 · quadruped 26개). 그 명령이 done (ok) 까지 가는 것 확인.
  - **같은 `--run-id` 로 끝난 리그를 다시 리깅**: 말없이 덮어쓰고 옛 `rigged.glb` 가 새 리그 옆에 남음 → 바꾼다는 한 줄, 옛 GLB·데모 영상 지움, `bw export <id>` 안내. 도움말의 "같은 id 면 덮어쓴다" 는 그대로(예제·bench 가 쓴다), GUIDE 한 문장.
  - **`[1/6] import:` 진행 줄**: 파이썬 dict·4×4 행렬 → `5 meshes · left out Icosphere · has its own skeleton · turned 180° so the front faces -Y`.
  - **`examples/rig_sample.py` 를 저장소 밖에서**: 끝 줄 `table: examples/out/…`(열리지 않음) → 돌린 폴더에서 열리는 경로(밖이면 절대). 벤치 자산 스크립트 안내도.
- CHANGELOG Fixed 다섯 줄. 사용자 체감: 다섯 모두 "막힌 자리에서 그대로 칠 다음 명령" 또는 "출력이 사람 말·열리는 경로". 설치~첫 결과 단계 수는 그대로.

**돌린 시험**
- `python3 -m unittest`(3.11, 블렌더 없음): 277개 중 16개 건너뜀, 나머지 통과(커밋마다 통과를 보고 커밋). 새 시험 7개는 고치기 전 코드에서 실패 확인.
- bpy 5.2.2 venv(Python 3.13) `BW_REQUIRE_BLENDER=1 BW_NO_RENDER=1 python -m unittest`: **277개 모두 통과, 건너뜀 0**(154초). 다섯 고침 모두 bpy 로 실제 명령을 쳐 문구 확인. 라이선스 경계 검사 OK.
- 렌더는 화면 없는 리눅스라 끔(BW_NO_RENDER=1) → Mac 첫 줄.
- CI: blender 잡은 pending 이 아니라 **잡 4개 전부 2~3초 만에 단계 없이 실패**(run 38580412076, 헤드 204a956) — 17회차와 같다. 러너가 안 붙는다: 코드 무관(비공개 저장소 Actions 사용량·결제 한도 추정 → 샘님 Settings → Billing 확인).

**완료 수·추가 수**: 완료 5 · 추가 5 (완료 ≥ 추가) · 남은 [ ] 0.

**막힌 것 / 다음**
- 남은 [ ] 가 0 — 다음 회차는 공개 준비 기준으로 새 항목 5개부터. 후보: `bw export`·`bw demo` 의 stdout 이 GLB·영상 경로인데 이름표가 `report:`, `bw export` 끝에 `next:`(GLB 를 어디에 쓰나) 없음.
- 지시문의 "4회차부터·3회차(커밋 24)" 는 옛 문구로 보여 기록대로 18회차로 적었다. 지시 브랜치 `claude/cloud-work` 와 세션 기본 브랜치 둘 다에 같은 커밋을 푸시.

## 2026-10-14 (17회차)

**한 일** (커밋마다 `claude/cloud-work` 와 이 세션 브랜치 `claude/cloud-work-uh4n8k` 에 푸시, PR #10 에 얹힘)
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main(145fe4b)은 이미 들어 있어 병합 없음. 같은 브랜치에 동시 세션 없음.
- 남은 [ ] 가 0개라 `pip install .` 설치본(3.11)으로 저장소 밖 임시 폴더에서 명령을 쳐 보고 **새 항목 5개** 추가, 5개 모두 처리:
  - **`python3 -m bonewright`**: "No module named bonewright.__main__" → `bw` 와 같은 CLI. `bw` 가 PATH 에 없을 때의 대안으로 README 두 언어 설치 절에 한 줄.
  - **`--preset dog`·`animal`·`human`·`Quadruped`**: 설명만 → 값만 바꾼 같은 명령(rig·motion·bench, `--preset=X` 꼴도). 모르는 말은 지금 설명.
  - **메시 자리의 `.zip`**: "다시 내보내라" → 안의 메시 이름 + `python3 -m zipfile -e hero.zip hero`(Windows `py`) + 푼 경로로 같은 명령. bpy 로 안내를 그대로 따라가 리깅 `done (ok)` 확인.
  - **README 자리 이름 `character.glb`·`x.glb`**: "check the path" → "README 의 예시 이름" + 저장소 캐릭터 첫 명령(비슷한 파일이 있으면 그 안내만).
  - **값 하나 자리에 낱말 여럿**(`bw rig my hero.glb` 아직 없는 파일·`--text a person walks`·`bw export r1 r2`): 최상위 사용법뿐 → 따옴표 친 같은 명령, run-id 자리는 첫 값만 둔 같은 명령. doctor·usage 처럼 자리 인자가 없는 명령엔 지어내지 않음.
- CHANGELOG Fixed 다섯 줄.
- 사용자 체감: 다섯 모두 "안내를 그대로 치면 도는가". 설치~첫 결과 단계 수는 그대로(`bw` 를 못 찾는 경우 막힘 → 한 줄 대안).

**돌린 시험**
- `python3 -m unittest`(3.11, 블렌더 없음): 270개 중 16개 건너뜀, 나머지 통과(커밋마다 통과를 보고 커밋).
- bpy 5.2.2 venv(Python 3.13) `BW_REQUIRE_BLENDER=1 BW_NO_RENDER=1 python -m unittest`: **270개 모두 통과, 건너뜀 0**(212초). 회차 시작 때 265개도 같은 조건으로 모두 통과.
- 새 시험 5개는 모두 고치기 전 코드에서 실패 확인. 렌더는 화면 없는 리눅스라 끔 → Mac 첫 줄.
- CI: blender 잡은 pending 이 아니라 **잡 4개 전부 1~3초(Windows 29초) 만에 단계·로그 없이 실패**(run 38500179100, 헤드 2d90f4f, 로그 404) — 10/13 14:2x 에 잠깐 돌았다가 다시 러너가 안 붙는다. 코드 무관(비공개 저장소 Actions 사용량·결제 한도 추정 → 샘님 Settings → Billing 확인).

**완료 수·추가 수**: 완료 5 · 추가 5 (완료 ≥ 추가) · 남은 [ ] 0.

**막힌 것 / 다음**
- 남은 [ ] 가 0 — 다음 회차는 공개 준비 기준으로 새 항목 5개부터.
- 작업 지시는 `claude/cloud-work`, 이 세션의 기본 브랜치는 `claude/cloud-work-uh4n8k` — PR #10 이 `claude/cloud-work` 라 지시대로 둘 다에 같은 커밋을 푸시. 지시문의 "4회차부터·3회차(커밋 24)" 는 옛 문구로 보여 기록대로 17회차로 적었다.

## 2026-10-13 (16회차)

**한 일** (커밋마다 `claude/cloud-work` 에 푸시, PR #10 에 얹힘)
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main(145fe4b)은 이미 들어 있어 병합 없음.
- 남은 [ ] 가 1개(CI — 샘님)라 저장소 밖 임시 폴더에서 명령을 쳐 보고 **새 항목 5개** 추가, 5개 모두 처리:
  - **`bw help`·`bw help rig`**: 오류 + "help is: `bw --help` · all commands: `bw --help`"(같은 말 두 번) → 도움말을 그대로(종료 0).
  - **내용이 .glb 인 다른 확장자(.vrm·확장자 없음)**: "다시 내보내라" → `cp hero.vrm hero.glb`, then `bw rig hero.glb …`(같은 옵션). bpy 로 복사본이 실제로 리깅되는 것 확인(진짜 VRM 파일로는 못 해 봄).
  - **값 없는 `--bvh`·`--rig`**: 저장소 밖에선 없는 `examples/wave.bvh`, `<rig run-id>` → 샘플 절대 경로·최근 리그.
  - **kimodo.cpp 없음**: "`--bvh file`" → `bw motion --bvh <샘플> --rig <준/최근 리그>`.
  - **리그가 하나도 없을 때 틀린 run-id**: `bw rig <mesh> --run-id X` → 저장소 캐릭터 첫 명령 + `--run-id X`(앞), 내 메시 꼴(뒤).
- CHANGELOG Fixed 세 항목.
- 사용자 체감: 다섯 모두 자리표시·되돌림 없이 "안내를 그대로 치면 도는가". 설치~첫 결과 단계 수는 그대로.
- 동시 세션: 회차 중에 다른 세션이 `claude/cloud-work` 에 d0a2ef9(Windows 시험 고침)를 푸시 → 병합(2e5a164), 내 새 시험 둘도 같은 `split_pasted` 로(688da85).
- 실수 하나: `bw help` 커밋이 `| tail` 로 시험 수 표 실패를 못 보고 커밋됨 → 바로 다음 커밋에서 고침. 그 뒤로는 시험이 통과할 때만 커밋하는 스크립트로.

**돌린 시험**
- `python3 -m unittest`(3.11, 블렌더 없음): 265개 중 16개 건너뜀, 나머지 통과. `scripts/check_license_boundary.py` OK.
- bpy 5.2.2 venv(Python 3.13) `BW_REQUIRE_BLENDER=1 BW_NO_RENDER=1 python -m unittest`: **265개 모두 통과, 건너뜀 0**(156초, 병합 전 헤드).
- 새 시험 6개는 모두 고치기 전 코드에서 실패 확인. 렌더는 화면 없는 리눅스라 끔 → Mac 명령 위.
- CI: **러너 복구** — blender 잡이 pending/러너 없음이 아니라 실제로 돌아 통과(run 38413301579, 헤드 86806f7). unit-windows 는 기존 시험 13개(대소문자 안 가리는 파일 시스템·역슬래시)로 실패 → d0a2ef9 가 고침, 새 시험은 Windows 에서도 통과. 최종 헤드 결과는 PR #10 참고.

**완료 수·추가 수**: 완료 6(새 5 + CI 러너 항목 — 복구 확인) · 추가 5 (완료 ≥ 추가) · 남은 [ ] 0.

**막힌 것 / 다음**
- 남은 [ ] 가 0 — 다음 회차는 공개 준비 기준으로 새 항목 5개부터.
- 작업 지시는 `claude/cloud-work`, 이 세션의 기본 브랜치는 `claude/cloud-work-zqeu89` — PR #10 이 `claude/cloud-work` 라 지시대로 그쪽에 푸시. 지시문의 "4회차부터·3회차(커밋 24)" 는 옛 문구로 보여 기록대로 16회차로 적었다.
- 같은 브랜치에 세션이 둘 이상 돌 수 있다(이번에 겹침) — 푸시 전 fetch 로 확인 중.

## 2026-10-13 (15회차)

**한 일** (커밋마다 `claude/cloud-work` 에 푸시, PR #10 에 얹힘)
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main(145fe4b)은 이미 들어 있어 병합 없음. 같은 브랜치에 동시 세션 없음.
- 남은 [ ] 가 1개(CI — 샘님)라 bpy 5.2.2(Python 3.13) 설치본으로 저장소 밖 임시 폴더에서 설치~첫 결과~모션을 그대로 쳐 보고 **새 항목 5개** 추가, 5개 모두 처리:
  - **화면 없는 리눅스**: README 첫 명령이 리깅을 다 마친 뒤 렌더에서 libEGL 로 죽고(종료 -6) "이슈를 열어라" 였다 → `BLOCKED:` + 리그는 이미 저장됨 + `BW_NO_RENDER=1 <같은 명령>` + `libegl1`. `bw demo` 는 끌 수 없다고. rig·motion·demo 셋 다 실제로 확인. GUIDE 한 문단.
  - **`bw motion` 의 `next:` 줄**: 열어 볼 `.blend`, GLB 경로 또는 같은 명령 + `--export`, 리그 없이 돌렸으면 최근 리그로 `--rig`.
  - **다른 명령의 옵션**: `bw status --days 7` → "`bw usage --days 7`", `bw rig … --out a.glb` → "`bw export <최근 리그> --out a.glb`", `--nojudge` → "`--no-judge`?".
  - **동의어 명령**: `bw retarget`·`why`·`version`·`check` 등 46개 낱말 → 진짜 명령을 그대로 칠 꼴(샘플 BVH·최근 리그 id 채움).
  - **`bw bench` 머리 확인**: 이름만 .fbx·.glb·.gltf 인 파일(메시·`--gt-mesh`)을 Blender 전에(14회차 "다음 후보").
- 사용자 체감: 설치~첫 결과 단계 수는 그대로(화면 없는 리눅스에선 실패 → 안내 한 줄로 성공). 다섯 모두 "오류가 다음 할 일을 그대로 칠 꼴로 말하는가".
- 실수 하나: 옵션 안내 커밋(4fbf494)이 `| tail` 때문에 실패한 시험(T() 첫 인자 문자열 덧셈) 위에 커밋됐다 → 바로 다음 커밋(a5b2c17)에서 고침.

**돌린 시험**
- `python3 -m unittest`(3.11, 블렌더 없음): 259개 중 16개 건너뜀, 나머지 통과(커밋마다). `scripts/check_license_boundary.py` OK.
- bpy 5.2.2 venv(Python 3.13) `BW_REQUIRE_BLENDER=1 BW_NO_RENDER=1 python -m unittest`: **259개 모두 통과, 건너뜀 0**(164초).
- 새 시험 10개(5개 시험 묶음)는 모두 고치기 전 코드에서 실패 확인. 렌더 성공 경로는 화면 없는 리눅스라 못 돌림 → Mac 명령 위(실패 경로는 이번에 실제로 돌림).
- CI: blender 잡은 pending 이 아니라 잡 4개 전부 러너 없이 2초 만에 실패(run 38336465122, 헤드 8a8e5a6, 단계 0개) — 10/11 02:49 이후 그대로, 코드 무관(비공개 저장소 Actions 사용량 추정, 백로그 [ ] — 샘님 Settings → Billing).

**완료 수·추가 수**: 완료 5 · 추가 5 (완료 ≥ 추가) · 남은 [ ] 1(CI 러너 — 샘님).

**막힌 것 / 다음**
- 작업 지시는 `claude/cloud-work`, 이 세션의 기본 브랜치는 `claude/cloud-work-v8edcw` — PR #10 이 `claude/cloud-work` 라 지시대로 그쪽에 푸시.
- 지시문의 "3회차(커밋 24)" 는 옛 문구로 보인다(실제로는 14회차 다음) — 회차 번호는 기록을 따라 15회차로 적었다.
- `latest_rig` 는 렌더에서 실패한 실행도 02_rigged.blend 가 있으면 "최근 리그" 로 고른다(리그 자체는 멀쩡해서 그대로 둠) — 샘님 판단 필요시 백로그로.

## 2026-10-12 (14회차)

**한 일** (커밋마다 `claude/cloud-work` 에 푸시, PR #10 에 얹힘)
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main(145fe4b)은 이미 들어 있어 병합 없음. 같은 브랜치에 동시 세션 없음(푸시 전 fetch).
- 남은 [ ] 가 1개(CI — 샘님)라 `pip install .` 설치본으로 저장소 밖 임시 폴더에서 쳐 보고 **새 항목 5개** 추가, 5개 모두 처리:
  - bpy 설치 안내 `pip install . bpy==5.2.2` — 저장소 밖에선 `.` 에 pyproject 가 없다 → 저장소 절대 경로(설치본만이면 "저장소 폴더에서").
  - `examples/rig_sample.py` Blender 없음 안내도 `bw` 와 같은 `bpy_install`(3.11 이면 3.13 venv 명령).
  - 이름만 `.gltf`·`.fbx`·`.blend`·`.obj` 인 파일을 Blender 전에 막음(첫 바이트). bpy 5.2.2 로 실제 내보낸 파일 다섯 개(압축 .blend 는 zstd — 5.2 기본값)가 통과하는 것도 확인.
  - 안내 속 `docs/GUIDE.md` 4곳 → `config.guide()`(저장소 밖이면 절대 경로).
  - `bw motion --bvh hero.glb` → "이건 메시다, `bw rig hero.glb`" + 샘플 BVH, 확장자 하나면 'one of' 없이. CHANGELOG 세 줄.
- 사용자 체감: 다섯 모두 "안내를 그대로 치면 도는가"·"원인이 'Blender not found' 뒤에 숨지 않는가". 설치~첫 결과 단계 수는 그대로.

**돌린 시험**
- `python3 -m unittest`(3.11, 블렌더 없음): 249개 중 16개 건너뜀, 나머지 통과(커밋마다). `scripts/check_license_boundary.py` OK.
- bpy 5.2.2 venv(Python 3.13) `BW_REQUIRE_BLENDER=1 BW_NO_RENDER=1 python -m unittest`: **249개 모두 통과, 건너뜀 0**(143초).
- 새 시험 5개는 모두 고치기 전 코드(bonewright/·examples/ 만 되돌림)에서 실패 확인. 렌더는 화면 없는 리눅스라 끔 → Mac 명령 위.
- CI: blender 잡은 pending 이 아니라 잡 전부 러너 없이 3초 만에 실패(run 38261814390, 헤드 a1f6d39) — 10/11 02:49 이후 그대로, 코드 무관(비공개 저장소 Actions 사용량 추정, 백로그 [ ] — 샘님 Settings → Billing).

**완료 수·추가 수**: 완료 5 · 추가 5 (완료 ≥ 추가) · 남은 [ ] 1(CI 러너 — 샘님).

**막힌 것 / 다음**
- 작업 지시는 `claude/cloud-work`, 이 세션의 기본 브랜치는 `claude/cloud-work-meg5zz` — PR #10 이 `claude/cloud-work` 라 지시대로 그쪽에 푸시.
- `bw bench` 의 메시도 같은 머리 확인을 할지(지금은 `bw rig` 만) — 다음 회차 후보.

## 2026-10-12 (13회차)

**한 일** (커밋마다 `claude/cloud-work` 에 푸시, PR #10 에 얹힘)
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main(145fe4b)은 이미 들어 있어 병합 없음. 이번엔 같은 브랜치에 동시 세션 없음(푸시 전마다 fetch 로 확인).
- 남은 [ ] 가 1개(CI — 샘님)라 README 대로 `pip install .`(편집 설치 아님)한 스크래치 venv 로 저장소 밖 임시 폴더에서 명령을 쳐 보고 **새 항목 5개** 추가, 5개 모두 처리:
  - 없는 메시·`--bvh`·`--targets`: 같은 폴더의 비슷한 파일(대소문자·확장자·오타)을 준 꼴 그대로(`hero.glb` → `Hero.glb`, 공백이면 따옴표).
  - `bw bench` 의 자산 받기 명령(인자 없음·없는 경로·빈 폴더): 저장소 밖이면 `fetch_bench_assets.py` 의 절대 경로, 설치본만이면 "저장소 폴더에서".
  - 설치본으로 저장소 밖: `bw export`·`bw demo` 의 첫 실행 안내도 "저장소 폴더에서"(`bw rig`·`bw status` 와 같게).
  - `bw motion`(출처 없음): 리그가 있으면 `--rig <run-id>` 대신 최근 리그 id(`export`·`demo` 와 같은 `latest_rig`).
  - 휠에 샘플 BVH(`bonewright/_samples/wave.bvh`, 12KB)를 싣고 설치본의 안내가 그 실제 파일을 가리킴. CHANGELOG 한 항목.
- 사용자 체감: 다섯 모두 "안내를 그대로 치면 도는가" — 시험이 안내 명령을 parser 에 다시 넣거나(motion) 임시 폴더에서 스크립트를 실제로 돌린다(bench). 설치~첫 결과 단계 수는 그대로(clone·venv·pip·Blender·`bw rig`).

**돌린 시험**
- `python3 -m unittest`(3.11, 블렌더 없음): 244개 중 16개 건너뜀, 나머지 통과. 커밋마다 종료 코드 OK 일 때만 커밋. `scripts/check_license_boundary.py` OK.
- bpy 5.2.2 venv(Python 3.13) `BW_REQUIRE_BLENDER=1 BW_NO_RENDER=1 python -m unittest`: **244개 모두 통과, 건너뜀 0**(148초).
- 새 시험 5개는 모두 고치기 전 코드(bonewright/·pyproject 만 되돌림)에서 실패 확인. 휠은 스크래치 venv 에 실제로 `pip install .` 해 `_samples/wave.bvh` 가 실리는 것 확인.
- 렌더는 화면 없는 리눅스라 끔 → Mac 명령 위.
- CI: blender 잡은 pending 이 아니라 10/11 02:49 이후처럼 잡 4개 모두 러너 없이 2초 만에 실패(run 38195059273, 헤드 8c19696) — 코드 무관, 비공개 저장소 Actions 사용량·지출 한도 추정(백로그 [ ], 샘님 Settings → Billing).

**완료 수·추가 수**: 완료 5 · 추가 5 (완료 ≥ 추가) · 남은 [ ] 1(CI 러너 — 샘님).

**막힌 것 / 다음**
- 작업 지시는 `claude/cloud-work`, 이 세션의 기본 브랜치는 `claude/cloud-work-qxooqe` — PR #10 이 `claude/cloud-work` 라 지시대로 그쪽에 푸시.
- 다음 회차 후보(아직 백로그에 안 넣음): 첫 결과 캐릭터(`tests/assets/…glb`, 1.9MB)도 휠에 실을지 — 휠 크기 결정이라 샘님 판단.

## 2026-10-11 (12회차)

**한 일** (커밋마다 `claude/cloud-work` 에 푸시, PR #10 에 얹힘)
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main(145fe4b)은 이미 들어 있어 병합 없음.
- **같은 브랜치에 다른 세션(11회차, session_01Sbdo…)이 동시에 돌고 있었다.** 시작 때 고른 백로그 4개(`--targets` 모양·doctor 모델 호출 줄·rig 시작 줄·형 이름 두 언어)를
  그쪽이 30초 간격으로 먼저 푸시해, 내가 만든 `--targets` 커밋(중복)은 버리고 그쪽이 6분 조용해질 때까지 기다렸다.
- 그 뒤 남은 [ ] 가 2개(`spikes/` 라이선스·CI — 둘 다 샘님)라 빈 BW_HOME·저장소 밖 폴더에서 명령을 쳐 보고 **새 항목 5개** 추가, 처리:
  - 첫 실행 안내(`bw status`·id 없는 `bw export`/`bw demo`·메시 없는 `bw rig`)의 `bw rig tests/assets/…` 가 저장소 밖에서는 "메시가 없다" → 지금 폴더에 없으면 저장소 캐릭터의 절대 경로.
  - `examples/rig_sample.py` 의 Blender 없음 안내 `--table` 명령도 같은 문제 → 스크립트의 실제 경로(그 폴더에서 돌려 보는 시험).
  - `bw motion --text … --bvh …` 가 말없이 `--text` 로 가 kimodo 없음으로 멈춤 → 상호 배타(종료 2) + 고르는 법(샘플 BVH).
  - 영어 문구 "`--export only apply`" → "`--export: used only when retargeting onto a rig`"(옵션 수와 상관없는 꼴).
  - bpy 안내가 지금 파이썬이 3.13 이 아니어도 `pip install bpy==5.2.2` → 이 항목은 다른 세션이 1분 먼저 푸시(81f6ea2), 내 같은 커밋은 버림.
- 사용자 체감: 고친 넷 모두 "안내를 그대로 치면 도는가" 를 시험이 실제로 쳐 본다(저장소 밖 폴더 포함). 설치~첫 결과 단계 수는 그대로.

**돌린 시험**
- `python3 -m unittest`(3.11, 블렌더 없음): 239개 중 16개 건너뜀, 나머지 통과.
- bpy 5.2.2 venv(Python 3.13, 스크래치패드에 새로 만듦) `BW_REQUIRE_BLENDER=1 BW_NO_RENDER=1 python -m unittest`: **239개 모두 통과, 건너뜀 0**(156초).
- 새 시험은 모두 고치기 전 코드에서 실패 확인. 렌더는 화면 없는 리눅스라 끔 → Mac 명령 위.
- 실수 한 번: 49ca516(applies/apply)은 T() 자리표시 짝·docstring 영어 시험 2개를 깬 채 푸시됐다(`| tail -1` 의 종료 코드를 봄). 바로 다음 48609ad 에서 고침 — 그 뒤로는 unittest 종료 코드로만 커밋.
- CI: blender 잡은 pending 이 아니라 10/11 02:49 이후 모든 잡처럼 러너 없이 1~2초 만에 실패(단계 0개) — 코드 무관, 비공개 저장소 Actions 사용량·지출 한도 추정(11회차 백로그 [ ], 샘님 Settings → Billing).

**완료 수·추가 수**: 완료 4(내 커밋, + 같은 회차 묶음의 다섯째는 다른 세션) · 추가 5 · 남은 [ ] 2(`spikes/` 라이선스·CI 러너 — 둘 다 샘님).

**막힌 것 / 다음**
- 같은 시각에 두 세션이 `claude/cloud-work` 를 함께 쓰면 같은 항목을 겹쳐 한다. 예약이 겹치지 않게(한 회차 끝난 뒤 다음) 샘님이 일정을 봐 주시면 좋다.
- 작업 지시는 `claude/cloud-work`, 세션 기본 브랜치는 `claude/cloud-work-hz5hjr` — PR #10 은 `claude/cloud-work`.

## 2026-10-11 (11회차)

**한 일** (커밋마다 `claude/cloud-work` 에 푸시, PR #10 에 얹힘)
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main 은 이미 들어 있어 병합 없음.
- 기존 1개: `--pin` 형식 오류를 argparse 입력 오류로(종료 1 → 2), `→` 예에 사용자 본 이름.
- 새 항목 15개 추가(실측 근거, 세 묶음), 그중 14개(남은 1개는 CI — 샘님) + 실측 중 발견 1개 처리. 완료 합계 16:
  - **돈·안전**: `BW_BACKEND` 오타(`Mock`·`moc`)가 말없이 유료 codex 로 돌던 것 → 설정을 읽을 때 BLOCKED. 실행 id 8곳에서 `/ \ ..` 거절(runs/ 밖 쓰기·`--for-issue ../..` 읽기).
  - **설정 검사**: `runs/config.json` 값의 형(나중 TypeError 이던 것)·허용 값(명령줄 선택지와 같게), 형 이름 두 언어, GUIDE Settings 문단.
    이 검사로 `bw doctor`·`--for-issue` 가 통째로 멈추게 된 것을 실측으로 잡아 `[settings]` 한 줄 + 기본값으로 계속(깨진 JSON 은 전부터 그랬다).
  - **입력**: `--targets` 파일 모양, 값 없이 끝난 옵션에 선택지·예(`--facing`·`--size`·`--out`·`--bvh` …), `BW_HOME` 이 파일·없는 폴더.
  - **보이기**: `bw doctor` 에 모델 호출 여부 한 줄, `bw rig` 시작 줄에 모델 호출 수, Ctrl-C 한 줄·종료 130·state interrupted,
    `bw status` 가 죽은 프로세스의 running 을 "멈춤(프로세스 없음)" 으로(POSIX 만 — Windows 의 os.kill 은 프로세스를 끝낸다), GUIDE 에 실행 id 규칙.
- 시험 수 219 → 234(블렌더 16 그대로).

**막힌 것 / 샘님 결정**
- **CI**: 10/11 02:49 이후 모든 run 이 러너 없이 1~3초 만에 실패한다(잡 로그 404, 단계 0개 — 코드와 무관). 비공개 저장소 Actions 사용량·지출 한도로 보인다.
  결제는 손대지 않았다. Settings → Billing and plans → Actions 를 봐 주시면 된다. 그동안 근거는 아래 로컬 시험(bpy 포함).
- `spikes/` 라이선스(10/9 3회차부터) — 그대로.
- 설정 문구의 "`--from-skeleton` 0 tokens" 결정 대기와 어긋나지 않게, 새 doctor·시작 줄 문구는 "--from-skeleton·--targets 에 --no-judge 를 함께" 라고 적었다.

**돌린 시험**
- `python3 -m unittest`(3.11, 블렌더 없음): 234개 중 16개 건너뜀, 나머지 통과. 커밋마다 OK 일 때만 커밋.
- bpy 5.2.2 venv(Python 3.13) `BW_REQUIRE_BLENDER=1 BW_NO_RENDER=1 python -m unittest`: **234개 모두 통과, 건너뜀 0**(145초).
- 새 시험은 고치기 전 코드(해당 파일만 되돌림)에서 실패하는 것을 확인.

## 2026-10-11 (10회차)

**한 일** (커밋마다 `claude/cloud-work` 에 푸시, PR #10 에 얹힘)
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main 은 이미 들어 있어 병합 없음.
- 기존 1개: `--facing` 도움말·틀린 값 오류에 고르는 법 — Blender 앞 보기(숫자패드 1)에서 얼굴이면 `neg-y`, 뒤통수면 `pos-y`(rig·bench).
- 남은 [ ] 가 결정 대기 1개뿐이라 빈 BW_HOME·Blender 없음에서 명령을 직접 쳐 보고 새 항목 5개 추가, 그중 4개:
  - 따옴표 없는 공백 든 경로 `bw rig my char.glb` → "unrecognized arguments" 끝에 따옴표 친 명령(이어 붙여 있는 파일일 때만, `--bvh` 도).
  - 틀린 `--preset`(dog) → "네 발 짐승은 quadruped, 그 밖은 `--from-shape`"(rig·bench·motion).
  - `bw motion --bvh` 에 빈 파일·HIERARCHY 로 시작 안 하는 파일 → 실행 폴더·Blender 전에 BLOCKED + 샘플 BVH.
  - `bw bench <없는 경로>` → "파일이나 폴더가 없다" + 받아 둔 `bench-assets/` 폴더 명령 또는 받는 명령.
- 오류 메시지가 다음 할 일을 말하는지: 고친 다섯 곳 모두 `→` 뒤에 그대로 칠 명령이나 고를 값. 따옴표 제안은 시험이 parser 에 다시 넣어 본다.
- 설치~첫 결과 단계 수는 그대로(clone·venv·pip·Blender·`bw rig`). 예제는 이번에 손대지 않았고 bpy 시험(test_examples)으로 그대로 도는 것 확인.

**돌린 시험**
- `python3 -m unittest`(3.11, 블렌더 없음): 219개 중 16개 건너뜀, 나머지 통과. 커밋마다 OK 일 때만 커밋.
- bpy 5.2.2 venv(Python 3.13) `BW_REQUIRE_BLENDER=1 BW_NO_RENDER=1 python -m unittest`: **219개 모두 통과, 건너뜀 0**(148초).
- 새 시험은 모두 옛 코드(bonewright/ 만 되돌림)에서 실패 확인. `scripts/check_license_boundary.py` OK. 렌더는 화면 없는 리눅스라 끔 → Mac 명령 위.
- CI: 코드 커밋 5개(마지막 b7c061c 까지)는 푸시마다 unit(3.11·3.13)·unit-windows·blender 모두 성공 — blender 잡은 pending 으로 멈추지 않았다.
- CI 막힘: 그 뒤 기록 전용 커밋(81880b8·5005720)의 잡 4개는 러너를 받지 못하고(runner_id 0, 로그 404) 1~2초 만에 failure/cancelled — 코드 실패가 아니라 Actions 쪽(비공개 저장소 사용 시간·결제 한도로 추정, 결제는 손대지 않음). 샘님이 Settings → Billing 의 Actions 사용량을 보고 다시 돌리면 된다.

**완료 수·추가 수**: 완료 5(기존 1 + 새 4) · 추가 5 · 남은 [ ] 2(`spikes/` 라이선스 — 샘님 결정 대기, `--pin` 형식 오류 꼴·종료 코드 — 다음 회차).

**막힌 것 / 다음**
- `spikes/` 라이선스: 그대로 샘님 결정 대기.
- 작업 지시는 `claude/cloud-work`, 세션 기본 브랜치는 `claude/cloud-work-0jt8k0` — 같은 커밋을 둘 다에 푸시, PR #10 은 `claude/cloud-work`.

## 2026-10-11 (9회차)

**한 일** (커밋마다 `claude/cloud-work` 에 푸시, PR #10 에 얹힘)
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main 은 이미 들어 있어 병합 없음.
- 기존 1개: `bw rig --pin <없는 본>` 을 Blender 전에 — 이름표 `bonewright/metarig_names.json` 을 이 컨테이너의 bpy 5.2.2 에서
  뽑아 실었고(사람 159·늑대 190본), Blender 시험이 `metarig_dump.py` 결과와 대조한다. 대소문자만 다르면 그 이름을 맨 앞에.
  `--from-skeleton` 은 일반 리그(원본 본 이름)로 갈 수 있어 막지 않고 경고, `--from-shape` 는 건너뜀.
- 남은 [ ] 가 결정 대기 1개뿐이라 새 항목 5개 추가(실측 근거), 그중 4개:
  - **첫 결과 다음 단계**: 저장소에 BVH 가 하나도 없어 `next:` 줄의 `bw motion --bvh <file.bvh>` 에서 막혔다 →
    `examples/wave.bvh`(예제 생성기 출력 그대로, 시험이 같음을 확인) + 안내 세 곳이 이 파일을 준다. README 캐릭터에 18본 리타겟(bpy 확인).
  - 빈 BW_HOME 의 `bw status`·리그 없는 id 생략 `bw demo`/`bw export` → README 첫 명령 그대로(`cli.FIRST_RIG` 하나로).
  - 틀린 run-id(`bw export`·`bw demo`·`bw motion --rig`) → 가까운 리그를 그대로 붙여 넣을 명령으로(없으면 가장 최근 리그).
  - 거절 안내·report.md 의 재실행 명령 `bw rig <mesh> --targets …` → 실제 메시 경로(프로젝트 기준 상대·홈 `~`·공백 따옴표).
- 오류 메시지가 다음 할 일을 말하는지: 고친 곳 모두 안내한 명령을 시험이 cli 에 그대로 넣어 본다.
- 설치~첫 결과 단계 수는 그대로(clone·venv·pip·Blender·`bw rig`), 첫 결과 **다음**(리타겟)이 자리표시 없이 한 줄로 이어진다.

**돌린 시험**
- `python3 -m unittest`(3.11, 블렌더 없음): 213개 중 16개 건너뜀, 나머지 통과. 커밋마다 OK 일 때만 커밋.
- bpy 5.2.2 venv(Python 3.13) `BW_REQUIRE_BLENDER=1 BW_NO_RENDER=1 python -m unittest`: **213개 모두 통과, 건너뜀 0**(131초).
- 새 시험은 모두 옛 코드(bonewright/ 만 되돌림)에서 실패 확인. 렌더는 화면 없는 리눅스라 끔 → Mac 명령 위.
- CI: 이번 회차 푸시 5번 모두 unit(3.11·3.13)·unit-windows·blender 성공. blender 잡은 pending 으로 멈추지 않았다.

**완료 수·추가 수**: 완료 5(기존 1 + 새 4) · 추가 5 · 남은 [ ] 2(`spikes/` 라이선스 — 샘님 결정 대기, `--facing` 값 설명 — 다음 회차).

**막힌 것 / 다음**
- `spikes/` 라이선스: 그대로 샘님 결정 대기.
- 작업 지시는 `claude/cloud-work` 이고 세션 기본 브랜치는 `claude/cloud-work-ow4vsy` 였다 — 지시대로 `claude/cloud-work` 에 푸시(PR #10).

## 2026-10-10 (8회차)

**한 일** (커밋마다 `claude/cloud-work` 에 푸시, PR #10 에 얹힘)
- 7회차 이후 상태에서 이어감. `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main 은 이미 들어 있어 병합 없음.
- 기존 2개: `bw demo --size/--frames`·`bw usage --days` 1 이상만(`cli.positive_int`, 고쳐 칠 예).
- 새 항목 20개 추가(실측 근거), 그중 19개 처리:
  - 입력: `--budget` 1 이상·도움말, `bw rig <폴더>` → 폴더라고·안의 메시·`bw bench`, 0바이트·가짜 `.glb` 를 Blender 전에,
    `--from-skeleton`/`--from-shape` 상호 배타, `--targets` 에 바이너리, `bw bench --gt-mesh` 이름, `bw export --out` 폴더·확장자,
    `bw motion --map` 을 Blender 전에.
  - 순서: Blender 를 실행 폴더보다 먼저 확인(`blender.require`), `bw motion --text` 의 kimodo 확인도 그 앞, `BW_NO_RENDER=1 bw demo` 는 Blender 확인보다 먼저.
  - 상태: export·demo 실패가 리그 `state.json` 을 덮지 않음(`export_state.json`·`demo_state.json`, `--for-issue` 에도 실음),
    `bw status` 줄 "input tokens N"·실패 줄 끝 `→ why: bw doctor --for-issue <id>`, GUIDE 에 `bw status` 절.
  - 도움말·명령: 인자 21개 두 언어 도움말, 도움말 숫자를 실제 기본값과 대조, 틀린 하위 명령에 가까운 명령(`bw resume` 은 대신할 것).
  - 기타: `has_bpy_module` 캐시(0.7초짜리 프로세스를 단계마다 띄우던 것), ffmpeg 설치 안내 OS 별.
- 시험 수 182 → 203(블렌더 15 그대로).

**실수 기록**
- `--budget` 커밋(5f81117)을 시험 실패 상태로 푸시했다(새 시험 docstring 첫 줄이 한국어 — 7회차에 생긴 규칙). 바로 다음 커밋에서 고침.
  이후로는 `python3 -m unittest` 가 OK 일 때만 커밋되게 명령을 묶었다.
- 같은 크기 숫자를 sed 로 바꿨다 되돌리면 `.pyc` 가 낡은 채 남아 시험이 거짓 실패했다 → 확인 뒤 `__pycache__` 를 지우고 돌림.

**막힌 것 / 다음**
- `spikes/` 라이선스(10/9 3회차부터 샘님 결정 대기) — 그대로.
- `--pin` 의 없는 본 이름: 메타리그 본 이름 목록이 Blender 안에만 있어 Blender 전 대조 방법을 정하지 못했다. 다음 회차.

**돌린 시험**
- `python3 -m unittest`(3.13, 블렌더 없음): 203개 중 15개 건너뜀, 나머지 통과. 커밋마다.
- bpy 5.2.2 venv `BW_REQUIRE_BLENDER=1 BW_NO_RENDER=1 python -m unittest`: **203개 모두 통과, 건너뜀 0**(137초). 192개 시점에도 한 번 전부 통과.
- 새 시험은 고치기 전 코드(해당 파일만 되돌림)에서 실패하는 것을 확인(도움말 숫자 시험은 기본값 하나를 바꿔 실패 확인).

## 2026-10-10 (7회차)

**한 일** (커밋마다 `claude/cloud-work` 에 푸시, PR #10 에 얹힘)
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main(145fe4b)은 이미 들어 있어 병합 없음.
- 백로그 남은 2개(샘님 결정 대기 1개 제외): `examples/rig_sample.py` 의 Blender 없음 안내가 자리표시 `--table x.glb` 를 주던 것 →
  그대로 붙여 도는 `python3 examples/rig_sample.py --table adventurer` / run-id 없는 `bw demo`·`bw export` 의 argparse
  "required: run_id" → `BLOCKED:` + 가장 최근 리그(`02_rigged.blend` 있는 것)의 명령과 `bw status`, 없으면 `bw rig <메시>`·찾은 곳.
- 남은 [ ] 가 1개라 새 항목 5개 추가(빈 BW_HOME·Blender 없음에서 하위 명령을 인자 없이·틀린 값으로 쳐 봄), 그중 3개:
  메시 없는 `bw rig` → README 첫 명령 한 줄 / 자산 없는 `bw bench` → `fetch_bench_assets.py --only samples && bw bench bench-assets/samples`
  / 단위 시험이 진짜 stderr 에 id 빈 "next: `bw demo `" 줄을 흘리던 것.
- 오류 메시지가 다음 할 일을 말하는지: 이번에 고친 5곳 모두 안내한 명령을 시험이 실제로 넣어 본다(예제는 subprocess 로 실행,
  `bw rig`·`bw bench` 는 cli 파서에 그대로, 받기 스크립트는 `--help` 의 선택지·기본 폴더와 대조).
- 설치~첫 결과 단계 수는 6회차와 같음(clone·venv·pip·Blender·`bw rig`). 대신 그 사이에서 인자를 빠뜨렸을 때 막히는 곳이 줄었다.

**돌린 시험**
- `python3 -m unittest`(3.11, 블렌더 없음): 182개 중 15개 건너뜀, 나머지 통과. 매 커밋 전, 결과 줄을 보고 커밋.
- 새 시험 6개는 모두 옛 코드(해당 파일만 되돌림)에서 실패하는 것을 확인.
- 블렌더 시험 15개는 이 컨테이너에 Blender·bpy 가 없어 건너뜀(이번 변경은 Blender 전 단계라 영향 없을 것으로 봄) → Mac 명령 위.
- CI: blender 잡은 pending 아님 — 이번 푸시 직후 queued/in_progress 로 바로 잡혔다. 결과는 PR #10 체크.

**완료 수·추가 수**: 완료 5(기존 2 + 새 3) · 추가 5 · 남은 [ ] 3(그중 1개 `spikes/` 라이선스는 샘님 결정 대기, 나머지
`bw demo --size 0`·`--frames -1` 검사 없음, `bw usage --days 0` 받음).

**샘님 결정 필요** (6회차와 같음, 새 것 없음)
- `--from-skeleton`·`--from-shape` "0 tokens" 문구, 웹 병합 커밋의 개인 메일, `spikes/` 라이선스, README clone 주소(비공개 저장소).

## 2026-10-10 (6회차)

**한 일** (커밋마다 `claude/cloud-work` 에 푸시, PR #10 에 얹힘)
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main(145fe4b)은 이미 들어 있어 병합 없음.
- 백로그 남은 2개(샘님 결정 대기 1개 제외): `bw doctor` 가 Blender·bpy 를 둘 다 `[required]` 로 찍던 것 → 줄마다
  `[required: one of]`, 찾은 쪽이 있으면 다른 쪽은 `[not needed]` / 호출 없는 `bw usage` 의 0 만 든 JSON → stderr 에 장부 위치
  (없으면 BW_HOME 확인)·토큰 0 경로·`--days` 한 줄(stdout JSON 그대로).
- 남은 [ ] 가 1개라 새 항목 5개 추가(빈 BW_HOME 에서 `bw`·`examples/` 를 직접 돌리고 README 설치 절을 처음부터 따라 함), 그중 3개:
  `bw status` 가 읽히지 않는 state.json 하나로 목록 전체를 '예상 못 한 오류'로 막던 것 → 그 실행만 한 줄 / `bw rig` 끝에
  run-id 를 넣은 다음 명령(`bw demo`·`bw export`·`bw motion --rig`) 한 줄 / README 설치 절이 clone 없이 `pip install .` 부터,
  Homebrew 파이썬의 PEP 668 거절, doctor 주석의 'Rigify 확인'(doctor 는 안 본다) → clone → venv → pip → doctor.
- 설치~첫 결과 단계: 빈 Mac 기준 clone·venv·pip·(Blender 설치)·`bw rig` — 전에는 clone·venv 가 README 에 없어 따라 하면
  `pip install .` 에서 막혔다(저장소 밖이면 "not a Python project", Homebrew 면 PEP 668).
- 새 시험은 모두 옛 코드에서 실패하는 것을 확인. 시험 수 171 → 177(블렌더 15 그대로).
- 실수 하나: 4ea8636 을 기존 시험 하나가 실패한 채 푸시했다(`unittest | tail -1 && git commit` 이 tail 의 종료 코드를 봄).
  그 시험(`test_early_commands_also_reported`)은 깨진 state.json 으로 '예상 못 한 오류' 안내를 시험했는데 status 가 이제 그걸
  건너뛰므로 `bw usage` 로 옮겨 e9c30b0 에서 고침. 이후 커밋은 시험 결과 파일의 마지막 줄을 보고 커밋했다.

**돌린 시험**
- `python3 -m unittest`(3.11, 블렌더 없음): 177개 중 15개 건너뜀, 나머지 통과. 매 커밋 전.
- bpy 5.2.2 venv(Python 3.13) `BW_REQUIRE_BLENDER=1 BW_NO_RENDER=1 python -m unittest`: **177개 모두 통과, 건너뜀 0**(231초).
- README 첫 명령을 bpy 환경에서 실제로: `final ok`, 끝에 "next: `bw demo rig-…`" 줄, 그 줄의 `bw export <id>` 를 그대로 붙여
  GLB 나옴. 설치 절은 로컬 clone 에 venv 를 만들고 `pip install .` → `bw doctor` 까지(Blender 없음이라 종료 1, 새 표시 확인).
- `scripts/check_license_boundary.py` OK. 렌더는 화면 없는 리눅스라 안 돌림(Mac 명령 위).
- CI: blender 잡은 pending 아님(5회차 마지막 run 도 4분 안팎에 success). 결과는 PR #10 체크.

**완료 수·추가 수**: 완료 5(기존 2 + 새 3) · 추가 5 · 남은 [ ] 3(그중 1개 `spikes/` 라이선스는 샘님 결정 대기, 나머지
`examples/rig_sample.py` 의 Blender 없음 안내가 자리표시 `x.glb` 를 주는 것, run-id 없는 `bw demo`·`bw export`).

**샘님 결정 필요** (5회차와 같음, 새 것 없음)
- `--from-skeleton`·`--from-shape` "0 tokens" 문구(GUIDE·`--help`·`bw doctor` 의 codex 줄): 문서를 고칠지, 판정을 기본으로 끌지.
- 웹 병합 커밋의 개인 메일(GitHub Emails 설정), `spikes/` 라이선스.
- README 설치 절의 clone 주소는 지금 비공개 저장소다(공개 전에는 샘님만 받을 수 있다). 공개할 때 주소가 바뀌면
  `test_install_starts_from_nothing` 이 pyproject Homepage 와 함께 바꾸라고 알린다.

## 2026-10-10 (5회차)

**한 일** (커밋마다 `claude/cloud-work` 에 푸시, PR #10 에 얹힘)
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main(145fe4b)은 이미 들어 있어 병합 없음.
- 백로그 남은 2개(샘님 결정 대기 1개 제외): `bw motion --bvh` 진행이 `[3/3]` 부터 시작하던 것 → 실제로 도는 단계만 셈(`[1/1]`,
  `--rig --export` 면 `[1/3]`…`[3/3]`) / 인자 없는 `bw` 가 argparse 한 줄 오류로 끝나던 것 → 명령 목록 + "처음이면 `bw doctor`
  → README 첫 실행 첫 명령"(종료 2 유지).
- 남은 [ ] 가 1개라 새 항목 5개 추가(빈 BW_HOME·Blender 없음 상태로 `bw` 명령을 직접 돌려 찾음), 그중 3개:
  실행 없는 `bw status` 의 빈 출력 → 찾은 폴더·`bw rig`·BW_HOME 안내 / `bw motion` 이 `--rig` 없는 `--export`·`--map`·`--legs`·
  `--no-roll` 을 말없이 버리던 것 → Blender 전에 거절 / `bw bench` 빈 폴더·없는 파일이 종료 0 에 "mean Nonecm"·"Blender not found"
  → Blender 전에 `BLOCKED:`(→ `fetch_bench_assets.py`), Blender 없음은 설치 안내 한 번, 하나도 못 쟀으면 종료 2.
- 새 시험은 모두 옛 코드에서 실패하는 것을 확인. 시험 수 163 → 171(블렌더 15 그대로).

**돌린 시험**
- `python3 -m unittest`(3.11, 블렌더 없음): 171개 중 15개 건너뜀, 나머지 통과. 매 커밋 전.
- bpy 5.2.2 venv(Python 3.13) `BW_REQUIRE_BLENDER=1 BW_NO_RENDER=1 python -m unittest`: **171개 모두 통과, 건너뜀 0**(194초, 36a0415)
- `scripts/check_license_boundary.py` OK. 렌더는 화면 없는 리눅스라 안 돌림(Mac 명령 위).
- CI: blender 잡은 pending 아님(매 run 4분 안팎에 끝남). 결과는 PR #10 체크.

**완료 수·추가 수**: 완료 5(기존 2 + 새 3) · 추가 5 · 남은 [ ] 3(그중 1개 `spikes/` 라이선스는 샘님 결정 대기, 나머지 `bw doctor`
Blender/bpy 표시·빈 `bw usage` 안내).

**샘님 결정 필요** (4회차와 같음, 새 것 없음)
- `--from-skeleton`·`--from-shape` "0 tokens" 문구(GUIDE·`--help`·`bw doctor` 의 codex 줄): 문서를 고칠지, 판정을 기본으로 끌지.
- 웹 병합 커밋의 개인 메일(GitHub Emails 설정), `spikes/` 라이선스.

## 2026-10-10 (4회차)

**한 일** (커밋마다 `claude/cloud-work` 에 푸시, PR #10 에 얹힘)
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main(145fe4b)은 이미 들어 있어 병합 없음.
- 백로그 남은 3개: 시험 설명(`-v` 가 찍는 docstring 첫 줄) 65개 영어 + 지키는 시험 / `spikes/README.md`(영어, `walk_wave.bvh`
  는 시험·GIF 가 써서 지우면 안 된다는 것) / `PRE-PUBLIC-AUDIT.md` 다시 훑음.
- 새 묶음(사용자 체감 기준, 설치 직후 상태로 `bw` 명령을 직접 돌려 찾음) 5개 중 3개:
  Blender 없음이 '예상 못 한 오류'(빈 로그 폴더·BW_DEBUG·이슈 안내, 실행은 계속 `running`)로 빠지던 것 → `BLOCKED:` +
  다운로드 주소 + `bw doctor`, 실행 `failed`, 없는 BW_BLENDER 경로를 짚음, codex 없음에 토큰 0 경로 /
  README 첫 실행 맨 위에 저장소 안 캐릭터로 모델·codex 없이 도는 명령(설치 → 첫 결과 3단계, 전에는 codex 설치·로그인 포함 5단계) /
  `bw doctor | head` 의 BrokenPipeError.
- 시험 수 156 → 163(블렌더 15 그대로).

**돌린 시험**
- `python3 -m unittest`(3.11, 블렌더 없음): 163개 중 15개 건너뜀, 나머지 통과. 매 커밋 전.
- bpy 5.2.2 venv(Python 3.13) `BW_REQUIRE_BLENDER=1 BW_NO_RENDER=1 python -m unittest`: **163개 모두 통과, 건너뜀 0**(172초).
- README 첫 명령을 codex 없는 bpy 환경에서 실제로: 관문 pass, report 나옴(렌더는 화면 없는 리눅스라 `BW_NO_RENDER=1`).
- `scripts/check_license_boundary.py` OK.
- CI: blender 잡은 pending 아님(매 run 4분 안팎에 끝남). 33c0adb 에서 unit(3.11)이 빨강 — BrokenPipe 가 끝날 때 flush 에서
  나는 경우를 로컬은 경쟁 때문에 못 잡았다 → d58b6b4 에서 `main()` 안 flush + 경쟁 없는 시험, unit 셋 초록.

**완료 수·추가 수**: 완료 6(기존 3 + 새 3) · 추가 5 · 남은 [ ] 3(그중 1개는 샘님 결정 대기).

**샘님 결정 필요**
- `--from-skeleton`·`--from-shape` 는 맞춤 호출만 건너뛰고 시각 판정(judge)은 모델을 부른다. GUIDE(160·368·422행)와
  `bw rig --help` 는 "0 tokens" 라 적었다. README·codex 없음 문구는 `--no-judge` 를 함께 적도록 고쳤다. 고를 것:
  (a) 문서를 고친다(GUIDE·help 에 "판정 포함 시 모델 1회"), (b) 두 옵션이 판정을 기본으로 끄게 바꾼다(동작 변경, CHANGELOG).
- 공개 전 점검: GitHub 웹 병합 커밋의 개인 메일이 2 → 9개(PR #1~#9). GitHub → Settings → Emails 의
  "Keep my email addresses private" 를 켜기 전에는 PR #10 병합도 하나를 더한다. 자세히는 `docs/PRE-PUBLIC-AUDIT.md` "다시 훑음".
- 10/9 3회차의 `spikes/` 라이선스 결정은 그대로 남음(아래).

## 2026-10-09 (3회차)

**한 일** (커밋마다 푸시, PR #10 에 얹힘)
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main 은 cloud-work 에 이미 들어 있어 병합 없음.
- 백로그 기존 3개: `rig_sample.py --help` 두 언어 / 예시 문서 영어(`examples/README.md` 영어·`README.ko.md` 한국어,
  결과 문서·`sample-output/*.md` 머리글 영어) / GUIDE 리타겟 절에 BVH 관절 → 컨트롤 표와 `Spine` 을 안 옮기는 이유
  (표를 `bvh_mapping` 과 대조하는 시험).
- 새 항목 5개(첫째 묶음) 모두 처리: 인자 없는 `python3 -m unittest` 가 0개로 끝나던 것(`tests/__init__.py`), `--motion
  --preset quadruped` 를 리깅 전에 거절, 자산 라이선스 표기 영어(tests/assets·ATTRIBUTION), `fetch_bench_assets.py`
  두 언어, `report.md` 버전 줄(Blender 쪽 `_common.done` 이 `blender` 버전을 결과에)·rig-problem 템플릿 `bw --version`.
- 새 항목 5개(둘째 묶음) 모두 처리: T() 짝 점검을 저장소 스크립트까지, `check_license_boundary.py` 두 언어·→,
  GUIDE 의 한글 6곳(ROADMAP 앵커 링크로), RELEASING 영어 요약, fetch User-Agent 버전·주소.
- 새 항목 5개(셋째 묶음) 모두 처리: `bench_score.py` 두 언어(판정은 영어 코드 — 실행 id 가 `sc_<자산>_skeleton|preset|shape`
  로 바뀜), examples README 짝 시험(한국어판에 빠진 GUIDE 링크를 잡음), CI 단계 이름 영어, `check_issue_report.py`
  도움말·→, tests/README 영어 요약.
- 넷째 묶음 5개 추가, 그중 `addon/README`("v0.2 예정" 낡은 문구) 처리. 남은 4개.
- 시험 수 136 → 156(블렌더 15 그대로). CI: d6e4f96 까지 푸시·PR run 모두 초록, 이후 run 은 이 기록을 쓸 때 진행 중.

**막힌 것 / 샘님 결정**
- 넷째 묶음 첫 항목(라이선스): `spikes/` 의 `bvh_check.py`·`render_rig2.py`·`rigify_headless.py` 가 `import bpy` 인데
  `LICENSE` 는 bpy_scripts/ 말고 전부 MIT 라 적었다. LICENSE 문구를 바꾸는 일이라 손대지 않았다. 고를 것:
  (a) LICENSE·`bpy_scripts/README.md` 표에 `spikes/` 를 GPL 로 적는다, (b) 스파이크 셋을 지운다(기록은 git 에 남음).
  정해지면 `check_license_boundary.py` 가 `bonewright/` 밖도 보게 넓힐 수 있다(지금 넓히면 spikes 때문에 CI 가 빨개진다).

**돌린 시험**
- `python3 -m unittest`(Python 3.13, 블렌더 없음) — 156개 중 15개 건너뜀, 나머지 통과. 매 커밋 전 같은 명령.
- bpy 5.2.2 venv(`BW_REQUIRE_BLENDER=1 BW_NO_RENDER=1 python -m unittest`, 인자 없는 형태): **156개 모두 통과, 건너뜀 0**(230초). 145개 시점에도 한 번 전부 통과.
- 새 시험마다 고치기 전 코드로 되돌려 실패하는 것 확인(`--help`·`--motion` 순서·발견·fetch 문구·라이선스 문구·addon).
- `check_license_boundary.py` OK(MIT 영역 15개). 렌더는 안 돌렸다(화면 없는 리눅스).

## 2026-10-09 (2회차)

**한 일**
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main 은 cloud-work 에 이미 들어 있어 병합 없음.
- CI 액션 Node 24 판: `actions/checkout@v5`·`actions/setup-python@v6`(세 잡 모두). `test_release.WorkflowActionTests` 가 Node 20 판
  재발을 잡는다. CHANGELOG Fixed. 푸시 뒤 run 37943600285·37943625346(e5b140b) 네 잡 모두 초록 — `Run actions/checkout@v5`·`setup-python@v6` 단계 성공.
- 두 README 에 설정 한 줄: `runs/config.json` 예시(`{"lang": "en", "rig": {"rest_pose": "t"}}`)와 GUIDE Settings 앵커 링크.
  `test_docs.FirstRunTests.test_settings_line_matches_between_languages`(두 언어 예시가 같고 모르는 키가 없는지).
- `tests/README.md` 표를 실제와 맞춤(cli 15→20, examples 3→블렌더 묶음 7·나머지 5, errors 15→24, docs 14→22, i18n 7→10,
  release 4→6, "15개 건너뜀", CI 세 잡). `test_docs.TestListTests.test_tests_readme_table_is_current` 가 묶음별 수·블렌더 칸을
  unittest 로더와 대조한다(숫자 하나를 틀리게 바꿔 실패하는 것 확인).
- `bw doctor --for-issue` 의 모르는 설정 키를 한 번만: `doctor(warn_unknown=False)`, 설정 절 줄만 남김. 그냥 `bw doctor` 는 그대로 경고.
  기존 시험은 doctor 를 가짜로 바꿔 중복이 안 보였다 → 진짜 doctor 로 도는 `test_unknown_key_warned_once`(옛 코드에서 2≠1 로 실패 확인).
- CONTRIBUTING 시험 수 130 → 135(블렌더 15). 백로그 남은 3개라 새 항목은 안 더함.
- 실수 기록: tests/README 시험을 확인하다 `git checkout` 으로 커밋 전 편집을 날렸다가 직전 백업으로 되살렸다(커밋 내용에 영향 없음).

**돌린 시험**
- `BW_REQUIRE_BLENDER=1 BW_NO_RENDER=1 python -m unittest <7개 모듈>`(bpy 5.2.2, Python 3.13 venv) — **135개 모두 통과, 건너뜀 0**(191초).
  Python 3.11(블렌더 없음) — 135개 중 15개 건너뜀, 나머지 통과.
- `check_license_boundary.py` OK. 설치본(venv) `check_issue_report.py --expect-config` OK, 출력에서 `cross_trimm` 은
  JSON 본문 1번 + 경고 1번. 렌더는 안 돌렸다(화면 없는 리눅스).

**Mac에서 확인할 것**
```bash
git fetch && git checkout claude/cloud-work && python3 -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release tests.test_docs tests.test_i18n
d=$(mktemp -d) && mkdir $d/runs && echo '{"rig": {"cross_trimm": false}}' > $d/runs/config.json && BW_HOME=$d BW_LANG=en bw doctor --for-issue 2>/dev/null | grep -c 'cross_trimm (→'   # 1 이어야 한다
```

## 2026-10-09

**한 일**
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main(145fe4b, PR #9 병합)은 cloud-work 에 이미 들어 있어 병합 없음.
- 리타겟 예시: `python3 examples/rig_sample.py --motion` — 캡슐 인형을 리깅하고 절차 생성 BVH(`wave_bvh`, Mixamo 식 이름
  19관절, 손 흔들기 24프레임, 라이선스 문제 없음)를 `pipeline.motion` 으로 옮긴다. 결과 `examples/sample-output/capsule_doll_motion.md`
  (18개 옮김, `Spine` 1개 안 옮김, report.md 발췌 — 오차 숫자는 기계마다 달라 뺐고 BVH 절대 경로는 `examples/out/` 로).
  README·README.ko·examples/README 링크. `test_examples`: 매핑 표 대조(블렌더 불필요)·파일 결정성·경로 없음·블렌더 대조.
- 예제 오류 문구 두 언어: `rig_sample.py` 의 Blender 없음·파일 없음·GLB 아님·`--table`·`--motion` 문구가 `BW_LANG` 을 따른다.
  `ExampleMessageTests` 2개, CHANGELOG Fixed.
- `bw doctor --for-issue` 에 `runs/config.json` 절: 내용 그대로(깨진 JSON 도), 4000자 상한, 홈 경로 `~`, 모르는 키 한 줄.
  `test_cli` 3개, GUIDE·rig-problem 템플릿 문구, CI unit 잡이 홈 경로 든 설정을 두고 `check_issue_report.py --expect-config`.
- 안 읽히는 설정 삭제: `blender.prefer_module`, 같은 점검으로 찾은 `default_model`. `test_errors.test_every_default_setting_is_read`
  (기본 설정 키가 모두 `bonewright/` 어딘가에서 읽히는지), CHANGELOG Changed. 옛 설정에 남아 있으면 `bw doctor` 가 모르는 키로 알린다.
- 백로그 남은 2개(CI 액션 버전·README 설정 안내) → 10/9 절에 새 항목 5개. CONTRIBUTING 시험 수 130(블렌더 15).
- PR #10(claude/cloud-work → main)이 열려 있어 새 PR 은 만들지 않음 — 이번 커밋이 그 PR 에 얹힌다.

**돌린 시험**
- `BW_REQUIRE_BLENDER=1 BW_NO_RENDER=1 python -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release tests.test_docs tests.test_i18n`
  (bpy 5.2.2, Python 3.13 venv) — **130개 모두 통과, 건너뜀 0**(193초). `BW_SKIP_BLENDER=1`(Python 3.11) — 130개 중 15개 건너뜀, 나머지 통과.
- `check_license_boundary.py` OK. 설치본(venv) `check_issue_report.py --expect-config`(BW_HOME 을 홈 아래, 홈 경로 든 설정) OK.
  렌더는 안 돌렸다(화면 없는 리눅스). CI 의 새 `--expect-config` 단계 결과는 이번 푸시의 Actions 에서 본다.

**Mac에서 확인할 것**
```bash
git fetch && git checkout claude/cloud-work && python3 -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release tests.test_docs tests.test_i18n
BW_NO_RENDER=1 python3 examples/rig_sample.py --motion | tail -8   # 옮긴 본 18개 · 프레임 24, sample-output 과 같은지
BW_LANG=en bw doctor --for-issue | grep -A3 'runs/config.json'      # 설정 파일이 있으면 내용과 unknown keys 줄
```

## 2026-10-08 (2회차)

**한 일**
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main 이 앞서 있지 않아 병합 없음(cloud-work 가 13커밋 앞섬).
- `docs/GUIDE.md` 에 "Settings (`runs/config.json`)" 절: 자주 바꿀 키 10개·기본값 표, 프롬프트 언어 우선순위
  (`--lang` > config > `BW_LANG` > 로캘), JSON 예시. `test_docs.SettingsTableTests` 가 표·예시를 `config.DEFAULTS` 와 대조.
  `blender.prefer_module` 은 코드 어디서도 안 읽혀 표에서 뺐다(새 백로그).
- `runs/config.json` 의 모르는 키(오타) 경고: `bw doctor` 와 `bw rig` 시작에 한 줄, 가까운 키 제안(`rig.cross_trimm (→ rig.cross_trim?)`),
  멈추지 않음. 메시 경로로 막히기 전에 먼저 나온다. `test_errors.test_unknown_settings_key_warns`, CHANGELOG Added.
- 10/8 CI 새 단계 확인: run 37717221862 네 잡(unit 3.11·3.13, unit-windows, blender) 모두 초록. Windows 출력에
  `BW_HOME=~\bw-home`·`work folder (ROOT): ~\bw-home` — `C:\Users\…` 치환이 실제로 돈다. 고칠 것 없음.
  같은 로그의 Node.js 20 지원 종료 경고(checkout@v4·setup-python@v5)는 새 백로그로.
- 문서 오류 이슈 템플릿 `.github/ISSUE_TEMPLATE/docs-problem.md`(어디·무엇이라 적혔나·실제로 본 것·버전), CONTRIBUTING 템플릿 목록에 추가.
  `test_docs.IssueTemplateTests`: 템플릿마다 name·about·labels, CONTRIBUTING 이 모든 템플릿 이름을 든다.
- 백로그 남은 항목 1개(리타겟 예시) → 2회차 절에 새 항목 5개(예제 오류 문구 영어, `--for-issue` 에 설정 싣기,
  `prefer_module` 정리, CI 액션 버전, README 설정 안내). CONTRIBUTING 시험 수 121(블렌더 14).
- PR #10(claude/cloud-work → main)이 열려 있어 새 PR 은 만들지 않음 — 이번 커밋이 그 PR 에 얹힌다.

**돌린 시험**
- `BW_REQUIRE_BLENDER=1 BW_NO_RENDER=1 python -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release tests.test_docs tests.test_i18n`
  (bpy 5.2.2, Python 3.13 venv) — **121개 모두 통과, 건너뜀 0**(177초). `BW_SKIP_BLENDER=1`(Python 3.11) — 121개 중 14개 건너뜀, 나머지 통과.
- `check_license_boundary.py` OK. 설치본(venv) `check_issue_report.py`(BW_HOME 을 홈 아래) OK. 렌더는 안 돌렸다(화면 없는 리눅스).

**Mac에서 확인할 것**
```bash
git fetch && git checkout claude/cloud-work && python3 -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release tests.test_docs tests.test_i18n
mkdir -p runs && echo '{"rig": {"cross_trimm": false}}' > runs/config.json && bw doctor | tail -3; rm runs/config.json   # ⚠ … rig.cross_trimm (→ rig.cross_trim?) 한 줄
```

## 2026-10-08

**한 일**
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. main 이 앞서 있지 않아 병합 없음.
- 모델 프롬프트 언어 기본값: `--lang` 생략 시 `runs/config.json` 의 `lang`, 그것도 없으면 `BW_LANG`·로캘(기존 기본 ko →
  영어 사용자도 판정 notes·fit reasoning 을 한국어로 받았다). `config.DEFAULTS["lang"]` 은 빈 값. 프롬프트 en/ko 판 짝 확인.
  `test_i18n.PromptLangTests` 3개, CHANGELOG Changed 한 줄, `--lang` 도움말 갱신.
- CI 에 설치본 `bw doctor --for-issue` 점검(unit·unit-windows·blender 잡): `scripts/check_issue_report.py` — 종료코드 0/1,
  `<details>` 한 덩어리, traceback 없음, 홈·`/Users/`·`/home/`·`C:\Users\` 경로 없음. BW_HOME 을 홈 아래에 둬 치환할 경로가
  실제로 출력에 들어가게 함. bpy 잡은 설치본 리깅(`installed`)의 state.json·로그 꼬리까지 본다. 결과는 다음 CI 에서(새 백로그).
- 다음 버전 제안 0.2.1 → **0.3.0**(새 플래그 `--version`·`--for-issue`, 기본값 변경 2건). `docs/RELEASING.md` 에 "다음 버전 점검" 표,
  `test_release.ProposedVersionTests`(제안이 지금보다 크고, 셋째 자리 제안이면 "new flag/changed default" 문구 금지). 태그·릴리스 안 함.
- 깨진 `runs/config.json`(끝 쉼표·목록) → "예상 못 한 오류 — 이슈를 열어라" 대신 줄·칸을 짚는 `BLOCKED:`(`config._read_user_config`).
  `test_errors.test_broken_settings_file`. 3.13 json 은 칸 번호가 하나 달라(14 vs 15) 시험이 둘 다 받는다.
- 백로그 남은 항목 0 → 10/8 절에 새 항목 5개(근거 포함: GUIDE 설정 절, 모르는 설정 키 경고, CI 새 단계 결과 확인, 리타겟 예시, 문서 오류 신고 길).
  CONTRIBUTING 시험 수 117(블렌더 14).
- PR #10(claude/cloud-work → main)이 열려 있어 새 PR 은 만들지 않음 — 이번 커밋이 그 PR 에 얹힌다.

**돌린 시험**
- `BW_REQUIRE_BLENDER=1 BW_NO_RENDER=1 python -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release tests.test_docs tests.test_i18n`
  (bpy 5.2.2, Python 3.13 venv) — **117개 모두 통과, 건너뜀 0**(151초). `BW_SKIP_BLENDER=1`(Python 3.11) — 117개 중 14개 건너뜀, 나머지 통과.
- 설치본(저장소 밖 venv): `BW_BACKEND=mock bw rig … --run-id installed` 뒤 `check_issue_report.py installed --expect-code 0` OK,
  bpy 없는 3.11 설치본은 종료 1·경로 없음 OK. `check_license_boundary.py` OK. 렌더는 안 돌렸다(화면 없는 리눅스).
- Windows 단계는 여기서 못 돌린다 — GitHub Actions 결과로 확인(백로그).

**Mac에서 확인할 것**
```bash
git fetch && git checkout claude/cloud-work && python3 -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release tests.test_docs tests.test_i18n
python3 scripts/check_issue_report.py   # 설치된 bw 로: OK 와 /Users/ 없음
mkdir -p runs && echo '{"lang": "en",}' > runs/config.json && bw doctor; rm runs/config.json   # BLOCKED: … line 1, column 1x 가 떠야 한다(이슈 안내 아님)
```

## 2026-10-07 (2회차)

**한 일**
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main(PR #9 병합분) 빨리감기 병합.
- `rig.cross_trim` 기본값 문서 정정: v0.2.0 태그의 `config.py` 도 `True` 인데 CHANGELOG 0.2.0 절·ROADMAP 은 "기본 끔"(옛 광선 판정).
  0.2.0 절을 정정 표기와 함께 고치고 ROADMAP 에 정정 두 줄, `[Unreleased] Fixed` 에 한 줄.
  `test_docs.DefaultClaimTests`: README·GUIDE·CHANGELOG 의 "`섹션.키` … on/off by default" 를 `config.DEFAULTS` 와 대조.
- `runs/<id>/report.md` 절대 경로 제거(`pipeline._shown`): 실행 폴더 안 파일은 상대 경로(`targets.json`·`02_rigged.blend`·
  `motion.blend`), 밖(메시·BVH·`--export` 경로)은 홈 폴더를 `~` 로. 시험 2개 + 리깅·리타겟 블렌더 시험에 단언 추가.
- 사족 예시: `make_test_mesh` 에 `kind=quadruped`(절차 생성 네 발 캡슐 개, 키 0.92m, 앞 -Y, 꼬리).
  `rig_sample.py --preset quadruped` → 관문 ok·변형 본 110(앞·뒷다리 체인·발가락). 찾은 발 위치가 놓은 자리와 일치(y 중심 이동 반영).
  report 에 "조각 사이 빈틈을 지나는 본 4"(뒷다리 shin) 경고는 남는다 — 예시 머리 주석에 적음.
  `examples/sample-output/capsule_dog.md`, README·README.ko·examples/README 에서 링크. 시험 3개(표 재생성·네 다리·지금 리깅과 대조).
- 행동 강령: `docs/CODE-OF-CONDUCT-PLAN.md`(선택지·연락처 후보) + `docs/drafts/CODE_OF_CONDUCT.md`(Contributor Covenant 2.1 원문,
  공식 저장소에서 받음, 연락 칸 비움). 루트에는 넣지 않았다(샘님 결정). 루트로 옮겼는데 연락 칸이 비면 실패하는 시험.
- 백로그 남은 항목 3개라 새 항목은 추가하지 않음. CONTRIBUTING 시험 수 112(블렌더 14).

**돌린 시험**
- `BW_REQUIRE_BLENDER=1 BW_NO_RENDER=1 python -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release tests.test_docs tests.test_i18n`
  (bpy 5.2.2, Python 3.13 venv) — **112개 모두 통과, 건너뜀 0**(179초). `BW_SKIP_BLENDER=1`(Python 3.11) — 112개 중 14개 건너뜀, 나머지 통과.
- `python3 scripts/check_license_boundary.py` OK. 렌더는 안 돌렸다(화면 없는 리눅스, CI 와 같은 이유) — 캡슐 개가 눈으로 괜찮은지는 Mac 에서.

**Mac에서 확인할 것**
```bash
git fetch && git checkout claude/cloud-work && python3 -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release tests.test_docs tests.test_i18n
python3 examples/rig_sample.py --preset quadruped && open examples/out/runs/capsule_dog/   # 렌더 3장으로 네 다리 본 위치 눈으로
grep -c "$HOME" examples/out/runs/capsule_dog/report.md   # 0 이어야 한다(홈 경로가 ~ 로 바뀜)
```

## 2026-10-07

**한 일**
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main(PR #8 병합분) 빨리감기 병합.
- `bw doctor --for-issue [RUN_ID]`: 버그 신고에 붙일 한 덩어리(버전·Python·OS·`BW_*`·`bw doctor` 결과·실행 하나의
  `state.json`·마지막 로그 끝 40줄, run-id 생략 시 가장 최근 실행). 홈 폴더와 `/Users/<이름>`·`/home/<이름>`·`C:\Users\<이름>` → `~`.
  이슈 템플릿 2종·예상 못 한 오류 안내·GUIDE 가 이 명령을 가리킨다. 시험 4개.
- 영문화 마무리: `bw bench` 진행 줄·요약·`report.md` 표, `runs/<id>/report.md` 의 남은 한국어, fit `reasoning`, codex·manifest 오류,
  mock 응답 문구. `test_i18n` 의 "T() 밖 한글 금지"를 `bonewright/` 전체로 넓힘(gates 의 한글 범위 비교 `가`·`힣` 만 예외).
  bpy 로 `BW_LANG=en bw bench quaternius_adventurer.glb` 를 돌려 출력·report.md·json 에 한글 0 확인.
- 문서 점검 범위: `test_docs` 가 CONTRIBUTING·SECURITY·RELEASING·PR 템플릿·이슈 템플릿 3종의 상대 링크·`bw` 명령도 보고,
  템플릿이 인용한 GUIDE 절 제목, `ISSUE_TEMPLATE/config.yml` 의 `blob/main/<경로>`, `GUIDE.md#앵커` 링크까지 대조.
- `docs/GUIDE.md` "Known gaps and failed attempts": ROADMAP(한국어) 끝의 열린 구멍·실패 실험 7줄 영문 요약(숫자 포함), CONTRIBUTING 이 가리킴.
  쓰다가 발견: `rig.cross_trim` 은 지금 기본 **켬**(복셀 측지 판정)인데 CHANGELOG 0.2.0·ROADMAP 은 "기본 끔"(옛 광선 판정)이라 적었다
  → GUIDE 엔 실제 값으로 적고, 정정은 새 백로그로.
- 백로그 남은 항목 2개 → 새 항목 5개(근거 포함). CHANGELOG(새 플래그가 생겨 "only new flag" 문구 수정)·tests/README·CONTRIBUTING(시험 수 105) 갱신.

**돌린 시험**
- `BW_REQUIRE_BLENDER=1 BW_NO_RENDER=1 python -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release tests.test_docs tests.test_i18n`
  (bpy 5.2.2, Python 3.13 venv) — **105개 모두 통과, 건너뜀 0**(191초). `BW_SKIP_BLENDER=1`(Python 3.11) — 105개 중 13개 건너뜀, 나머지 통과.
- `python3 scripts/check_license_boundary.py` OK. 렌더는 안 돌렸다(화면 없는 리눅스에서 렌더러가 죽는다, CI 와 같은 이유).
- `bw doctor --for-issue` 의 Windows 경로 치환은 문자열 시험만 했다(Windows 에서 실제로는 안 돌림).

**Mac에서 확인할 것**
```bash
git fetch && git checkout claude/cloud-work && python3 -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release tests.test_docs tests.test_i18n
bw doctor --for-issue | grep -c "/Users/"   # 0 이어야 한다(홈 경로가 ~ 로 바뀜)
BW_LANG=en bw bench tests/assets/quaternius_adventurer.glb && cat runs/*/report.md | tail -3   # 표 머리가 영어인지
```

## 2026-10-06 (2회차)

**한 일**
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main(PR #7 병합분) 빨리감기 병합.
- Blender 스크립트 메시지 영문화: `bpy_scripts/` 의 분석 경고(`suspect`)·오류(`error`)·사족 notes 20곳을 `T()` 로.
  `T` 는 `bpy_scripts/_common.py` 에 하나(MIT 본체 import 없이 같은 규칙), `_quad` 의 사본은 그쪽을 쓴다.
  폴백 이름 `leg_axis(발 위치만 잼)` → `leg_axis(feet-only)`. 시험 1개(AST: bpy_scripts 에 T() 밖 한글 문자열 없음).
  README·README.ko·CHANGELOG 의 "Blender 스크립트 메시지는 한국어뿐" 문구 갱신.
- CI `blender` 잡에 단계 추가: 저장소 밖에서 설치본 `bw` 로 `BW_BACKEND=mock bw rig tests/assets/quaternius_adventurer.glb --no-judge`
  를 끝까지(저장소 사본을 import 하면 실패). 클라우드에서 같은 단계를 비편집 설치로 돌려 13초·본 410(변형 73)·관문 통과·출력 영어 확인.
- `docs/DOCS-SPLIT-PLAN.md`: 날짜 붙은 작업 노트 26개를 `docs/notes/` 로 나누는 안(목록·크기·가리키는 곳·개인 경로 2곳, 옮기지 않음 — 샘님 결정).
- README 첫 화면 시험 4개(`test_docs.FirstRunTests`): 설치·첫 실행 명령이 영문·한국어판에서 같고 실제 argparse·`pip` 추가 묶음과 맞는지,
  README 의 본 410·변형 73 이 `examples/sample-output/capsule_doll.md` 와 같은지.
- 백로그 남은 항목 1개 → 새 항목 5개(근거 포함) 추가. CHANGELOG·tests/README·CONTRIBUTING(시험 수 97) 갱신.

**돌린 시험**
- `BW_REQUIRE_BLENDER=1 BW_NO_RENDER=1 python -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release tests.test_docs tests.test_i18n`
  (bpy 5.2.2, Python 3.13 venv) — **97개 모두 통과, 건너뜀 0**(221초). `BW_SKIP_BLENDER=1`(Python 3.11) — 97개 중 13개 건너뜀, 나머지 통과.
- `python3 scripts/check_license_boundary.py` OK. 렌더는 안 돌렸다(화면 없는 리눅스에서 렌더러가 죽는다, CI 와 같은 이유).
- 영어 `suspect` 문구가 실제로 찍히는 메시(목·팔 중심선 실패)는 시험 자산에 없어 화면으로는 못 봤다 — AST 시험으로만 확인.

**Mac에서 확인할 것**
```bash
git fetch && git checkout claude/cloud-work && python3 -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release tests.test_docs tests.test_i18n
BW_LANG=en BW_BACKEND=mock bw rig <목·팔 추정이 실패하는 메시>.glb --no-judge   # "⚠ analysis is doubtful:" 뒤가 영어인지
open docs/DOCS-SPLIT-PLAN.md   # 노트를 docs/notes/ 로 옮길지·빼낼지·그대로 둘지 결정
```

## 2026-10-06

**한 일**
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main(PR #6 병합분) 빨리감기 병합.
- **이번 회차부터 클라우드에서도 `pip install bpy==5.2.2`(python3.13 venv)가 된다** → 블렌더 시험까지 전부 돌렸다.
- `examples/sample-output/capsule_doll.md`: 인자 없이 `rig_sample.py` 를 돌린 결과(변형 본 73·리그 본 410)를 싣고
  README·README.ko·examples/README 에서 링크. 시험 2개(표 손상 여부, 지금 리깅 결과와 대조 — 후자는 블렌더 필요).
  `test_docs` 의 블렌더 시험 수 대조가 메서드 단위 `@requires_blender` 도 세게 고침.
- kimodo.cpp 빌드 안내를 `docs/GUIDE.md` "Text → motion: building kimodo.cpp (optional)" 로 옮김(원본 저장소
  localai-org/kimodo.cpp, macOS 빌드 명령, 필요한 세 경로, `runs/config.json` 의 `kimodo.root`, 가중치 라이선스).
  `bw motion --text` 오류·`bw doctor` 가 이 절을 가리킨다. 시험 2개. 빌드 명령은 원본 README(preset `release`)와
  10/1 기록(`KIMODO_ENABLE_VULKAN=OFF`)을 합친 것이라 Mac 에서 한 번 따라 해 봐야 한다.
- 진행 로그 영문화: `pipeline._log` 30여 곳과 codex 대기 표시를 `T()` 로. 시험 1개(AST: `_log` 인자에 T() 밖 한글 없음).
  `BW_LANG=en BW_BACKEND=mock` 리깅 출력에서 남은 한글은 Blender 스크립트(analyze)의 suspect 문구 1줄 → 새 백로그.
- `docs/media/ATTRIBUTION.md`: `walk_wave.bvh` 생성 모델(kimodo.cpp)·가중치(SOMA RP v1.1, NVIDIA Open Model License).
  관절 30개 = SOMA 골격으로 확인. PRE-PUBLIC-AUDIT 4절 갱신.
- 백로그 남은 항목 0개 → 새 항목 5개(근거 포함) 추가, 그중 1개(위 ATTRIBUTION) 처리. CHANGELOG 갱신.
- PR #7 Codex 리뷰(P1 2건, P2 1건) 반영: 지금 kimodo.cpp 원본은 `build/release/` 에 빌드하고 텍스트 인코더를 GGUF 한 파일
  (옆에 `tokenizer.gguf`)로 깐다 → `pipeline.kimodo_paths` 가 옛·새 배치를 둘 다 찾는다(doctor·motion 공용, 시험 4개).
  `--from-skeleton` 일반 리그 사유 문구도 영문화. `kmd-generate` 인자 순서는 원본 `src/generate.cpp` 와 같음을 확인.

**돌린 시험**
- `BW_REQUIRE_BLENDER=1 BW_NO_RENDER=1 python -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release tests.test_docs tests.test_i18n`
  (bpy 5.2.2 LTS, Python 3.13) — **92개 모두 통과, 건너뜀 0**(154초, 리뷰 반영 뒤). `BW_SKIP_BLENDER=1` — 92개 중 13개 건너뜀, 나머지 통과.
- `python3 scripts/check_license_boundary.py` — OK(MIT 15개 파일). `python3.11 -m py_compile` 로 고친 파일 3.11 호환 확인.
- 렌더(`BW_NO_RENDER` 없이)는 안 돌렸다: 화면 없는 리눅스에서 렌더러가 죽는다(CI 와 같은 이유).

**Mac에서 확인할 것**
```bash
git fetch && git checkout claude/cloud-work && python3 -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release tests.test_docs tests.test_i18n
BW_LANG=en BW_BACKEND=mock bw rig tests/assets/quaternius_adventurer.glb --no-judge   # 진행 로그 영어인지
BW_LANG=en bw doctor   # kimodo 줄이 GUIDE 절을 가리키는지; GUIDE 의 kimodo 빌드 명령이 실제와 맞는지 한 번 대조
```

## 2026-10-05 (2회차)

**한 일**
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main(PR #5 병합분) 빨리감기 병합.
- Windows: `find_blender` 가 `<ProgramFiles>\Blender Foundation\Blender X.Y\blender.exe` 중 가장 높은 판을 찾는다(시험 2개).
  CI 에 `unit-windows`(windows-latest, Python 3.13, `PYTHONUTF8=1`) 추가 — run 48 에서 통과. README·GUIDE 의 Windows 문구 정정.
- 게이트 거절 사유(`gates.py` preflight·rig_gates·judge_gates 22곳 + fit 단계 1곳) `BW_LANG` 따라 영문화.
  한국어 대조 시험은 `BW_LANG=ko` 고정, 영어 모드에서 한글이 없는지 시험 1개.
- `tests/test_i18n.py`: AST 로 모든 `T()` 호출(60여 곳) — 두 인자 문자열, 영어 쪽 한글 없음, 자리표시자 같음.
  걸린 1곳(팔·다리 중심선 문구) 정리.
- CONTRIBUTING 정정(CI 세 잡, 예시 `Ran 82 … skipped=12`). `tests/test_docs.py` 에 시험 명령 목록 5곳 ↔ `tests/test_*.py`
  대조와 CONTRIBUTING 시험 수 대조 추가.
- 백로그 남은 항목 3개(`examples/sample-output` — Mac 필요, kimodo 안내, 진행 로그) → 새 항목 추가 안 함.
- PR #6 Codex 리뷰(P2 2건) 반영: 사족 발 검출 notes(`bpy_scripts/_quad.py`)도 BW_LANG 따라 영어로. 시각 판정의 자유 문장은
  프롬프트 언어(`--lang`, 기본 ko)로 오므로 번역 대신 영어 화면에서는 '모델 출력, `--lang en` 으로 영어' 라고 밝힘. 시험 1개.

**돌린 시험**
- `LANG=C.UTF-8 python3 -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release tests.test_docs tests.test_i18n`
  — 83개 중 71개 통과, 12개 건너뜀('Blender 없음': 클라우드에 Blender·bpy 없음 — `RigMockTests`).
- GitHub Actions run 48(unit·unit-windows·blender) 통과. 이후 푸시분은 PR 에서 확인.

**Mac에서 확인할 것**
```bash
git fetch && git checkout claude/cloud-work && BW_REQUIRE_BLENDER=1 python3 -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release tests.test_docs tests.test_i18n
BW_LANG=en bw rig 사람아닌.glb   # preflight 로 막히는 메시(예: 치비·사족 아닌 블롭)에서 BLOCKED 아래 거절 사유가 영어인지
```

## 2026-10-05

**한 일**
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main(PR #4 병합분) 빨리감기 병합.
- `bw doctor`: 항목마다 `[필수]`/`[선택]` 표시. Blender 앱이나 bpy 하나만 있으면 종료코드 0 — codex(기본 `bw rig` 의 모델 판정에만 필요)·
  kimodo.cpp 는 선택. 출력도 `BW_LANG` 을 따른다. 시험 3개.
- PR 템플릿 `.github/pull_request_template.md`(시험 목록·라이선스 경계·CHANGELOG 체크, 관절 코드 수정 시 벤치 4종 전후 표).
  CONTRIBUTING 의 시험 명령을 CI 목록과 맞춤.
- 패키지 메타데이터: `[project.urls]`, `license-files`(MIT `LICENSE` + `bpy_scripts/LICENSE` GPL), hatchling ≥ 1.27.
  `python -m build` 로 sdist·wheel 둘 다 두 고지가 실리고 METADATA 에 `License-File`·`Project-URL` 이 뜨는 것 확인. 시험 2개.
- `BLOCKED:` 오류 메시지 영문화: 새 `bonewright/i18n.py`(`T`, `lang`)로 cli·pipeline 문구 약 25곳. `BW_LANG` → 로캘 → 기본 영어.
  게이트 거절 사유(`gates.py`)와 진행 로그는 아직 한국어 — README·README.ko 에 명시, 새 백로그 항목으로.
  기존 오류 시험은 `BW_LANG=ko` 로 고정, 영어 시험 2개(한글이 섞이지 않는지 포함).
- 백로그 남은 항목 2개(`examples/sample-output` — Mac 필요, Windows CI) → 새 항목 5개(근거 포함) 추가.
- PR #5 Codex 리뷰(P2) 반영: `blender.py`·`codex.py` 의 오류(Blender 없음, codex 없음·인증·사용 한도·시간 초과)도 영어로. 영어 시험 1개 추가.

**돌린 시험**
- `LANG=C.UTF-8 python3 -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release tests.test_docs`
  — 72개 중 60개 통과, 12개 건너뜀('Blender 없음': 클라우드에 Blender·bpy 없음 — `RigMockTests`).
- 새 venv 에 `pip install .` → `bw doctor`(영어, bpy 없어 종료코드 1), `bw rig none.glb` 영어·`BW_LANG=ko` 한국어 둘 다 종료코드 2.
- `python -m build` → sdist·wheel 라이선스 파일 확인. `python3 scripts/check_license_boundary.py` — OK(MIT 15개 파일).

**Mac에서 확인할 것**
```bash
git fetch && git checkout claude/cloud-work && BW_REQUIRE_BLENDER=1 python3 -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release tests.test_docs
bw doctor; echo $?; BW_LANG=en bw doctor     # codex 가 있든 없든 Blender 가 있으면 0, [필수]/[선택] 표시
BW_LANG=en bw rig 없는파일.glb; BW_LANG=en bw motion   # 영어 BLOCKED + → 안내, 종료코드 2
```

## 2026-10-04 (2회차)

**한 일**
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main(PR #3 병합분) 빨리감기 병합.
- 이슈 템플릿: `install-problem.md`(설치·`bw doctor`), `feature-request.md` 추가, `config.yml` 은 빈 이슈를 끄고
  사용 질문 → `docs/GUIDE.md`, 보안 → `SECURITY.md` 로 안내(Discussions 는 켜져 있는지 몰라 링크 안 함). `bw --version` 추가.
- 예상 못 한 오류: 포괄 `except` 가 이제 오류 종류(`KeyError: ...`)·실행의 `logs/` 폴더·`BW_DEBUG=1`(트레이스백)·이슈 템플릿을 알림.
- 영어 사용자: `bw --help` 를 `BW_LANG`(없으면 로캘)에 따라 — `ko*` 면 한국어, 아니면 영어. 오류 메시지·`bw doctor` 는
  아직 한국어뿐임을 README·README.ko 에 적음(영문화는 새 백로그 항목).
- `tests/test_docs.py`: README·README.ko·GUIDE·examples/README 상대 링크 31개, 문서 속 `bw` 명령 57개를 실제 파서와 대조. CI 두 잡에 포함.
  이 과정에서 `cli.build_parser()` 로 파서 생성을 분리.
- 백로그 남은 항목 1개(`examples/sample-output` — Mac 결과물이 필요해 클라우드에서 못 함) → 새 항목 5개(근거 포함) 추가.

**돌린 시험**
- `python3 -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release tests.test_docs`
  — 64개 중 52개 통과, 12개 건너뜀('Blender 없음': 클라우드에 Blender·bpy 없음 — `RigMockTests`).
- 새 venv 에 `pip install .` → `bw --version`, 영어 `bw --help`, `bw rig 없는파일.glb` 종료코드 2 확인.
- `python3 scripts/check_license_boundary.py` — OK.

**Mac에서 확인할 것**
```bash
git fetch && git checkout claude/cloud-work && BW_REQUIRE_BLENDER=1 python3 -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release tests.test_docs
bw --help; BW_LANG=ko bw --help; bw --version     # 한국어 로캘 Mac 이면 첫 줄도 한국어가 맞다
python3 examples/rig_sample.py && mkdir -p examples/sample-output && cp examples/out/capsule_doll.md examples/sample-output/   # 백로그 남은 항목용
```

## 2026-10-04

**한 일**
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. origin/main(PR #2 병합분) 빨리감기 병합.
- 백로그 4번: 오류 메시지에 고칠 방법(`→` 줄). 메시·`--targets`·`--map`·`--bvh`·리그 run-id 를 Blender 호출 **전에** 확인
  (`pipeline.need_file`/`need_rig`). 없는 명령 `bw resume` 안내를 재실행·`--targets` 재사용으로 고침. `bw status <없는 id>` 종료코드 2.
  타입 힌트 보강. `tests/test_errors.py`(7개).
- 백로그 5번: `docs/PRE-PUBLIC-AUDIT.md` — 비밀 값 없음. 개인 경로는 git 기록(문서 2개, d6091c2 이전)에만,
  **GitHub 웹 병합 커밋 2개에 개인 gmail 주소**. 에셋 라이선스 표기는 다 있음(`walk_wave.bvh` 생성 모델 표기 보강 권장). 지운 것 없음.
- 백로그 6번: CHANGELOG 정리(0.2.0 에 실린 내용을 `[0.2.0] - 2026-09-20` 로 옮기고 Unreleased 채움, 비교 링크),
  `docs/RELEASING.md`, `tests/test_release.py`(버전 3곳 일치). plugin.json 0.1.0 → 0.2.0. 다음 버전 제안 **0.2.1**, 태그 안 만듦.
- 추가 1건: pip 설치본에서 `bw plugin-path` 가 없는 `site-packages/plugin` 을 가리키던 버그 → 휠에 `bonewright/_plugin` 으로 실음. CI 에서 확인.
- 백로그 남은 항목 0 → 공개 준비 기준 새 항목 5개(근거 포함) 추가.

**돌린 시험**
- `python3 -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release` — 54개 중 42개 통과,
  12개 건너뜀('Blender 없음': 클라우드에 Blender·bpy 없음 — `RigMockTests` 의 리그·스키닝·리타겟 시험).
- 새 venv 에 `pip install .` → 저장소 밖에서 `bw plugin-path` 가 `.../bonewright/_plugin` (`.codex-plugin/plugin.json` 있음) 확인.
- `python3 scripts/check_license_boundary.py` — OK. 워크플로 YAML 구문 확인.

**Mac에서 확인할 것**
```bash
git fetch && git checkout claude/cloud-work && BW_REQUIRE_BLENDER=1 python3 -m unittest tests.test_mock tests.test_cli tests.test_examples tests.test_errors tests.test_release
bw rig 없는파일.glb; bw export 없는id; bw status 없는id   # 셋 다 Blender 없이 바로 BLOCKED + "→" 안내
```
그리고 `docs/PRE-PUBLIC-AUDIT.md` 의 "판단 필요" 2건(기록 속 개인 경로, 병합 커밋 개인 메일)은 샘님 결정.

## 2026-10-03

**한 일**
- `latest.md`(10/1 Mac) 종합 PASS → FAIL 없음. main이 앞서 있지 않아 병합 없음.
- 백로그 3번: `examples/rig_sample.py` — 캡슐 인형(기본)·`adventurer`(CC0)·임의 GLB를 mock으로 리깅하고
  내보낸 `rigged.glb`의 변형 본을 순수 파이썬으로 읽어 개수·좌우·부위별 이름 표를 `examples/out/<이름>.md`로 쓴다.
  `--table x.glb`는 블렌더 없이 표만. 무거운 자산은 기존 `scripts/fetch_bench_assets.py` 안내. `examples/out/`은 git 제외.
- `tests/test_examples.py`(블렌더 불필요 3개) 추가, CI 두 잡에 포함. README·README.ko에 링크.

**돌린 시험**
- `python3 -m unittest tests.test_mock tests.test_cli tests.test_examples` — 44개 중 32개 통과, 12개 건너뜀('Blender 없음': 클라우드에 Blender·bpy 없음).
- `python3 examples/rig_sample.py --table adventurer` — 원본 스킨 본 62개 표 확인. 리깅 경로는 블렌더가 없어 못 돌림.
- `python3 scripts/check_license_boundary.py` — OK.

**Mac에서 확인할 것**
```bash
git fetch && git checkout claude/cloud-work && python3 examples/rig_sample.py && python3 examples/rig_sample.py adventurer
cat examples/out/capsule_doll.md examples/out/adventurer.md   # 관문 ok, 변형 본 60~120개, 이름 표가 말이 되는지
```

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
