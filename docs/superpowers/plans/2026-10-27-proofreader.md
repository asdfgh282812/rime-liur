# 台灣繁中校錯提示 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 在原有選字區提供可忽略、可自行採用的小模型校錯提示。

**Architecture:** CKIP ALBERT Tiny 匯出為 ONNX，獨立程序經本機 socket 提供保守的同音字評分。Lua filter 增加註解，processor 處理 Tab 與近期中文；短時間查詢失敗便保留原結果。

**Tech Stack:** Python、ONNX Runtime、Lua、C socket client、Rime C API。

---

- [x] `develop/export-proofreader-model.py`：固定官方來源版本，匯出最後一個遮罩字的 logits；量測模型大小與延遲。
- [x] `proofreader/service.py`：詞庫保護、同音候選限制、模型分數差門檻、短詞檢查；測試備住→備註，居住等正常詞不提示。
- [x] `proofreader/client.c`：獨立執行、有固定逾時的本機 socket client，封包及回應限制長度；失敗不輸出建議。
- [x] `Rime/lua/liur_proofreader.lua` 與 schema：保留候選排序，加註建議、Tab 採用、開關、上下文清除；不在輸入法程序載入模型。
- [x] `develop/test-proofreader.py`：測試模型正反例、無服務／慢服務、提示與採用、關閉；執行既有 Rime 整合測試。
- [x] `develop/install-proofreader.py` 與 README：備份、安裝模型與本機服務、啟停與移除說明；套用並讀取正式部署副本驗證。

使用者已授權直接試作，本次在既有對話依序完成，不再要求重複核准。

實機確認的最終修正：原廠 Squirrel 0.18 的 Library Validation 會拒絕不同 Team ID 的 `.so`。改成 Lua 經 `io.popen` 呼叫獨立 C client，保持原廠簽章與安全設定。38 項測試通過後，使用者授權系統按鍵模擬並開啟輔助使用權限；在原廠鼠鬚管的 TextEdit 新文件實測 `p 空白 pak` 已顯示提示，Tab 已上屏「備註」，均保存實際截圖。正式設定備份：`~/Library/Rime/backups/proofreader-20261027-232214`。

完成驗證：36 項測試通過；正式部署副本連到實際背景服務，確認 Tab 上屏「備註」、空白上屏「備住」。模型 16,266,559 bytes，較長左上下文的 100 次暖機推論中位數約 2.4ms、P95 約 3.1ms（Apple M2 Pro，僅模型時間）。正式設定已備份至 `~/Library/Rime/backups/proofreader-20261027-223819`。

實際載入相容性修正：先前測試使用 RTLD_GLOBAL，掩蓋了 Squirrel 的 RTLD_LOCAL 環境下找不到 Lua 符號的錯誤。已先在 LOCAL 環境重現失敗，再改為明確連結 librime-lua 並設定 rpath，36 項測試通過；另新增 2 項 launchd 重啟時序回歸測試通過。已重新安裝並部署，備份位於 `~/Library/Rime/backups/proofreader-20261027-230322`。

刪除與提示穩定度修正：已上屏 Backspace 回退一字、組字刪改與取消保留前文；候選導航和前端顯示選項不再清空上下文。閒置延長為 120 秒，僅在新組字開始時判斷；暫時連線失敗不快取為沒有建議。46 項完整測試及 1 項連線恢復回歸測試通過，實際鼠鬚管連續三次刪住重打 pak 均再次顯示提示，Tab 確認上屏備註。已備份並套用 `~/Library/Rime/backups/proofreader-context-20261027-234237`；實機截圖 `liur-proofreader-retype-after-delete.png`。

重複內容漏報修正：已量測「備註備住備」的全句模型註／住分數差只有 1.71，低於門檻 3，並非輸入字數限制。加入詞庫與詞界保護的局部回退，門檻提高至 4／0.90；正常準備＋住不回退。51 項完整測試通過，補測注意／帳號的重複錯字也通過。在原廠鼠鬚管實際輸入截圖相同的「備註備住備pak」已再次提示，Tab 驗證文件為「備註備住備註」。已套用，備份 `~/Library/Rime/backups/proofreader-20261027-235420`；實機截圖 `liur-proofreader-repeated-context.png`。
