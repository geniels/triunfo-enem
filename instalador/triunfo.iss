; Instalador da edição Estudante do TRIunfo (ADR 0017). Gerado por instalador/construir.py.
#ifndef Versao
  #define Versao "0.0.0"
#endif

[Setup]
AppId={{6F1C2E7A-9B4D-4E21-8C3A-7D5B2F1E9A60}
AppName=TRIunfo ENEM
AppVersion={#Versao}
AppVerName=TRIunfo ENEM {#Versao}
AppPublisher=Geniel Bonfim
AppPublisherURL=https://github.com/geniels/triunfo-enem
; Instala só para o usuário: não pede senha de administrador.
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\TRIunfo
DisableProgramGroupPage=yes
DisableDirPage=yes
OutputDir=..\dist
OutputBaseFilename=TRIunfo-Estudante-{#Versao}
SetupIconFile=..\build\triunfo.ico
UninstallDisplayIcon={app}\triunfo.ico
UninstallDisplayName=TRIunfo ENEM
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ShowLanguageDialog=no
; Fecha o TRIunfo aberto antes de atualizar.
CloseApplications=yes

[Languages]
Name: "pt"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "atalho"; Description: "Criar um atalho na Área de Trabalho"

[Files]
Source: "..\build\TRIunfo\*"; DestDir: "{app}"; Excludes: "data\enem.db"; Flags: recursesubdirs createallsubdirs ignoreversion
; O banco guarda o progresso do aluno: numa atualização, o existente é mantido.
Source: "..\build\TRIunfo\data\enem.db"; DestDir: "{app}\data"; Flags: onlyifdoesntexist uninsneveruninstall

[Icons]
Name: "{userprograms}\TRIunfo ENEM"; Filename: "{app}\python\python.exe"; Parameters: """{app}\triunfo.py"""; WorkingDir: "{app}"; IconFilename: "{app}\triunfo.ico"; Flags: runminimized
Name: "{userdesktop}\TRIunfo ENEM"; Filename: "{app}\python\python.exe"; Parameters: """{app}\triunfo.py"""; WorkingDir: "{app}"; IconFilename: "{app}\triunfo.ico"; Flags: runminimized; Tasks: atalho

[Run]
Filename: "{app}\python\python.exe"; Parameters: """{app}\triunfo.py"""; WorkingDir: "{app}"; Description: "Abrir o TRIunfo agora"; Flags: postinstall nowait skipifsilent runminimized

[UninstallDelete]
Type: filesandordirs; Name: "{app}\python"
Type: filesandordirs; Name: "{app}\app"

[Code]
// Ao desinstalar, pergunta se apaga o progresso do aluno. O padrão é manter (vale para reinstalar depois).
// Desinstalação silenciosa nunca apaga dados sem perguntar.
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usPostUninstall) and not UninstallSilent then
    if MsgBox('Apagar também suas respostas, redações e plano de estudos?' + #13#10#13#10 +
              'Escolha "Não" se pretende instalar o TRIunfo de novo e continuar de onde parou.',
              mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
      DelTree(ExpandConstant('{app}'), True, True, True);
end;
