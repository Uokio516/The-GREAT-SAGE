"""Great Sage - local-first AI desktop companion."""

import os as _os
import sys as _sys


def _register_ffmpeg_dlls():
    """讓 torchcodec 找得到 FFmpeg 的 DLL。

    新版 torchaudio 讀音檔要經過 torchcodec，而 torchcodec 需要「shared 版」
    FFmpeg 4～7 的 DLL（avcodec-61.dll 等）。Windows 上的 Python 3.8+ 載入
    原生 DLL 時不看 PATH，只能用 os.add_dll_directory()。詳見 NOTES.md
    「FFmpeg must be a specific kind of build」。

    找的順序：專案內的 ffmpeg/bin（建議放 7.1.1 shared 版）→ 環境變數
    GREAT_SAGE_FFMPEG_BIN。系統 PATH 上的 ffmpeg 常常是 static 版或 8.x，
    torchcodec 用不了，所以不拿它來猜。
    """
    if _sys.platform != "win32" or not hasattr(_os, "add_dll_directory"):
        return
    here = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    base = getattr(_sys, "_MEIPASS", None)
    candidates = [
        _os.environ.get("GREAT_SAGE_FFMPEG_BIN", ""),
        _os.path.join(here, "ffmpeg", "bin"),
        _os.path.join(base, "ffmpeg", "bin") if base else "",
    ]
    for path in candidates:
        if path and _os.path.isdir(path) and any(
                n.startswith("avcodec-") and n.endswith(".dll")
                for n in _os.listdir(path)):
            try:
                _os.add_dll_directory(path)
                # 子程序（log 視窗等）也一併看得到
                _os.environ["PATH"] = path + _os.pathsep + _os.environ.get("PATH", "")
            except OSError:
                pass
            return


_register_ffmpeg_dlls()
