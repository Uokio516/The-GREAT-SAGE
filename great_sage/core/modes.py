r"""Modes (spec S39/S40): what Great Sage is allowed to spend right now.

A mode is not a label. Each one changes real behaviour, because the point
is the RTX 3060 that Great Sage, the voice model and whatever Krazaa is
actually doing all share:

  COMPANION  the default. Everything on.
  WORK       everything on; the assistant is expected to stay quiet.
  GAMING     unload the model, drop the HUD frame rate, stop listening.
             This is the mode that matters - it hands back the ~4GB the
             model holds and the GPU time the HUD was spending.
  CODING     everything on, longer answers tolerated.
  SLEEP      unload the model, minimum frame rate, no listening.
  PRIVATE    local model only, no web, whatever else is on.
  ONLINE     an API provider may be used.

PRIVATE and ONLINE are about WHERE data goes; the rest are about what is
spent. They are kept in one list anyway, because a mode the user has to
combine by hand is a mode they will get wrong.

Nothing here talks to the HUD or to Ollama directly - a mode only
describes limits, and the server applies them. That keeps the policy
readable in one place instead of scattered through the code that enforces
it.
"""

import logging
from dataclasses import dataclass
from typing import Dict

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Mode:
    name: str
    label: str
    description: str
    # Keep the model resident between replies? False frees ~4GB of VRAM
    # at the cost of a reload (~4s) on the next message.
    keep_model_loaded: bool = True
    # Frame cap the HUD should use. None means "leave it alone".
    hud_fps: int = 0
    # Listen for the wake word in the background?
    wake_word: bool = True
    # May tools reach the network, whatever the permission says?
    allow_web: bool = True
    # May an API provider be used, whatever the settings say?
    allow_online: bool = True


MODES: Dict[str, Mode] = {
    "companion": Mode(
        "companion", "陪伴",
        "一般對話，所有功能都可用。"),
    "work": Mode(
        "work", "工作",
        "所有功能都可用，大賢者盡量不打擾。"),
    "gaming": Mode(
        "gaming", "遊戲",
        "釋放顯示卡：回覆之間卸載模型、介面降低幀率、"
        "停止背景聆聽。",
        keep_model_loaded=False, hud_fps=15, wake_word=False),
    "coding": Mode(
        "coding", "寫程式",
        "所有功能都可用，回答可以比較長。"),
    "sleep": Mode(
        "sleep", "休眠",
        "最低限度。卸載模型，在你先開口之前背景什麼都不跑。",
        keep_model_loaded=False, hud_fps=10, wake_word=False),
    "private": Mode(
        "private", "隱私",
        "只用本機。不論設定怎麼寫，都不上網、不用線上模型。",
        allow_web=False, allow_online=False),
    "online": Mode(
        "online", "線上",
        "有設定線上模型時可以使用。"),
}

DEFAULT = "companion"


def get(name: str) -> Mode:
    return MODES.get((name or "").strip().lower(), MODES[DEFAULT])


def public_list():
    return [{"name": m.name, "label": m.label, "description": m.description}
            for m in MODES.values()]
