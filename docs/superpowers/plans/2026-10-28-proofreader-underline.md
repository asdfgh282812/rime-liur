# Proofreader Underline Implementation Plan

**Goal:** 在獨立鼠鬚管測試版驗證有校錯建議時的紅色虛線。

**Architecture:** 固定官方 0.18 原始碼，添加最小前端 patch；重用現有模型建議與 Tab 採用。測試版以獨立資料目錄及輸入來源運作。

**Tech Stack:** Objective-C / AppKit / InputMethodKit / librime / Python 建置工具。

- [ ] 建立紅線樣式與選取候選判斷 helper，原生測試屬性與無提示情況。
- [ ] patch Squirrel showPreeditString 與快取、rimeUpdate 中提示判斷。
- [ ] 建立可重現建置工具，固定上游版本並保留來源與授權；產物使用獨立 App ID、連線、資料與更新設定。
- [ ] 建置並註冊獨立測試版，TextEdit 真正輸入 備pak、截圖、Tab 採用與候選切換測試。
- [ ] 依實機結果修正，記錄限制與切回方式。
