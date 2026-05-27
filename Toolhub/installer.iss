#define MyAppName "MLK-II ALVT"
#ifndef MyAppVersion
  #define MyAppVersion "16.1.27"
#endif
#define MyAppPublisher "Ashish Dixit"
#define MyAppExeName "MLK-II_ALVT.exe"

[Setup]
AppId={{MLK-II-ALVT-TOOL}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=installer_output
OutputBaseFilename=MLK-II_ALVT_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\{#MyAppExeName}
WizardImageFile=app_icon.png
WizardSmallImageFile=ide_icon.png
SetupIconFile=icon.ico
ChangesAssociations=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Components]
Name: "main"; Description: "MLK-II ALVT Tool (Main Validator & Hub)"; Types: full compact custom; Flags: fixed
Name: "ide"; Description: "MLK-II IDE (Microlok II Development)"; Types: full custom
Name: "pdf_editor"; Description: "PDF Editor (Merge, Split, Edit PDFs)"; Types: full custom
Name: "miss_converter"; Description: "MISS Converter (Convert & Compile MISS)"; Types: full custom
Name: "logic_cad"; Description: "Logic to AutoCAD Converter"; Types: full custom

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\MLK-II_ALVT\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "ide_icon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "pdf_editor.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "logic_cad.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "miss.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "app_icon.png"; DestDir: "{app}"; Flags: ignoreversion
Source: "ide_icon.png"; DestDir: "{app}"; Flags: ignoreversion

[InstallDelete]
Type: files; Name: "{autodesktop}\MLK-II ALVT Tool.lnk"
Type: files; Name: "{group}\MLK-II ALVT Tool.lnk"
Type: files; Name: "{autodesktop}\MLK-II ALVT.lnk"
Type: files; Name: "{group}\MLK-II ALVT.lnk"

[Icons]
Name: "{group}\MLK-II ALVT"; Filename: "{app}\MLK-II_ALVT.exe"; IconFilename: "{app}\icon.ico"; Components: main
Name: "{group}\MLK-II IDE"; Filename: "{app}\MLK-II_IDE.exe"; IconFilename: "{app}\ide_icon.ico"; Components: ide
Name: "{group}\PDF Editor"; Filename: "{app}\PDFEditor.exe"; IconFilename: "{app}\pdf_editor.ico"; Components: pdf_editor
Name: "{group}\MISS Converter"; Filename: "{app}\MISS_Converter.exe"; IconFilename: "{app}\miss.ico"; Components: miss_converter
Name: "{group}\Logic to AutoCAD"; Filename: "{app}\LogicToEquivalent.exe"; IconFilename: "{app}\logic_cad.ico"; Components: logic_cad
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

Name: "{autodesktop}\MLK-II ALVT"; Filename: "{app}\MLK-II_ALVT.exe"; IconFilename: "{app}\icon.ico"; Components: main; Tasks: desktopicon
Name: "{autodesktop}\MLK-II IDE"; Filename: "{app}\MLK-II_IDE.exe"; IconFilename: "{app}\ide_icon.ico"; Components: ide; Tasks: desktopicon
Name: "{autodesktop}\PDF Editor"; Filename: "{app}\PDFEditor.exe"; IconFilename: "{app}\pdf_editor.ico"; Components: pdf_editor; Tasks: desktopicon
Name: "{autodesktop}\Logic to AutoCAD"; Filename: "{app}\LogicToEquivalent.exe"; IconFilename: "{app}\logic_cad.ico"; Components: logic_cad; Tasks: desktopicon

[Registry]
; PDF file association for PDF Editor
Root: HKA; Subkey: "Software\Classes\.pdf\OpenWithProgids"; ValueType: string; ValueName: "MLKII.PDFEditor.pdf"; ValueData: ""; Flags: uninsdeletevalue; Components: pdf_editor
Root: HKA; Subkey: "Software\Classes\MLKII.PDFEditor.pdf"; ValueType: string; ValueName: ""; ValueData: "PDF Document"; Flags: uninsdeletekey; Components: pdf_editor
Root: HKA; Subkey: "Software\Classes\MLKII.PDFEditor.pdf\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\pdf_editor.ico"; Components: pdf_editor
Root: HKA; Subkey: "Software\Classes\MLKII.PDFEditor.pdf\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\PDFEditor.exe"" ""%1"""; Components: pdf_editor

; MLL file association for MLK-II IDE
Root: HKA; Subkey: "Software\Classes\.mll\OpenWithProgids"; ValueType: string; ValueName: "MLKII.IDE.mll"; ValueData: ""; Flags: uninsdeletevalue; Components: ide
Root: HKA; Subkey: "Software\Classes\MLKII.IDE.mll"; ValueType: string; ValueName: ""; ValueData: "Microlok MLL Logic File"; Flags: uninsdeletekey; Components: ide
Root: HKA; Subkey: "Software\Classes\MLKII.IDE.mll\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\ide_icon.ico"; Components: ide
Root: HKA; Subkey: "Software\Classes\MLKII.IDE.mll\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\MLK-II_IDE.exe"" ""%1"""; Components: ide

; MLP file association for MLK-II IDE
Root: HKA; Subkey: "Software\Classes\.mlp\OpenWithProgids"; ValueType: string; ValueName: "MLKII.IDE.mlp"; ValueData: ""; Flags: uninsdeletevalue; Components: ide
Root: HKA; Subkey: "Software\Classes\MLKII.IDE.mlp"; ValueType: string; ValueName: ""; ValueData: "Microlok MLP Project File"; Flags: uninsdeletekey; Components: ide
Root: HKA; Subkey: "Software\Classes\MLKII.IDE.mlp\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\ide_icon.ico"; Components: ide
Root: HKA; Subkey: "Software\Classes\MLKII.IDE.mlp\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\MLK-II_IDE.exe"" ""%1"""; Components: ide

[Run]
Flags: nowait postinstall skipifsilent; Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Components: main

