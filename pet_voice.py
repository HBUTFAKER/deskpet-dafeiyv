# -*- coding: utf-8 -*-
"""
大肥鱼语音桥 —— 给 dsh-pet 桌宠接上「耳朵和嘴」

自带整套运行环境（不再依赖旧的 dafeiyu-pet 项目）：
  · faster-whisper 本地识别（models/whisper-small）
  · edge-tts 合成，按语言各一条连接池
  · 人设、音色、唤醒词、报时全在语言包里（pet_lang.py）

用法：
    .venv/Scripts/python.exe pet_voice.py

中文：喊「小鱼」；日语：喊「さかなちゃん」。
说「说日语 / 日本語にして」切日语，说「说中文 / 中国語にして」切回来；
模式记在 pet_lang.json，重启后保持。
"""
import os
import re
import sys
import time
import uuid
import json
import random
import socket
import tempfile
import threading
import traceback
import urllib.request

# 控制台中文不炸
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import numpy as np

import sounddevice as sd
import pygame
from faster_whisper import WhisperModel
from edge_tts_pool import EdgePool
import voicevox_pool as VV

# ---------------- 配置 ----------------
import config
API_KEY = os.environ.get("DEEPSEEK_API_KEY") or config.api_key()
MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
CONV_WINDOW = 45.0          # 唤醒后对话窗口（秒）
TMP = tempfile.gettempdir()

# 语言（中文 / 日本語）全部由语言包提供：音色、语速、人设、唤醒词、识别语言
import pet_lang as L


# ---------------- 长期记忆：他说的关于自己的事 ----------------
FACT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pet_memory.json")
_facts = []
_facts_lock = threading.Lock()
_recall_cache = {}


def _recall_re():
    """当前语言的自述句正则（编译一次缓存）"""
    m = L.mode()
    if m not in _recall_cache:
        _recall_cache[m] = re.compile(L.pack(m)["recall"])
    return _recall_cache[m]


def load_facts():
    global _facts
    try:
        with open(FACT_FILE, encoding="utf-8") as f:
            data = json.load(f)
        _facts = [s for s in data if isinstance(s, str)][:40]
    except Exception:
        _facts = []


def save_facts():
    try:
        with open(FACT_FILE, "w", encoding="utf-8") as f:
            json.dump(_facts, f, ensure_ascii=False, indent=1)
    except Exception as e:
        log("MEM", f"存不下: {e}")


def maybe_remember(text):
    """他说到自己的事就记一句，下次能主动提"""
    t = (text or "").strip()
    if not (4 <= len(t) <= 60) or not _recall_re().search(t):
        return
    with _facts_lock:
        if any(t in f or f in t for f in _facts):
            return
        _facts.append(t)
        del _facts[:-40]
        save_facts()
    log("MEM", f"记住：{t}")


def _facts_context():
    with _facts_lock:
        if not _facts:
            return ""
        lines = "；".join(_facts[-12:])
    return f"【本鱼还记着他这些事】{lines}。这些是他亲口说的，聊天时可以自然带上，别硬塞。\n"

_STT_HALLUCINATIONS = (
    "谢谢观看", "感謝觀看", "感谢观看", "谢谢大家观看", "感谢您的观看", "感谢收看",
    "感谢您的收看", "請不吝點贊", "请不吝点赞", "点赞订阅", "訂閱", "订阅转发",
    "转发打赏", "字幕由", "字幕组提供", "字幕志愿者", "amara", "明镜与点点",
    "点点栏目", "请点赞", "点个赞", "一键三连", "本视频", "下期再见", "下集再见",
    "谢谢支持", "感谢支持", "谢谢观看视频", "谢谢观看本视频",
    "youtube", "mingpao", "订阅频道", "我的频道", "视频字幕",
)


def hallucinations():
    """当前语言额外的幻听词（日语视频里那套客套话）"""
    return _STT_HALLUCINATIONS + tuple(L.pack().get("hallucinations") or [])


def wake_tokens():
    return L.pack()["wake"]


# 桌宠气泡：说话时把同一句文字推到桌宠身上那个白气泡里（顺带触发它的说话动作）。
# 走 dsh-pet 的 broadcast 端点——它内部就是写 pets.<id>.say，渲染层 1s 内取到并弹泡。
# 0.4.7 独立模式要求 surface 参数 + 本机令牌（写在 standalone-runtime.json）；
# 老版插件模式没有这个文件，就退回不带令牌的原行为。
PET_HOST = config.pet_host()
BUBBLE_URL = os.environ.get("DSH_PET_BUBBLE_URL", PET_HOST + "/dsh-pet-7340/broadcast")
PET_ID = os.environ.get("DSH_PET_ID", "main")
RUNTIME_FILE = os.path.expanduser("~/.dsh/dsh-pet/standalone-runtime.json")


def _pet_token():
    """读独立模式的本机访问令牌；插件模式没有这个文件就返回空串。"""
    try:
        with open(RUNTIME_FILE, encoding="utf-8") as f:
            return (json.load(f) or {}).get("token") or ""
    except Exception:
        return ""

# ---------------- 共享状态 ----------------
_gen = 0                     # TTS 代次：递增即打断
_playing_text = ""           # 正在播的文本（回采过滤）
_tts_active = False
_conv_until = 0.0
_mute_until = 0.0
_state_lock = threading.Lock()

_model = None
_model_lock = threading.Lock()
_pools = {}                 # 引擎|音色 → EdgePool / VoicevoxPool
_pool_lock = threading.Lock()
_history = []                # 对话历史（最近 8 轮）
_hist_lock = threading.Lock()


def log(tag, msg):
    print(f"[{time.strftime('%H:%M:%S')}] {tag} {msg}", flush=True)


def _squash(text):
    """只留中日文字与数字，日语假名千万别滤掉，否则整句会被当成幻听"""
    return re.sub(r"[^\u3040-\u30ff\u4e00-\u9fff0-9A-Za-z]", "", text or "")


def looks_like_hallucination(text):
    t = _squash(text)
    if not t:
        return True
    if len(t) <= 26 and any(p in t.lower() for p in hallucinations()):
        return True
    if len(t) >= 6 and len(set(t)) <= 2:
        return True
    return False


def ensure_model():
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is None:
            # 1) 优先用本地 models/ 里的量化模型（离线、最快）
            for name in ("whisper-small", "whisper-base"):
                d = os.path.join(MODEL_DIR, name)
                if os.path.exists(os.path.join(d, "model.bin")):
                    log("ASR", f"加载本地模型 {name} …")
                    _model = WhisperModel(d, device="cpu", compute_type="int8")
                    log("ASR", "模型就绪")
                    break
            # 2) 本地没有就走 HuggingFace 自动下载（首次运行会拉 ~1.5GB，之后缓存）
            if _model is None:
                for size in ("small", "base"):
                    try:
                        log("ASR", f"本地无模型，从 HuggingFace 下载 whisper-{size}（首次较慢）…")
                        _model = WhisperModel(size, device="cpu", compute_type="int8")
                        log("ASR", "模型下载并加载完成")
                        break
                    except Exception as e:
                        log("ASR", f"whisper-{size} 下载失败：{e}")
            if _model is None:
                raise RuntimeError("未能加载语音识别模型（本地缺失且 HuggingFace 下载失败）")
    return _model


def get_pool(pack=None):
    """按「引擎 + 音色」缓存：中文一条 edge，日语一个本地 VOICEVOX"""
    pack = pack or L.pack()
    use_vv = pack.get("engine") == "voicevox" and VV.alive()
    if use_vv:
        key = "vv|%s|%s" % (pack.get("vv_speaker", ""), pack.get("vv_style", ""))
    else:
        key = "edge|%s" % pack["voice"]
    p = _pools.get(key)
    if p is not None:
        return p
    with _pool_lock:
        p = _pools.get(key)
        if p is None:
            p = (VV.VoicevoxPool(pack["vv_speaker"], pack["vv_style"])
                 if use_vv else EdgePool(pack["voice"]))
            try:
                p.warm()
            except Exception:
                pass
            _pools[key] = p
    return p


# ---------------- 说话 ----------------
def _sapi_speak(text):
    """edge-tts 挂了时的离线兜底"""
    try:
        import subprocess
        ps = ("Add-Type -AssemblyName System.Speech;"
              "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
              f"$s.Rate = 2; $s.Speak({json.dumps(text, ensure_ascii=False)})")
        subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       capture_output=True, timeout=60)
    except Exception as e:
        log("TTS", f"本机语音也失败: {e}")


# ---------------- 气泡 ----------------
def show_bubble(text):
    """把这句文字推到桌宠气泡上（失败一律静默：桌宠没开着也能只听声音）"""
    text = (text or "").strip()
    if not text:
        return
    time.sleep(0.12)                       # 让 TTS 先抢到播放通道，气泡这边稍后一拍，看着更同步
    body = json.dumps({"text": text}, ensure_ascii=False).encode("utf-8")
    sep = "&" if "?" in BUBBLE_URL else "?"
    url = f"{BUBBLE_URL}{sep}pet={PET_ID}&surface=desktop"
    headers = {"Content-Type": "application/json"}
    tok = _pet_token()
    if tok:
        headers["x-dsh-pet-token"] = tok
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=2.0) as r:
            r.read(200)
    except Exception as e:
        log("BUBBLE", f"推送失败（桌宠没开？）{e}")


def show_bubble_async(text):
    threading.Thread(target=show_bubble, args=(text,), daemon=True).start()


def bubble_alive():
    """桌宠那边在不在（只用于启动时给一句提示）"""
    try:
        urllib.request.urlopen(PET_HOST + "/dsh-pet-7340/state", timeout=2.0).read(64)
        return True
    except Exception:
        return False


def _bubble_for(text):
    """日语模式下气泡要显示中文：先查固定台词对照表，查不到就原样"""
    table = L.pack().get("bubble") or {}
    return table.get(text, text)


def speak(text, bubble=None):
    """同步朗读一句（新调用会打断旧的）。
    bubble 是气泡里显示的文字，默认跟朗读文本一致。"""
    global _gen, _playing_text, _tts_active
    text = (text or "").strip()
    if not text:
        return
    if bubble is None:
        bubble = _bubble_for(text)
    with _state_lock:
        _gen += 1
        gen = _gen
        _playing_text = text
        _tts_active = True
    try:
        pygame.mixer.music.stop()
    except Exception:
        pass

    tid = uuid.uuid4().hex[:8]
    pack = L.pack()
    ok = False
    mp3 = os.path.join(TMP, f"pet_tts_{tid}.mp3")
    try:
        if pack.get("engine") == "voicevox" and VV.alive():
            wav = os.path.join(TMP, f"pet_tts_{tid}.wav")
            ok = get_pool(pack).synth(
                text, pack.get("vv_speed", 1.0), pack.get("vv_pitch", 0.0),
                pack.get("vv_volume", 1.0), wav,
                intonation=pack.get("vv_intonation", 1.0))
            if ok:
                mp3 = wav
        if not ok:                          # 引擎没起来 / 合成失败 → edge 顶上
            ok = get_pool(dict(pack, engine="edge")).synth(
                text, pack["rate"], pack["pitch"], pack["volume"], mp3)
    except Exception as e:
        log("TTS", f"合成异常: {e}")
    if gen != _gen:
        return
    show_bubble_async(bubble)              # 文字和声音一起出现（日语模式：声音日语、文字中文）
    if not ok:
        log("TTS", "在线合成失败，走本机语音")
        _sapi_speak(text)
        with _state_lock:
            _tts_active = False
        return
    try:
        pygame.mixer.music.load(mp3)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            if gen != _gen:
                pygame.mixer.music.stop()
                break
            time.sleep(0.04)
    except Exception as e:
        log("TTS", f"播放失败: {e}")
    finally:
        with _state_lock:
            if gen == _gen:
                _tts_active = False
        try:
            os.remove(mp3)
        except Exception:
            pass


def speak_async(text, bubble=None):
    threading.Thread(target=speak, args=(text, bubble), daemon=True).start()


def stop_speaking():
    global _gen
    with _state_lock:
        _gen += 1
    try:
        pygame.mixer.music.stop()
    except Exception:
        pass


# ---------------- 对话 ----------------
_BILINGUAL_RE = re.compile(
    r"中[文文]?\s*[:：]\s*(.+?)\s*\n+\s*日[文本语]?\s*[:：]\s*(.+)", re.S)


def _split_bilingual(raw):
    """模型按约定给了「中文：… / 日文：…」两行就拆开；没给返回 (None, None)"""
    m = _BILINGUAL_RE.search(raw or "")
    if not m:
        return None, None
    cn = re.sub(r"\s+", " ", m.group(1)).strip()
    ja = re.sub(r"\s+", "", m.group(2)).strip()
    if not (cn and ja):
        return None, None
    return cn, ja


def ask_deepseek(user_text):
    """调 DeepSeek，返回 (朗读文本, 气泡文本)。

    日语模式下模型按人设输出「中文：… / 日文：…」两行：
    日文交给 TTS 念，中文推到气泡——瑞哥听日语、看中文。
    """
    pack = L.pack()
    if not API_KEY:
        log("LLM", "没配 DeepSeek API Key：填 config.local.json 的 api_key 或设环境变量 DEEPSEEK_API_KEY")
        err = pack.get("net_error") or "网络好像不听使唤，等我一下下。"
        return err, err
    msgs = [{"role": "system", "content": pack["system"] + _facts_context() + L.now_context()}]
    with _hist_lock:
        msgs.extend(_history[-16:])
    msgs.append({"role": "user", "content": user_text})
    body = json.dumps({
        "model": "deepseek-chat",
        "messages": msgs,
        "max_tokens": 400,
        "temperature": 0.8,
    }, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        "https://api.deepseek.com/v1/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {API_KEY}",
                 "Content-Type": "application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode("utf-8"))
        reply = data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log("LLM", f"请求失败: {e}")
        err = pack.get("net_error") or "网络好像不听使唤，等我一下下。"
        return err, err
    # 去掉可能出现的 markdown 痕迹，念出来更自然
    reply = re.sub(r"[*#`>]+", "", reply)

    if L.mode() == "ja":
        # 先拆双语——拆之前不能把换行压平，否则两行会糊成一行
        cn, ja = _split_bilingual(reply)
        if cn and ja:
            tts, bubble = ja, cn
        else:
            reply = re.sub(r"\s+", "", reply).replace("。。", "。")
            log("LLM", "没按双语格式回，原样念")
            tts = bubble = reply
    else:
        reply = re.sub(r"\s+", " ", reply).strip()
        tts = bubble = reply

    with _hist_lock:
        _history.append({"role": "user", "content": user_text})
        _history.append({"role": "assistant", "content": bubble})
        del _history[:-16]
    return tts, bubble


def _apply_switch(target):
    """真正切模式：换音色、换人设、清掉混合语言的旧上下文（不出声，由调用方决定说什么）"""
    global _conv_until, _mute_until
    if target == L.mode():
        return False
    old = L.mode()
    stop_speaking()
    L.set_mode(target)
    with _hist_lock:
        _history.clear()
    _conv_until = time.time() + CONV_WINDOW
    _mute_until = time.time() + 0.7
    log("LANG", f"{L.pack(old)['name']} → {L.pack(target)['name']}")
    return True


def handle_speech(text):
    """一段识别结果 → 决定是切语言、唤醒、对话还是忽略"""
    global _conv_until, _mute_until
    text = re.sub(r"^[，。！？、\s]+", "", text or "").strip()
    if not text or looks_like_hallucination(text):
        return

    # 切换语言走本地判断：没唤醒也能切，也不浪费一次模型调用
    want, rest = L.split_switch(text)
    if want:
        changed = _apply_switch(want)
        log("🌐", f"语言指令：{text[:24]} → {want}" + (f"；余下：{rest}" if rest else ""))
        if not rest:                     # 只说了一句「切换」：回一句确认
            _conv_until = time.time() + CONV_WINDOW
            _mute_until = time.time() + 0.7
            speak_async(L.pack()["switch_ack"] if changed else L.pack()["switch_same"])
            return
        text = rest                      # 「用日语说…」：切完直接用新语言回应内容

    in_conv = time.time() < _conv_until
    tokens = wake_tokens()
    is_wake = any(t in text for t in tokens) and (
        len(text) <= 8 or min(text.find(t) for t in tokens if t in text) <= 2)

    # 正在播报时，识别到的可能是自己声音的回采
    with _state_lock:
        playing = _playing_text
    if playing:
        norm = _squash(playing)
        probe = _squash(text)
        if probe and (probe in norm or (len(probe) >= 4 and any(
                probe[i:i + len(probe) // 2 + 1] in norm
                for i in range(len(probe) - len(probe) // 2)))):
            log("⤺", f"判定回采，丢弃：{text[:16]}")
            return

    if is_wake:
        log("🎤", f"唤醒：{text}")
        stop_speaking()
        _conv_until = time.time() + CONV_WINDOW
        _mute_until = time.time() + 0.6
        pack = L.pack()
        h = time.localtime().tm_hour
        speak_async(random.choice(pack["wake_ack_late"] if (h >= 23 or h < 5)
                                  else pack["wake_ack"]))
        return

    if not in_conv:
        log("·", f"（未唤醒，忽略）{text[:20]}")
        return

    log("👤", text)
    _conv_until = time.time() + CONV_WINDOW      # 说话即续期
    maybe_remember(text)                         # 说到自己的事就记下来

    quick = L.local_time_answer(text)            # 时间/日期：本地直答，准且不卡
    if quick:
        tts, bubble = quick                      # 日语模式：念日语、气泡写中文
        log("⏰", tts)
        with _hist_lock:
            _history.append({"role": "user", "content": text})
            _history.append({"role": "assistant", "content": bubble})
            del _history[:-16]
        speak(tts, bubble)
        return

    tts, bubble = ask_deepseek(text)
    log("🐋", bubble if bubble == tts else f"{bubble} ｜ {tts}")
    speak(tts, bubble)


# ---------------- 监听 ----------------
def listen_loop():
    ensure_model()
    sr = 16000
    try:
        stream = sd.InputStream(samplerate=sr, channels=1, dtype="float32", blocksize=1600)
        block_len = 1600
        stream.start()
    except Exception:
        dev = sd.query_devices(kind="input")
        sr = int(dev["default_samplerate"])
        block_len = max(1600, sr // 10)
        stream = sd.InputStream(samplerate=sr, channels=1, dtype="float32",
                                blocksize=block_len)
        stream.start()
    log("MIC", f"开始监听（{sr}Hz）—— 喊「{L.pack()['wake'][0]}」试试")

    seg = []
    quiet = 0
    noise = 0.001
    last_stt = 0.0
    min_seg = int(0.2 * sr)
    max_blocks = int(8 * sr / block_len)

    while True:
        try:
            data, _ = stream.read(block_len)
        except Exception:
            time.sleep(0.2)
            continue
        block = data[:, 0].copy()

        with _state_lock:
            active = _tts_active
            playing_text = _playing_text
        if active and any(t in (playing_text or "") for t in wake_tokens()):
            _mute_until_local = time.time() + 0.3
            seg, quiet = [], 0
            time.sleep(0.01)
            continue

        if time.time() < _mute_until:
            seg, quiet = [], 0
            continue

        rms = float(np.sqrt(np.mean(block ** 2)))
        if rms < noise:
            noise = noise * 0.995 + rms * 0.005
        elif rms < 0.02:
            noise = noise * 0.999 + rms * 0.001

        thr = max(0.003, noise * 3.5)
        if active:
            thr = max(0.010, noise * 8.0)      # 它说话时只有大声喊才理

        in_conv = time.time() < _conv_until
        if rms > thr:
            seg.append(block)
            quiet = 0
            if len(seg) >= max_blocks:
                _process(np.concatenate(seg), sr)
                last_stt = time.time()
                seg = []
        elif seg:
            quiet += 1
            quiet_cut = 11 if in_conv else 5
            if quiet >= quiet_cut:
                audio = np.concatenate(seg)
                seg, quiet = [], 0
                gap = 0.5 if in_conv else 1.2
                if len(audio) >= min_seg and time.time() - last_stt >= gap:
                    last_stt = time.time()
                    _process(audio, sr)


def _process(audio, sr):
    pack = L.pack()
    try:
        model = ensure_model()
        segments, _ = model.transcribe(
            audio, language=pack["stt_lang"], beam_size=5, vad_filter=True,
            condition_on_previous_text=False, initial_prompt=pack["stt_prompt"])
        text = "".join(s.text for s in segments).strip()
    except Exception as e:
        log("ASR", f"识别出错: {e}")
        return
    if not text:
        return
    try:
        handle_speech(text)
    except Exception:
        # 对话逻辑的异常别再算成「识别出错」，否则会静默失聪
        log("ERR", traceback.format_exc(limit=4))


# ---------------- 单实例（麦克风只有一份） ----------------
VOICE_PORT = 47823          # 别用 8765：机器上可能有别的 http.server 占着
VOICE_HELLO = b"FATUIYU\n"  # 握手标记：端口通不代表是我们（可能被别的程序占了）
_lock_sock = None


def _lock_serve(sock):
    """应答启动器的探活：回一个标记，确认这条端口属于语音桥"""
    while True:
        try:
            c, _ = sock.accept()
        except Exception:
            return
        try:
            c.sendall(VOICE_HELLO)
        except Exception:
            pass
        finally:
            try:
                c.close()
            except Exception:
                pass


def acquire_single_instance():
    """占住 47823 当单实例锁：起第二份会被启动器看到端口已占，直接跳过"""
    global _lock_sock
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", VOICE_PORT))
        s.listen(8)
    except OSError:
        s.close()
        return False
    _lock_sock = s
    threading.Thread(target=_lock_serve, args=(s,), daemon=True).start()
    return True


def watch_lang_file():
    """盯着 pet_lang.json：桌面快捷方式 / 手动改文件也能切，不必重启"""
    while True:
        try:
            m = L.changed_on_disk()
            if m:
                stop_speaking()
                with _hist_lock:
                    _history.clear()
                log("LANG", f"外部切换 → {L.pack(m)['name']}")
                speak_async(L.pack(m)["switch_ack"])
        except Exception:
            pass
        time.sleep(1.5)


def _record_pid():
    """把自己 pid 写进 pids.json：右键「退出」时桌宠照着表直接收，不依赖外部脚本"""
    try:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pids.json")
        cur = {}
        try:
            with open(p, "r", encoding="utf-8") as f:
                cur = json.load(f) or {}
        except Exception:
            pass
        cur["voice"] = os.getpid()
        with open(p, "w", encoding="utf-8") as f:
            json.dump(cur, f)
    except Exception:
        pass


def main():
    if not acquire_single_instance():
        log("BOOT", "已经有一份语音桥在跑了，这份退出")
        return
    _record_pid()
    pygame.mixer.init()
    L.load()                                   # 读取上次用的语言
    log("BOOT", f"大肥鱼语音桥启动（{L.pack()['name']}模式）")
    load_facts()
    if _facts:
        log("MEM", f"带上了 {len(_facts)} 条关于他的旧事")
    try:
        ensure_model()
    except Exception as e:
        log("ERR", f"识别模型加载失败：{e}")
        return
    get_pool()      # 预热中文 TTS 长连接
    if L.mode() == "ja":
        try:
            get_pool(L.pack("ja"))    # 日语那条也先热上
        except Exception:
            pass
    log("BOOT", "TTS 连接已预热")
    if bubble_alive():
        log("BOOT", "桌宠在，气泡通道已接上")
    else:
        log("BOOT", "桌宠没开——只能听见声音，看不到气泡（双击桌面 dsh-pet.vbs 就有）")
    threading.Thread(target=watch_lang_file, daemon=True).start()
    speak_async(L.pack()["boot"])
    listen_loop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("BYE", "收到停止信号")
