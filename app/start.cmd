@echo off
cd /d "%~dp0.."
python app\launch.py
if errorlevel 1 pause
