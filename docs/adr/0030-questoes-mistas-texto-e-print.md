# 0030. Provas novas: texto quando a extração é segura, print do caderno quando não é

- **Status:** Aceita
- **Data:** 2026-11-24

## Contexto
As provas de 2024 e 2025 (Fase 5.3) só existem em PDF no INEP. O piloto do extrator (`scripts/importar_prova_pdf.py`)
acerta a estrutura de 91 dos 107 trechos testados, mas parte das questões não vira texto sem perda: raízes e frações
desenhadas ("6∛6" sai "6³ 6") e alternativas que são imagens dispostas em grade. Revisar e corrigir essas questões à mão
seria lento e sujeito a erro, e um erro ali troca a resposta.

O autor sugeriu usar o print do caderno em vez de replicar o texto. Usar print em **todas** as questões, porém, piora
o que a ADR 0005 exige: leitor de tela não lê imagem, o texto não se ajusta a 390 px (fica com cerca de 12 px), o
tema escuro ganha um retângulo branco por questão, e o pacote de dados cresce.

## Decisão
- **Questão sem aviso do extrator:** entra em **texto**, como as demais do banco.
- **Questão com aviso** (alternativas incompletas, enunciado não identificado, figura possivelmente perdida, fração ou
  raiz desenhada): entra como **print do caderno**, recortado só até onde vai o conteúdo da questão, sem o
  cabeçalho "QUESTÃO NN", com escala 2.
  - O texto extraído vira a **descrição da imagem** para o leitor de tela. Um erro pequeno nela não muda o que o
    aluno vê.
  - Os botões A–E ficam **só com a letra**, porque as alternativas estão no print. O gabarito continua no servidor
    (ADR 0003).
- O extrator também deixou de recortar enfeites da página (a faixa azul da margem e a barra de microtexto), que antes
  viravam "figura" em 20 questões em texto: um desenho que passa do cabeçalho ou do início da próxima questão é
  descartado. A última questão do caderno termina no primeiro trecho de continuação sem texto, sem levar a contracapa.

## Consequências
- As questões difíceis ficam idênticas ao original, sem revisão de texto. Na revisão humana, basta conferir o recorte.
- No caderno Azul de 2024 (2º dia), 16 de 90 questões entram como print, com cerca de 3 MB a mais no pacote.
- No celular, a letra do print é menor que a do app: o aluno pode ampliar com os dedos. O tema escuro mostra o print
  com fundo branco, como já acontece com as figuras.
- Se o extrator melhorar (por exemplo, para montar raízes), menos questões caem no print, sem mudar o app.
