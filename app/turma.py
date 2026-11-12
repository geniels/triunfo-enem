"""Modo turma (ADR 0022): um PC (o do organizador) serve o TRIunfo na rede local enquanto a turma está aberta.

- O servidor normal continua só em 127.0.0.1, sem login: é o dono do PC / organizador (aluno 1).
- O dono do PC pode definir nome e PIN para entrar pela rede como ele mesmo, no tablet ou celular, com o mesmo
  progresso (ADR 0025). As funções de administração continuam só no próprio PC.
- "Abrir turma" sobe um SEGUNDO servidor em 0.0.0.0. Tudo o que chega por ele exige nome + PIN de 4 dígitos.
- O PIN é guardado como hash (PBKDF2); o aparelho fica lembrado por um cookie assinado com HMAC.
"""
from __future__ import annotations

import functools
import hashlib
import hmac
import secrets
import socket
import sqlite3
import threading
import time
import unicodedata

PORTAS = range(8780, 8790)
TENTATIVAS = 5        # PINs errados seguidos antes de esperar
ESPERA_SEG = 60
COOKIE = "triunfo_turma"
ORGANIZADOR = 1       # o dono do PC (aluno "Eu"); entra pela rede só se tiver definido o PIN

_servidor = None      # uvicorn.Server da turma, quando aberta
_porta: int | None = None
_trava = threading.Lock()


# ---------------------------- PIN e cookie ----------------------------

def hash_pin(pin: str, sal: str | None = None) -> str:
    sal = sal or secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", pin.encode(), bytes.fromhex(sal), 200_000).hex()
    return f"{sal}${h}"


def pin_confere(pin: str, guardado: str | None) -> bool:
    if not guardado:
        return False
    sal, _ = guardado.split("$", 1)
    return hmac.compare_digest(hash_pin(pin, sal), guardado)


def segredo(con: sqlite3.Connection) -> bytes:
    """Chave para assinar os cookies, criada na primeira vez e guardada no aluno.db."""
    r = con.execute("SELECT valor FROM config WHERE chave = 'segredo_turma'").fetchone()
    if r:
        return bytes.fromhex(r[0])
    novo = secrets.token_hex(32)
    with con:
        con.execute("INSERT OR IGNORE INTO config (chave, valor) VALUES ('segredo_turma', ?)", (novo,))
    return segredo(con)


def _assinatura(con: sqlite3.Connection, aluno_id: int, pin_hash: str) -> str:
    # Entra o hash do PIN: quando o organizador gera um PIN novo, os aparelhos lembrados saem sozinhos.
    return hmac.new(segredo(con), f"{aluno_id}:{pin_hash}".encode(), hashlib.sha256).hexdigest()


def cookie_para(con: sqlite3.Connection, aluno_id: int) -> str:
    pin_hash = con.execute("SELECT pin_hash FROM alunos WHERE id = ?", (aluno_id,)).fetchone()[0]
    return f"{aluno_id}.{_assinatura(con, aluno_id, pin_hash)}"


def aluno_do_cookie(con: sqlite3.Connection, valor: str | None) -> int | None:
    try:
        texto_id, assinatura = (valor or "").split(".", 1)
        aluno_id = int(texto_id)
    except ValueError:
        return None
    r = con.execute("SELECT pin_hash FROM alunos WHERE id = ?", (aluno_id,)).fetchone()
    if not r or not r[0] or not hmac.compare_digest(_assinatura(con, aluno_id, r[0]), assinatura):
        return None
    return aluno_id


NAO_CONFERE = ("Nome ou PIN não conferem. Confira o que você digitou; se esqueceu o PIN, peça um novo a quem organiza "
               "a turma (ou, se o computador é seu, troque em Configurações).")


@functools.cache
def _hash_falso() -> str:
    return hash_pin("0000")


def chave_nome(nome: str) -> str:
    """Forma de comparar nomes: espaços normalizados e maiúsculas/minúsculas com acento ("JOÃO" = "joão").
    O COLLATE NOCASE do SQLite só ignora maiúsculas sem acento."""
    return unicodedata.normalize("NFKC", " ".join(nome.split())).casefold()


def achar(con: sqlite3.Connection, nome: str, com_pin: bool = True) -> int | None:
    """Id do aluno com esse nome. shortcut: percorre a tabela em Python; ok até milhares de alunos por PC."""
    chave = chave_nome(nome)
    filtro = " WHERE pin_hash IS NOT NULL" if com_pin else ""
    return next((i for i, n in con.execute(f"SELECT id, nome FROM alunos{filtro}") if chave_nome(n) == chave), None)


CADASTROS_POR_MINUTO = 5
_cadastros: dict[str, list[float]] = {}  # IP -> horários dos últimos cadastros (memória do processo)
_trava_cadastros = threading.Lock()


def pode_cadastrar(ip: str) -> bool:
    """Limite de cadastros por aparelho: um script na rede não enche a turma nem ocupa o PC com PBKDF2."""
    agora = time.time()
    with _trava_cadastros:
        recentes = [t for t in _cadastros.get(ip, []) if agora - t < 60]
        if len(recentes) >= CADASTROS_POR_MINUTO:
            _cadastros[ip] = recentes
            return False
        _cadastros[ip] = recentes + [agora]
        return True


def entrar(con: sqlite3.Connection, nome: str, pin: str) -> tuple[int | None, str]:
    """(id, "") se conferir; senão (None, mensagem para o aluno).

    A tentativa é reservada ANTES de calcular o hash, num UPDATE atômico: pedidos em paralelo não conseguem testar mais
    que TENTATIVAS PINs por janela. Nome inexistente e PIN errado dão a mesma resposta, no mesmo tempo."""
    agora = time.time()
    aluno_id = achar(con, nome)
    with con:
        r = con.execute(
            "UPDATE alunos SET tentativas = tentativas + 1 WHERE id = ? AND pin_hash IS NOT NULL "
            "AND (bloqueado_ate IS NULL OR bloqueado_ate <= ?) RETURNING id, pin_hash, tentativas", (aluno_id, agora)).fetchone()
    if r is None:
        b = con.execute("SELECT bloqueado_ate FROM alunos WHERE id = ?", (aluno_id,)).fetchone()
        if b and b[0] and b[0] > agora:
            return None, f"Muitas tentativas. Espere {int(b[0] - agora) + 1} segundos e tente de novo."
        pin_confere(pin, _hash_falso())  # mesmo tempo de resposta: não revela quais nomes existem
        return None, NAO_CONFERE
    if r["tentativas"] > TENTATIVAS:  # pedidos em paralelo já gastaram as tentativas desta janela
        return None, "Muitas tentativas. Espere 1 minuto e tente de novo."
    if pin_confere(pin, r["pin_hash"]):
        with con:
            con.execute("UPDATE alunos SET tentativas = 0, bloqueado_ate = NULL WHERE id = ?", (r["id"],))
        return r["id"], ""
    if r["tentativas"] >= TENTATIVAS:
        with con:
            con.execute("UPDATE alunos SET tentativas = 0, bloqueado_ate = ? WHERE id = ?", (agora + ESPERA_SEG, r["id"]))
        return None, (f"PIN errado {TENTATIVAS} vezes. Espere 1 minuto. Se esqueceu o PIN, peça um novo a quem organiza "
                      "a turma.")
    return None, NAO_CONFERE


# ---------------------------- Servidor da rede ----------------------------

def ip_local() -> str | None:
    """IP deste PC na rede local. Conectar UDP não envia nada: só escolhe a interface de saída."""
    for destino in ("192.168.0.1", "10.0.0.1", "8.8.8.8"):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect((destino, 80))
                ip = s.getsockname()[0]
                if not ip.startswith("127."):
                    return ip
        except OSError:
            continue
    try:
        return next(ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127."))
    except (OSError, StopIteration):
        return None


def _livre(porta: int) -> bool:
    with socket.socket() as s:
        try:
            s.bind(("0.0.0.0", porta))
            return True
        except OSError:
            return False


def porta() -> int | None:
    """Porta do servidor da turma, ou None se ela está fechada."""
    return _porta if _servidor and not _servidor.should_exit else None


def endereco() -> str | None:
    ip = ip_local()
    return f"http://{ip}:{_porta}" if ip and porta() else None


def abrir(app) -> int:
    global _servidor, _porta
    import uvicorn
    with _trava:
        if porta():
            return _porta
        p = next((x for x in PORTAS if _livre(x)), None)
        if p is None:
            raise OSError("nenhuma porta livre")
        # proxy_headers=False: ninguém na rede consegue se passar por outro endereço com cabeçalhos.
        _servidor = uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=p, log_level="warning", proxy_headers=False))
        _porta = p
        threading.Thread(target=_servidor.run, daemon=True, name="turma").start()
        for _ in range(50):  # espera até 5 s o servidor reservar a porta
            if _servidor.started:
                return p
            time.sleep(0.1)
        # Não subiu (outro programa pegou a porta entre a conferência e o uso): não diz que a turma está aberta.
        _servidor.should_exit = True
        _servidor = None
        raise OSError("o servidor da turma não subiu")


def fechar() -> None:
    global _servidor
    with _trava:
        if _servidor:
            _servidor.should_exit = True
            _servidor = None
