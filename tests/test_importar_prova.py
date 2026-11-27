"""Provas em PDF (Fase 5.3, ADR 0030): extrator, revisão e importação. Só roda com requirements-dev.txt instalado."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
try:
    from PIL import Image, ImageDraw

    from importar_prova_pdf import aparar_bordas, texto_plano
    from importar_prova_revisada import preparar
    from revisao_prova import gravar_decisao
except ImportError:  # pypdfium2 e Pillow não estão no instalador nem na CI
    texto_plano = None

QUESTAO = {
    "numero": 6, "idioma": "", "contexto": "Texto.\n\n![Tabela](/imagens/006-1.png)", "introducao": "A autora",
    "alternativas": [{"letra": x, "texto": f"opção {x}"} for x in "ABCDE"], "prints": ["006-print-1.png"],
    "prefixo": "![De próprio punho](/imagens/006co-print-1.png)", "prefixo_figuras": ["006co-print-1.png"],
    "avisos": [],
}


@unittest.skipUnless(texto_plano, "precisa de requirements-dev.txt")
class Extrator(unittest.TestCase):
    def test_descricao_do_print_nao_fecha_a_imagem(self):
        md = "Veja **a tabela**.\n\n![Ano · Total (mil)](/imagens/x.png)\n\nAlternativa A: [2]"
        self.assertEqual(texto_plano(md), "Veja a tabela. Figura: Ano · Total mil. Alternativa A: 2")

    def test_fio_na_borda_sai_do_print(self):
        tinta = Image.new("L", (200, 100), 0)
        d = ImageDraw.Draw(tinta)
        d.rectangle((10, 10, 150, 90), fill=255)  # o conteúdo
        d.line((190, 0, 190, 99), fill=255, width=2)  # o separador das colunas, depois de um vão
        self.assertEqual(aparar_bordas(tinta), (10, 10, 151, 91))

    def test_conteudo_na_borda_fica(self):
        tinta = Image.new("L", (200, 100), 0)
        ImageDraw.Draw(tinta).rectangle((10, 10, 199, 90), fill=255)
        self.assertEqual(aparar_bordas(tinta), (10, 10, 200, 91))


@unittest.skipUnless(texto_plano, "precisa de requirements-dev.txt")
class RevisaoEImportacao(unittest.TestCase):
    def test_decisao_gravada_e_validada(self):
        with tempfile.TemporaryDirectory() as d:
            gravar_decisao(Path(d), {"chave": "6", "decisao": "print"})
            gravar_decisao(Path(d), {"chave": "1-ingles", "decisao": "texto"})
            revisao = json.loads((Path(d) / "revisao.json").read_text(encoding="utf-8"))
            self.assertEqual({k: v["decisao"] for k, v in revisao.items()}, {"6": "print", "1-ingles": "texto"})
            with self.assertRaises(ValueError):
                gravar_decisao(Path(d), {"chave": "6", "decisao": "apagar tudo"})

    def test_texto_leva_prefixo_e_troca_o_caminho_das_imagens(self):
        q, usadas = preparar(dict(QUESTAO), "texto", 2025)
        self.assertEqual(usadas, ["006co-print-1.png", "006-1.png"])
        self.assertIn("](/imagens/inep2025-006co-print-1.png)", q["contexto"])
        self.assertIn("](/imagens/inep2025-006-1.png)", q["contexto"])
        self.assertEqual(q["alternativas"][0]["texto"], "opção A")

    def test_texto_sem_as_cinco_alternativas_e_recusado(self):
        q = {**QUESTAO, "alternativas": QUESTAO["alternativas"][:2]}
        with self.assertRaises(ValueError):
            preparar(q, "texto", 2024)
        self.assertEqual(len(preparar(q, "print", 2024)[0]["alternativas"]), 5)
        fracao = {**QUESTAO, "avisos": ["fração, raiz ou traço desenhado no meio do texto: conferir com o original"]}
        self.assertEqual(preparar(fracao, "texto", 2024)[0]["alternativas"][0]["texto"], "opção A")  # quem decide é o revisor

    def test_print_usa_a_imagem_do_caderno_e_so_as_letras(self):
        q, usadas = preparar(dict(QUESTAO), "print", 2025)
        self.assertEqual(usadas, ["006co-print-1.png", "006-print-1.png"])  # a figura do texto não vai junto
        self.assertTrue(q["contexto"].startswith("![De próprio punho](/imagens/inep2025-006co-print-1.png)"))
        self.assertIn("Texto. Figura: Tabela. A autora Alternativa A: opção A", q["contexto"])  # descrição
        self.assertEqual(q["introducao"], "")
        self.assertEqual([a["texto"] for a in q["alternativas"]], [""] * 5)


if __name__ == "__main__":
    unittest.main()
