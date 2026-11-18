# Proposal

## Why

Tracking issue: [#4](https://github.com/3sztof/phonnect/issues/4).

Recording what happens on the phone (a tutorial, a bug, a practice session) currently means a separate screen recorder. scrcpy can record losslessly from the phone's own video stream.

## What Changes

- A **Record** button in the sidebar. Pressing it starts recording to a video file in the user's Videos folder (`Videos/phonnect/<phone>_<date-time>.mp4`); pressing it again stops.
- While recording, the button shows that it's active and the elapsed time. Recording stops automatically when the mirror window closes or the phone disconnects, and the file is kept.
- Recording doesn't restart or interrupt the visible mirror window.
- Right-click opens the recordings folder (like Screenshot).

Out of scope: editing/trimming, recording the desktop-mode window, recording audio when audio is Off.

## Capabilities

### New Capabilities
- `session-recording`: recording the mirrored phone screen to a file.

### Modified Capabilities
- `sidebar`: gains the Record button.

## Impact

Sidebar, watcher (second scrcpy process with `--no-window --record`), control channel (start/stop requests), docs/usage.md, tests.
