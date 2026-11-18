# Spec Delta

## MODIFIED Requirements

### Requirement: Docked on Windows
On Windows and macOS the sidebar SHALL stay attached to the mirror window's right edge (left edge when there's no room) and follow it when moved, resized or minimized. On Windows it MUST NOT take keyboard focus from the mirror when clicked. On macOS it SHALL stay above the mirror window only while the mirror or the sidebar is the front app, and SHALL NOT show its own Dock icon. Elsewhere it MAY float.

#### Scenario: Window moved
- **WHEN** the user drags the mirror window
- **THEN** the sidebar moves with it

#### Scenario: Window at the right screen edge
- **WHEN** the mirror window touches the right edge of the screen
- **THEN** the sidebar is shown on its left side

#### Scenario: Another app in front on macOS
- **WHEN** the user switches to another app that covers the mirror window
- **THEN** the sidebar doesn't stay on top of that app
