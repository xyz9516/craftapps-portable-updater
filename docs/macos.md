# macOS test builds / Mac 測試版

Separate ZIPs target Apple Silicon / M-series (`macos-arm64`) and Intel (`macos-x64`).
Choose by processor, not macOS release year: check Apple menu → About This Mac.
M 系列 Mac 請下載 `macos-arm64`；Intel Mac 請下載 `macos-x64`。
GitHub's native macOS runners compile the applications and Rust updater. The
packager creates `.app` bundles and applies ad-hoc signatures with `codesign`.
These signatures **do not identify an Apple-verified publisher**. No Developer ID
certificate or Apple notarization is used. Gatekeeper may block downloaded apps,
including versioned helper executables. Successful CI compilation is not evidence
that every Mac can launch or automatically update these packages.

只有確認來源可信時，才依 Apple 官方說明處理開啟提示。不要關閉整台電腦的安全保護，
也不要期待更新器自動繞過系統提示。某些受管理的 Mac 不允許使用者自行允許開啟。
Mac 版目前屬於待實機驗證的實驗版本。正式推薦日常使用前，仍須在實機測試
首次下載、首次開啟、背景下載、新版重開與版本回復。

- [Apple: safely open apps on your Mac](https://support.apple.com/102445)
- [Apple: Developer ID distribution](https://developer.apple.com/developer-id/)

Extract to a writable folder and keep its entire contents together. The outer
app is a launcher; Finder file-open events and default-PDF associations through
that launcher are not supported in v1. Use File > Open inside the application.

Future Developer ID signing and notarization should cover both app bundles and
all executable helpers before archives are published. Certificates and private
keys must be stored in Actions secrets, never committed.
