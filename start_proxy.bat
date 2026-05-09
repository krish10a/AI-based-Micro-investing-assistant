@echo off
title Claude Proxy Server
cd /d "%~dp0free-claude-proxy"
echo Starting NVIDIA NIM Proxy on port 8082...
uv run uvicorn server:app --host 0.0.0.0 --port 8082 --reload
pause
