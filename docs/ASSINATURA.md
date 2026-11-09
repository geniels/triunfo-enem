# Assinatura digital do instalador: passo a passo

**Por quê:** sem assinatura, o Windows mostra "O Windows protegeu o computador" e, com o **Controle Inteligente de
Aplicativos** ligado (Windows 11), pode **bloquear** o programa sem opção de continuar. No PC de referência, isso
aconteceu com o desinstalador (ADR 0017).

**Caminho escolhido:** [SignPath Foundation](https://signpath.org/), gratuita para projetos de código aberto.
O TRIunfo já cumpre os requisitos técnicos: repositório público, licença aberta (MIT) e instalador gerado no
GitHub Actions (`.github/workflows/instalador.yml`, ADR 0021).

## 1. Candidatar o projeto (o autor faz)

1. Acesse <https://signpath.org/> e procure o formulário de candidatura (*apply*).
2. Informe:
   - Repositório: `https://github.com/geniels/triunfo-enem`
   - Licença: MIT
   - O que é: plataforma gratuita e offline de estudo para o ENEM, para estudantes do ensino médio
   - O que será assinado: `TRIunfo-Estudante-<versão>.exe`, gerado pelo workflow `Instalador` no GitHub Actions
3. A aprovação é a critério da fundação e pode levar algum tempo. O certificado fica em nome da fundação, que
   aparece como editor ("SignPath Foundation") junto com o nome do projeto.

## 2. Depois de aprovado (o autor faz, com ajuda)

1. Instale o **GitHub App da SignPath** no repositório `geniels/triunfo-enem`, como indicado por eles.
2. No painel da SignPath, confira ou crie:
   - projeto com o *slug* `triunfo-enem`;
   - política de assinatura `release-signing`;
   - configuração de artefato `instalador`, que assina o arquivo `.exe` de dentro do artefato `instalador`.
3. No GitHub (Settings → Secrets and variables → Actions):
   - **Variable** `SIGNPATH_ORGANIZATION_ID` = o ID da organização na SignPath;
   - **Secret** `SIGNPATH_API_TOKEN` = o token gerado na SignPath. Nunca coloque o token num arquivo do repositório.
4. Confira no [guia da SignPath para GitHub](https://docs.signpath.io/trusted-build-systems/github) a versão atual
   da ação `signpath/github-action-submit-signing-request` e ajuste o `@v1` do workflow, se preciso.

A partir daí, cada versão publicada (`gh release create vX.Y.Z`) dispara o workflow, que gera, assina e anexa o
instalador assinado, com o SHA-256 recalculado.

## 3. Ponto em aberto: o desinstalador

O arquivo bloqueado no teste foi o **desinstalador** (`unins000.exe`), que o Inno Setup gera de dentro do
instalador. Assinar só o instalador talvez não assine o desinstalador. Opções a confirmar com a SignPath:

- **Assinatura em duas etapas:** o Inno Setup aceita um desinstalador já assinado (`SignedUninstaller` e
  `SignedUninstallerDir`). O workflow geraria o desinstalador, mandaria assinar e montaria o instalador final.
- Perguntar à SignPath se a configuração de artefato pode assinar o desinstalador embutido.

## Alternativas

| Caminho | Quando faz sentido |
|---|---|
| Certificado **Certum Open Source** (pago, em nome do autor) | Se a SignPath não aprovar ou demorar |
| Certificado **ICP-Brasil** de uma escola, secretaria ou do MEC | Quando o TRIunfo for adotado por uma instituição |

Em todos os casos o SmartScreen ainda constrói "reputação" com o tempo: a assinatura evita o bloqueio e mostra quem
publicou, mas não garante zero avisos no primeiro dia.
