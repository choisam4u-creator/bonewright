"""문서 점검: README·README.ko·GUIDE·examples/README 의 상대 링크가 실제 파일을 가리키고,
문서에 적힌 `bw <명령> --옵션` 이 실제 argparse 에 있는지. 블렌더 불필요.
(10/1 Mac 이 손으로 한 링크 점검, 9/20 문서 검증의 틀린 주장 11건을 시험으로 굳힌다)"""
import argparse
import re
import shlex
import unittest
from pathlib import Path

from bonewright import cli

REPO = Path(__file__).resolve().parent.parent
DOCS = [REPO / "README.md", REPO / "README.ko.md", REPO / "docs" / "GUIDE.md", REPO / "examples" / "README.md"]

LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)|<img[^>]*\ssrc=\"([^\"]+)\"")
INLINE_BW = re.compile(r"`((?:[A-Z_]+=\S+\s+)*bw\s[^`]*)`")
FENCE = re.compile(r"```[a-z]*\n(.*?)```", re.S)


def relative_links(text: str) -> list[str]:
    out = []
    for m in LINK.finditer(text):
        target = m.group(1) or m.group(2)
        if re.match(r"[a-z]+:", target) or target.startswith("#"):
            continue
        out.append(target.split("#", 1)[0])
    return out


def bw_commands(text: str) -> list[str]:
    """인라인 코드와 코드 블록 줄에서 `bw ...` 명령을 뽑는다(앞의 환경 변수 대입은 건너뜀, 주석은 뗌)."""
    cmds = [m.group(1) for m in INLINE_BW.finditer(text)]
    for block in FENCE.findall(text):
        for line in block.splitlines():
            line = line.split(" #", 1)[0].strip()
            if re.match(r"(?:[A-Z_]+=\S+\s+)*bw\s", line):
                cmds.append(line)
    return cmds


def check_command(parser: argparse.ArgumentParser, cmd: str) -> str | None:
    """틀린 점이 있으면 설명을, 없으면 None."""
    try:
        words = shlex.split(cmd.replace("[", " ").replace("]", " "))
    except ValueError:
        words = cmd.replace("[", " ").replace("]", " ").split()
    words = words[words.index("bw") + 1:]
    sub = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    if not words or words[0].startswith("--"):
        known = parser._option_string_actions
        bad = [w for w in words if w.startswith("--") and w.split("=")[0] not in known]
        return f"없는 옵션 {bad}" if bad else None
    if words[0] not in sub.choices:
        return f"없는 명령 {words[0]!r}"
    known = sub.choices[words[0]]._option_string_actions
    bad = [w for w in words[1:] if w.startswith("--") and w.split("=")[0] not in known]
    return f"`bw {words[0]}` 에 없는 옵션 {bad}" if bad else None


class DocLinkTests(unittest.TestCase):
    def test_relative_links_exist(self):
        for doc in DOCS:
            for target in relative_links(doc.read_text(encoding="utf-8")):
                with self.subTest(doc=doc.name, link=target):
                    self.assertTrue((doc.parent / target).exists(), f"{doc.relative_to(REPO)} → {target} 없음")


class DocCommandTests(unittest.TestCase):
    def test_documented_commands_parse(self):
        parser = cli.build_parser()
        seen = 0
        for doc in DOCS:
            for cmd in bw_commands(doc.read_text(encoding="utf-8")):
                seen += 1
                with self.subTest(doc=doc.name, cmd=cmd):
                    self.assertIsNone(check_command(parser, cmd), f"{doc.relative_to(REPO)}: {cmd}")
        self.assertGreater(seen, 20, "명령 추출이 망가졌다")

    def test_checker_catches_mistakes(self):
        parser = cli.build_parser()
        self.assertIsNotNone(check_command(parser, "bw resume rig-1"))
        self.assertIsNotNone(check_command(parser, "bw rig x.glb --no-such-flag"))
        self.assertIsNone(check_command(parser, 'BW_BACKEND=mock bw rig x.glb --pin "spine.004=0,0,1.42" --no-judge'))


# 시험 명령 목록이 적힌 곳. 시험 모듈이 늘 때마다 따로 놀았다(10/5 에 CONTRIBUTING 을 손으로 맞춤)
TEST_LISTS = [REPO / ".github" / "workflows" / "test.yml", REPO / "CONTRIBUTING.md", REPO / ".github" / "pull_request_template.md",
              REPO / "tests" / "README.md", REPO / "docs" / "RELEASING.md"]
UNITTEST_LINE = re.compile(r"python3? -m unittest(?: -v)?((?: tests\.test_\w+)+)")


class TestListTests(unittest.TestCase):
    """CI·CONTRIBUTING·PR 템플릿·tests/README·RELEASING 의 `python -m unittest …` 목록이 tests/test_*.py 전부와 같은지."""

    def test_every_unittest_command_lists_every_module(self):
        modules = sorted(f"tests.{p.stem}" for p in (REPO / "tests").glob("test_*.py"))
        for doc in TEST_LISTS:
            found = UNITTEST_LINE.findall(doc.read_text(encoding="utf-8"))
            self.assertTrue(found, f"{doc.relative_to(REPO)} 에 시험 명령이 없다")
            for listed in found:
                with self.subTest(doc=str(doc.relative_to(REPO)), listed=listed.strip()):
                    self.assertEqual(modules, sorted(listed.split()))

    def test_contributing_sample_count_is_current(self):
        """CONTRIBUTING 의 `Ran N tests ... (skipped=M)` 예시가 지금 시험 수·블렌더 시험 수와 같은지."""
        m = re.search(r"Ran (\d+) tests \.\.\. OK \(skipped=(\d+)\)", (REPO / "CONTRIBUTING.md").read_text(encoding="utf-8"))
        self.assertIsNotNone(m)
        loader = unittest.TestLoader()

        def flat(suite):
            for t in suite:
                yield from (flat(t) if isinstance(t, unittest.TestSuite) else [t])
        tests = [t for p in (REPO / "tests").glob("test_*.py") for t in flat(loader.loadTestsFromName(f"tests.{p.stem}"))]
        blender = [t for t in tests if getattr(type(t), "_requires_blender", False)]
        self.assertEqual(int(m.group(1)), len(tests))
        self.assertEqual(int(m.group(2)), len(blender))


if __name__ == "__main__":
    unittest.main()
