# -*- coding: utf-8 -*-
"""给桌宠右键菜单加「退出大肥鱼」。

改的是插件运行时的三个文件（升级 dsh-pet 会覆盖，重跑本脚本即可复原）：
  preload.js  → 暴露 petBridge.quitApp()
  main.js     → 收到 pet:quit-app 就拉起退出脚本
  sprite.js   → 菜单加一项 + 点击分发

    python patch_quit_menu.py          # 打补丁
    python patch_quit_menu.py --check  # 只看有没有打过
"""
import os
import shutil
import sys

import config

HELPER = os.path.join(config.dsh_pet_dir(), "runtime", "electron-helper")
BASE = os.path.dirname(os.path.abspath(__file__))
BACKUP = os.path.join(BASE, "backup_dshpet")

# 退出不再拉外部 python（那条路一坏就只弹窗不干活）；main.js 改成按 pid 直接收。
# 这里保留引用仅用于旧版回退判断，新逻辑不依赖它。
QUIT_EXE = os.path.join(BASE, ".venv", "Scripts", "pythonw.exe")
QUIT_PY = os.path.join(BASE, "quit.py")

MARK = "退出大肥鱼"


def read(p):
    with open(p, "r", encoding="utf-8", newline="") as f:
        return f.read()


def write(p, s):
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(s)


# ---------------------------------------------------------------- 三处补丁
PRE_OLD = """  openDshSite(url) {
    ipcRenderer.send('pet:open-site', { url });
  },"""
PRE_NEW = """  openDshSite(url) {
    ipcRenderer.send('pet:open-site', { url });
  },
  // 右键菜单「退出大肥鱼」：走宿主侧退出脚本，把语音桥 / 宿主服务 / 日语引擎一起收掉
  quitApp() {
    ipcRenderer.send('pet:quit-app');
  },"""

MAIN_OLD = "  // 显示器热更新：分辨率/缩放变化、插拔屏、旋转都会让桌面几何失效。"
MAIN_NEW = """  // 右键菜单「退出大肥鱼」：全部在本进程里做掉，不拉任何外部程序。
  // 以前是 spawn 一个 venv 里的 pythonw 去跑 quit.py——解释器一失效就只弹个报错窗、
  // 鱼还活得好好的（截图那个 "Python venv launcher is sorry to say"）。
  ipcMain.on('pet:quit-app', () => {
    try {
      const { readFileSync } = require('node:fs');
      const { join } = require('node:path');
      let pids = {};
      try {
        pids = JSON.parse(readFileSync(join(QUIT_CWD, 'pids.json'), 'utf8')) || {};
      } catch {}
      const die = (pid) => {
        try {
          if (pid) process.kill(pid);
        } catch {}
      };
      // 先收语音桥和日语引擎，宿主留到最后——它一死会顺手把本进程也带走
      die(pids.voice);
      die(pids.voicevox);
      die(process.ppid);
    } catch (error) {
      console.error('[dsh-pet-desktop-helper] quit failed:', error);
    }
    setTimeout(() => app.exit(0), 400);
  });

  // 显示器热更新：分辨率/缩放变化、插拔屏、旋转都会让桌面几何失效。"""

QUIT_CONST = """
// ---- 退出脚本（右键菜单「退出大肥鱼」用）----
const QUIT_EXE = %r;
const QUIT_PY = %r;
const QUIT_CWD = %r;
""" % (QUIT_EXE, QUIT_PY, BASE)

MAIN_CONST_ANCHOR = "const { execFileSync } = require('node:child_process');"

SPR_OLD = "      { label: '重载配置', action: 'reload' },\n    );"
SPR_NEW = ("      { label: '重载配置', action: 'reload' },\n"
           "      // 关掉整个大肥鱼：语音桥 / 宿主 / 日语引擎一起收，不只是关这个窗口\n"
           "      { label: '退出大肥鱼', action: 'quit' },\n    );")

SPR_ACT_OLD = """    if (leaf.action === 'reload') {
      this.reloadDesktop(); // 请宿主重启桌面 Helper：全部桌面宠物窗口按最新配置重建
      return;
    }"""
SPR_ACT_NEW = """    if (leaf.action === 'reload') {
      this.reloadDesktop(); // 请宿主重启桌面 Helper：全部桌面宠物窗口按最新配置重建
      return;
    }
    if (leaf.action === 'quit') {
      // 交给主进程拉退出脚本：连语音桥 / 宿主 / 日语引擎一起停
      if (window.petBridge && window.petBridge.quitApp) window.petBridge.quitApp();
      return;
    }"""


def patch(path, old, new, label, guard=None):
    """guard 是补丁留下的特征串：已存在就不再插一遍（升级后重跑要幂等）"""
    s = read(path)
    if guard and guard in s:
        print("  已打过：", label)
        return False
    if old not in s:
        print("  !! 找不到锚点：", label)
        return False
    write(path, s.replace(old, new, 1))
    print("  已修改：", label)
    return True


def main():
    check = "--check" in sys.argv
    files = ["preload.js", "main.js", "sprite.js"]
    if check:
        for f in files:
            s = read(os.path.join(HELPER, f))
            print("%-11s %s" % (f, "已含退出菜单" if MARK in s else "未打补丁"))
        return 0

    os.makedirs(BACKUP, exist_ok=True)
    for f in files:
        src = os.path.join(HELPER, f)
        dst = os.path.join(BACKUP, f)
        if not os.path.exists(dst):
            shutil.copy2(src, dst)
            print("  备份：", f)

    patch(os.path.join(HELPER, "preload.js"), PRE_OLD, PRE_NEW,
          "preload.js 暴露 quitApp", "quitApp()")
    patch(os.path.join(HELPER, "main.js"), MAIN_CONST_ANCHOR,
          MAIN_CONST_ANCHOR + QUIT_CONST, "main.js 写入退出脚本路径", "QUIT_EXE")
    patch(os.path.join(HELPER, "main.js"), MAIN_OLD, MAIN_NEW,
          "main.js 处理 pet:quit-app", "pet:quit-app")
    patch(os.path.join(HELPER, "sprite.js"), SPR_OLD, SPR_NEW,
          "sprite.js 菜单加一项", MARK)
    patch(os.path.join(HELPER, "sprite.js"), SPR_ACT_OLD, SPR_ACT_NEW,
          "sprite.js 点击分发", "leaf.action === 'quit'")
    print("\n完成。重启桌宠后生效。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
