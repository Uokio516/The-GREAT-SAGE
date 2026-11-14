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
