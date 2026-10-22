# -*- coding: utf-8 -*-
"""运行配置加载：本文件不含任何明文密钥。

读取优先级（从高到低）：
    1. 环境变量（便于 CI / 临时覆盖）
    2. config.local.json（本机私有配置，已被 .gitignore 排除，不入库）
    3. 自动探测 / 默认值

config.local.json 结构示例见 config.example.json。
"""
import os
import json
import glob

BASE = os.path.dirname(os.path.abspath(__file__))

# key -> 对应的环境变量名
_ENV = {
    "api_key": "DEEPSEEK_API_KEY",
    "node_dir": "WORKBUDDY_NODE_DIR",
    "voicevox_dir": "VOICEVOX_DIR",
    "dsh_pet_dir": "DSH_PET_DIR",
}


def _load_local():
    p = os.path.join(BASE, "config.local.json")
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f) or {}
        except Exception:
            pass
    return {}


_local = _load_local()


def get(key, default=None):
    if key in _ENV and os.environ.get(_ENV[key]):
        return os.environ[_ENV[key]]
    if key in _local and _local[key]:
        return _local[key]
    return default


# ------------------------------------------------------------ 自动探测
def detect_node_dir():
    cand = sorted(glob.glob(os.path.expanduser("~/.workbuddy/binaries/node/versions/*")))
    cand = [c for c in cand if os.path.isdir(c)]
    return cand[-1] if cand else None


def detect_pythonw():
    cand = sorted(
        glob.glob(os.path.expanduser("~/.workbuddy/binaries/python/versions/*/pythonw.exe"))
    )
    return cand[-1] if cand else None


def detect_dsh_pet_dir():
    return os.path.expanduser("~/.dsh/profiles/web/node_modules/dsh-pet")


# ------------------------------------------------------------ 对外接口
def api_key():
    return get("api_key")


def node_dir():
    return get("node_dir") or detect_node_dir()


def voicevox_dir():
    return get("voicevox_dir") or r"D:\voicevox\windows-cpu"


def dsh_pet_dir():
    return get("dsh_pet_dir") or detect_dsh_pet_dir()


def pythonw():
    return detect_pythonw()
