' scrcpy-auto-launch.vbs
' Silent launcher — no console flash, no UAC prompt.
' Runs the PowerShell watcher with WindowStyle 0 (hidden).
' The scrcpy mirror window itself is a GUI window and appears normally.

Dim oShell
Set oShell = CreateObject("WScript.Shell")

Dim scriptDir
scriptDir = oShell.ExpandEnvironmentStrings("%USERPROFILE%") & "\scrcpy-auto"

Dim psScript
psScript = scriptDir & "\scrcpy-auto.ps1"

' WindowStyle 0 = hidden; bWaitOnReturn = False (fire-and-forget)
oShell.Run "powershell.exe -ExecutionPolicy Bypass -NonInteractive -WindowStyle Hidden -File """ & psScript & """", 0, False
