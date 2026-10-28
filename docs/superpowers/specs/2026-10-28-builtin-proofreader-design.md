# 鼠鬚管內建校錯

使用者已同意把模型、執行環境與連線程式一起包進現有 Squirrel.app，由輸入法管理獨立校錯程序，不需使用者安裝 Python 或另設 LaunchAgent。保留紅色候選高亮、Tab 採用與原有繁體中文校錯規則。

採 PyInstaller onedir 封裝既有 Python/NumPy/ONNX Runtime，模型、詞表與授權資料放 App SharedSupport，原生 NSTask 管理 helper，退出時終止、父程序異常退出時 helper 自行結束，意外退出採有限頻率重啟。正常打字不得等待模型初始化；服務未就緒時略過提示。

Lua 優先讀鼠鬚管提供的內建 client/socket 環境變數，其他前端沿用既有設定。內建 socket 與舊服務分開。遷移工具先確認已安裝的內建 helper 真能推論，再備份並停止舊 LaunchAgent、更新 Lua 及連線程式。模型、Python 與動態函式庫均在 App 內，簽章保留 Hardened Runtime 與函式庫驗證。

本機建置 arm64；備份原 App 後產生更新套件，安裝認證由使用者在系統視窗完成。不得以建置成功代替安裝後驗證。
