"""문서 점검: README·README.ko·GUIDE·examples/README(두 언어)·CONTRIBUTING·SECURITY·RELEASING·이슈/PR 템플릿의 상대 링크가 실제 파일을 가리키고,
문서에 적힌 `bw <명령> --옵션` 이 실제 argparse 에 있는지. 블렌더 불필요.
(10/1 Mac 이 손으로 한 링크 점검, 9/20 문서 검증의 틀린 주장 11건을 시험으로 굳힌다)"""
import argparse
import re
import shlex
import unittest
from pathlib import Path

from bonewright import cli

REPO = Path(__file__).resolve().parent.parent
DOCS = [REPO / "README.md", REPO / "README.ko.md", REPO / "docs" / "GUIDE.md", REPO / "examples" / "README.md", REPO / "examples" / "README.ko.md",
        # 10/7 추가: 공개 뒤 기여자·신고자가 처음 따라 하는 문서
        REPO / "CONTRIBUTING.md", REPO / "SECURITY.md", REPO / "docs" / "RELEASING.md",
        REPO / ".github" / "pull_request_template.md", *sorted((REPO / ".github" / "ISSUE_TEMPLATE").glob("*.md")),
        # 10/10 추가: 공개 뒤 spikes/ 를 본체로 오해하지 않게 붙인 설명
        REPO / "spikes" / "README.md"]

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
        """GUIDE.md#<anchor> links point at real GUIDE headings (GitHub slug rules).

        `GUIDE.md#<앵커>` 링크가 GUIDE 의 실제 제목을 가리키는지(GitHub 방식: 소문자, 구두점 삭제, 공백 → -)."""
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

    def test_roadmap_anchors_exist(self):
        """ROADMAP.md#<anchor> links in GUIDE "Known gaps" point at real ROADMAP headings.

        GUIDE "Known gaps" 의 `ROADMAP.md#<앵커>` 링크(한국어 절 제목)가 실제 ROADMAP 제목을 가리키는지."""
        def slug(h):
            return re.sub(r"[^\w\- ]", "", h.strip().lower()).replace(" ", "-")
        heads = {slug(ln.lstrip("#")) for ln in (REPO / "docs" / "ROADMAP.md").read_text(encoding="utf-8").splitlines()
                 if ln.startswith("#")}
        links = re.findall(r"\]\(ROADMAP\.md#([^)\s]+)\)", (REPO / "docs" / "GUIDE.md").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(links), 5)
        for anchor in links:
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, heads)

    def test_guide_has_no_korean_outside_link_targets(self):
        """GUIDE is English: no Hangul outside the targets of links into the Korean ROADMAP.

        GUIDE 는 영어 문서다 — 한국어 ROADMAP 을 가리키는 링크 주소 말고는 한글이 없어야 한다(10/9 3회차까지 6곳)."""
        text = re.sub(r"\]\([^)\s]+\)", "]()", (REPO / "docs" / "GUIDE.md").read_text(encoding="utf-8"))
        self.assertEqual([], [ln for ln in text.splitlines() if re.search(r"[가-힣]", ln)])


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


def all_tests():
    """tests/test_*.py 의 시험 전부(unittest 로더가 실제로 도는 것)."""
    def flat(suite):
        for t in suite:
            yield from (flat(t) if isinstance(t, unittest.TestSuite) else [t])
    loader = unittest.TestLoader()
    return [t for p in sorted((REPO / "tests").glob("test_*.py")) for t in flat(loader.loadTestsFromName(f"tests.{p.stem}"))]


def needs_blender(t):
    # 클래스에 붙인 것과 메서드 하나에 붙인 것 둘 다 센다
    return bool(getattr(type(t), "_requires_blender", False)
                or getattr(getattr(t, t._testMethodName), "_requires_blender", False))


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
        """The `Ran N tests ... (skipped=M)` sample in CONTRIBUTING matches the current counts.

        CONTRIBUTING 의 `Ran N tests ... (skipped=M)` 예시가 지금 시험 수·블렌더 시험 수와 같은지."""
        m = re.search(r"Ran (\d+) tests \.\.\. OK \(skipped=(\d+)\)", (REPO / "CONTRIBUTING.md").read_text(encoding="utf-8"))
        self.assertIsNotNone(m)
        tests = all_tests()
        self.assertEqual(int(m.group(1)), len(tests))
        self.assertEqual(int(m.group(2)), sum(map(needs_blender, tests)))

    def test_bare_unittest_discovers_every_test(self):
        """Bare `python3 -m unittest` discovers the same tests as the seven named modules.

        인자 없는 `python3 -m unittest`(저장소 맨 위에서 발견)가 명시한 7개 묶음과 같은 시험을 돈다 — 0개로 끝나지 않게."""
        def flat(suite):
            for t in suite:
                yield from (flat(t) if isinstance(t, unittest.TestSuite) else [t])
        found = unittest.TestLoader().discover(str(REPO), top_level_dir=str(REPO))
        self.assertEqual(sorted(t.id() for t in all_tests()), sorted(t.id() for t in flat(found)))

    def test_verbose_test_names_are_english(self):
        """The line `unittest -v` prints next to each test name (first docstring line) is English.

        CI 는 `-v` 로 돌아 docstring 첫 줄을 찍는다 — 10/9 3회차까지 156개 중 65개가 한국어라 영어 기여자가
        CI 로그에서 무엇이 깨졌는지 못 읽었다. 한국어 설명은 둘째 단락부터."""
        korean = [t.id() for t in all_tests() if re.search("[가-힣]", t.shortDescription() or "")]
        self.assertEqual([], korean, "→ put an English first line, then a blank line, then the Korean explanation")

    def test_tests_readme_table_is_current(self):
        """Per-module counts, Blender column and skip count in tests/README.md match the loader.

        tests/README.md 표의 묶음별 시험 수·블렌더 칸과 '없으면 N개 건너뜀' 이 실제 로더와 같은지
        (10/9 에 시험 9개를 더할 때 CONTRIBUTING 은 시험이 잡았는데 이 표는 아무도 안 잡았다)."""
        text = (REPO / "tests" / "README.md").read_text(encoding="utf-8")
        tests = all_tests()
        rows = []
        for line in text.splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) == 4 and cells[0].startswith("`tests.test_"):
                names = re.findall(r"`(\w+(?:\.\w+)?)`", cells[0])
                rows.append((names[0].split(".")[1], names[1:], "나머지" in cells[0], cells[1], int(cells[2])))
        self.assertGreater(len(rows), 5, "표 읽기가 망가졌다")
        self.assertEqual(sorted({r[0] for r in rows}), sorted({t.__module__.split(".")[-1] for t in tests}),
                         "표에 없는(또는 없어진) 시험 모듈")
        for mod, classes, rest, need, count in rows:
            others = {c for r in rows if r[0] == mod and not r[2] for c in r[1]}
            mine = [t for t in tests if t.__module__.endswith(mod)
                    and (not others or (type(t).__name__ not in others if rest else type(t).__name__ in classes))]
            blender = sum(map(needs_blender, mine))
            with self.subTest(row=f"{mod} {'나머지' if rest else ' '.join(classes)}"):
                self.assertEqual(count, len(mine))
                if "불필요" in need:
                    self.assertEqual(blender, 0)
                elif "일부" in need:
                    self.assertTrue(0 < blender < len(mine))
                else:
                    self.assertEqual(blender, len(mine))
        summary = "\n".join(ln for ln in text.splitlines() if ln.startswith(">"))
        self.assertIn(f"{sum(map(needs_blender, tests))} Blender tests skip", summary)   # 영어 요약의 건너뜀 수
        glossary = re.sub(r"(불필요|필요|일부) = (yes|no|some)", "", summary)   # 표 칸 낱말 풀이만 한국어
        self.assertIsNone(re.search(r"[가-힣]", glossary), glossary)
        m = re.search(r"없으면 (\d+)개 건너뜀", text)
        self.assertIsNotNone(m)
        self.assertEqual(int(m.group(1)), sum(map(needs_blender, tests)))



class CodePointsAtDocsTests(unittest.TestCase):
    def test_guide_sections_named_in_messages_exist(self):
        """GUIDE sections that error and doctor messages name by title actually exist.

        오류·doctor 문구가 `"<절 제목>" ... docs/GUIDE.md` 로 가리키는 절이 GUIDE 에 실제로 있는지."""
        heads = {ln.lstrip("#").strip() for ln in (REPO / "docs" / "GUIDE.md").read_text(encoding="utf-8").splitlines()
                 if ln.startswith("#")}
        named = set()
        for p in (REPO / "bonewright").rglob("*.py"):
            for line in p.read_text(encoding="utf-8").splitlines():
                if "docs/GUIDE.md" in line or "{guide()}" in line:   # 14회차부터 위치는 config.guide()
                    named |= set(re.findall(r'\\"([^"\\]+)\\"', line))
        self.assertTrue(named)
        for title in named:
            with self.subTest(title=title):
                self.assertTrue(any(h.startswith(title) for h in heads), f"GUIDE 에 '{title}' 절이 없다")

    def test_guide_sections_named_in_docs_exist(self):
        """GUIDE sections that docs and templates name by title actually exist.

        이슈 템플릿 등이 `docs/GUIDE.md` → "<절 제목>" 으로 가리키는 절이 GUIDE 에 실제로 있는지."""
        heads = {ln.lstrip("#").strip() for ln in (REPO / "docs" / "GUIDE.md").read_text(encoding="utf-8").splitlines()
                 if ln.startswith("#")}
        named = [(doc, t) for doc in DOCS for t in re.findall(r'docs/GUIDE\.md`?\s*→\s*"([^"]+)"', doc.read_text(encoding="utf-8"))]
        self.assertTrue(named, "feature-request 템플릿의 \"Which flag do I want?\" 를 못 뽑았다")
        for doc, title in named:
            with self.subTest(doc=doc.name, title=title):
                self.assertTrue(any(h.startswith(title) for h in heads), f"GUIDE 에 '{title}' 절이 없다")

    def test_issue_config_links_point_at_repo_files(self):
        """blob/main/<path> links in the issue template config point at files in the repository.

        `.github/ISSUE_TEMPLATE/config.yml` 의 `blob/main/<경로>` 안내 링크가 저장소에 있는 파일인지."""
        text = (REPO / ".github" / "ISSUE_TEMPLATE" / "config.yml").read_text(encoding="utf-8")
        paths = re.findall(r"/blob/main/(\S+)", text)
        self.assertTrue(paths)
        for rel in paths:
            with self.subTest(path=rel):
                self.assertTrue((REPO / rel).is_file(), f"config.yml → {rel} 없음")

    def test_messages_do_not_point_at_dated_research_notes(self):
        """Code messages do not point at dated research notes (docs/research-*.html).

        날짜 붙은 연구 노트(docs/research-*.html)는 공개용 안내가 아니다 — 코드 문구가 가리키지 않는다."""
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

    def test_install_starts_from_nothing(self):
        """Install starts with the clone (First run uses files inside it), then a venv, and says what doctor checks.

        10/10 6회차: `pip install .` 앞에 저장소를 받는 줄이 없었고, macOS Homebrew 파이썬은 venv 없이 PEP 668 로
        거절하며, doctor 주석은 doctor 가 보지 않는 Rigify 를 확인한다고 적었다."""
        for doc, install, _ in (self.EN, self.KO):
            with self.subTest(doc=doc.name):
                cmds = section_commands(doc, install)
                self.assertTrue(cmds[0].startswith("git clone ") and cmds[0].endswith("&& cd bonewright"), cmds[0])
                self.assertIn(cmds[0].split()[2], (REPO / "pyproject.toml").read_text(encoding="utf-8"))   # Homepage 와 같은 주소
                self.assertTrue(cmds[1].startswith("python3 -m venv .venv"), cmds[1])
                self.assertLess(cmds.index("python3 -m venv .venv && source .venv/bin/activate"), cmds.index("pip install ."))
                doctor_line = next(ln for ln in doc.read_text(encoding="utf-8").splitlines() if ln.startswith("bw doctor "))
                self.assertNotIn("Rigify", doctor_line)

    def test_first_command_needs_no_model(self):
        """The first `bw rig` in "First run" runs on a file in the repository with 0 model calls (no codex needed).

        10/10 4회차: 첫 명령 `bw rig character.glb` 는 codex 설치·로그인·약 $1 이 있어야 결과가 나왔다.
        `--from-skeleton`·`--from-shape` 는 맞춤 호출만 건너뛰고 시각 판정은 그대로라 `--no-judge` 도 있어야 0 토큰이다."""
        for doc, _, first in (self.EN, self.KO):
            with self.subTest(doc=doc.name):
                cmd = next(c for c in section_commands(doc, first) if c.startswith("bw rig "))
                words = cmd.split()
                self.assertTrue((REPO / words[2]).is_file(), f"{words[2]} 가 저장소에 없다")
                self.assertIn("--no-judge", words)
                self.assertTrue({"--from-skeleton", "--from-shape"} & set(words), cmd)

    def test_quickstart_commands_parse(self):
        parser = cli.build_parser()
        for doc, install, first in (self.EN, self.KO):
            for cmd in section_commands(doc, install) + section_commands(doc, first):
                if cmd.startswith("bw "):
                    with self.subTest(doc=doc.name, cmd=cmd):
                        self.assertIsNone(check_command(parser, cmd))

    def test_settings_line_matches_between_languages(self):
        """The settings line in both READMEs parses the same, uses real keys and links to GUIDE Settings.

        두 README 의 설정 한 줄: 같은 예시 JSON 이 읽히고, 그 키가 실제 기본 설정에 있고, GUIDE Settings 로 링크한다
        (README 에 config.json 이 안 나오면 영어 사용자가 매번 `--lang` 을 붙여야 하는 줄 안다)."""
        import json
        import tempfile
        from bonewright import config
        examples = []
        for doc in (self.EN[0], self.KO[0]):
            text = doc.read_text(encoding="utf-8")
            with self.subTest(doc=doc.name):
                self.assertIn("runs/config.json", text)
                self.assertIn("](docs/GUIDE.md#settings-runsconfigjson)", text)
                found = re.findall(r"`(\{[^`]*\})`", text)
                self.assertTrue(found, "설정 예시 JSON 이 없다")
                examples.append(found)
        self.assertEqual(examples[0], examples[1], "두 README 의 설정 예시가 다르다")
        for ex in examples[0]:
            with tempfile.TemporaryDirectory() as d:
                (Path(d) / "runs").mkdir()
                (Path(d) / "runs" / "config.json").write_text(ex, encoding="utf-8")
                self.assertIsInstance(json.loads(ex), dict)
                self.assertEqual(config.unknown_keys(Path(d)), [], f"README 예시에 모르는 키: {ex}")

    def test_install_extras_exist(self):
        """Install extras named in the README (e.g. .[headless]) exist in pyproject.

        README 의 `pip install ".[headless]"` 같은 추가 묶음이 pyproject 에 있는지."""
        import tomllib
        extras = set(tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))["project"].get("optional-dependencies", {}))
        for doc in (self.EN[0], self.KO[0]):
            for extra in re.findall(r'pip install "?\.\[(\w+)\]', doc.read_text(encoding="utf-8")):
                with self.subTest(doc=doc.name, extra=extra):
                    self.assertIn(extra, extras)

    def test_readme_bone_counts_match_sample_output(self):
        """README bone counts and the sample-output capsule doll come from the same human metarig.

        README 의 '본 410(변형 73)'(mannequiny)과 sample-output 의 캡슐 인형 숫자는 같은 사람 메타리그에서 나온다.
        리그 구성이 바뀌면 둘 다 바뀌어야 한다 — 한쪽만 고치면 여기서 걸린다."""
        sample = (REPO / "examples" / "sample-output" / "capsule_doll.md").read_text(encoding="utf-8")
        m = re.search(r"rig bones (\d+) \(deform (\d+)\)", sample)
        self.assertIsNotNone(m)
        total, deform = m.groups()
        self.assertRegex((REPO / "README.md").read_text(encoding="utf-8"), rf"{total} bones \({deform} deform\)")
        self.assertRegex((REPO / "README.ko.md").read_text(encoding="utf-8"), rf"본 {total}개\(변형 본 {deform}개\)")
        self.assertIn(f"{deform} deform bones", (REPO / "examples" / "README.md").read_text(encoding="utf-8"))
        self.assertIn(f"변형 본 {deform}개", (REPO / "examples" / "README.ko.md").read_text(encoding="utf-8"))


class RetargetTableTests(unittest.TestCase):
    """GUIDE "Motion retargeting" 의 관절 → 컨트롤 표가 retarget.bvh_mapping 과 같은지. 10/9: 예시에서 `Spine` 이
    안 옮겨진 이유가 문서 어디에도 없어 처음 보는 사람이 실패로 읽었다 — 표가 코드와 어긋나면 같은 혼란이 다시 온다."""

    def test_guide_table_matches_bvh_mapping(self):
        from bonewright.retarget import bvh_mapping
        text = (REPO / "docs" / "GUIDE.md").read_text(encoding="utf-8")
        part = text.split("| Rig control | Mixamo-style names | kimodo-style names |", 1)[1].split("\n\n", 1)[0]
        rows = [[c.strip() for c in ln.strip("|").split("|")] for ln in part.splitlines()[1:] if ln.startswith("|")]
        self.assertGreaterEqual(len(rows), 12)
        for col, style in ((1, "Mixamo"), (2, "kimodo")):
            # 이름순이면 Spine < Spine1 < Spine2 로 실제 BVH 계층 순서와 같다(가슴 판정이 순서를 본다)
            names = sorted(n for r in rows for n in re.findall(r"`([^`]+)`", r[col]))
            got = bvh_mapping(names)
            for r in rows:
                want = re.match(r"`([^`]+)`", r[0])
                for n in re.findall(r"`([^`]+)`", r[col]):
                    with self.subTest(style=style, joint=n):
                        self.assertEqual(want[1] if want else None, got.get(n))


class AssetLicenceTests(unittest.TestCase):
    """자산 라이선스 표기는 영어 사용자가 가장 먼저 확인한다 — 10/9 까지 tests/assets/README 와 bench-assets/ATTRIBUTION.md 가 한국어뿐이었다."""

    def test_test_asset_licence_is_stated_in_english(self):
        text = (REPO / "tests" / "assets" / "README.md").read_text(encoding="utf-8")
        english = text.split("## 한국어", 1)[0]
        self.assertEqual([], re.findall(r"[가-힣]+", english))
        for asset in sorted((REPO / "tests" / "assets").glob("*.glb")):
            with self.subTest(asset=asset.name):
                line = next((ln for ln in english.splitlines() if asset.name in ln), "")
                self.assertRegex(line, r"CC0 1\.0|CC BY|MIT")   # 파일 이름 줄에 라이선스
        self.assertIn("Source: https://", english)

    def test_bench_attribution_is_english_and_complete(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("fetch_bench_assets", REPO / "scripts" / "fetch_bench_assets.py")
        fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)
        texts = [fb.ATTRIBUTION, *fb.SAMPLES.values(), *(lic for _, _, lic in fb.CHARACTERS.values()), *fb.UNRESOLVED.values()]
        for t in texts:
            self.assertEqual([], re.findall(r"[가-힣]+", t), t[:80])
        for name, (url, _, lic) in fb.CHARACTERS.items():
            with self.subTest(asset=name):
                self.assertRegex(lic, r"^(CC0 1\.0|CC BY 4\.0|MIT) ·")
                self.assertTrue(url.startswith("https://"))


class ExamplesReadmePairTests(unittest.TestCase):
    """examples/README.md(영어)와 README.ko.md 는 10/9 3회차에 한 파일을 둘로 나눴다 — 명령·링크를 한쪽만 고치면 갈라진다."""

    def parts(self, name):
        text = (REPO / "examples" / name).read_text(encoding="utf-8")
        cmds = [re.sub(r"<[^>]+>", "<>", ln.split("#")[0].strip()) for block in re.findall(r"```bash\n(.*?)```", text, re.S) for ln in block.splitlines()]
        links = sorted(set(re.findall(r"\]\(([^)\s]+)\)", text)) - {"README.md", "README.ko.md"})
        table = text.split("| part | count | names |", 1)[1]
        return cmds, links, table

    def test_commands_links_and_table_match(self):
        en, ko = self.parts("README.md"), self.parts("README.ko.md")
        self.assertGreater(len(en[0]), 5)
        self.assertEqual(en[0], ko[0], "코드 블록 명령")
        self.assertEqual(en[1], ko[1], "링크")
        self.assertEqual(en[2], ko[2], "입력 예 표")


class StaleVersionClaimTests(unittest.TestCase):
    """"planned for v0.2" 처럼 이미 지난 버전에 무엇이 온다고 적은 문장(10/9 3회차 addon/README — 0.2.0 이 나왔는데 add-on 은 없다)."""

    def test_no_plan_for_a_released_version(self):
        from bonewright import __version__
        now = tuple(int(x) for x in __version__.split(".")[:2])
        for doc in (REPO / "addon" / "README.md", REPO / "bonewright" / "bpy_scripts" / "README.md", REPO / "README.md"):
            for m in re.finditer(r"(?:planned|coming|arrives?|lands?) (?:for|in) v?(\d+)\.(\d+)", doc.read_text(encoding="utf-8")):
                with self.subTest(doc=str(doc.relative_to(REPO)), claim=m.group(0)):
                    self.assertGreater((int(m.group(1)), int(m.group(2))), now)


class SettingsChecksDocTests(unittest.TestCase):
    def test_guide_examples_of_refused_values_are_refused(self):
        """The refused settings values the guide quotes (`"lang": "fr"`, `"rest_pose": "T"`) really are refused by the checks."""
        from bonewright import config
        text = (REPO / "docs" / "GUIDE.md").read_text(encoding="utf-8")
        self.assertIn('`"lang": "fr"`', text); self.assertIn('`"rest_pose": "T"`', text)
        self.assertTrue(config.choice_problems({"lang": "fr"}))
        self.assertTrue(config.choice_problems({"rig": {"rest_pose": "T"}}))
        self.assertTrue(config.type_problems({"budget": {"max_input_tokens": "lots"}}))

    def test_guide_run_id_rule_matches_the_parser(self):
        """The run-id rule in the guide is what `--run-id` accepts and refuses."""
        import argparse
        text = (REPO / "docs" / "GUIDE.md").read_text(encoding="utf-8")
        self.assertIn("`--run-id` takes letters, digits and `. _ -` only", text)
        for ok in ("rig-20261010-101500", "hero_v2.1"):
            self.assertEqual(ok, cli.run_id_arg(ok))
        for bad in ("a/b", "a\\b", "..", "x y"):
            with self.subTest(bad=bad), self.assertRaises(argparse.ArgumentTypeError):
                cli.run_id_arg(bad)


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


class CodeOfConductTests(unittest.TestCase):
    """행동 강령 초안(`docs/drafts/`)을 루트로 옮길 때 연락 칸을 비운 채 공개하지 않도록. docs/CODE-OF-CONDUCT-PLAN.md"""

    def test_root_code_of_conduct_has_a_contact(self):
        coc = REPO / "CODE_OF_CONDUCT.md"
        if coc.exists():   # 아직 결정 대기면 통과(건너뜀으로 세면 CONTRIBUTING 의 '블렌더 시험 수' 예시가 흐려진다)
            self.assertNotIn("[INSERT CONTACT METHOD]", coc.read_text(encoding="utf-8"))

    def test_draft_keeps_the_attribution(self):
        """The Code of Conduct draft keeps the CC BY 4.0 Attribution section.

        Contributor Covenant 는 CC BY 4.0 — 끝의 Attribution 절이 출처 표기다."""
        for doc in (REPO / "docs" / "drafts" / "CODE_OF_CONDUCT.md", REPO / "CODE_OF_CONDUCT.md"):
            if doc.exists():
                with self.subTest(doc=str(doc.relative_to(REPO))):
                    self.assertIn("## Attribution", doc.read_text(encoding="utf-8"))
                    self.assertIn("contributor-covenant.org/version/2/1", doc.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()


class SettingsTableTests(unittest.TestCase):
    """GUIDE "Settings (`runs/config.json`)" 표의 기본값이 `config.DEFAULTS` 와 같은지(10/8 2회차).
    프롬프트 언어 우선순위에 config 가 끼었는데 적힌 곳이 CHANGELOG 뿐이었다."""
    ROW = re.compile(r"^\| `([\w.]+)` \| `([^`]*)` \|", re.M)

    def test_settings_defaults_match_config(self):
        import json
        from bonewright.config import DEFAULTS
        text = (REPO / "docs" / "GUIDE.md").read_text(encoding="utf-8")
        section = text.split("### Settings (`runs/config.json`)", 1)[1].split("\n#", 1)[0]
        rows = self.ROW.findall(section)
        self.assertGreaterEqual(len(rows), 8)
        for key, shown in rows:
            with self.subTest(key=key):
                val = DEFAULTS
                for part in key.split("."):
                    self.assertIn(part, val, f"DEFAULTS 에 없는 키 {key}")
                    val = val[part]
                self.assertEqual(json.loads(shown), val)

    def test_settings_example_is_valid_json_with_known_keys(self):
        import json
        from bonewright.config import DEFAULTS
        text = (REPO / "docs" / "GUIDE.md").read_text(encoding="utf-8")
        section = text.split("### Settings (`runs/config.json`)", 1)[1].split("\n#", 1)[0]
        example = json.loads(re.search(r"```json\n(.*?)```", section, re.S).group(1))
        for sec, v in example.items():
            self.assertIn(sec, DEFAULTS)
            for k in (v if isinstance(v, dict) else {}):
                self.assertIn(k, DEFAULTS[sec])


class IssueTemplateTests(unittest.TestCase):
    """이슈 템플릿마다 name·about·labels 머리말이 있고, CONTRIBUTING 이 모든 템플릿 이름을 든다(10/8 2회차: 문서 오류 템플릿 추가).
    9/20·10/7 문서 감사에서 실제와 다른 주장이 11개·1개 나왔다 — 공개 뒤 흔한 첫 기여가 문서 지적이다."""
    def test_templates_have_front_matter_and_are_listed(self):
        contributing = " ".join((REPO / "CONTRIBUTING.md").read_text(encoding="utf-8").split())
        templates = sorted((REPO / ".github" / "ISSUE_TEMPLATE").glob("*.md"))
        self.assertIn("docs-problem.md", [t.name for t in templates])
        for t in templates:
            with self.subTest(template=t.name):
                head = re.match(r"---\n(.*?)\n---\n", t.read_text(encoding="utf-8"), re.S)
                self.assertIsNotNone(head, "머리말(---) 없음")
                fields = dict(line.split(":", 1) for line in head.group(1).splitlines() if ":" in line)
                for key in ("name", "about", "labels"):
                    self.assertTrue(fields.get(key, "").strip(), f"{key} 비어 있음")
                self.assertIn(f"*{fields['name'].strip()}*", contributing)
