# 0002. App web local e offline (Python + SQLite + JS puro)

- **Status:** Aceita
- **Data:** 2026-11-08

## Contexto
O público são estudantes do ensino médio, muitos com internet ruim ou pacote de dados limitado, e
computadores modestos (a máquina de desenvolvimento é um i3-N305 com 8 GB de RAM, típica do público).
Queremos também que **um PC sirva uma sala inteira** pela rede local, inclusive para celulares.

Opções consideradas:
1. App desktop nativo (Electron, Tauri): instalador pesado, não serve outros aparelhos da sala.
2. Site na nuvem: exige internet e hospedagem paga.
3. **Servidor local + navegador**: um processo leve que serve a interface para o próprio PC ou para a rede.

## Decisão
- **Backend:** Python 3.12 + FastAPI + Uvicorn. Duas dependências apenas.
- **Banco:** SQLite em um único arquivo (`data/enem.db`), em modo WAL.
- **Frontend:** HTML, CSS e JavaScript puros, **sem CDN, sem framework e sem etapa de build**.
  Nada carrega da internet em tempo de uso, incluindo as fontes (usamos a fonte do sistema).
- **Execução:** `iniciar.bat` cria o ambiente, importa as questões na primeira vez e abre o navegador.
- Por segurança, o servidor escuta só em `127.0.0.1`. O modo escola (rede local) abrirá em `0.0.0.0`
  com uma opção explícita e terá sua própria ADR.
- A tabela `respostas` já tem `aluno_id` (padrão 1) para o modo escola não exigir migração difícil.

## Consequências
- Roda em qualquer PC com Python; no futuro, empacotar como `.exe` (PyInstaller) ou em Raspberry Pi.
- Sem framework JS, telas complexas exigem mais disciplina. Se o frontend crescer muito, reavaliar
  (com nova ADR), preferindo opções sem build.
- Dados gerados (`data/`) não vão para o Git; cada instalação os gera pelo importador.
