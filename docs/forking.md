# Fork setup guide / Fork 設定指南

## English

This repository can serve as the packaging and update layer for your own
PhotoCraft and PdfCraft forks. Fork this repository into a public GitHub repository,
clone your fork, and make the following changes before producing your first package.

| File | Change |
| --- | --- |
| `src/lib.rs` | Set `REPOSITORY` to `YOUR-OWNER/YOUR-REPO`. This controls the update feed and allowed asset URLs. |
| `scripts/package.py` | Change the release-download URL to the same repository; replace the `io.github.xyz9516` macOS bundle identifier prefix with your own. |
| `upstreams.json` | Set each application's `repository` and full `commit` hash to your desired source. Keep the existing application keys and target names. |
| `patches/photocraft/`, `patches/pdfcraft/` | Maintain your patches here; revalidate them against your pinned source. |
| `release-public-key.txt` | Replace with the public key generated below. Rebuild to embed it. |
| `src/tests.rs` | Adjust repository-specific test URLs to match your chosen release repository. Keep rejection tests for other repositories. |
| `README.md`, `README.zh-TW.md`, `docs/PORTABLE.txt`, `docs/maintaining.md` | Update maintainer identity, links, release status, and support information. Preserve upstream attribution and licenses. |

Generate a new Ed25519 key pair once with Python and `cryptography` installed.
Run this from your cloned repository; the script refuses to overwrite an existing
seed. `.secrets/` is ignored by Git. The private seed is written to disk, not printed.

```python
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, PrivateFormat, NoEncryption

key = Ed25519PrivateKey.generate()
folder = Path('.secrets')
folder.mkdir(exist_ok=True)
with (folder / 'release-key.hex').open('x', encoding='ascii') as f:
    f.write(key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()).hex())
Path('release-public-key.txt').write_text(
    key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex() + '\n',
    encoding='ascii',
)
```

Commit the public key with your source changes. Store the private seed as the
repository Actions secret **`UPDATE_SIGNING_KEY`**, and retain a private backup.
Do not commit or distribute `.secrets/`. Enable Actions on your fork, run CI, and
follow the [maintainer guide](maintaining.md) to build, review, and publish a release.
The release workflow uses the repository where it runs; application update URLs
still require the source changes listed above.

The current workflow builds both applications on Windows x64, macOS Apple Silicon,
and macOS Intel. If you remove an application or platform, also adjust
`.github/workflows/release.yml` and the six-asset requirement in
`scripts/sign_release.py`. An unrelated application needs additional work on
application identity, build commands, paths, and packaging; this is not a universal
one-click updater generator.

Distribute your freshly built `*-portable.zip` for first installation. Copies built
by this project continue using this project's repository and key; they do not
automatically switch to yours. Later fixes to your patches and versioned updater
are delivered by publishing a higher version through your own signed release feed.
Keep the same signing key for subsequent releases; protocol v1 does not support
in-place key rotation.

## 繁體中文

你可以將本倉庫作為自己 PhotoCraft／PdfCraft fork 的打包與自動更新層。
先將本倉庫 Fork 到自己的公開 GitHub 倉庫，拉回本機，再調整以下位置：

| 檔案 | 要修改的內容 |
| --- | --- |
| `src/lib.rs` | 將 `REPOSITORY` 改為 `你的帳號/你的倉庫`；更新來源與允許的下載網址都由此決定。 |
| `scripts/package.py` | 將發布下載網址改為同一個倉庫，並把 macOS bundle identifier 的 `io.github.xyz9516` 前綴改成自己的識別名稱。 |
| `upstreams.json` | 指定自己應用程式 fork 的 `repository` 與完整 `commit` hash；保留現有應用程式鍵值與編譯目標名稱。 |
| `patches/photocraft/`、`patches/pdfcraft/` | 放入自己維護的 patch，確認能套用至指定原始碼。 |
| `release-public-key.txt` | 換成自己的發布驗證公鑰，再重新編譯。 |
| `src/tests.rs` | 將發布倉庫相關測試網址改成自己的倉庫，保留拒絕其他倉庫的測試。 |
| README 與 `docs/PORTABLE.txt`、`docs/maintaining.md` | 更新維護者、連結、發布狀態與支援說明，保留上游致謝與授權。 |

安裝 Python 的 `cryptography` 後，在倉庫根目錄執行上方 Python 範例，
產生自己的 Ed25519 金鑰。程式不會覆寫既有私鑰，也不會將私鑰印在終端機。
只將 `release-public-key.txt` 公鑰納入版本控制；私鑰位於 Git 忽略的
`.secrets/release-key.hex`，將其內容存入自己倉庫的 Actions secret
**`UPDATE_SIGNING_KEY`**，另行私下備份，不要提交或放入下載包。

在自己的 Fork 啟用 Actions，確認 CI 通過，再依[維護指南](maintaining.md)
建置、檢查並發布 Release。發布工作流程會使用執行它的倉庫，但程式內的更新
網址仍須完成上述修改。現有流程要求兩個應用程式乘以三個平台，共六個更新包；
若只保留部分程式或平台，需同時調整 `.github/workflows/release.yml` 與
`scripts/sign_release.py` 的完整性檢查。若套用到其他應用程式，還需修改
程式識別、編譯命令、路徑及打包邏輯。

首次安裝請提供自己重新編譯的 `*-portable.zip`。本專案原本的下載包仍使用
原本的更新倉庫與公鑰，不會自動改連你的 Fork。往後發布較高版本，即可將你的
應用程式、patch 與版本化更新器修補送給自己的使用者。後續發布應沿用同一把
簽章金鑰；protocol v1 尚不支援就地更換信任金鑰。
