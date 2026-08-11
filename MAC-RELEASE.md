# MakerQ Downloads and Mac Release Sync

How the website download buttons work, and how the Mac build stays in sync with
Windows. Written because the Mac download kept falling behind the Windows release.

## Where the downloads live

- Public release repo: **`c3dprints/MakerQ-download`** (GitHub Releases).
- The website links to the "latest release" permalinks, so they always point at
  whatever the newest release is:
  - Windows: `https://github.com/c3dprints/MakerQ-download/releases/latest/download/MakerQ-Setup.exe`
  - Mac: the download page does NOT hardcode the dmg. It calls the GitHub API
    (`/repos/c3dprints/MakerQ-download/releases/latest`) and activates the Mac
    card if that release has ANY `.dmg` asset (any filename). See `download.html`
    bottom script (`#mac-badge` / `#mac-dl` / `#mac-note`).

Because the Mac card reads the LATEST release, a Windows-only release makes the
Mac download disappear ("Coming soon") until a `.dmg` is attached to that same
release.

## The recurring problem

Windows releases are cut from a Windows machine and keep advancing (1.1.44 ->
1.1.48 -> 1.1.49 ...). Each new release is a new tag with only `MakerQ-Setup.exe`
attached. The Mac side is NOT rebuilt each time, so:

- The latest release has no `.dmg` -> the Mac permalink 404s -> the site shows
  "Coming soon".
- The last Mac build that actually exists is whatever was last built on the Mac
  (as of this writing, **1.1.44**, in
  `~/Library/Application Support/C3DPrints/updates/MakerQ-1.1.44.dmg`, and the
  installed `/Applications/MakerQ.app` is also 1.1.44).

"The app works on my Mac" (installed 1.1.44, auto-updater) is separate from "the
Mac download on the site is current." The download only has whatever `.dmg` was
uploaded to the latest release.

## To publish a Mac build that matches Windows

1. Get the current source (the version Windows just shipped, e.g. 1.1.49) onto the
   Mac. The local checkout at `~/Documents/c3dprints-quote-portal` may be behind
   (it was at 1.1.44); pull/sync it to the released version first.
2. Build the Mac app + dmg with the normal pipeline (staging dirs seen on this
   machine: `/private/tmp/mq-macbuild`, `/private/tmp/mqbuild`; output lands in
   `backend/dist/`). Confirm the built `MakerQ.app` version matches:
   `/usr/libexec/PlistBuddy -c 'Print CFBundleShortVersionString' backend/dist/MakerQ.app/Contents/Info.plist`
3. Upload the dmg to the SAME release tag as the Windows build. Any `.dmg` name
   works (the site detects by extension); `MakerQ.dmg` keeps the URL clean:
   ```
   gh release upload vX.Y.Z "/path/to/MakerQ.dmg" --repo c3dprints/MakerQ-download --clobber
   ```
4. The website needs no change. On the next load the Mac card auto-flips to
   "Available now" pointing at the new dmg.

## Access

The `cdezbch` GitHub account has Write on `c3dprints/MakerQ-download` (accepted
the collaborator invite), so it can upload release assets via `gh`.

## Signing / Gatekeeper

The 1.1.44 dmg is ad-hoc signed and NOT notarized (`Signature=adhoc`,
`TeamIdentifier=not set`). The in-app auto-updater bypasses Gatekeeper, so updates
are fine, but a fresh download from GitHub trips Gatekeeper ("cannot be verified").
The download page shows a first-open note (Control-click > Open, or System
Settings > Privacy and Security > Open Anyway) whenever the Mac download is live.
For a friction-free install, Developer-ID sign + notarize + staple the dmg before
uploading; then the note can be removed.

## Quick status check

```
# latest release tag
curl -s -o /dev/null -w '%{redirect_url}\n' https://github.com/c3dprints/MakerQ-download/releases/latest
# do the assets resolve?
curl -s -o /dev/null -w 'exe %{http_code}\n' -I -L https://github.com/c3dprints/MakerQ-download/releases/latest/download/MakerQ-Setup.exe
curl -s -o /dev/null -w 'dmg %{http_code}\n' -I -L https://github.com/c3dprints/MakerQ-download/releases/latest/download/MakerQ.dmg
```
