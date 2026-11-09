# -*- coding: utf-8 -*-
"""大肥鱼一键退出：桌宠宿主 → 语音桥 → 日语引擎 → 桌宠窗口 → 启动器。

匹配命令行而不是进程名，免得误杀别的 python / node / electron。
独立模式下 standalone.js 是宿主，必须先死，否则它会把桌面窗口重新拉起来。
"""
import os
import sys
import time

import psutil

import config

BASE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(BASE, "quit.log")

VV_EXE = os.path.join(config.voicevox_dir() or "", "run.exe")

TARGETS = [
    ("桌宠宿主", os.path.join("dsh-pet", "lib", "standalone.js")),
    ("语音桥", "pet_voice.py"),
    ("菜单桥", "pet_menu.py"),
    ("日语引擎", VV_EXE),
    ("桌宠窗口", os.path.join(".dsh", "electron", "electron.exe")),
    ("启动器", os.path.join(BASE, "launcher.py")),
]

# 宿主死后给它的重启逻辑一点时间走完，再补刀窗口
SETTLE = {"桌宠宿主": 1.2}


def log(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def find_like(pattern):
    hit = []
    if not pattern:
        return hit
    for p in psutil.process_iter(["pid", "cmdline"]):
        try:
            cmd = " ".join(p.info.get("cmdline") or [])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        if cmd and pattern in cmd:
            hit.append(p)
    return hit


def kill_like(tag, pattern, tries=2):
    """按命令行特征杀进程；先 terminate 再 kill 兜底"""
    total = 0
    for _ in range(tries):
        hit = find_like(pattern)
        if not hit:
            break
        for p in hit:
            try:
                p.terminate()
                total += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        try:
            psutil.wait_procs(hit, timeout=2.0)
        except Exception:
            pass
        for p in hit:                      # 还活着的强杀
            try:
                if p.is_running() and p.status() != psutil.STATUS_ZOMBIE:
                    p.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    if total:
        log("%s：关了 %d 个进程" % (tag, total))
    return total


def main():
    dry = "--dry" in sys.argv
    if dry:
        print("（预演模式，不会真的关）")
        for tag, pattern in TARGETS:
            hit = find_like(pattern)
            print("%s：%d 个" % (tag, len(hit)))
            for p in hit:
                try:
                    print("   ", p.pid, " ".join(p.info.get("cmdline") or [])[:110])
                except Exception:
                    print("   ", p.pid, "(读不到命令行)")
        return 0

    log("收到退出指令")
    n = 0
    for tag, pattern in TARGETS:
        n += kill_like(tag, pattern)
        time.sleep(SETTLE.get(tag, 0))
    time.sleep(0.4)
    left = 0
    for _tag, pattern in TARGETS:
        if find_like(pattern):
            left += 1
    log("完成，共关 %d 个%s" % (n, "，仍有残留" if left else "，全部已退出"))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        log("退出失败：%r" % (e,))
        sys.exit(1)
