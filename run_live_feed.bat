@echo off
setlocal enabledelayedexpansion

echo ======================================================================
echo    NIFTY REAL-TIME QUOTE FEED SYNC SENTINEL
echo    Updates live_quotes.json and pushes to GitHub Pages
echo ======================================================================

cd /d "C:\Users\HP\.gemini\antigravity\scratch\nifty-regime-hmm"

:loop
echo [%date% %time%] Fetching live NSE market quotes...
python update_live_quotes.py

echo Syncing to GitHub Pages origin...
git add live_quotes.json
git diff --staged --quiet
if errorlevel 1 (
    git commit -m "Live NSE Quote Feed Tick: %time% [skip ci]"
    git push origin main
    echo [OK] Updated quotes published to GitHub Pages!
) else (
    echo [INFO] Quotes unchanged.
)

echo.
echo Waiting 60 seconds before next market sweep... (Press Ctrl+C to stop)
timeout /t 60 /nobreak >nul
goto loop
