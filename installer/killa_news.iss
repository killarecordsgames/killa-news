; Installatore di KILLA NEWS per Inno Setup 6 (versione passata da GitHub Actions con /DAppVersion=x.y.z) (https://jrsoftware.org/isinfo.php)
; Compilazione: eseguire prima CREA_INSTALLER.bat (che crea dist\KillaNews e poi richiama ISCC).
; La procedura guidata di Inno Setup è leggibile con NVDA (controlli standard di Windows).

#define AppName "KILLA NEWS"
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#define AppPublisher "Killa Records"
#define AppExe "KillaNews.exe"

[Setup]
AppId={{4408A067-9003-4FC3-BCD4-58F5B3ED20C4}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppComments=L'informazione, senza barriere.
DefaultDirName={autopf}\Killa Records\KILLA NEWS
DefaultGroupName=KILLA NEWS
DisableDirPage=no
DisableProgramGroupPage=no
AllowNoIcons=yes
OutputDir=..\dist
OutputBaseFilename=KillaNews_Installazione
SetupIconFile=..\assets\killa_news.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
CloseApplications=yes
RestartApplications=no
Compression=lzma2
SolidCompression=yes
WizardStyle=classic
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

[Tasks]
Name: "desktopicon"; Description: "Crea un collegamento sul &desktop"; GroupDescription: "Collegamenti aggiuntivi:"; Flags: unchecked

[Files]
Source: "..\dist\KillaNews\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\CHECKLIST_NVDA.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\KILLA NEWS"; Filename: "{app}\{#AppExe}"; Comment: "L'informazione, senza barriere."
Name: "{group}\Leggimi di KILLA NEWS"; Filename: "{app}\README.md"
Name: "{group}\Disinstalla KILLA NEWS"; Filename: "{uninstallexe}"
Name: "{autodesktop}\KILLA NEWS"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Avvia KILLA NEWS ora"; Flags: nowait postinstall skipifsilent
; Dopo un aggiornamento automatico (installazione silenziosa) KILLA NEWS si riapre da solo
Filename: "{app}\{#AppExe}"; Flags: nowait runasoriginaluser; Check: WizardSilent

; I dati personali (preferiti, cronologia, archivio offline) sono in %APPDATA%\KillaNews e
; NON vengono cancellati dalla disinstallazione, così una nuova installazione li ritrova.
