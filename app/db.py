"""Bancos locais (SQLite), ADR 0018:

- data/questoes.db: conteúdo (questões, alternativas, parâmetros TRI). Pode ser trocado a cada versão.
- data/aluno.db:    progresso do aluno (respostas, redações, simulados, plano). Nunca é substituído.

O app abre o aluno.db e anexa o questoes.db como "banco": as consultas usam os nomes das tabelas sem prefixo.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATA_DIR = RAIZ / "data"
IMAGENS_DIR = DATA_DIR / "imagens"

AREAS = {
    "linguagens": "Linguagens, Códigos e suas Tecnologias",
    "ciencias-humanas": "Ciências Humanas e suas Tecnologias",
    "ciencias-natureza": "Ciências da Natureza e suas Tecnologias",
    "matematica": "Matemática e suas Tecnologias",
}
IDIOMAS = {"": 0, "ingles": 1, "espanhol": 2}


def id_questao(ano: int, indice: int, idioma: str) -> int:
    """Número fixo da questão (ex.: ENEM 2022, questão 175, sem idioma -> 20221750). Igual em qualquer instalação,
    para o progresso do aluno continuar valendo quando o banco de questões for trocado."""
    return ano * 10000 + indice * 10 + IDIOMAS[idioma]


ESQUEMA_BANCO = """
CREATE TABLE IF NOT EXISTS banco.questoes (
    id          INTEGER PRIMARY KEY,           -- id_questao(ano, indice, idioma)
    ano         INTEGER NOT NULL,
    indice      INTEGER NOT NULL,
    area        TEXT    NOT NULL,
    idioma      TEXT    NOT NULL DEFAULT '',   -- 'ingles' / 'espanhol' / '' (todas)
    titulo      TEXT,
    contexto    TEXT,                          -- Markdown
    introducao  TEXT,                          -- enunciado (Markdown)
    arquivos    TEXT    NOT NULL DEFAULT '[]', -- JSON: imagens extras
    gabarito    TEXT,
    fonte       TEXT,
    UNIQUE (ano, indice, idioma)
);
CREATE INDEX IF NOT EXISTS banco.ix_questoes_area_ano ON questoes (area, ano);

CREATE TABLE IF NOT EXISTS banco.alternativas (
    questao_id  INTEGER NOT NULL REFERENCES questoes(id) ON DELETE CASCADE,
    letra       TEXT    NOT NULL,
    texto       TEXT,
    arquivo     TEXT,
    PRIMARY KEY (questao_id, letra)
);

-- Parâmetros TRI oficiais de cada questão (microdados do INEP) e escala de cada área/ano (ADR 0014).
CREATE TABLE IF NOT EXISTS banco.questoes_tri (
    questao_id  INTEGER PRIMARY KEY REFERENCES questoes(id) ON DELETE CASCADE,
    a REAL NOT NULL, b REAL NOT NULL, c REAL NOT NULL,
    anulada     INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS banco.tri_escala (
    ano INTEGER NOT NULL, area TEXT NOT NULL,
    k REAL NOT NULL, s REAL NOT NULL,          -- nota = k + s * theta
    erro_medio REAL NOT NULL, amostra INTEGER NOT NULL,  -- conferência contra notas oficiais
    PRIMARY KEY (ano, area)
);
"""

# Sem chave estrangeira para "questoes": ela mora em outro arquivo (o SQLite não liga bancos diferentes).
ESQUEMA_ALUNO = """
-- Cada aluno tem seu progresso. O 1 ("Eu") é quem usa o próprio PC; os outros entram pelo modo turma (ADR 0022).
CREATE TABLE IF NOT EXISTS alunos (
    id    INTEGER PRIMARY KEY,
    nome  TEXT NOT NULL
);
INSERT OR IGNORE INTO alunos (id, nome) VALUES (1, 'Eu');

CREATE TABLE IF NOT EXISTS config (
    chave  TEXT PRIMARY KEY,
    valor  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS respostas (
    id           INTEGER PRIMARY KEY,
    aluno_id     INTEGER NOT NULL DEFAULT 1 REFERENCES alunos(id),
    questao_id   INTEGER NOT NULL,
    alternativa  TEXT    NOT NULL,
    correta      INTEGER NOT NULL,
    tempo_seg    INTEGER,
    motivo_erro  TEXT,      -- 'conteudo' | 'atencao' | 'tempo' | 'chute'
    criado_em    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS ix_respostas_aluno_questao ON respostas (aluno_id, questao_id);

CREATE TABLE IF NOT EXISTS redacoes (
    id             INTEGER PRIMARY KEY,
    aluno_id       INTEGER NOT NULL DEFAULT 1 REFERENCES alunos(id),
    tema           TEXT    NOT NULL,
    texto          TEXT    NOT NULL DEFAULT '',
    tempo_seg      INTEGER NOT NULL DEFAULT 0,
    entregue       INTEGER NOT NULL DEFAULT 0,
    notas          TEXT,    -- JSON {"c1": 0..200, ..., "c5": ...}, autoavaliação
    criado_em      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    atualizado_em  TEXT
);

-- Plano de estudos (ADR 0016): configuração e blocos do ciclo marcados como feitos em cada semana.
CREATE TABLE IF NOT EXISTS plano (
    aluno_id      INTEGER PRIMARY KEY REFERENCES alunos(id),
    data_prova    TEXT    NOT NULL,
    horas_semana  INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS plano_feitos (
    aluno_id  INTEGER NOT NULL REFERENCES alunos(id),
    semana    TEXT    NOT NULL,   -- semana ISO, ex.: 2026-W45
    posicao   INTEGER NOT NULL,   -- posição do bloco no ciclo
    PRIMARY KEY (aluno_id, semana, posicao)
);

-- Simulado de um dia de prova de um ano, na ordem oficial (ADR 0013).
CREATE TABLE IF NOT EXISTS simulados (
    id          INTEGER PRIMARY KEY,
    aluno_id    INTEGER NOT NULL DEFAULT 1 REFERENCES alunos(id),
    ano         INTEGER NOT NULL,
    dia         INTEGER NOT NULL CHECK (dia IN (1, 2)),
    idioma      TEXT    NOT NULL DEFAULT 'ingles',
    respostas   TEXT    NOT NULL DEFAULT '{}',  -- JSON {questao_id: "A".."E"}
    marcadas    TEXT    NOT NULL DEFAULT '[]',  -- JSON [questao_id] para revisar (2ª passada)
    tempo_seg   INTEGER NOT NULL DEFAULT 0,
    entregue    INTEGER NOT NULL DEFAULT 0,
    criado_em   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- Rascunho com caneta (ADR 0023): traços por questão. chave = "q<questão>" na prática ou "s<simulado>-<questão>".
CREATE TABLE IF NOT EXISTS rascunhos (
    aluno_id       INTEGER NOT NULL REFERENCES alunos(id),
    chave          TEXT    NOT NULL,
    tracos         TEXT    NOT NULL,   -- JSON [{tipo, pressao, pontos: [[x, y], ...]}], coordenadas / largura
    atualizado_em  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    PRIMARY KEY (aluno_id, chave)
);
"""
TABELAS_ALUNO = ["alunos", "config", "respostas", "redacoes", "plano", "plano_feitos", "simulados", "rascunhos"]


def abrir(pasta: Path = DATA_DIR) -> sqlite3.Connection:
    """Conexão nova com o banco de questões anexado. O servidor abre uma por requisição: conexões
    compartilhadas entre threads misturariam as transações de alunos diferentes (modo escola)."""
    # check_same_thread=False: o FastAPI pode abrir, usar e fechar a conexão em threads diferentes do pool,
    # mas nunca ao mesmo tempo. timeout: espera o outro aluno terminar de gravar em vez de dar erro.
    con = sqlite3.connect(pasta / "aluno.db", check_same_thread=False, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("ATTACH DATABASE ? AS banco", (str(pasta / "questoes.db"),))
    con.execute("PRAGMA foreign_keys = ON")
    return con


def conectar(pasta: Path = DATA_DIR) -> sqlite3.Connection:
    """Prepara a pasta (migração e modo de diário) e abre uma conexão. Usar uma vez, ao iniciar."""
    pasta.mkdir(exist_ok=True)
    migrar(pasta)
    con = abrir(pasta)
    con.execute("PRAGMA main.journal_mode = WAL")  # fica gravado no arquivo; vale para as conexões seguintes
    # O banco de questões não usa WAL: o instalador troca o arquivo, e um -wal antigo ao lado o corromperia.
    con.execute("PRAGMA banco.journal_mode = DELETE")
    return con


# Colunas acrescentadas depois da criação da tabela: bancos antigos as ganham ao abrir.
COLUNAS_NOVAS = {
    "alunos": {
        "pin_hash": "TEXT",                                   # PBKDF2 "sal$hash"; NULL para o organizador
        "tentativas": "INTEGER NOT NULL DEFAULT 0",           # PINs errados seguidos
        "bloqueado_ate": "REAL",                              # time.time() até quando espera
        "criado_em": "TEXT",
    },
}


def criar_tabelas(con: sqlite3.Connection) -> None:
    con.executescript(ESQUEMA_BANCO + ESQUEMA_ALUNO)
    for tabela, colunas in COLUNAS_NOVAS.items():
        existentes = {c[1] for c in con.execute(f"PRAGMA main.table_info({tabela})")}
        for nome, tipo in colunas.items():
            if nome not in existentes:
                con.execute(f"ALTER TABLE {tabela} ADD COLUMN {nome} {tipo}")
    con.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_alunos_nome ON alunos (nome COLLATE NOCASE)")
    con.commit()


def _inteiro(v) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def migrar(pasta: Path) -> None:
    """Converte o formato antigo (um só data/enem.db, ids sequenciais) para questoes.db + aluno.db (ids fixos).

    Casos: instalação de desenvolvimento (só enem.db) e atualização pelo instalador (enem.db antigo com o
    progresso + questoes.db novo). Antes de mexer, guarda uma cópia do enem.db.

    Pode ser interrompida em qualquer ponto (falta de luz, erro): o aluno.db é montado num arquivo temporário e só
    ganha o nome final quando tudo deu certo; na próxima abertura, recomeça da cópia original."""
    antigo, aluno_db, copia = pasta / "enem.db", pasta / "aluno.db", pasta / "enem-antes-da-migracao.db"
    if aluno_db.exists():
        # Parou entre os dois últimos passos: o progresso já foi para o aluno.db, falta o banco de questões.
        if antigo.exists() and not (pasta / "questoes.db").exists():
            antigo.rename(pasta / "questoes.db")
        return
    if not antigo.exists():
        return
    if copia.exists():
        shutil.copy2(copia, antigo)  # tentativa anterior interrompida: recomeça do original
    else:
        shutil.copy2(antigo, copia)
    temporario = pasta / "aluno.db.migrando"
    temporario.unlink(missing_ok=True)

    velho = sqlite3.connect(antigo)
    aluno = sqlite3.connect(temporario)
    try:
        novo_id = {
            qid: id_questao(ano, indice, idioma)
            for qid, ano, indice, idioma in velho.execute("SELECT id, ano, indice, idioma FROM questoes")
        }
        converter = lambda v: novo_id.get(_inteiro(v), _inteiro(v))  # noqa: E731

        # 1. Progresso do aluno -> aluno.db, com os ids das questões convertidos.
        aluno.executescript(ESQUEMA_ALUNO)
        existentes = {r[0] for r in velho.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        for tabela in (t for t in TABELAS_ALUNO if t in existentes):
            colunas = [c[1] for c in velho.execute(f"PRAGMA table_info({tabela})")]
            for linha in velho.execute(f"SELECT {', '.join(colunas)} FROM {tabela}"):
                r = dict(zip(colunas, linha))
                if tabela == "respostas":
                    r["questao_id"] = converter(r["questao_id"])
                if tabela == "simulados":  # chaves inválidas (dado corrompido) são ignoradas, sem travar
                    respostas = json.loads(r["respostas"] or "{}")
                    r["respostas"] = json.dumps({str(converter(k)): v for k, v in respostas.items() if _inteiro(k) is not None})
                    r["marcadas"] = json.dumps([converter(q) for q in json.loads(r["marcadas"] or "[]") if _inteiro(q) is not None])
                aluno.execute(f"INSERT OR REPLACE INTO {tabela} ({', '.join(r)}) VALUES ({', '.join('?' * len(r))})",
                              list(r.values()))
        aluno.commit()
        aluno.close()

        # 2. O que sobra do enem.db vira o questoes.db (se o instalador ainda não trouxe um novo).
        if not (pasta / "questoes.db").exists():
            velho.execute("PRAGMA foreign_keys = OFF")
            velho.execute("CREATE TEMP TABLE mapa (velho INTEGER PRIMARY KEY, novo INTEGER)")
            velho.executemany("INSERT INTO mapa VALUES (?, ?)", novo_id.items())
            for tabela, coluna in (("alternativas", "questao_id"), ("questoes_tri", "questao_id"), ("questoes", "id")):
                if tabela in existentes:
                    velho.execute(f"UPDATE {tabela} SET {coluna} = (SELECT novo FROM mapa WHERE velho = {coluna})")
            for tabela in (t for t in TABELAS_ALUNO if t in existentes):
                velho.execute(f"DROP TABLE {tabela}")
            velho.commit()
            velho.execute("PRAGMA journal_mode = DELETE")
            velho.execute("VACUUM")
    finally:
        velho.close()
        aluno.close()

    # 3. Por último: o aluno.db só passa a existir quando tudo deu certo.
    temporario.rename(aluno_db)
    if (pasta / "questoes.db").exists():
        antigo.unlink()
    else:
        antigo.rename(pasta / "questoes.db")
    for resto in ("enem.db-wal", "enem.db-shm"):
        (pasta / resto).unlink(missing_ok=True)
