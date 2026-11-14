# 大賢者 Great Sage（繁體中文・台灣腔版）

本機執行的 Windows 語音 AI 助理。按住 Alt+1 說話，大賢者會用台灣腔的中文回答，也能幫你開程式、開網頁、搜尋、看螢幕。

這個專案是 [shogunyan12/The-GREAT-SAGE](https://github.com/shogunyan12/The-GREAT-SAGE) 的 fork。原作者 Krazaa 做了英文版，名字取自《關於我轉生變成史萊姆這檔事》裡的技能「大賢者」。這個 fork 把它改成繁體中文、台灣用語、台灣腔語音。原作者的英文說明保留在 [README.en.md](README.en.md)。

> 所有繁中化的修改都在 **`zh-tw` 分支**；`master` 是原作者的版本。

---

## 跟原版差在哪

### 中文化
- **介面**：選單、設定、對話面板、提示訊息全部改成繁體中文。
- **人設**：提示詞改寫成中文，保留大賢者的口吻，例如「告。」「解。」「尚未取得。」「警告。預測結果不利。」。
- **簡轉繁**：模型或語音辨識偶爾吐出簡體字時，用 [OpenCC](https://github.com/yichen0831/opencc-python)（s2twp）自動轉成台灣繁體與台灣用語，例如「軟件」變「軟體」、「視頻」變「影片」。
- **語音辨識**：Whisper 從只認英文的 `base.en` 改成多語的 `small`，固定辨識中文，中英夾雜（「打開 Spotify」）也聽得懂。
- **喚醒詞**：改成「大賢者」「嘿大賢者」「智慧之王」。原版的比對會把中文字全部濾掉，中文喚醒詞永遠對不上，已修正。
- **中文指令**：「現在幾點」「打開下載資料夾」「在 YouTube 搜尋轉生史萊姆片頭然後點第一個」這類說法會直接執行。`check_routing.py` 的測試從 49 項加到 83 項，原本的英文指令照樣能用。
- **其他中文適配**：中文版的防護規則（擋「我是語言模型」這類出戲回答、擋洩漏提示詞）、記憶檢索（中文用相鄰兩字當關鍵詞）、對話模式名稱。

### 台灣腔語音（F5-TTS）
- **預設聲音**：從 [Mozilla Common Voice](https://commonvoice.mozilla.org/) 25 版台灣華語資料集（CC0，經 [OpenFormosa/common_voice_25_zh-TW](https://huggingface.co/datasets/OpenFormosa/common_voice_25_zh-TW) 取得）挑出三位台灣女聲，當作參考聲音：`voice_cv01`、`voice_cv09`、`voice_cv15`，預設是 cv09。
- **逐句合成**：中文一句一句合成，句與句之間插入固定 0.3 秒停頓。整段一起合成再加速，停頓會被壓扁。
- **自動語速**：依參考錄音的語速，自動換算成每秒約 5 個字。
- **念前整理文字**（只影響聲音，畫面文字不變）：
  - 頓號當逗號停頓。
  - 拿掉引號和括號。
  - 數字轉中文念法，例如「20%」念「百分之二十」、「20-27度」念「二十到二十七度」。
  - 型號一個一個念，例如「RTX 5090」念「RTX 五零九零」。
- **避免吞字**：參考錄音限制在 10.5 秒以內（F5 會把太長的參考錄音截短，尾巴會漏進輸出）；很短的句子（例如「告。」）併入下一句一起念。

### Bug 修正
- **預錄語音缺檔**：原作者刪掉了大部分預錄語音檔，設定卻還指著 `notice.wav`，造成整個語音引擎初始化失敗、只剩文字。現在缺檔只會略過那一句。
- **FFmpeg DLL**：新版 torchaudio 需要 FFmpeg 4～7 **shared** 版的 DLL。程式會自動載入專案內 `ffmpeg\bin` 的 DLL（Windows 的 Python 不會從 PATH 找 DLL）。
- **重複啟動**：只允許同時開一個大賢者。啟動要十幾秒，多點幾次會開出好幾個，互搶快捷鍵和麥克風。
- **語音辨識離線優先**：Whisper 優先用本機已下載的模型，不必每次上網檢查。
- **對話面板選單**：在獨立的對話面板視窗裡，三點選單和確認框被 CSS 一起藏掉，點了看不到。已修正。
- **編碼**：台灣版 Windows 的預設編碼是 cp950。啟動一律用 UTF-8 模式，子程序輸出也用 UTF-8 解讀，避免亂碼。

---

## 安裝（Windows 10／11，NVIDIA 顯示卡）

需要：

| 項目 | 說明 |
|---|---|
| Python 3.14 | 主程式 |
| Python 3.11 | 只給透明浮窗用（PySide6 6.4.3 沒有 3.14 版） |
| [Ollama](https://ollama.com/download) | 本機語言模型，下載 `qwen3.5:4b` |
| FFmpeg 7.x **shared** 版 | 例如 [ffmpeg-7.1.1-full_build-shared](https://github.com/GyanD/codexffmpeg/releases/download/7.1.1/ffmpeg-7.1.1-full_build-shared.zip)，把裡面的 `bin` 放到專案的 `ffmpeg\bin`。**FFmpeg 8 或 static 版不能用** |
| NVIDIA 顯示卡 | 8GB 顯存可以跑，但不要同時開大型遊戲 |

```powershell
git clone -b zh-tw https://github.com/Uokio516/The-GREAT-SAGE.git
cd The-GREAT-SAGE

# 主程式環境：先裝 CUDA 版 PyTorch，再裝其他套件
py -3.14 -m venv .venv
.venv\Scripts\pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128
.venv\Scripts\pip install -r requirements.txt

# 浮窗環境
py -3.11 -m venv .overlay-venv
.overlay-venv\Scripts\pip install PySide6==6.4.3

# 語言模型
ollama pull qwen3.5:4b

# 啟動（-X utf8 很重要，避免中文亂碼）
.venv\Scripts\pythonw.exe -X utf8 app.py
```

第一次講話時會自動下載語音模型（F5-TTS 約 3.6GB、Whisper small 約 460MB），會等比較久。出問題時先看專案資料夾裡的 `great_sage.log`。

## 使用

| 操作 | 功能 |
|---|---|
| 按住 **Alt+1** | 說話，放開送出。在任何視窗都有效，玩遊戲時也行 |
| 點中間的核心 | 打開選單：設定、對話、紀錄、浮窗 |
| 說「大賢者，……」 | 語音喚醒（要先在設定開啟） |
| 視窗右上角 ✕ | 關閉大賢者 |

可以試試看這些說法：

- 「現在幾點」
- 「顯存還剩多少」
- 「打開 Spotify」
- 「打開下載資料夾」
- 「搜尋台中明天的天氣」
- 「在 YouTube 搜尋轉生史萊姆片頭然後點第一個」
- 「看一下我的螢幕」

## 調整

主要設定在 `great_sage/config/settings.py`：

| 設定 | 預設 | 用途 |
|---|---|---|
| `STT_MODEL` | `small` | 語音辨識模型（base／small／medium，越大越準越慢） |
| `F5_CJK_CHARS_PER_SEC` | `5.0` | 中文語速（字／秒） |
| `F5_CJK_SENTENCE_GAP` | `0.3` | 句子之間停頓幾秒 |
| `F5_CJK_SPLIT_COMMA` | `False` | `True`：逗號也切開，有固定停頓 |
| `F5_NFE_STEP_CJK` | `32` | 中文取樣步數，越高越清楚越慢 |

聲音可以在介面的「設定 → 聲音自訂」切換。如果想換成自己的聲音，把 5～10 秒、咬字清楚的錄音放進 `voice_samples/candidates/`，再附一個同名的 `.txt` 寫上逐字稿。錄音一定要在 10.5 秒以內。

## 檢查

改程式後跑一下這三個檢查（打包時也會自動跑）：

```powershell
.venv\Scripts\python -X utf8 check_js.py
.venv\Scripts\python -X utf8 check_shaders.py
.venv\Scripts\python -X utf8 check_routing.py
```

## 授權與來源

- **程式碼**：原作者 [shogunyan12（Krazaa）](https://github.com/shogunyan12/The-GREAT-SAGE)。原專案**沒有附授權條款**，這個 fork 依 GitHub 服務條款以 fork 形式公開修改，沒有另外加上授權。要拿去做其他用途前，請先取得原作者同意。
- **預設聲音** `voice_cv01`／`voice_cv09`／`voice_cv15`：取自 Mozilla Common Voice 台灣華語資料集，CC0（公眾領域）。依 Common Voice 的使用規範，請勿嘗試辨識錄音者的身分。
- **原版預錄語音**：`voice_lines/` 裡的片段來自動畫《關於我轉生變成史萊姆這檔事》，版權屬於原權利人。原作者註明只供個人使用。
- **「大賢者」**：是《關於我轉生變成史萊姆這檔事》（伏瀨／講談社）的角色與技能名稱。本專案是非官方的粉絲作品，與原作和講談社無關。
