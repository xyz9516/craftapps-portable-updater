# CraftApps Portable Updater

**Community portable builds of PhotoCraft and PdfCraft, with integrated automatic updates.**

**English** · [繁體中文](README.zh-TW.md)

[![CI](https://github.com/xyz9516/craftapps-portable-updater/actions/workflows/ci.yml/badge.svg)](https://github.com/xyz9516/craftapps-portable-updater/actions/workflows/ci.yml)
[Releases](https://github.com/xyz9516/craftapps-portable-updater/releases) · [Builds](https://github.com/xyz9516/craftapps-portable-updater/actions) · [Report an issue](https://github.com/xyz9516/craftapps-portable-updater/issues)

## Why this project exists

PhotoCraft and PdfCraft are developing rapidly. At the upstream revisions tracked by this project, their portable packages do not automatically download and install new versions. A built-in **check for updates**, where available, is different from an installer that keeps a portable copy current.

We created this community distribution to close that gap: a portable application, a console-free launcher, and an updater in one download. You can follow new builds without repeatedly downloading, extracting, and replacing the application yourself—or installing Rust and Git on every computer.

Updates include the applications, our maintained patches, and the versioned launcher/update runtime. They align your installation with **the latest validated release published by this project**, not every untested commit on upstream `main`. Upstream work remains credited to its authors.

> **Independent community project.** This repository is maintained by `xyz9516`; it is not an official PhotoCraft, PdfCraft, Storyteller, or ArtCraft release channel. Upstream release schedules, feature availability, and support policies remain separate.

## Status and downloads

The initial release pipeline is being validated. Downloadable builds, when published, appear only on this repository's **Releases** page. A passing CI build is not a claim that every application feature has been tested.

| Platform | Package | Status |
| --- | --- | --- |
| Windows x64 | Portable ZIP | Build pipeline implemented; first release validation in progress |
| macOS Apple Silicon (M-series) | `.app` bundles in a portable ZIP | CI build target; hardware validation pending |
| macOS Intel | `.app` bundles in a portable ZIP | CI build target; hardware validation pending |

For an M-series Mac, choose `macos-arm64`; for a Mac with an Intel processor, choose `macos-x64`. Check **Apple menu → About This Mac** if unsure. These are processor architectures, not old/new macOS version labels.

Each platform has separate PhotoCraft and PdfCraft downloads. macOS test builds use ad-hoc signatures and **are not Apple Developer ID signed or notarized**. Gatekeeper can block them; see [macOS notes](docs/macos.md). Windows community builds also do not have a publisher code-signing certificate.

## Quick start

1. Download the `*-portable.zip` for your application and platform from [Releases](https://github.com/xyz9516/craftapps-portable-updater/releases).
2. Extract the **entire ZIP** into a folder you can write to. Do not run from inside the ZIP or a read-only disk image.
3. Open `PhotoCraft.exe` / `PdfCraft.exe` on Windows, or the top-level `.app` on macOS.
4. Keep the application entry point, `state.json`, `versions/`, and `data/` together when moving the installation.

No Rust, Python, PowerShell, Git, or developer tools are needed on an end user's computer. Existing local development installations are not automatically migrated or modified.

## How updates work

1. Launch the current installed application immediately.
2. Check this repository's latest published release in the background.
3. Verify the release manifest's **Ed25519 signature**, then the matching package's size and **SHA-256**.
4. Extract into a fresh staging directory, validate application/platform/version identity, and install a new version directory.
5. Atomically change the active-version pointer. The new version is used on the **next launch**.

The updater never terminates an open application or overwrites its running executable. Network errors, invalid signatures, damaged downloads, and rejected payloads leave the active version in place. Concurrent update checks are serialized. Older version directories are retained for recovery.

The update runtime is inside each versioned payload, so fixes to the updater itself are distributed through the same verified channel. A small, fixed protocol-v1 bootstrap outside those payloads dispatches to the active runtime; replacing that bootstrap is a separate full-package migration, not an in-place self-update. Release signing keys are distinct from Apple/Windows publisher certificates. See [architecture and trust model](docs/architecture.md).

## Portable data and recovery

```text
PdfCraft-Portable/
  PdfCraft.exe              # Windows entry point; macOS uses PdfCraft.app/
  state.json                # Current and previous versions
  versions/
    0.1.0/
      build.json            # Upstream commit, patch digest, updater revision
      craft-runtime.exe     # Versioned launcher and updater
      pdfcraft.exe          # macOS uses an application bundle
      licenses/
  data/                     # Settings and recovery data; never in update archives
  logs/
```

Back up `data/` before moving between computers or reverting application versions. Portable means the application data travels with the folder; it does not promise the operating system creates no recent-file, font-cache, or diagnostic records. Close all application instances before moving the folder or switching removable drives between machines.

Pass `--rollback` to the top-level launcher to select the previous version. This creates `updates-paused.txt`; remove that file to resume automatic updates. You can also create the file yourself to pause background checks. Rollback switches binaries; it does not reverse data-format migrations. No automated version-directory cleanup is performed.

## Upstream tracking and our patches

| Application | Upstream | Recorded source |
| --- | --- | --- |
| PhotoCraft | [storytold/photocraft](https://github.com/storytold/photocraft) | [`upstreams.json`](upstreams.json) |
| PdfCraft | [storytold/pdfcraft](https://github.com/storytold/pdfcraft) | [`upstreams.json`](upstreams.json) |

Upstreams are pinned to full commit hashes; dependency lockfiles and the upstream font pins are respected. Patch application fails closed: conflicts stop the build instead of silently dropping our changes. Each payload records the upstream commit, patch-set digest, and this repository's revision in `build.json`.

Current PdfCraft patches add a persistent portable data-directory override and remove restricted upstream trademark artwork from our modified builds. PhotoCraft already supports a data-directory override. The updater and console-free launcher are maintained here, outside the upstream source trees. See [patch inventory](patches/README.md).

## Build and release

See [the maintainer guide](docs/maintaining.md) for local builds, upstream updates, signing, and GitHub Actions releases. Windows, Apple Silicon, and Intel macOS are built separately on their native CI runners. Cross-platform build success does not replace testing on real Macs.

The Release workflow requires all six application/platform packages and a matching signing key before publishing an update manifest. New upstream commits or local patches reach users **after** a new release is built and published; edits in a working tree are not sent directly to installations.

## Make your own fork with automatic updates

You can reuse this project to package your own PhotoCraft/PdfCraft forks and publish updates from your own GitHub repository. The launcher, updater, patches, and release workflow are included, so you can adapt the existing setup instead of building an updater from scratch.

Change the release repository in `src/lib.rs` and `scripts/package.py`, point `upstreams.json` at your own application forks and full commit hashes, and generate your own release-signing key. Adjust package identity and documentation, then rebuild and publish through your fork's Actions workflow. Your users will receive your application's changes, patches, and versioned updater fixes from **your** release channel.

See the [fork setup guide / Fork 設定指南](docs/forking.md) for the exact files and steps. This is a source-level setup, not an end-user channel switch: existing installations remain tied to the repository and verification key embedded when they were built.

## Licensing and attribution

Our launcher, updater, and packaging code are [MIT licensed](LICENSE). PhotoCraft and PdfCraft retain their upstream MIT OR Apache-2.0 licensing; dependencies, fonts, and other assets retain their respective licenses. Packages carry upstream license and attribution files plus font notices. The ArtCraft name and artwork are not covered by those open-source licenses; restricted branding is excluded from our modified PdfCraft application output. This project makes no claim to those trademarks.

Report packaging/update issues [here](https://github.com/xyz9516/craftapps-portable-updater/issues), including the package version, OS/architecture, and a **redacted** updater log. Do not upload private documents, access tokens, signing keys, or unredacted personal file paths.
