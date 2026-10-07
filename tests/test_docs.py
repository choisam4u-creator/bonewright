"""문서 점검: README·README.ko·GUIDE·examples/README·CONTRIBUTING·SECURITY·RELEASING·이슈/PR 템플릿의 상대 링크가 실제 파일을 가리키고,
문서에 적힌 `bw <명령> --옵션` 이 실제 argparse 에 있는지. 블렌더 불필요.
(10/1 Mac 이 손으로 한 링크 점검, 9/20 문서 검증의 틀린 주장 11건을 시험으로 굳힌다)"""
import argparse
import re
import shlex
import unittest
from pathlib import Path

from bonewright import cli

REPO = Path(__file__).resolve().parent.parent
DOCS = [REPO / "README.md", REPO / "README.ko.md", REPO / "docs" / "GUIDE.md", REPO / "examples" / "README.md",
        # 10/7 추가: 공개 뒤 기여자·신고자가 처음 따라 하는 문서
        REPO / "CONTRIBUTING.md", REPO / "SECURITY.md", REPO / "docs" / "RELEASING.md",
        REPO / ".github" / "pull_request_template.md", *sorted((REPO / ".github" / "ISSUE_TEMPLATE").glob("*.md"))]

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


    def test_guide_anchors_exist(self):
        """`GUIDE.md#<앵커>` 링크가 GUIDE 의 실제 제목을 가리키는지(GitHub 방식: 소문자, 구두점 삭제, 공백 → -)."""
        def slug(h):
            return re.sub(r"[^\w\- ]", "", h.strip().lower()).replace(" ", "-")
        heads = {slug(ln.lstrip("#")) for ln in (REPO / "docs" / "GUIDE.md").read_text(encoding="utf-8").splitlines()
                 if ln.startswith("#")}
        self.assertIn("known-gaps-and-failed-attempts", heads)
        seen = 0
        for doc in DOCS:
            for m in re.finditer(r"\]\(([^)\s]*GUIDE\.md)#([^)\s]+)\)", doc.read_text(encoding="utf-8")):
                seen += 1
                with self.subTest(doc=doc.name, anchor=m.group(2)):
                    self.assertIn(m.group(2), heads)
        self.assertGreater(seen, 2)


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
        # 클래스에 붙인 것과 메서드 하나에 붙인 것 둘 다 센다
        blender = [t for t in tests if getattr(type(t), "_requires_blender", False)
                   or getattr(getattr(t, t._testMethodName), "_requires_blender", False)]
        self.assertEqual(int(m.group(1)), len(tests))
        self.assertEqual(int(m.group(2)), len(blender))



class CodePointsAtDocsTests(unittest.TestCase):
    def test_guide_sections_named_in_messages_exist(self):
        """오류·doctor 문구가 `"<절 제목>" ... docs/GUIDE.md` 로 가리키는 절이 GUIDE 에 실제로 있는지."""
        heads = {ln.lstrip("#").strip() for ln in (REPO / "docs" / "GUIDE.md").read_text(encoding="utf-8").splitlines()
                 if ln.startswith("#")}
        named = set()
        for p in (REPO / "bonewright").rglob("*.py"):
            for line in p.read_text(encoding="utf-8").splitlines():
                if "docs/GUIDE.md" in line:
                    named |= set(re.findall(r'\\"([^"\\]+)\\"', line))
        self.assertTrue(named)
        for title in named:
            with self.subTest(title=title):
                self.assertTrue(any(h.startswith(title) for h in heads), f"GUIDE 에 '{title}' 절이 없다")

    def test_guide_sections_named_in_docs_exist(self):
        """이슈 템플릿 등이 `docs/GUIDE.md` → "<절 제목>" 으로 가리키는 절이 GUIDE 에 실제로 있는지."""
        heads = {ln.lstrip("#").strip() for ln in (REPO / "docs" / "GUIDE.md").read_text(encoding="utf-8").splitlines()
                 if ln.startswith("#")}
        named = [(doc, t) for doc in DOCS for t in re.findall(r'docs/GUIDE\.md`?\s*→\s*"([^"]+)"', doc.read_text(encoding="utf-8"))]
        self.assertTrue(named, "feature-request 템플릿의 \"Which flag do I want?\" 를 못 뽑았다")
        for doc, title in named:
            with self.subTest(doc=doc.name, title=title):
                self.assertTrue(any(h.startswith(title) for h in heads), f"GUIDE 에 '{title}' 절이 없다")

    def test_issue_config_links_point_at_repo_files(self):
        """`.github/ISSUE_TEMPLATE/config.yml` 의 `blob/main/<경로>` 안내 링크가 저장소에 있는 파일인지."""
        text = (REPO / ".github" / "ISSUE_TEMPLATE" / "config.yml").read_text(encoding="utf-8")
        paths = re.findall(r"/blob/main/(\S+)", text)
        self.assertTrue(paths)
        for rel in paths:
            with self.subTest(path=rel):
                self.assertTrue((REPO / rel).is_file(), f"config.yml → {rel} 없음")

    def test_messages_do_not_point_at_dated_research_notes(self):
        """날짜 붙은 연구 노트(docs/research-*.html)는 공개용 안내가 아니다 — 코드 문구가 가리키지 않는다."""
        for p in (REPO / "bonewright").rglob("*.py"):
            with self.subTest(file=str(p.relative_to(REPO))):
                self.assertNotRegex(p.read_text(encoding="utf-8"), r"docs/research-\d+")


def section_commands(doc: Path, heading: str) -> list[str]:
    """`## <heading>` 절의 첫 코드 블록에서 주석을 뗀 명령 줄."""
    text = doc.read_text(encoding="utf-8")
    m = re.search(rf"^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m:
        return []
    block = FENCE.search(m.group(1))
    return [ln.split(" #", 1)[0].strip() for ln in block.group(1).splitlines() if ln.strip()] if block else []


class FirstRunTests(unittest.TestCase):
    """README 첫 화면(설치 → `bw doctor` → 첫 리깅)은 공개 뒤 가장 많이 읽힌다. 명령이 실제와 맞고,
    영문·한국어판이 같은 명령을 적고, 결과 숫자가 `examples/sample-output/` 과 같은지."""
    EN = (REPO / "README.md", "Install", "First run")
    KO = (REPO / "README.ko.md", "설치", "첫 실행")

    def test_quickstart_blocks_exist_and_match_between_languages(self):
        for doc, install, first in (self.EN, self.KO):
            with self.subTest(doc=doc.name):
                self.assertIn("pip install .", section_commands(doc, install))
                self.assertIn("bw doctor", section_commands(doc, install))
                self.assertTrue(any(c.startswith("bw rig ") for c in section_commands(doc, first)))
        for i in (1, 2):
            self.assertEqual(section_commands(self.EN[0], self.EN[i]), section_commands(self.KO[0], self.KO[i]))

    def test_quickstart_commands_parse(self):
        parser = cli.build_parser()
        for doc, install, first in (self.EN, self.KO):
            for cmd in section_commands(doc, install) + section_commands(doc, first):
                if cmd.startswith("bw "):
                    with self.subTest(doc=doc.name, cmd=cmd):
                        self.assertIsNone(check_command(parser, cmd))

    def test_install_extras_exist(self):
        """README 의 `pip install ".[headless]"` 같은 추가 묶음이 pyproject 에 있는지."""
        import tomllib
        extras = set(tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))["project"].get("optional-dependencies", {}))
        for doc in (self.EN[0], self.KO[0]):
            for extra in re.findall(r'pip install "?\.\[(\w+)\]', doc.read_text(encoding="utf-8")):
                with self.subTest(doc=doc.name, extra=extra):
                    self.assertIn(extra, extras)

    def test_readme_bone_counts_match_sample_output(self):
        """README 의 '본 410(변형 73)'(mannequiny)과 sample-output 의 캡슐 인형 숫자는 같은 사람 메타리그에서 나온다.
        리그 구성이 바뀌면 둘 다 바뀌어야 한다 — 한쪽만 고치면 여기서 걸린다."""
        sample = (REPO / "examples" / "sample-output" / "capsule_doll.md").read_text(encoding="utf-8")
        m = re.search(r"리그 본 (\d+)\(변형 (\d+)\)", sample)
        self.assertIsNotNone(m)
        total, deform = m.groups()
        self.assertRegex((REPO / "README.md").read_text(encoding="utf-8"), rf"{total} bones \({deform} deform\)")
        self.assertRegex((REPO / "README.ko.md").read_text(encoding="utf-8"), rf"본 {total}개\(변형 본 {deform}개\)")
        self.assertIn(f"변형 본 {deform}개", (REPO / "examples" / "README.md").read_text(encoding="utf-8"))


class DefaultClaimTests(unittest.TestCase):
    """문서의 "`rig.cross_trim` … on/off by default" 주장이 `config.DEFAULTS` 와 같은지.
    10/7: 0.2.0 CHANGELOG·ROADMAP 이 옛 광선 판정 때의 "기본 끔"을 적은 채 나갔다(실제는 켬)."""
    CLAIM = re.compile(r"`(\w+)\.(\w+)`[^.;\n`]{0,100}?\b(on|off)\b\**\s+by default")

    def test_on_off_claims_match_config(self):
        from bonewright.config import DEFAULTS
        seen = 0
        for doc in (REPO / "README.md", REPO / "docs" / "GUIDE.md", REPO / "CHANGELOG.md"):
            for sec, key, state in self.CLAIM.findall(doc.read_text(encoding="utf-8")):
                if sec not in DEFAULTS or key not in DEFAULTS[sec]:
                    continue
                seen += 1
                with self.subTest(doc=doc.name, key=f"{sec}.{key}"):
                    self.assertEqual(bool(DEFAULTS[sec][key]), state == "on")
        self.assertGreater(seen, 0)   # 정규식이 아무것도 못 잡으면 시험이 아무 일도 안 한 것이다


if __name__ == "__main__":
    unittest.main()
