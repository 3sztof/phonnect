# sidebar Specification

## Purpose

A slim button bar next to each mirror window for phone buttons and gestures that are awkward to reach with a mouse, plus quick tools.

## Requirements

### Requirement: Shown with every mirror window
A sidebar SHALL open with each mirror window when "Show sidebar next to the window" is on (the default), and SHALL close with it. Changing the setting SHALL apply to open windows.

#### Scenario: Window closed
- **WHEN** the mirror window closes
- **THEN** its sidebar closes too

#### Scenario: App stopped
- **WHEN** the app quits or is stopped
- **THEN** all sidebars close

### Requirement: Docked on Windows
On Windows the sidebar SHALL stay attached to the mirror window's right edge (left edge when there's no room), follow it when moved, resized or minimized, and MUST NOT take keyboard focus from the mirror when clicked. Elsewhere it MAY float.

#### Scenario: Window moved
- **WHEN** the user drags the mirror window
- **THEN** the sidebar moves with it

#### Scenario: Window at the right screen edge
- **WHEN** the mirror window touches the right edge of the screen
- **THEN** the sidebar is shown on its left side

### Requirement: Phone buttons
The sidebar SHALL offer Back, Home, Recent apps, Notifications, Quick settings, Volume up/down and Power, delivered to the phone without noticeable delay.

#### Scenario: Recent apps
- **WHEN** the user presses Recent apps
- **THEN** the phone shows its app switcher

### Requirement: Tools
The sidebar SHALL offer: a screenshot saved to the user's Pictures folder, Force landscape, desktop mode, an adb shell in the OS terminal, and the content-size slider.

#### Scenario: Screenshot
- **WHEN** the user presses Screenshot
- **THEN** a PNG of the phone screen is saved to Pictures/scrcpy-autolaunch, and right-clicking the button opens that folder

#### Scenario: Shell
- **WHEN** the user presses Shell
- **THEN** a terminal window opens with an adb shell on that phone

### Requirement: Explained by tooltips
Every sidebar control SHALL have a tooltip naming what it does.

#### Scenario: Hover
- **WHEN** the user hovers over a button
- **THEN** its name appears
