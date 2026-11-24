"""PILOTO (Fase 5.3): extrai questões de um caderno de prova do ENEM em PDF (INEP) para revisão humana.

Uso (desenvolvimento; precisa de requirements-dev.txt):
    .venv\\Scripts\\python.exe scripts\\importar_prova_pdf.py <prova.pdf> <pasta de saída> [primeira última]

Saída: <pasta>/questoes.json e as figuras recortadas em PNG. Nada entra no banco: é material para conferir.

Como funciona: o caderno tem duas colunas. Cada questão começa em "QUESTÃO NN" e vai até a próxima, seguindo a
ordem de leitura (coluna esquerda, coluna direita, próxima página). O texto é montado letra a letra com a posição
de cada uma: linha que chega à margem foi quebrada pelo layout e se junta à seguinte; linha curta é fim de
parágrafo ou verso. Figuras (imagens e desenhos vetoriais) são recortadas da página e entram no ponto do texto.
Questão com aviso (raiz ou fração desenhada, alternativas em imagem) sai como print do caderno, com o texto
extraído como descrição (ADR 0030).
"""
from __future__ import annotations

import ctypes
import json
import re
import sys
from pathlib import Path

import pypdfium2 as pdfium
import pypdfium2.raw as raw

TOPO_REL, BASE_REL = 56, 30     # cabeçalho e rodapé (pontos, a partir da margem de corte da página); o topo
                                # de cada caderno é medido em extrair(): o de 2025 é mais alto que o de 2024
MARGEM_DIREITA = 12             # linha que termina a menos disso da borda da coluna foi quebrada pelo layout
RUIDO = re.compile(r"^\*\w+\*$|ENEM\s?20\d\dENEM|^\d+$|•\s*\d+º DIA\s*•|CADERNO \d+ • ")
CABECALHO = re.compile(r"^((?i:QUEST ?ÃO) \d{2,3}|Questões de \d{2,3} a \d{2,3}.*|LINGUAGENS, CÓDIGOS.*|CIÊNCIAS (HUMANAS|DA NATUREZA).*|"
                       r"MATEMÁTICA E SUAS TECNOLOGIAS.*)$")


FIM_DE_BLOCO = re.compile(r"^(LINGUAGENS, CÓDIGOS E SUAS TECNOLOGIAS|CIÊNCIAS HUMANAS E SUAS TECNOLOGIAS|"
                          r"CIÊNCIAS DA NATUREZA E SUAS TECNOLOGIAS|MATEMÁTICA E SUAS TECNOLOGIAS|"
                          r"INSTRUÇÕES PARA A REDAÇÃO)$")


def area(pagina):
    """(esq, base, dir, topo) da parte impressa: o PDF tem margem de corte (cropbox) e as letras vêm em coordenadas
    absolutas."""
    return pagina.get_cropbox()


def vao_no_meio(pagina, y_topo, y_base) -> int:
    """Maior faixa (em pt) sem letras perto do meio da página, entre y_base e y_topo. Duas colunas deixam um vão de
    uns 9 pt ou mais; texto de largura inteira não deixa nenhum."""
    esq, _, dir_, _ = area(pagina)
    meio = (esq + dir_) / 2
    tp = pagina.get_textpage()
    ocupado = [0] * 31  # quantas letras cobrem cada ponto de meio-15 a meio+15
    for i in range(tp.count_chars()):
        l, b, r, t = tp.get_charbox(i)
        # Só letras de tamanho normal: em 2024, o separador das colunas é um microtexto vertical bem no meio
        if r - l > 2 and y_base < b < y_topo and tp.get_text_range(i, 1).strip():
            for k in range(max(int(l - meio + 15), 0), min(int(r - meio + 15) + 1, 31)):
                ocupado[k] += 1
    vao = maior = 0
    for n in ocupado:  # quase sem letra: rótulos de figura deixam uma ou outra
        vao = vao + 1 if n <= 1 else 0
        maior = max(maior, vao)
    return maior


def colunas(pagina) -> list[tuple[float, float]]:
    """Duas colunas; ou uma só, quando o texto atravessa o meio da página (em 2024 e 2025, há páginas de largura
    inteira, como o texto das questões 06 a 10 de 2025)."""
    esq, _, dir_, _ = area(pagina)
    meio = (esq + dir_) / 2
    topo, base = faixa_util(pagina)
    # shortcut: página metade de largura inteira e metade em colunas sai como uma coluna só; em 2024/2025, só a da
    # redação, que não é questão
    if vao_no_meio(pagina, topo, base) < 5:
        return [(esq, dir_ - 25)]
    return [(esq, meio - 2), (meio + 2, dir_ - 25)]  # à direita, uma faixa decorativa


def faixa_util(pagina, topo_rel=TOPO_REL) -> tuple[float, float]:
    _, base, _, topo = area(pagina)
    return topo - topo_rel, base + BASE_REL


SOBRE = str.maketrans("0123456789+-−=()ni", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁻⁼⁽⁾ⁿⁱ")
SOB = str.maketrans("0123456789+-−=()aeoxhklmnpst", "₀₁₂₃₄₅₆₇₈₉₊₋₋₌₍₎ₐₑₒₓₕₖₗₘₙₚₛₜ")


def elevar(c: str, tabela) -> str:
    """Expoente/índice em Unicode (2¹⁹, H₂O); sem equivalente, fica com ^ ou _ para não virar outro número."""
    t = c.translate(tabela)
    return t if t != c or not c.strip() else ("^" if tabela is SOBRE else "_") + c


def fonte(tp, i: int) -> str:
    nome = ctypes.create_string_buffer(128)
    raw.FPDFText_GetFontInfo(tp.raw, i, nome, 128, ctypes.byref(ctypes.c_int()))
    return nome.value.decode(errors="replace")


def linhas_da_regiao(tp, x0, x1, y_topo, y_base):
    """Letras da região agrupadas em linhas: [(y, x_inicio, x_fim, texto, alternativa)], de cima para baixo.
    alternativa: a letra (A-E) quando a linha começa com o marcador de alternativa, senão None."""
    letras, anterior = [], None
    for i in range(tp.count_chars()):
        l, b, r, t = tp.get_charbox(i, loose=True)  # caixa "solta": vai até onde a próxima letra começa
        if r - l <= 0 and anterior:  # espaços gerados pelo PDF não têm posição: ficam onde a letra anterior terminou
            l, b, r, t = anterior[2], anterior[1], anterior[2], anterior[3]
        anterior = (l, b, r, t)
        cx, cy = (l + r) / 2, (b + t) / 2
        if x0 <= cx <= x1 and y_base <= cy <= y_topo:
            letras.append((cy, l, r, tp.get_text_range(i, 1), i, b, t))
    letras.sort(key=lambda c: -c[0])
    # Primeiro as letras de tamanho normal formam as linhas; depois cada letra pequena (índice de química, expoente)
    # entra na linha cuja altura a contém. Antes, o índice de "H₂O" ficava tão abaixo que virava outra linha.
    alturas = sorted(c[6] - c[5] for c in letras if c[3].strip()) or [0]
    normal = alturas[len(alturas) // 2]
    pequena = lambda c: c[3].strip() and c[6] - c[5] < 0.8 * normal  # noqa: E731
    linhas = []
    for c in letras:  # mesma linha: altura a até 3 pt da média da linha
        if pequena(c) or not c[3].strip():
            continue
        if linhas and abs(c[0] - sum(x[0] for x in linhas[-1]) / len(linhas[-1])) <= 3:
            linhas[-1].append(c)
        else:
            linhas.append([c])
    for c in (c for c in letras if pequena(c) or not c[3].strip()):
        # Espaços também entram depois: sozinhos, formavam uma linha que roubava as letras pequenas da citação
        # ("SARTORI" virava "TORI … SAR"). Entre as linhas possíveis (as de 2025 são mais juntas, e um expoente cabe
        # na altura de duas), vale a que não tem letra embaixo dele; antes, "mol⁻¹" da linha de baixo ia parar em
        # "mo₋₁lar", na de cima.
        perto = lambda ln: abs(c[0] - sum(x[0] for x in ln) / len(ln))  # noqa: E731
        # Mesma altura: a citação inteira em letra pequena, com um "." de tamanho normal no meio, é uma linha só
        mesma_altura = [ln for ln in linhas if perto(ln) <= 3 and any(x[3].strip() for x in ln)]
        candidatas = [ln for ln in linhas if min(x[5] for x in ln) - 1 <= c[0] <= max(x[6] for x in ln) + 1
                      and min(x[1] for x in ln) - 20 <= c[1] <= max(x[2] for x in ln) + 20]
        livres = [ln for ln in candidatas
                  if not any(x[3].strip() and c[1] < x[2] - 0.5 and x[1] < c[2] - 0.5 for x in ln)]
        if mesma_altura or not c[3].strip():
            dona = min(mesma_altura, key=perto, default=None)
        else:  # expoente ou índice: fora do meio da linha
            dona = min(livres or candidatas, key=perto, default=None)
        if dona:
            dona.append(c)
        elif c[3].strip():  # espaço sem linha fica de fora (sozinho, atraía os índices de várias fórmulas: "2 2 2")
            linhas.append([c])  # letra pequena sozinha (rótulo): linha própria
    linhas.sort(key=lambda ln: -max(x[0] for x in ln))
    saida = []
    for ln in linhas:
        ln.sort(key=lambda c: c[1])
        # Expoente e índice: letra bem menor que as da linha, acima ou abaixo do meio dela. Sem isto, 2¹⁹ virava 219.
        visiveis = sorted(c for c in ln if c[3].strip())
        alturas = sorted(c[6] - c[5] for c in ln if c[3].strip()) or [0]
        h, meio = alturas[len(alturas) // 2], (visiveis[len(visiveis) // 2][0] if visiveis else 0)
        partes, fim = [], None
        for c in ln:
            if fim is not None and c[1] - fim > 1.2 and c[3] != " " and partes and partes[-1] != " ":
                partes.append(" ")  # espaço que o PDF não registra como letra (comum em negrito)
            letra = c[3]
            if letra.strip() and h and c[6] - c[5] < 0.8 * h:
                if c[0] > meio + 0.12 * h:
                    letra = elevar(letra, SOBRE)
                elif c[0] < meio - 0.12 * h:
                    letra = elevar(letra, SOB)
            partes.append(letra)
            fim = c[2] if fim is None else max(fim, c[2])
        texto = "".join(partes).replace("\r", "").replace("\n", "").replace("￾", "").strip()
        if texto:
            # O marcador da alternativa é uma letra num círculo, de uma fonte de símbolos (e mais larga que um "A" comum).
            primeira = next(c for c in ln if c[3].strip())
            alt = None
            if primeira[3] in "ABCDE" and ("Pi" in fonte(tp, primeira[4]) or primeira[2] - primeira[1] > 9):
                alt = primeira[3]
                texto = texto[1:].strip()
            saida.append((ln[0][0], ln[0][1], max(c[2] for c in ln), re.sub(r"\s+", " ", texto), alt))
    return saida


def figuras_da_regiao(pagina, x0, x1, y_topo, y_base):
    """Caixas (esq, base, dir, topo) das imagens e desenhos da região, juntando os que se tocam."""
    # Cada caixa: [esq, base, dir, topo, formas cheias, filetes horizontais, filetes verticais]
    caixas = []
    for o in pagina.get_objects(max_depth=2):
        if o.type not in (raw.FPDF_PAGEOBJ_IMAGE, raw.FPDF_PAGEOBJ_PATH):
            continue
        l, b, r, t = o.get_bounds()
        # Pelo centro: figuras largas passam um pouco da margem da coluna (antes, sumiam sem aviso).
        if not (x0 <= (l + r) / 2 <= x1 and y_base <= (b + t) / 2 <= y_topo):
            continue
        if t > y_topo + 15 or b < y_base - 15:  # passa do cabeçalho ou da próxima questão: faixa decorativa da página
            continue
        l, r = max(l, x0 - 15), min(r, x1 + 15)  # sem invadir a outra coluna
        imagem = o.type == raw.FPDF_PAGEOBJ_IMAGE
        horizontal, vertical = not imagem and t - b < 6 and r - l >= 6, not imagem and r - l < 6 and t - b >= 6
        if t - b < 6 and r - l < 6:
            continue
        caixas.append([l, b, r, t, int(not (horizontal or vertical)), int(horizontal), int(vertical),
                       int(o.type == raw.FPDF_PAGEOBJ_IMAGE)])
    juntou = True
    while juntou:  # partes de um mesmo gráfico viram uma figura só
        juntou = False
        for i in range(len(caixas)):
            for j in range(i + 1, len(caixas)):
                a, c = caixas[i], caixas[j]
                if a[0] <= c[2] + 4 and c[0] <= a[2] + 4 and a[1] <= c[3] + 4 and c[1] <= a[3] + 4:
                    caixas[i] = [min(a[0], c[0]), min(a[1], c[1]), max(a[2], c[2]), max(a[3], c[3]),
                                 a[4] + c[4], a[5] + c[5], a[6] + c[6], a[7] + c[7]]
                    del caixas[j]
                    juntou = True
                    break
            if juntou:
                break
    # Fica: o que tem forma cheia (imagem, gráfico) ou é grade de filetes (tabela); some o filete solto (separador,
    # sublinhado, a barra ao lado de "QUESTÃO"). Menores que 30x30 pt são enfeite.
    # Imagem rasterizada fica mesmo pequena (as setas de alternativa têm 64x8 pt); desenho pequeno é enfeite.
    # Faixa fina e comprida (a barra ao lado de "QUESTÃO" nas páginas de largura inteira, em 2025) também é enfeite.
    return [c[:4] for c in caixas if (c[4] or (c[5] >= 2 and c[6] >= 2)) and (c[7] or (c[2] - c[0]) * (c[3] - c[1]) > 900)
            and not (not c[7] and c[3] - c[1] < 10 and c[2] - c[0] > 15 * (c[3] - c[1]))]


def desenhos_no_texto(pagina, linhas, caixas, x0, x1) -> int:
    """Quantos desenhos soltos encostam numa linha de texto: raiz, traço de fração, sublinhado. O texto dessas linhas
    pode ter perdido o sentido ("6∛6" vira "6³ 6"), então a questão vai para a revisão humana com aviso."""
    n = 0
    for o in pagina.get_objects(max_depth=2):
        if o.type != raw.FPDF_PAGEOBJ_PATH:
            continue
        l, b, r, t = o.get_bounds()
        if not (x0 <= l and r <= x1) or any(c[0] - 2 <= l and r <= c[2] + 2 and c[1] - 2 <= b and t <= c[3] + 2 for c in caixas):
            continue
        if r - l > 0.8 * (x1 - x0):  # separador de largura inteira
            continue
        for ln in linhas:
            no_meio = ln[1] + 14 < r and l < ln[2]  # depois do marcador de alternativa (círculo atrás da letra)
            if no_meio and b - 4 <= ln[0] <= t + 4:
                n += 1
                break
    return n


def montar_paragrafos(itens):
    """itens: linhas de texto e figuras, de cima para baixo. Devolve blocos {"alt": letra ou None, "texto": ...}.
    Junta linhas quebradas pelo layout; cada alternativa começa um bloco novo, mesmo após uma linha cheia."""
    blocos, atual = [], None

    def fechar():
        nonlocal atual
        if atual and atual["texto"]:
            blocos.append({"alt": atual["alt"], "texto": atual["texto"]})
        atual = None

    for item in itens:
        if item[0] == "figura":
            if atual and atual["alt"] and not atual["texto"]:  # alternativa que é só uma figura
                atual["texto"] = item[1]
                fechar()
                continue
            fechar()
            blocos.append({"alt": None, "texto": item[1]})
            continue
        _, texto, x_fim, alt, x_ini, base_x, x1 = item  # x1: margem direita da coluna desta linha
        recuo = x_ini - base_x  # medido na coluna da própria linha: o texto continua de uma coluna para a outra
        ultimo = blocos[-1] if blocos and atual is None else None
        # "Acesso em: ..." é sempre o fim de uma fonte: junta com o que veio antes, seja qual for o alinhamento.
        if not alt and texto.startswith("Acesso em") and (atual or blocos):
            alvo = atual if atual else blocos[-1]
            alvo["texto"] = f"{alvo['texto']} {texto}".strip()
            if atual:
                fechar()
            continue
        # Fonte em mais de uma linha ("Disponível em: ..." / "Acesso em: ..."): junta com a anterior.
        if not alt and ultimo and ultimo.get("fonte") and (texto.startswith("Acesso em") or ultimo["texto"].endswith(":")):
            ultimo["texto"] = f"{ultimo['texto']} {texto}"
            continue
        # Fonte do texto: alinhada à direita (começa longe da margem e vai até o fim) ou "Disponível em".
        if not alt and not (atual and atual["alt"]) and (
                texto.startswith("Disponível em") or (recuo > 30 and x_fim >= x1 - MARGEM_DIREITA)):
            if ultimo and ultimo.get("fonte"):
                ultimo["texto"] = f"{ultimo['texto']} {texto}"
            else:
                fechar()
                blocos.append({"alt": None, "texto": texto, "fonte": True})
            continue
        if alt:
            fechar()
            atual = {"alt": alt, "texto": ""}
        elif atual and not atual["alt"] and recuo > atual["recuo"] + 5:  # recuo de primeira linha ou título
            fechar()
        if atual is None:
            atual = {"alt": None, "texto": ""}
        atual["recuo"] = recuo
        atual["texto"] = f"{atual['texto']} {texto}".strip() if atual["texto"] else texto
        if atual["texto"].endswith("-") and x_fim >= x1 - MARGEM_DIREITA:  # hífen de quebra de linha
            atual["texto"] = atual["texto"][:-1]
            continue
        if x_fim < x1 - MARGEM_DIREITA and not atual["alt"]:  # linha curta: fim de parágrafo ou verso
            fechar()
    fechar()
    return blocos


def extrair(pdf_path: Path, saida: Path, primeira=1, ultima=180) -> list[dict]:
    pdf = pdfium.PdfDocument(pdf_path)
    saida.mkdir(parents=True, exist_ok=True)
    # 1. Cabeçalhos "QUESTÃO NN" na ordem de leitura, e o idioma (questões 1 a 5 do 1º dia vêm duas vezes)
    marcas, idioma = [], ""
    for np_, pagina in enumerate(pdf):
        tp = pagina.get_textpage()
        topo, base = faixa_util(pagina)
        for ci, (x0, x1) in enumerate(colunas(pagina)):
            for y, xi, xf, texto, _ in linhas_da_regiao(tp, x0, x1, topo + 30, base):
                if "opção espanhol" in texto:
                    idioma = "espanhol"
                elif "opção inglês" in texto:
                    idioma = "ingles"
                comum = re.match(r"Texto para as Quest.es de (\d{2,3}) a (\d{2,3})", texto)
                if comum:  # texto de várias questões: vira print e entra no começo de cada uma (ver o fim de extrair)
                    marcas.append({"n": int(comum.group(1)), "ate": int(comum.group(2)), "idioma": "comum",
                                   "pagina": np_, "coluna": ci, "y": y})
                if FIM_DE_BLOCO.match(texto):  # título de área ou página da redação: a questão anterior termina aqui
                    marcas.append({"n": 0, "idioma": "fim", "pagina": np_, "coluna": ci, "y": y})
                m = re.match(r"QUEST ?ÃO (\d{2,3})", texto, re.I)  # 2025: "Quest ão", em versalete
                if m:
                    n = int(m.group(1))
                    marcas.append({"n": n, "idioma": idioma if n <= 5 else "", "pagina": np_, "coluna": ci, "y": y})
    # A área útil começa logo acima da marca "QUESTÃO" mais alta das páginas (o cabeçalho muda de um ano para outro)
    questoes_ = [m for m in marcas if m["n"]]
    topo_rel = min(area(pdf[m["pagina"]])[3] - m["y"] for m in questoes_) - 10 if questoes_ else TOPO_REL
    # 2. Região de cada questão: do cabeçalho até o próximo, atravessando colunas e páginas
    questoes = []
    for k, m in enumerate(marcas):
        if not primeira <= m["n"] <= ultima:
            continue
        fim = marcas[k + 1] if k + 1 < len(marcas) else None
        trechos, (p, c, y) = [], (m["pagina"], m["coluna"], m["y"] + 8)
        while True:
            if fim and (p, c) == (fim["pagina"], fim["coluna"]):
                if fim["y"] + 8 < y:  # a próxima marca no topo da coluna (ex.: página da redação): nada a pegar aqui
                    trechos.append((p, c, y, fim["y"] + 8))
                break
            trechos.append((p, c, y, faixa_util(pdf[p], topo_rel)[1]))
            p, c = (p, c + 1) if c + 1 < len(colunas(pdf[p])) else (p + 1, 0)
            if p < len(pdf):
                y = faixa_util(pdf[p], topo_rel)[0]  # continuação: só a área útil (antes, o logotipo do cabeçalho entrava)
            if p >= len(pdf) or (not fim and p > m["pagina"] + 1):
                break
        itens, figuras = [], []
        originais, desenhos, perdidas, cortadas, limites = [], 0, 0, 0, []
        for p, c, y_topo, y_base in trechos:
            pagina = pdf[p]
            x0, x1 = colunas(pagina)[c]
            tp = pagina.get_textpage()
            caixas = figuras_da_regiao(pagina, x0, x1, y_topo, y_base)
            texto_util = [ln for ln in linhas_da_regiao(tp, x0, x1, y_topo, y_base)  # sem rodapé e cabeçalho (logotipos)
                          if ln[4] or not (RUIDO.search(ln[3]) or CABECALHO.match(ln[3]))]
            if limites and not texto_util:  # continuação sem texto: a questão acabou (a última iria até a contracapa)
                break
            desenhos += desenhos_no_texto(pagina, texto_util, caixas, x0, x1)
            if len(colunas(pagina)) == 2:
                cortadas += vao_no_meio(pagina, y_topo, y_base) < 5  # rede de segurança: texto cortado no meio
            for o in pagina.get_objects(max_depth=2):  # rede de segurança: imagem da região que não virou figura
                if o.type == raw.FPDF_PAGEOBJ_IMAGE:
                    l, b, r, t = o.get_bounds()
                    cx, cy = (l + r) / 2, (b + t) / 2
                    if r - l > 40 and x0 <= cx <= x1 and y_base <= cy <= y_topo and not any(
                            c[0] - 2 <= cx <= c[2] + 2 and c[1] - 2 <= cy <= c[3] + 2 for c in caixas):
                        perdidas += 1
            entradas = []
            linhas = linhas_da_regiao(tp, x0, x1, y_topo, y_base)
            base_x = min((ln[1] for ln in linhas if not ln[4]), default=x0)  # onde o texto comum começa nesta coluna
            for ln in linhas:
                dentro = any(b[0] - 1 <= ln[1] and ln[2] <= b[2] + 1 and b[1] - 1 <= ln[0] <= b[3] + 1 for b in caixas)
                # Alternativa nunca é ruído: "A 1" vira só "1", que pareceria número de página.
                if not dentro and (ln[4] or (not RUIDO.search(ln[3]) and not CABECALHO.match(ln[3]))):
                    entradas.append((ln[0], ("texto", ln[3], ln[2], ln[4], ln[1], base_x, x1)))
            for b in caixas:
                nome = f"{m['n']:03d}{m['idioma'][:2]}-{len(figuras) + 1}.png"
                escala = 2.5
                esq, base_p, dir_, topo_p = area(pagina)  # o recorte é medido a partir das bordas da área impressa
                imagem = pagina.render(scale=escala, crop=(b[0] - esq - 2, b[1] - base_p - 2, dir_ - b[2] - 2,
                                                          topo_p - b[3] - 2)).to_pil()
                imagem.save(saida / nome, optimize=True)
                figuras.append(nome)
                # Texto de dentro da figura (tabela, rótulos de gráfico) vira a descrição: leitor de tela lê (ADR 0005).
                dentro_dela = [ln[3] for ln in linhas if b[0] - 1 <= ln[1] and ln[2] <= b[2] + 1 and b[1] - 1 <= ln[0] <= b[3] + 1]
                descricao = re.sub(r"[\[\]()]", "", " · ".join(dentro_dela))[:400] or "Figura da questão"
                entradas.append((b[3], ("figura", f"![{descricao}](/imagens/{nome})")))
            # Onde termina o conteúdo deste trecho (o print não leva linha separadora nem contracapa)
            fundos = [e[1][0] == "texto" and e[0] - 7 for e in entradas] + [b[1] for b in caixas]
            limites.append((y_topo, min(f for f in fundos if f is not False)) if entradas else None)
            entradas.sort(key=lambda e: -e[0])
            itens += [e[1] for e in entradas]
        blocos = montar_paragrafos(itens)
        for i, (p, c, y_topo, y_base) in enumerate(trechos):  # recorte do caderno, para a revisão lado a lado
            pagina = pdf[p]
            x0, x1 = colunas(pagina)[c]
            esq, base_p, dir_, topo_p = area(pagina)
            nome = f"original-{m['n']:03d}{m['idioma'][:2]}-{i + 1}.png"
            pagina.render(scale=1.6, crop=(x0 - esq, max(y_base - base_p - 4, 0), dir_ - x1, max(topo_p - y_topo, 0))).to_pil().save(saida / nome)
            originais.append(nome)
        questoes.append({"numero": m["n"], "idioma": m["idioma"], "blocos": blocos, "figuras": figuras,
                         "originais": originais, "pagina": m["pagina"] + 1, "desenhos": desenhos, "perdidas": perdidas, "cortadas": cortadas,
                         "trechos": [(p, c, *lim) for (p, c, _, _), lim in zip(trechos, limites) if lim],
                         **({"ate": m["ate"]} if "ate" in m else {})})
    questoes = [separar_alternativas(q) for q in questoes]
    for q in questoes:
        trechos = q.pop("trechos")
        if q["avisos"]:  # o texto comum não tem alternativas, então sempre cai aqui
            usar_print(pdf, saida, q, trechos)
    for comum in [q for q in questoes if q["idioma"] == "comum"]:
        questoes.remove(comum)
        for q in questoes:
            if comum["numero"] <= q["numero"] <= comum["ate"]:
                q["contexto"] = f"{comum['contexto']}\n\n{q['contexto']}".strip()
                q["figuras"] = comum["figuras"] + q["figuras"]
                q["originais"] = comum["originais"] + q["originais"]
    return questoes


def texto_plano(md: str) -> str:
    """Markdown da questão em texto corrido, para a descrição do print (sem colchetes e parênteses, que fechariam
    a imagem no markdown.js)."""
    md = re.sub(r"!\[([^\[\]]*)\]\([^()\s]*\)", r" Figura: \1. ", md)
    return re.sub(r"\s+", " ", re.sub(r"[\[\]()*_]", "", md)).strip()


def usar_print(pdf, saida: Path, q: dict, trechos) -> None:
    """Questão com aviso (raiz ou fração desenhada, alternativas em imagem): entra como print do caderno, que mostra
    exatamente o original. O texto extraído vira a descrição para o leitor de tela (ADR 0005), e os botões A-E
    ficam só com a letra, porque as alternativas já estão no print (ADR 0030)."""
    from PIL import ImageOps

    descricao = texto_plano(" ".join([q["contexto"], q["introducao"]]
                                     + [f"Alternativa {a['letra']}: {a['texto']}" for a in q["alternativas"]]))
    for nome in q["figuras"]:  # os recortes das figuras já estão dentro do print
        (saida / nome).unlink(missing_ok=True)
    prints = []
    for i, (p, c, y_topo, y_base) in enumerate(trechos):
        pagina = pdf[p]
        x0, x1 = colunas(pagina)[c]
        esq, base_p, dir_, topo_p = area(pagina)
        if i == 0:
            y_topo -= 15  # começa abaixo de "QUESTÃO NN": o app mostra o número
        img = pagina.render(scale=2, crop=(x0 - esq, max(y_base - 3 - base_p, 0), dir_ - x1, max(topo_p - y_topo, 0))).to_pil()
        caixa = ImageOps.invert(img.convert("L")).point(lambda v: 255 if v > 24 else 0).getbbox()
        if not caixa:  # trecho em branco (a questão terminou no fim da coluna)
            continue
        img = img.crop((max(caixa[0] - 8, 0), max(caixa[1] - 8, 0), min(caixa[2] + 8, img.width), min(caixa[3] + 8, img.height)))
        nome = f"{q['numero']:03d}{q['idioma'][:2]}-print-{i + 1}.png"
        img.save(saida / nome, optimize=True)
        prints.append(nome)
    q["figuras"] = prints
    q["contexto"] = "\n\n".join(f"![{descricao if k == 0 else 'Continuação da questão'}](/imagens/{n})"
                                for k, n in enumerate(prints))
    q["introducao"] = ""
    q["alternativas"] = [{"letra": letra, "texto": ""} for letra in "ABCDE"]
    q["print"] = True


def separar_alternativas(q: dict) -> dict:
    """Blocos marcados com letra são as alternativas; o que vem antes é o texto. O último parágrafo antes das
    alternativas é a pergunta (enunciado). Problemas ficam em q["avisos"] para a revisão humana."""
    blocos = q.pop("blocos")
    primeira = next((i for i, b in enumerate(blocos) if b["alt"]), len(blocos))
    corpo = [b["texto"] for b in blocos[:primeira]]
    alts = {}
    for b in blocos[primeira:]:
        if b["alt"]:
            alts[b["alt"]] = b["texto"]
        elif alts:  # parágrafo solto depois de uma alternativa: continuação dela
            ultima = list(alts)[-1]
            alts[ultima] = f"{alts[ultima]}\n\n{b['texto']}"
    q["alternativas"] = [{"letra": l, "texto": alts[l]} for l in sorted(alts)]
    q["introducao"] = corpo[-1] if corpo else ""
    q["contexto"] = "\n\n".join(corpo[:-1])
    q["avisos"] = []
    if sorted(alts) != list("ABCDE"):
        q["avisos"].append(f"alternativas encontradas: {''.join(sorted(alts)) or 'nenhuma'}")
    if q["introducao"].startswith("![") or not q["introducao"]:
        q["avisos"].append("enunciado não identificado")
    if q.pop("cortadas", 0):
        q["avisos"].append("texto atravessa as colunas (página de largura inteira?): conferir com o original")
    if q.pop("perdidas", 0):
        q["avisos"].append("figura possivelmente perdida: conferir com o original")
    if q.pop("desenhos", 0):
        q["avisos"].append("fração, raiz ou traço desenhado no meio do texto: conferir com o original")
    return q


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    pdf, saida = Path(sys.argv[1]), Path(sys.argv[2])
    faixa = [int(x) for x in sys.argv[3:5]] or [1, 180]
    questoes = extrair(pdf, saida, *faixa)
    (saida / "questoes.json").write_text(json.dumps(questoes, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(questoes)} questões extraídas em {saida}")


if __name__ == "__main__":
    main()
