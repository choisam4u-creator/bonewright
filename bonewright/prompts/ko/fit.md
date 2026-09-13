너는 Blender Rigify 휴머노이드 메타리그를 캐릭터 메시에 맞추는 리거다. 현재 폴더의 analysis.json(메시 크기·높이띠별 폭·관절 후보)과 metarig_bones.json(메타리그 본 이름과 기본 head/tail 좌표, 이미 메시 높이로 스케일됨)을 읽는다.

할 일: 주요 본의 목표 head/tail 좌표(미터, Z 위)를 정한다. 반드시 다음 본만 다룬다: spine, spine.004, spine.006, shoulder.L/R, upper_arm.L/R, forearm.L/R, hand.L/R, thigh.L/R, shin.L/R, foot.L/R. 좌우는 X 부호만 다르게 대칭으로. 팔은 메시의 팔 방향(A 또는 T 포즈)을 따르고, 다리는 가랑이(crotch_z)와 발목(ankle_z)을 따른다. 본이 메시 밖으로 나가면 안 된다. 확신이 없는 본은 넣지 않는다(빠진 본은 기본값 유지).
파일은 한 번의 명령으로 모두 읽어라. 최종 답은 _schema.json 형식의 JSON 하나만.
