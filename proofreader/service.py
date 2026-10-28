#!/usr/bin/env python3
"""離線繁體中文選字校錯。只在記憶體處理短上下文，不保存輸入或使用網路。"""
import argparse
from functools import lru_cache
import math
import os
from pathlib import Path
import signal
import socket
import sys

import numpy as np
import onnxruntime as ort


def chinese(text):
    return bool(text) and all("\u3400" <= char <= "\u9fff" for char in text)


class Proofreader:
    def __init__(self, model_dir, essay, readings):
        self.words = {}
        for line in Path(essay).read_text().splitlines():
            fields = line.split()
            if len(fields) == 2 and 2 <= len(fields[0]) <= 4 and chinese(fields[0]):
                # 少見詞也保護，只有較常見的詞才能成為建議。
                self.words[fields[0]] = int(fields[1])
        self.endings = {}
        for word, frequency in self.words.items():
            if frequency >= 1000:
                self.endings.setdefault(word[:-1], set()).add(word[-1])
        self.readings = {}
        for line in Path(readings).read_text(encoding="utf-8-sig").splitlines():
            fields = line.split("\t")
            if len(fields) >= 2 and len(fields[0]) == 1 and chinese(fields[0]):
                self.readings.setdefault(fields[0], set()).add(fields[1])
        # splitlines() 會把詞表中的 Unicode 分隔字元誤切成多行，導致索引錯位。
        vocabulary = Path(model_dir, "vocab.txt").read_text().split("\n")
        if vocabulary[-1] == "": vocabulary.pop()
        self.ids = {word: index for index, word in enumerate(vocabulary)}
        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        options.add_session_config_entry("session.intra_op.allow_spinning", "0")
        self.model = ort.InferenceSession(str(Path(model_dir, "model.onnx")), options,
                                         providers=["CPUExecutionProvider"])
        self.logits("備")  # 在接受連線前暖機，不讓首次選字承擔初始化時間。

    def logits(self, history):
        ids = np.array([[self.ids["[CLS]"]] + [self.ids.get(c, self.ids["[UNK]"]) for c in history[-32:]]
                        + [self.ids["[MASK]"], self.ids["[SEP]"]]], dtype=np.int64)
        return self.model.run(None, {"input_ids": ids, "attention_mask": np.ones_like(ids),
                                     "token_type_ids": np.zeros_like(ids)})[0][0]

    @lru_cache(maxsize=32)
    def local_logits(self, prefix):
        return self.logits(prefix)

    def winner(self, scores, original, choices, margin_limit=3.0, confidence_limit=0.85):
        ranked = sorted(choices, key=lambda char: float(scores[self.ids[char]]), reverse=True)
        best = ranked[0]
        margin = float(scores[self.ids[best]] - scores[self.ids[original]])
        competitors = [original] + ranked[1:]
        confidence = 1 / (1 + sum(math.exp(min(50, float(scores[self.ids[c]] - scores[self.ids[best]])))
                                  for c in competitors))
        if margin < margin_limit or confidence < confidence_limit:
            return None
        return best

    def crosses_word_boundary(self, history, prefix):
        if prefix in self.words:
            return False
        # 不能把「準備／住…」硬拆成「準／備註」，局部回退應保護完整詞。
        return any(self.words.get(history[-length:], 0) >= 1000
                   for length in range(len(prefix) + 1, min(4, len(history)) + 1))

    @lru_cache(maxsize=256)
    def suggest(self, history, original):
        if not chinese(history) or len(history) > 32 or len(original) != 1 or not chinese(original):
            return None
        if original not in self.ids or original not in self.readings:
            return None
        suffixes = [history[-length:] for length in (1, 2, 3) if len(history) >= length]
        if any(prefix + original in self.words for prefix in suffixes):
            return None
        choices, local_choices = {}, {}
        for prefix in suffixes:
            for char in self.endings.get(prefix, ()):
                if char != original and char in self.ids and self.readings[original] & self.readings.get(char, set()):
                    phrase = prefix + char
                    if char not in choices or len(phrase) > len(choices[char]): choices[char] = phrase
                    local_choices.setdefault(prefix, {})[char] = phrase
        if not choices:
            return None
        scores = self.logits(history)
        best = self.winner(scores, original, choices)
        if best:
            return best, choices[best]
        # 長上下文中的重複錯字可能讓小模型模仿錯誤模式。
        # 以詞庫界定的當前詞再次評分，使用更嚴格門檻，不降低全句門檻。
        local_results = {}
        for prefix, candidates in local_choices.items():
            if prefix == history or self.crosses_word_boundary(history, prefix):
                continue
            best = self.winner(self.local_logits(prefix), original, candidates, 4.0, 0.90)
            if best:
                phrase = candidates[best]
                if best not in local_results or len(phrase) > len(local_results[best]):
                    local_results[best] = phrase
        # 不同局部視窗若互相矛盾，保持不提示。
        if len(local_results) == 1:
            return next(iter(local_results.items()))
        return None


def serve(checker, path, parent_pid=None):
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    if path.exists():
        # 已有服務就退出，不能切斷仍在使用的 socket。
        with socket.socket(socket.AF_UNIX) as probe:
            try:
                probe.connect(str(path))
                raise RuntimeError("校錯服務已在執行")
            except (ConnectionRefusedError, FileNotFoundError):
                path.unlink(missing_ok=True)
    server = socket.socket(socket.AF_UNIX)
    try:
        server.bind(str(path))
        path.chmod(0o600)
        server.listen(4)
        server.settimeout(0.5)
        signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
        while True:
            if parent_pid is not None and os.getppid() != parent_pid:
                break
            try:
                connection, _ = server.accept()
            except TimeoutError:
                continue
            with connection:
                connection.settimeout(0.05)
                try:
                    payload = bytearray()
                    while b"\n" not in payload and len(payload) <= 512:
                        chunk = connection.recv(512)
                        if not chunk: break
                        payload.extend(chunk)
                    if len(payload) > 512 or b"\n" not in payload: continue
                    fields = payload.split(b"\n", 1)[0].decode("utf-8").split("\t")
                    if len(fields) != 2: continue
                    result = checker.suggest(*fields)
                    connection.sendall(("\t".join(result) + "\n" if result else "\n").encode())
                except (TimeoutError, OSError, UnicodeError):
                    # 超時或輸入法已放棄查詢時，不記錄輸入，也不影響後續連線。
                    pass
    finally:
        server.close()
        path.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--rime-dir", type=Path, required=True)
    parser.add_argument("--socket", type=Path)
    parser.add_argument("--parent-pid", type=int)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    checker = Proofreader(args.model_dir, args.rime_dir / "essay.txt", args.rime_dir / "terra_pinyin.dict.yaml")
    if args.self_test:
        if checker.suggest("備", "住") != ("註", "備註") or checker.suggest("意", "議") != ("義", "意義"):
            raise RuntimeError("內建校錯自我檢查失敗")
        print("OK: 備住→備註; 意議→意義")
        return
    if args.socket is None:
        parser.error("需要 --socket 或 --self-test")
    serve(checker, args.socket, args.parent_pid)


if __name__ == "__main__":
    main()
