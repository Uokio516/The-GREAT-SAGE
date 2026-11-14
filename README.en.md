# Great Sage (Traditional Chinese · Taiwanese Mandarin edition)

[繁體中文](README.md) | **English**

A local-first Windows voice AI assistant. Hold Alt+1 and speak; Great Sage answers in Mandarin with a Taiwanese accent, and can open apps and websites, search the web, and look at your screen.

This is a fork of [shogunyan12/The-GREAT-SAGE](https://github.com/shogunyan12/The-GREAT-SAGE). The original author, Krazaa, built the English version, named after the skill "Great Sage" from *That Time I Got Reincarnated as a Slime*. This fork localizes it to Traditional Chinese, Taiwanese wording and a Taiwanese-accented voice. For the original English documentation, see the [upstream README](https://github.com/shogunyan12/The-GREAT-SAGE#readme).

> All localization changes live on the **`zh-tw` branch**; `master` is the upstream version.

---

## What's different from upstream

### Localization
- **Interface**: menus, settings, the chat panel and messages are in Traditional Chinese.
- **Persona**: the system prompt was rewritten in Chinese while keeping Great Sage's voice, e.g. 「告。」 (Notice.), 「解。」 (Answer.), 「尚未取得。」 (Not yet acquired.), 「警告。預測結果不利。」 (Warning. Projected outcome is unfavourable.).
- **Simplified → Traditional**: when the model or speech recognition emits Simplified Chinese, [OpenCC](https://github.com/yichen0831/opencc-python) (s2twp) converts it to Traditional Chinese with Taiwanese vocabulary.
- **Speech recognition**: Whisper switched from the English-only `base.en` to multilingual `small`, fixed to Chinese; mixed Chinese–English commands such as 「打開 Spotify」 still work.
- **Wake words**: 「大賢者」, 「嘿大賢者」, 「智慧之王」. Upstream's matcher stripped every non-ASCII character, so a Chinese wake word could never match; this is fixed.
- **Chinese commands**: phrases like 「現在幾點」 (what time is it), 「打開下載資料夾」 (open my downloads folder) or 「在 YouTube 搜尋……然後點第一個」 (search YouTube for … and play the first one) are routed straight to tools. `check_routing.py` grew from 49 to 83 cases; the original English commands still work.
- **Other Chinese adaptations**: Chinese versions of the guardrails (persona breaks such as "I am a language model", prompt leaks), memory recall (character bigrams as keywords), and mode names.

### Taiwanese-accented voice (F5-TTS)
- **Default voices**: three Taiwanese female speakers picked from the [Mozilla Common Voice](https://commonvoice.mozilla.org/) 25 Taiwan Mandarin dataset (CC0, via [OpenFormosa/common_voice_25_zh-TW](https://huggingface.co/datasets/OpenFormosa/common_voice_25_zh-TW)) as reference voices: `voice_cv01`, `voice_cv09`, `voice_cv15`. The default is cv09.
- **Sentence-by-sentence synthesis**: Chinese is synthesized one sentence at a time with a fixed 0.3 s pause in between. Synthesizing the whole reply at once and then speeding it up squashed the pauses.
- **Automatic speaking rate**: the rate is normalized to about 5 characters per second based on the reference clip.
- **Text clean-up before speaking** (audio only; the on-screen text is unchanged):
  - The enumeration comma 「、」 is read as a pause.
  - Quotes and brackets are dropped.
  - Numbers are read in Chinese, e.g. 「20%」 as 「百分之二十」 and 「20-27度」 as 「二十到二十七度」.
  - Model numbers are read digit by digit, e.g. 「RTX 5090」 as 「RTX 五零九零」.
- **No swallowed words**: reference clips are kept under 10.5 s (F5 trims longer ones, which leaks the clip's tail into the output), and very short sentences such as 「告。」 are merged into the next one.

### Bug fixes
- **Missing voice-line clips**: upstream removed most pre-recorded clips but the config still pointed at `notice.wav`, so the whole voice engine failed to start and the app fell back to text only. Missing clips are now skipped.
- **FFmpeg DLLs**: recent torchaudio needs the DLLs of a **shared** FFmpeg 4–7 build. The app now loads them from the project's `ffmpeg\bin` (Python on Windows does not search PATH for DLLs).
- **Duplicate launches**: only one instance can run. Start-up takes 10+ seconds, and clicking the shortcut again used to start several copies that fought over the hotkey and microphone.
- **Offline-first speech recognition**: Whisper loads the locally cached model instead of contacting Hugging Face on every load.
- **Chat panel menu**: in the standalone chat panel window, the three-dot menu and confirmation dialogs were hidden by CSS, so clicks appeared to do nothing.
- **Encoding**: Taiwanese Windows defaults to cp950. The app now runs in UTF-8 mode and decodes child-process output as UTF-8 to avoid mojibake.

---

## Installation (Windows 10/11, NVIDIA GPU)

Requirements:

| Item | Notes |
|---|---|
| Python 3.14 | the main app |
| Python 3.11 | only for the transparent overlay (PySide6 6.4.3 has no 3.14 build) |
| [Ollama](https://ollama.com/download) | local language model; pull `qwen3.5:4b` |
| FFmpeg 7.x **shared** build | e.g. [ffmpeg-7.1.1-full_build-shared](https://github.com/GyanD/codexffmpeg/releases/download/7.1.1/ffmpeg-7.1.1-full_build-shared.zip); put its `bin` folder at `ffmpeg\bin` in the project. **FFmpeg 8 and static builds will not work** |
| NVIDIA GPU | 8 GB VRAM works, but not alongside a large game |

```powershell
git clone -b zh-tw https://github.com/Uokio516/The-GREAT-SAGE.git
cd The-GREAT-SAGE

# Main app: install the CUDA build of PyTorch first, then everything else
py -3.14 -m venv .venv
.venv\Scripts\pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128
.venv\Scripts\pip install -r requirements.txt

# Overlay environment
py -3.11 -m venv .overlay-venv
.overlay-venv\Scripts\pip install PySide6==6.4.3

# Language model
ollama pull qwen3.5:4b

# Run (-X utf8 matters: it prevents garbled Chinese)
.venv\Scripts\pythonw.exe -X utf8 app.py
```

The first time Great Sage speaks it downloads the voice models (F5-TTS about 3.6 GB, Whisper small about 460 MB), so the first reply is slow. If anything goes wrong, check `great_sage.log` in the project folder first.

## Usage

| Action | What it does |
|---|---|
| Hold **Alt+1** | talk; release to send. Works from any window, including games |
| Click the core | open the menu: settings, chat, logs, overlay |
| Say 「大賢者，……」 | voice wake-up (enable it in settings first) |
| ✕ at the top right | quit Great Sage |

Things to try:

- 「現在幾點」 (what time is it)
- 「顯存還剩多少」 (how much VRAM is free)
- 「打開 Spotify」 (open Spotify)
- 「打開下載資料夾」 (open my downloads folder)
- 「搜尋台中明天的天氣」 (search for tomorrow's weather in Taichung)
- 「在 YouTube 搜尋轉生史萊姆片頭然後點第一個」 (search YouTube for the Slime opening and play the first result)
- 「看一下我的螢幕」 (look at my screen)

## Tuning

The main settings are in `great_sage/config/settings.py`:

| Setting | Default | Purpose |
|---|---|---|
| `STT_MODEL` | `small` | speech recognition model (base / small / medium; larger is more accurate and slower) |
| `F5_CJK_CHARS_PER_SEC` | `5.0` | Chinese speaking rate (characters per second) |
| `F5_CJK_SENTENCE_GAP` | `0.3` | pause between sentences, in seconds |
| `F5_CJK_SPLIT_COMMA` | `False` | `True` also splits at commas, with a fixed pause |
| `F5_NFE_STEP_CJK` | `32` | sampling steps for Chinese; higher is clearer and slower |

Switch voices in the interface under 設定 → 聲音自訂 (Settings → Voice). To use your own voice, put a clear 5–10 s recording in `voice_samples/candidates/` with a `.txt` transcript of the same name. Keep the clip under 10.5 s.

## Checks

Run these after changing the code (the build also runs them):

```powershell
.venv\Scripts\python -X utf8 check_js.py
.venv\Scripts\python -X utf8 check_shaders.py
.venv\Scripts\python -X utf8 check_routing.py
```

## License and sources

- **Code**: by the original author, [shogunyan12 (Krazaa)](https://github.com/shogunyan12/The-GREAT-SAGE). The upstream project **has no license**. This fork publishes its changes as a GitHub fork under GitHub's Terms of Service and does not add a license. Ask the original author before using it for anything else.
- **Default voices** `voice_cv01` / `voice_cv09` / `voice_cv15`: from the Mozilla Common Voice Taiwan Mandarin dataset, CC0 (public domain). Per Common Voice's terms, do not attempt to identify the speakers.
- **Upstream voice lines**: the clips in `voice_lines/` come from the anime *That Time I Got Reincarnated as a Slime* and belong to their rights holders; the original author notes they are for personal use only.
- **"Great Sage"** is a character and skill name from *That Time I Got Reincarnated as a Slime* (Fuse / Kodansha). This is an unofficial fan project, not affiliated with the original work or Kodansha.
