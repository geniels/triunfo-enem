# 0027. Cadeia de build protegida: ações fixadas, menor permissão e hash de tudo

- **Status:** Aceita
- **Data:** 2026-11-12
- **Complementa:** ADR 0021 (build no GitHub Actions) e 0019 (atualização em 1 clique)

## Contexto
O agente de segurança da revisão geral (2026-11-11) apontou que o SHA-256 publicado junto com o instalador só pega
arquivo **corrompido**, e não arquivo **trocado**. Quem conseguir alterar o build publica um instalador envenenado
com o hash "certo", e o programa o instala sozinho na atualização em 1 clique. As brechas eram:
- ações do GitHub referenciadas por tag (`@v5`), que o dono da ação pode mover para outro código;
- `contents: write` no workflow inteiro, inclusive nos passos que rodam código de terceiros;
- downloads sem hash conhecido: Python embutido, `dados.zip`, dependências do pip (inclusive as indiretas) e Inno
  Setup sem versão fixa.

## Decisão
- **Ações fixadas pelo SHA do commit**, com a tag num comentário (`actions/checkout@fbc6f39… # v5`). Para atualizar
  uma ação, conferir o novo SHA (`gh api repos/<ação>/commits/<tag> -q .sha`) e trocar.
- **Dois jobs:** `construir` só com `contents: read` (roda testes, pip, Inno Setup e a SignPath) e `anexar`, o único
  com `contents: write`, que só baixa o pacote pronto e o anexa à versão, sem rodar código do projeto.
- **Hash conhecido de tudo o que é baixado:**
  - `dados.zip`: `DADOS_SHA256` no workflow, trocado junto com `DADOS`;
  - Python embutido: `PY_SHA256` em `instalador/construir.py` (o de 3.12.10 conferido pelo MD5 do python.org);
  - dependências: `instalador/requirements-lock.txt`, com versão e hash das 12 bibliotecas, instaladas com
    `pip --require-hashes --only-binary=:all:`. Um teste garante que ela acompanha o `requirements.txt`;
  - Inno Setup: versão fixa (`INNOSETUP` no workflow).
- **Atualizar as dependências:** mudar o `requirements.txt` e regerar a lista travada, baixando as wheels para
  Windows/CPython 3.12 (`pip download -r requirements.txt --only-binary=:all: --platform win_amd64 --python-version 3.12
  --implementation cp -d <pasta>`) e escrevendo `nome==versão --hash=sha256:<hash>` de cada uma.

## Avaliado e adiado: assinatura Ed25519 do `.sha256`
Assinar o arquivo de hash com uma chave privada fora do GitHub, com a chave pública dentro do programa, provaria
que a versão veio do autor. Para um autor sozinho, porém, a chave teria de ficar no PC dele (e o build passaria a
depender desse PC, contra a ADR 0021) ou no próprio GitHub (o que não protege contra quem domina o GitHub). A
assinatura Authenticode pela SignPath (ADR 0021, `docs/ASSINATURA.md`), vinculada ao build público, resolve a
autenticidade de forma verificável pelo próprio Windows. Reavaliar se a SignPath não aprovar o projeto.

## Consequências
- Atualizar uma ação, o Python, o Inno Setup, o pacote de dados ou uma dependência passa a ser uma mudança explícita
  no repositório, com hash.
- O build fica um pouco mais trabalhoso de atualizar, e bem mais difícil de adulterar sem que alguém perceba.
