# 0008. Guia da prova em Markdown, sincronizável sob demanda

- **Status:** Aceita
- **Data:** 2026-11-08

## Contexto
As regras do ENEM mudam todo ano com um novo **edital**. O app é offline (ADR 0002), mas o aluno precisa das regras
do ano dele. Reinstalar o app a cada edital não é realista para escolas.

## Decisão
- O guia fica em **`app/conteudo/guia.md`**, com um cabeçalho:
  ```
  ---
  versao: 2026.1
  edital: Edital nº 64, de 21 de maio de 2026 (ENEM 2026)
  atualizado: 2026-11-08
  ---
  ```
  Cada `## Título` é uma seção. A **primeira seção é "Regras de ouro"**, que também aparece na tela inicial.
- Em **Configurações → Verificar atualização**, o servidor baixa
  `raw.githubusercontent.com/geniels/triunfo-enem/main/app/conteudo/guia.md`. **Só grava** em `data/guia.md` se:
  tiver o cabeçalho com `versao` numérica e `edital`, tiver ao menos uma seção, tiver no máximo 200 KB e for de
  **versão maior** que a atual. Caso contrário, nada muda.
- O app usa sempre o mais novo entre o embutido e o baixado: uma atualização do app traz um guia novo mesmo sem sincronizar.
- O conteúdo é exibido pelo mesmo renderizador seguro das questões (escapa todo HTML; links só `https://` ou `#rota`).
  Mesmo que o arquivo remoto fosse adulterado, ele não executaria código no navegador.
- O servidor envia `Cache-Control: no-cache`, para o navegador não mostrar uma versão antiga do app depois de uma atualização.

## Como publicar o guia de um novo edital
1. Edite `app/conteudo/guia.md`: textos, itens do edital, e **aumente `versao`** (ex.: `2027.1`).
2. Rode os testes: `.venv\Scripts\python.exe -m unittest discover tests`.
3. Faça commit e push na `main`. Todos os TRIunfo que tocarem em "Verificar atualização" passam a ter o guia novo.

## Consequências
- Só a sincronização usa a internet, e só quando o aluno pede. Nenhum dado do aluno é enviado.
- Quem publica na `main` do repositório controla o guia de todos; proteger a branch quando houver mais colaboradores.
- No futuro, o mesmo mecanismo pode trazer temas de redação novos e as provas de cada ano.
