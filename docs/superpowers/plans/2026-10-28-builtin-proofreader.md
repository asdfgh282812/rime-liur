# 內建校錯實作計畫

- [x] 新增可封裝服務的父程序監看、自我檢查，以及 Lua 內建路徑支援。
- [x] 新增原生程序管理，接上鼠鬚管啟動與退出；驗證退出、異常重啟。
- [x] 封裝獨立 Python runtime、ONNX Runtime、模型、詞典、授權資料並完整簽章。
- [x] 跑既有校錯測試，測封裝 helper 的真實推論與無 Python 環境執行。
- [x] 建置、驗證套件及 App 備份，準備舊服務遷移工具。
- [x] 系統安裝認證後，遷移並驗證實際 App 生命周期及校錯。

## 驗證結果

- `python3 develop/test-builtin-proofreader.py`：4 項通過，真實封裝 helper 在清空環境、沒有外部 Python 路徑時可推論；原生 supervisor 啟動、SIGKILL 後重啟、正常退出及父程序異常退出均通過。
- `LIUR_BUNDLED_CHECKER=…/LiurChecker python3 develop/test-proofreader.py`：52 項通過，Lua 使用環境變數指定的 App 內 client 與測試 socket，含提示、Tab、候選切換、停用、逾時。
- `.squirrel-proofreader/original/Squirrel-Liur-Builtin.pkg`（約 80 MB）已用 pkgutil 解開，App 深層嚴格簽章驗證及解包 helper 的真實推論均通過；保留 Hardened Runtime 與 Library Validation。
- 安裝前完整 App 備份：`~/Library/Rime/backups/squirrel-app-20261028-110316`。
- 使用者已完成 macOS 安裝認證，安裝後執行檔 SHA-256 與建置產物一致。已執行 `bash develop/activate-builtin-proofreader.sh`；舊 LaunchAgent 已卸載，舊 Python service 行程已停止，備份為 `~/Library/Rime/backups/builtin-migration-20261028-110457`。
- 未 commit。

## 安裝後實機結果

- 正式鼠鬚管 PID 92423 自行啟動 App 內 LiurChecker PID 92427（PPID 92423），使用 `builtin.sock`，權限 0600；不依賴外部 Python。
- 在 TextEdit 新建「未命名2」，以實際蝦米按鍵輸入 `ldh iax`，第一次就顯示「議 建議『義』：意義〔Tab採用〕」紅底；下移候選變回藍底，上移後 Tab 送出「意義」。
- 接著輸入 `p pak`，顯示「住 建議『註』：備註〔Tab採用〕」紅底，Tab 送出「備註」。最終文件兩行為「意義」「備註」，保留在 TextEdit 供使用者查看。
- 安裝後自我檢查與實機校錯均通過；沒有 commit。
