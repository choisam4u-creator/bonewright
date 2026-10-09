"""`T(한국어, 영어)` 짝 점검(블렌더 불필요): `bonewright/` 의 모든 `T(...)` 호출을 AST 로 찾아
영어 쪽에 한글이 없고, f-문자열 자리표시자(`{H}`, `{verts}` …)가 양쪽에 같은지 본다.
한쪽만 고치면 영어 모드에 한국어가 섞이거나 숫자·경로가 빠지는 것을 막는다."""
import ast
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent / "bonewright"
# 사용자가 직접 돌리는 저장소 스크립트(README·examples/README 가 안내한다). 10/9 3회차에 T() 를 넣었다
USER_SCRIPTS = [PKG.parent / "examples" / "rig_sample.py", PKG.parent / "scripts" / "fetch_bench_assets.py",
                PKG.parent / "scripts" / "check_license_boundary.py", PKG.parent / "scripts" / "bench_score.py"]


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
    for path in [*sorted(PKG.rglob("*.py")), *USER_SCRIPTS]:
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

    def bare_hangul(self, files) -> int:
        """docstring 이 아닌 문자열 중 T() 첫 인자 밖의 한국어를 subTest 로 잡는다. 돌려주는 값은 T() 호출 수."""
        found = 0
        for path in files:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            skip = set()
            for node in ast.walk(tree):
                if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and node.body \
                        and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
                    skip.add(id(node.body[0].value))   # docstring
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "T":
                    found += 1
                    skip.update(id(n) for n in ast.walk(node.args[0]))
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skip \
                        and node.value not in ("가", "힣"):   # 한글 범위 비교(gates 의 한글 경로 검사)
                    with self.subTest(at=f"{path.relative_to(PKG.parent)}:{node.lineno}"):
                        self.assertFalse(hangul(node.value), node.value)
        return found

    def test_blender_scripts_have_no_bare_hangul(self):
        """Blender 스크립트(`bpy_scripts/`, GPL 쪽)의 문자열 중 한국어는 docstring 이 아니면 T() 안에 있어야 한다.
        오류(`error`)·분석 경고(`suspect`)·사족 notes 가 `bw` 화면에 그대로 나오기 때문이다. 주석은 AST 에 없어 상관없다."""
        self.assertGreater(self.bare_hangul(sorted((PKG / "bpy_scripts").glob("*.py"))), 15)   # 10/6: analyze·_quad·_common 등에 20곳

    def test_package_has_no_bare_hangul(self):
        """`bonewright/` 전체(본체): `bw bench` 표·`runs/<id>/report.md`·오류·mock 응답까지 영어 모드에 한국어가 섞이지 않게.
        10/7 bench 17·pipeline 12·codex 2·mock 2·manifest 1곳을 T() 로 옮기고 넓혔다."""
        files = sorted(p for p in PKG.rglob("*.py") if "bpy_scripts" not in p.parts)
        self.assertGreater(self.bare_hangul(files), 100)


    def test_user_scripts_have_no_bare_hangul(self):
        """`examples/rig_sample.py`·`scripts/fetch_bench_assets.py`·`scripts/check_license_boundary.py`: 영어 화면에 나오는 문자열의 한국어는 T() 안에만."""
        for path in USER_SCRIPTS:
            with self.subTest(script=path.name):
                self.assertGreater(self.bare_hangul([path]), 3)


class PromptLangTests(unittest.TestCase):
    """모델 프롬프트 언어: `--lang` > runs/config.json 의 lang > 화면 언어(BW_LANG·로캘).
    10/8 전에는 기본이 ko 라 영어 사용자도 판정 문장(notes·reasoning)을 한국어로 받았다."""

    def load(self, env: dict, lang=None, cfg_json=None):
        import json
        import os
        import tempfile
        from unittest.mock import patch
        from bonewright import config
        with tempfile.TemporaryDirectory() as d:
            if cfg_json is not None:
                (Path(d) / "runs").mkdir()
                (Path(d) / "runs" / "config.json").write_text(json.dumps(cfg_json), encoding="utf-8")
            clean = {k: v for k, v in os.environ.items() if k not in ("BW_LANG", "LC_ALL", "LC_MESSAGES", "LANG")}
            with patch.dict(os.environ, {**clean, **env}, clear=True):
                return config.load(Path(d), lang)["lang"]

    def test_follows_screen_language(self):
        self.assertEqual("en", self.load({}))
        self.assertEqual("en", self.load({"BW_LANG": "en"}))
        self.assertEqual("ko", self.load({"BW_LANG": "ko"}))
        self.assertEqual("ko", self.load({"LANG": "ko_KR.UTF-8"}))

    def test_flag_and_config_win(self):
        self.assertEqual("ko", self.load({"BW_LANG": "en"}, lang="ko"))
        self.assertEqual("ko", self.load({"BW_LANG": "en"}, cfg_json={"lang": "ko"}))
        self.assertEqual("en", self.load({"BW_LANG": "ko"}, lang="en", cfg_json={"lang": "ko"}))

    def test_every_prompt_has_both_languages(self):
        ko = sorted(p.name for p in (PKG / "prompts" / "ko").glob("*.md"))
        en = sorted(p.name for p in (PKG / "prompts" / "en").glob("*.md"))
        self.assertEqual(ko, en)
        self.assertTrue(ko)
        for name in en:
            self.assertFalse(hangul((PKG / "prompts" / "en" / name).read_text(encoding="utf-8")), name)


if __name__ == "__main__":
    unittest.main()


class FetchScriptLanguageTests(unittest.TestCase):
    """`scripts/fetch_bench_assets.py` 는 두 README·examples/README 가 안내하는 명령이다 — 영어 화면에 한글이 없는지.
    10/9 까지 `--help`·진행 문구가 한국어뿐이었다. 내려받기는 가짜로 바꿔 네트워크 없이 돈다."""

    def test_help_and_progress_follow_screen_language(self):
        import contextlib, importlib.util, io, sys, tempfile
        from unittest import mock
        spec = importlib.util.spec_from_file_location("fetch_bench_assets", PKG.parent / "scripts" / "fetch_bench_assets.py")
        fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)
        calls = iter(range(10_000))

        def fake_get(url, dest):   # 하나는 실패, 나머지는 받은 척
            if next(calls) == 0:
                raise OSError("offline")
            return 2048
        for argv in (["--help"], ["--out", "{d}"]):
            with self.subTest(argv=argv[0]), tempfile.TemporaryDirectory() as d:
                out = io.StringIO()
                with mock.patch.dict("os.environ", {"BW_LANG": "en"}), mock.patch.object(fb, "get", fake_get), \
                     mock.patch.object(sys, "argv", ["fetch_bench_assets.py", *[a.format(d=d) for a in argv]]), \
                     contextlib.redirect_stdout(out), contextlib.redirect_stderr(out), contextlib.suppress(SystemExit):
                    fb.main()
                text = out.getvalue()
                self.assertTrue(text.strip())
                self.assertFalse(hangul(text), [ln for ln in text.splitlines() if hangul(ln)][:3])


class BenchScoreLanguageTests(unittest.TestCase):
    """`scripts/bench_score.py` 는 README·GUIDE 가 벤치 숫자의 출처로 안내한다 — 영어 화면의 진행 줄·점수·실패 목록에
    한글이 없는지(10/9 3회차까지 한국어뿐). 리깅·상태·늘어남은 가짜로 바꿔 Blender 없이 돈다."""

    def test_score_lines_follow_screen_language(self):
        import contextlib, importlib.util, io, sys, tempfile
        from unittest import mock
        spec = importlib.util.spec_from_file_location("bench_score", PKG.parent / "scripts" / "bench_score.py")
        bs = importlib.util.module_from_spec(spec); spec.loader.exec_module(bs)
        with tempfile.TemporaryDirectory() as d:
            for n in ("a_ok", "b_fail"):
                (Path(d) / f"{n}.glb").write_bytes(b"glTF")
            out = io.StringIO()
            status = lambda home, rid: "ok" if rid == "sc_a_ok_preset" else "rejected"   # noqa: E731
            with mock.patch.dict("os.environ", {"BW_LANG": "en"}), mock.patch.object(bs, "run", return_value=(0, "")), \
                 mock.patch.object(bs, "status", status), mock.patch.object(bs, "stretch", return_value=(8.0, 0.02)), \
                 mock.patch.object(sys, "argv", ["bench_score.py", "--assets", d, "--home", d, "--motion-humanoid", "w.bvh"]), \
                 contextlib.redirect_stdout(out):
                bs.main()
        text = out.getvalue()
        self.assertFalse(hangul(text), text)
        self.assertIn("rig score     1/2", text)
        self.assertIn("motion pass   0/1", text)
        self.assertIn("rig failed: b_fail", text)
        self.assertIn("motion tear: a_ok", text)
        self.assertIn(" preset ", text)
