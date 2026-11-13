#define AppVersion "1.3.1"

[Setup]
AppId={{EAF472AB-2D52-4702-BA59-975A7794DAA1}
AppName=ClipForge Studio
AppVersion={#AppVersion}
AppPublisher=ClipForge
DefaultDirName={localappdata}\Programs\ClipForge
DefaultGroupName=ClipForge Studio
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..
OutputBaseFilename=ClipForge-Setup-{#AppVersion}
SetupIconFile=ClipForge.ico
UninstallDisplayIcon={app}\ClipForge.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
WizardSizePercent=115
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
VersionInfoDescription=ClipForge Studio Setup
VersionInfoVersion={#AppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a Desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: checkedonce

[Files]
Source: "ClipForge.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "ClipForge.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "bin\*"; DestDir: "{app}\bin"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "HUONG_DAN.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "FFMPEG_LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\ClipForge Studio"; Filename: "{app}\ClipForge.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\ClipForge Studio"; Filename: "{app}\ClipForge.exe"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{group}\Uninstall ClipForge Studio"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\ClipForge.exe"; Description: "Launch ClipForge Studio"; Flags: nowait postinstall skipifsilent
Filename: "{app}\ClipForge.exe"; Flags: nowait skipifnotsilent
