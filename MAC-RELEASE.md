# MakerQ Downloads and Mac Release Sync

How the website download buttons work, and how the Mac build is produced and
published. Windows and Mac use SEPARATE release repos, which is the thing that
trips people up.

## Two separate release repos

- **Windows** -> `c3dprints/MakerQ-download`
  - Site links directly to
    `https://github.com/c3dprints/MakerQ-download/releases/latest/download/MakerQ-Setup.exe`
- **Mac** -> `cdezbch/MakerQ-mac-releases`  (this is ALSO the Mac auto-updater feed)
  - The build script uploads a stable-named `MakerQ-mac.dmg` on every release so
    the site can hardlink the newest build:
    `https://github.com/cdezbch/MakerQ-mac-releases/releases/latest/download/MakerQ-mac.dmg`
  - It also keeps the versioned `MakerQ-<version>.dmg` alongside it.

The website's macOS button (`download.html`) points at the stable Mac URL above,
mirroring the Windows button. (Earlier it wrongly auto-detected against the
Windows repo, which never has a `.dmg`, so the Mac card showed "Coming soon"
even though a Mac build existed. Fixed 2026-08-12.)

## Why Mac can look "behind"

Windows releases are cut from the Windows machine and advance the version
(1.1.44 -> 1.1.49 ...). The Mac dmg is only produced when someone runs the Mac
build script below. If that has not been run for the latest version, the Mac
release repo (and the site download) still serves the previous Mac version even
though the app "works" locally via the auto-updater.

## Building + publishing a matching Mac release

Script: **`tools/mac-release-from-main.sh`** in the app repo
(`~/Documents/c3dprints-quote-portal`). It builds the Mac app+dmg from
`origin/main` (the live Windows source, highest version) and can publish it.

```
# build only -> prints the DMG path (no upload)
tools/mac-release-from-main.sh

# build + upload the dmg (and the stable MakerQ-mac.dmg) to
# cdezbch/MakerQ-mac-releases at v<version>
tools/mac-release-from-main.sh --publish
```

What it does: finds the live app on `origin/main`, extracts it, applies the two
Mac-only deltas (transparent-corner icon + baked read-only update token from
`backend/_secrets_baked.py`, and repoints the updater at the Mac releases repo),
runs pyinstaller (`backend/c3dprints.spec`), packages the dmg
(`backend/make-dmg.command`), and with `--publish` uploads to the matching
release tag.

Prerequisites (all verified present on this Mac as of 2026-08-12):
- `backend/.buildvenv` Python 3.12 with PyInstaller
- `backend/_secrets_baked.py` (the update token)
- `gh` authed as `cdezbch` (admin on `cdezbch/MakerQ-mac-releases`)

NOTE: this pipeline bakes a real update token into the distributable and, with
`--publish`, ships a production release to end users. Treat it as a real deploy.

No website change is needed after publishing: the stable `MakerQ-mac.dmg` URL the
site links to always serves the newest Mac build.

## Signing / Gatekeeper

The Mac build is ad-hoc signed and NOT notarized (`Signature=adhoc`,
`TeamIdentifier=not set`). The in-app auto-updater bypasses Gatekeeper, so updates
are fine, but a fresh download from GitHub trips Gatekeeper ("cannot be
verified"). The download page shows a first-open note (Control-click > Open, or
System Settings > Privacy and Security > Open Anyway). For a friction-free
install, Developer-ID sign + notarize + staple the dmg before uploading; then the
note can be removed.

## Quick status check

```
# latest Windows tag + asset
curl -s -o /dev/null -w 'win-latest %{redirect_url}\n' https://github.com/c3dprints/MakerQ-download/releases/latest
curl -s -o /dev/null -w 'exe %{http_code}\n' -I -L https://github.com/c3dprints/MakerQ-download/releases/latest/download/MakerQ-Setup.exe
# latest Mac tag + stable asset
curl -s -o /dev/null -w 'mac-latest %{redirect_url}\n' https://github.com/cdezbch/MakerQ-mac-releases/releases/latest
curl -s -o /dev/null -w 'mac-dmg %{http_code}\n' -I -L https://github.com/cdezbch/MakerQ-mac-releases/releases/latest/download/MakerQ-mac.dmg
```

## Current state (2026-08-12)

- Windows latest: v1.1.49
- Mac latest (cdezbch/MakerQ-mac-releases): v1.1.44  <- behind; run the build
  script with --publish to bring Mac to 1.1.49.
