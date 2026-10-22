# -*- coding: utf-8 -*-
"""让桌宠右键菜单里的「对话」聊天框跟随中/日语言模式。

问题：聊天框走插件的 /chat，人设是 config.jsonc 里写死的中文 whisperPrompt，
和语音链路的 pet_lang 完全无关，所以切到日语后聊天框照样回中文。

改法：在插件拼 system 提示词的地方（lib/index.js 的 petSystemPrompt）读一次
pet_lang.json 的 mode，追加一行语言要求。切语言后下一次对话立即生效，不用重启。

    python patch_chat_lang.py          # 打补丁
    python patch_chat_lang.py --check  # 只看状态
"""
import os
import shutil
import sys

import config

PLUGIN = config.dsh_pet_dir()
BASE = os.path.dirname(os.path.abspath(__file__))
BACKUP = os.path.join(BASE, "backup_dshpet")
LANG_FILE = os.path.join(BASE, "pet_lang.json")

MARK = "【语言】"

ANCHOR = "\tconst petSystemPrompt = (petId, cfg) => {"

HELPER = """\t/** 聊天框只用文字、不朗读，所以永远走中文——日语模式的声音由语音桥单独处理 */
\tconst languageHint = () => {
\t\ttry {
\t\t\tconst j = JSON.parse(readFileSync(%r, "utf8"));
\t\t\tconst ja = j && j.mode === "ja";
\t\t\treturn "\\n【语言】现在用中文说话：整段回复必须是中文，不要输出日文；"
\t\t\t\t+ "历史里就算有日语也不要跟着说日语。"
\t\t\t\t+ (ja ? "瑞哥听的是另外配的日语语音，这里只负责给他看懂文字。" : "");
\t\t} catch {
\t\t\treturn "";
\t\t}
\t};
""" % LANG_FILE

OLD_RET = '\t\treturn time ? base + "\\n" + time : base;'
NEW_RET = """\t\tconst lang = languageHint();
\t\tconst parts = [base];
\t\tif (time) parts.push(time);
\t\tif (lang) parts.push(lang);
\t\treturn parts.join("\\n");"""


def read(p):
    with open(p, "r", encoding="utf-8", newline="") as f:
        return f.read()


def write(p, s):
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(s)


def main():
    path = os.path.join(PLUGIN, "lib", "index.js")
    s = read(path)

    if "--check" in sys.argv:
        print("index.js:", "已含语言注入" if MARK in s else "未打补丁")
        print("语言文件:", LANG_FILE, "存在" if os.path.exists(LANG_FILE) else "不存在")
        return 0

    if MARK in s:
        print("已经打过了，不用重复。")
        return 0

    if ANCHOR not in s:
        print("!! 找不到 petSystemPrompt 锚点，插件版本可能变了")
        return 1
    if OLD_RET not in s:
        print("!! 找不到 return 锚点，插件版本可能变了")
        return 1

    os.makedirs(BACKUP, exist_ok=True)
    dst = os.path.join(BACKUP, "index.js")
    if not os.path.exists(dst):
        shutil.copy2(path, dst)
        print("备份 lib/index.js")

    s = s.replace(ANCHOR, HELPER + ANCHOR, 1)
    s = s.replace(OLD_RET, NEW_RET, 1)
    write(path, s)
    print("已打补丁：聊天框会跟随语言模式")
    print("重启桌宠后生效（点桌面图标即可）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
