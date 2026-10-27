# Proofreader Underline Implementation Plan

**Goal:** 在獨立鼠鬚管測試版驗證有校錯建議時的紅色虛線。

**Architecture:** 固定官方 0.18 原始碼，添加最小前端 patch；重用現有模型建議與 Tab 採用。測試版以獨立資料目錄及輸入來源運作。

**Tech Stack:** Objective-C / AppKit / InputMethodKit / librime / Python 建置工具。

- [x] 建立紅線樣式與選取候選判斷 helper，原生測試屬性與無提示情況。
- [x] patch Squirrel showPreeditString 與快取、rimeUpdate 中提示判斷。
- [x] 建立可重現建置工具，固定上游版本並保留來源與授權；產物使用獨立 App ID、執行檔、連線、資料與更新設定。
- [x] ~~建置並註冊獨立測試版~~ 已取消：改為直接更新原廠鼠鬚管。獨立測試版的輸入法、`~/Library/Rime-Liur-Underline`、`develop/build-squirrel-proofreader.py` 與 README 段落已於 2026-10-28 全數移除；下方該版本的實測紀錄僅保留作歷史。
- [x] 依實機結果修正，記錄限制與切回方式。

## 2026-10-28 實際結果

原生紅線屬性與選取候選測試通過，既有 51 項功能測試通過。測試 App 已建置、簽章驗證與註冊，透過系統設定加入；使用者已親自完成首次使用的系統確認。

實機驗證尚未完成，不能宣稱已顯示紅線。初期 TIS 選取回傳 -50；系統設定加入後回傳 0，但 TextEdit 候選視窗仍屬於原廠 PID 1188。為了排除執行檔名稱衝突改為獨立的 LiurProofread，並重啟測試 App，再先切 ABC、後切測試版；實際輸入變成原始英文，測試版的日誌未出現 createSession。由此確認 TIS 的選取成功不足以證明輸入連線已啟用。目前需要使用者自行存檔、登出再登入，重新載入新輸入法後接續實機驗證。原廠 App 未修改，已切回原廠鼠鬚管。

官方安裝說明： https://github.com/rime/squirrel/blob/0.18/INSTALL.md#directly-install

## 改為直接更新原廠 App

使用者已指定直接修改原廠版。新增 `develop/build-original-squirrel-underline.py`，沿用已完成的紅線 patch，保留原廠輸入法識別與資料位置。

- [x] 使用現有 Apple 開發憑證簽章全部載入的函式庫與程式，保留 Hardened Runtime 與函式庫驗證。
- [x] 以原生 ditto 備份全部檔案與腳本簽章屬性，核對每個檔案及簽章屬性的雜湊。
- [x] 產生禁止重新定位的 macOS 更新套件；安裝前核對原 App 尚未變更。
- [x] 解開套件並再次完整驗證程式簽章，確認包裝沒有遺失腳本簽章屬性。
- [x] 使用者在系統視窗完成管理員認證，安裝至現有 Squirrel.app。已確認 `/Library/Input Methods/Squirrel.app` 含 LiurProofreadUnderlinePanel，簽章時間 2026-10-28 00:51，行程 00:52 重啟。已部署的 `liur_proofreader.lua`、`liur.schema.yaml` 與 repo 一致，校錯服務 socket 存在。
- [ ] 以實際按鍵驗證紅線、換候選與 Tab；截圖記錄成功或實際限制。

2026-10-28 00:59 實機嘗試：TextEdit 輸入 `備pak` 只得到原始英文 `apak`，無候選窗也無紅線。原因是 `im.rime.inputmethod.Squirrel.Hant` 不在已啟用的輸入來源（Ctrl+Space 只在 ABC 與系統注音間循環；TIS 選取回傳 0 但不生效）。需要使用者在「系統設定 > 鍵盤 > 輸入方式」重新加入「鼠鬚管（繁體）」後才能續測。紅線是否顯示仍未驗證。

## 改為候選窗紅色高亮

- [x] 取消組字區底線；`SquirrelPanel.m` 在選取候選帶校錯建議時將高亮底色改紅、字改白。patch 只剩此檔，helper 改為 `LiurProofreadHint.h`，原生測試為 `test-hint.m`（通過）。
- [x] 重新建置並簽章，驗證 Hardened Runtime，執行檔已不含底線面板；新套件為 `.squirrel-proofreader/original/Squirrel-Liur-Underline.pkg`，備份 `~/Library/Rime/backups/squirrel-app-20261028-010708`。
- [x] 使用者在 macOS 安裝程式完成管理員認證；已安裝的執行檔雜湊與新建置一致，舊行程已重啟。
- [x] 使用者自行確認紅色高亮已出現，並表示不需要我再做實機測試。我自己的 TextEdit 自動按鍵測試未取得畫面（直接送 Unicode 的 `備` 不經過蝦米字碼），因此換候選與 Tab 的行為沒有我這邊的截圖紀錄。
