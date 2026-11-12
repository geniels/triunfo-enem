"""Modo turma (ADR 0022): PIN, cookie assinado e espera depois de PINs errados."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app import db, turma


class TestTurma(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        pasta = Path(self.tmp.name)
        sqlite3.connect(pasta / "questoes.db").close()
        self.con = db.conectar(pasta)
        db.criar_tabelas(self.con)
        with self.con:
            self.ana = self.con.execute("INSERT INTO alunos (nome, pin_hash) VALUES ('Ana', ?) RETURNING id",
                                        (turma.hash_pin("1234"),)).fetchone()[0]

    def tearDown(self):
        self.con.close()
        self.tmp.cleanup()

    def test_pin_guardado_como_hash(self):
        guardado = self.con.execute("SELECT pin_hash FROM alunos WHERE id = ?", (self.ana,)).fetchone()[0]
        self.assertNotIn("1234", guardado)
        self.assertTrue(turma.pin_confere("1234", guardado))
        self.assertFalse(turma.pin_confere("1235", guardado))

    def test_entrar_ignora_maiusculas(self):
        self.assertEqual(turma.entrar(self.con, "  ana ", "1234"), (self.ana, ""))

    def test_nome_repetido_e_recusado(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.con.execute("INSERT INTO alunos (nome) VALUES ('ANA')")

    def test_cookie(self):
        valor = turma.cookie_para(self.con, self.ana)
        self.assertEqual(turma.aluno_do_cookie(self.con, valor), self.ana)
        self.assertIsNone(turma.aluno_do_cookie(self.con, valor[:-1] + "0" if valor[-1] != "0" else valor[:-1] + "1"))
        self.assertIsNone(turma.aluno_do_cookie(self.con, "1." + valor.split(".")[1]))  # outro id
        self.assertIsNone(turma.aluno_do_cookie(self.con, "lixo"))

    def test_pin_novo_invalida_aparelho_lembrado(self):
        valor = turma.cookie_para(self.con, self.ana)
        with self.con:
            self.con.execute("UPDATE alunos SET pin_hash = ? WHERE id = ?", (turma.hash_pin("9999"), self.ana))
        self.assertIsNone(turma.aluno_do_cookie(self.con, valor))

    def test_dono_do_pc_so_entra_pela_rede_depois_de_criar_o_pin(self):
        self.assertIsNone(turma.entrar(self.con, "Eu", "0000")[0])
        self.assertIsNone(turma.aluno_do_cookie(self.con, "1.qualquer"))
        with self.con:  # o que PUT /api/turma/meu-acesso faz
            self.con.execute("UPDATE alunos SET nome = 'Geni', pin_hash = ? WHERE id = 1", (turma.hash_pin("2468"),))
        self.assertEqual(turma.entrar(self.con, "geni", "2468"), (turma.ORGANIZADOR, ""))
        valor = turma.cookie_para(self.con, turma.ORGANIZADOR)
        self.assertEqual(turma.aluno_do_cookie(self.con, valor), turma.ORGANIZADOR)

    def test_espera_depois_de_pins_errados(self):
        for _ in range(turma.TENTATIVAS):
            aluno, _ = turma.entrar(self.con, "Ana", "0000")
            self.assertIsNone(aluno)
        aluno, msg = turma.entrar(self.con, "Ana", "1234")  # até o PIN certo espera
        self.assertIsNone(aluno)
        self.assertIn("Espere", msg)
        with self.con:
            self.con.execute("UPDATE alunos SET bloqueado_ate = 0")
        self.assertEqual(turma.entrar(self.con, "Ana", "1234")[0], self.ana)


if __name__ == "__main__":
    unittest.main()
