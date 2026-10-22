# -*- coding: utf-8 -*-
"""
大肥鱼一键启动：宿主服务（桌宠的壳）→ 桌宠窗口 → 语音桥。

重复双击只会有一起效果：已经在跑的都跳过。
桌面上的 dsh-pet.vbs 只是无窗口调这个脚本，所以开机自启也走这里。

    python launcher.py
"""
import os
import sys
import time
import subprocess
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = os.path.dirname(os.path.abspath(__file__))
PY = os.path.join(BASE, ".venv", "Scripts", "python.exe")
LOG = os.path.join(BASE, "launcher.log")

HOST_STATE = "http://127.0.0.1:3080/dsh-pet-7340/state"
VOICE_PORT = 47823
VOICE_HELLO = b"FATUIYU\n"
NO_WINDOW = 0x08000000

VV_PORT = 50021
VV_STATE = f"http://127.0.0.1:{VV_PORT}/version"

import socket

from config import node_dir, voicevox_dir, api_key

# 不再把密钥 / 本机路径写死在这里：统一走 config.py（环境变量 > config.local.json > 自动探测）。
NODE_DIR = node_dir() or r"C:\Users\29212\.workbuddy\binaries\node\versions\22.22.2-6"
VV_DIR = voicevox_dir()
API_KEY = api_key()

PIDS = os.path.join(BASE, "pids.json")


def record(**kv):
    """把起出来的进程 pid 记下来：右键「退出」时桌宠照着这张表逐个收，
    不用再去 spawn python 跑退出脚本（那条路一坏就只弹窗不干活）。"""
    try:
        import json
        cur = {}
        try:
            with open(PIDS, "r", encoding="utf-8") as f:
                cur = json.load(f) or {}
        except Exception:
            pass
        cur.update({k: v for k, v in kv.items() if v})
        with open(PIDS, "w", encoding="utf-8") as f:
            json.dump(cur, f)
    except Exception:
        pass


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    # pythonw 下 sys.stdout 是 None，print 会抛 AttributeError，必须兜住
    try:
        print(line, flush=True)
    except Exception:
        pass
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def host_alive(timeout=2.0):
    try:
        urllib.request.urlopen(HOST_STATE, timeout=timeout).read(64)
        return True
    except Exception:
        return False


def voice_alive():
    """端口占用 + 握手标记都符合，才认为语音桥在跑（端口可能被别的程序占着）"""
    try:
        with socket.create_connection(("127.0.0.1", VOICE_PORT), timeout=0.8) as c:
            c.settimeout(0.8)
            return c.recv(16) == VOICE_HELLO
    except Exception:
        return False


def start_host():
    env = dict(os.environ)
    if API_KEY:
        env["DEEPSEEK_API_KEY"] = API_KEY
    env.setdefault("ELECTRON_MIRROR", "https://npmmirror.com/mirrors/electron/")
    cmd = f'"{os.path.join(NODE_DIR, "dsh.cmd")}" web --no-open'
    log("启动宿主服务 …")
    # 输出落盘，起不来时能直接看到原因（以前丢进 DEVNULL，出问题查不到）
    hf = open(os.path.join(BASE, "host.log"), "ab", buffering=0)
    p = subprocess.Popen(cmd, shell=True, cwd=NODE_DIR, env=env,
                         stdout=hf, stderr=subprocess.STDOUT,
                         creationflags=NO_WINDOW)
    record(host=p.pid)


def start_voice():
    log("启动语音桥 …")
    rf = open(os.path.join(BASE, "run.log"), "ab", buffering=0)
    p = subprocess.Popen([PY, "-u", os.path.join(BASE, "pet_voice.py")],
                         cwd=BASE, stdout=rf, stderr=subprocess.STDOUT,
                         creationflags=NO_WINDOW)
    record(voice=p.pid)


def vv_alive(timeout=1.5):
    try:
        urllib.request.urlopen(VV_STATE, timeout=timeout).read(32)
        return True
    except Exception:
        return False


def start_voicevox():
    """本地日语引擎（古河渚音色的来源）；起不来不影响中文"""
    exe = os.path.join(VV_DIR, "run.exe")
    if not os.path.exists(exe):
        log("找不到 VOICEVOX 引擎，日语会退回 edge 音色")
        return False
    log("启动 VOICEVOX 引擎 …")
    p = subprocess.Popen([exe, "--host", "127.0.0.1", "--port", str(VV_PORT)],
                         cwd=VV_DIR, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, creationflags=NO_WINDOW)
    record(voicevox=p.pid)
    return True


def warm_voicevox():
    """先把日语要用的角色模型加载好，第一句才不卡"""
    code = ("import pet_lang as L, voicevox_pool as v;"
            "p = L.pack('ja');"
            "v.VoicevoxPool(p['vv_speaker'], p['vv_style']).warm()")
    try:
        subprocess.run([PY, "-c", code], cwd=BASE, timeout=180,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       creationflags=NO_WINDOW)
    except Exception:
        pass


def main():
    if host_alive():
        log("宿主服务已在跑")
    else:
        start_host()
        for i in range(75):
            time.sleep(1)
            if host_alive(0.8):
                log(f"宿主服务就绪（{i + 1}s）")
                break
        else:
            log("宿主服务 75s 还没起来——桌宠可能不会出现，看一下 ~/.dsh/logs")
            return

    if vv_alive():
        log("VOICEVOX 引擎已在跑")
    else:
        if start_voicevox():
            for i in range(40):
                time.sleep(1)
                if vv_alive(0.8):
                    log(f"VOICEVOX 就绪（{i + 1}s），预热音色 …")
                    warm_voicevox()
                    break
            else:
                log("VOICEVOX 40s 没起来，日语会退回 edge 音色")

    if voice_alive():
        log("语音桥已在跑（麦克风不被抢）")
    else:
        start_voice()
        for i in range(40):
            time.sleep(1)
            if voice_alive():
                log(f"语音桥就绪（{i + 1}s），喊「小鱼」")
                break
        else:
            log("语音桥没起来，看一眼 pet-voice/run.log")
            return
    log("都好了")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"启动失败：{e}")
        raise
