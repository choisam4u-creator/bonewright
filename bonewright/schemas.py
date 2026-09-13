"""Codex 답 JSON 스키마."""
_BONE = {"type": "object", "properties": {"head": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3},
                                          "tail": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3}},
         "additionalProperties": False}
FIT = {"type": "object",
       "properties": {"targets": {"type": "object", "additionalProperties": _BONE},
                      "reasoning": {"type": "string"}, "confidence": {"type": "number"}},
       "required": ["targets", "reasoning", "confidence"], "additionalProperties": False}
JUDGE = {"type": "object",
         "properties": {"bones_outside_mesh": {"type": "array", "items": {"type": "string"}},
                        "proportions_ok": {"type": "boolean"}, "issues": {"type": "array", "items": {"type": "string"}},
                        "confidence": {"type": "number"}, "notes": {"type": "string"}},
         "required": ["bones_outside_mesh", "proportions_ok", "issues", "confidence", "notes"], "additionalProperties": False}
