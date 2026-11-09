# 0021. Instalador gerado no GitHub Actions, pronto para assinatura

- **Status:** Aceita
- **Data:** 2026-11-08

## Contexto
A assinatura gratuita para código aberto (SignPath Foundation) exige que o arquivo assinado seja gerado no GitHub
Actions, em servidores do GitHub, para provar que veio do código público. Até aqui o instalador era gerado no PC do
autor.

## Decisão
- Workflow `.github/workflows/instalador.yml` em `windows-latest`: instala Python 3.12.10 e Inno Setup, roda os
  testes, baixa o **pacote de dados** e roda `instalador/construir.py`.
- **Pacote de dados** (`dados.zip`: questões, imagens, parâmetros TRI e marcas de importação) publicado como
  **versão-prévia** `dados-AAAA.N`, para não ser confundido com uma versão do programa pelo aviso de atualização
  (que só olha a versão mais recente não-prévia). Questões novas: gerar um pacote novo e trocar `DADOS` no workflow.
- Roda à mão (Actions → Instalador) e ao publicar uma versão `v*`, anexando o instalador e o SHA-256 a ela.
- A assinatura pela SignPath fica **desligada** até existirem a variável `SIGNPATH_ORGANIZATION_ID` e o segredo
  `SIGNPATH_API_TOKEN` (passo a passo em `docs/ASSINATURA.md`).

## Consequências
- O build fica reproduzível e independente do PC do autor.
- O instalador anexado pelo workflow substitui (`--clobber`) o que tiver sido enviado do PC do autor.
- Ponto em aberto: assinar também o desinstalador embutido (ver `docs/ASSINATURA.md`).
