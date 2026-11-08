"""Gera o instalador da edição Estudante (ADR 0017).

Uso (na raiz do projeto, com o banco e os parâmetros TRI já importados):
    .venv\\Scripts\\python.exe instalador\\construir.py

Saída: dist\\TRIunfo-Estudante-<versão>.exe e o SHA-256 dele (para conferir a integridade).
Requer o Inno Setup 6 (winget install JRSoftware.InnoSetup).
"""
from __future__ import annotations

import hashlib
import shutil
import sqlite3
import struct
import subprocess
import sys
import urllib.request
import zipfile
import zlib
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from app.versao import VERSAO  # noqa: E402

PY_VERSAO = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"  # a mesma do .venv
PY_URL = f"https://www.python.org/ftp/python/{PY_VERSAO}/python-{PY_VERSAO}-embed-amd64.zip"
BUILD = RAIZ / "build"
ALVO = BUILD / "TRIunfo"
DIST = RAIZ / "dist"
ISCC = [Path.home() / "AppData/Local/Programs/Inno Setup 6/ISCC.exe", Path("C:/Program Files (x86)/Inno Setup 6/ISCC.exe")]
TABELAS_DO_ALUNO = ["respostas", "redacoes", "simulados", "plano", "plano_feitos"]


def etapa(texto: str) -> None:
    print(f"\n== {texto}")


def python_embutido() -> None:
    cache = BUILD / f"python-{PY_VERSAO}-embed-amd64.zip"
    if not cache.exists():
        etapa(f"Baixando o Python {PY_VERSAO} embutido (python.org)")
        urllib.request.urlretrieve(PY_URL, cache)
    destino = ALVO / "python"
    with zipfile.ZipFile(cache) as z:
        z.extractall(destino)
    # O ._pth define o caminho de módulos do Python embutido: as dependências e a pasta do app (..).
    pth = next(destino.glob("python*._pth"))
    pth.write_text(f"{pth.stem}.zip\n.\nLib\\site-packages\n..\nimport site\n", encoding="utf-8")


def dependencias() -> None:
    etapa("Instalando as dependências no Python embutido")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--no-compile", "-r", str(RAIZ / "requirements.txt"),
                    "--target", str(ALVO / "python" / "Lib" / "site-packages")], check=True)


def precompilar() -> None:
    """Gera os .pyc na montagem (mesma versão do Python embutido): a primeira abertura do aluno fica mais rápida."""
    etapa("Pré-compilando o código")
    import compileall
    for pasta in ("python/Lib/site-packages", "app", "scripts"):
        compileall.compile_dir(ALVO / pasta, quiet=1)


def codigo() -> None:
    etapa("Copiando o TRIunfo")
    ignorar = shutil.ignore_patterns("__pycache__", "*.pyc")
    shutil.copytree(RAIZ / "app", ALVO / "app", ignore=ignorar)
    shutil.copytree(RAIZ / "scripts", ALVO / "scripts", ignore=ignorar)
    for arquivo in ("LICENSE", "README.md"):
        shutil.copy2(RAIZ / arquivo, ALVO / arquivo)
    shutil.copy2(RAIZ / "instalador" / "triunfo.py", ALVO / "triunfo.py")


def dados() -> None:
    etapa("Copiando questões, imagens e parâmetros TRI (banco sem dados de aluno)")
    origem = RAIZ / "data"
    for marca in (".importado", ".tri"):
        if not (origem / marca).exists():
            sys.exit(f"Falta data/{marca}: rode os importadores antes de gerar o instalador.")
    destino = ALVO / "data"
    shutil.copytree(origem / "imagens", destino / "imagens")
    for marca in (".importado", ".tri"):
        shutil.copy2(origem / marca, destino / marca)
    origem_db = sqlite3.connect(origem / "enem.db")
    db = sqlite3.connect(destino / "enem.db")
    origem_db.backup(db)  # cópia consistente mesmo com o servidor aberto
    origem_db.close()
    for tabela in TABELAS_DO_ALUNO:
        db.execute(f"DELETE FROM {tabela}")
    db.commit()
    db.execute("PRAGMA journal_mode = DELETE")  # um arquivo só, sem -wal/-shm
    db.execute("VACUUM")
    questoes = db.execute("SELECT COUNT(*) FROM questoes").fetchone()[0]
    params = db.execute("SELECT COUNT(*) FROM questoes_tri").fetchone()[0]
    db.close()
    print(f"  {questoes} questões, {params} com parâmetros TRI")


def png(tamanho: int) -> bytes:
    """Ícone desenhado à mão: quadrado arredondado azul com um sinal de visto branco (sem dependências)."""
    azul, branco = (31, 95, 209, 255), (255, 255, 255, 255)
    raio, linhas = tamanho * 0.22, []
    pontos = [(0.27, 0.53), (0.43, 0.69), (0.74, 0.34)]  # o "visto", em fração do tamanho
    espessura = tamanho * 0.11

    def perto_do_visto(x, y):
        for (x1, y1), (x2, y2) in zip(pontos, pontos[1:]):
            x1, y1, x2, y2 = x1 * tamanho, y1 * tamanho, x2 * tamanho, y2 * tamanho
            t = max(0, min(1, ((x - x1) * (x2 - x1) + (y - y1) * (y2 - y1)) / ((x2 - x1) ** 2 + (y2 - y1) ** 2)))
            if (x - x1 - t * (x2 - x1)) ** 2 + (y - y1 - t * (y2 - y1)) ** 2 <= (espessura / 2) ** 2:
                return True
        return False

    for y in range(tamanho):
        linha = bytearray([0])
        for x in range(tamanho):
            cx = min(max(x + 0.5, raio), tamanho - raio)
            cy = min(max(y + 0.5, raio), tamanho - raio)
            dentro = (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 <= raio ** 2
            linha += bytes(branco if dentro and perto_do_visto(x + 0.5, y + 0.5) else azul if dentro else (0, 0, 0, 0))
        linhas.append(bytes(linha))

    def bloco(tipo, dados):
        return struct.pack(">I", len(dados)) + tipo + dados + struct.pack(">I", zlib.crc32(tipo + dados))

    cab = struct.pack(">IIBBBBB", tamanho, tamanho, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + bloco(b"IHDR", cab) + bloco(b"IDAT", zlib.compress(b"".join(linhas), 9)) + bloco(b"IEND", b"")


def icone() -> None:
    etapa("Gerando o ícone")
    imagens = [(t, png(t)) for t in (16, 32, 48, 256)]
    cabecalho = struct.pack("<HHH", 0, 1, len(imagens))
    deslocamento, entradas, corpo = 6 + 16 * len(imagens), b"", b""
    for t, dados in imagens:
        entradas += struct.pack("<BBBBHHII", t % 256, t % 256, 0, 0, 1, 32, len(dados), deslocamento + len(corpo))
        corpo += dados
    ico = cabecalho + entradas + corpo
    (BUILD / "triunfo.ico").write_bytes(ico)
    (ALVO / "triunfo.ico").write_bytes(ico)


def instalador() -> Path:
    etapa("Gerando o instalador (Inno Setup)")
    iscc = next((p for p in ISCC if p.exists()), None)
    if not iscc:
        sys.exit("Inno Setup não encontrado. Instale com: winget install JRSoftware.InnoSetup")
    iss = RAIZ / "instalador" / "triunfo.iss"
    texto = iss.read_text(encoding="utf-8-sig")
    iss.write_text(texto, encoding="utf-8-sig")  # o Inno Setup precisa do BOM para ler os acentos
    subprocess.run([str(iscc), "/Q", f"/DVersao={VERSAO}", str(iss)], check=True)
    return DIST / f"TRIunfo-Estudante-{VERSAO}.exe"


def main() -> None:
    if ALVO.exists():
        shutil.rmtree(ALVO)
    ALVO.mkdir(parents=True)
    python_embutido()
    dependencias()
    codigo()
    precompilar()
    dados()
    icone()
    exe = instalador()
    sha = hashlib.sha256(exe.read_bytes()).hexdigest()
    (DIST / f"{exe.name}.sha256").write_text(f"{sha}  {exe.name}\n", encoding="utf-8")
    print(f"\nPronto: {exe} ({exe.stat().st_size / 1e6:.0f} MB)\nSHA-256: {sha}")


if __name__ == "__main__":
    main()
