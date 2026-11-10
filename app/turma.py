"""Modo turma (ADR 0022): um PC (o do organizador) serve o TRIunfo na rede local enquanto a turma está aberta.

- O servidor normal continua só em 127.0.0.1, sem login: é o organizador no próprio PC (aluno 1).
- "Abrir turma" sobe um SEGUNDO servidor em 0.0.0.0. Tudo o que chega por ele exige nome + PIN de 4 dígitos.
- O PIN é guardado como hash (PBKDF2); o aparelho fica lembrado por um cookie assinado com HMAC.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import socket
import sqlite3
import threading
import time

PORTAS = range(8780, 8790)
TENTATIVAS = 5        # PINs errados seguidos antes de esperar
ESPERA_SEG = 60
COOKIE = "triunfo_turma"
ORGANIZADOR = 1       # o aluno "Eu" do PC do organizador

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
    r = con.execute("SELECT pin_hash FROM alunos WHERE id = ? AND id != ?", (aluno_id, ORGANIZADOR)).fetchone()
    if not r or not r[0] or not hmac.compare_digest(_assinatura(con, aluno_id, r[0]), assinatura):
        return None
    return aluno_id


def entrar(con: sqlite3.Connection, nome: str, pin: str) -> tuple[int | None, str]:
    """(id, "") se conferir; senão (None, mensagem para o aluno)."""
    r = con.execute("SELECT id, pin_hash, tentativas, bloqueado_ate FROM alunos WHERE nome = ? COLLATE NOCASE "
                    "AND id != ?", (nome.strip(), ORGANIZADOR)).fetchone()
    if not r:
        return None, "Não achamos esse nome na turma. Confira como você escreveu ou escolha \"Primeira vez\"."
    agora = time.time()
    if r["bloqueado_ate"] and r["bloqueado_ate"] > agora:
        falta = int(r["bloqueado_ate"] - agora) + 1
        return None, f"Muitas tentativas. Espere {falta} segundos e tente de novo."
    if pin_confere(pin, r["pin_hash"]):
        with con:
            con.execute("UPDATE alunos SET tentativas = 0, bloqueado_ate = NULL WHERE id = ?", (r["id"],))
        return r["id"], ""
    tentativas = r["tentativas"] + 1
    with con:
        if tentativas >= TENTATIVAS:
            con.execute("UPDATE alunos SET tentativas = 0, bloqueado_ate = ? WHERE id = ?", (agora + ESPERA_SEG, r["id"]))
        else:
            con.execute("UPDATE alunos SET tentativas = ? WHERE id = ?", (tentativas, r["id"]))
    if tentativas >= TENTATIVAS:
        return None, f"PIN errado {TENTATIVAS} vezes. Espere 1 minuto. Se esqueceu o PIN, peça um novo ao organizador da turma."
    return None, "PIN errado. Se esqueceu, peça um novo ao organizador da turma."


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
                break
            time.sleep(0.1)
        return p


def fechar() -> None:
    global _servidor
    with _trava:
        if _servidor:
            _servidor.should_exit = True
            _servidor = None
