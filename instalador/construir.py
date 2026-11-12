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
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from app.versao import VERSAO  # noqa: E402

PY_VERSAO = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"  # a mesma do .venv
PY_URL = f"https://www.python.org/ftp/python/{PY_VERSAO}/python-{PY_VERSAO}-embed-amd64.zip"
# SHA-256 conhecido do Python embutido (ADR 0027). O de 3.12.10 foi conferido pelo MD5 publicado no python.org.
# Versão nova do Python: baixar, conferir com o python.org e acrescentar aqui.
PY_SHA256 = {"3.12.10": "4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3"}
LOCK = RAIZ / "instalador" / "requirements-lock.txt"  # dependências com versão e hash travados
BUILD = RAIZ / "build"
ALVO = BUILD / "TRIunfo"
DIST = RAIZ / "dist"
ISCC = [Path.home() / "AppData/Local/Programs/Inno Setup 6/ISCC.exe", Path("C:/Program Files (x86)/Inno Setup 6/ISCC.exe")]


def etapa(texto: str) -> None:
    print(f"\n== {texto}")


def python_embutido() -> None:
    cache = BUILD / f"python-{PY_VERSAO}-embed-amd64.zip"
    if not cache.exists():
        etapa(f"Baixando o Python {PY_VERSAO} embutido (python.org)")
        urllib.request.urlretrieve(PY_URL, cache)
    esperado = PY_SHA256.get(PY_VERSAO)
    if not esperado:
        sys.exit(f"Sem SHA-256 conhecido para o Python {PY_VERSAO}: confira o arquivo e acrescente em PY_SHA256.")
    if hashlib.sha256(cache.read_bytes()).hexdigest() != esperado:
        cache.unlink()
        sys.exit(f"O Python embutido baixado não confere com o SHA-256 conhecido ({PY_URL}). Nada foi montado.")
    destino = ALVO / "python"
    with zipfile.ZipFile(cache) as z:
        z.extractall(destino)
    # O ._pth define o caminho de módulos do Python embutido: as dependências e a pasta do app (..).
    pth = next(destino.glob("python*._pth"))
    pth.write_text(f"{pth.stem}.zip\n.\nLib\\site-packages\n..\nimport site\n", encoding="utf-8")


def dependencias() -> None:
    etapa("Instalando as dependências no Python embutido")
    # --require-hashes: todas as dependências, inclusive as indiretas, com versão e hash travados (ADR 0027).
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--no-compile", "--require-hashes", "--only-binary=:all:",
                    "-r", str(LOCK), "--target", str(ALVO / "python" / "Lib" / "site-packages")], check=True)


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
    etapa("Copiando questões, imagens e parâmetros TRI (só o banco de questões: nada de dados de aluno)")
    origem = RAIZ / "data"
    for marca in (".importado", ".tri"):
        if not (origem / marca).exists():
            sys.exit(f"Falta data/{marca}: rode os importadores antes de gerar o instalador.")
    destino = ALVO / "data"
    shutil.copytree(origem / "imagens", destino / "imagens")
    for marca in (".importado", ".tri"):
        shutil.copy2(origem / marca, destino / marca)
    origem_db = sqlite3.connect(origem / "questoes.db")
    db = sqlite3.connect(destino / "questoes.db")
    origem_db.backup(db)  # cópia consistente mesmo com o servidor aberto
    origem_db.close()
    db.execute("PRAGMA journal_mode = DELETE")  # um arquivo só, sem -wal/-shm
    db.execute("VACUUM")
    questoes = db.execute("SELECT COUNT(*) FROM questoes").fetchone()[0]
    params = db.execute("SELECT COUNT(*) FROM questoes_tri").fetchone()[0]
    db.close()
    print(f"  {questoes} questões, {params} com parâmetros TRI")


def icone() -> None:
    etapa("Copiando o ícone (gerado por instalador/gerar_icone.py)")
    for destino in (BUILD / "triunfo.ico", ALVO / "triunfo.ico"):
        shutil.copy2(RAIZ / "instalador" / "triunfo.ico", destino)


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
