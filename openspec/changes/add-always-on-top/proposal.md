# Proposal

## Why

Tracking issue: [#3](https://github.com/3sztof/phonnect/issues/3).

People keep the mirror next to other work (e.g. the Spark app while playing along with a video). Without "always on top" the mirror disappears behind other windows as soon as they're clicked.

## What Changes

- An **Always on top** toggle in the sidebar, remembered for next time, also available in the tray.
- Toggling it applies immediately to the open window, without reopening it (Windows: change the window's topmost state directly; elsewhere: reopen with scrcpy's `--always-on-top` if a live change isn't possible).
- The sidebar stays above the mirror window either way.

Out of scope: per-monitor placement, picture-in-picture mini mode.

## Capabilities

### New Capabilities
- `mirror-window`: options for how the mirror window behaves (always on top, screen off, position).

### Modified Capabilities
- `sidebar`: gains the Always on top toggle.

## Impact

Sidebar, tray, watcher/osutil (topmost on Windows), config (`always_on_top`), docs/usage.md, tests.
