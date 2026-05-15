; ============================================
; OpenBL3CMM Inno Setup Installer Script
; ============================================
; Requirements: Inno Setup 6+ (https://jrsoftware.org/isinfo.php)
;
; Usage:
;   1. Build the EXE first: python -m PyInstaller --clean OpenBL3CMM.spec
;   2. Open this .iss file in Inno Setup Compiler
;   3. Click Build > Compile
;   4. Output: Output\OpenBL3CMM_Setup.exe

#define MyAppName "OpenBL3CMM"
#define MyAppVersion "1.0"
#define MyAppPublisher "Ty-Gone"
#define MyAppURL "https://github.com/mantorofficial/OpenBL3CMM"
#define MyAppExeName "OpenBL3CMM.exe"

[Setup]
AppId={{B3CMM-OPEN-BL3-HOTFIX-EDITOR}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=Output
OutputBaseFilename=OpenBL3CMM_Setup_v{#MyAppVersion}
SetupIconFile=openbl3cmm.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
WizardSizePercent=120
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DisableProgramGroupPage=yes
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "associatebl3hotfix"; Description: "Associate .bl3hotfix files with {#MyAppName}"; GroupDescription: "File associations:"
Name: "associateblmod"; Description: "Associate .blmod files with {#MyAppName}"; GroupDescription: "File associations:"

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "openbl3cmm.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKA; Subkey: "Software\Classes\.bl3hotfix"; ValueType: string; ValueData: "OpenBL3CMM.bl3hotfix"; Flags: uninsdeletevalue; Tasks: associatebl3hotfix
Root: HKA; Subkey: "Software\Classes\OpenBL3CMM.bl3hotfix"; ValueType: string; ValueData: "BL3 Hotfix Mod"; Flags: uninsdeletekey; Tasks: associatebl3hotfix
Root: HKA; Subkey: "Software\Classes\OpenBL3CMM.bl3hotfix\DefaultIcon"; ValueType: string; ValueData: "{app}\openbl3cmm.ico"; Tasks: associatebl3hotfix
Root: HKA; Subkey: "Software\Classes\OpenBL3CMM.bl3hotfix\shell\open\command"; ValueType: string; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: associatebl3hotfix
Root: HKA; Subkey: "Software\Classes\.blmod"; ValueType: string; ValueData: "OpenBL3CMM.blmod"; Flags: uninsdeletevalue; Tasks: associateblmod
Root: HKA; Subkey: "Software\Classes\OpenBL3CMM.blmod"; ValueType: string; ValueData: "BL3 Mod File"; Flags: uninsdeletekey; Tasks: associateblmod
Root: HKA; Subkey: "Software\Classes\OpenBL3CMM.blmod\DefaultIcon"; ValueType: string; ValueData: "{app}\openbl3cmm.ico"; Tasks: associateblmod
Root: HKA; Subkey: "Software\Classes\OpenBL3CMM.blmod\shell\open\command"; ValueType: string; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: associateblmod
; .bl3hotfix association
Root: HKCR; Subkey: ".bl3hotfix"; ValueType: string; ValueName: ""; ValueData: "OpenBL3CMM.bl3hotfix"; Flags: uninsdeletevalue
Root: HKCR; Subkey: "OpenBL3CMM.bl3hotfix"; ValueType: string; ValueName: ""; ValueData: "BL3 Hotfix Mod"; Flags: uninsdeletekey
Root: HKCR; Subkey: "OpenBL3CMM.bl3hotfix\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\OpenBL3CMM.exe,0"
Root: HKCR; Subkey: "OpenBL3CMM.bl3hotfix\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\OpenBL3CMM.exe"" ""%1"""

; .blmod association
Root: HKCR; Subkey: ".blmod"; ValueType: string; ValueName: ""; ValueData: "OpenBL3CMM.blmod"; Flags: uninsdeletevalue
Root: HKCR; Subkey: "OpenBL3CMM.blmod"; ValueType: string; ValueName: ""; ValueData: "BL3 Mod File"; Flags: uninsdeletekey
Root: HKCR; Subkey: "OpenBL3CMM.blmod\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\OpenBL3CMM.exe,0"
Root: HKCR; Subkey: "OpenBL3CMM.blmod\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\OpenBL3CMM.exe"" ""%1"""

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Dirs]
Name: "{localappdata}\Programs\OpenBL3CMM"
Name: "{localappdata}\Programs\OpenBL3CMM\backups"
Name: "{localappdata}\Programs\OpenBL3CMM\datapacks"
Name: "{localappdata}\Programs\OpenBL3CMM\mods"

[Code]
function InitializeSetup(): Boolean;
var
  UninstallKey: String;
  UninstallString: String;
  ResultCode: Integer;
begin
  Result := True;
  UninstallKey := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#SetupSetting("AppId")}_is1';
  if RegQueryStringValue(HKCU, UninstallKey, 'UninstallString', UninstallString) then
  begin
    if MsgBox('An older version of {#MyAppName} is already installed. Would you like to uninstall it first?',
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      Exec(RemoveQuotes(UninstallString), '/SILENT', '', SW_SHOW, ewWaitUntilTerminated, ResultCode);
    end;
  end;
end;
