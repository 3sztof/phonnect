# Proposal

## Why

Tracking issue: [#7](https://github.com/3sztof/phonnect/issues/7).

Many sessions are about one app (for example the Spark guitar amp app). Opening the mirror and then finding the app on the phone is extra clicks every time.

## What Changes

- Pin favourite apps per phone. They appear under the phone's tray entry and as a sidebar menu: clicking one opens the mirror (if needed) with that app in front.
- Optional per-phone "open this app when the phone connects".
- Optionally open a favourite app in desktop mode instead of the phone screen.
- Picking favourites: a small window listing the phone's launchable apps, with search.

Out of scope: installing or uninstalling apps, app shortcuts/deep links.

## Capabilities

### New Capabilities
- `favourite-apps`: pinning phone apps and opening them directly.

### Modified Capabilities
- `tray-menu`: phone entries list their favourite apps.
- `sidebar`: gains the favourites menu.

## Impact

Watcher (scrcpy's start-app option, needs scrcpy 3.0+), app list from the phone, remembered-phones storage, tray, sidebar, a picker window, docs/usage.md, tests.
