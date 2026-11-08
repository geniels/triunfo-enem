"""Banco de dados local (SQLite). Um único arquivo em data/enem.db."""
from __future__ import annotations

import sqlite3
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATA_DIR = RAIZ / "data"
IMAGENS_DIR = DATA_DIR / "imagens"
DB_PATH = DATA_DIR / "enem.db"

AREAS = {
    "linguagens": "Linguagens, Códigos e suas Tecnologias",
    "ciencias-humanas": "Ciências Humanas e suas Tecnologias",
    "ciencias-natureza": "Ciências da Natureza e suas Tecnologias",
    "matematica": "Matemática e suas Tecnologias",
}

ESQUEMA = """
CREATE TABLE IF NOT EXISTS questoes (
    id          INTEGER PRIMARY KEY,
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
CREATE INDEX IF NOT EXISTS ix_questoes_area_ano ON questoes (area, ano);

CREATE TABLE IF NOT EXISTS alternativas (
    questao_id  INTEGER NOT NULL REFERENCES questoes(id) ON DELETE CASCADE,
    letra       TEXT    NOT NULL,
    texto       TEXT,
    arquivo     TEXT,
    PRIMARY KEY (questao_id, letra)
);

-- Preparado para o modo escola: cada aluno tem suas respostas.
CREATE TABLE IF NOT EXISTS alunos (
    id    INTEGER PRIMARY KEY,
    nome  TEXT NOT NULL
);
INSERT OR IGNORE INTO alunos (id, nome) VALUES (1, 'Eu');

CREATE TABLE IF NOT EXISTS respostas (
    id           INTEGER PRIMARY KEY,
    aluno_id     INTEGER NOT NULL DEFAULT 1 REFERENCES alunos(id),
    questao_id   INTEGER NOT NULL REFERENCES questoes(id),
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
"""


def conectar() -> sqlite3.Connection:
    DATA_DIR.mkdir(exist_ok=True)
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    return con


def criar_tabelas(con: sqlite3.Connection) -> None:
    con.executescript(ESQUEMA)
    con.commit()
