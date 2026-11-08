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

-- Parâmetros TRI oficiais de cada questão (microdados do INEP) e escala de cada área/ano (ADR 0014).
CREATE TABLE IF NOT EXISTS questoes_tri (
    questao_id  INTEGER PRIMARY KEY REFERENCES questoes(id) ON DELETE CASCADE,
    a REAL NOT NULL, b REAL NOT NULL, c REAL NOT NULL,
    anulada     INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS tri_escala (
    ano INTEGER NOT NULL, area TEXT NOT NULL,
    k REAL NOT NULL, s REAL NOT NULL,          -- nota = k + s * theta
    erro_medio REAL NOT NULL, amostra INTEGER NOT NULL,  -- conferência contra notas oficiais
    PRIMARY KEY (ano, area)
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
