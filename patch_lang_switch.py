# -*- coding: utf-8 -*-
"""右键菜单加「切换语言」：点一下就在中文/日语之间切，不用说话。

原理：菜单项让主进程写 pet_lang.json，语音桥本来就盯着这个文件的 mtime，
改完它自己会热切换音色和人设（还会说一句确认语）。

    python patch_lang_switch.py          # 打补丁
    python patch_lang_switch.py --check  # 只看状态
"""
import os
import shutil
import sys

import config

HELPER = os.path.join(config.dsh_pet_dir(), "runtime", "electron-helper")
BASE = os.path.dirname(os.path.abspath(__file__))
BACKUP = os.path.join(BASE, "backup_dshpet")
LANG_FILE = os.path.join(BASE, "pet_lang.json")

MARK = "切换语言"

# ---------------------------------------------------------------- preload.js
PRE_OLD = """  quitApp() {
    ipcRenderer.send('pet:quit-app');
  },"""
PRE_NEW = """  quitApp() {
    ipcRenderer.send('pet:quit-app');
  },
  // 右键菜单「切换语言」：读/写 pet_lang.json，语音桥盯着这个文件热切换
  getLang() {
    return ipcRenderer.sendSync('pet:get-lang');
  },
  switchLang(mode) {
    ipcRenderer.send('pet:switch-lang', { mode });
  },"""

# ---------------------------------------------------------------- main.js
MAIN_ANCHOR = "// ---- 退出脚本（右键菜单「退出大肥鱼」用）----"
MAIN_NEW = """// ---- 语言切换（右键菜单「切换」用）----
// 只改 pet_lang.json：语音桥每 1.5s 比对 mtime，改完自动换音色/人设并说一句确认语。
const LANG_FILE = %r;
const readLangMode = () => {
  try {
    const j = JSON.parse(readFileSync(LANG_FILE, "utf8"));
    return j && j.mode === "ja" ? "ja" : "zh";
  } catch {
    return "zh";
  }
};
ipcMain.on("pet:get-lang", (event) => {
  event.returnValue = readLangMode();
});
ipcMain.on("pet:switch-lang", (event, payload) => {
  const want = payload && payload.mode === "ja" ? "ja" : "zh";
  try {
    writeFileSync(LANG_FILE, JSON.stringify({ mode: want }), "utf8");
    console.error("[dsh-pet-desktop-helper] lang -> " + want);
  } catch (error) {
    console.error("[dsh-pet-desktop-helper] lang switch failed:", error);
  }
});

""" % LANG_FILE

# ---------------------------------------------------------------- sprite.js
SPR_OLD = """    tools.push(
      { label: '碎碎念', action: 'whisper' },"""
SPR_NEW = """    // 当前语言（主进程读 pet_lang.json）：决定菜单上写「切换日语」还是「切回中文」
    const curLang = window.petBridge && window.petBridge.getLang ? window.petBridge.getLang() : 'zh';
    tools.push(
      { label: curLang === 'ja' ? '切回中文' : '切换日语', action: 'switch-lang' },
      { label: '碎碎念', action: 'whisper' },"""

SPR_ACT_OLD = """    if (leaf.action === 'quit') {"""
SPR_ACT_NEW = """    if (leaf.action === 'switch-lang') {
      const cur = window.petBridge && window.petBridge.getLang ? window.petBridge.getLang() : 'zh';
      if (window.petBridge && window.petBridge.switchLang) window.petBridge.switchLang(cur === 'ja' ? 'zh' : 'ja');
      return;
    }
    if (leaf.action === 'quit') {"""


def read(p):
    with open(p, "r", encoding="utf-8", newline="") as f:
        return f.read()


def write(p, s):
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(s)


def patch(path, old, new, label, guard):
    """guard 是补丁留下的特征串：已经在文件里就说明打过了，绝不再插一遍"""
    s = read(path)
    if guard in s:
        print("  已打过：", label)
        return False
    if old not in s:
        print("  !! 找不到锚点：", label)
        return False
    write(path, s.replace(old, new, 1))
    print("  已修改：", label)
    return True


def main():
    if "--check" in sys.argv:
        s = read(os.path.join(HELPER, "sprite.js"))
        print("语言切换菜单:", "已存在" if MARK in s else "没有")
        print("语言文件:", LANG_FILE, "存在" if os.path.exists(LANG_FILE) else "不存在")
        return 0

    os.makedirs(BACKUP, exist_ok=True)
    for f in ("preload.js", "main.js", "sprite.js"):
        src = os.path.join(HELPER, f)
        dst = os.path.join(BACKUP, f)
        if not os.path.exists(dst):
            shutil.copy2(src, dst)
            print("  备份：", f)

    patch(os.path.join(HELPER, "preload.js"), PRE_OLD, PRE_NEW,
          "preload.js 暴露 getLang/switchLang", "getLang()")
    patch(os.path.join(HELPER, "main.js"), MAIN_ANCHOR, MAIN_NEW + MAIN_ANCHOR,
          "main.js 读写 pet_lang.json", "const LANG_FILE")
    patch(os.path.join(HELPER, "sprite.js"), SPR_OLD, SPR_NEW,
          "sprite.js 菜单加「切换语言」", "switch-lang")
    patch(os.path.join(HELPER, "sprite.js"), SPR_ACT_OLD, SPR_ACT_NEW,
          "sprite.js 点击分发", "leaf.action === 'switch-lang'")
    print("\n完成。重启桌宠后生效。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
