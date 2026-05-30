@echo off
set PYTHONIOENCODING=utf-8
title YouTube Transcription Pipeline
echo ============================================================
echo Starting Transcription Task...
echo ============================================================
e:\desktop\gemini-json\.venv\Scripts\python.exe e:\desktop\gemini-json\cli_transcribe.py
echo.
echo ============================================================
echo Task finished or crashed.
pause
