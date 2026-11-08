# 0010. Duas edições: Estudante e Escola

- **Status:** Aceita
- **Data:** 2026-11-08

## Contexto
Quem usa o TRIunfo são estudantes do ensino médio. Eles não têm, nem precisam ter, conhecimento técnico para
administrar um sistema: instalar dependências, configurar chaves de API, abrir terminal ou resolver erros. Ao mesmo
tempo, uma escola tem professores ou um responsável pelo laboratório que podem configurar algo uma vez para todos.

## Decisão
O mesmo código terá duas edições, com responsabilidades diferentes:

| | **Estudante** | **Escola** |
|---|---|---|
| Quem instala | O próprio aluno ou a família | Professor ou responsável pelo laboratório |
| Administração | **Nenhuma.** Instalar, abrir e usar | Configura uma vez: rede local, turmas, recursos opcionais |
| Onde roda | No PC do aluno, só para ele (`127.0.0.1`) | Um PC serve a sala pela rede (Fase 4) |
| Correção por IA | Só local (offline), opcional | Local, ou online com conta paga da escola (ADR 0011) |
| Atualizações | Botão "Verificar atualizações" e, com o instalador, aplicação em 1 clique (ADR 0012) | Feita pelo responsável |

Regras para a edição Estudante:
- Nunca exigir terminal, chave de API, edição de arquivo ou qualquer configuração técnica.
- Toda mensagem de erro precisa dizer **o que o aluno faz** em seguida, em linguagem simples.
- Tudo funciona offline; a internet é opcional e só usada quando o aluno pede.

## Consequências
- O instalador `.exe` (Fase 5) é pré-requisito real da edição Estudante: o `iniciar.bat` atual ainda exige o Python
  instalado, o que é aceitável para testes, mas não para o aluno final.
- Recursos "de administrador" (chave de IA online, rede, turmas) ficam fora da edição Estudante.
