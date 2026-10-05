@echo off
cd /d "%~dp0.."
python -X utf8 app\demo_check.py
if errorlevel 1 goto failed
echo Demo check passed. Open RetryLab.cmd and follow app\DEMO_GIA_SU_AI.md for the presentation steps.
pause
exit /b 0
:failed
echo Demo check failed. Keep this window open and read the error above.
pause
exit /b 1
