; Script Inno Setup : crée Setup_MaVideotheque.exe (installation classique)
; Installer Inno Setup gratuit : https://jrsoftware.org/isinfo.php
; Ouvre ce fichier avec Inno Setup puis clique sur Compiler (F9).

#define MonAppVersion "1.11.26"

[Setup]
AppName=Ma Vidéothèque
AppVersion={#MonAppVersion}
AppPublisher=FabR1
DefaultDirName={localappdata}\MaVideotheque
DefaultGroupName=Ma Vidéothèque
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=output
OutputBaseFilename=Setup_MaVideotheque_{#MonAppVersion}
SetupIconFile=logo.ico
UninstallDisplayIcon={app}\Videotheque.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "bureau"; Description: "Créer une icône sur le Bureau"; GroupDescription: "Raccourcis :"

[Files]
Source: "dist\Videotheque.exe"; DestDir: "{app}"; Flags: ignoreversion

; VLC portable inclus (dossier VLC en CI, ou vlc-3.0.21 en local)
#if DirExists("VLC")
Source: "VLC\*"; DestDir: "{app}\VLC"; Flags: ignoreversion recursesubdirs createallsubdirs
#elif DirExists("vlc-3.0.21")
Source: "vlc-3.0.21\*"; DestDir: "{app}\VLC"; Flags: ignoreversion recursesubdirs createallsubdirs
#endif

[Icons]
Name: "{group}\Ma Vidéothèque"; Filename: "{app}\Videotheque.exe"
Name: "{group}\Désinstaller Ma Vidéothèque"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Ma Vidéothèque"; Filename: "{app}\Videotheque.exe"; Tasks: bureau

[Run]
Filename: "{app}\Videotheque.exe"; Description: "Lancer Ma Vidéothèque"; Flags: nowait postinstall skipifsilent
