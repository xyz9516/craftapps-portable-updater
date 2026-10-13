# CraftApps Portable Updater

**整合自動更新的 PhotoCraft 與 PdfCraft 社群便攜版。**

[English](README.md) · **繁體中文**

[![CI](https://github.com/xyz9516/craftapps-portable-updater/actions/workflows/ci.yml/badge.svg)](https://github.com/xyz9516/craftapps-portable-updater/actions/workflows/ci.yml)
[下載與版本發布](https://github.com/xyz9516/craftapps-portable-updater/releases) · [建置紀錄](https://github.com/xyz9516/craftapps-portable-updater/actions) · [回報問題](https://github.com/xyz9516/craftapps-portable-updater/issues)

## 為什麼建立此專案

PhotoCraft 與 PdfCraft 的原始碼持續快速發展。在本專案目前追蹤的上游版本中，Portable 發行包尚不會自動下載並安裝新版。部分版本提供的「檢查更新」，也不等於能自動維護便攜版的更新器。

因此，我們先建立這個社群整合版本，把應用程式、無黑窗啟動器與自動更新器放進同一個下載包，減少反覆下載、解壓縮及手動替換程式的步驟，也不需要每台電腦都安裝 Rust 或 Git。

更新涵蓋應用程式、我們維護的 patch，以及版本化的啟動與更新元件，讓安裝內容對齊**本專案最新通過驗證並發布的版本**。我們不承諾即時安裝上游 `main` 的每一筆未驗證提交；上游成果仍歸原作者所有。

> **獨立社群專案。** 本倉庫由 `xyz9516` 維護，不是 PhotoCraft、PdfCraft、Storyteller 或 ArtCraft 的官方發布管道。上游與本專案的版本發布、功能支援及問題處理彼此獨立。

## 目前狀態與下載

首次發布流程正在驗證中。可下載的發行版只會出現在本倉庫的 **Releases** 頁面；CI 編譯成功並不代表應用程式的所有功能都已完成測試。

| 平台 | 格式 | 狀態 |
| --- | --- | --- |
| Windows x64 | Portable ZIP | 已實作建置流程，正在驗證首次發布 |
| macOS Apple Silicon（M 系列） | 含 `.app` 的 Portable ZIP | 已配置 CI 建置，待實機驗證 |
| macOS Intel | 含 `.app` 的 Portable ZIP | 已配置 CI 建置，待實機驗證 |

M 系列晶片的 Mac 請選 `macos-arm64`；Intel 處理器的 Mac 請選 `macos-x64`。不確定時，可在「 → 關於這台 Mac」查看晶片／處理器。這是處理器架構的區別，不是 macOS 系統版本的新舊之分。

PhotoCraft 與 PdfCraft 分別提供下載包。Mac 測試版採 ad-hoc 簽章，**沒有 Apple Developer ID 簽章，也未經 Apple 公證**，可能被 Gatekeeper 攔截，請參閱 [macOS 說明](docs/macos.md)。Windows 社群版本也尚未使用發行者程式碼簽章憑證。

## 快速開始

1. 從 [Releases](https://github.com/xyz9516/craftapps-portable-updater/releases) 下載對應程式與平台的 `*-portable.zip`。
2. **完整解壓縮**至可寫入的資料夾。不要直接在 ZIP 或唯讀映像檔中執行。
3. Windows 開啟 `PhotoCraft.exe`／`PdfCraft.exe`；Mac 開啟最外層的 `.app`。
4. 搬移時保留整個資料夾，包含啟動入口、`state.json`、`versions/` 與 `data/`。

使用者電腦不需要安裝 Rust、Python、PowerShell、Git 或開發工具。既有的本機開發版不會被自動遷移或修改。

## 自動更新如何運作

1. 先開啟目前可用的程式。
2. 在背景檢查本倉庫最新發布版本。
3. 驗證更新清單的 **Ed25519 數位簽章**，再核對更新包大小與 **SHA-256**。
4. 解壓至新的暫存資料夾，檢查程式、平台及版本是否吻合，再安裝到獨立版本目錄。
5. 以原子寫入切換版本指標，**下次啟動**才使用新版。

更新不會關閉正在使用的程式，也不會覆寫執行中的檔案。網路中斷、簽章不符、檔案損壞或內容驗證失敗時，維持原版本。鎖定機制避免同時執行多個更新；舊版本會保留以供回復。

更新器本身位於版本化的更新包內，因此我們修補更新邏輯後，也能經相同驗證管道送到使用者端。最外層僅保留固定的 protocol-v1 引導程式，負責啟動目前的 runtime；若將來要更換這層引導協定，需透過完整新包遷移，不屬於就地自動替換。更新簽章與 Apple／Windows 發行者簽章不同，詳見 [架構與信任模型](docs/architecture.md)。

## 資料保存與版本回復

```text
PdfCraft-Portable/
  PdfCraft.exe              # Mac 使用 PdfCraft.app/
  state.json                # 目前版本與上一版
  versions/
    0.1.0/
      build.json            # 上游提交、patch 摘要與更新器版本
      craft-runtime.exe     # 版本化啟動器與更新器
      pdfcraft.exe          # Mac 使用應用程式 bundle
      licenses/
  data/                     # 設定與復原資料，更新包不覆蓋
  logs/
```

換電腦或回復版本前，請先備份 `data/`。Portable 表示應用程式資料可跟著資料夾移動，不代表作業系統完全不留下最近使用紀錄、字型快取或診斷資訊。搬移資料夾或拔除隨身碟前，請先關閉所有應用程式實例。

向最外層啟動器傳入 `--rollback`，可選用上一版，並自動建立 `updates-paused.txt` 暫停更新。刪除該檔即可恢復更新；也可以自行建立它來暫停背景檢查。版本回復只切換程式，不會逆轉資料格式遷移。舊版本目錄目前不會自動清除。

## 上游追蹤與我們的 patch

| 程式 | 上游倉庫 | 固定版本紀錄 |
| --- | --- | --- |
| PhotoCraft | [storytold/photocraft](https://github.com/storytold/photocraft) | [`upstreams.json`](upstreams.json) |
| PdfCraft | [storytold/pdfcraft](https://github.com/storytold/pdfcraft) | [`upstreams.json`](upstreams.json) |

每次建置使用完整上游 commit hash，遵守依賴 lockfile 與上游字型版本。若 patch 與上游衝突，建置會停止，不會默默忽略修補。每個更新包的 `build.json` 記錄上游提交、patch 集合雜湊及本倉庫版本。

目前 PdfCraft patch 提供跨版本沿用的便攜資料目錄，並移除修改版不應散布的上游商標圖示；PhotoCraft 已有資料目錄覆寫機制。更新器與無黑窗啟動器則由本倉庫獨立維護。詳見 [patch 清單](patches/README.md)。

## 建置與發布

[維護指南](docs/maintaining.md) 說明本機建置、更新上游、簽章及 GitHub Actions 發布流程。Windows、Apple Silicon 與 Intel Mac 分別在對應 CI 平台編譯；跨平台編譯通過不取代 Mac 實機測試。

Release 工作流程須完成全部六種程式／平台組合，且簽章金鑰吻合，才會產出發布用更新清單。上游新提交或本機 patch 必須先完成新版本建置與發布，才會送至使用者；工作目錄中的未發布修改不會直接同步。

## 快速改成自己的 Fork 自動更新版

你也可以沿用本專案，把自己的 PhotoCraft／PdfCraft fork 打包成便攜版，並從自己的 GitHub 倉庫發布更新。啟動器、更新器、patch 與發布工作流程都已包含在內，可直接修改現有設定，不必從零建立更新器。

將 `src/lib.rs` 與 `scripts/package.py` 的發布倉庫改成自己的倉庫，在 `upstreams.json` 指定自己的應用程式 fork 與完整 commit hash，再產生專屬的發布簽章金鑰。調整套件識別與說明文件後，重新編譯並透過自己倉庫的 Actions 發布，即可讓使用者從**你的發布管道**接收程式變更、patch 及版本化更新器的修補。

完整檔案清單與步驟請見 [Fork 設定指南](docs/forking.md#繁體中文)。這是原始碼層級的設定，並非使用者端的一鍵切換來源；既有安裝仍綁定編譯時內嵌的倉庫與驗證公鑰。

## 授權、致謝與回報

本專案的啟動器、更新器與打包程式採 [MIT 授權](LICENSE)。PhotoCraft、PdfCraft 保留上游 MIT OR Apache-2.0 授權；依賴、字型與其他素材各依原授權條款。下載包包含上游授權、素材歸屬及字型聲明。ArtCraft 名稱與圖示不屬於上述開源授權，修改版 PdfCraft 產物會排除受限制的品牌圖示；本專案不主張其商標權。

打包或更新問題請在[本倉庫回報](https://github.com/xyz9516/craftapps-portable-updater/issues)，附上版本、作業系統／架構及**已遮蔽個資**的更新日誌。請勿上傳私人文件、存取 token、簽章私鑰或含私人檔案路徑的完整日誌。
