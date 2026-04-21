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
// Ask the user whether to keep their data (cadence.db, config.txt) on uninstall.
var
  KeepDataPage: TInputOptionWizardPage;

procedure InitializeWizard();
begin
  if WizardForm <> nil then
  begin
    KeepDataPage := CreateInputOptionPage(
      wpReady,
      'Existing Data',
      'Cadence found a previous installation.',
      'What would you like to do with your existing data?',
      True, False,
      ['Keep my data (students, invoices, settings)',
       'Remove all data when uninstalling']);
    KeepDataPage.Values[0] := True;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{app}');
    // Only delete data files if user chose "Remove all data"
    if not KeepDataPage.Values[0] then
    begin
      DeleteFile(DataDir + '\cadence.db');
      DeleteFile(DataDir + '\cadence.db-journal');
      DeleteFile(DataDir + '\cadence.db-wal');
      DeleteFile(DataDir + '\cadence.db-shm');
      DeleteFile(DataDir + '\config.txt');
    end;
  end;
end;
