# 0031. Provas de 2024 e 2025: extração, revisão humana e importação

- **Status:** Aceita
- **Data:** 2026-11-24

## Contexto
O enem.dev vai até 2023. As provas de 2024 e 2025 só existem em PDF no INEP. O formato de cada questão (texto ou print
do caderno) já está decidido (ADR 0030). Falta definir:
- como as questões chegam ao banco sem que um erro de extração passe despercebido;
- de onde vêm o gabarito, a nota TRI e o assunto.

Rodar o extrator nos quatro cadernos (Azul, 1º e 2º dias de 2024 e 2025) mostrou erros **sem aviso** que a amostra
do piloto não pegava:
- páginas de largura inteira lidas como duas colunas (linhas cortadas ao meio);
- a última letra das linhas perdida na margem direita ("da" no lugar de "das");
- citações embaralhadas ("onível … Disp" no lugar de "Disponível");
- expoentes da linha de baixo dentro da linha de cima ("mo₋₁lar").

## Decisão
- **Extração** (`scripts/importar_prova_pdf.py`), com as correções acima e mais:
  - **Páginas de largura inteira:** o extrator procura o vão vazio entre as colunas.
  - **Texto comum a várias questões** ("Texto para as Questões de 06 a 10", em 2025): entra como print no começo
    de cada uma, porque as alternativas citam as linhas numeradas.
  - **Títulos de área e a página da redação** encerram a questão anterior.
  - **Print de toda questão**, para que qualquer uma possa trocar de texto para print na revisão.
  - **Duas redes de segurança** dão aviso (e, com ele, o print): texto que atravessa o vão entre as colunas e letra
    além da margem direita. Ambas foram testadas simulando os erros antigos.
- **Revisão humana** (`scripts/revisao_prova.py`): uma página local mostra o caderno ao lado da prévia, com o
  gabarito. Para cada questão, o autor escolhe **Texto**, **Print** ou **Fora**. Cada clique grava em
  `provas/<ano>-d<dia>/revisao.json`, que é **versionado** como registro da revisão. Os PDFs e a extração ficam
  fora do git (refazem-se com os scripts).
- **Importação** (`scripts/importar_prova_revisada.py`):
  - **Questão pendente não entra.** A opção `--sem-revisao` existe só para testar o app, avisa na saída e não deve
    gerar o pacote de dados.
  - **Questão anulada no gabarito oficial fica fora:** 129 de 2024; 123, 132 e 174 de 2025.
  - **Imagens:** ganham o prefixo `inep<ano>-`.
  - **Fonte:** gravada como `inep`.
  - **Id da questão:** o mesmo esquema fixo (ADR 0018).
- **TRI e assunto** (`scripts/importar_tri.py`, sem mudança de método):
  - **2024:** as notas passaram para `RESULTADOS_2024.csv`. No teste, todas as questões casaram com o caderno
    oficial e a escala conferiu (erro médio de 0,03 ponto).
  - **2025:** o casamento e o assunto funcionam, porque `ITENS_PROVA` abre normalmente. Mas `RESULTADOS_2025.csv`
    vem em Deflate64, que o Python não lê. Sem conferir a escala, 2025 entra **sem nota TRI**, como já acontece com
    anos que não conferem. A saída proposta é o pacote `inflate64`, só em `requirements-dev.txt`, e aguarda
    autorização.

## Consequências
- O que entra no banco foi visto por uma pessoa, e a decisão fica registrada no git.
- No teste, os dois anos somaram cerca de 30 MB de imagens ao pacote de dados, que hoje tem 77 MB. Esse valor muda
  com o que a revisão mandar para print.
- Um caderno de outro ano pode ter um layout novo. As redes de segurança e o recorte lado a lado na revisão são a
  defesa, e um layout que elas não reconheçam exige ajustar o extrator.
