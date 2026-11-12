"""Modo turma (ADR 0022): PIN, cookie assinado e espera depois de PINs errados."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app import db, turma


class TestTurma(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        pasta = self.pasta = Path(self.tmp.name)
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
        self.assertIsNone(turma.aluno_do_cookie(self.con, "1." + valor.split(".", 1)[1]))  # outro id
        self.assertIsNone(turma.aluno_do_cookie(self.con, "lixo"))
        self.assertIsNone(turma.aluno_do_cookie(self.con, valor.split(".")[0] + "." + valor.split(".", 1)[1]
                                                .replace(valor.split(".")[1], str(int(valor.split(".")[1]) + 1), 1)))  # outra data

    def test_cookie_vence(self):
        import time
        velho = turma.cookie_para(self.con, self.ana, agora=time.time() - turma.VALIDADE_SEG - 60)
        self.assertIsNone(turma.aluno_do_cookie(self.con, velho))
        quase = turma.cookie_para(self.con, self.ana, agora=time.time() - turma.VALIDADE_SEG + 3600)
        self.assertEqual(turma.aluno_do_cookie(self.con, quase), self.ana)

    def test_sair_invalida_o_cookie_no_servidor(self):
        """Antes, "Sair" só apagava o cookie daquele navegador: uma cópia continuava entrando."""
        copia = turma.cookie_para(self.con, self.ana)
        turma.encerrar_sessao(self.con, self.ana)
        self.assertIsNone(turma.aluno_do_cookie(self.con, copia))
        self.assertEqual(turma.aluno_do_cookie(self.con, turma.cookie_para(self.con, self.ana)), self.ana)

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


    def test_tentativas_em_paralelo_nao_furam_o_limite(self):
        """Antes, pedidos simultâneos liam tentativas=0 juntos e testavam dezenas de PINs por minuto."""
        import threading
        conferidos = []
        original = turma.pin_confere

        def contar(pin, guardado):
            if guardado != turma._hash_falso():
                conferidos.append(pin)
            return original(pin, guardado)

        turma.pin_confere = contar
        try:
            def tentar(pin):
                con = db.abrir(self.pasta)
                turma.entrar(con, "Ana", pin)
                con.close()

            t = [threading.Thread(target=tentar, args=(f"{n:04d}",)) for n in range(5000, 5030)]
            [x.start() for x in t]
            [x.join() for x in t]
        finally:
            turma.pin_confere = original
        self.assertLessEqual(len(conferidos), turma.TENTATIVAS)

    def test_mesma_resposta_para_nome_inexistente_e_pin_errado(self):
        self.assertEqual(turma.entrar(self.con, "Ninguém", "1234")[1], turma.entrar(self.con, "Ana", "0000")[1])


class TestEnderecos(unittest.TestCase):
    def test_lista_so_ips_privados_sem_repetir(self):
        from unittest import mock
        nomes = ("pc", [], ["192.168.1.7", "127.0.0.1", "169.254.10.2", "172.20.5.1", "8.8.4.4", "10.8.0.3", "192.168.1.7"])
        with (mock.patch.object(turma.socket, "socket", side_effect=OSError),
              mock.patch.object(turma.socket, "gethostbyname_ex", return_value=nomes)):
            self.assertEqual(turma.ips_locais(), ["192.168.1.7", "172.20.5.1", "10.8.0.3"])

if __name__ == "__main__":
    unittest.main()
