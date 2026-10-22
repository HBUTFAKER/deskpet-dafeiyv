# -*- coding: utf-8 -*-
"""一键重打所有插件补丁（升级 dsh-pet 后跑这个就行）。

三个补丁都可重复执行：已经打过的会输出「已打过」并跳过。
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PATCHES = [
    ("patch_quit_menu.py", "右键菜单「退出大肥鱼」"),
    ("patch_lang_switch.py", "右键菜单「切换语言」"),
    ("patch_chat_lang.py", "聊天框永远中文"),
]

if __name__ == "__main__":
    for script, what in PATCHES:
        print("== %s（%s）" % (script, what))
        r = subprocess.run([sys.executable, os.path.join(HERE, script)], cwd=HERE)
        if r.returncode != 0:
            print("   失败，先停下")
            sys.exit(r.returncode)
        print()
    print("全部完成。重启桌宠（点桌面图标）后生效。")
