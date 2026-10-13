Community portable builds of PhotoCraft and PdfCraft with a native console-free
launcher and signed automatic updates. Includes the maintained portable-data and
branding patches documented in the repository.

Download a `*-portable.zip`: the same package supports first installation and
automatic updates. No separate update ZIP is provided. Keep the whole extracted
folder together. [Downloads](https://github.com/xyz9516/craftapps-portable-updater/releases/latest)

社群維護的 PhotoCraft／PdfCraft Portable 整合版，包含無黑窗啟動器、自動更新與本專案 patch。
首次安裝請下載對應平台的 `*-portable.zip`，完整解壓縮後執行。
同一包也供內建更新器使用，不再提供獨立的 update ZIP。

This release number versions our updater and packaging. The bundled upstream
applications retain their own versions: PhotoCraft 0.8.2 and PdfCraft 0.7.1.
本版本號代表本專案的更新器與打包版本；上游程式版本分別為 PhotoCraft 0.8.2、PdfCraft 0.7.1。

macOS builds are ad-hoc signed, not Apple Developer ID signed or notarized.
Mac packages are experimental: real-hardware validation is pending.
Windows builds are not publisher-signed.
Please read the README and macOS notes before using these test builds.

Windows validation: both downloaded packages passed checksum and executable
startup checks, launched responsive application windows, and stored settings in
their own portable data folders. PdfCraft opened a bundled upstream test PDF
through a path containing spaces. These are smoke tests, not a full feature audit.

Mac download selection: M-series / Apple Silicon → `macos-arm64`;
Intel processors → `macos-x64`. Check Apple menu → About This Mac.
Mac 下載選擇：M 系列用 `macos-arm64`；Intel 處理器用 `macos-x64`。

Both README languages explain why this community updater exists and how to adapt
the project for your own forks and independently signed GitHub release channel.
