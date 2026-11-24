"""Extrator das provas em PDF (Fase 5.3): só roda com requirements-dev.txt instalado."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
try:
    from importar_prova_pdf import texto_plano
except ImportError:  # pypdfium2 não está no instalador nem na CI
    texto_plano = None


@unittest.skipUnless(texto_plano, "precisa de requirements-dev.txt")
class TextoPlano(unittest.TestCase):
    def test_descricao_do_print_nao_fecha_a_imagem(self):
        md = "Veja **a tabela**.\n\n![Ano · Total (mil)](/imagens/x.png)\n\nAlternativa A: [2]"
        self.assertEqual(texto_plano(md), "Veja a tabela. Figura: Ano · Total mil. Alternativa A: 2")


if __name__ == "__main__":
    unittest.main()
