# -*- coding: utf-8 -*-
"""
VOICEVOX 引擎客户端（本地 127.0.0.1:50021）

接口故意做成跟 edge_tts_pool.EdgePool 一样：
    pool = VoicevoxPool("四国めたん", "ノーマル")
    pool.synth("こんにちは", out_path="out.wav")

区别只在参数含义：rate/pitch/volume 传的是倍率，不是 "+10%" 字符串。
"""
import json
import os
import threading
import urllib.error
import urllib.parse
import urllib.request

ENGINE = os.environ.get("VOICEVOX_URL", "http://127.0.0.1:50021")

_lock = threading.Lock()
_speakers_cache = None


def alive(timeout=1.5):
    """引擎在不在"""
    try:
        with urllib.request.urlopen(ENGINE + "/version", timeout=timeout) as r:
            r.read(64)
        return True
    except Exception:
        return False


def _get(path, timeout=5):
    with urllib.request.urlopen(ENGINE + path, timeout=timeout) as r:
        return r.read()


def _post(path, body=None, timeout=60):
    req = urllib.request.Request(
        ENGINE + path, data=body if body is not None else b"",
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def speakers():
    """角色 + 风格列表（缓存；引擎重启才会变）"""
    global _speakers_cache
    with _lock:
        if _speakers_cache is None:
            _speakers_cache = json.loads(_get("/speakers").decode("utf-8"))
        return _speakers_cache


def resolve_style_id(name, style="ノーマル"):
    """
    按角色名 + 风格名找 style id。
    支持模糊：name 传 "四国めたん" 就行；找不到风格就退回该角色第一个风格。
    """
    try:
        data = speakers()
    except Exception:
        return None
    hit = None
    for sp in data:
        if sp.get("name") == name:
            hit = sp
            break
    if hit is None:
        for sp in data:
            if name in sp.get("name", "") or sp.get("name", "") in name:
                hit = sp
                break
    if hit is None:
        return None
    styles = hit.get("styles") or []
    for st in styles:
        if st.get("name") == style:
            return st.get("id")
    return styles[0].get("id") if styles else None


def _boost(wav, target_peak=0.88):
    """VOICEVOX 原始输出偏轻（峰值只有 40% 左右），这里纯线性抬到 target_peak。
    只用增益，不做任何压缩/限幅 —— 一旦改波形就会听成电流声。"""
    try:
        import io
        import wave as _w
        import numpy as _np
        with _w.open(io.BytesIO(wav), "rb") as f:
            n, sr = f.getnframes(), f.getframerate()
            ch, sw = f.getnchannels(), f.getsampwidth()
            raw = f.readframes(n)
        if sw != 2 or not raw:
            return wav
        a = _np.frombuffer(raw, dtype=_np.int16).astype(_np.float64)
        peak = float(_np.abs(a).max()) or 1.0
        g = (target_peak * 32767.0) / peak
        if g <= 1.0:
            return wav
        a = _np.clip(_np.round(a * g), -32768, 32767).astype(_np.int16)
        out = io.BytesIO()
        with _w.open(out, "wb") as f:
            f.setnchannels(ch)
            f.setsampwidth(sw)
            f.setframerate(sr)
            f.writeframes(a.tobytes())
        return out.getvalue()
    except Exception:
        return wav


class VoicevoxPool:
    """跟 EdgePool 同接口；本地推理，不需要连接池"""

    def __init__(self, speaker="四国めたん", style="ノーマル"):
        self.speaker = speaker
        self.style = style
        self.style_id = resolve_style_id(speaker, style)

    def refresh(self):
        self.style_id = resolve_style_id(self.speaker, self.style)

    def synth(self, text, rate=1.0, pitch=0.0, volume=1.0, out_path=None,
              intonation=1.0, boost=True):
        """合成到 out_path（wav），成功返回 True

        注意参数语义跟 edge 完全不同：
          rate        1.0 = 原速（0.5~2.0）
          pitch       0.0 = 原调，是「半音比例」不是倍率，范围只有 -0.15~0.15
          volume      1.0 = 原音量（0~2）
          intonation  1.0 = 原起伏（0~2）
        传错 pitch 会把整句压成气声，所以要 clamp。
        """
        if not out_path or not (text or "").strip():
            return False
        if self.style_id is None:
            self.refresh()
        if self.style_id is None:
            return False
        try:
            qs = urllib.parse.urlencode({"speaker": self.style_id, "text": text})
            query = json.loads(_post("/audio_query?" + qs).decode("utf-8"))
            query["speedScale"] = max(0.5, min(2.0, float(rate)))
            query["pitchScale"] = max(-0.15, min(0.15, float(pitch)))
            query["volumeScale"] = max(0.0, min(2.0, float(volume)))
            query["intonationScale"] = max(0.0, min(2.0, float(intonation)))
            query["outputSamplingRate"] = 24000
            wav = _post("/synthesis?speaker=%d" % self.style_id,
                        json.dumps(query, ensure_ascii=False).encode("utf-8"))
            if not wav or len(wav) < 800:
                return False
            if boost:
                wav = _boost(wav)
            with open(out_path, "wb") as f:
                f.write(wav)
            return True
        except Exception:
            return False

    def warm(self):
        """预热：第一次合成要加载模型，很慢；先跑一个短句垫掉"""
        import tempfile
        p = os.path.join(tempfile.gettempdir(), "vv_warm.wav")
        ok = self.synth("はい", out_path=p)
        try:
            os.remove(p)
        except Exception:
            pass
        return ok
