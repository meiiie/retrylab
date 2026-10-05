@echo off
chcp 65001 >nul
title RetryLab
setlocal
python -X utf8 -c "import sys" >nul 2>nul
if not "%errorlevel%"=="0" (
    echo.
    echo   Không tìm thấy Python trên máy này, nên chưa mở được RetryLab.
    echo   Hãy cài Python 3.13 từ https://www.python.org/downloads/ và chọn "Add python.exe to PATH" khi cài.
    echo   Sau đó bấm đúp RetryLab.cmd lần nữa.
    echo.
    pause
    exit /b 9009
)
python -X utf8 "%~dp0app\desktop.py" %*
set "RETRYLAB_EXIT=%errorlevel%"
if not "%RETRYLAB_EXIT%"=="0" pause
exit /b %RETRYLAB_EXIT%
