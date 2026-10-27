#!/usr/bin/env python3
"""以 Mac 已安裝的 Rime/Lua，在暫存設定目錄執行整合測試。

執行：python3 develop/test-rime-features.py
RIME_TEST_SOURCE 可指定注音與拼音相依資料目錄，預設為 ~/Library/Rime。
RIME_TEST_USE_INSTALLED=1 可只驗證已部署設定的副本，不覆蓋或重新編譯專案內容。
不會寫入或部署使用者的正式設定，也不會開啟正式使用者詞庫。
"""

import ctypes as C
import os
from pathlib import Path
import shutil
import tempfile
import unittest


class Traits(C.Structure):
    _fields_ = [("data_size", C.c_int)] + [
        (name, C.c_char_p) for name in (
            "shared_data_dir", "user_data_dir", "distribution_name",
            "distribution_code_name", "distribution_version", "app_name",
        )
    ] + [("modules", C.POINTER(C.c_char_p)), ("min_log_level", C.c_int)] + [
        (name, C.c_char_p) for name in ("log_dir", "prebuilt_data_dir", "staging_dir")
    ]


class Composition(C.Structure):
    _fields_ = [(name, C.c_int) for name in (
        "length", "cursor_pos", "sel_start", "sel_end"
    )] + [("preedit", C.c_char_p)]


class Candidate(C.Structure):
    _fields_ = [("text", C.c_char_p), ("comment", C.c_char_p), ("reserved", C.c_void_p)]


class Menu(C.Structure):
    _fields_ = [(name, C.c_int) for name in (
        "page_size", "page_no", "is_last_page", "highlighted_candidate_index", "num_candidates"
    )] + [("candidates", C.POINTER(Candidate)), ("select_keys", C.c_char_p)]


class Context(C.Structure):
    _fields_ = [("data_size", C.c_int), ("composition", Composition), ("menu", Menu),
                ("commit_text_preview", C.c_char_p), ("select_labels", C.POINTER(C.c_char_p))]


class Commit(C.Structure):
    _fields_ = [("data_size", C.c_int), ("text", C.c_char_p)]


def initialized(struct):
    result = struct()
    result.data_size = C.sizeof(struct) - C.sizeof(C.c_int)
    return result


def decoded(value):
    return value.decode("utf-8") if value else ""


class RimeFeatures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app = Path("/Library/Input Methods/Squirrel.app/Contents")
        source = Path(os.environ.get("RIME_TEST_SOURCE", Path.home() / "Library/Rime"))
        plugin = app / "Frameworks/rime-plugins/librime-lua.dylib"
        if not plugin.exists() or not (source / "terra_pinyin.dict.yaml").exists():
            raise unittest.SkipTest("需要已安裝鼠鬚管、librime-lua 與地球拼音資料")
        cls.scratch = tempfile.TemporaryDirectory(prefix="rime-liur-test-")
        cls.data = Path(cls.scratch.name)
        cls.addClassCleanup(cls.scratch.cleanup)
        for item in source.iterdir():
            if item.is_file() and item.suffix in (".yaml", ".txt"):
                shutil.copy2(item, cls.data / item.name)
        for directory in ("build", "opencc"):
            if (source / directory).exists():
                shutil.copytree(source / directory, cls.data / directory)
        # 僅繼承相依資料和已編譯的詞庫；所有專案內容使用本次 checkout。
        installed_only = os.environ.get("RIME_TEST_USE_INSTALLED") == "1"
        if not installed_only:
            project = Path(__file__).resolve().parents[1] / "Rime"
            shutil.copytree(project, cls.data, dirs_exist_ok=True)
            # 移除新功能產物，驗證正常部署會自動編譯相依方案。
            for pattern in ("liur_Japan.*.bin", "liur_TradToSimp.*.bin", "liur_readings.*"):
                for path in (cls.data / "build").glob(pattern):
                    path.unlink()
        elif (source / "lua").exists():
            shutil.copytree(source / "lua", cls.data / "lua")
        cls.lib = C.CDLL(str(app / "Frameworks/librime.1.dylib"))
        # 與鼠鬚管一致；GLOBAL 會掩蓋連線模組未明確連結 Lua 的錯誤。
        cls.lua = C.CDLL(str(plugin), mode=C.RTLD_LOCAL)
        signatures = {
            "Setup": ([C.POINTER(Traits)], None),
            "Initialize": ([C.POINTER(Traits)], None),
            "Finalize": ([], None),
            "DeployWorkspace": ([], C.c_int),
            "CreateSession": ([], C.c_size_t),
            "DestroySession": ([C.c_size_t], C.c_int),
            "SelectSchema": ([C.c_size_t, C.c_char_p], C.c_int),
            "ProcessKey": ([C.c_size_t, C.c_int, C.c_int], C.c_int),
            "GetContext": ([C.c_size_t, C.POINTER(Context)], C.c_int),
            "FreeContext": ([C.POINTER(Context)], C.c_int),
            "GetCommit": ([C.c_size_t, C.POINTER(Commit)], C.c_int),
            "FreeCommit": ([C.POINTER(Commit)], C.c_int),
            "GetOption": ([C.c_size_t, C.c_char_p], C.c_int),
            "SetOption": ([C.c_size_t, C.c_char_p, C.c_int], None),
        }
        for name, (args, result) in signatures.items():
            function = getattr(cls.lib, "Rime" + name)
            function.argtypes, function.restype = args, result
        cls.modules = (C.c_char_p * 4)(b"default", b"deployer", b"lua", None)
        cls.traits = initialized(Traits)
        cls.traits.shared_data_dir = os.fsencode(app / "SharedSupport")
        cls.traits.user_data_dir = os.fsencode(cls.data)
        cls.traits.app_name = b"rime.liur_test"
        cls.traits.modules = cls.modules
        cls.traits.min_log_level = 2
        cls.traits.log_dir = os.fsencode(cls.data)
        cls.lib.RimeSetup(C.byref(cls.traits))
        cls.lib.RimeInitialize(C.byref(cls.traits))
        cls.addClassCleanup(cls.lib.RimeFinalize)
        if not installed_only and not cls.lib.RimeDeployWorkspace():
            raise AssertionError("Rime 部署失敗")
        for name in ("liur_Japan.table.bin", "liur_TradToSimp.table.bin", "liur_readings.prism.bin"):
            if not (cls.data / "build" / name).exists():
                raise AssertionError("相依方案未編譯：" + name)

    def setUp(self):
        self.session = self.lib.RimeCreateSession()
        self.addCleanup(self.lib.RimeDestroySession, self.session)
        self.assertTrue(self.lib.RimeSelectSchema(self.session, b"liur"))
        self.commits = []

    @classmethod
    def tearDownClass(cls):
        errors = []
        for path in cls.data.glob("*.ERROR.*"):
            errors.extend(line for line in path.read_text(errors="replace").splitlines()
                          if line.startswith("E20"))
        if errors:
            raise AssertionError("Rime 錯誤日誌：\n" + "\n".join(errors))

    def snapshot(self):
        ctx = initialized(Context)
        self.assertTrue(self.lib.RimeGetContext(self.session, C.byref(ctx)))
        result = {
            "preedit": decoded(ctx.composition.preedit),
            "candidates": [decoded(ctx.menu.candidates[i].text) for i in range(ctx.menu.num_candidates)],
            "comments": [decoded(ctx.menu.candidates[i].comment) for i in range(ctx.menu.num_candidates)],
            "page": ctx.menu.page_no,
        }
        self.lib.RimeFreeContext(C.byref(ctx))
        return result

    def key(self, code, modifiers=0):
        handled = self.lib.RimeProcessKey(self.session, code, modifiers)
        commit = initialized(Commit)
        if self.lib.RimeGetCommit(self.session, C.byref(commit)):
            self.commits.append(decoded(commit.text))
            self.lib.RimeFreeCommit(C.byref(commit))
        return handled

    def type(self, text):
        for char in text:
            self.key({"\n": 0xff0d, "\b": 0xff08, "\x1b": 0xff1b, "\t": 0xff09}.get(char, ord(char)))
        return self.snapshot()

    def switch(self, command):
        before = list(self.commits)
        self.type(command + " ")
        self.assertEqual(self.commits, before, "切換指令不應上屏")

    def test_simplified_codes(self):
        self.switch(",,c")
        self.type("oek ")
        self.assertEqual(self.commits, ["呒"])
        self.assertTrue(self.lib.RimeGetOption(self.session, b"liur_simplified"))

    def test_traditional_to_simplified_and_back(self):
        self.switch(",,ct")
        self.type("cofu ")
        self.switch(",,t")
        self.type("cofu ")
        self.assertEqual(self.commits, ["虾", "蝦"])

    def test_japanese_dictionary_and_kana(self):
        self.switch(",,j")
        self.type("fqo a, a. ")
        self.switch(",,t")
        self.type("fqo ")
        self.assertEqual(self.commits, ["畑", "あ", "ア", "熇"])

    def test_command_enter_and_numeric_zero(self):
        self.type(",,j\n")
        self.assertEqual(self.commits, [])
        self.type("fqo ")
        self.type(",,t0a ")
        self.assertEqual(self.commits, ["畑", "對"])

    def test_command_cancel_and_edit(self):
        self.type(",,j\x1b")
        self.assertTrue(self.lib.RimeGetOption(self.session, b"liur_traditional"))
        self.type(",,ct\b ")
        self.type("oek ")
        self.assertEqual(self.commits, ["呒"])

    def test_mode_option_from_menu(self):
        self.lib.RimeSetOption(self.session, b"liur_traditional", False)
        self.lib.RimeSetOption(self.session, b"liur_japanese", True)
        self.type("fqo ")
        self.assertEqual(self.commits, ["畑"])

    def test_homophone_two_stages_and_tone(self):
        state = self.type("'mnfo")
        self.assertEqual(state["candidates"][0], "瞎")
        state = self.type(" ")
        self.assertEqual(self.commits, [])
        self.assertIn("蝦", state["candidates"])
        self.assertFalse({"夏", "霞", "俠"} & set(state["candidates"]))
        index = state["candidates"].index("蝦")
        self.type(str(index))  # 本專案選字鍵由 0 起算。
        self.assertEqual(self.commits, ["蝦"])

    def test_homophone_numeric_first_stage_and_arrows(self):
        state = self.type("'mnfo0")
        self.assertIn("蝦", state["candidates"])
        self.key(0xff54)  # Down
        self.type(" ")
        self.assertEqual(self.commits, ["蝦"])

    def test_homophone_page_selection(self):
        self.type("'mv ")  # 行：hang2、xing2、xing4
        self.key(0xff56)  # Page_Down
        state = self.snapshot()
        self.assertGreater(state["page"], 0)
        expected = state["candidates"][0]
        self.type("0")
        self.assertEqual(self.commits, [expected])

    def test_homophone_all_readings(self):
        state = self.type("'mv ")
        comments = []
        candidates = []
        for _ in range(30):
            comments += state["comments"]
            candidates += state["candidates"]
            old_page = state["page"]
            self.key(0xff56)
            state = self.snapshot()
            if state["page"] == old_page:
                break
        combined = " ".join(comments)
        for reading in ("hang2", "xing2", "xing4"):
            self.assertIn(reading, combined)
        self.assertEqual(len(candidates), len(set(candidates)))

    def test_homophone_return_and_cancel(self):
        self.type("'mnfo ")
        state = self.type("\b")
        self.assertEqual(state["preedit"], "mnfo")
        state = self.type("\x1b")
        self.assertEqual(state["preedit"], "")
        self.assertEqual(self.commits, [])

    def test_homophone_uses_current_language_dictionary(self):
        self.switch(",,j")
        state = self.type("'fqo")
        self.assertEqual(state["candidates"][0], "畑")
        self.type("\x1b")
        self.switch(",,c")
        state = self.type("'oek")
        self.assertEqual(state["candidates"][0], "呒")

    def test_homophone_simplified_output(self):
        self.switch(",,c")
        state = self.type("'mnfo ")
        self.assertIn("虾", state["candidates"])
        self.assertNotIn("蝦", state["candidates"])
        self.type(str(state["candidates"].index("虾")))
        self.assertEqual(self.commits, ["虾"])

    def test_homophone_neutral_tone(self):
        state = self.type("'omf ")  # 嗎：ma3、ma5；輕聲必須能查到。
        comments = []
        for _ in range(20):
            comments += state["comments"]
            old_page = state["page"]
            self.key(0xff56)
            state = self.snapshot()
            if state["page"] == old_page:
                break
        self.assertIn("ma5", " ".join(comments))

    def test_homophone_missing_pronunciation(self):
        state = self.type("'liu ")
        self.assertIn("嘸蝦米", state["candidates"])
        self.assertIn("查無讀音", " ".join(state["comments"]))
        self.type(" ")
        self.assertEqual(self.commits, ["嘸蝦米"])

    def test_first_tone_and_phrase(self):
        state = self.type("';su ")
        self.assertIn("ㄋㄧˉ", state["preedit"])
        self.assertEqual(self.commits, [])
        self.type(" \x1b';5j/ jp6 ")
        self.assertEqual(self.commits, ["呢", "中文"])

    def test_other_tones(self):
        self.type("';su6 ';su3 ';su4 ';a87 ';-6 ")
        self.assertEqual(self.commits, ["呢", "你", "膩", "嗎", "而"])

    def test_phonetic_and_pinyin_in_language_modes(self):
        for command, expected in ((",,j", "中文"), (",,c", "中文"), (",,ct", "中文")):
            self.switch(command)
            self.type("';5j/ jp6 ")
            self.assertEqual(self.commits[-1], expected)
        self.switch(",,t")
        self.type("`nihao ")
        self.assertEqual(self.commits[-1], "你好")

    def test_simplified_phonetic_output(self):
        self.switch(",,c")
        state = self.type("';xj/6")
        self.assertIn("龙", state["candidates"])
        self.assertNotIn("龍", state["candidates"])

    def test_language_modes_are_exclusive(self):
        modes = {",,c": "liur_simplified", ",,ct": "liur_trad_to_simp",
                 ",,j": "liur_japanese", ",,t": "liur_traditional"}
        for command, expected in modes.items():
            self.switch(command)
            for option in modes.values():
                self.assertEqual(bool(self.lib.RimeGetOption(self.session, option.encode())),
                                 option == expected)

    def test_normal_input_and_raw_english(self):
        self.type("a hello\n")
        self.assertEqual(self.commits, ["對", "hello"])

    def test_punctuation_reverse_lookup_and_custom_phrases(self):
        self.type("' ")
        self.assertEqual(self.commits, ["、"])
        state = self.type(";;cofu")
        self.assertIn("蝦", state["candidates"])
        self.assertIn("ㄒㄧㄚ", " ".join(state["comments"]))
        self.type("\x1b\x1b")
        state = self.type(";ci`aj`oxx`ohe`")
        self.assertIn("中華民國", state["candidates"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
