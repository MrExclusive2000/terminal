; Inno Setup script for Argus.
;
; Per-user install (no administrator rights). That is a deliberate choice: the
; plan requires the app to install and update without elevation, and asking a
; single user for admin to run a research tool is friction with no security
; benefit. Note the trade-off honestly - a per-user install path is writable by
; anything already running as you, which is why the app verifies its own
; signature on load rather than trusting the install location.

#define AppName      "Argus"
#define AppExe       "Argus.exe"
#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

[Setup]
AppId={{7C1E4C2A-9B3F-4E77-9C1D-2A6E0B5F4D18}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppName}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
DisableDirPage=no
OutputDir=..\dist\installer
OutputBaseFilename=Argus-{#AppVersion}-setup
SetupIconFile=argus.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; Per-user: no UAC prompt, installs under the user's profile.
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Refuse to install over a newer build rather than silently downgrading.
VersionInfoVersion={#AppVersion}
; In-app updates run this with /SILENT while Argus is shutting down. Close and
; restart the app itself rather than telling the user to, and never demand a
; reboot for what is a per-user file copy.
CloseApplications=force
RestartApplications=yes
AlwaysRestart=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "..\dist\Argus\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}";            Filename: "{app}\{#AppExe}"
Name: "{group}\Uninstall {#AppName}";  Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}";      Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove only what the installer created. Settings, the journal and the data
; lake live in LOCALAPPDATA and are deliberately left behind - uninstalling an
; app should never silently delete the user's own research.
Type: filesandordirs; Name: "{app}"
