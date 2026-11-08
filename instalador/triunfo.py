"""Abre o TRIunfo na edição Estudante (ADR 0017): sobe o servidor local e abre o navegador.

O atalho do instalador roda:  python\\python.exe triunfo.py   (janela minimizada; fechar a janela fecha o TRIunfo)
"""
import json
import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
os.chdir(RAIZ)
sys.path.insert(0, str(RAIZ))
PORTAS = range(8765, 8775)  # longe da 8000, que outros programas costumam usar
ARQUIVO_PORTA = RAIZ / "data" / ".porta"  # a porta da última vez: testar só ela evita esperas


def triunfo_em(porta: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{porta}/api/versao", timeout=1) as r:
            return "atual" in json.load(r)
    except Exception:
        return False


def livre(porta: int) -> bool:
    # Reservar é instantâneo; tentar conectar numa porta fechada leva ~1 s no Windows.
    with socket.socket() as s:
        try:
            s.bind(("127.0.0.1", porta))
            return True
        except OSError:
            return False


def main() -> None:
    anterior = int(ARQUIVO_PORTA.read_text()) if ARQUIVO_PORTA.exists() else None
    if anterior and not livre(anterior) and triunfo_em(anterior):  # já está aberto: só mostra de novo
        webbrowser.open(f"http://127.0.0.1:{anterior}")
        return
    porta = next((p for p in PORTAS if livre(p)), None)
    if porta is None:
        input("Não foi possível abrir o TRIunfo: todas as portas estão ocupadas. Reinicie o computador e tente de novo.")
        return

    if os.name == "nt":
        import ctypes
        ctypes.windll.kernel32.SetConsoleTitleW("TRIunfo - feche esta janela para sair")
    import uvicorn
    from app.main import app

    ARQUIVO_PORTA.write_text(str(porta))
    url = f"http://127.0.0.1:{porta}"

    def abrir_quando_pronto():
        for _ in range(300):  # até 30 s em PCs bem lentos
            if not livre(porta):  # o servidor já reservou a porta
                webbrowser.open(url)
                return
            time.sleep(0.1)

    threading.Thread(target=abrir_quando_pronto, daemon=True).start()
    print(f"TRIunfo aberto em {url}\n\nPode minimizar esta janela. Para fechar o TRIunfo, feche esta janela.")
    uvicorn.run(app, host="127.0.0.1", port=porta, log_level="warning")


if __name__ == "__main__":
    main()
