"""Rotas da API com banco temporário, sem dependência nova (Parte 1 das correções da revisão geral).

As rotas são funções comuns: chamadas direto com uma conexão do banco temporário. A proteção contra outros sites
(ADR 0026) passa por HTTP de verdade, com o uvicorn numa thread e urllib.
Importar app.main prepara o data/ do projeto (cria um vazio no CI); os testes não usam esse banco.
"""
import json
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from fastapi import HTTPException
from starlette.requests import Request

from app import db, main, turma

ANO, DIA = 2022, 2
QS = [db.id_questao(ANO, i, "") for i in (91, 92, 93)]


def banco_temporario(pasta: Path) -> None:
    con = db.conectar(pasta)
    db.criar_tabelas(con)
    with con:
        for qid, indice, gabarito in zip(QS, (91, 92, 93), "BCD"):
            con.execute("INSERT INTO questoes (id, ano, indice, area, gabarito) VALUES (?, ?, ?, 'ciencias-natureza', ?)",
                        (qid, ANO, indice, gabarito))
            con.executemany("INSERT INTO alternativas (questao_id, letra, texto) VALUES (?, ?, ?)",
                            [(qid, letra, f"alt {letra}") for letra in "ABCDE"])
        con.execute("INSERT INTO alunos (id, nome, pin_hash) VALUES (2, 'Ana', ?)", (turma.hash_pin("1234"),))
    con.close()


def status(funcao, *args, **kw) -> int:
    try:
        funcao(*args, **kw)
        return 200
    except HTTPException as e:
        return e.status_code


class TestApi(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pasta = Path(self.tmp.name)
        banco_temporario(self.pasta)
        self.con = db.abrir(self.pasta)

    def tearDown(self):
        self.con.close()
        self.tmp.cleanup()

    def simulado(self, aluno=1) -> int:
        return main.criar_simulado(self.con, aluno, main.NovoSimulado(ano=ANO, dia=DIA))["id"]

    def test_gabarito_nao_sai_antes_da_resposta(self):  # ADR 0003
        self.assertNotIn("gabarito", main.questao(self.con, QS[0]))
        s = main.abrir_simulado(self.con, 1, self.simulado())
        self.assertNotIn("resultado", s)
        self.assertNotIn("gabarito", json.dumps(s))
        self.assertNotIn("gabarito", json.dumps(main.listar_simulados(self.con, 1)))

    def test_entrega_do_simulado(self):
        sid = self.simulado()
        main.atualizar_simulado(self.con, 1, sid, main.AtualizaSimulado(respostas={QS[0]: "A", QS[1]: "C"}))
        main.atualizar_simulado(self.con, 1, sid, main.AtualizaSimulado(respostas={QS[0]: None}, marcadas=[QS[2], 999]))
        self.assertEqual(status(main.atualizar_simulado, self.con, 1, sid, main.AtualizaSimulado(respostas={999: "A"})), 422)
        s = main.entregar_simulado(self.con, 1, sid)
        area = s["resultado"]["areas"][0]
        self.assertEqual((area["acertos"], area["brancos"]), (1, 2))
        self.assertEqual(s["marcadas"], [QS[2]])
        self.assertEqual(status(main.entregar_simulado, self.con, 1, sid), 409)  # entregar de novo não duplica
        self.assertEqual(status(main.atualizar_simulado, self.con, 1, sid, main.AtualizaSimulado(tempo_seg=1)), 409)
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM respostas").fetchone()[0], 1)

    def test_entrega_simultanea_nao_duplica(self):
        sid = self.simulado()
        main.atualizar_simulado(self.con, 1, sid, main.AtualizaSimulado(respostas={QS[0]: "B"}))
        resultados = []

        def entregar():
            con = db.abrir(self.pasta)
            resultados.append(status(main.entregar_simulado, con, 1, sid))
            con.close()

        t = [threading.Thread(target=entregar) for _ in range(4)]
        [x.start() for x in t]
        [x.join() for x in t]
        self.assertEqual(sorted(resultados), [200, 409, 409, 409])
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM respostas").fetchone()[0], 1)

    def test_salvamentos_simultaneos_nao_apagam_respostas(self):
        sid = self.simulado()

        def responder(qid, letra):
            con = db.abrir(self.pasta)
            main.atualizar_simulado(con, 1, sid, main.AtualizaSimulado(respostas={qid: letra}))
            con.close()

        t = [threading.Thread(target=responder, args=(q, "A")) for q in QS]
        [x.start() for x in t]
        [x.join() for x in t]
        self.assertEqual(len(main.abrir_simulado(self.con, 1, sid)["respostas"]), 3)

    def test_aluno_nao_ve_dados_de_outro(self):
        sid = self.simulado(aluno=1)
        rid = main.criar_redacao(self.con, 1, main.NovaRedacao(tema="Tema do organizador"))["id"]
        main.salvar_rascunho(main.NovoRascunho(tracos=[]), self.con, 1, chave=f"s{sid}-{QS[0]}")
        for funcao, args in [
            (main.abrir_simulado, (sid,)), (main.entregar_simulado, (sid,)),
            (main.atualizar_simulado, (sid, main.AtualizaSimulado(tempo_seg=1))),
            (main.abrir_redacao, (rid,)), (main.apagar_redacao, (rid,)),
            (main.atualizar_redacao, (rid, main.AtualizaRedacao(texto="x"))),
        ]:
            self.assertEqual(status(funcao, self.con, 2, *args), 404, funcao.__name__)
        self.assertEqual(status(main.ler_rascunho, self.con, 2, chave=f"s{sid}-{QS[0]}"), 404)
        self.assertEqual(main.listar_simulados(self.con, 2), [])

    def test_toda_rota_tem_dono(self):
        """Rota nova precisa ser classificada: pública, do aluno (Aluno) ou só do organizador (Organizador)."""
        publicas = {"/api/guia", "/api/versao", "/api/versao/lembrete", "/api/filtros", "/api/questao/{qid}",
                    "/api/redacao/conteudo", "/api/turma/eu", "/api/turma/entrar", "/api/turma/cadastrar",
                    "/api/turma/sair", "/"}
        so_organizador = {"/api/guia/sincronizar", "/api/atualizar", "/api/preferencias", "/api/turma",
                          "/api/turma/abrir", "/api/turma/fechar", "/api/turma/meu-acesso",
                          "/api/turma/participantes/{pid}/pin", "/api/turma/participantes/{pid}"}

        def chamadas(d):
            for filho in d.dependencies:
                yield filho.call
                yield from chamadas(filho)

        for rota in main.app.routes:
            if not hasattr(rota, "dependant"):
                continue  # arquivos estáticos
            deps = set(chamadas(rota.dependant))
            if rota.path in so_organizador:
                self.assertIn(main.so_organizador, deps, rota.path)
            elif rota.path not in publicas:
                self.assertIn(main.aluno_atual, deps, f"{rota.path}: classifique a rota neste teste")

    def test_pela_turma_pela_porta_mesmo_com_a_turma_fechada(self):
        pedido = lambda porta: Request({"type": "http", "server": ("127.0.0.1", porta), "headers": []})
        self.assertIsNone(turma.porta())
        self.assertTrue(main.pela_turma(pedido(turma.PORTAS[0])))  # fechando: continua sendo da rede
        self.assertFalse(main.pela_turma(pedido(8765)))
        self.assertFalse(main.pela_turma(pedido(8000)))


class TestProtecaoWeb(unittest.TestCase):
    """ADR 0026: CSRF, DNS rebinding e clickjacking, por HTTP de verdade."""

    @classmethod
    def setUpClass(cls):
        import uvicorn
        cls.tmp = tempfile.TemporaryDirectory()
        pasta = Path(cls.tmp.name)
        banco_temporario(pasta)

        def banco():
            con = db.abrir(pasta)
            try:
                yield con
            finally:
                con.close()

        main.app.dependency_overrides[main.banco] = banco
        cls.servidor = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=8799, log_level="error"))
        threading.Thread(target=cls.servidor.run, daemon=True).start()
        for _ in range(100):
            if cls.servidor.started:
                break
            time.sleep(0.05)

    @classmethod
    def tearDownClass(cls):
        cls.servidor.should_exit = True
        main.app.dependency_overrides.clear()
        time.sleep(0.3)
        cls.tmp.cleanup()

    def pedir(self, metodo, caminho, corpo=None, **cabecalhos):
        r = urllib.request.Request(f"http://127.0.0.1:8799{caminho}", method=metodo,
                                   data=json.dumps(corpo).encode() if corpo is not None else None,
                                   headers={"Content-Type": "application/json", **cabecalhos})
        try:
            with urllib.request.urlopen(r) as x:
                return x.status, dict(x.headers)
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers)

    def test_dns_rebinding_recusado(self):
        self.assertEqual(self.pedir("GET", "/api/estatisticas", Host="ataque.exemplo:8799")[0], 400)
        self.assertEqual(self.pedir("GET", "/api/estatisticas", Host="localhost:8799")[0], 200)
        self.assertEqual(self.pedir("GET", "/api/estatisticas")[0], 200)

    def test_csrf_recusado(self):
        corpo = {"lembrete_versao": False}
        self.assertEqual(self.pedir("PUT", "/api/preferencias", corpo, Origin="https://ataque.exemplo")[0], 403)
        self.assertEqual(self.pedir("PUT", "/api/preferencias", corpo, **{"Sec-Fetch-Site": "cross-site"})[0], 403)
        self.assertEqual(self.pedir("PUT", "/api/preferencias", corpo, Origin="http://127.0.0.1:8799")[0], 200)

    def test_cabecalhos_de_seguranca(self):
        cod, cab = self.pedir("GET", "/")
        self.assertEqual(cod, 200)
        self.assertIn("frame-ancestors 'none'", cab["content-security-policy"])
        self.assertIn("script-src 'self' 'sha256-", cab["content-security-policy"])
        self.assertEqual(cab["x-frame-options"], "DENY")


if __name__ == "__main__":
    unittest.main()
