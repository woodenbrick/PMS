[Setup]
AppName=PMS
AppVerName=PMS 0.15.5
AppVersion=0.15.5
AppPublisher=Daniel Woodhouse
AppPublisherUrl=http://github.com/woodenbrick
DefaultDirName={pf}\PMS

[Files]
Source: "dist\*"; DestDir: {app}; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{commonprograms}\PMS"; Filename: "{app}\PMS.exe"
Name: "{commondesktop}\PMS"; Filename: "{app}\PMS.exe"
