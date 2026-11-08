"""Testes das partes com regra: validação do guia baixado e área pela numeração oficial.

Rodar:  .venv\\Scripts\\python.exe -m unittest discover tests
"""
import unittest

from app import guia
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


class TestAreaOficial(unittest.TestCase):
    def test_ordem_das_areas_mudou_em_2017(self):
        self.assertEqual(area_oficial(2016, 1, "x"), "ciencias-humanas")
        self.assertEqual(area_oficial(2016, 91, "x"), "linguagens")
        self.assertEqual(area_oficial(2017, 1, "x"), "linguagens")
        self.assertEqual(area_oficial(2017, 180, "x"), "matematica")
        self.assertEqual(area_oficial(2017, 181, "fonte"), "fonte")


if __name__ == "__main__":
    unittest.main()
