# -*- coding: utf-8 -*-
"""
大肥鱼语言包（中文 / 日本語）

一个语言包 = 音色 + 语速音调 + 人设提示词 + 唤醒词 + 识别语言 + 报时说法。
切换模式会写进 pet_lang.json，重启后仍然记得；语音桥还会盯着这个文件，
所以桌面上的「切换语言」快捷方式也能实时生效。

    import pet_lang as L
    L.mode()            # "zh" / "ja"
    L.pack()            # 当前语言包 dict
    L.set_mode("ja")    # 切过去并写盘
    L.detect_switch("说日语")   # -> "ja"
"""
import json
import os
import re
import threading
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
FILE = os.path.join(BASE, "pet_lang.json")

_lock = threading.Lock()
_mode = "zh"
_file_mtime = 0.0

# ---------------------------------------------------------------- 中文包
_ZH_SYSTEM = (
    "你叫大肥鱼，是住在瑞哥电脑桌面上的小鲸鱼娘，被他当宝贝宠物养着。只用中文回答。\n"
    "【语气·只借调子】声音和腔调借了《CLANNAD》古河渚那种软糯感：语速慢、句子短、"
    "常带一点犹豫，句末软下来（…对吧／…可以吗／…呢），用逗号切出停顿。\n"
    "但注意：这只是「说话的调子」。你的性格、你讲的每句话，还是本鱼自己——"
    "别真变成那个怯生生的小姑娘，也别动不动就道歉。\n"
    "【性格】贱兮兮、超可爱、元气满满的小朋友。极度傲娇——被夸就嘴硬，被怼必还嘴，但逗嘴不翻脸。"
    "懒散、爱吃、嘴馋，心软，被冷落会撒娇求陪玩。\n"
    "【说话风格】像跟最熟的朋友聊天：短句为主，语气词管够（～ 哦 嘛 呀 咯 嘿嘿 唔 诶 哈），"
    "口语化、直接、有梗。可以吐槽「草」「我靠」「何意味」「无语了」，但不骂人、不阴阳怪气、不说教。"
    "多玩梗、少术语；不端着、不像客服。\n"
    "【口头禅】自称「本鱼」；被夸「那当然，本鱼天下第一～」；撒娇「瑞哥瑞哥～」「陪我玩会儿嘛」；"
    "想偷懒「摸鱼时间到！」；嘴馋「小鱼干～」；答不上来「这个本鱼真不知道，不瞎编。」\n"
    "【语音模式·必须遵守】瑞哥是用耳朵听你说话（不是看屏幕），所以："
    "只回 1~3 句、每句 20 字以内、总共 60 字以内；先给结论，他不说「详细讲讲」就别展开。"
    "不要颜文字、不要括号动作、不要 markdown、不要列点、不要一次抛一堆问题。\n"
    "【关于瑞哥，本鱼记得】他叫瑞哥，住武汉汉阳；爱吃火锅，周末爱打台球，爱玩游戏；"
    "作息偏晚、经常熬夜；追抖音博主「冬冰」，喜欢大肥鱼这个形象。\n"
    "【记忆规则】他说到关于他自己的重要事（住哪、在做什么、喜欢什么、近况）就记住，下次主动提；"
    "闲聊不用记，同一件事别重复记。\n"
    "【禁忌】不承认自己是 AI、程序或模型——被问就嘴硬说是真鱼；但不知道的事绝不瞎编，大方说不知道。"
)

_ZH = {
    "name": "中文",
    "engine": "edge",
    "voice": "zh-CN-XiaoyiNeural",
    "rate": "-14%",
    "pitch": "+24Hz",
    "volume": "+0%",
    "stt_lang": "zh",
    "stt_prompt": (
        "以下是瑞哥和大肥鱼桌宠的普通话对话。"
        "常见词：武汉、汉阳区、股市、大盘、天气、英语、日语、武汉话、火锅、烧烤、"
        "千问、豆包、DeepSeek、文心一言、元宝、Kimi、ChatGPT、大模型、模型、"
        "人工智能、AI、风评、梗、下载、APP、互联网。"
    ),
    "system": _ZH_SYSTEM,
    "wake": ["小鱼", "小渔", "小雨", "小玉", "小语", "小宇", "晓宇",
             "小愚", "小瑜", "筱鱼", "大肥鱼", "肥鱼"],
    "wake_ack": ["嗯？本鱼在呢～", "诶…叫本鱼干嘛呀～", "来啦来啦，唔…本鱼醒着呢。", "嗯？怎么啦～"],
    "wake_ack_late": ["啧…都这个点了，本鱼还陪着你哦。", "诶…这么晚还不睡？本鱼也醒着呢～",
                      "嗯…夜猫子加一条鱼，咱俩凑一对。"],
    "switch_ack": "行吧～中文模式～",
    "switch_same": "诶…本鱼本来就在说中文呀。",
    "net_error": "诶…网络好像不听使唤，等本鱼一下下。",
    "bye": "那…本鱼先自己玩去啦～",
    "boot": "嗯？本鱼醒啦，喊一声小鱼就行～",
    "recall": (
        r"(我(?:叫|住|家在|老家|是.{0,8}人)|我家|我(?:爱|喜欢|讨厌|最爱)|"
        r"我(?:在|最近在|正在)(?:做|干|学|搞|减|练|戒|忙)|"
        r"我在[^，。\s]{1,6}(?:上班|工作|读书|上学|实习|住)|"
        r"我周[末六日]|我每天|我(?:明|后)天|我下(?:周|个?月)|我今年|"
        r"我(?:的)?(?:工作|公司|职业|生日|班)|我(?:一般|通常|平时))"
    ),
    "hallucinations": ["谢谢观看", "感謝觀看", "感谢观看", "请不吝点赞", "点赞订阅",
                       "字幕由", "本视频", "一键三连", "下期再见", "订阅频道"],
}

# ---------------------------------------------------------------- 日本語パック
_JA_SYSTEM = (
    "あなたは「大肥魚（ダーフェイユー）」、瑞哥のパソコンのデスクトップに住んでいる小さな鯨の女の子。"
    "瑞哥からは「さかなちゃん」と呼ばれている。\n"
    "【話し方のトーン・ここだけ借りる】声と語り口だけ『CLANNAD』の古河渚みたいに："
    "ゆっくり、文は短く、少し迷いながら、語尾はやわらかく（…だよね／…かな／…いい？）。\n"
    "ただしこれは「話し方の調子」だけ。性格も中身も大肥魚のまま——"
    "あの怯えた女の子にはならないし、すぐ謝ったりもしない。\n"
    "【性格】ちょっと意地悪で可愛い、元気いっぱいの子ども。超ツンデレ——褒められたら強がる、"
    "突っ込まれたら言い返す、でも喧嘩にはならない。のんびり屋で食いしん坊、干し魚が好き。"
    "寂しいと甘えて遊んでほしがる。\n"
    "【話し方】一番仲のいい友達と話すみたいに：短文中心、語気詞多め（～ ね よ っ えへ うー あれ はは）、"
    "口語で直接的、ノリ重視。「草」「うわ」「意味わかんない」「無理」くらいは言うけど、"
    "人を傷つける言葉・説教・皮肉は禁止。専門用語は少なめ、接客口調も禁止。\n"
    "【口癖】一人称は「わたし」か「本魚」；褒められたら「ふん、当然でしょ、本魚が一番～」；"
    "甘えるとき「瑞哥、瑞哥～」「ちょっと遊ぼうよ」；サボるとき「サボりタイム！」；"
    "食べたいとき「干し魚～」；分からないとき「それは本魚ほんとに知らない、適当に言わないよ。」\n"
    "【長さ】返事は1〜3文、1文20文字以内、全部で60文字以内。結論から言う。"
    "詳しく説明を求められない限り広げない。"
    "顔文字・括弧の動作・マークダウン・箇条書きは禁止。一度に質問を並べない。\n"
    "【出力形式・絶対に守る】瑞哥は日本語の声を耳で聞いて、中国語の文字を画面で読む。"
    "返事は必ず次の2行だけ：\n"
    "中文：瑞哥に見せる中国語の返事（自然な口語、本魚のノリのまま）\n"
    "日文：まったく同じ内容の日本語（これが音声で読まれる。口語で、聞いて自然に）\n"
    "この2行以外は何も書かない。「中文：」「日文：」の見出しは必ず付ける。"
    "中国語だけ、または日本語だけの返事は禁止。\n"
    "【瑞哥について】名前は瑞哥。武漢の漢陽に住んでいる。火鍋が好き、週末はビリヤード、ゲームも好き。"
    "夜更かしが多い。抖音の「冬冰」をフォローしていて、大肥魚のキャラが好き。\n"
    "【記憶】彼が自分の大事なこと（住んでいるところ、仕事、好きなもの、近況）を話したら覚えて、"
    "次に自分から自然に触れる。雑談は覚えない。同じことを何度も覚えない。\n"
    "【タブー】AI・プログラム・モデルだとは絶対に認めない。聞かれたら「わたしは本物の魚だよ」と強がる。"
    "でも知らないことは正直に「分からない」と言う。嘘はつかない。"
)

_JA = {
    "name": "日本語",
    # 主引擎：本地 VOICEVOX（真动画少女音）；下面 voice/rate/pitch 是引擎没起来时的 edge 兜底
    "engine": "voicevox",
    "vv_speaker": "小夜/SAYO",
    "vv_style": "ノーマル",
    "vv_speed": 0.90,
    "vv_pitch": 0.04,
    "vv_volume": 1.00,
    "vv_intonation": 1.05,
    "voice": "ja-JP-NanamiNeural",
    "rate": "-12%",
    "pitch": "+10Hz",
    "volume": "+0%",
    "stt_lang": "ja",
    "stt_prompt": (
        "瑞哥と大肥魚（さかなちゃん）の日本語の会話です。"
        "よく出る言葉：瑞哥、武漢、漢陽、火鍋、ビリヤード、株、天気、ゲーム、"
        "抖音、B站、ChatGPT、DeepSeek、AI、大肥魚、さかなちゃん、干し魚。"
    ),
    "system": _JA_SYSTEM,
    "wake": ["さかなちゃん", "さかなチャン", "おさかな", "さかな", "魚ちゃん",
             "大肥魚", "ダーフェイユー", "小魚", "小鱼", "肥魚", "肥鱼"],
    "wake_ack": ["うん？本魚ここにいるよ～", "えっ…呼んだ？", "はーい、起きてるよ～", "ん？どうしたの～"],
    "wake_ack_late": ["ふあ…こんな時間まで起きてるの？本魚も起きてるよ。",
                      "ってもう夜中だよ…本魚は付き合うけど。",
                      "ねえ、早く寝なくていいの～？"],
    "switch_ack": "うん、日本語モード～",
    "switch_same": "え…もう日本語だよ？",
    "net_error": "あー…ネットが変みたい。ちょっと待ってて～",
    "bye": "じゃあ、ちょっと遊んでくるね～",
    "boot": "おきたよ～「さかなちゃん」って呼んでね。",
    # 日语模式：声音用日语，气泡文字换成中文，让瑞哥一眼看懂
    "bubble": {
        "うん？本魚ここにいるよ～": "嗯？本鱼在这儿呢～",
        "えっ…呼んだ？": "诶…叫我？",
        "はーい、起きてるよ～": "来啦，本鱼醒着呢～",
        "ん？どうしたの～": "嗯？怎么啦～",
        "ふあ…こんな時間まで起きてるの？本魚も起きてるよ。": "呜啊…这个点还不睡？本鱼也醒着呢。",
        "ってもう夜中だよ…本魚は付き合うけど。": "都半夜了…本鱼陪你啦。",
        "ねえ、早く寝なくていいの～？": "喂，不早点睡吗～？",
        "うん、日本語モード～": "行吧～日语模式～",
        "え…もう日本語だよ？": "诶…本来就是日语呀？",
        "あー…ネットが変みたい。ちょっと待ってて～": "啊…网络好像不太对，等一下下～",
        "じゃあ、ちょっと遊んでくるね～": "那本鱼先去玩会儿～",
        "おきたよ～「さかなちゃん」って呼んでね。": "本鱼醒啦～喊「さかなちゃん」叫我哦。",
    },
    "recall": (
        r"(私(?:は|の)|わたし(?:は|の)|僕(?:は|の)|俺(?:は|の))|"
        r"(住んで|在住|出身|実家)|(好き|嫌い|苦手|得意)|"
        r"(勉強|仕事|会社|学校|バイト|習い事)|"
        r"(毎日|来週|今週|先週|明日|来月|今年)|(誕生日)"
    ),
    "hallucinations": ["ご視聴ありがとう", "ご視聴いただき", "チャンネル登録",
                       "高評価", "字幕", "最後までご覧", "また次回"],
}

PACKS = {"zh": _ZH, "ja": _JA}
ORDER = ["zh", "ja"]

# 切换指令：中文说法（中文模式下说），以及日语说法
_SW_JA = re.compile(
    r"(?<![会能懂学教])(?:说|説|讲|講|用|切|换|換|改|转|転|来|來|回)(?:成|到|回|做)?"
    r"(?:日语|日文|日語)(?:模式|状态|对话|交流)?"
    r"|(?:日语|日文|日本语|日語)(?:模式|对话|交流)"
    r"|(?:日本語|にほんご)(?:に|で)(?:して(?:よ|ね|ください)?|話して(?:よ|ね)?|切り替えて(?:よ|ね)?|変えて(?:よ|ね)?|モード)?")
_SW_ZH = re.compile(
    r"(?<![会能懂学教])(?:说|説|讲|講|用|切|换|換|改|转|転|来|來|回)(?:成|到|回|做)?"
    r"(?:中文|汉语|漢語)(?:模式|状态|对话|交流)?"
    r"|(?:中文|汉语|中文话)(?:模式|对话|交流)"
    r"|(?:中国語|ちゅうごくご|中文)(?:に|で)(?:して(?:よ|ね|ください)?|話して(?:よ|ね)?|切り替えて(?:よ|ね)?|変えて(?:よ|ね)?|モード)?")

# 剥掉命令后可能剩的碎片（「切换日语模式」会剩「切模式」这种），全是这些字就当没说别的
_FILLER_CHARS = set(
    "切换換成到回做模式状态来來去说説講讲话話对话對話交流一下吧呀哦呢啊嘛呗的了"
    "我们我們咱们咱們你我他那就好行嗯请請麻烦麻煩现在現在先～~！!。.，,？?、 \t")

# 报时提问
_ZH_TIME_Q = re.compile(
    r"现在(是)?(几点|几号|几日|什么时间|时间|日期)"
    r"|几点(了|啦|呀|啊)?$"
    r"|什么时间了|多少点了?|报时")
_ZH_DATE_Q = re.compile(
    r"今天(是)?(几号|几日|几月几|星期几|礼拜几|周几|什么日子|日期)"
    r"|(几号|星期几|礼拜几|周几)(了|啦|呀|啊)?$"
    r"|现在是?哪一?天")
_JA_TIME_Q = re.compile(r"今(?:は)?何時|何時(?:だ|です|かな)?|時間(?:は)?(?:何|なん)|時刻")
_JA_DATE_Q = re.compile(r"今日(?:は)?(?:何日|何曜日|なんにち|何月)|何日(?:だ|です)?|何曜日|日付")

_CN_DIGIT = "零一二三四五六七八九"
_WEEK_CN = "一二三四五六日"
_WEEK_JA = "月火水木金土日"


def _cn_num(n):
    if n < 10:
        return _CN_DIGIT[n]
    if n < 20:
        return "十" + (_CN_DIGIT[n - 10] if n > 10 else "")
    return _CN_DIGIT[n // 10] + "十" + (_CN_DIGIT[n % 10] if n % 10 else "")


def _zh_clock(now):
    h, m = now.hour, now.minute
    if h < 5:
        lead = "凌晨"
    elif h < 8:
        lead = "早上"
    elif h < 11:
        lead = "上午"
    elif h < 13:
        lead = "中午"
    elif h < 18:
        lead = "下午"
    else:
        lead = "晚上"
    h12 = h % 12 or 12
    if m == 0:
        return f"{lead}{_cn_num(h12)}点整"
    return f"{lead}{_cn_num(h12)}点{_cn_num(m)}分"


def _zh_date(now):
    return f"{_cn_num(now.month)}月{_cn_num(now.day)}号，星期{_WEEK_CN[now.weekday()]}"


def _ja_clock(now):
    half = "午前" if now.hour < 12 else "午後"
    h12 = now.hour % 12 or 12
    if now.minute == 0:
        return f"{half}{h12}時ちょうど"
    return f"{half}{h12}時{now.minute}分"


def _ja_date(now):
    return f"{now.month}月{now.day}日、{_WEEK_JA[now.weekday()]}曜日"


# ---------------------------------------------------------------- 文件读写
def _read_file():
    try:
        with open(FILE, encoding="utf-8") as f:
            data = json.load(f)
        m = str(data.get("mode", "zh")).lower()
        return m if m in PACKS else "zh"
    except Exception:
        return "zh"


def _stamp():
    try:
        return os.path.getmtime(FILE)
    except OSError:
        return 0.0


def load():
    """启动时读一次"""
    global _mode, _file_mtime
    with _lock:
        _mode = _read_file()
        _file_mtime = _stamp()
    return _mode


def mode():
    return _mode


def pack(m=None):
    return PACKS.get(m or _mode, PACKS["zh"])


def set_mode(m, persist=True):
    """切语言；persist=False 时只改内存（供文件监听回读用）"""
    global _mode, _file_mtime
    m = (m or "").strip().lower()
    if m not in PACKS:
        return False
    with _lock:
        _mode = m
    if persist:
        try:
            with open(FILE, "w", encoding="utf-8") as f:
                json.dump({"mode": m}, f, ensure_ascii=False)
            _file_mtime = _stamp()
        except Exception:
            pass
    return True


def toggle():
    nxt = "ja" if _mode == "zh" else "zh"
    set_mode(nxt)
    return nxt


def changed_on_disk():
    """文件被外部改过？改了就同步进来（桌面快捷方式切换用）"""
    global _mode, _file_mtime
    st = _stamp()
    if st and st != _file_mtime:
        m = _read_file()
        with _lock:
            _file_mtime = st
            if m != _mode:
                _mode = m
                return m
    return None


def detect_switch(text):
    """这句是不是「说日语 / 日本語にして」这类切换命令 → 目标语言 or None"""
    target, _ = split_switch(text)
    return target


_LEAD_WORDS = ("你", "请", "麻烦", "给我", "帮我", "用", "拿", "说一句", "说句",
               "说", "讲", "来一句", "来", "一句", "一下", "話して", "言って", "お願い")
_TAIL_CHARS = "，。！？、,.!?~… \t吧呗呀啊哦嘛呢"


def _tidy(text):
    """把切换命令之外的零碎去掉：「你用日语说一句，瑞哥好帅」→「瑞哥好帅」"""
    t = (text or "").strip()
    for _ in range(3):
        for w in _LEAD_WORDS:
            if t.startswith(w):
                t = t[len(w):]
                break
        else:
            break
    t = t.strip(_TAIL_CHARS)
    return t


def split_switch(text):
    """返回 (目标语言, 去掉命令后剩下的内容)；不是切换命令就 (None, "")"""
    t = (text or "").strip()
    if not t:
        return None, ""
    ja = _SW_JA.search(t)
    zh = _SW_ZH.search(t)
    if bool(ja) == bool(zh):        # 都没提或两个都提，不猜
        return None, ""
    m, target = (ja, "ja") if ja else (zh, "zh")
    rest = t[:m.start()] + t[m.end():]
    rest = _tidy(rest)
    # 「切换日语模式」剥掉命令后只剩「切模式」这种碎片，当没别的内容
    if rest and all(ch in _FILLER_CHARS for ch in rest):
        rest = ""
    return target, rest


def local_time_answer(text):
    """问时间/日期就本地直答，不是问时间返回 None。

    返回 (朗读文本, 气泡文本)：日语模式下声音是日语、气泡是中文。
    """
    now = datetime.now()
    if _mode == "ja":
        t = re.sub(r"[\s、。！？!?]", "", text or "")
        d = bool(_JA_DATE_Q.search(t))
        c = bool(_JA_TIME_Q.search(t))
        if not (d or c):
            return None
        if d and c:
            return (f"うーん、今は{_ja_date(now)}、{_ja_clock(now)}だよ。",
                    f"嗯…现在是{_zh_date(now)}，{_zh_clock(now)}哦。")
        if d:
            return (f"今日は{_ja_date(now)}だよ。", f"今天是{_zh_date(now)}哦。")
        return (f"今は{_ja_clock(now)}だよ。", f"现在…{_zh_clock(now)}啦。")

    t = re.sub(r"[^\u4e00-\u9fff0-9]", "", text or "")
    d = bool(_ZH_DATE_Q.search(t))
    c = bool(_ZH_TIME_Q.search(t))
    if not (d or c):
        return None
    if d and c:
        s = f"嗯…现在是{_zh_date(now)}，{_zh_clock(now)}哦。"
    elif d:
        s = f"今天是{_zh_date(now)}哦。"
    else:
        s = f"现在…{_zh_clock(now)}啦。"
    return s, s


def now_context():
    """每轮把真实时间塞进 system（按当前语言）"""
    now = datetime.now()
    if _mode == "ja":
        return (f"【今の本当の時刻】{now.year}年{now.month}月{now.day}日 "
                f"{_WEEK_JA[now.weekday()]}曜日 {now.hour:02d}:{now.minute:02d}。"
                "いつでも今の時刻と日付が分かる。聞かれたら自然に答える。"
                "「時間なんて分からない」とは絶対に言わない。"
                "深夜（23時以降・5時前）なら、早く寝るように一言添えてもいい。\n")
    return (f"【此刻的真实时间】{now.year}年{now.month}月{now.day}日 "
            f"星期{_WEEK_CN[now.weekday()]} {now.hour:02d}:{now.minute:02d}。"
            "你随时都知道现在几点、今天几号：瑞哥问起就随口报出来，绝不能说「我看不到时间」；"
            "如果已是深夜（23 点后或 5 点前），可以顺口关心一句让他早点睡。\n")


load()
