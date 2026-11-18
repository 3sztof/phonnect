# Proposal

## Why

Tracking issue: [#9](https://github.com/3sztof/phonnect/issues/9).

Settings are global today. Someone with a phone and a tablet wants different ones per device (landscape and a smaller content size on the tablet, audio on the PC for one but not the other).

## What Changes

- Audio mode, force landscape, content size, sidebar, keyboard and window position can be set per phone. Values not set for a phone fall back to the global settings.
- Changing a session setting from the tray or sidebar while a phone is mirrored applies to that phone (with a clear way to make it the default for all phones).
- Existing users keep their current global settings; nothing changes until a per-phone value is set.

Out of scope: syncing settings between computers, import/export.

## Capabilities

### New Capabilities
- `phone-profiles`: per-phone settings with global defaults.

### Modified Capabilities
- `phone-settings`: content size and force landscape can come from a phone's profile.
- `audio-and-input`: the audio mode and keyboard option can come from a phone's profile.
- `tray-menu`: settings are shown and changed for the selected phone.

## Impact

Config format (migration from global-only), watcher, tray, sidebar, docs/usage.md, tests. Probably the largest change in the backlog; should come after the smaller mirror-window features.
