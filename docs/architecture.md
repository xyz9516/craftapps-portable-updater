# Architecture and trust model

A small protocol-v1 native bootstrap locates `state.json` relative to itself and
starts `versions/<current>/craft-runtime`. Both binaries use the Windows GUI
subsystem; process spawning uses no shell. The same Rust code builds on macOS.

The versioned runtime launches the application and a detached background update
check. It supplies the portable `data/` path to both applications. PdfCraft needs
our data-directory patch; PhotoCraft already supports an override. The runtime
and application are in the same update ZIP, so updater patches advance with app
patches. The tiny bootstrap protocol is deliberately fixed. A future incompatible
bootstrap requires a full package migration and cannot be advertised as an
automatic update to protocol-v1 installations.

The trust root is the Ed25519 public key embedded at compile time. Release
manifests are verified before their URLs or metadata are used. Only this GitHub
repository's HTTPS Release asset URLs are accepted (GitHub redirects the actual
download to its asset CDN). SHA-256 and exact byte counts authenticate payloads
against the signed manifest. A release must have a strictly newer semantic
version; a replay cannot roll an existing installation backward.

Updates stage on the installation's filesystem. Extraction rejects absolute
paths, traversal, alternate data streams, symlinks, duplicate file writes and
excessive sizes. A single file lock serializes updates and rollback. The active
pointer changes only after the entire payload passes checks. Running versions
are never modified, and app data is never extracted into the installation root.

The signing private key is a GitHub Actions secret, never an artifact or source
file. Maintainers must retain an offline backup; the initial public key is pinned
in existing clients. Key rotation is not implemented in protocol v1. Losing the
key requires a new trusted full-package install, not silently trusting a new key
from the same update server.

Limits: no transparency log, expiry/freshness guarantee against a frozen feed,
or automatic detection of application bugs in an otherwise valid signed update.
Build/UI smoke tests are not a full application test suite. macOS packages are
not Apple notarized. SHA-256 alone is not a publisher identity guarantee.

## macOS layout

The outer `.app` contains only the signed bootstrap. Data and version directories
are siblings, outside that bundle, so updates do not mutate its signed contents.
Each version contains a separate application bundle and native runtime. Move the
whole enclosing folder, not only the outer `.app`. Finder document handoff and
default-file associations to the outer bootstrap are not supported in v1; open
documents using the running application's Open dialog. CLI file arguments work.
