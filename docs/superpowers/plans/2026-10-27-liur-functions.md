# 同音字查詢與多國語言 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 加入已確認的同音字查詢與四種語言切換指令，並套用到使用者的 Mac。

**Architecture:** Rime 原生字典提供字碼和帶調拼音資料。Lua processor 管理指令與兩階段選字，segmentor 依語言標記一般字碼，translator 列出同音字；各注音與反查模式繼續使用現有流程。

**Tech Stack:** Rime YAML、librime-lua、原生 Rime C API 整合測試。

---

### Task 1: 操作與分段

Files: `Rime/lua/liur_features.lua`, `Rime/liur.schema.yaml`。

- [x] 在獨立設定目錄重現缺少指令與同音字查詢的行為。
- [x] 加入 `lua_processor@*liur_features*processor` 和 `lua_segmentor@*liur_features*segmentor`，保留 recognizer 的一聲設定。
- [x] 加入四選一模式、簡體和日文 table translator；只有一般字碼依模式分段，注音等 matcher 已辨識的段落不介入。
- [x] 加入原字查詢前綴與原生詞庫讀音查詢，`Memory:dict_lookup(reading, false, 0)` 查完整同音字，`ReverseLookup("terra_pinyin")` 查所有聲調讀音。

### Task 2: 整合驗證

Files: `develop/test-rime-features.py`。

- [x] 測試 `,,c oek ` → 呒、`,,ct cofu ` → 虾、`,,j fqo ` → 畑、`,,t a ` → 對。
- [x] 測試 `'mnfo ` 先列同音字而不上屏，再以數字選到蝦；驗證方向鍵、翻頁、取消、返回及多音字。
- [x] 測試 `';su  ` 一聲、`';5j/ jp6 ` → 中文、其他聲調、拼音與 Enter 英文。
- [x] 測試語言切換的來源碼表確實不同，且指令不上屏；確認既有 symbol、造詞與讀音反查仍可使用。

### Task 3: 文件與本機部署

Files: `README.md`, 本機 `~/Library/Rime`。

- [x] 說明新功能按鍵、日文假名後綴、Lua 外掛需求與檔案複製方式。
- [x] 備份本機涉及的設定與 Lua 檔案，只套用此次修改，執行 Squirrel `--reload`。
- [x] 確認部署產物包含新設定與模式字典，重新讀取部署設定測試，檢查 `git diff --check`。

使用者已要求直接執行；本次在原對話內依步驟執行，不另開執行選擇或審批流程。

驗證結果：專案全新部署與正式部署副本各通過 22 項原生 Rime 整合測試。正式設定已於 2026-10-27 套用並重新部署，原檔備份於 `~/Library/Rime/backups/liur-functions-20261027-182315`，客製按鍵設定指紋比對一致。
