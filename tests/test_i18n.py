"""`T(한국어, 영어)` 짝 점검(블렌더 불필요): `bonewright/` 의 모든 `T(...)` 호출을 AST 로 찾아
영어 쪽에 한글이 없고, f-문자열 자리표시자(`{H}`, `{verts}` …)가 양쪽에 같은지 본다.
한쪽만 고치면 영어 모드에 한국어가 섞이거나 숫자·경로가 빠지는 것을 막는다."""
import ast
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent / "bonewright"


def hangul(s: str) -> bool:
    return any("가" <= c <= "힣" for c in s)


def literal_text(node: ast.expr) -> str | None:
    """문자열·f-문자열의 고정 부분을 이어 붙인다. 문자열이 아니면 None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(v.value for v in node.values if isinstance(v, ast.Constant))
    if isinstance(node, ast.IfExp):   # T("준비됨" if ok else "…", "ready" if ok else "…")
        a, b = literal_text(node.body), literal_text(node.orelse)
        return None if a is None or b is None else a + "\n" + b
    return None


class _BlankStrings(ast.NodeTransformer):
    """자리표시자 식 안의 문자열 상수(`p.suffix or '(확장자 없음)'`)는 번역 대상이라 비교에서 뺀다."""
    def visit_Constant(self, node):
        return ast.Constant("") if isinstance(node.value, str) else node


def placeholders(node: ast.expr) -> list[str]:
    """f-문자열 안 `{...}` 식의 소스(정렬, 안의 문자열 상수는 비움). 일반 문자열은 빈 목록."""
    if isinstance(node, ast.IfExp):
        return placeholders(node.body) + placeholders(node.orelse)
    if not isinstance(node, ast.JoinedStr):
        return []
    return sorted(ast.unparse(_BlankStrings().visit(v.value)) for v in node.values if isinstance(v, ast.FormattedValue))


def t_calls():
    for path in sorted(PKG.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "T":
                yield path.relative_to(PKG.parent), node


class TPairTests(unittest.TestCase):
    def test_there_are_calls_to_check(self):
        self.assertGreater(len(list(t_calls())), 50)   # 10/5 기준 cli·pipeline·gates·blender·codex 에 수십 곳

    def test_two_string_arguments(self):
        for path, node in t_calls():
            with self.subTest(at=f"{path}:{node.lineno}"):
                self.assertEqual(2, len(node.args), "T(한국어, 영어) 두 인자")
                self.assertFalse(node.keywords)
                self.assertIsNotNone(literal_text(node.args[0]), "첫 인자는 문자열이어야 한다")
                self.assertIsNotNone(literal_text(node.args[1]), "둘째 인자는 문자열이어야 한다")

    def test_english_side_has_no_hangul(self):
        for path, node in t_calls():
            with self.subTest(at=f"{path}:{node.lineno}"):
                en = literal_text(node.args[1]) or ""
                self.assertFalse(hangul(en), en)

    def test_same_placeholders_on_both_sides(self):
        for path, node in t_calls():
            with self.subTest(at=f"{path}:{node.lineno}"):
                self.assertEqual(placeholders(node.args[0]), placeholders(node.args[1]))


    def test_progress_log_has_no_bare_hangul(self):
        """진행 로그(`_log(quiet, 메시지)`)의 한국어는 모두 T() 안에 있어야 영어 모드 첫 화면에 한국어가 안 섞인다."""
        def bare(node):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "T":
                return
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                yield node.value
            for child in ast.iter_child_nodes(node):
                yield from bare(child)
        calls = 0
        for path in sorted(PKG.rglob("*.py")):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("_log", "heartbeat"):
                    calls += 1
                    for s in bare(node.args[-1]):
                        with self.subTest(at=f"{path.relative_to(PKG.parent)}:{node.lineno}"):
                            self.assertFalse(hangul(s), s)
        self.assertGreater(calls, 30)


if __name__ == "__main__":
    unittest.main()
