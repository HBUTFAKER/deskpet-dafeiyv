# -*- coding: utf-8 -*-
"""桌宠右键菜单桥：用 dsh-pet 0.4.7 的第三方菜单 API 补回「退出 / 切语言」。

旧版靠给插件文件打补丁加菜单，新版锚点全变了、补丁打不上；
这里改用官方 /menu/item + /menu/events 接口，不碰插件源码。

切语言只写 pet_lang.json：语音桥的 watch_lang_file 每 1.5s 比对 mtime，
发现变化就自动换音色、换人设并说一句确认语。

    .venv/Scripts/python.exe pet_menu.py
"""
import os
import sys
import json
import time
import socket
import subprocess
import urllib.request
import urllib.error

import config

BASE = os.path.dirname(os.path.abspath(__file__))
PY = os.path.join(BASE, ".venv", "Scripts", "python.exe")
PREFIX = config.pet_host() + "/dsh-pet-7340"
RUNTIME = os.path.expanduser("~/.dsh/dsh-pet/standalone-runtime.json")
LANG_FILE = os.path.join(BASE, "pet_lang.json")
NO_WINDOW = 0x08000000

OWNER = "dafeiyu"
LABELS = ["退出大肥鱼", "切换语言"]
MENU_PORT = 47824          # 单实例锁：重复双击不会注册两份菜单
_lock_sock = None


def acquire_single_instance():
    global _lock_sock
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", MENU_PORT))
        s.listen(4)
    except OSError:
        s.close()
        return False
    _lock_sock = s
    return True


def log(msg):
    try:
        print("[%s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)
    except Exception:
        pass


def token():
    """独立模式把访问令牌写在运行时文件里；插件模式没有就不带。"""
    try:
        with open(RUNTIME, encoding="utf-8") as f:
            return (json.load(f) or {}).get("token") or ""
    except Exception:
        return ""


def request(path, body=None, timeout=10):
    headers = {"Content-Type": "application/json"}
    tok = token()
    if tok:
        headers["x-dsh-pet-token"] = tok
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = urllib.request.Request(PREFIX + path, data=data, headers=headers,
                                 method="POST" if body is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8")
    return json.loads(raw) if raw.strip() else {}


def register_menu():
    return request("/menu/item", {"owner": OWNER, "labels": LABELS, "target": "desktop"})


def current_mode():
    try:
        with open(LANG_FILE, encoding="utf-8") as f:
            return (json.load(f) or {}).get("mode", "zh")
    except Exception:
        return "zh"


def toggle_lang():
    nxt = "ja" if current_mode() == "zh" else "zh"
    with open(LANG_FILE, "w", encoding="utf-8") as f:
        json.dump({"mode": nxt}, f, ensure_ascii=False)
    log("切换语言 → %s" % nxt)


def do_quit():
    """交给 quit.py 收摊：宿主 → 语音桥 → 日语引擎 → 窗口。"""
    log("菜单点了退出，收摊")
    try:
        subprocess.Popen([PY, os.path.join(BASE, "quit.py")], cwd=BASE,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=NO_WINDOW)
    except Exception as e:
        log("拉起退出脚本失败: %s" % e)


def main():
    if not acquire_single_instance():
        log("已经有一份菜单桥在跑了，这份退出")
        return 0
    registered_for = ""
    while True:
        try:
            tok = token()
            if not tok:
                time.sleep(3)
                continue
            if tok != registered_for:
                register_menu()
                registered_for = tok
                log("右键菜单已注册：%s" % " / ".join(LABELS))
            events = request("/menu/events?owner=%s&wait=5000" % OWNER, timeout=12) or {}
            for label, pet in events.items():
                if not pet:
                    continue
                if label == "退出大肥鱼":
                    do_quit()
                    return 0
                if label == "切换语言":
                    toggle_lang()
        except urllib.error.HTTPError as e:
            log("接口返回 %s，重连" % e.code)
            registered_for = ""
            time.sleep(2)
        except Exception as e:
            log("重连：%s" % e)
            registered_for = ""
            time.sleep(2)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
