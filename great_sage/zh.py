"""繁體中文（台灣）輔助工具。

小模型和 Whisper 在中文時很容易輸出簡體字，光靠提示詞擋不住，所以模型回覆、
語音辨識結果在進入畫面、語音與對話紀錄之前，都先經過 to_tw() 轉成台灣繁體與
台灣用語（OpenCC 的 s2twp：軟件→軟體、視頻→影片、內存→記憶體）。

OpenCC 載入失敗時原文照樣傳回，不會讓整個程式掛掉。
"""

import logging
import re

log = logging.getLogger(__name__)

_cc = None
_cc_failed = False

# 中日韓統一表意文字（含擴充 A）與全形標點，用來判斷一段文字是不是中文。
CJK_RE = re.compile(r"[㐀-䶿一-鿿豈-﫿]")


def _converter():
    global _cc, _cc_failed
    if _cc is None and not _cc_failed:
        try:
            from opencc import OpenCC
            _cc = OpenCC("s2twp")
        except Exception as exc:  # 缺套件時降級成不轉換
            _cc_failed = True
            log.warning("OpenCC 無法載入，簡轉繁停用：%s", exc)
    return _cc


def to_tw(text):
    """簡體／中國用語 → 台灣繁體。非中文或空字串原樣傳回。"""
    if not text or not CJK_RE.search(text):
        return text
    cc = _converter()
    if cc is None:
        return text
    try:
        return cc.convert(text)
    except Exception:
        return text


def has_cjk(text) -> bool:
    return bool(text) and bool(CJK_RE.search(text))


# ---------------------------------------------------------------------
# 念出來之前的整理（只影響語音，畫面上的文字不變）
#
# F5 每遇到一個標點就停一下，估算長度時也把標點當成一個字，標點越多整句
# 越拖。頓號、引號、括號念出來沒有意義，直接拿掉；數字轉成中文念法，避免
# 「20%」被念得怪腔怪調。
# ---------------------------------------------------------------------

_DIGITS = "零一二三四五六七八九"


def _int_zh(n: int) -> str:
    if n == 0:
        return "零"
    if n < 0:
        return "負" + _int_zh(-n)
    units = [(10 ** 8, "億"), (10 ** 4, "萬")]
    for size, name in units:
        if n >= size:
            hi, lo = divmod(n, size)
            rest = _int_zh(lo) if lo else ""
            if lo and lo < size // 10:
                rest = "零" + rest
            return _int_zh(hi) + name + rest
    out, started, zero = "", False, False
    for size, name in ((1000, "千"), (100, "百"), (10, "十"), (1, "")):
        d, n = divmod(n, size)
        if d:
            if zero:
                out += "零"
            out += _DIGITS[d] + name
            started, zero = True, False
        elif started:
            zero = True
    if out.startswith("一十"):          # 十五，不是一十五
        out = out[1:]
    return out


def _num_zh(s: str) -> str:
    s = s.replace(",", "")
    if "." in s:
        a, b = s.split(".", 1)
        return _int_zh(int(a or "0")) + "點" + "".join(_DIGITS[int(c)] for c in b)
    if len(s) >= 5 and s.startswith("0"):   # 電話、編號：逐位念
        return "".join(_DIGITS[int(c)] for c in s)
    return _int_zh(int(s))


_YEAR_RE = re.compile(r"(\d{4})年")
# 英數混合的一個「詞」：RTX 5090、A100、i7-13700H、40GB、3D
_ALNUM_RE = re.compile(r"[A-Za-z]+(?:[-\s]?\d[\dA-Za-z]*(?![.\d]))+|\d+(?:\.\d+)?[A-Za-z]+[\dA-Za-z]*")
_UNIT_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*(GB|MB|TB|KB|GHz|MHz|Hz|kg|km|cm|mm|ms|fps|mAh|W|V|K|k)$")
_UNIT_ZH = {"kg": "公斤", "km": "公里", "cm": "公分", "mm": "毫米", "ms": "毫秒",
            "fps": "幀", "W": "瓦", "V": "伏特", "k": "K"}


def _alnum_zh(m):
    """數量＋單位照數字念（40GB→四十GB）；型號逐位念（A100→A一零零）。"""
    word = m.group(0)
    u = _UNIT_RE.match(word)
    if u:
        return _num_zh(u.group(1)) + _UNIT_ZH.get(u.group(2), u.group(2))
    word = re.sub(r"(?<=[A-Za-z])\s(?=\d)", "", word)
    return "".join(_DIGITS[int(c)] if c.isdigit() else ("槓" if c == "-" else c)
                   for c in word)
_PCT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*[%％]")
_RANGE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*[-~～–]\s*(\d+(?:\.\d+)?)")
_NUM_RE = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")
_DROP_RE = re.compile(r"[「」『』《》〈〉（）()\[\]【】\"“”‘’*_#`]")


def tts_normalize_zh(text: str) -> str:
    """把要念的中文整理成適合語音合成的樣子。非中文原樣傳回。"""
    if not has_cjk(text):
        return text
    t = text
    t = re.sub(r"NT\$|NTD|新台幣\$", "新台幣", t)
    t = re.sub(r"US\$|USD", "美金", t)
    t = _ALNUM_RE.sub(_alnum_zh, t)
    t = _YEAR_RE.sub(lambda m: "".join(_DIGITS[int(c)] for c in m.group(1)) + "年", t)
    t = _PCT_RE.sub(lambda m: "百分之" + _num_zh(m.group(1)), t)
    t = _RANGE_RE.sub(lambda m: _num_zh(m.group(1)) + "到" + _num_zh(m.group(2)), t)
    t = _NUM_RE.sub(lambda m: _num_zh(m.group(0)), t)
    t = _DROP_RE.sub("", t)
    t = t.replace("、", "，").replace("﹑", "，")   # 頓號當逗號，念到時停一下
    t = re.sub(r"[：；]", "，", t)
    t = re.sub(r"……|…|——|—", "，", t)
    t = re.sub(r"\s+", "", t) if CJK_RE.search(t) and not re.search(r"[A-Za-z] [A-Za-z]", t) else t
    t = re.sub(r"([，。！？])[，。！？]+", r"\1", t)   # 連續標點合併
    t = re.sub(r"^[，。]+", "", t)
    return t.strip()
