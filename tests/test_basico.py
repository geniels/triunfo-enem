"""Testes das partes com regra: validação do guia baixado e área pela numeração oficial.

Rodar:  .venv\\Scripts\\python.exe -m unittest discover tests
"""
import json
import unittest
from datetime import date
from pathlib import Path

from app import guia, revisao, tri
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


class TestAreaOficial(unittest.TestCase):
    def test_ordem_das_areas_mudou_em_2017(self):
        self.assertEqual(area_oficial(2016, 1, "x"), "ciencias-humanas")
        self.assertEqual(area_oficial(2016, 91, "x"), "linguagens")
        self.assertEqual(area_oficial(2017, 1, "x"), "linguagens")
        self.assertEqual(area_oficial(2017, 180, "x"), "matematica")
        self.assertEqual(area_oficial(2017, 181, "fonte"), "fonte")


if __name__ == "__main__":
    unittest.main()
