# Spec Delta

## ADDED Requirements

### Requirement: The desktop's own taskbar opens apps
With a scrcpy version that supports it, apps SHALL open from the desktop's own taskbar and app drawer on the virtual screen, in windows that can be moved, resized and closed, without the Apps panel or any phone setting change. With older scrcpy versions, the Apps panel workaround SHALL be used, and the prompt SHALL suggest updating scrcpy.

#### Scenario: Fixed scrcpy
- **WHEN** the installed scrcpy includes the fix and the user opens an app from the desktop's taskbar on a Pixel with Android 17
- **THEN** the app opens in a window with a title bar on the desktop

#### Scenario: Older scrcpy
- **WHEN** the installed scrcpy doesn't include the fix
- **THEN** desktop mode opens with the Apps panel, and the prompt suggests updating scrcpy
