# 校錯紅色虛線測試版

使用者已同意嘗試修改鼠鬚管，在有校錯建議時標記正在輸入的字碼。

## 行為

以「備」接「pak」為實測：目前反白候選「住」附有「備註」建議時，將尚未送出的 pak 加上紅色虛線。選取其他候選、取消、關閉校錯或送出後撤除標記。Tab 與空白的既有行為維持。

## 做法

以官方 Squirrel 0.18 的固定版本建立獨立測試 App，修改 showPreeditString 的 attributed string。只在 liur 方案且目前反白候選帶有既有校錯提示時加入 NSUnderlineColorAttributeName 與 NSUnderlineStyleSingle | NSUnderlinePatternDash。將提示狀態納入前端更新快取，避免同一字碼切換候選時紅線殘留。

測試版使用獨立 bundle ID、連線名稱與 Rime 資料目錄，不同時開啟正式版的使用者字庫。模型服務沿用本機既有 socket，不新增服務或系統權限。原廠 App 不修改。保留來源版本、patch、建置工具與測試紀錄；使用者可切回原廠鼠鬚管。

## 驗證

原生檢查紅線屬性、反白候選切換、關閉與復原狀態。註冊獨立輸入法後，在自己的 TextEdit 測試文件用實際按鍵輸入，截取 pak 紅線畫面並檢查 Tab 結果。能否讓應用程式保留紅線樣式必須由實機結果確認，不能以建置成功代替。
