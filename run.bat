@echo off
title CSV Imputer & 3NF Normalizer Engine
cd /d "%~dp0"

where uv >nul 2>&1
if %errorlevel% equ 0 (
    uv run imputer.py %*
) else (
    python imputer.py %*
)

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Script exited with an error code.
    pause
)
