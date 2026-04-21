; Cadence — Inno Setup installer script
; Requires Inno Setup 6.x  →  https://jrsoftware.org/isdl.php
; Build order:  build.bat  (runs PyInstaller first, then calls ISCC on this file)

#define AppName      "Cadence"
#define AppVersion   "1.0.0"
#define AppPublisher "Cadence"
#define AppExeName   "Cadence.exe"
#define AppURL       "https://github.com/"

[Setup]
AppId={{A7C2E3F1-4D8B-4E9A-B2C3-1F5A6D7E8B9C}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}

; Install per-user by default — no admin required
DefaultDirName={localappdata}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes

; Output
OutputDir=dist
OutputBaseFilename=Cadence_Setup_{#AppVersion}
SetupIconFile=static\icon.ico
UninstallDisplayIcon={app}\{#AppExeName}

; Compression
Compression=lzma2/ultra64
SolidCompression=yes

; No admin rights needed (per-user install)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Windows 10+ only
MinVersion=10.0

; Wizard appearance
WizardStyle=modern
WizardSmallImageFile=static\icon.ico

; Architecture
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";  Description: "Create a &desktop shortcut";         GroupDescription: "Additional shortcuts:"; Flags: unchecked
Name: "startuprun";   Description: "Launch Cadence when Windows &starts"; GroupDescription: "Startup:";             Flags: unchecked

[Files]
; Everything PyInstaller produced
Source: "dist\Cadence\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu
Name: "{group}\{#AppName}";           Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"

; Desktop (optional task)
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

; Startup (optional task)
Name: "{userstartup}\{#AppName}";   Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: startuprun

[Run]
; Offer to launch after install
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName} now"; \
  Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove runtime caches left by the app
Type: filesandordirs; Name: "{app}\__pycache__"
Type: files;          Name: "{app}\*.log"

[Code]
// On uninstall, ask whether to keep cadence.db and config.txt.
function InitializeUninstall(): Boolean;
var
  Res: Integer;
begin
  Result := True;
  Res := SuppressibleMsgBox(
    'Do you want to keep your Cadence data?' + #13#10 + #13#10 +
    'Click YES to keep your student records, invoices, and settings.' + #13#10 +
    'Click NO to delete all Cadence data when uninstalling.',
    mbConfirmation, MB_YESNO, IDYES);
  if Res = IDNO then
  begin
    // User chose to delete data — remove data files after uninstall
    DeleteFile(ExpandConstant('{app}\cadence.db'));
    DeleteFile(ExpandConstant('{app}\cadence.db-journal'));
    DeleteFile(ExpandConstant('{app}\cadence.db-wal'));
    DeleteFile(ExpandConstant('{app}\cadence.db-shm'));
    DeleteFile(ExpandConstant('{app}\config.txt'));
  end;
end;
