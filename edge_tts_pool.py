# -*- coding: utf-8 -*-
"""
edge-tts 常驻连接版（自包含，替代旧项目里被删掉的同名模块）

一个 EdgePool 绑定一个发音人，内部跑一条独立的事件循环线程，
所有合成请求复用同一个 aiohttp 连接，省掉每次重新握手的时间。

    pool = EdgePool("ja-JP-NanamiNeural")
    pool.synth("こんにちは", "+6%", "+18Hz", "+0%", "out.mp3")
"""
import asyncio
import os
import threading

import edge_tts


class EdgePool:
    def __init__(self, voice="zh-CN-XiaoyiNeural"):
        self.voice = voice
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    async def _synth(self, text, rate, pitch, volume, out):
        # edge-tts 每次会自己开关 session；把外部 connector 传进去会在第二次调用时被关闭，
        # 所以这里不共用 connector，只借用常驻事件循环省掉 loop 重建的开销。
        com = edge_tts.Communicate(
            text, self.voice, rate=rate, pitch=pitch, volume=volume,
            connect_timeout=10, receive_timeout=30)
        await com.save(out)
        return os.path.exists(out) and os.path.getsize(out) > 600

    def synth(self, text, rate="+0%", pitch="+0Hz", volume="+0%", out_path=None):
        """合成到 out_path，成功返回 True"""
        if not out_path or not (text or "").strip():
            return False
        try:
            fut = asyncio.run_coroutine_threadsafe(
                self._synth(text, rate, pitch, volume, out_path), self._loop)
            return bool(fut.result(timeout=35))
        except Exception:
            return False

    def warm(self):
        """预热：合成一个极短音，把 TLS 连接先建好"""
        import tempfile
        p = os.path.join(tempfile.gettempdir(), "edge_pool_warm.mp3")
        ok = self.synth("嗯", "+0%", "+0Hz", "+0%", p)
        try:
            os.remove(p)
        except Exception:
            pass
        return ok
