"""테스트용 가짜 모델: 분석 랜드마크에서 기계적으로 목표 본 위치를 만든다(BW_BACKEND=mock)."""
import json


def mock_backend(step: str, prompt: str, inputs: dict) -> dict:
    if step == "fit":
        a = json.loads(inputs["analysis.json"]); L = a["landmarks"]
        sw, y = L["shoulder_halfwidth"], 0.0
        meta0 = json.loads(inputs["metarig_bones.json"])
        t = {"spine": {"head": [0, y, L["hip_z"]], "tail": meta0.get("spine", {"tail": [0, y, L["hip_z"] + 0.1]})["tail"]}}   # 척추·목·머리는 균일 스케일에 맡긴다
        thw, tx, tz = L["torso_halfwidth"], L["arm_tip_x"], L["arm_tip_z"]
        for s, x in (("L", 1), ("R", -1)):
            sh = [x * thw * 0.8, y, L["shoulder_z"]]; tip = [x * (tx - 0.02), y, tz]
            mid = lambda a, b, f: [a[0] + (b[0] - a[0]) * f, y, a[2] + (b[2] - a[2]) * f]
            t[f"shoulder.{s}"] = {"head": [x * 0.04, y, L["shoulder_z"] + 0.02], "tail": sh}
            t[f"upper_arm.{s}"] = {"head": sh, "tail": mid(sh, tip, 0.45)}
            t[f"forearm.{s}"] = {"head": mid(sh, tip, 0.45), "tail": mid(sh, tip, 0.85)}
            t[f"hand.{s}"] = {"head": mid(sh, tip, 0.85), "tail": tip}
            lx = x * max(0.08, thw * 0.6)
            t[f"thigh.{s}"] = {"head": [lx, y, L["hip_z"]], "tail": [lx, y, L["knee_z"]]}
            t[f"shin.{s}"] = {"head": [lx, y, L["knee_z"]], "tail": [lx, y, L["ankle_z"]]}
            t[f"foot.{s}"] = {"head": [lx, y, L["ankle_z"]], "tail": [lx, y - 0.12, L["ground_z"] + 0.02]}
        meta = json.loads(inputs["metarig_bones.json"])
        out = []
        for name, v in t.items():
            base = meta.get(name, {"head": [0, 0, 0], "tail": [0, 0, 0.05]})
            out.append({"name": name, "head": v.get("head", base["head"]), "tail": v.get("tail", base["tail"])})
        return {"targets": out, "reasoning": "mock: 랜드마크 비례 배치", "confidence": 0.5}
    if step == "judge":
        return {"bones_outside_mesh": [], "proportions_ok": True, "issues": [], "confidence": 0.5, "notes": "mock"}
    raise ValueError(step)
