#!/usr/bin/env python3
"""安裝／停用本機校錯原型；不改客製按鍵檔或詞庫。"""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import socket as sockets
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
LABEL = "org.rime-liur.proofreader"
DOMAIN = f"gui/{os.getuid()}"
SQUIRREL = "/Library/Input Methods/Squirrel.app/Contents/MacOS/Squirrel"


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".liur-install-", delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(data)
    temporary.replace(path)


def launchctl(*args, check=False):
    return subprocess.run(["launchctl", *args], check=check, stdout=subprocess.DEVNULL,
                          stderr=subprocess.PIPE)


def service_ready(path):
    try:
        with sockets.socket(sockets.AF_UNIX) as connection:
            connection.settimeout(0.05)
            connection.connect(str(path))
            connection.sendall(b"\t\n")
            return connection.recv(1) == b"\n"
    except OSError:
        return False


def bootstrap_agent(agent):
    # bootout 回傳時，launchd 仍可能正在移除舊註冊，立即 bootstrap 會回傳 5。
    deadline = time.monotonic() + 5
    while True:
        result = launchctl("bootstrap", DOMAIN, str(agent))
        if result.returncode == 0:
            return
        if result.returncode != 5 or time.monotonic() >= deadline:
            raise subprocess.CalledProcessError(result.returncode, result.args, stderr=result.stderr)
        time.sleep(0.1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path, default=ROOT / ".proofreader-model")
    parser.add_argument("--rime-dir", type=Path, default=Path.home() / "Library/Rime")
    parser.add_argument("--disable", action="store_true")
    args = parser.parse_args()
    if sys.platform != "darwin": raise RuntimeError("此安裝工具僅支援 macOS")
    if args.disable:
        launchctl("disable", f"{DOMAIN}/{LABEL}", check=True)
        launchctl("bootout", f"{DOMAIN}/{LABEL}")
        print("已停用背景校錯服務；一般輸入不受影響。重新執行安裝可啟用。")
        return

    import numpy  # 確認 launch agent 使用的這個 Python 有所需執行環境。
    import onnxruntime
    del numpy, onnxruntime
    rime = args.rime_dir.resolve()
    for name in ("essay.txt", "terra_pinyin.dict.yaml", "liur.schema.yaml"):
        if not (rime / name).exists(): raise RuntimeError("缺少 Rime 相依資料：" + name)
    model = args.model_dir.resolve()
    manifest = json.loads((model / "provenance.json").read_text())
    for name in ("model.onnx", "vocab.txt"):
        if hashlib.sha256((model / name).read_bytes()).hexdigest() != manifest["sha256"][name]:
            raise RuntimeError("模型檔案驗證失敗：" + name)
    socket = rime / "proofreader/run/checker.sock"
    if len(os.fsencode(socket)) >= 104: raise RuntimeError("Rime 路徑過長，無法建立本機 socket")
    agent = Path.home() / "Library/LaunchAgents" / (LABEL + ".plist")
    backup = rime / "backups" / ("proofreader-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    backup.mkdir(parents=True, exist_ok=False)
    files = {"liur.schema.yaml": (ROOT / "Rime/liur.schema.yaml").read_bytes(),
             "lua/liur_proofreader.lua": (ROOT / "Rime/lua/liur_proofreader.lua").read_bytes(),
             "proofreader/service.py": (ROOT / "proofreader/service.py").read_bytes()}
    for name in ("model.onnx", "vocab.txt", "provenance.json"):
        files["proofreader/model/" + name] = (model / name).read_bytes()
    files["proofreader/model/README.md"] = (model / "original/README.md").read_bytes()
    with tempfile.TemporaryDirectory(prefix="liur-client-") as temporary:
        client = Path(temporary) / "liur_proofread_client"
        subprocess.run(["clang", "-Wall", "-Wextra", "-Werror", "-O2",
                        str(ROOT / "proofreader/client.c"), "-o", str(client)], check=True)
        files["proofreader/liur_proofread_client"] = client.read_bytes()
    existed = {}
    for name in files:
        target = rime / name
        existed[name] = target.exists()
        if target.exists():
            saved = backup / name
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, saved)
    old_agent = agent.read_bytes() if agent.exists() else None
    if old_agent: (backup / "launch-agent.plist").write_bytes(old_agent)
    (backup / "manifest.json").write_text(json.dumps(existed, ensure_ascii=False, indent=2) + "\n")
    custom_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in rime.glob("*.custom.yaml")}
    (backup / "custom-sha256.json").write_text(json.dumps(custom_hashes, indent=2) + "\n")
    was_running = launchctl("print", f"{DOMAIN}/{LABEL}").returncode == 0
    try:
        if was_running: launchctl("bootout", f"{DOMAIN}/{LABEL}", check=True)
        for name, data in files.items(): atomic_write(rime / name, data)
        (rime / "proofreader/liur_proofread_client").chmod(0o755)
        definition = {
            "Label": LABEL,
            "ProgramArguments": [sys.executable, str(rime / "proofreader/service.py"),
                                 "--model-dir", str(rime / "proofreader/model"),
                                 "--rime-dir", str(rime), "--socket", str(socket)],
            "RunAtLoad": True, "KeepAlive": {"SuccessfulExit": False},
            "ProcessType": "Interactive", "ThrottleInterval": 10,
            "EnvironmentVariables": {"PYTHONUNBUFFERED": "1", "OMP_NUM_THREADS": "1"},
            "StandardOutPath": "/dev/null",
            "StandardErrorPath": str(rime / "proofreader/service-errors.log"),
        }
        atomic_write(agent, plistlib.dumps(definition))
        launchctl("enable", f"{DOMAIN}/{LABEL}", check=True)
        bootstrap_agent(agent)
        deadline = time.monotonic() + 15
        while not service_ready(socket):
            if time.monotonic() > deadline: raise RuntimeError("背景校錯服務啟動逾時")
            time.sleep(0.05)
        subprocess.run([SQUIRREL, "--reload"], check=True)
        for name, digest in custom_hashes.items():
            if hashlib.sha256((rime / name).read_bytes()).hexdigest() != digest:
                raise RuntimeError("客製設定在安裝期間發生變更：" + name)
    except Exception:
        launchctl("bootout", f"{DOMAIN}/{LABEL}")
        for name, present in existed.items():
            if present:
                atomic_write(rime / name, (backup / name).read_bytes())
                shutil.copystat(backup / name, rime / name)
            else: (rime / name).unlink(missing_ok=True)
        if old_agent:
            atomic_write(agent, old_agent)
            if was_running: bootstrap_agent(agent)
        else: agent.unlink(missing_ok=True)
        subprocess.run([SQUIRREL, "--reload"], check=False)
        raise
    print("校錯原型已安裝並重新部署。")
    print("原設定備份：", backup)
    print("輸入 p + 空白，再輸入 pak；Tab 採用『註』，空白保留『住』。")
    print("可在 Rime 選單關閉『校錯提示』。背景服務登入時會自動啟動。")


if __name__ == "__main__":
    main()
