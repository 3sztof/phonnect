# Spec Delta

## ADDED Requirements

### Requirement: Apps panel while the taskbar can't open apps
When desktop mode uses scrcpy's virtual screen, the app SHALL show an Apps panel next to the desktop window that lists the phone's apps, opens a chosen app on the desktop, and lists the apps open there with ways to bring one to the front, close it, and show the desktop. It MUST NOT change any phone setting.

#### Scenario: Open an app
- **WHEN** the user double-clicks an app in the Apps panel
- **THEN** the app opens on the desktop window, full screen unless "Open in a window" is ticked

#### Scenario: Switch and close
- **WHEN** the user selects an app under "Open on the desktop" and clicks Switch to or Close
- **THEN** that app comes to the front, or closes

#### Scenario: Closes with the desktop
- **WHEN** the desktop window closes
- **THEN** the Apps panel closes too

### Requirement: Ask before desktop mode opens
Before desktop mode opens, the app SHALL explain in a prompt that it's an experimental workaround and what to expect, and open it only if the user confirms. The user MAY turn the prompt off; with the simulated second screen it SHALL be shown every time.

#### Scenario: Cancelled
- **WHEN** the user clicks Cancel in the prompt
- **THEN** no desktop window opens

#### Scenario: Don't show again
- **WHEN** the user ticks "Don't show this again" and opens desktop mode
- **THEN** next time desktop mode opens without the prompt

#### Scenario: Already open
- **WHEN** the desktop window is already open and the user presses Desktop mode again
- **THEN** the window comes to the front without a prompt
