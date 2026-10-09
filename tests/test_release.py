"""릴리스 준비 점검: 버전 문자열 세 곳과 CHANGELOG 가 맞는지. 블렌더 불필요(docs/RELEASING.md)."""
import json
import re
import tomllib
import unittest
from pathlib import Path

import bonewright

ROOT = Path(__file__).resolve().parents[1]


class VersionTests(unittest.TestCase):
    def setUp(self):
        self.version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]

    def test_versions_agree(self):
        plugin = json.loads((ROOT / "plugin/.codex-plugin/plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(bonewright.__version__, self.version, "bonewright/__init__.py 와 pyproject.toml 버전을 맞춰라")
        self.assertEqual(plugin["version"], self.version, "plugin/.codex-plugin/plugin.json 버전을 pyproject.toml 과 맞춰라")

    def test_changelog_has_current_version_and_links(self):
        text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        heads = re.findall(r"^## \[([^\]]+)\]", text, re.M)
        self.assertEqual(heads[0], "Unreleased", "CHANGELOG 맨 위는 [Unreleased] 여야 한다")
        self.assertIn(self.version, heads, f"CHANGELOG 에 [{self.version}] 절이 없다 — docs/RELEASING.md 2단계")
        self.assertEqual(len(heads), len(set(heads)), "CHANGELOG 에 같은 버전 절이 두 번 있다")
        for h in heads:
            self.assertRegex(text, rf"(?m)^\[{re.escape(h)}\]: https://", f"CHANGELOG 맨 아래에 [{h}] 링크가 없다")


    def test_fetch_script_user_agent_follows_version(self):
        """`fetch_bench_assets.py` 의 User-Agent 는 원배포처가 보는 이름 — 손으로 박은 0.2 가 0.3.0 에서 어긋났다(10/9 3회차)."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("fetch_bench_assets", ROOT / "scripts" / "fetch_bench_assets.py")
        fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)
        homepage = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["urls"]["Homepage"]
        self.assertEqual(f"bonewright-bench-fetch/{self.version} (+{homepage})", fb.UA["User-Agent"])

class ReleasingSummaryTests(unittest.TestCase):
    """영어 CHANGELOG 가 "See docs/RELEASING.md" 로 가리킨다 — 맨 위 영어 요약이 있고, 버전 세 곳이 위 시험과 같은지(10/9 3회차)."""

    def test_english_summary_names_the_checked_files(self):
        import re
        text = (ROOT / "docs" / "RELEASING.md").read_text(encoding="utf-8")
        summary = "\n".join(ln for ln in text.splitlines() if ln.startswith(">"))
        self.assertIn("English summary", summary)
        self.assertIsNone(re.search(r"[가-힣]", summary), summary)
        for f in ("pyproject.toml", "bonewright/__init__.py", "plugin/.codex-plugin/plugin.json", "[Unreleased]"):
            self.assertIn(f, summary)

class ProposedVersionTests(unittest.TestCase):
    """`[Unreleased]` 첫 줄의 다음 버전 제안이 docs/RELEASING.md 의 표와 어긋나지 않게.
    10/7 까지 "0.2.1 — fixes only" 라 적힌 채 새 플래그가 쌓였다."""

    def test_proposal_is_ahead_and_matches_the_table(self):
        text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        body = text.split("## [Unreleased]", 1)[1].split("\n## [", 1)[0]
        m = re.search(r"Proposed next version: \*\*(\d+)\.(\d+)\.(\d+)\*\*(.*?)(?:\n\n|$)", body, re.S)
        self.assertIsNotNone(m, "[Unreleased] 첫 줄에 'Proposed next version: **X.Y.Z**' 가 없다")
        proposed = tuple(int(x) for x in m.groups()[:3])
        current = tuple(int(x) for x in bonewright.__version__.split("."))
        self.assertGreater(proposed, current, "제안 버전이 지금 버전보다 커야 한다")
        if proposed[:2] == current[:2]:   # 셋째 자리만 올리면 새 옵션·기본값 변경이 없어야 한다
            self.assertNotRegex(m.group(4), r"(?i)new flag|changed default", "새 플래그·기본값 변경은 둘째 자리(RELEASING.md 표)")


class PackageMetadataTests(unittest.TestCase):
    """배포본(sdist·wheel)에 두 라이선스 고지가 실리고 PyPI 페이지에 저장소 링크가 뜨게."""

    def setUp(self):
        self.project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]

    def test_license_files_exist(self):
        files = self.project.get("license-files", [])
        self.assertIn("LICENSE", files)
        self.assertIn("bonewright/bpy_scripts/LICENSE", files, "bpy_scripts 의 GPL 고지가 배포본에서 빠진다")
        for f in files:
            self.assertTrue((ROOT / f).is_file(), f"license-files 의 {f} 가 없다")

    def test_project_urls(self):
        urls = self.project.get("urls", {})
        for key in ("Homepage", "Issues", "Changelog"):
            self.assertRegex(urls.get(key, ""), r"^https://", f"[project.urls] 에 {key} 가 없다")


class WorkflowActionTests(unittest.TestCase):
    """CI 가 Node 20 판 액션을 쓰지 않게(10/8 Windows 로그의 지원 종료 경고 — 강제 전환 뒤 깨질 수 있다)."""

    # Node 24 로 도는 첫 메이저
    MIN_MAJOR = {"actions/checkout": 5, "actions/setup-python": 6}

    def test_actions_run_on_node24(self):
        text = (ROOT / ".github" / "workflows" / "test.yml").read_text(encoding="utf-8")
        found = re.findall(r"uses:\s*([\w.-]+/[\w.-]+)@v(\d+)", text)
        self.assertTrue(found, "test.yml 에서 uses: 줄을 못 찾았다")
        for name, major in found:
            if name in self.MIN_MAJOR:
                self.assertGreaterEqual(int(major), self.MIN_MAJOR[name], f"{name}@v{major} 는 Node 20 판이다")

    def test_workflow_is_english(self):
        """공개 뒤 PR 기여자가 Actions 화면에서 보는 단계 이름·주석 — 10/9 3회차까지 한국어였다."""
        text = (ROOT / ".github" / "workflows" / "test.yml").read_text(encoding="utf-8")
        self.assertEqual([], [ln for ln in text.splitlines() if re.search(r"[가-힣]", ln)])


if __name__ == "__main__":
    unittest.main()
