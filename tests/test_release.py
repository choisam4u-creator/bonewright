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


if __name__ == "__main__":
    unittest.main()
