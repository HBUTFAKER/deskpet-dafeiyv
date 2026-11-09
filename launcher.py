# -*- coding: utf-8 -*-
"""
大肥鱼一键启动：桌宠窗口 → 日语引擎 → 语音桥。

重复双击只会有一起效果：已经在跑的都跳过。
桌宠走 dsh-pet 独立模式（3080 端口提供 /dsh-pet-7340/state 与 /broadcast），
不再依赖已下线的 dsh web 宿主。

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

import socket

from config import pet_exe, pet_host, voicevox_dir, api_key

# 密钥 / 本机路径统一走 config.py（环境变量 > config.local.json > 自动探测）。
PET_EXE = pet_exe()
PET_HOST = pet_host()
VV_DIR = voicevox_dir()
API_KEY = api_key()

HOST_STATE = PET_HOST + "/dsh-pet-7340/state"
VOICE_PORT = 47823
MENU_PORT = 47824
VOICE_HELLO = b"FATUIYU\n"
NO_WINDOW = 0x08000000

VV_PORT = 50021
VV_STATE = f"http://127.0.0.1:{VV_PORT}/version"

PIDS = os.path.join(BASE, "pids.json")


def record(**kv):
    """把起出来的进程 pid 记下来：退出时照着这张表逐个收。"""
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


def menu_alive():
    try:
        with socket.create_connection(("127.0.0.1", MENU_PORT), timeout=0.8):
            return True
    except Exception:
        return False


def start_host():
    """拉起独立桌宠：自带 3080 端口的桌宠窗口与气泡接口。"""
    if not PET_EXE or not os.path.isfile(PET_EXE):
        log("找不到 dsh-pet 独立入口：桌宠窗口不会出现，但仍能听见语音")
        return False
    env = dict(os.environ)
    if API_KEY:
        env["DEEPSEEK_API_KEY"] = API_KEY
    env.setdefault("DSH_PET_ELECTRON_MIRROR", "https://npmmirror.com/mirrors/electron/")
    log(f"启动桌宠 … {PET_EXE}")
    # 输出落盘，起不来时能直接看到原因
    hf = open(os.path.join(BASE, "host.log"), "ab", buffering=0)
    cwd = os.path.dirname(PET_EXE)
    if PET_EXE.lower().endswith((".cmd", ".bat")):
        p = subprocess.Popen(f'"{PET_EXE}"', shell=True, cwd=cwd, env=env,
                             stdout=hf, stderr=subprocess.STDOUT,
                             creationflags=NO_WINDOW)
    else:
        p = subprocess.Popen([PET_EXE], cwd=cwd, env=env,
                             stdout=hf, stderr=subprocess.STDOUT,
                             creationflags=NO_WINDOW)
    record(host=p.pid)
    return True


def start_voice():
    if not os.path.isfile(PY):
        log("找不到 .venv/Scripts/python.exe，先跑 setup.bat 建虚拟环境")
        return False
    log("启动语音桥 …")
    rf = open(os.path.join(BASE, "run.log"), "ab", buffering=0)
    p = subprocess.Popen([PY, "-u", os.path.join(BASE, "pet_voice.py")],
                         cwd=BASE, stdout=rf, stderr=subprocess.STDOUT,
                         creationflags=NO_WINDOW)
    record(voice=p.pid)
    return True


def start_menu():
    """右键菜单桥：注册「退出大肥鱼 / 切换语言」，跟着语音桥常驻。"""
    if not os.path.isfile(PY):
        return
    log("启动右键菜单桥 …")
    mf = open(os.path.join(BASE, "menu.log"), "ab", buffering=0)
    p = subprocess.Popen([PY, "-u", os.path.join(BASE, "pet_menu.py")],
                         cwd=BASE, stdout=mf, stderr=subprocess.STDOUT,
                         creationflags=NO_WINDOW)
    record(menu=p.pid)


def vv_alive(timeout=1.5):
    try:
        urllib.request.urlopen(VV_STATE, timeout=timeout).read(32)
        return True
    except Exception:
        return False


def start_voicevox():
    """本地日语引擎（古河渚音色的来源）；起不来不影响中文"""
    exe = os.path.join(VV_DIR, "run.exe") if VV_DIR else ""
    if not exe or not os.path.exists(exe):
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
        log("桌宠已在跑")
    elif start_host():
        for i in range(75):
            time.sleep(1)
            if host_alive(0.8):
                log(f"桌宠就绪（{i + 1}s）")
                break
        else:
            log("桌宠 75s 没起来——窗口可能不会出现，看 host.log")
    else:
        log("桌宠未启动，继续拉语音链路（听得到、看不到气泡）")

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
    elif start_voice():
        for i in range(40):
            time.sleep(1)
            if voice_alive():
                log(f"语音桥就绪（{i + 1}s），喊「小鱼」")
                break
        else:
            log("语音桥没起来，看一眼 run.log")
            return
    if not menu_alive():
        start_menu()
    if not API_KEY:
        log("提醒：还没配 DeepSeek API Key，对话会回「网络不听使唤」；"
            "填 config.local.json 的 api_key 或设环境变量 DEEPSEEK_API_KEY")
    log("都好了")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"启动失败：{e}")
        raise
