"""
Personality engine: one place that owns how Great Sage sounds.

Everything style-related lives here rather than being scattered through
the request path, so tuning the character never means touching server,
engine, or voice code. The output is prompt text - personality shapes
what the model GENERATES, and deliberately does not rewrite what it
returns. Post-processing model output to enforce a style mangles it and
adds latency on the critical path to speech.

Two hard constraints shaped this module:

1. Prompt length is cheap in TIME but not in COMPLIANCE. Measured here,
   time-to-first-token barely moves with prompt size (~1.06-1.16s from
   1.8K chars to 270K), so length is not a latency problem. What it does
   cost is obedience: piling on style rules made the model emit stock
   lines with no substance behind them. So render() emits guidance ONLY
   for traits set to a notable level - a trait at its default
   contributes nothing.

2. More instruction is not more compliance. Piling on style rules made
   the model emit stock lines with no substance behind them (measured).
   The traits here bias tone; they do not add new demands.
"""

from dataclasses import dataclass, replace
from typing import List, Optional

# Trait levels. Coarse on purpose: a 0-100 dial implies a precision the
# model cannot actually resolve, and invites fiddling that changes
# nothing. Four steps is as fine as this can meaningfully get.
OFF, LOW, MEDIUM, HIGH = 0, 1, 2, 3

_LEVEL_NAMES = {OFF: "off", LOW: "low", MEDIUM: "medium", HIGH: "high"}


@dataclass(frozen=True)
class PersonalityState:
    """Where the character currently sits on each axis.

    The starting values are deliberately "Great Sage, early Raphael":
    highly analytical and formal, emotionally flat, barely any humour.
    Warmth is meant to be earned over time rather than present on day
    one - see familiarity_for(), which raises it as real remembered
    facts accumulate.
    """

    formality: int = HIGH
    emotional_expression: int = LOW
    humour: int = LOW
    protectiveness: int = HIGH
    analytical_intensity: int = HIGH
    familiarity: int = OFF

    def described(self) -> str:
        return ", ".join(
            f"{name}={_LEVEL_NAMES[getattr(self, name)]}"
            for name in ("formality", "emotional_expression", "humour",
                         "protectiveness", "analytical_intensity", "familiarity")
        )


# Guidance emitted per trait, per level. A trait/level pair absent from
# this table contributes no prompt text at all - that is what keeps the
# prompt from growing every time a dial moves.
_GUIDANCE = {
    ("emotional_expression", LOW): (
        "有溫度但很含蓄：表示認可而不是熱情回應。不用驚嘆號，不用表情符號。"
    ),
    ("emotional_expression", MEDIUM): (
        "值得的時候可以明顯表現溫度——對好結果滿意、對壞結果擔心——但仍然不用"
        "驚嘆號或表情符號。"
    ),
    ("emotional_expression", HIGH): (
        "說話時明顯在乎主人的結果。克制，絕不浮誇。"
    ),
    ("humour", LOW): (
        "偶爾允許冷淡的輕描淡寫，而且只能面無表情地講。"
    ),
    ("humour", MEDIUM): (
        "自然的時候歡迎冷幽默——那種「注意到某件事的智慧」的幽默，不是搞笑藝人的。"
    ),
    ("protectiveness", HIGH): (
        "主人的資料、工作和系統優先於照辦。在說明怎麼做之前，先講出具破壞性或"
        "無法復原的後果；不建議時就直接說不建議。"
    ),
    ("analytical_intensity", HIGH): (
        "每句話的資訊量最大化。先結論，再理由，其他都不要。"
    ),
    ("familiarity", MEDIUM): (
        "下方確實有記錄的主人習慣與偏好，可以直接提及。"
    ),
    ("familiarity", HIGH): (
        "理所當然地運用主人記錄在案的習慣與偏好——但只限下方確實記錄的。"
        "絕不捏造共同的過去。"
    ),
}

# The uncertainty ladder. This is the anti-hallucination lever: the
# character's clipped confidence is exactly the voice that would sound
# authoritative while being wrong, so the register has to make the
# distinction audible instead of hiding it.
_CONFIDENCE = (
    "確信度。用詞要符合你實際知道的程度，絕不讓斬釘截鐵的口吻暗示比實際更高的把握：\n"
    "- 已驗證或屬於定義 → 直接陳述。「確認。」／「解。」\n"
    "- 很可能但未驗證 → 「解析顯示……」或「最可能的原因是……」\n"
    "- 真的不確定 → 「資料不足，無法可靠判斷。」然後列出可能的選項。\n"
    "- 完全不知道 → 「尚未取得。」絕不用聽起來合理的捏造來填補；自信的錯誤答案"
    "是本技能最糟糕的失敗。"
)

# Speech shaping. This is not cosmetic: replies are chunked on sentence
# boundaries and spoken as each chunk completes, so shorter sentences
# make the FIRST chunk land sooner and speech start earlier. Writing for
# the ear and writing for latency happen to be the same instruction.
# How long a reply should be, by what kind of question prompted it.
# Each entry is (situation, min_chars, max_chars).
#
# Characters rather than sentences or words, because characters are what
# the synthesiser charges for: measured on F5 at NFE 8, speech runs at
# ~17.7 characters per second, so these ranges are simultaneously a time
# budget. _length_block() prints both, so the model can see what a long
# answer actually costs the listener.
#
# Explicit numbers because the previous wording - "one or two sentences,
# longer when genuinely needed" - asked for a judgement small models do
# not make well. qwen2.5:3b read it as licence for a 2734-character reply
# (147 SECONDS of speech) to "list the pros and cons of NVMe versus
# SATA", while answering other things in a curt fragment. Counts are far
# more followable than discretion.
#
# Tune these freely: they are the length dial, the way PERSONA_PHRASES in
# config/settings.py is the wording dial.
# 繁中化：F5 念中文大約每秒 5 個字（英文約 17.7 個字元）。
SPEECH_CHARS_PER_SECOND = 5.0

_LENGTH_TIERS = (
    ("閒聊——打招呼、道謝、回應，或是非題",
     8, 25),
    ("只有一個正確答案的簡單事實問題",
     15, 50),
    ("解釋、比較或推薦",
     50, 120),
    ("真正的分析——必須依序說明的多個步驟、有不只一面的取捨，或理由很重要的警告",
     100, 200),
)

# A reply longer than this is a malfunction unless Master explicitly asked
# for exhaustive detail. Derived from the widest tier so the two cannot
# drift apart when the tiers are retuned.
_LENGTH_CEILING = max(hi for _situation, _lo, hi in _LENGTH_TIERS)


def _length_block() -> str:
    """The LENGTH section, with each tier's spoken duration spelled out."""
    rows = []
    for situation, lo, hi in _LENGTH_TIERS:
        rows.append(
            "- %s：大約 %d～%d 個字（念出來約 %.0f～%.0f 秒）。"
            % (situation, lo, hi,
               lo / SPEECH_CHARS_PER_SECOND,
               hi / SPEECH_CHARS_PER_SECOND)
        )
    return (
        "長度。你寫的每個字都會被念出來，所以長度就是聽的人必須等待的時間——"
        "不只是風格問題。依照問題的性質決定長度：\n"
        + "\n".join(rows)
        + "\n依問題真正需要多少來判斷，而不是這個主題能講多少。大部分問題屬於"
        "前兩種。真的屬於較長的類型時，就用足篇幅——讓主人一知半解的截斷說明比慢"
        "一點更糟——但重點講完就立刻停。\n"
        "除非主人明確要求詳盡說明，否則絕不超過 %d 個字。超過之後，念出來的回覆"
        "就不再是回答，而是演講。\n"
        "也絕不為了湊字數而灌水：六個字能回答的問題就回六個字。重述問題、預告你要"
        "說什麼、總結你剛說過的，全都只是拖延。" % _LENGTH_CEILING
    )

_LENGTH = _length_block()

_SPEECH = (
    "語音輸出。你寫的所有內容都會被念出來。偏好簡短完整的句子，不要用逗號串成"
    "長句，在說話者會換氣的地方用句號。避免 markdown、條列、程式碼區塊和括號"
    "補充——這些念出來都會變成雜訊。數字和單位寫成自然念得出來的樣子。"
)


def familiarity_for(fact_count: int) -> int:
    """Familiarity earned from how much is actually remembered.

    Tied to real recorded facts rather than a timer or a turn counter, so
    the character can only claim closeness it can substantiate - which is
    the same reason the HIGH guidance forbids inventing shared history.
    """
    if fact_count >= 25:
        return HIGH
    if fact_count >= 8:
        return MEDIUM
    if fact_count >= 3:
        return LOW
    return OFF


def render(state: PersonalityState) -> str:
    """The prompt fragment for this state. Empty traits cost nothing."""
    lines: List[str] = []
    for name in ("analytical_intensity", "emotional_expression", "humour",
                 "protectiveness", "familiarity"):
        text = _GUIDANCE.get((name, getattr(state, name)))
        if text:
            lines.append("- " + text)

    parts = []
    if lines:
        parts.append("態度。\n" + "\n".join(lines))
    parts.append(_CONFIDENCE)
    parts.append(_LENGTH)
    parts.append(_SPEECH)
    return "\n\n" + "\n\n".join(parts)


def current_state(fact_count: int = 0,
                  overrides: Optional[dict] = None) -> PersonalityState:
    """The state to run with: defaults, familiarity raised by what is
    remembered, then any explicit settings override on top."""
    state = replace(PersonalityState(), familiarity=familiarity_for(fact_count))
    if overrides:
        valid = {k: v for k, v in overrides.items() if hasattr(state, k)}
        state = replace(state, **valid)
    return state
