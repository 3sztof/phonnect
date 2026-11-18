# Design

## Context

scrcpy (2.5+) has `--mouse-bind=xxxx[:xxxx]`: four characters for right, middle, 4th and 5th click, each `+` (forward to the device), `-` (ignore), `b` (Back), `h` (Home), `s` (App switch) or `n` (notification panel). The optional second sequence applies while Shift is held. Its default for the SDK mouse (the one we use) is `bhsn:++++`.

## Decisions

- **Store one action per button** in config as readable names, not scrcpy's characters: `mouse_buttons = {"right": "app", "middle": "home", "back": "back", "forward": "recents"}` with values `app | back | home | recents | notifications | nothing`. The watcher translates to `--mouse-bind=<primary>:bhsn`. Readable config survives scrcpy changing its option format.
- **Shift keeps scrcpy's originals (`bhsn`)** instead of being configurable: it's the escape hatch for anyone who learned scrcpy's defaults, and it keeps the menu small.
- **Version gate:** only pass `--mouse-bind` when scrcpy is 2.5 or newer (or the version is unknown); older versions would refuse to start.
- **User override wins:** if `scrcpy_args` already contains `--mouse-bind`, the app doesn't add its own.
- **Tray UI:** Settings → Mouse buttons, with one radio group per button under a disabled heading line ("Right click", "Middle click", "Side button (back)", "Side button (forward)"). Choosing reopens open windows (same as the keyboard and audio settings).
- **Desktop mode windows** use the same bindings.

## Risks

- Sending right clicks to apps: some apps treat a forwarded secondary click as a long press. That's closer to PC behavior than an unexpected Back, and it's one menu click to change.
