"""오류 메시지 회귀 테스트: Blender 를 부르기 전에 막히고, 메시지에 '무엇을 바꾸면 되는지'(→)가 들어 있어야 한다. 블렌더 불필요."""
import contextlib
import io
import json
import os
import re
import shlex
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bonewright import cli, pipeline
from tests._marks import requires_blender



def split_pasted(cmd: str) -> list[str]:
    """Split a command the way the user's shell would: POSIX rules, or cmd/PowerShell rules on Windows.

    안내는 공백 있는 경로만 큰따옴표로 감싸고 역슬래시는 그대로 둔다(Windows 셸에선 그대로 돈다).
    POSIX shlex 는 C:\\Users 의 역슬래시를 지운다 — 10/13 CI unit-windows."""
    if os.name != "nt":
        return shlex.split(cmd)
    return [w[1:-1] if len(w) > 1 and w[0] == w[-1] == '"' else w for w in shlex.split(cmd, posix=False)]

class InputErrorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        lang = patch.dict(os.environ, {"BW_LANG": "ko"}); lang.start(); self.addCleanup(lang.stop)   # 문구 대조는 한국어로

    def tearDown(self):
        self.tmp.cleanup()

    def blocked(self, fn, *args, **kw) -> str:
        with patch.object(pipeline, "run_script", side_effect=AssertionError("Blender 를 부르면 안 된다")):
            with self.assertRaises(pipeline.Blocked) as cm:
                fn(*args, **kw)
        msg = str(cm.exception)
        self.assertIn("→", msg, msg)
        return msg

    def test_missing_mesh(self):
        msg = self.blocked(pipeline.rig, self.root, str(self.root / "없음.glb"), quiet=True)
        self.assertIn("메시 파일이 없다", msg)
        self.assertFalse((self.root / "runs").exists(), "빈 실행 폴더를 남기면 안 된다")

    def test_glb_under_another_extension_says_copy_it(self):
        """A .glb under another extension (VRM) gets a copy command and the same command on the copy.

        10/13 16회차 실측: `hero.vrm` 은 "export it as one of …" 뿐 — 다시 내보낼 것이 없다."""
        glb = b"glTF" + (2).to_bytes(4, "little") + (12).to_bytes(4, "little")
        (self.root / "my hero.vrm").write_bytes(glb)
        (self.root / "noext").write_bytes(glb)
        (self.root / "a.stl").write_bytes(b"solid a\n")
        vrm = str(self.root / "my hero.vrm")
        with patch.object(sys, "argv", ["bw", "rig", vrm, "--from-skeleton"]):
            msg = self.blocked(pipeline.rig, self.root, vrm, quiet=True)
            with patch.dict(os.environ, {"BW_LANG": "en"}):
                en = self.blocked(pipeline.rig, self.root, vrm, quiet=True)
        glbpath = f'"{self.root / "my hero.glb"}"'
        self.assertIn("glTF Binary(.glb)", msg); cp = "copy" if os.name == "nt" else "cp"
        self.assertIn(f'`{cp} "{vrm}" {glbpath}` 뒤 `bw rig {glbpath} --from-skeleton`', msg)
        self.assertIn(f", then `bw rig {glbpath} --from-skeleton`", en); self.assertNotIn("export it as", en)
        self.assertIn(str(self.root / "noext.glb"), self.blocked(pipeline.rig, self.root, str(self.root / "noext"), quiet=True))
        self.assertIn("내보내서", self.blocked(pipeline.rig, self.root, str(self.root / "a.stl"), quiet=True))   # glTF 가 아니면 그대로
        self.assertFalse((self.root / "runs").exists())

    def test_zip_says_unzip_and_names_the_mesh_inside(self):
        """A .zip given as the mesh names the mesh inside, an unzip command that runs anywhere and the same command on it.

        10/14 17회차 실측: `.glb` 하나 든 zip → "export it as one of …" 뿐 — 다시 내보낼 것이 아니라 풀면 된다."""
        import zipfile
        z = self.root / "my hero.zip"
        with zipfile.ZipFile(z, "w") as f:
            f.writestr("__MACOSX/scene/._hero.glb", b"x"); f.writestr("README.txt", "x")
            f.writestr("scene/hero.fbx", b"x"); f.writestr("scene/hero.glb", b"glTF")
        with zipfile.ZipFile(self.root / "empty.zip", "w") as f:
            f.writestr("a.usdz", b"x")
        for lang, then in (("ko", "` 뒤 `"), ("en", "`, then `")):
            with self.subTest(lang=lang), patch.dict(os.environ, {"BW_LANG": lang}), \
                    patch.object(sys, "argv", ["bw", "rig", str(z), "--from-skeleton"]):
                msg = self.blocked(pipeline.rig, self.root, str(z), quiet=True)
                self.assertIn("scene/hero.glb", msg.splitlines()[0])   # .glb 가 .fbx 보다 먼저, __MACOSX 는 빼고
                unzip, again = msg.splitlines()[-1].split("`")[1], msg.splitlines()[-1].split(then)[1].rstrip("`")
                self.assertEqual(["-m", "zipfile", "-e", str(z), str(self.root / "my hero")], split_pasted(unzip)[1:])
                zipfile.main(split_pasted(unzip)[3:])   # 안내의 풀기 명령을 그대로 — 그 뒤 같은 명령이 가리키는 파일이 있다
                cmd = split_pasted(again)
                a = cli.build_parser().parse_args(cmd[1:])
                self.assertTrue(Path(a.mesh).is_file(), a.mesh); self.assertTrue(a.from_skeleton)
                self.assertNotIn("export", msg); self.assertNotIn("내보내서", msg)
        msg = self.blocked(pipeline.rig, self.root, str(self.root / "empty.zip"), quiet=True)
        self.assertIn("a.usdz", msg)
        self.assertFalse((self.root / "runs").exists())

    def test_readme_example_name_points_at_the_shipped_character(self):
        """The README's placeholder name (`bw rig character.glb`) says so and gives the first-run command that works.

        10/14 17회차 실측: README "First run" 둘째 줄을 그대로 치면 "check the path" 뿐."""
        cwd = os.getcwd()
        try:
            os.chdir(self.root)   # 저장소 밖 폴더 — 안내의 첫 명령은 저장소 캐릭터의 절대 경로
            for lang, want in (("ko", "README 의 예시 이름"), ("en", "example name from the README")):
                with self.subTest(lang=lang), patch.dict(os.environ, {"BW_LANG": lang}):
                    msg = self.blocked(pipeline.rig, self.root, "character.glb", quiet=True)
                    self.assertIn(want, msg)
                    cmd = split_pasted(msg.splitlines()[-1].split("`")[-2])
                    a = cli.build_parser().parse_args(cmd[1:])
                    self.assertTrue(Path(a.mesh).is_file(), a.mesh); self.assertTrue(a.no_judge)
            (self.root / "Character.glb").write_bytes(b"glTF")   # 비슷한 파일이 있으면 그 안내가 먼저 — 예시 이름 말은 없다
            if not (self.root / "character.glb").exists():
                self.assertNotIn("README", self.blocked(pipeline.rig, self.root, "character.glb", quiet=True))
            self.assertNotIn("README", self.blocked(pipeline.rig, self.root, "nosuch.glb", quiet=True))
        finally:
            os.chdir(cwd)

    def test_missing_file_names_the_similar_one_beside_it(self):
        """A missing mesh, --bvh or --targets names the file beside it that differs in case, extension or a typo.

        10/12 13회차 실측: 옆에 Hero.glb 를 두고 `bw rig hero.glb`·`bw rig Hero`·`bw rig Hero.gltf` → '경로를 확인하라' 뿐."""
        d = self.root / "my dir"
        d.mkdir()
        (d / "Hero.glb").write_bytes(b"glTF")
        (d / "walk.bvh").write_text("HIERARCHY\n")
        (d / "targets.json").write_text("{}")
        case_blind = (d / "hero.glb").exists()
        near = lambda rel: f'"{Path(rel)}"'   # 안내는 그 OS 의 구분자로 적는다(Windows 는 my dir\\Hero.glb)
        cwd = os.getcwd()
        try:
            os.chdir(self.root)   # 준 꼴(상대 경로·공백 → 따옴표) 그대로 돌려주는지
            for lang in ("ko", "en"):
                with patch.dict(os.environ, {"BW_LANG": lang}):
                    for typed in ("my dir/hero.glb", "my dir/Hero", "my dir/Hero.gltf", "my dir/Heroo.glb"):
                        if typed == "my dir/hero.glb" and case_blind:
                            continue   # 대소문자를 안 가리는 파일 시스템(Windows·macOS 기본)에선 hero.glb 가 Hero.glb 로 열린다
                        with self.subTest(lang=lang, typed=typed):
                            msg = self.blocked(pipeline.rig, self.root, typed, quiet=True)
                            self.assertIn(pipeline.T('비슷한 파일', 'similar file'), msg)
                            self.assertIn(near("my dir/Hero.glb"), msg)
                    with self.subTest(lang=lang, flag="--bvh"):
                        self.assertIn(near("my dir/walk.bvh"), self.blocked(pipeline.motion, self.root, bvh="my dir/Wakl.bvh" if case_blind else "my dir/Walk.bvh"))
                    with self.subTest(lang=lang, flag="--targets"):
                        self.assertIn(near("my dir/targets.json"), self.blocked(pipeline.rig, self.root, "my dir/Hero.glb", targets_file="my dir/target.json", quiet=True))
                    with self.subTest(lang=lang, case="nothing alike"):
                        self.assertNotIn(pipeline.T('비슷한 파일', 'similar file'), self.blocked(pipeline.rig, self.root, "my dir/zzz.glb", quiet=True))
        finally:
            os.chdir(cwd)
        self.assertFalse((self.root / "runs").exists(), "빈 실행 폴더를 남기면 안 된다")

    def test_folder_instead_of_mesh(self):
        """A folder passed as the mesh says so, names a mesh inside and points at `bw bench`.

        `bw rig .` 이 "메시 파일이 없다: ." 라 했다(폴더는 있다, 10/10 8회차)."""
        d = self.root / "models"; d.mkdir()
        (d / "hero.glb").write_bytes(b"glTF"); (d / "notes.txt").write_text("x")
        msg = self.blocked(pipeline.rig, self.root, str(d), quiet=True)
        self.assertIn("폴더를 줬다", msg); self.assertNotIn("파일이 없다", msg)
        self.assertIn("hero.glb", msg); self.assertNotIn("notes.txt", msg)
        self.assertIn(f"bw bench {d}", msg)
        self.assertFalse((self.root / "runs").exists(), "빈 실행 폴더를 남기면 안 된다")
        with patch.dict(os.environ, {"BW_LANG": "en"}):
            self.assertIn("this is a folder, not a file", self.blocked(pipeline.rig, self.root, str(d), quiet=True))

    def test_empty_or_fake_glb_stops_before_blender(self):
        """An empty or non-glTF .glb is refused before Blender starts.

        0바이트 .glb 가 Blender 를 띄운 뒤에야 실패했다 — Blender 가 없는 곳에선 'Blender not found' 가 원인을 가렸다(10/10 8회차)."""
        empty, fake = self.root / "empty.glb", self.root / "fake.glb"
        empty.write_bytes(b""); fake.write_text("<html>not a model</html>")
        self.assertIn("비었다(0바이트)", self.blocked(pipeline.rig, self.root, str(empty), quiet=True))
        self.assertIn("GLB 가 아니다", self.blocked(pipeline.rig, self.root, str(fake), quiet=True))
        self.assertFalse((self.root / "runs").exists(), "빈 실행 폴더를 남기면 안 된다")

    def test_fake_gltf_fbx_blend_obj_stop_before_blender(self):
        """A .gltf/.fbx/.blend/.obj that does not start the way that format does is refused before Blender starts.

        10/12 14회차 실측: `echo hi > a.fbx` 가 Blender 단계까지 가서, Blender 가 없는 곳에선 'Blender not found' 가 원인을 가렸다."""
        html = b"<!DOCTYPE html><html>not a model</html>"
        for name, bad, good in (("a.gltf", html, b'\xef\xbb\xbf\n  {"asset": {"version": "2.0"}}'),
                                ("a.fbx", b"hi\n", b"; FBX 7.4.0 project file\n"),
                                ("b.fbx", b"\x00\x01binary junk", b"Kaydara FBX Binary  \x00\x1a\x00"),
                                ("a.blend", html, b"BLENDER-v402REND"),
                                ("z.blend", b"PK\x03\x04zip", b"\x28\xb5\x2f\xfdzstd"),
                                ("a.obj", b"\x4c\x01\x00\x00coff object", b"# Blender OBJ\nv 0 0 0\n")):
            with self.subTest(name=name):
                f = self.root / name
                f.write_bytes(bad)
                msg = self.blocked(pipeline.rig, self.root, str(f), quiet=True)
                self.assertIn("파일이 아니다", msg); self.assertIn(f"{Path(name).suffix} 로 다시 내보내라", msg)
                with patch.dict(os.environ, {"BW_LANG": "en"}):
                    self.assertIn("Export it again as", self.blocked(pipeline.rig, self.root, str(f), quiet=True))
                f.write_bytes(good)
                pipeline.need_mesh_bytes(f)
        self.assertFalse((self.root / "runs").exists(), "빈 실행 폴더를 남기면 안 된다")

    def test_mesh_given_as_bvh_says_rig_it(self):
        """`bw motion --bvh hero.glb` names the one format it reads and says a mesh goes to `bw rig`, as pasted.

        10/12 14회차 실측: "export it as one of .bvh" 뿐 — 확장자 하나에 'one of', 메시를 잘못 준 경우의 다음 할 일이 없었다."""
        for name in ("hero.glb", "my hero.fbx"):
            f = self.root / name
            f.write_bytes(b"glTF")
            with self.subTest(name=name):
                with patch.dict(os.environ, {"BW_LANG": "en"}):
                    msg = self.blocked(pipeline.motion, self.root, bvh=str(f), rig_run="r1", quiet=True)
                self.assertIn("export it as .bvh and pass that", msg); self.assertNotIn("one of", msg)
                cmd = re.search(r"`(bw rig [^`]+)`", msg).group(1)
                from bonewright import cli
                self.assertEqual(str(f), cli.build_parser().parse_args(split_pasted(cmd)[1:]).mesh)
                self.assertIn("wave.bvh", msg)
                ko = self.blocked(pipeline.motion, self.root, bvh=str(f), rig_run="r1", quiet=True)
                self.assertIn(".bvh 로 내보내서", ko); self.assertIn("이건 메시다", ko)
        f = self.root / "notes.txt"; f.write_text("x")
        self.assertNotIn("bw rig", self.blocked(pipeline.motion, self.root, bvh=str(f), rig_run="r1", quiet=True))
        self.assertFalse((self.root / "runs").exists(), "빈 실행 폴더를 남기면 안 된다")

    def test_empty_or_fake_bvh_stops_before_blender(self):
        """An empty .bvh or one that does not start with HIERARCHY is refused before the run folder and Blender.

        10/11 10회차: 이름만 .bvh 인 웹 페이지가 확장자만 보고 Blender 가져오기까지 갔다. BOM·빈 줄 뒤의 HIERARCHY 는 그대로 된다."""
        empty, fake, bom = self.root / "empty.bvh", self.root / "fake.bvh", self.root / "bom.bvh"
        empty.write_bytes(b""); fake.write_text("<!DOCTYPE html><html>not a motion</html>")
        bom.write_bytes(b"\xef\xbb\xbf\nHIERARCHY\nROOT Hips\n")
        self.assertIn("비었다(0바이트)", self.blocked(pipeline.motion, self.root, bvh=str(empty), rig_run="r1", quiet=True))
        msg = self.blocked(pipeline.motion, self.root, bvh=str(fake), rig_run="r1", quiet=True)
        self.assertIn("BVH 가 아니다", msg); self.assertIn("<!DOCTYPE", msg); self.assertIn("wave.bvh", msg)
        pipeline.need_bvh_bytes(bom); pipeline.need_bvh_bytes(Path(pipeline.__file__).resolve().parents[1] / "examples" / "wave.bvh")
        with patch.dict(os.environ, {"BW_LANG": "en"}):
            self.assertIn("not a BVH", self.blocked(pipeline.motion, self.root, bvh=str(fake), quiet=True))
        self.assertFalse((self.root / "runs").exists(), "빈 실행 폴더를 남기면 안 된다")

    def test_export_out_is_checked_before_blender(self):
        """`bw export --out` must be a .glb or a folder, checked before Blender starts.

        10/10 8회차: 폴더·.fbx 가 Blender 를 띄운 뒤에야 실패했다."""
        (self.root / "runs" / "r1").mkdir(parents=True); (self.root / "runs" / "r1" / "02_rigged.blend").write_bytes(b"x")
        self.assertIn("GLB 만 쓴다", self.blocked(pipeline.export_rig, self.root, "r1", out=str(self.root / "a.fbx"), quiet=True))
        self.assertIn("출력 폴더가 없다", self.blocked(pipeline.export_rig, self.root, "r1", out=str(self.root / "no" / "a.glb"), quiet=True))
        seen = {}
        def fake(name, params, *a, **k):
            seen.update(params)
            return {"bones": 1, "verts": 1, "verts_in_source": 1, "max_diff_cm": 0.0}
        out = self.root / "exports"; out.mkdir()
        with patch.object(pipeline, "run_script", side_effect=fake), patch.object(pipeline, "need_blender", lambda cfg: None):
            dst = pipeline.export_rig(self.root, "r1", out=str(out), quiet=True)
        self.assertEqual(out.resolve() / "r1.glb", dst); self.assertEqual(str(dst), seen["out"])

    def test_missing_map_stops_before_blender(self):
        """`bw motion --map` that does not exist (or is not JSON) stops before the BVH import.

        10/10 8회차: 없는 매핑 파일이 Blender 로 BVH 를 가져온 뒤에야 걸렸다."""
        (self.root / "runs" / "r1").mkdir(parents=True); (self.root / "runs" / "r1" / "02_rigged.blend").write_bytes(b"x")
        bvh = self.root / "w.bvh"; bvh.write_text("HIERARCHY\n")
        msg = self.blocked(pipeline.motion, self.root, bvh=str(bvh), rig_run="r1", bone_map=str(self.root / "nope.json"), quiet=True)
        self.assertIn("--map 파일이 없다", msg)
        self.assertEqual(["r1"], sorted(p.name for p in (self.root / "runs").iterdir()), "실행 폴더를 만들면 안 된다")

    def test_binary_targets_file_is_named_as_such(self):
        """A binary file passed to --targets (usually the mesh) is called binary, not "a broken comma"."""
        mesh = self.root / "a.glb"; mesh.write_bytes(b"glTF\x02\x00\x00\x00\xaa\xff\xfe")
        msg = self.blocked(pipeline.rig, self.root, str(mesh), targets_file=str(mesh), quiet=True)
        self.assertIn("바이너리", msg); self.assertNotIn("쉼표", msg); self.assertIn("runs/<id>/targets.json", msg)

    def test_settings_value_of_wrong_type(self):
        """A settings value of the wrong type (a string budget, a string where an object goes) stops before Blender, naming key and type.

        10/11 11회차: `{"budget": {"max_input_tokens": "lots"}}` 는 첫 모델 호출에서, `{"rig": "t"}` 는 rig 단계에서 TypeError 였다."""
        (self.root / "runs").mkdir()
        (self.root / "runs" / "config.json").write_text('{"budget": {"max_input_tokens": "lots"}, "rig": "t", "lang": "en"}', encoding="utf-8")
        msg = self.blocked(pipeline.rig, self.root, str(self.root / "a.glb"), quiet=True)
        self.assertIn("형이 틀렸다", msg)
        self.assertIn('budget.max_input_tokens: 숫자 (600000) ← 문자열 "lots"', msg)   # 한국어 화면이면 형 이름도 한국어
        with patch.dict(os.environ, {"BW_LANG": "en"}):
            self.assertIn('budget.max_input_tokens: number (600000) ← string "lots"',
                          self.blocked(pipeline.rig, self.root, str(self.root / "a.glb"), quiet=True))
        self.assertIn('rig: {...} ← 문자열 "t"', msg)
        self.assertNotIn("lang", msg.split("\n")[1])   # 맞는 값은 짚지 않는다
        (self.root / "runs" / "config.json").write_text('{"budget": {"max_input_tokens": 1000}, "rig": {"face": true}}', encoding="utf-8")
        from bonewright import config
        self.assertEqual([], config.type_problems({"budget": {"max_input_tokens": 1000, "price_input_per_m": 3}, "rig": {"face": True}}))

    def test_settings_value_not_allowed(self):
        """Settings values outside the command-line choices (`"lang": "fr"`, `"rest_pose": "T"`) stop with the allowed values."""
        (self.root / "runs").mkdir()
        (self.root / "runs" / "config.json").write_text('{"lang": "fr", "rig": {"rest_pose": "T", "weights": "auto"}}', encoding="utf-8")
        msg = self.blocked(pipeline.rig, self.root, str(self.root / "a.glb"), quiet=True)
        self.assertIn("쓸 수 없는 값", msg)
        self.assertIn('lang: "fr" → "" | "ko" | "en"', msg)
        self.assertIn('rig.rest_pose: "T" → "keep" | "t" ("t"?)', msg)
        self.assertNotIn("rig.weights", msg)
        from bonewright import cli, config
        for key, allowed in config.CHOICES.items():   # 명령줄 선택지와 같은지
            flag = "--" + key.split(".")[-1].replace("_", "-")
            act = [a for a in cli.build_parser()._subparsers._group_actions[0].choices["rig"]._actions if flag in a.option_strings][0]
            with self.subTest(key=key):
                self.assertEqual(set(act.choices), set(a for a in allowed if a))

    def test_targets_file_of_the_wrong_shape(self):
        """A --targets JSON of the wrong shape (a list, a bone without head/tail, two-number coordinates) stops before Blender."""
        mesh = self.root / "a.glb"; mesh.write_bytes(b"glTF")
        for body, want in (("[1, 2]", "객체가 아니다"), ('{"foo": 1}', "foo: head·tail 이 없다"),
                           ('{"spine": {"head": [0, 0]}}', "spine.head: 숫자 x,y,z 세 개"), ("{}", "본이 하나도 없다")):
            tf = self.root / "t.json"; tf.write_text(body, encoding="utf-8")
            with self.subTest(body=body):
                msg = self.blocked(pipeline.rig, self.root, str(mesh), targets_file=str(tf), quiet=True)
                self.assertIn(want, msg); self.assertIn("runs/<id>/targets.json", msg)
        self.assertEqual([], pipeline.targets_problems({"spine": {"head": [0, 0, 1], "tail": [0, 0, 1.2]}, "hand.L": {"tail": [1, 0, 1]}}))
        self.assertFalse((self.root / "runs").exists())

    def test_broken_settings_file(self):
        """A trailing comma in runs/config.json is reported as BLOCKED with line and column.

        runs/config.json 의 끝 쉼표가 '예상 못 한 오류 — 이슈를 열어라'로 끝나던 것(10/8 발견) → 줄·칸을 짚는 Blocked."""
        (self.root / "runs").mkdir()
        cfg = self.root / "runs" / "config.json"
        cfg.write_text('{"lang": "en",}', encoding="utf-8")
        msg = self.blocked(pipeline.rig, self.root, str(self.root / "a.glb"), quiet=True)
        self.assertIn("설정 파일이 JSON 이 아니다", msg)
        self.assertRegex(msg, r"1줄 1[45]칸")   # 끝 쉼표 위치: Python 3.11 은 15, 3.13 은 14
        cfg.write_text('["en"]', encoding="utf-8")
        self.assertIn("객체여야 한다", self.blocked(pipeline.rig, self.root, str(self.root / "a.glb"), quiet=True))

    def test_every_default_setting_is_read(self):
        """Every default settings key is read somewhere in the code.

        기본 설정의 키는 모두 코드 어딘가에서 읽힌다 — 안 읽히는 키를 문서에 적으면 문서가 거짓말을 한다.
        (10/9: `blender.prefer_module`·`default_model` 이 어디서도 안 읽혀 뺐다. 옛 설정 파일에 남아 있으면 모르는 키로 알린다.)"""
        from bonewright import config
        src = "".join(p.read_text(encoding="utf-8") for p in (Path(__file__).resolve().parents[1] / "bonewright").rglob("*.py") if p.name != "config.py")

        def leaves(d, pre=""):
            for k, v in d.items():
                yield from (leaves(v, f"{pre}{k}.") if isinstance(v, dict) and v else [f"{pre}{k}"])
        unread = [k for k in leaves(config.DEFAULTS) if f'"{k.rsplit(".", 1)[-1]}"' not in src and f"'{k.rsplit('.', 1)[-1]}'" not in src]
        self.assertEqual([], unread)
        (self.root / "runs").mkdir()
        (self.root / "runs" / "config.json").write_text('{"blender": {"prefer_module": false}}', encoding="utf-8")
        self.assertEqual(["blender.prefer_module"], config.unknown_keys(self.root))

    def test_unknown_settings_key_warns(self):
        """A misspelt settings key (rig.cross_trimm) prints one warning and does not stop.

        runs/config.json 의 오타 키(`rig.cross_trimm`)를 조용히 받아 기본값으로 돌던 것(10/8 2회차) → 경고 한 줄, 멈추지는 않는다."""
        from bonewright import config
        (self.root / "runs").mkdir()
        cfg = self.root / "runs" / "config.json"
        cfg.write_text('{"lang": "en", "rig": {"cross_trimm": false, "face": true}, "blendr": {}, "models": {"fit": {"effort": "low"}}}', encoding="utf-8")
        self.assertEqual(config.unknown_keys(self.root), ["rig.cross_trimm (→ rig.cross_trim?)", "blendr (→ blender?)"])
        self.assertIn("rig.cross_trimm", config.unknown_keys_line(self.root))
        self.assertTrue(config.load(self.root)["rig"]["face"])   # 아는 키는 그대로 먹는다
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.blocked(pipeline.rig, self.root, str(self.root / "a.glb"))   # 메시가 없어 막혀도 경고는 먼저 나온다
        self.assertIn("rig.cross_trimm", err.getvalue())
        cfg.write_text('{"lang": "en", "rig": {"cross_trim": false}}', encoding="utf-8")
        self.assertIsNone(config.unknown_keys_line(self.root))
        cfg.write_text('{"lang": "en",}', encoding="utf-8")
        self.assertEqual(config.unknown_keys(self.root), [])   # 깨진 파일은 load 의 Blocked 가 맡는다

    def test_unsupported_mesh_format(self):
        f = self.root / "char.stl"; f.write_bytes(b"solid x")
        msg = self.blocked(pipeline.rig, self.root, str(f), quiet=True)
        self.assertIn(".glb", msg)

    def test_missing_targets_file(self):
        f = self.root / "char.glb"; f.write_bytes(b"glTF")
        msg = self.blocked(pipeline.rig, self.root, str(f), quiet=True, targets_file=str(self.root / "t.json"))
        self.assertIn("--targets", msg)

    def test_export_and_demo_without_rig(self):
        for fn in (pipeline.export_rig, pipeline.demo):
            with self.subTest(fn=fn.__name__):
                msg = self.blocked(fn, self.root, "rig-없는것", quiet=True)
                self.assertIn("bw rig", msg)
                self.assertIn("bw status", msg)

    def test_motion_without_source_or_missing_bvh(self):
        self.assertIn("--bvh", self.blocked(pipeline.motion, self.root, quiet=True))
        self.assertIn("BVH 파일이 없다", self.blocked(pipeline.motion, self.root, bvh=str(self.root / "w.bvh"), quiet=True))

    def test_bad_targets_json_leaves_no_run(self):
        f = self.root / "char.glb"; f.write_bytes(b"glTF")
        t = self.root / "t.json"; t.write_text("{oops", encoding="utf-8")
        self.assertIn("JSON", self.blocked(pipeline.rig, self.root, str(f), quiet=True, run_id="keep", targets_file=str(t)))
        self.assertFalse((self.root / "runs" / "keep").exists(), "형식 오류로 실행 폴더를 만들면 안 된다")

    def test_motion_missing_rig_checked_before_import(self):
        b = self.root / "w.bvh"; b.write_text("HIERARCHY", encoding="utf-8")
        msg = self.blocked(pipeline.motion, self.root, bvh=str(b), rig_run="없는리그", run_id="m1", quiet=True)
        self.assertIn("bw rig", msg)
        self.assertFalse((self.root / "runs" / "m1").exists(), "리그 확인 전에 동작 실행 폴더를 만들면 안 된다")

    def test_bad_bone_map(self):
        bad = self.root / "map.json"; bad.write_text("{oops", encoding="utf-8")
        self.assertIn("JSON", self.blocked(pipeline.apply_bone_map, {}, bad, []))
        wrong = self.root / "map2.json"; wrong.write_text(json.dumps(["LeftArm"]), encoding="utf-8")
        self.assertIn("LeftArm", self.blocked(pipeline.apply_bone_map, {}, wrong, []))

    def test_status_unknown_run(self):
        err = io.StringIO()
        with patch.object(cli, "ROOT", self.root), patch.object(sys, "argv", ["bw", "status", "nope"]), patch("sys.stderr", err):
            self.assertEqual(cli.main(), 2)
        self.assertIn("→", err.getvalue())


class MissingRunIdTests(unittest.TestCase):
    """`bw demo` / `bw export` with no run-id name the latest rig as a command to paste, or say how to get one.

    10/10 6회차 실측: argparse 의 "the following arguments are required: run_id" 로 끝났고, README 첫 실행은
    `bw demo <run-id>` 를 자리표시 그대로 보여 준다."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def run_bw(self, lang: str, *argv: str) -> tuple[int, str]:
        err = io.StringIO()
        with patch.object(cli, "ROOT", self.root), patch.object(sys, "argv", ["bw", *argv]), patch("sys.stderr", err), \
                patch.dict(os.environ, {"BW_LANG": lang}):
            code = cli.main()
        return code, err.getvalue()

    def test_latest_rig_is_named(self):
        """With rigs on disk, the message carries the newest finished rig, not a motion run or an unfinished one."""
        for i, rid in enumerate(("rig-old", "rig-new")):
            (self.root / "runs" / rid).mkdir(parents=True)
            blend = self.root / "runs" / rid / "02_rigged.blend"; blend.write_bytes(b"")
            os.utime(blend, (1000 + i, 1000 + i))
        (self.root / "runs" / "rig-unfinished").mkdir()
        (self.root / "runs" / "rig-unfinished" / "state.json").write_text("{}", encoding="utf-8")
        for cmd in ("demo", "export"):
            for lang in ("en", "ko"):
                with self.subTest(cmd=cmd, lang=lang):
                    code, err = self.run_bw(lang, cmd)
                    self.assertEqual(2, code)
                    self.assertIn(f"`bw {cmd} rig-new`", err)
                    self.assertIn("`bw status`", err)
                    self.assertNotIn("required", err)

    def test_motion_without_source_fills_in_the_latest_rig(self):
        """`bw motion` with no source names the newest rig in a command that parses, and keeps the placeholder with no rig.

        10/12 13회차: export·demo 는 최근 리그 id 를 채우는데 같은 상황의 `bw motion` 은 `--rig <rig run-id>` 자리표시였다."""
        for lang in ("en", "ko"):
            with self.subTest(lang=lang, rigs=0):
                code, err = self.run_bw(lang, "motion")
                self.assertEqual(2, code); self.assertIn("run-id>", err)
        for i, rid in enumerate(("rig-old", "rig-new")):
            (self.root / "runs" / rid).mkdir(parents=True)
            blend = self.root / "runs" / rid / "02_rigged.blend"; blend.write_bytes(b"")
            os.utime(blend, (1000 + i, 1000 + i))
        for lang in ("en", "ko"):
            with self.subTest(lang=lang, rigs=2):
                code, err = self.run_bw(lang, "motion")
                self.assertEqual(2, code); self.assertNotIn("run-id>", err)
                cmd = re.search(r"`(bw motion --bvh [^`]+)`", err)[1]
                self.assertTrue(cmd.endswith("--rig rig-new"), cmd)
                with patch.object(sys, "argv", cmd.split()), patch.object(cli.pipeline, "motion", return_value="runs/m/report.md") as mo, \
                        patch("sys.stdout", io.StringIO()), patch("sys.stderr", io.StringIO()):
                    self.assertEqual(0, cli.main())
                self.assertEqual("rig-new", mo.call_args.kwargs["rig_run"])

    def test_no_runs_points_at_rig(self):
        """With no finished rig, the message says to run `bw rig` first and where it looked."""
        code, err = self.run_bw("en", "demo")
        self.assertEqual(2, code)
        self.assertIn("BLOCKED:", err); self.assertIn("`bw rig <mesh>`", err); self.assertIn(str(self.root / "runs"), err)
        self.assertIsNone(re.search(r"[가-힣]", err), err)


class WrongRunIdTests(unittest.TestCase):
    """A run-id that is not on disk, while other rigs are, names the closest rig as a command to paste.

    10/11 9회차 실측: `bw export nosuch` 가 "Rig first with `bw rig <mesh> --run-id nosuch`" 라 했다 — 리그가 이미 있으면
    id 오타일 가능성이 크다."""

    run_bw = MissingRunIdTests.run_bw

    def setUp(self):
        MissingRunIdTests.setUp(self)
        for i, rid in enumerate(("hero", "rig-20261011-010203")):
            (self.root / "runs" / rid).mkdir(parents=True)
            blend = self.root / "runs" / rid / "02_rigged.blend"; blend.write_bytes(b"")
            os.utime(blend, (1000 + i, 1000 + i))

    def test_typo_names_the_closest_rig(self):
        """`bw export hreo` → `bw export hero`; `bw motion --rig hro` → `--rig hero`; the command parses as pasted."""
        cases = (("export", ["export", "hreo"], "`bw export hero`"), ("demo", ["demo", "hreo"], "`bw demo hero`"),
                 ("motion", ["motion", "--bvh", str(Path(__file__).resolve().parents[1] / "examples" / "wave.bvh"), "--rig", "hro"], "`--rig hero`"))
        for name, argv, want in cases:
            for lang in ("en", "ko"):
                with self.subTest(cmd=name, lang=lang):
                    code, err = self.run_bw(lang, *argv)
                    self.assertEqual(2, code); self.assertIn(want, err); self.assertIn("`bw status`", err)
                    self.assertNotIn("bw rig <", err)
                    self.assertEqual(lang == "ko", bool(re.search("[가-힣]", err)), err)
        with patch.object(sys, "argv", ["bw", "export", "hero"]), patch.object(cli.pipeline, "export_rig", return_value="x.glb") as ex, \
                patch("sys.stdout", io.StringIO()), patch("sys.stderr", io.StringIO()):
            self.assertEqual(0, cli.main())
        self.assertEqual("hero", ex.call_args.args[1])

    def test_no_close_name_falls_back_to_latest(self):
        """Nothing close: the newest rig is offered, not `bw rig <mesh>`."""
        code, err = self.run_bw("en", "demo", "zzzzzz")
        self.assertEqual(2, code); self.assertIn("`bw demo rig-20261011-010203`", err)


class NoRigAtAllTests(unittest.TestCase):
    """With no rig anywhere, an unknown run-id gets the shipped character's first command with that id, which parses.

    10/13 16회차 실측: 임시 폴더에서 `bw export nosuch` → "Rig first with `bw rig <mesh> --run-id nosuch`" — 자리표시."""

    run_bw = MissingRunIdTests.run_bw
    setUp = MissingRunIdTests.setUp

    def test_first_command_carries_the_id(self):
        sample = str(Path(__file__).resolve().parents[1] / "examples" / "wave.bvh")
        for argv in (["export", "nosuch"], ["demo", "nosuch"], ["motion", "--bvh", sample, "--rig", "nosuch"]):
            for lang in ("en", "ko"):
                with self.subTest(argv=argv, lang=lang):
                    code, err = self.run_bw(lang, *argv)
                    self.assertEqual(2, code)
                    cmd = re.search(r"`(bw rig [^`<]*--run-id nosuch)`", err).group(1)
                    self.assertIn("quaternius_adventurer.glb --from-skeleton --no-judge --run-id nosuch", cmd)
                    a = cli.build_parser().parse_args(split_pasted(cmd)[1:])
                    self.assertTrue(Path(a.mesh).is_file() or Path(__file__).resolve().parents[1].joinpath(a.mesh).is_file())
                    self.assertEqual(lang == "ko", bool(re.search("[가-힣]", err)), err)
        (self.root / "runs" / "half").mkdir(parents=True); (self.root / "runs" / "half" / "state.json").write_text("{}")
        self.assertIn("`bw status half`", self.run_bw("en", "export", "half")[1])   # 리깅을 못 마친 실행은 그 메시를 안다 — 지금 문구


class HeadlessRenderTests(unittest.TestCase):
    """A renderer that dies for want of a display (libEGL) says so, keeps the finished rig, and gives the same command with BW_NO_RENDER=1.

    10/13 15회차 실측(bpy 5.2.2, 화면 없는 리눅스): README 첫 명령이 리깅을 마친 뒤 "render_views: Blender exit code -6"·
    "Couldn't open libEGL.so.1" 로 끝나고, 안내는 "이슈를 열어라" 였다."""
    TAIL = "render_views: Blender exit code -6\nCouldn't open libEGL.so.1: libEGL.so.1: cannot open shared object file"

    def step(self, name, err, argv, lang="en"):
        from bonewright import blender
        with tempfile.TemporaryDirectory() as d:
            from bonewright import config
            r = pipeline.Run(Path(d), "rig-x", config.DEFAULTS, quiet=True)
            (r.dir / "02_rigged.blend").write_bytes(b"BLENDER")
            cwd = os.getcwd(); os.chdir(d)
            try:
                with patch.dict(os.environ, {"BW_LANG": lang}), patch.object(sys, "argv", ["bw", *argv]), \
                        patch.object(pipeline, "run_script", side_effect=blender.BlenderError(err)):
                    try:
                        r.blender(name, {})
                    except (pipeline.Blocked, blender.BlenderError) as e:
                        state = json.loads((r.dir / "state.json").read_text())
                        return e, state
            finally:
                os.chdir(cwd)
        self.fail("no error")

    def test_headless_render_is_blocked_with_the_same_command(self):
        import shlex
        e, state = self.step("render_views", self.TAIL, ["rig", "my hero.glb", "--from-skeleton", "--no-judge"])
        self.assertIsInstance(e, pipeline.Blocked)
        msg = str(e)
        self.assertIn("could not start without a display", msg)
        self.assertIn("the rig itself is done: runs/rig-x/02_rigged.blend", msg)
        cmd = msg.split("`BW_NO_RENDER=1 ", 1)[1].split("`", 1)[0]
        self.assertEqual("my hero.glb", cli.build_parser().parse_args(shlex.split(cmd)[1:]).mesh)   # 그대로 붙여 넣으면 된다
        self.assertIn("libegl1", msg); self.assertEqual("failed", state["status"])
        ko, _ = self.step("render_views", self.TAIL, ["rig", "a.glb"], "ko")
        self.assertIn("화면(EGL/OpenGL) 없이", str(ko)); self.assertIn("리깅은 이미 끝났다", str(ko))

    def test_demo_and_motion_wording(self):
        demo, _ = self.step("render_demo", self.TAIL, ["demo", "rig-x"])
        self.assertNotIn("BW_NO_RENDER", str(demo)); self.assertNotIn("rig itself is done", str(demo))   # 영상은 끌 수 없다
        motion, _ = self.step("retarget_bvh", self.TAIL, ["motion", "--bvh", "examples/wave.bvh", "--rig", "rig-x"])
        self.assertIn("`BW_NO_RENDER=1 bw motion --bvh examples/wave.bvh --rig rig-x`", str(motion))
        self.assertNotIn("visual judge", str(motion))

    def test_other_blender_errors_stay_unexpected(self):
        from bonewright import blender
        e, _ = self.step("render_views", "render_views: Blender exit code 1\nTraceback ... KeyError", ["rig", "a.glb"])
        self.assertIsInstance(e, blender.BlenderError)

    def test_cli_says_blocked_without_the_issue_line(self):
        from bonewright import blender
        err = io.StringIO()
        def rig(root, *a, **k):
            raise pipeline.Blocked(pipeline.headless_hint("render_views", Path("nowhere")))
        with tempfile.TemporaryDirectory() as d, patch.object(cli, "ROOT", Path(d)), patch.object(cli.pipeline, "rig", side_effect=rig), \
                patch.object(sys, "argv", ["bw", "rig", "a.glb"]), patch("sys.stderr", err), patch.dict(os.environ, {"BW_LANG": "en"}):
            self.assertEqual(2, cli.main())
        self.assertIn("BLOCKED: render_views: the Blender renderer", err.getvalue()); self.assertNotIn("open an issue", err.getvalue())


class UnexpectedErrorTests(unittest.TestCase):
    """포괄 except: 한 줄 메시지 대신 오류 종류·로그 위치·BW_DEBUG 안내가 나와야 한다."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        lang = patch.dict(os.environ, {"BW_LANG": "ko"}); lang.start(); self.addCleanup(lang.stop)   # 문구 대조는 한국어로

    def tearDown(self):
        self.tmp.cleanup()

    def run_bw(self, env: dict) -> str:
        def boom(root, *a, **kw):
            (root / "runs" / "rig-x" / "logs").mkdir(parents=True)
            return {}["없는 키"]
        err = io.StringIO()
        with patch.object(cli, "ROOT", self.root), patch.object(cli.pipeline, "rig", side_effect=boom), \
                patch.object(sys, "argv", ["bw", "rig", "m.glb"]), patch("sys.stderr", err), patch.dict("os.environ", env):
            self.assertEqual(cli.main(), 2)
        return err.getvalue()

    def test_default_points_at_logs_and_debug(self):
        with patch.dict(os.environ):
            os.environ.pop("BW_DEBUG", None)
            out = self.run_bw({})
        self.assertIn("BLOCKED: KeyError", out)
        self.assertIn(str(self.root / "runs" / "rig-x" / "logs"), out)
        self.assertIn("BW_DEBUG=1", out)
        self.assertNotIn("Traceback", out)

    def test_early_commands_also_reported(self):
        # bw usage 처럼 파이프라인 전에 끝나는 명령도 같은 안내를 거친다(Codex 리뷰 #4 지적).
        # 예전에는 깨진 state.json 으로 `bw status` 를 썼지만, 10/10 6회차부터 status 는 그 실행만 건너뛴다(BrokenStateTests)
        err = io.StringIO()
        with patch.object(cli, "ROOT", self.root), patch.object(sys, "argv", ["bw", "usage"]), \
                patch.object(cli, "summarize", side_effect=json.JSONDecodeError("잘림", "{", 1)), \
                patch("sys.stderr", err), patch("sys.stdout", io.StringIO()), patch.dict(os.environ):
            os.environ.pop("BW_DEBUG", None)
            self.assertEqual(cli.main(), 2)
        self.assertIn("BLOCKED: JSONDecodeError", err.getvalue())
        self.assertIn("BW_DEBUG=1", err.getvalue())

    def test_debug_prints_traceback(self):
        out = self.run_bw({"BW_DEBUG": "1"})
        self.assertIn("Traceback", out)
        self.assertIn("KeyError", out)


class EnglishErrorTests(unittest.TestCase):
    """BW_LANG=en(또는 ko 가 아닌 로캘)이면 BLOCKED 메시지도 영어, 고칠 방법(→)은 그대로."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        lang = patch.dict(os.environ, {"BW_LANG": "en"}); lang.start(); self.addCleanup(lang.stop)
        self.addCleanup(self.tmp.cleanup)

    def blocked(self, fn, *args, **kw) -> str:
        with patch.object(pipeline, "run_script", side_effect=AssertionError("Blender 를 부르면 안 된다")):
            with self.assertRaises(pipeline.Blocked) as cm:
                fn(*args, **kw)
        msg = str(cm.exception)
        self.assertIn("→", msg, msg)
        self.assertNotRegex(msg, "[가-힣]", "영어 모드에 한국어가 섞였다")
        return msg

    def test_input_errors_in_english(self):
        self.assertIn("mesh file not found", self.blocked(pipeline.rig, self.root, str(self.root / "none.glb"), quiet=True))
        f = self.root / "char.stl"; f.write_bytes(b"solid x")
        self.assertIn("cannot read mesh format", self.blocked(pipeline.rig, self.root, str(f), quiet=True))
        self.assertIn("no rig result", self.blocked(pipeline.export_rig, self.root, "rig-none", quiet=True))
        self.assertIn("no motion source", self.blocked(pipeline.motion, self.root, quiet=True))
        bad = self.root / "map.json"; bad.write_text("{oops", encoding="utf-8")
        self.assertIn("not JSON", self.blocked(pipeline.apply_bone_map, {}, bad, []))

    def test_status_and_pin_in_english(self):
        err = io.StringIO()
        with patch.object(cli, "ROOT", self.root), patch.object(sys, "argv", ["bw", "status", "nope"]), patch("sys.stderr", err):
            self.assertEqual(cli.main(), 2)
        self.assertIn("no such run", err.getvalue())
        err = io.StringIO()
        with patch.object(sys, "argv", ["bw", "rig", "m.glb", "--pin", "hand.L=a,b,c"]), patch.object(cli.pipeline, "rig") as rig, \
                patch("sys.stderr", err):
            with self.assertRaises(SystemExit) as cm:
                cli.main()
        self.assertEqual(2, cm.exception.code)   # 다른 입력 오류와 같은 종료 코드(10/11 11회차)
        self.assertIn("coordinates are three numbers", err.getvalue()); self.assertNotRegex(err.getvalue(), "[가-힣]")
        rig.assert_not_called()

    def test_missing_blender_and_codex_in_english(self):
        # 파이프라인 밖(blender.py·codex.py)에서 올라오는 오류도 영어여야 한다(Codex 리뷰 PR #5)
        from bonewright import blender, codex
        with patch.object(blender, "find_blender", return_value=None), patch.object(blender, "has_bpy_module", return_value=False):
            with self.assertRaises(blender.BlenderError) as cm:
                blender.run_script("analyze", {}, {}, self.root / "logs")
        self.assertIn("Blender not found", str(cm.exception))
        self.assertNotRegex(str(cm.exception), "[가-힣]")
        with patch.object(codex.subprocess, "Popen", side_effect=FileNotFoundError("codex")), patch.dict(os.environ, {"BW_BACKEND": "codex"}):
            with self.assertRaises(codex.CodexError) as cm:
                codex.run_step("fit", "prompt", {}, {}, {"model": "m"}, {}, self.root / "logs")
        self.assertIn("codex executable not found", str(cm.exception))
        self.assertNotRegex(str(cm.exception), "[가-힣]")



class MissingToolTests(unittest.TestCase):
    """A missing Blender or codex says what to install and how to check it, not "open an issue".

    10/10 4회차 실측: Blender 없이 `bw rig` 를 치면 '예상 못 한 오류' 로 빠져 빈 로그 폴더·BW_DEBUG·이슈 템플릿을
    안내했고, state.json 은 'running' 으로 남아 `bw status` 가 계속 도는 중이라 했다."""
    MESH = Path(__file__).resolve().parent / "assets" / "quaternius_adventurer.glb"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        env = {k: v for k, v in os.environ.items() if k != "BW_BLENDER"}
        env.update(BW_LANG="en", BW_BACKEND="mock")
        e = patch.dict(os.environ, env, clear=True); e.start(); self.addCleanup(e.stop)

    def run_bw(self, *argv: str) -> tuple[int, str]:
        from bonewright import blender
        err = io.StringIO()
        with patch.object(cli, "ROOT", self.root), patch.object(sys, "argv", ["bw", *argv]), patch("sys.stderr", err), \
                patch("sys.stdout", io.StringIO()), patch.object(blender, "find_blender", return_value=None), \
                patch.object(blender, "has_bpy_module", return_value=False):
            code = cli.main()
        return code, err.getvalue()

    def test_rig_without_blender_points_at_install_and_doctor(self):
        """`bw rig` without Blender: BLOCKED with the download page and `bw doctor`, no issue line, run marked failed."""
        code, err = self.run_bw("rig", str(self.MESH), "--no-judge", "--run-id", "nob")
        self.assertEqual(2, code)
        self.assertIn("BLOCKED: Blender not found", err)
        self.assertIn("https://www.blender.org/download/", err)
        self.assertIn("`bw doctor`", err)
        self.assertNotIn("open an issue", err)
        self.assertNotIn("BW_DEBUG", err)
        # 10/10 8회차부터 실행 폴더를 만들기 전에 막는다 — `bw status` 에 실패 실행이 쌓이지 않는다
        self.assertFalse((self.root / "runs" / "nob").exists())

    def test_motion_without_blender_leaves_no_run_folder(self):
        """`bw motion` without Blender stops before making runs/<id>, so `bw status` does not fill with failed runs."""
        bvh = self.root / "w.bvh"; bvh.write_text("HIERARCHY\n")
        code, err = self.run_bw("motion", "--bvh", str(bvh), "--run-id", "m1")
        self.assertEqual(2, code); self.assertIn("BLOCKED: Blender not found", err)
        self.assertFalse((self.root / "runs" / "m1").exists())

    def test_failed_export_keeps_the_rig_status(self):
        """A failed `bw export` writes export_state.json and leaves the rig's state.json as it was."""
        from bonewright import blender
        run = self.root / "runs" / "r1"; run.mkdir(parents=True)
        (run / "02_rigged.blend").write_bytes(b"x")
        (run / "state.json").write_text('{"step": "final", "status": "ok"}', encoding="utf-8")
        with patch.object(pipeline, "need_blender", lambda cfg: None), \
                patch.object(pipeline, "run_script", side_effect=blender.BlenderError("export_rig: exit 1")):
            with self.assertRaises(blender.BlenderError):
                pipeline.export_rig(self.root, "r1", quiet=True)
        self.assertEqual("ok", json.loads((run / "state.json").read_text(encoding="utf-8"))["status"])
        self.assertEqual("failed", json.loads((run / "export_state.json").read_text(encoding="utf-8"))["status"])

    def test_demo_with_no_render_says_so_even_without_blender(self):
        """`BW_NO_RENDER=1 bw demo` explains that no video is made, instead of "Blender not found"."""
        run = self.root / "runs" / "r1"; run.mkdir(parents=True); (run / "02_rigged.blend").write_bytes(b"x")
        os.environ["BW_NO_RENDER"] = "1"
        code, err = self.run_bw("demo", "r1")
        self.assertEqual(2, code)
        self.assertIn("BW_NO_RENDER=1, so no demo video is made", err); self.assertNotIn("Blender not found", err)
        self.assertFalse((run / "demo_state.json").exists())

    def test_bw_blender_pointing_nowhere_is_named(self):
        """BW_BLENDER set to a missing file: the message names that path instead of "set BW_BLENDER"."""
        os.environ["BW_BLENDER"] = str(self.root / "no" / "blender")
        code, err = self.run_bw("rig", str(self.MESH), "--no-judge")
        self.assertEqual(2, code)
        self.assertIn("points at a file that does not exist", err)
        self.assertIn(str(self.root / "no" / "blender"), err)

    def test_missing_codex_offers_zero_token_routes(self):
        """codex not installed: the message also offers the 0-token routes a first-time user can take now."""
        from bonewright import codex
        with patch.object(codex.subprocess, "Popen", side_effect=FileNotFoundError("codex")), patch.dict(os.environ, {"BW_BACKEND": "codex"}):
            with self.assertRaises(codex.CodexMissing) as cm:
                codex.run_step("fit", "prompt", {}, {}, {"model": "m"}, {}, self.root / "logs")
        for route in ("--from-skeleton --no-judge", "--from-shape --no-judge", "BW_BACKEND=mock"):
            self.assertIn(route, str(cm.exception))

class PinNameTests(unittest.TestCase):
    """`--pin` with a bone name the metarig does not have stops before Blender with the closest names.

    10/10 8회차 실측: `--pin nosuchbone=0,0,1` 이 Blender 단계까지 갔고, fit_generate 는 없는 이름을 말없이 건너뛴다."""
    MESH = MissingToolTests.MESH; setUp = MissingToolTests.setUp; run_bw = MissingToolTests.run_bw

    def test_typo_names_the_closest_bone(self):
        """A lower-case side (`hand.l`) is named with `hand.L`, before the Blender check, and no run folder is made."""
        code, err = self.run_bw("rig", str(self.MESH), "--no-judge", "--run-id", "p1", "--pin", "hand.l=0.6,0,1.3")
        self.assertEqual(2, code)
        self.assertIn("--pin bone not in the humanoid metarig", err)
        self.assertIn("closest: hand.L", err)
        self.assertNotIn("Blender not found", err)
        self.assertFalse((self.root / "runs" / "p1").exists())

    def test_quadruped_uses_the_wolf_names(self):
        """The wolf metarig has front_thigh.L but no upper_arm.L — the check follows --preset."""
        code, err = self.run_bw("rig", str(self.MESH), "--preset", "quadruped", "--no-judge", "--pin", "upper_arm.L=0,0,1")
        self.assertEqual(2, code); self.assertIn("quadruped metarig", err)
        code, err = self.run_bw("rig", str(self.MESH), "--preset", "quadruped", "--no-judge", "--pin", "front_thigh.L=0,0,1")
        self.assertIn("Blender not found", err); self.assertNotIn("--pin bone", err)

    def test_known_name_and_from_skeleton_go_on(self):
        """A real name passes; under --from-skeleton an unknown name only warns (it may be a source bone of a generic rig)."""
        code, err = self.run_bw("rig", str(self.MESH), "--no-judge", "--pin", "spine.004=0,0,1.42")
        self.assertIn("Blender not found", err)
        code, err = self.run_bw("rig", str(self.MESH), "--no-judge", "--from-skeleton", "--pin", "Hips=0,0,1")
        self.assertIn("Blender not found", err)
        self.assertIn("--pin bone not in the humanoid metarig", err)

    @requires_blender
    def test_names_match_blender(self):
        """bonewright/metarig_names.json is the same as the Rigify metarigs in this Blender."""
        from bonewright import blender, pipeline
        for preset in ("humanoid", "quadruped"):
            got = blender.run_script("metarig_dump", {"preset": preset, "height": 1.8, "ground_z": 0.0}, {}, self.root / "logs")
            self.assertEqual(got["names"], pipeline.metarig_names(preset), preset)


class ReportPathTests(unittest.TestCase):
    """report.md 는 이슈에 그대로 붙인다(템플릿 'A rig came out wrong'). 실행 폴더 안 파일은 상대 경로로,
    밖의 파일은 홈 폴더를 `~` 로 적어 사용자 이름이 들어가지 않게 한다."""

    def test_inside_run_dir_is_relative(self):
        with tempfile.TemporaryDirectory() as d:
            run = Path(d) / "runs" / "r1"
            self.assertEqual("02_rigged.blend", pipeline._shown(run / "02_rigged.blend", run))
            self.assertEqual("motion/motion.bvh", pipeline._shown(str(run / "motion" / "motion.bvh"), run))

    def test_outside_run_dir_hides_home(self):
        with tempfile.TemporaryDirectory() as d, patch.object(Path, "home", return_value=Path(d) / "alice"):
            run = Path(d) / "work" / "runs" / "r1"
            mesh = Path(d) / "alice" / "models" / "hero.glb"
            self.assertEqual("~" + os.sep + os.path.join("models", "hero.glb"), pipeline._shown(mesh, run))
            self.assertEqual(str(Path(d) / "alicex.glb"), pipeline._shown(Path(d) / "alicex.glb", run))   # 이름이 겹칠 뿐인 형제 경로는 그대로

    def test_command_path_is_pasteable(self):
        """Paths put inside a suggested `bw rig … --targets …` are relative to the project folder, or quoted with spaces.

        10/11 9회차: 거절 안내·report.md 의 재실행 명령이 메시 경로를 알면서 `bw rig <mesh>` 자리표시를 줬다."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.assertEqual("models/hero.glb", pipeline._arg(root / "models" / "hero.glb", root))
            self.assertEqual('"my models/hero.glb"', pipeline._arg(root / "my models" / "hero.glb", root))
            with patch.object(sys, "argv", ["bw", "rig", "models/hero.glb", "--targets", "runs/r1/targets.json"]), \
                    patch.object(cli.pipeline, "rig", return_value="runs/r1/report.md") as rig, \
                    patch("sys.stdout", io.StringIO()), patch("sys.stderr", io.StringIO()):
                self.assertEqual(0, cli.main())
            self.assertEqual("runs/r1/targets.json", rig.call_args.kwargs["targets_file"])
        src = Path(pipeline.__file__).read_text(encoding="utf-8")
        self.assertNotIn("bw rig <mesh> --targets", src)   # 값이 있는 곳에 자리표시를 다시 넣지 않는다

    def test_symlinked_home_is_hidden_too(self):
        """report.md hides the home even when it is a symlink and the mesh path was resolved.

        홈이 심볼릭 링크(/home/alice → /mnt/users/alice)면 rig() 가 resolve 한 메시 경로는 실제 쪽에 있다(10/7 Codex 리뷰)."""
        with tempfile.TemporaryDirectory() as d:
            real = Path(d) / "mnt" / "alice"; real.mkdir(parents=True)
            link = Path(d) / "alice"
            try:
                link.symlink_to(real, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("심볼릭 링크를 만들 권한이 없다(Windows 일반 계정)")
            with patch.object(Path, "home", return_value=link):
                mesh = (link / "hero.glb").resolve()
                self.assertEqual("~" + os.sep + "hero.glb", pipeline._shown(mesh, Path(d) / "runs" / "r1"))


    def test_versions_line_for_issue_reports(self):
        """report.md carries a versions line (bonewright, Blender, Python, OS) for issue reports.

        rig-problem 템플릿은 report.md 를 붙이라 한다 — 버전 없는 신고는 재현이 안 된다(10/9 3회차)."""
        from bonewright import __version__
        line = pipeline.versions_line({"blender": "5.2.2 LTS"})
        self.assertTrue(line.startswith(f"- versions: bonewright {__version__} · Blender 5.2.2 LTS · Python "), line)
        self.assertIn("Blender ? ·", pipeline.versions_line({}))   # 옛 결과(버전 없음)에도 멈추지 않는다
        tpl = (Path(pipeline.__file__).resolve().parents[1] / ".github" / "ISSUE_TEMPLATE" / "rig-problem.md").read_text(encoding="utf-8")
        self.assertIn("bw --version", tpl)

class KimodoPathTests(unittest.TestCase):
    """kimodo.cpp 원본이 빌드 폴더(build-release → build/release)와 텍스트 인코더(구성품 폴더 → GGUF 한 파일)를 바꿨다.
    옛 Mac 빌드와 지금 원본 안내대로 만든 것 둘 다 찾아야 한다."""
    K = {"text_bundle": "generated/llm2vec-text-bundle"}

    def test_nothing_built(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual((None, None), pipeline.kimodo_paths(Path(d), self.K))

    def test_old_layout(self):
        with tempfile.TemporaryDirectory() as d:
            k = Path(d); (k / "build-release").mkdir(); (k / "build-release" / "kmd-generate").write_text("")
            (k / "generated" / "llm2vec-text-bundle").mkdir(parents=True)
            self.assertEqual((k / "build-release" / "kmd-generate", k / "generated" / "llm2vec-text-bundle"),
                             pipeline.kimodo_paths(k, self.K))

    def test_current_upstream_layout_prefers_q8(self):
        with tempfile.TemporaryDirectory() as d:
            k = Path(d); (k / "build" / "release").mkdir(parents=True); (k / "build" / "release" / "kmd-generate").write_text("")
            (k / "models").mkdir(); (k / "models" / "kimodo-soma-rp-v1.1-f32.gguf").write_text("")   # 움직임 모델은 텍스트가 아니다
            t = k / "text"; t.mkdir()
            for name in ("tokenizer.gguf", "Llama-3-Kimodo-BF16.gguf", "Llama-3-Kimodo-Q8_0.gguf"):
                (t / name).write_text("")
            self.assertEqual((k / "build" / "release" / "kmd-generate", t / "Llama-3-Kimodo-Q8_0.gguf"),
                             pipeline.kimodo_paths(k, self.K))

    def test_not_built_gives_a_bvh_command_that_runs(self):
        """Without kimodo.cpp the BVH alternative is a pasteable command: the sample BVH and the given or latest rig.

        10/13 16회차 실측: "or use `--bvh file` instead of text" — 자리표시. 출처 없음 안내는 샘플·최근 리그를 채운다."""
        import shlex
        from bonewright import cli
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for lang, rig, want in (("en", None, ""), ("ko", None, ""), ("en", "r7", " --rig r7"), ("en", "", " --rig r7")):
                if rig is not None:
                    (root / "runs" / "r7").mkdir(parents=True, exist_ok=True); (root / "runs" / "r7" / "02_rigged.blend").write_bytes(b"BLENDER")
                with self.subTest(lang=lang, rig=rig), patch.dict(os.environ, {"BW_LANG": lang}):
                    with self.assertRaises(pipeline.Blocked) as cm:
                        pipeline.motion(root, text="a person walks", rig_run=rig or None, quiet=True)
                    cmd = re.search(r"`(bw motion --bvh [^`]*)`", str(cm.exception)).group(1)
                    self.assertTrue(cmd.endswith(f"{pipeline.sample_bvh()}{want}"), cmd)
                    self.assertNotIn("<", cmd)
                    cli.build_parser().parse_args(split_pasted(cmd)[1:])

    def test_missing_text_encoder_says_how_to_get_it(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {"BW_LANG": "en"}):
            root = Path(d); k = root / "vendor" / "kimodo.cpp" / "build" / "release"; k.mkdir(parents=True)
            (k / "kmd-generate").write_text("")
            with self.assertRaisesRegex(pipeline.Blocked, r"download_gguf_weights\.sh"):
                pipeline.motion(root, text="a person walks", quiet=True)


class MotionStepNumberTests(unittest.TestCase):
    """Motion progress counts only the steps that run (a BVH alone starts at [1/1], not [3/3]).

    10/10 4회차 실측: `bw motion --bvh` 첫 줄이 `[3/3]` 이라 앞 단계가 빠진 줄 안다. Blender 는 가짜로 바꿔 끼운다."""
    FAKE = {"import_bvh": {"bones": 2, "frames": [1, 3], "fps": 30, "root_move": 0.0, "armature": "A", "bone_names": ["Hips", "Spine"]},
            "retarget_bvh": {"mapped": {"Hips": "torso"}, "unmapped": ["Spine"], "scale": 1.0},
            "export_anim": {"bones": 1, "frames": [1, 3], "max_diff_cm": 0.0, "verts": 8, "probe_frame": 2, "reimport_diff_cm": 0.0}}

    def steps(self, **kw):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {"BW_LANG": "en"}), \
                patch.object(pipeline, "run_script", lambda name, *a, **k: dict(self.FAKE[name])), \
                patch.object(pipeline, "need_blender", lambda cfg: None):
            root = Path(d); bvh = root / "walk.bvh"; bvh.write_text("HIERARCHY\n", encoding="utf-8")
            if kw.get("rig_run"):
                (root / "runs" / "r1").mkdir(parents=True); (root / "runs" / "r1" / "02_rigged.blend").write_text("")
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                pipeline.motion(root, bvh=str(bvh), run_id="m1", bvh_up="y", **kw)
        return re.findall(r"\[(\d+)/(\d+)\] (\w+)", err.getvalue())

    def test_bvh_only_is_one_step(self):
        self.assertEqual([("1", "1", "import")], self.steps())

    def test_bvh_with_rig_and_export_counts_from_one(self):
        self.assertEqual([("1", "3", "import"), ("2", "3", "retarget"), ("3", "3", "export")],
                         self.steps(rig_run="r1", export="auto"))


class MotionRigOnlyFlagTests(unittest.TestCase):
    """`bw motion` refuses retarget-only flags without `--rig`, before Blender and before a run folder.

    10/10 5회차 코드 읽기: `--export`·`--map`·`--legs`·`--no-roll` 은 `if rig_run:` 안에서만 쓰여 말없이 버려졌다."""

    def test_rig_only_flags_need_rig(self):
        cases = {"--export": {"export": "auto"}, "--map": {"bone_map": "map.json"}, "--legs ik": {"legs": "ik"}, "--no-roll": {"roll": False}}
        for flag, kw in cases.items():
            with self.subTest(flag=flag), tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {"BW_LANG": "en"}), \
                    patch.object(pipeline, "run_script", side_effect=AssertionError("Blender must not start")):
                root = Path(d); bvh = root / "walk.bvh"; bvh.write_text("HIERARCHY\n", encoding="utf-8")
                with self.assertRaises(pipeline.Blocked) as cm:
                    pipeline.motion(root, bvh=str(bvh), run_id="m1", quiet=True, **kw)
                self.assertIn(flag, str(cm.exception)); self.assertIn("--rig", str(cm.exception)); self.assertIn("→", str(cm.exception))
                self.assertFalse((root / "runs" / "m1").exists())


    def test_english_verb_agrees_with_the_flag_count(self):
        """The English line reads right for one flag or several ("--export: used only when", not "--export only apply").

        10/11 12회차 실측: `--export only apply`."""
        for kw, want in (({"export": "auto"}, "--export: used only when"), ({"export": "auto", "roll": False}, "--export · --no-roll: used only when")):
            with self.subTest(kw=kw), tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {"BW_LANG": "en"}):
                root = Path(d); bvh = root / "walk.bvh"; bvh.write_text("HIERARCHY\n", encoding="utf-8")
                with self.assertRaises(pipeline.Blocked) as cm:
                    pipeline.motion(root, bvh=str(bvh), run_id="m1", quiet=True, **kw)
                self.assertIn(want, str(cm.exception))

class FfmpegHintTests(unittest.TestCase):
    def test_install_command_matches_the_os(self):
        """The no-ffmpeg line names an install command for the OS it runs on (not brew everywhere)."""
        self.assertEqual("`brew install ffmpeg`", pipeline.ffmpeg_install("Darwin"))
        self.assertEqual("`winget install ffmpeg`", pipeline.ffmpeg_install("Windows"))
        self.assertEqual("`sudo apt install ffmpeg`", pipeline.ffmpeg_install("Linux"))
        src = Path(pipeline.__file__).read_text(encoding="utf-8")
        self.assertNotIn("(brew install ffmpeg)", src)


class BackendTypoTests(unittest.TestCase):
    def test_unknown_backend_stops_before_paid_calls(self):
        """A BW_BACKEND typo (`Mock`, `moc`) stops with the nearest value instead of silently calling the paid model.

        10/11 11회차: `codex.run_step` 이 `== "mock"` 으로만 비교해 오타가 codex 로 돌았다."""
        from bonewright import config
        with tempfile.TemporaryDirectory() as d:
            for value in ("Mock", "moc", " mock"):
                with self.subTest(value=value), patch.dict(os.environ, {"BW_BACKEND": value, "BW_LANG": "en"}), \
                        patch.object(pipeline, "run_script", side_effect=AssertionError("Blender 를 부르면 안 된다")):
                    with self.assertRaises(pipeline.Blocked) as cm:
                        pipeline.rig(Path(d), str(Path(__file__).parent / "assets" / "quaternius_adventurer.glb"), quiet=True)
                    self.assertIn("`BW_BACKEND=mock`", str(cm.exception))
                    self.assertFalse((Path(d) / "runs").exists())
            for value in ("mock", "codex"):
                with patch.dict(os.environ, {"BW_BACKEND": value}):
                    self.assertIsNone(config.backend_problem())
            with patch.dict(os.environ, {}, clear=True):
                self.assertIsNone(config.backend_problem())   # 없으면 codex(기본)


class RigStartLineTests(unittest.TestCase):
    def start_line(self, backend, **kw):
        from bonewright import blender
        seen = []
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {"BW_LANG": "en", "BW_BACKEND": backend}), \
                patch.object(pipeline, "need_blender", lambda cfg: None), \
                patch.object(pipeline, "run_script", side_effect=blender.BlenderError("stop here")), \
                patch.object(pipeline, "_log", lambda quiet, msg: seen.append(msg)):
            mesh = Path(d) / "a.glb"; mesh.write_bytes(b"glTF")
            with self.assertRaises(blender.BlenderError):
                pipeline.rig(Path(d), str(mesh), quiet=True, **kw)
        return next(m for m in seen if m.startswith("rig "))

    def test_start_line_says_how_many_model_calls(self):
        """The first `bw rig` line says how many model calls it may make (cost used to show only in report.md at the end)."""
        self.assertIn("up to 2 model call(s) (fit·judge)", self.start_line("codex"))
        self.assertIn("up to 1 model call(s) (fit)", self.start_line("codex", no_judge=True))
        self.assertIn("0 model calls", self.start_line("codex", from_skeleton=True, no_judge=True))
        self.assertIn("0 model calls", self.start_line("mock"))


class BpyHintTests(unittest.TestCase):
    def test_bpy_hint_fits_the_running_python(self):
        """The bpy install hint is `pip install bpy==5.2.2` on Python 3.13 and a 3.13 venv command on any other version.

        bpy 5.2.2 는 cp313 휠뿐 — 3.11 에서 그대로 치면 "No matching distribution" 이었다(10/11 12회차)."""
        from bonewright import blender
        with patch.dict(os.environ, {"BW_LANG": "en"}):
            self.assertIn("`pip install bpy==5.2.2`", blender.bpy_install((3, 13)))
            other = blender.bpy_install((3, 11))
            self.assertIn("Python 3.13 only, this is 3.11", other); self.assertIn("`python3.13 -m venv .venv`", other)
            self.assertNotIn("`pip install bpy==5.2.2`", other)
            self.assertIn(blender.bpy_install(), blender.missing_message({}))
        with patch.dict(os.environ, {"BW_LANG": "ko"}):
            self.assertIn("지금 3.11", blender.bpy_install((3, 11)))

    def test_bpy_hint_package_path_works_from_any_folder(self):
        """`pip install . bpy==5.2.2` only works in the repository folder; elsewhere the hint carries the repository's path.

        10/12 14회차 실측: 임시 폴더에서 `bw rig hero.glb` 의 안내를 그대로 치면 `.` 에 pyproject 가 없어 실패했다."""
        from bonewright import blender
        repo = Path(__file__).resolve().parents[1]
        with patch.dict(os.environ, {"BW_LANG": "en"}):
            self.assertIn("`pip install . bpy==5.2.2`", blender.bpy_install((3, 11)))   # 시험은 저장소 폴더에서 돈다
            cwd = os.getcwd()
            with tempfile.TemporaryDirectory() as d:
                try:
                    os.chdir(d)
                    hint = blender.bpy_install((3, 11))
                finally:
                    os.chdir(cwd)
            self.assertNotIn("install . ", hint)
            pkg = hint.split("`pip install ", 1)[1].split(" bpy==", 1)[0].strip('"')
            self.assertTrue((Path(pkg) / "pyproject.toml").is_file(), hint)
            self.assertEqual(Path(pkg).resolve(), repo)
            with patch.object(blender, "__file__", str(Path(d) / "site-packages" / "bonewright" / "blender.py")):   # 설치본만
                self.assertIn("from the repository folder, `python3.13", blender.bpy_install((3, 11)))
        with patch.dict(os.environ, {"BW_LANG": "ko"}), \
                patch.object(blender, "__file__", str(Path(d) / "site-packages" / "bonewright" / "blender.py")):
            self.assertIn("저장소 폴더에서 `python3.13", blender.bpy_install((3, 11)))


class GuideRefTests(unittest.TestCase):
    def test_guide_path_in_messages_opens_from_any_folder(self):
        """Messages that send the reader to docs/GUIDE.md give a path that exists from wherever bw was run.

        10/12 14회차 실측: 임시 폴더에서 `bw doctor` 의 kimodo 줄이 그 폴더엔 없는 `docs/GUIDE.md` 를 가리켰다."""
        from bonewright import cli, config
        repo = Path(__file__).resolve().parents[1]
        self.assertEqual("docs/GUIDE.md", config.guide())   # 시험은 저장소 폴더에서 돈다
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as d:
            try:
                os.chdir(d)
                out = io.StringIO()
                with patch.dict(os.environ, {"BW_LANG": "en"}), patch.object(cli, "ROOT", Path(d)), patch("sys.stdout", out):
                    cli.doctor()
            finally:
                os.chdir(cwd)
            line = next(ln for ln in out.getvalue().splitlines() if "kimodo.cpp:" in ln)
            where = line.rsplit(" in ", 1)[1].strip().strip('"')
            self.assertEqual(Path(where), repo / "docs" / "GUIDE.md", line)
            with patch.object(config, "__file__", str(Path(d) / "site-packages" / "bonewright" / "config.py")):   # 설치본만
                for lang, want in (("en", "docs/GUIDE.md in the repository"), ("ko", "저장소의 docs/GUIDE.md")):
                    with patch.dict(os.environ, {"BW_LANG": lang}):
                        self.assertEqual(want, config.guide())


class BenchInputTests(unittest.TestCase):
    """`bw bench` stops with what to do on an empty folder, a missing file, no Blender or nothing measured.

    10/10 5회차 실측: 빈 폴더는 종료 0 에 "mean Nonecm", 없는 파일은 "nope: Blender not found" 에 종료 0 이었다."""

    def bench(self, root: Path, meshes: list[str], fake=None):
        from bonewright import bench, blender
        run = (lambda name, *a, **k: fake) if fake is not None else _raising(blender.BlenderMissing("Blender not found"))
        with patch.dict(os.environ, {"BW_LANG": "en"}), patch.object(bench, "run_script", run):
            return bench.run(root, meshes, run_id="b1", quiet=True)

    def test_empty_and_missing_stop_before_blender(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for meshes, want in (([], "no meshes"), ([str(root / "nope.glb")], "not found")):
                with self.subTest(want=want), self.assertRaises(pipeline.Blocked) as cm:
                    self.bench(root, meshes, fake={})
                self.assertIn(want, str(cm.exception)); self.assertIn("fetch_bench_assets.py", str(cm.exception))
            self.assertFalse((root / "runs").exists())

    def test_fake_mesh_stops_before_blender(self):
        """A file only named .fbx/.glb/.gltf (a web page, `echo hi > a.fbx`) is refused before Blender, for meshes and --gt-mesh.

        10/13 15회차 실측: `bw bench a.fbx` 는 "Blender not found" 만 — `bw rig a.fbx` 는 14회차부터 막는데 bench 는 안 봤다."""
        from bonewright import bench
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            good = root / "ok.glb"; good.write_bytes(GLB_HEAD)
            for name, want, ko in (("a.fbx", "not FBX data", "FBX 파일이 아니다"), ("b.glb", "not a GLB", "GLB 가 아니다"),
                                   ("c.gltf", "not glTF (JSON) data", "glTF (JSON) 파일이 아니다")):
                bad = root / name; bad.write_text("<html>hi</html>")
                for meshes, gt in (([str(bad)], None), ([str(good)], str(bad))):
                    with self.subTest(name=name, gt=bool(gt)), self.assertRaises(pipeline.Blocked) as cm:
                        with patch.dict(os.environ, {"BW_LANG": "en"}), patch.object(bench, "run_script", _raising(AssertionError("Blender ran"))):
                            bench.run(root, meshes, run_id="b1", quiet=True, gt_mesh=gt)
                    self.assertIn(want, str(cm.exception)); self.assertIn(name, str(cm.exception))
                with patch.dict(os.environ, {"BW_LANG": "ko"}), self.assertRaises(pipeline.Blocked) as cm:
                    bench.run(root, [str(bad)], run_id="b1", quiet=True)
                self.assertIn(ko, str(cm.exception))
            self.assertFalse((root / "runs").exists())

    def test_missing_path_says_file_or_folder_and_next_step(self):
        """A missing bench path says "file or folder" and gives the fetch command, or a folder already fetched.

        10/11 10회차 실측: `bw bench nofolder` → "mesh file not found" — bench 는 폴더도 받는다."""
        with tempfile.TemporaryDirectory() as d:
            root, cwd = Path(d), os.getcwd()
            os.chdir(d)
            try:
                for have, want in ((False, "fetch_bench_assets.py --only samples && bw bench bench-assets/samples"),
                                   (True, "`bw bench " + str(Path("bench-assets") / "samples") + "`")):
                    if have:
                        (root / "bench-assets" / "samples").mkdir(parents=True)
                    with self.subTest(fetched=have), self.assertRaises(pipeline.Blocked) as cm:
                        self.bench(root, ["nofolder"], fake={})
                    self.assertIn("file or folder not found: nofolder", str(cm.exception)); self.assertIn(want, str(cm.exception))
                with patch.dict(os.environ, {"BW_LANG": "ko"}), self.assertRaises(pipeline.Blocked) as cm:
                    from bonewright import bench
                    bench.run(root, ["nofolder"], run_id="b1", quiet=True)
                self.assertIn("파일이나 폴더가 없다", str(cm.exception))
            finally:
                os.chdir(cwd)
            self.assertFalse((root / "runs").exists())

    def test_missing_gt_mesh_is_named(self):
        """A missing `--gt-mesh` file is named as --gt-mesh, not as "mesh"."""
        from bonewright import bench
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); a = root / "a.glb"; a.write_bytes(b"glTF")
            with patch.dict(os.environ, {"BW_LANG": "en"}), self.assertRaises(pipeline.Blocked) as cm:
                bench.run(root, [str(a)], run_id="b1", quiet=True, gt_mesh=str(root / "nope.glb"))
            self.assertIn("--gt-mesh file not found", str(cm.exception))
            self.assertFalse((root / "runs").exists())

    def test_missing_blender_is_raised_once(self):
        from bonewright import blender
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); a = root / "a.glb"; a.write_bytes(GLB_HEAD); b = root / "b.glb"; b.write_bytes(GLB_HEAD)
            with self.assertRaises(blender.BlenderMissing):
                self.bench(root, [str(a), str(b)])

    def test_nothing_measured_is_not_success(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); a = root / "a.glb"; a.write_bytes(GLB_HEAD)
            with self.assertRaises(pipeline.Blocked) as cm:
                self.bench(root, [str(a)], fake={"joints": []})   # 원본 뼈대 없는 자산
            self.assertIn("none of 1", str(cm.exception)); self.assertIn("report.md", str(cm.exception))
            self.assertIn("no skeleton", (root / "runs" / "b1" / "report.md").read_text())


GLB_HEAD = b"glTF" + b"\0" * 16   # 머리만 맞는 GLB — Blender 전 확인(need_mesh_bytes)을 지나 가짜 run_script 까지 간다


def _raising(exc):
    def run(*a, **k):
        raise exc
    return run


class LicenseBoundaryTests(unittest.TestCase):
    """`scripts/check_license_boundary.py` 는 CONTRIBUTING·PR 템플릿·CI 가 돌린다 — 영어 기여자가 처음 보는 CI 실패 문구라
    위반 줄이 영어로, 고칠 방법(→)과 함께 나와야 한다(10/9 3회차까지 한국어뿐, 방법 없음)."""

    def test_violation_says_what_to_do_in_english(self):
        import importlib.util
        root_repo = Path(__file__).resolve().parent.parent
        spec = importlib.util.spec_from_file_location("check_license_boundary", root_repo / "scripts" / "check_license_boundary.py")
        lb = importlib.util.module_from_spec(spec); spec.loader.exec_module(lb)
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {"BW_LANG": "en"}):
            root = Path(d)
            (root / "bonewright" / "bpy_scripts").mkdir(parents=True)
            (root / "bonewright" / "core.py").write_text("import bpy\nfrom mathutils import Vector\n", encoding="utf-8")
            (root / "bonewright" / "bpy_scripts" / "ok.py").write_text("import bpy\n", encoding="utf-8")   # GPL 쪽은 된다
            (root / "spikes").mkdir(); (root / "spikes" / "try.py").write_text("import bpy\n", encoding="utf-8")   # 본체 밖도 MIT 다(10/11: spikes/ 를 못 잡았다)
            bad, checked = lb.problems(root)
        self.assertEqual(2, checked)
        self.assertEqual(4, len(bad), bad)   # core 의 bpy · mathutils · spikes 의 bpy · 라이선스 파일 없음
        self.assertIn("bonewright/core.py:1: MIT-licensed code imports 'bpy'", bad[0])
        self.assertTrue(any(b.startswith("spikes/try.py:1:") for b in bad), bad)
        for b in bad:
            self.assertIn("→", b)
            self.assertIsNone(re.search(r"[가-힣]", b), b)
        self.assertIn("LICENSE", bad[-1])
        ok, _ = lb.problems(root_repo)
        self.assertEqual([], ok)


class BpyProbeCacheTests(unittest.TestCase):
    def test_import_bpy_probe_runs_once_per_python(self):
        """`has_bpy_module` starts `python -c "import bpy"` once per interpreter, not once per Blender step.

        한 번에 0.7초쯤 든다(10/10 8회차 실측) — bpy 휠로 도는 `bw rig` 는 단계마다 이 값을 다시 냈다."""
        import subprocess
        from bonewright import blender
        calls = []
        def fake(cmd, **kw):
            calls.append(cmd[0])
            return subprocess.CompletedProcess(cmd, 1, "", "")
        with patch.dict(blender._BPY_CACHE, clear=True), patch.object(blender.subprocess, "run", side_effect=fake):
            self.assertFalse(blender.has_bpy_module("/x/python"))
            self.assertFalse(blender.has_bpy_module("/x/python"))
            self.assertFalse(blender.has_bpy_module("/y/python"))
        self.assertEqual(["/x/python", "/y/python"], calls)


if __name__ == "__main__":
    unittest.main()
