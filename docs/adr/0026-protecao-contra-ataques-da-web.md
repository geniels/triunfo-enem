# 0026. Proteção contra ataques vindos de sites da internet

- **Status:** Aceita
- **Data:** 2026-11-11
- **Complementa:** ADR 0010 (servidor só em 127.0.0.1), 0022 e 0025 (acesso pela rede)

## Contexto
A revisão geral (agentes de segurança e de revisão de código e `/ponytail-audit`) mostrou que "só o próprio PC
alcança o 127.0.0.1" não basta. O navegador do aluno pode ser usado por **outro site** aberto no mesmo PC:
- **CSRF:** um site envia `POST http://127.0.0.1:<porta>/api/turma/abrir` (ou trocar PIN, entregar simulado, gravar
  respostas). O navegador envia sem perguntar, e o servidor local não tem login.
- **DNS rebinding:** um domínio externo passa a apontar para 127.0.0.1. Para o navegador, a página fica sendo da
  "mesma origem" e consegue **ler** redações, progresso e a lista da turma (LGPD, ADR 0011).
- **Clickjacking:** a tela de Configurações dentro de um iframe invisível.
- **XSS no Markdown:** imagem e link aninhados no texto de uma questão ou do guia escapavam do atributo `alt` e
  rodavam código na página.

## Decisão
- **Um middleware** (`protecao_e_cache` em `app/main.py`), nos dois servidores (local e da turma):
  - `Host` precisa ser um endereço IP ou `localhost`. O DNS rebinding depende de um nome de domínio, então é recusado (400).
  - Pedidos que alteram dados (não GET, HEAD ou OPTIONS) com `Sec-Fetch-Site: cross-site` ou `Origin` diferente de
    `http://<Host>` são recusados (403). Pedidos sem `Origin`, que não vêm de navegador, passam.
  - Cabeçalhos em toda resposta: CSP (`script-src 'self'` mais o hash do único script dentro do `index.html`, calculado
    ao iniciar; `img-src 'self' data:`; `frame-ancestors 'none'`), `X-Frame-Options: DENY`, `nosniff` e
    `Referrer-Policy: no-referrer`.
- **Markdown:** imagens e links viram marcadores antes das outras trocas e só voltam como HTML no fim. Colchetes não
  são aceitos no texto alternativo nem no texto do link. Só imagens locais (`/imagens/`), coerente com o modo offline
  (ADR 0002).
- A checagem "o pedido veio pela rede" (`pela_turma`) passa a usar a **faixa de portas** da turma, e não o estado
  atual. Ao fechar a turma, um pedido em andamento não vira administrador.

## Consequências
- Testes em `tests/test_api.py` (DNS rebinding, CSRF e cabeçalhos por HTTP de verdade) falham no código anterior.
- Uma tela nova não pode usar `onclick="..."` nem `<script>` dentro do HTML (a CSP bloqueia). Use `addEventListener`.
  `style="..."` continua permitido.
- Se o script do `index.html` mudar, o hash é recalculado sozinho ao iniciar.
