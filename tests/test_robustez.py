"""Parte 2 das correções da revisão geral: robustez (limites, nomes com acento, atualização, simulado sem questões,
lembrete, rascunho, remoção de participante, nota TRI, plano)."""
import io
import tempfile
import unittest
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from unittest import mock

from fastapi import HTTPException
from starlette.requests import Request

from app import db, main, plano, turma, versao
from tests.test_api import ANO, QS, banco_temporario, status


def pedido(porta=8765, ip="10.0.0.5"):
    return Request({"type": "http", "server": ("127.0.0.1", porta), "client": (ip, 5000), "headers": []})


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pasta = Path(self.tmp.name)
        banco_temporario(self.pasta)
        self.con = db.abrir(self.pasta)
        turma._cadastros.clear()

    def tearDown(self):
        self.con.close()
        self.tmp.cleanup()


class TestTurma(Base):
    def test_nome_com_acento_em_maiusculas(self):
        main.cadastrar_na_turma(main.Acesso(nome="JOÃO  Silva", pin="1357"), pedido(), main.Response(), self.con)
        self.assertIsNotNone(turma.entrar(self.con, "joão silva", "1357")[0])
        with self.assertRaises(HTTPException) as e:  # "João Silva" e "JOÃO SILVA" são a mesma pessoa
            main.cadastrar_na_turma(main.Acesso(nome="João Silva", pin="2468"), pedido(ip="10.0.0.6"), main.Response(), self.con)
        self.assertEqual(e.exception.status_code, 409)

    def test_limite_de_cadastros_por_aparelho(self):
        for n in range(turma.CADASTROS_POR_MINUTO):
            main.cadastrar_na_turma(main.Acesso(nome=f"Pessoa {n}", pin="1357"), pedido(), main.Response(), self.con)
        with self.assertRaises(HTTPException) as e:
            main.cadastrar_na_turma(main.Acesso(nome="Mais uma", pin="1357"), pedido(), main.Response(), self.con)
        self.assertEqual(e.exception.status_code, 429)
        main.cadastrar_na_turma(main.Acesso(nome="Outro aparelho", pin="1357"), pedido(ip="10.0.0.9"), main.Response(), self.con)

    def test_meu_acesso_nao_usa_nome_de_participante(self):
        self.assertEqual(status(main.definir_meu_acesso, main.Acesso(nome="ANA", pin="1111"), self.con), 409)
        main.definir_meu_acesso(main.Acesso(nome="Dono", pin="1111"), self.con)
        main.definir_meu_acesso(main.Acesso(nome="dono", pin="2222"), self.con)  # trocar o próprio PIN

    def test_remover_participante_apaga_so_os_dados_dele(self):
        sid_ana = main.criar_simulado(self.con, 2, main.NovoSimulado(ano=ANO, dia=2))["id"]
        sid_eu = main.criar_simulado(self.con, 1, main.NovoSimulado(ano=ANO, dia=2))["id"]
        for aluno, sid in ((2, sid_ana), (1, sid_eu)):
            main.responder(self.con, aluno, main.Resposta(questao_id=QS[0], alternativa="A"))
            main.criar_redacao(self.con, aluno, main.NovaRedacao(tema="Tema qualquer"))
            main.configurar_plano(self.con, aluno, main.ConfigPlano(data_prova=date(2027, 11, 7), horas_semana=10))
            main.marcar_bloco(self.con, aluno, main.BlocoFeito(posicao=0, feito=True))
            main.salvar_rascunho(main.NovoRascunho(tracos=[main.Traco(tipo="caneta", pontos=[(0.1, 0.1)])]), self.con,
                                 aluno, chave=f"s{sid}-{QS[0]}")
        main.remover_participante(2, self.con)
        for tabela in ("respostas", "redacoes", "plano", "plano_feitos", "simulados", "rascunhos"):
            por_aluno = dict(self.con.execute(f"SELECT aluno_id, COUNT(*) FROM {tabela} GROUP BY aluno_id"))
            self.assertEqual((por_aluno.get(2), por_aluno.get(1)), (None, 1), tabela)
        self.assertEqual(status(main.remover_participante, 1, self.con), 404)  # o dono do PC não é removível


class TestProxima(Base):
    def test_lista_de_vistas_grande_e_modos(self):
        sortear = lambda **kw: main.proxima(main.PedidoProxima(**kw), self.con, 1)
        self.assertEqual(sortear(modo="todas", excluir=list(range(9000)) + QS[:2])["id"], QS[2])  # antes ia na URL
        main.responder(self.con, 1, main.Resposta(questao_id=QS[0], alternativa="A"))  # gabarito B: erro
        self.assertNotIn(QS[0], {sortear(modo="novas")["id"] for _ in range(20)})
        r = sortear(modo="erros")
        self.assertEqual((r["id"], r["restantes"], r["questao"]["id"]), (QS[0], 1, QS[0]))  # a questão vem junto
        self.assertNotIn("gabarito", r["questao"])
        self.assertEqual(sortear(modo="todas", excluir=QS)["id"], None)


class TestSimuladoSemQuestoes(Base):
    def test_lista_nao_quebra_se_o_banco_novo_nao_tem_o_ano(self):
        with self.con:  # simulado entregue de um ano que o banco de questões atual não tem
            self.con.execute("INSERT INTO simulados (aluno_id, ano, dia, respostas, entregue) VALUES (1, 1999, 1, '{}', 1)")
        lista = main.listar_simulados(self.con, 1)
        self.assertEqual((lista[0]["total"], lista[0]["acertos"]), (0, 0))


class TestRascunho(Base):
    def test_vazio_apaga_e_grande_recusa(self):
        chave = f"q{QS[0]}"
        main.salvar_rascunho(main.NovoRascunho(tracos=[main.Traco(tipo="caneta", pontos=[(0.1, 0.2)])]), self.con, 1, chave=chave)
        self.assertEqual(len(main.ler_rascunho(self.con, 1, chave=chave)["tracos"]), 1)
        main.salvar_rascunho(main.NovoRascunho(tracos=[]), self.con, 1, chave=chave)
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM rascunhos").fetchone()[0], 0)
        grande = main.NovoRascunho(tracos=[main.Traco(tipo="caneta", pontos=[(0.123456, 0.654321)] * 20_000)] * 3)
        self.assertEqual(status(main.salvar_rascunho, grande, self.con, 1, chave=chave), 413)


class TestNotaTri(Base):
    def itens(self, n=10):
        return [{"id": QS[0] + i, "area": "matematica", "resposta": "A", "gabarito": "A"} for i in range(n)]

    def com_parametros(self, erro_medio, anuladas):
        with self.con:
            self.con.execute("INSERT INTO tri_escala VALUES (?, 'matematica', 500, 100, ?, 100)", (ANO, erro_medio))
            for i in range(10):
                self.con.execute("INSERT INTO questoes (id, ano, indice, area, gabarito) VALUES (?, ?, ?, 'matematica', 'A') "
                                 "ON CONFLICT DO NOTHING", (QS[0] + i, ANO, 140 + i))
                self.con.execute("INSERT INTO questoes_tri VALUES (?, 1.5, 0, 0.2, ?)", (QS[0] + i, int(i < anuladas)))

    def nota(self):
        areas = {"matematica": {}}
        main._nota_tri(self.con, ANO, areas, self.itens())
        return areas["matematica"]

    def test_sem_nota_se_a_escala_nao_conferiu(self):
        self.com_parametros(erro_medio=1.5, anuladas=0)
        self.assertNotIn("nota_tri", self.nota())

    def test_sem_nota_com_menos_de_90_por_cento_das_questoes(self):
        self.com_parametros(erro_medio=0.2, anuladas=2)
        self.assertNotIn("nota_tri", self.nota())

    def test_com_nota_quando_pode(self):
        self.com_parametros(erro_medio=0.2, anuladas=1)
        a = self.nota()
        self.assertEqual(a["tri_questoes"], 9)
        self.assertGreater(a["nota_tri"], 500)


class TestLembreteEVersao(Base):
    def test_consulta_uma_vez_por_dia_e_espera_6h_sem_internet(self):
        chamadas = []
        relogio = [1_000_000.0]
        with mock.patch.object(versao, "verificar", lambda: chamadas.append(1) or {"atual": "0.5.3", "nova": None}), \
                mock.patch.object(main.time, "time", lambda: relogio[0]):
            main.lembrete_versao(pedido(), self.con)
            main.lembrete_versao(pedido(), self.con)
            self.assertEqual(len(chamadas), 1)
            relogio[0] += main.UM_DIA + 1
            main.lembrete_versao(pedido(), self.con)
            self.assertEqual(len(chamadas), 2)
        with mock.patch.object(versao, "verificar", mock.Mock(side_effect=OSError)) as sem_internet, \
                mock.patch.object(main.time, "time", lambda: relogio[0]):
            relogio[0] += main.UM_DIA + 1
            main.lembrete_versao(pedido(), self.con)
            relogio[0] += 5 * 3600
            main.lembrete_versao(pedido(), self.con)  # antes de 6 h: não tenta de novo
            self.assertEqual(sem_internet.call_count, 1)
            relogio[0] += 2 * 3600
            main.lembrete_versao(pedido(), self.con)
            self.assertEqual(sem_internet.call_count, 2)

    def test_pela_rede_nao_consulta_o_github(self):
        with mock.patch.object(versao, "verificar", mock.Mock(side_effect=AssertionError("não devia consultar"))):
            self.assertEqual(main.lembrete_versao(pedido(turma.PORTAS[0]), self.con), {"nova": None})
            self.assertEqual(main.verificar_versao(pedido(turma.PORTAS[0]), verificar=True), {"atual": versao.VERSAO})


class TestBaixarInstalador(unittest.TestCase):
    """O SHA-256 é a única defesa contra um instalador corrompido no caminho."""
    CONTEUDO = b"instalador de mentira"

    def baixar(self, sha_texto: bytes, conteudo: bytes = CONTEUDO):
        url = versao.DOWNLOADS + "v9.9.9/"
        dados = {"tag_name": "v9.9.9", "assets": [
            {"name": "TRIunfo-Estudante-9.9.9.exe", "browser_download_url": url + "a.exe", "size": len(conteudo)},
            {"name": "TRIunfo-Estudante-9.9.9.exe.sha256", "browser_download_url": url + "a.sha256", "size": 1}]}

        @contextmanager
        def falso(u, timeout=10):
            yield io.BytesIO(sha_texto if u.endswith(".sha256") else conteudo)

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        with mock.patch.object(versao, "_ultima", lambda: dados), mock.patch.object(versao, "_baixar", falso), \
                mock.patch.object(versao, "DATA_DIR", Path(tmp.name)):
            try:
                return versao.baixar_instalador()
            finally:
                self.sobrou = list(Path(tmp.name).rglob("*.exe"))

    def test_sha_certo(self):
        import hashlib
        sha = hashlib.sha256(self.CONTEUDO).hexdigest().encode()
        self.assertTrue(self.baixar(sha + b"  TRIunfo-Estudante-9.9.9.exe\n").name.endswith(".exe"))

    def test_sha_errado_apaga_o_arquivo(self):
        with self.assertRaises(ValueError):
            self.baixar(b"0" * 64)
        self.assertEqual(self.sobrou, [])

    def test_sha_vazio_vira_erro_tratado(self):  # antes: IndexError -> erro 500
        with self.assertRaises(ValueError):
            self.baixar(b"")


class TestDesempenho(Base):
    """Parte 3: o resultado do simulado é calculado uma vez; a revisão só olha questões com erro."""

    def test_resultado_guardado_na_entrega_e_lista_sem_recalcular(self):
        sid = main.criar_simulado(self.con, 1, main.NovoSimulado(ano=ANO, dia=2))["id"]
        main.atualizar_simulado(self.con, 1, sid, main.AtualizaSimulado(respostas={QS[0]: "B"}))
        main.entregar_simulado(self.con, 1, sid)
        with mock.patch.object(main, "_resultado", mock.Mock(side_effect=AssertionError("recalculou"))):
            self.assertEqual(main.listar_simulados(self.con, 1)[0]["acertos"], 1)
            self.assertEqual(main.abrir_simulado(self.con, 1, sid)["resultado"]["areas"][0]["acertos"], 1)

    def test_simulado_entregue_antes_da_versao_guarda_na_primeira_abertura(self):
        sid = main.criar_simulado(self.con, 1, main.NovoSimulado(ano=ANO, dia=2))["id"]
        with self.con:
            self.con.execute("UPDATE simulados SET entregue = 1 WHERE id = ?", (sid,))  # sem resultado guardado
        main.abrir_simulado(self.con, 1, sid)
        self.assertIsNotNone(self.con.execute("SELECT resultado FROM simulados WHERE id = ?", (sid,)).fetchone()[0])

    def test_revisao_so_com_questoes_que_tiveram_erro(self):
        with self.con:
            self.con.executemany("INSERT INTO respostas (aluno_id, questao_id, alternativa, correta, criado_em) "
                                 "VALUES (1, ?, 'A', ?, '2020-01-01 10:00:00')", [(QS[0], 0), (QS[1], 1)])
        self.assertEqual(main._revisoes(self.con, 1)["hoje"], [QS[0]])


class TestImagens(unittest.TestCase):
    def test_dimensoes_dos_formatos(self):
        import struct
        from app import imagens
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        pasta = Path(tmp.name)
        nulo = bytes(1)
        png = bytes([0x89]) + b"PNG" + bytes(12) + struct.pack(">II", 640, 480)
        (pasta / "a.png").write_bytes(png + nulo * 8)
        (pasta / "b.gif").write_bytes(b"GIF89a" + struct.pack("<HH", 30, 20) + nulo * 20)
        (pasta / "c.bmp").write_bytes(b"BM" + nulo * 16 + struct.pack("<ii", 50, -40) + nulo * 10)
        app0 = bytes([0xFF, 0xE0]) + struct.pack(">H", 4) + nulo * 2
        sof = bytes([0xFF, 0xC0]) + struct.pack(">HBHH", 11, 8, 300, 200)
        (pasta / "d.jpg").write_bytes(bytes([0xFF, 0xD8]) + app0 + sof + nulo * 8)
        imagens.dimensoes.cache_clear()
        self.addCleanup(imagens.dimensoes.cache_clear)
        with mock.patch.object(imagens, "IMAGENS_DIR", pasta):
            texto = "![](/imagens/a.png) ![](/imagens/b.gif) ![](/imagens/c.bmp) ![](/imagens/d.jpg) ![](/imagens/nao.png)"
            self.assertEqual(imagens.da_questao(texto), {"/imagens/a.png": [640, 480], "/imagens/b.gif": [30, 20],
                                                         "/imagens/c.bmp": [50, 40], "/imagens/d.jpg": [200, 300]})


class TestPlanoLimites(unittest.TestCase):
    def test_limites_de_horas(self):
        for horas, blocos in ((1, 2), (60, 60)):
            p = plano.montar(horas, date(2027, 11, 7), date(2026, 11, 8), {})
            self.assertEqual(len(p["ciclo"]), blocos)

    def test_prova_que_ja_passou(self):
        p = plano.montar(10, date(2026, 11, 8), date(2026, 11, 20), {})
        self.assertEqual(p["fase"]["nome"], "Depois da prova")


if __name__ == "__main__":
    unittest.main()
