"""Testes das partes com regra: validação do guia baixado e área pela numeração oficial.

Rodar:  .venv\\Scripts\\python.exe -m unittest discover tests
"""
import json
import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path

from app import db, guia, plano, revisao, tri, versao
from app.redacao import notas_validas
from scripts.importar_enem_dev import area_oficial


class TestGuia(unittest.TestCase):
    def test_guia_embutido_e_valido(self):
        g = guia.ler(guia.EMBUTIDO.read_text(encoding="utf-8"))
        self.assertEqual(g["secoes"][0]["titulo"], "Regras de ouro")
        self.assertIn("Edital", g["edital"])

    def test_rejeita_arquivo_que_nao_e_guia(self):
        for texto in ("<html>erro 404</html>", "---\nversao: 2027.1\n---\n## A\nx",  # sem edital
                      "---\nversao: abc\nedital: E\n---\n## A\nx",  # versão não numérica
                      "---\nversao: 2027.1\nedital: E\n---\nsem seções"):
            with self.assertRaises(ValueError, msg=texto):
                guia.ler(texto)

    def test_versao_compara_numeros(self):
        self.assertGreater(guia.versao("2027.1"), guia.versao("2026.10"))
        self.assertGreater(guia.versao("2026.10"), guia.versao("2026.9"))  # não é comparação de texto


class TestNotasRedacao(unittest.TestCase):
    def test_aceita_niveis_oficiais(self):
        self.assertTrue(notas_validas({"c1": 0, "c2": 40, "c3": 120, "c4": 160, "c5": 200}))

    def test_recusa_notas_invalidas(self):
        cinco = {"c1": 200, "c2": 200, "c3": 200, "c4": 200}
        for notas in (cinco | {"c5": 999}, cinco | {"c5": 100}, cinco, cinco | {"c5": 200, "c6": 0},
                      cinco | {"c5": True}):
            self.assertFalse(notas_validas(notas), notas)


class TestTRI(unittest.TestCase):
    def test_reproduz_notas_oficiais(self):
        dados = json.loads((Path(__file__).parent / "dados" / "tri_2020_mt.json").read_text(encoding="utf-8"))
        k, s = dados["escala"]["k"], dados["escala"]["s"]
        for caso in dados["casos"]:
            calculada = tri.nota([tuple(i) for i in caso["itens"]], k, s)
            self.assertAlmostEqual(calculada, caso["nota_oficial"], delta=1.0)

    def test_mais_acertos_nao_diminui_a_nota(self):
        itens = [(1.5, b / 10, 0.2, False) for b in range(-20, 25)]
        n0 = tri.nota(itens, 500, 100)
        itens[0] = (*itens[0][:3], True)
        self.assertGreater(tri.nota(itens, 500, 100), n0)


class TestRevisao(unittest.TestCase):
    def test_ciclo_completo(self):
        p = revisao.proxima
        self.assertIsNone(p([("2026-11-01", True)]))  # nunca errou
        self.assertEqual(p([("2026-11-01", False)]), date(2026, 11, 2))
        h = [("2026-11-01", False), ("2026-11-02", True)]
        self.assertEqual(p(h), date(2026, 11, 5))  # +3
        h += [("2026-11-05", True)]
        self.assertEqual(p(h), date(2026, 11, 12))  # +7
        h += [("2026-11-12", True)]
        self.assertEqual(p(h), date(2026, 12, 3))  # +21
        h += [("2026-12-03", True)]
        self.assertIsNone(p(h))  # dominada

    def test_acerto_antes_da_data_nao_conta_e_erro_recomeca(self):
        p = revisao.proxima
        self.assertEqual(p([("2026-11-01", False), ("2026-11-01", True)]), date(2026, 11, 2))
        self.assertEqual(p([("2026-11-01", False), ("2026-11-02", True), ("2026-11-05", False)]), date(2026, 11, 6))


class TestPlano(unittest.TestCase):
    def test_area_mais_fraca_recebe_mais_blocos_e_soma_fecha(self):
        taxas = {"linguagens": 0.8, "ciencias-humanas": 0.7, "ciencias-natureza": 0.5, "matematica": 0.2}
        p = plano.montar(10, date(2027, 11, 7), date(2026, 11, 8), taxas)
        self.assertEqual(len(p["ciclo"]), 10)
        self.assertEqual(p["ciclo"].count("redacao"), 1)
        n = p["blocos_por_area"]
        self.assertGreater(n["matematica"], n["linguagens"])
        self.assertEqual(p["fase"]["nome"], "Base")

    def test_intercala_e_fases(self):
        p = plano.montar(5, date(2026, 11, 15), date(2026, 11, 8), {})
        areas = [a for a in p["ciclo"] if a != "redacao"]
        self.assertEqual(len(set(areas)), len(areas))  # 4 blocos, 4 áreas diferentes
        self.assertEqual(p["fase"]["nome"], "Semana da prova")
        self.assertEqual(plano.fase(20)["nome"], "Reta final")
        self.assertEqual(plano.fase(60)["nome"], "Simulados")


class TestMigracao(unittest.TestCase):
    """Formato antigo (enem.db único, ids sequenciais) -> questoes.db + aluno.db com ids fixos (ADR 0018)."""

    def montar_antigo(self, pasta: Path) -> None:
        velho = sqlite3.connect(pasta / "enem.db")
        velho.executescript("""
            CREATE TABLE questoes (id INTEGER PRIMARY KEY, ano INT, indice INT, area TEXT, idioma TEXT, gabarito TEXT);
            CREATE TABLE alternativas (questao_id INT, letra TEXT, texto TEXT);
            CREATE TABLE questoes_tri (questao_id INTEGER PRIMARY KEY, a REAL, b REAL, c REAL, anulada INT);
            CREATE TABLE alunos (id INTEGER PRIMARY KEY, nome TEXT);
            CREATE TABLE respostas (id INTEGER PRIMARY KEY, aluno_id INT, questao_id INT, alternativa TEXT,
                                    correta INT, tempo_seg INT, motivo_erro TEXT, criado_em TEXT);
            CREATE TABLE simulados (id INTEGER PRIMARY KEY, aluno_id INT, ano INT, dia INT, idioma TEXT,
                                    respostas TEXT, marcadas TEXT, tempo_seg INT, entregue INT, criado_em TEXT);
            INSERT INTO questoes VALUES (1, 2022, 175, 'matematica', '', 'B'), (2, 2022, 1, 'linguagens', 'ingles', 'A');
            INSERT INTO alternativas VALUES (1, 'B', 'certa'), (2, 'A', 'certa');
            INSERT INTO questoes_tri VALUES (1, 1.5, 0.2, 0.1, 0);
            INSERT INTO alunos VALUES (1, 'Eu');
            INSERT INTO respostas VALUES (7, 1, 1, 'C', 0, 30, 'atencao', '2026-11-01 10:00:00');
            INSERT INTO simulados VALUES (3, 1, 2022, 2, 'ingles', '{"1": "B"}', '[1, 2]', 100, 0, '2026-11-01');
        """)
        velho.commit()
        velho.close()

    def test_migra_progresso_e_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            pasta = Path(tmp)
            self.montar_antigo(pasta)
            db.migrar(pasta)
            self.assertFalse((pasta / "enem.db").exists())
            self.assertTrue((pasta / "enem-antes-da-migracao.db").exists())
            banco = sqlite3.connect(pasta / "questoes.db")
            self.assertEqual(sorted(r[0] for r in banco.execute("SELECT id FROM questoes")), [20220011, 20221750])
            self.assertEqual(banco.execute("SELECT questao_id FROM questoes_tri").fetchone()[0], 20221750)
            self.assertEqual(banco.execute("SELECT questao_id FROM alternativas WHERE letra = 'B'").fetchone()[0], 20221750)
            self.assertIsNone(banco.execute("SELECT name FROM sqlite_master WHERE name = 'respostas'").fetchone())
            banco.close()
            aluno = sqlite3.connect(pasta / "aluno.db")
            self.assertEqual(aluno.execute("SELECT questao_id, motivo_erro FROM respostas").fetchone(), (20221750, "atencao"))
            resp, marc = aluno.execute("SELECT respostas, marcadas FROM simulados").fetchone()
            self.assertEqual((json.loads(resp), json.loads(marc)), ({"20221750": "B"}, [20221750, 20220011]))
            aluno.close()

    def test_atualizacao_pelo_instalador_mantem_questoes_novas(self):
        with tempfile.TemporaryDirectory() as tmp:
            pasta = Path(tmp)
            self.montar_antigo(pasta)
            (pasta / "questoes.db").write_bytes(b"")  # o instalador já trouxe o banco novo
            db.migrar(pasta)
            self.assertEqual((pasta / "questoes.db").stat().st_size, 0)  # não foi substituído
            self.assertFalse((pasta / "enem.db").exists())
            aluno = sqlite3.connect(pasta / "aluno.db")
            self.assertEqual(aluno.execute("SELECT questao_id FROM respostas").fetchone()[0], 20221750)
            aluno.close()


class TestAtualizacao(unittest.TestCase):
    def test_so_aceita_instalador_do_repositorio_oficial_com_sha(self):
        base = "https://github.com/geniels/triunfo-enem/releases/download/v9.9.9/"
        def release(url_exe, com_sha=True):
            assets = [{"name": "TRIunfo-Estudante-9.9.9.exe", "browser_download_url": url_exe, "size": 1}]
            if com_sha:
                assets.append({"name": "TRIunfo-Estudante-9.9.9.exe.sha256", "browser_download_url": base + "x.sha256"})
            return {"assets": assets}
        self.assertIsNotNone(versao._instalador(release(base + "TRIunfo-Estudante-9.9.9.exe"), "9.9.9"))
        self.assertIsNone(versao._instalador(release("https://exemplo.com/TRIunfo.exe"), "9.9.9"))
        self.assertIsNone(versao._instalador(release(base + "TRIunfo-Estudante-9.9.9.exe", com_sha=False), "9.9.9"))


class TestAreaOficial(unittest.TestCase):
    def test_ordem_das_areas_mudou_em_2017(self):
        self.assertEqual(area_oficial(2016, 1, "x"), "ciencias-humanas")
        self.assertEqual(area_oficial(2016, 91, "x"), "linguagens")
        self.assertEqual(area_oficial(2017, 1, "x"), "linguagens")
        self.assertEqual(area_oficial(2017, 180, "x"), "matematica")
        self.assertEqual(area_oficial(2017, 181, "fonte"), "fonte")


if __name__ == "__main__":
    unittest.main()
