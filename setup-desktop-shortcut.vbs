' Ozon Analytics — 创建桌面快捷方式
' 运行一次即可在桌面生成带图标的 .lnk 快捷方式

Set ws = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

desktopPath = ws.SpecialFolders("Desktop")
projectPath = fso.GetParentFolderName(WScript.ScriptFullName)
batPath = projectPath & "\start-all.bat"
iconPath = ws.ExpandEnvironmentStrings("%SystemRoot%\System32\dpapimig.exe")

Set shortcut = ws.CreateShortcut(desktopPath & "\Ozon Analytics.lnk")
shortcut.TargetPath = batPath
shortcut.WorkingDirectory = projectPath
shortcut.Description = "Ozon Analytics 数据分析平台 — 一键启动"
shortcut.IconLocation = iconPath & ", 0"
shortcut.Save

MsgBox "快捷方式已创建到桌面！" & vbCrLf & vbCrLf & "文件名：Ozon Analytics.lnk", vbInformation, "Ozon Analytics"
