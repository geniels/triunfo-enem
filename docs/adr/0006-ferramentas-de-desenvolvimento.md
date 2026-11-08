# 0006. Ferramentas de desenvolvimento com agentes de IA

- **Status:** Aceita
- **Data:** 2026-11-08

## Contexto
O desenvolvimento é feito com o Claude Code no VS Code. Avaliamos ferramentas externas para o agente
(skills, plugins e CLIs) pelo critério: **ajuda este projeto agora, e é segura?** Antes de instalar,
lemos os hooks e scripts de cada uma.

## Decisão

| Ferramenta | Onde está | Para que usamos | Avaliação |
|---|---|---|---|
| **playwright-cli** (Microsoft) | CLI global (npm) e skill em `.claude/skills/playwright-cli` | Abrir o app no Chrome, clicar e tirar capturas, em desktop e celular | Essencial. Achou e confirmou correções reais |
| **ui-ux-pro-max** | Skill em `.claude/skills/ui-ux-pro-max` (só a skill principal, sem testes) | Auditoria de UX e acessibilidade por regras (`--domain ux`) | Útil na auditoria. A geração de design system acertou só a paleta e errou o estilo (sugeriu visual infantil e "AI-native"); **não persistir** a saída sem validar |
| **agent-skills** (Addy Osmani) | Plugin, escopo do usuário | Roteiros de engenharia e 4 agentes: code-reviewer, security-auditor, test-engineer, web-performance-auditor | Útil. O agente code-reviewer achou 10 problemas reais em 2026-11-08 (5 corrigidos, o resto no ROADMAP). Inclui `interview-me`, que cobre o "grill me" |
| **ponytail** | Plugin, escopo do usuário | Força soluções mínimas; `/ponytail-audit` audita o repositório | Útil. A auditoria coincidiu com a revisão nos itens críticos. Hooks rodam localmente; webhook desligado |
| **graphify** | CLI (`uv tool`), skill global | Grafo do código, gerado 100% offline (`--code-only`) | Pouco valor hoje (6 arquivos de código). Reavaliar quando o código crescer. **Hook de leitura não instalado** |

Avaliadas e **não instaladas** (2026-11-08):
- **grill-me** (mattpocock/skills): entrevista o usuário sobre um plano antes de codar. Duplica o `interview-me`
  do agent-skills, que já responde a "grill me".
- **design-taste-frontend** (Leonxlnx/taste-skill): "anti-slop" visual voltado a landing pages e portfólios. O próprio
  projeto diz que não é para dashboards nem interfaces de produto, que é o nosso caso, e costuma puxar fontes web e
  animações, o que conflita com o modo offline (ADR 0002). Reavaliar se houver uma página de divulgação.

Uso:
```powershell
playwright-cli open http://localhost:8000      # testar a interface
python .claude/skills/ui-ux-pro-max/scripts/search.py "<tema>" --domain ux
graphify extract . --code-only; graphify cluster-only . --no-label   # gera graphify-out/
```

## Consequências
- Novas ferramentas passam pela mesma avaliação (o que faz, hooks, rede, custo de contexto) e entram nesta tabela.
- Os plugins de escopo do usuário não ficam no repositório; colaboradores instalam se quiserem.
- `graphify-out/` e `.playwright-cli/` estão no `.gitignore`.
