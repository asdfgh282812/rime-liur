#!/usr/bin/env python3
"""模型正反例、本機服務失效及原生 Rime 校錯操作的整合測試。"""
import importlib.util
import os
from pathlib import Path
import socket
import statistics
import subprocess
import sys
import threading
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
MODEL = Path(os.environ.get("LIUR_MODEL_DIR", ROOT / ".proofreader-model"))
sys.path.insert(0, str(ROOT))
from proofreader.service import Proofreader

spec = importlib.util.spec_from_file_location("rime_tests", ROOT / "develop/test-rime-features.py")
rime_tests = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rime_tests)


class InstallerTests(unittest.TestCase):
    def installer(self):
        spec = importlib.util.spec_from_file_location("installer", ROOT / "develop/install-proofreader.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_restart_retries_launchd_removal_race(self):
        installer = self.installer()
        pending = subprocess.CompletedProcess(["launchctl"], 5, stderr=b"Input/output error")
        ready = subprocess.CompletedProcess(["launchctl"], 0, stderr=b"")
        with mock.patch.object(installer, "launchctl", side_effect=[pending, ready]) as launch, \
                mock.patch.object(installer.time, "sleep") as sleep:
            installer.bootstrap_agent(Path("test.plist"))
            self.assertEqual(launch.call_count, 2)
            sleep.assert_called_once_with(0.1)

    def test_restart_reports_other_failure(self):
        installer = self.installer()
        failed = subprocess.CompletedProcess(["launchctl"], 1, stderr=b"failure")
        with mock.patch.object(installer, "launchctl", return_value=failed):
            with self.assertRaises(subprocess.CalledProcessError):
                installer.bootstrap_agent(Path("test.plist"))


class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (MODEL / "model.onnx").exists(): raise unittest.SkipTest("請先匯出校錯模型")
        source = Path.home() / "Library/Rime"
        cls.checker = Proofreader(MODEL, source / "essay.txt", source / "terra_pinyin.dict.yaml")

    def test_typo_examples(self):
        examples = {("備", "住"): "註", ("請在下方備", "住"): "註",
                    ("這是我的備", "住"): "註", ("請注", "義"): "意",
                    ("請完成部", "暑"): "署", ("帳", "浩"): "號"}
        for args, expected in examples.items():
            with self.subTest(text="".join(args)):
                self.assertEqual(self.checker.suggest(*args)[0], expected)

    def test_known_words_are_protected(self):
        for history, original in (("居", "住"), ("我們居", "住"), ("備", "註"),
                                  ("收", "入"), ("注", "意"), ("申", "請"),
                                  ("帳", "號"), ("紀", "錄"), ("記", "錄")):
            with self.subTest(text=history + original):
                self.assertIsNone(self.checker.suggest(history, original))

    def test_repeated_typo_context_does_not_hide_local_word(self):
        examples = [(h, "住", ("註", "備註")) for h in
                    ("備註備住備", "備住備住備", "請填寫備註備住備", ("備註備住" * 10 + "備")[-32:])]
        examples += [("注意注義注", "義", ("意", "注意")), ("注義注義注", "義", ("意", "注意")),
                     ("帳號帳浩帳", "浩", ("號", "帳號")), ("帳浩帳浩帳", "浩", ("號", "帳號"))]
        for history, original, expected in examples:
            with self.subTest(history=history):
                self.assertEqual(self.checker.suggest(history, original), expected)

    def test_local_word_fallback_respects_existing_word_boundary(self):
        for history in ("我準備", "我們準備", "請準備", "他們預備", "他的備註裡說我們準備"):
            with self.subTest(history=history):
                self.assertIsNone(self.checker.suggest(history, "住"))

    def test_invalid_and_unrelated_inputs(self):
        for args in (("", "住"), ("abc", "住"), ("備\n", "住"), ("備", "abc"),
                     ("備", "你"), ("備" * 33, "住"), ("123", "住")):
            self.assertIsNone(self.checker.suggest(*args))

    def test_inference_latency(self):
        times = []
        for _ in range(100):
            start = time.perf_counter()
            self.checker.logits("請將相關內容填寫於下方備")
            times.append((time.perf_counter() - start) * 1000)
        print(f"\n模型推論：中位數 {statistics.median(times):.2f}ms，P95 {sorted(times)[94]:.2f}ms")


class NativeProofreaderTests(rime_tests.RimeFeatures):
    @classmethod
    def setUpClass(cls):
        if not (MODEL / "model.onnx").exists(): raise unittest.SkipTest("請先匯出校錯模型")
        client = ROOT / "Rime/proofreader/liur_proofread_client"
        client.parent.mkdir(exist_ok=True)
        subprocess.run(["clang", "-Wall", "-Wextra", "-Werror", "-O2",
                        str(ROOT / "proofreader/client.c"), "-o", str(client)], check=True)
        super().setUpClass()
        cls.socket = cls.data / "proofreader/run/checker.sock"
        if os.environ.get("LIUR_BUNDLED_CHECKER"):
            client = Path(os.environ["LIUR_BUNDLED_CHECKER"]).parents[2] / "Helpers/liur_proofread_client"
            previous = {key: os.environ.get(key) for key in ("LIUR_PROOFREADER_CLIENT", "LIUR_PROOFREADER_SOCKET")}
            os.environ["LIUR_PROOFREADER_CLIENT"] = str(client)
            os.environ["LIUR_PROOFREADER_SOCKET"] = str(cls.socket)
            def restore_environment():
                for key, value in previous.items():
                    if value is None: os.environ.pop(key, None)
                    else: os.environ[key] = value
            cls.addClassCleanup(restore_environment)
        worker_command = ([os.environ["LIUR_BUNDLED_CHECKER"]] if os.environ.get("LIUR_BUNDLED_CHECKER")
                          else [sys.executable, str(ROOT / "proofreader/service.py")])
        cls.worker = subprocess.Popen([*worker_command,
                                      "--model-dir", str(MODEL), "--rime-dir", str(cls.data),
                                      "--socket", str(cls.socket)], stdout=subprocess.DEVNULL,
                                     stderr=subprocess.PIPE)
        cls.addClassCleanup(cls.stop_worker)
        deadline = time.monotonic() + 15
        while not cls.socket.exists():
            if cls.worker.poll() is not None:
                raise AssertionError(cls.worker.stderr.read().decode())
            if time.monotonic() > deadline: raise AssertionError("校錯服務啟動逾時")
            time.sleep(0.02)

    @classmethod
    def stop_worker(cls):
        cls.worker.terminate()
        cls.worker.wait(timeout=5)
        errors = cls.worker.stderr.read().decode()
        cls.worker.stderr.close()
        if errors: raise AssertionError(errors)

    def test_proofreader_hint_without_reordering(self):
        state = self.type("p pak")
        self.assertEqual(self.commits, ["備"])
        self.assertEqual(state["candidates"][0], "住")
        self.assertIn("建議「註」：備註", state["comments"][0])
        candidates = state["candidates"]
        self.lib.RimeSetOption(self.session, b"liur_proofread", False)
        self.assertEqual(self.snapshot()["candidates"], candidates)

    def test_proofreader_tab_accepts_suggestion(self):
        self.type("p pak\t")
        self.assertEqual(self.commits, ["備", "註"])
        self.assertEqual(self.snapshot()["preedit"], "")

    def test_proofreader_space_keeps_original(self):
        self.type("p pak ")
        self.assertEqual(self.commits, ["備", "住"])

    def test_proofreader_numeric_keeps_original(self):
        self.type("p pak0")
        self.assertEqual(self.commits, ["備", "住"])

    def test_proofreader_enter_keeps_raw_input(self):
        self.type("p pak\n")
        self.assertEqual(self.commits, ["備", "pak"])

    def test_proofreader_off(self):
        self.lib.RimeSetOption(self.session, b"liur_proofread", False)
        state = self.type("p pak")
        self.assertNotIn("建議", " ".join(state["comments"]))
        self.type(" ")
        self.assertEqual(self.commits, ["備", "住"])

    def test_proofreader_cursor_and_delete_clear_context(self):
        for key in (0xff51, 0xff08):
            self.type("p ")
            self.key(key)
            state = self.type("pak")
            self.assertNotIn("建議", " ".join(state["comments"]))
            self.type("\x1b")

    def test_proofreader_retype_after_backspace(self):
        self.type("p pak ")
        self.assertFalse(self.key(0xff08), "刪除鍵仍須交給文件處理")
        state = self.type("pak")
        self.assertIn("建議「註」：備註", state["comments"][0])
        self.type("\t")
        self.assertEqual(self.commits[-1], "註")

    def test_proofreader_repeated_delete_and_retype(self):
        self.type("p ")
        for _ in range(3):
            state = self.type("pak")
            self.assertIn("建議「註」：備註", state["comments"][0])
            self.type(" ")
            self.assertFalse(self.key(0xff08))
        state = self.type("pak")
        self.assertIn("建議「註」：備註", state["comments"][0])

    def test_proofreader_mixed_repeated_text_from_screenshot(self):
        state = self.type("p pak\tp pak p pak")  # 備註備住備 + pak
        self.assertEqual("".join(self.commits), "備註備住備")
        self.assertIn("建議「註」：備註", state["comments"][0])
        self.type("\t")
        self.assertEqual("".join(self.commits), "備註備住備註")

    def test_proofreader_continuous_text_longer_than_context_window(self):
        self.type("p pak " * 18)  # 已輸入 36 個字，上下文只保留末 32 字。
        state = self.type("p pak")
        self.assertIn("建議「註」：備註", state["comments"][0])

    def test_proofreader_delete_all_known_text(self):
        self.type("p pak \b\b")
        state = self.type("pak")
        self.assertNotIn("建議", " ".join(state["comments"]))

    def test_proofreader_edit_code_keeps_prefix(self):
        self.type("p pak\b")
        state = self.type("k")
        self.assertIn("建議「註」：備註", state["comments"][0])

    def test_proofreader_cancel_code_keeps_prefix(self):
        state = self.type("p pak\x1bpak")
        self.assertIn("建議「註」：備註", state["comments"][0])

    def test_proofreader_frontend_option_keeps_context(self):
        self.type("p ")
        self.lib.RimeSetOption(self.session, b"_horizontal", True)
        self.lib.RimeSetOption(self.session, b"soft_cursor", True)
        state = self.type("pak")
        self.assertIn("建議「註」：備註", state["comments"][0])

    def test_proofreader_context_survives_reading_pause(self):
        self.type("p ")
        time.sleep(9.1)  # 原先的 8 秒限制會使手動照著說明輸入時失效。
        state = self.type("pak")
        self.assertIn("建議「註」：備註", state["comments"][0])

    def test_proofreader_candidate_navigation_keeps_hint(self):
        self.type("p pak")
        self.key(0xff54)
        self.key(0xff52)
        self.type("\t")
        self.assertEqual(self.commits, ["備", "註"])

    def test_proofreader_language_switch_clears_context(self):
        self.type("p ")
        self.switch(",,j")
        self.switch(",,t")
        state = self.type("pak")
        self.assertNotIn("建議", " ".join(state["comments"]))

    def test_proofreader_no_service(self):
        saved = self.socket.with_name("saved.sock")
        self.socket.rename(saved)
        try:
            state = self.type("p pak")
            self.assertNotIn("建議", " ".join(state["comments"]))
            self.type(" ")
            self.assertEqual(self.commits, ["備", "住"])
        finally:
            saved.rename(self.socket)

    def test_proofreader_transient_failure_is_not_cached(self):
        saved = self.socket.with_name("saved.sock")
        self.socket.rename(saved)
        try:
            state = self.type("p pak")
            self.assertNotIn("建議", " ".join(state["comments"]))
        finally:
            saved.rename(self.socket)
        # 只重繪目前候選，不改字碼或前文；服務恢復後應能重新查詢。
        self.lib.RimeSetOption(self.session, b"_horizontal", True)
        state = self.snapshot()
        self.assertIn("建議「註」：備註", state["comments"][0])

    def test_proofreader_cold_query_slower_than_cache_still_shows_hint(self):
        # 新上下文第一次查詢要跑模型，系統忙碌時可能比快取命中慢數十毫秒；
        # 只要還在截止時間內，就必須第一次就顯示建議，不能等使用者重打。
        self.type("p pa")
        saved = self.socket.with_name("saved.sock")
        self.socket.rename(saved)
        fake = socket.socket(socket.AF_UNIX)
        fake.bind(str(self.socket))
        fake.listen(1)
        def slow_answer():
            with fake.accept()[0] as connection:
                connection.recv(512)
                time.sleep(0.035)
                connection.sendall("註\t備註\n".encode())
        thread = threading.Thread(target=slow_answer, daemon=True)
        thread.start()
        try:
            state = self.type("k")
            self.assertIn("建議「註」：備註", state["comments"][0])
        finally:
            fake.close()
            self.socket.unlink(missing_ok=True)
            saved.rename(self.socket)
            thread.join(timeout=0.5)

    def test_proofreader_slow_service_has_deadline(self):
        self.type("p pa")
        saved = self.socket.with_name("saved.sock")
        self.socket.rename(saved)
        fake = socket.socket(socket.AF_UNIX)
        fake.bind(str(self.socket))
        fake.listen(1)
        def delayed():
            with fake.accept()[0]: time.sleep(0.1)
        thread = threading.Thread(target=delayed, daemon=True)
        thread.start()
        try:
            start = time.perf_counter()
            state = self.type("k")
            elapsed = time.perf_counter() - start
            self.assertLess(elapsed, 0.08, "輸入法不可等待卡住的模型")
            self.assertNotIn("建議", " ".join(state["comments"]))
        finally:
            fake.close()
            self.socket.unlink(missing_ok=True)
            saved.rename(self.socket)
            thread.join(timeout=0.5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
