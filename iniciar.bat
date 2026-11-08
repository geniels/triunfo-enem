@echo off
chcp 65001 >nul
title TRIunfo
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo Python nao encontrado. Instale em https://www.python.org/downloads/ e marque "Add to PATH".
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Preparando o ambiente pela primeira vez...
  python -m venv .venv || goto erro
)
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt || goto erro

if not exist "data\.importado" (
  echo Baixando as questoes do ENEM pela primeira vez. Isso leva alguns minutos e precisa de internet.
  ".venv\Scripts\python.exe" scripts\importar_enem_dev.py || goto erro
)

echo.
echo TRIunfo rodando em http://localhost:8000
echo Feche esta janela para desligar.
start "" http://localhost:8000
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
goto :eof

:erro
echo.
echo Ocorreu um erro. Veja a mensagem acima.
pause
