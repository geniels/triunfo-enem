# 0003. Questões do enem.dev, com correções e imagens locais

- **Status:** Aceita
- **Data:** 2026-11-08

## Contexto
O INEP publica provas e gabaritos apenas em PDF. Extrair questões de PDFs (texto, imagens e fórmulas)
é trabalhoso e propenso a erro. O projeto comunitário **enem.dev** já oferece as questões de 2009 a 2023
estruturadas em JSON, com uso dos dados liberado.

Ao importar, encontramos problemas na fonte:
- **Área errada:** a classificação por disciplina vem inconsistente (em 2010, só 7 questões apareciam como Linguagens).
- **Idioma:** a API devolve só uma língua estrangeira por chamada, por padrão o espanhol.
- **Limite de requisições:** a API responde 429 se receber muitas chamadas seguidas.
- **Imagens:** ficam hospedadas no enem.dev; 6 questões têm imagem faltando na própria fonte.

## Decisão
- Importar do enem.dev com `scripts/importar_enem_dev.py`, que pode ser rodado de novo sem duplicar nada.
- **Área pela numeração oficial**, que é fixa e confiável:
  - 2009–2016: 1–45 Humanas · 46–90 Natureza · 91–135 Linguagens · 136–180 Matemática
  - 2017 em diante: 1–45 Linguagens · 46–90 Humanas · 91–135 Natureza · 136–180 Matemática
- Buscar cada prova **uma vez por idioma** (`language=ingles|espanhol`) e guardar `idioma` ('' quando a questão é comum aos dois).
- Pausa de 0,5 s entre páginas e novas tentativas com espera crescente.
- **Baixar todas as imagens** para `data/imagens/` (cerca de 72 MB) e reescrever os links para `/imagens/...`.
  Imagens quebradas aparecem como "imagem indisponível na fonte".
- O gabarito **nunca** é enviado ao navegador antes da resposta (`/api/questao` não o inclui).

## Consequências
- Resultado verificado: 2.749 questões, 45 por área por ano (a fonte não tem algumas), inglês e espanhol completos.
- As provas de 2024 e 2025 não estão no enem.dev. Precisarão de um importador próprio a partir dos PDFs do INEP
  (Fase 5), com revisão humana.
- 7 questões vêm da fonte sem a alternativa E (2011/180, 2013/64, 2016/47, 2021/105, 2021/175, 2022/144, 2022/166;
  conferido de novo em 2026-11-11). O gabarito está entre as presentes, e a tela avisa. Recuperar a E exigiria os PDFs do INEP.
- O importador ignora gabarito ou alternativa com letra fora de A–E (a letra entra no HTML e decide o acerto).
- Se o enem.dev mudar o formato ou sair do ar, o banco já baixado continua funcionando, e o importador precisará de ajuste.
