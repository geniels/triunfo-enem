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
| **agent-skills** (Addy Osmani) | Plugin, escopo do usuário | Roteiros de engenharia e 4 agentes: code-reviewer, security-auditor, test-engineer, web-performance-auditor | Útil a partir da Fase 2 (testes, segurança do modo escola) |
| **ponytail** | Plugin, escopo do usuário | Força soluções mínimas (stdlib primeiro, sem abstrações desnecessárias) | Alinhado com a ADR 0002. Hooks rodam localmente; webhook desligado |
| **graphify** | CLI (`uv tool`), skill global | Grafo do código, gerado 100% offline (`--code-only`) | Pouco valor hoje (6 arquivos de código). Reavaliar quando o código crescer. **Hook de leitura não instalado** |

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
