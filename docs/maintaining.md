# Maintainer guide

## Prerequisites

Rust 1.95 (see rust-toolchain.toml), Git, Python 3.11+, platform build tools.
Windows needs Visual Studio C++ Build Tools and CMake; Mac needs Xcode command-line
tools. Python `cryptography` is needed only for release signing.

```sh
cargo test --locked
cargo clippy --locked --all-targets -- -D warnings
cargo build --release --locked
python scripts/prepare.py pdfcraft --build
python scripts/package.py pdfcraft --platform windows-x64 --version 0.1.0 --source work/pdfcraft
```

Use `photocraft` for the other app and the appropriate platform on Mac. The
prepare script uses an isolated `work/` checkout and full commit pins. It never
resets a developer's original checkout. To change patch inputs, use a fresh work
directory. Prepared builds include the upstream-pinned craft-fonts repository.

## Publishing a release

1. Review upstream pins, patch conflicts, third-party licenses and README status.
2. Run local tests and require CI to pass. Test the resulting portable build on
   Windows; Mac hardware testing remains a separate release criterion.
3. Set repository Actions secret `UPDATE_SIGNING_KEY` to the hex-encoded 32-byte
   Ed25519 seed matching `release-public-key.txt`. Keep an offline backup. Never
   print the seed or put it into an issue, workflow artifact, or Git history.
4. Run the Release workflow with a strictly increasing SemVer, e.g. `0.1.0`.
5. All six builds must succeed. The workflow creates a **draft** Release with ZIPs,
   checksums, source snapshot and signed `channel.json` / `channel.sig`.
6. Review the draft and smoke-test downloaded artifacts before publishing it.
   Drafts and prereleases are not served by the updater's `/releases/latest` feed.

Published versions are immutable: do not replace an asset under an existing tag.
Fixes, including updater-only patches, require a new version and release. An app
already running remains on its current binary until relaunched.

The daily upstream check compares GitHub `main` heads with `upstreams.json` and
uploads a report. It does not auto-merge upstream changes or publish them. To adopt
new upstream code, edit the full commit pins, revalidate patches, and release.

The update endpoint is fixed to xyz9516/craftapps-portable-updater. Forks must
change that endpoint, generate their own signing key, and rebuild the runtime.
See the bilingual [fork setup guide](forking.md) for the full file checklist.

## Testing without a published release

`cargo test` exercises signature tampering, repository URL restrictions, unsafe
ZIP paths, failed activation, downgrade rejection, updater replacement and data
retention. `python -m unittest discover -s tests` checks packaging and pinned patch
inputs. CI verifies both upstream patch application and the patched data-directory
test. Local first-launch logs can contain a harmless update HTTP 404 before a
stable Release exists; the application still opens normally.
