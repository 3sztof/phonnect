# Tasks

- [x] `scripts/install.sh` and `scripts/install.ps1`: plan, confirmation, uv, scrcpy + adb, Phonnect, doctor, install; options; safe under `irm | iex` (no `exit`, nothing left in the user's session)
- [x] `scripts/uninstall.sh` and `scripts/uninstall.ps1`
- [x] `just install` runs the installer with the checkout as source
- [x] macOS app bundle in `~/Applications`; Windows entries named `Phonnect.lnk`; rewrite entries once per version
- [x] Release workflow: read-only build job, publish job, provenance, scripts stamped with the version, new release notes
- [x] CI: syntax checks for the scripts
- [x] README and docs/installation.md
