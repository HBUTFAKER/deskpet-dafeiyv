# -*- coding: utf-8 -*-
"""在桌面生成「蓝色大肥鱼」快捷方式（图标是她的大头照）。

⚠ 目标解释器刻意用**基础版** pythonw.exe，不走 .venv\\Scripts\\pythonw.exe：
   后者是 venv 的重定向壳，找不到基础解释器时会弹
   "Python venv launcher is sorry to say ..."，而且什么活都干不了。
   launcher.py 只用标准库，基础解释器完全够用。
   退出不靠桌面图标，走大肥鱼右键菜单里的「退出大肥鱼」。
"""
import os

from pylnk3 import for_file

import config

BASE = os.path.dirname(os.path.abspath(__file__))
DESK = os.path.expanduser("~/Desktop")
PYW = config.pythonw() or os.path.join(BASE, ".venv", "Scripts", "pythonw.exe")

# 早先那个独立的「退出大肥鱼」图标已经废弃：退出改到右键菜单里了
STALE = os.path.join(DESK, "退出大肥鱼.lnk")
if os.path.exists(STALE):
    os.remove(STALE)
    print("已删除旧图标：退出大肥鱼.lnk")

out = os.path.join(DESK, "蓝色大肥鱼.lnk")
if os.path.exists(out):
    os.remove(out)

lnk = for_file(
    PYW,
    arguments='"%s"' % os.path.join(BASE, "launcher.py"),
    description="启动大肥鱼桌宠",
    icon_file=os.path.join(BASE, "fatuiyu.ico"),
    work_dir=BASE,
)
lnk.save(out)
print("OK", out, os.path.getsize(out), "bytes")
