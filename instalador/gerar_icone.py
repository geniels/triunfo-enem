"""Gera instalador/triunfo.ico a partir de app/static/icone.svg, usando o Chrome para desenhar cada tamanho.

Uso (só quando o ícone mudar; o .ico gerado vai para o repositório):
    .venv\\Scripts\\python.exe instalador\\gerar_icone.py
"""
import struct
import subprocess
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SVG = RAIZ / "app" / "static" / "icone.svg"
ICO = RAIZ / "instalador" / "triunfo.ico"
TAMANHOS = [16, 24, 32, 48, 64, 256]
CHROME = [Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
          Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")]


def desenhar(tamanho: int, pasta: Path) -> bytes:
    html = pasta / f"i{tamanho}.html"
    png = pasta / f"i{tamanho}.png"
    html.write_text(f'<html><body style="margin:0"><img src="{SVG.as_uri()}" width="{tamanho}" height="{tamanho}">'
                    "</body></html>", encoding="utf-8")
    navegador = next(p for p in CHROME if p.exists())
    subprocess.run([str(navegador), "--headless", "--disable-gpu", "--allow-file-access-from-files",
                    "--hide-scrollbars", "--default-background-color=00000000",  # fundo transparente
                    f"--window-size={tamanho},{tamanho}", f"--screenshot={png}", html.as_uri()],
                   check=True, capture_output=True, timeout=60)
    return png.read_bytes()


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        imagens = [(t, desenhar(t, Path(tmp))) for t in TAMANHOS]
    cabecalho = struct.pack("<HHH", 0, 1, len(imagens))
    deslocamento, entradas, corpo = 6 + 16 * len(imagens), b"", b""
    for t, dados in imagens:  # ICO com PNGs dentro (aceito desde o Windows Vista)
        entradas += struct.pack("<BBBBHHII", t % 256, t % 256, 0, 0, 1, 32, len(dados), deslocamento + len(corpo))
        corpo += dados
    ICO.write_bytes(cabecalho + entradas + corpo)
    print(f"{ICO} ({len(imagens)} tamanhos, {ICO.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
