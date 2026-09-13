"""Codex 답 JSON 스키마."""
_VEC = {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3}
_BONE = {"type": "object", "properties": {"name": {"type": "string"}, "head": _VEC, "tail": _VEC},
         "required": ["name", "head", "tail"], "additionalProperties": False}
# Codex 엄격 스키마: 모든 속성이 required 여야 하고 additionalProperties=false. 그래서 목표는 배열이다.
FIT = {"type": "object",
       "properties": {"targets": {"type": "array", "items": _BONE},
                      "reasoning": {"type": "string"}, "confidence": {"type": "number"}},
       "required": ["targets", "reasoning", "confidence"], "additionalProperties": False}
JUDGE = {"type": "object",
         "properties": {"bones_outside_mesh": {"type": "array", "items": {"type": "string"}},
                        "proportions_ok": {"type": "boolean"}, "issues": {"type": "array", "items": {"type": "string"}},
                        "confidence": {"type": "number"}, "notes": {"type": "string"}},
         "required": ["bones_outside_mesh", "proportions_ok", "issues", "confidence", "notes"], "additionalProperties": False}
