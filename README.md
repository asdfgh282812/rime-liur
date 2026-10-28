# 鼠鬚管(RIME) + 嘸蝦米 with 注音模式 + 拼音模式 + 讀音反查 + 簡繁轉換 + 中英混輸
[blog好讀版](https://blog.typeart.cc/rime-liur/guide/)

[我的修正方法](https://blog.typeart.cc/rime-liur/fix/)

## 功能
基於[PTT/afrink大大的RIME-蝦米方案(iOS、中英混輸、動態造詞)](https://www.ptt.cc/bbs/Liu/M.1546884178.A.B99.html)

### 基於afrink大大的功能
此段取自[PTT/afrink大大的RIME-蝦米方案(iOS、中英混輸、動態造詞)](https://www.ptt.cc/bbs/Liu/M.1546884178.A.B99.html)

1. **注音模式：** 以「`';`」鍵引導可進行注音輸入(但無法透過數字鍵選字)
    - 一聲按空白鍵，二、三、四聲與輕聲分別按 `6`、`3`、`4`、`7`。輸入聲調後，再按空白鍵即可送出候選字。
    - 例如輸入 `';su`（ㄋㄧ）後按空白鍵，會顯示 ㄋㄧˉ 的候選字；再按空白鍵即可送出。Enter 鍵仍用於送出原始英文輸入碼。
2. **拼音模式：** 以「\`」鍵(上排數字鍵1左邊)引導可進行拼音輸入
3. **讀音反查：** 以「`;;`」鍵引導並輸入無蝦米碼，可反查該字讀音，如「龘」=`ㄉㄚˊ`
4. **日文漢字/罕用字輸入功能**
    1. 字典檔包含日文漢字如「辻」「雫」「渋」等…。不需要的人，可至`liur.extended`中，把`- liur_Japan`這行註解掉
    2. 可透過`ctrl + /`切換至擴充字集，輸入罕用字，如四個金(AAAA)等字
5. **複合型查碼：**
    1. 於造詞、拼音、注音模式下鍵入`ctrl + '`(Enter鍵左邊)，可直接查詢蝦米編碼，
    2. 於注音或拼音模式下，可以進行以詞查碼
        (例：於注音模式下輸入ㄍㄢㄍㄚ或拼音模式下輸入ganga，再切換查碼就可以
        找出「尷尬」這個詞的所有蝦米編碼，減少選字)
        於造詞模式下，則可以反查出該字及其候選字的所有編碼(例：輸miep，可以查
        出微、徵、徽、徾、鰴、徴)等字的蝦米編碼
6. **簡繁轉換：** 於任何模式下透過`ctrl + .`，可進行即時簡繁轉換，無須切換模式
7. **中英混輸：** 在不切換輸入法的情形下，可以空白鍵上中文字或中文符號；Enter鍵上英文字或英文符號
8. **shift切換中英輸入：** afrink大大在ptt沒寫到，但是目前版本可用shift切換中英輸入，caps lock變為大寫，如同Windows習慣
    1. 我跳MacOS也3年多了，目前工作會雙平台交互使用，實在是不喜歡MacOS下用caps lock來切換中英輸入，每次大小寫都搞得我很混亂
    2. 在長段落用全英文輸入時，亦可shift切換，不必enter上詞！
    3. 甚至是含大寫的英文句子，可直接shift + 英文，再放開shift繼續輸入小寫，最後enter上詞！
---
### 我修正、新增的功能
1. **修正MAC下無法使用注音模式、讀音反查**
    - 因鼠鬚管預設只有拼音，無注音輸入，導致MAC下直接安裝會無法使用這2個功能
2. **修正自動造詞失效**
    - 現在照著PTT文章說明的方式造詞也可以順利造詞了！
    - EX:輸入
      ```
        ;ci`aj`oxx`ohe`
        註：最後一碼的`，可以不輸入
        邊造詞的同時，編碼打出來的字也會同時出現在下方
      ```
      即可自動將`中華民國`加入自定義詞彙，以後輸入`caoo`就可以得到中華民國
    - 因mac的鍵盤只有backspace(往前刪除)，無del，測試發現若要刪除自動造詞，按`Control+k`就行
    - 如要刪除前例造的`caoo`→`中華民國`，先打出`caoo`，接著按`Control+k`或`backspace`即可清除
3. **修正自定義詞彙順序** 
    - 預設會排在第一碼，影響原本字碼使用。現在會乖乖的排在原本字碼後面了
    - 已回報原作者afrink，原作者反饋之後更新會修正
4. **增加`squirrel.custom.yaml`：** 用以開啟被RIME預設關閉中文輸入的程式(如VS、VSCode、iTerms...)
    1. 因RIME預設有關閉特定程式的中文輸入，只能輸入英文，如VSCode、iTerms等。詳見[官方文件/在特定程序裏關閉中文輸入](https://github.com/rime/home/wiki/CustomizationGuide#%E5%9C%A8%E7%89%B9%E5%AE%9A%E7%A8%8B%E5%BA%8F%E8%A3%8F%E9%97%9C%E9%96%89%E4%B8%AD%E6%96%87%E8%BC%B8%E5%85%A5)
    2. 若常用的工具被RIME關閉，可在此文件自行加入開啟
    3. 預設先加入VSCode，其餘程式可照抄改成自己的程式就可以了
5. **增加六大主題：** 整合[RIME『洋蔥 純注音 版』注音設定檔](http://deltazone.pixnet.net/blog/post/264319309-%E9%BC%A0%E9%AC%9A%E7%AE%A1%E6%B3%A8%E9%9F%B3%E6%96%B9%E6%A1%88---%E7%AC%A6%E5%90%88%E4%B8%80%E8%88%AC%E6%B3%A8%E9%9F%B3%E4%BD%BF%E7%94%A8%E8%80%85%E7%BF%92%E6%85%A3%E8%A8%AD)之主題樣式
    1. 特別感謝L’Étranger 大大提供主題
    2. 於`squirrel.custom.yaml`選擇喜歡的主題
6. **調整選字順序與官蝦一致：** 鼠鬚管選字順序由1開始排起，導致所有字碼順序會比官蝦往後多一位。調整由0開始，讓字碼順序如同官方嘸蝦米。
7. (2022/07/02)**修正注音模式，無法輸入ㄦ的bug：**有人反應注音模式下輸入ㄦ，無法順利讀取ㄦ。修正此 bug

### 同音字查詢與多國語言模式

這兩項功能需要 **librime-lua** 外掛。Mac 可使用內附此外掛的鼠鬚管版本；部署時請一併複製 `Rime/lua` 資料夾及所有方案檔案。

**同音字查詢**（[官方操作說明](https://boshiamy.com/tutorial_function.php?page=5&sub=2)）：

1. 輸入 `'`，再輸入一個同音字的蝦米碼，例如 `'mnfo`，候選字會出現「瞎」。
2. 按空白鍵或數字鍵選原字，此時會列出「瞎、蝦、呷……」等同聲調的同音字，不會立即送出原字。多音字會合併各讀音的候選字。
3. 再按空白鍵送出反白的字，或以數字鍵直接選字。支援上下鍵和翻頁，選字鍵仍由 `0` 起算。
4. 第二階段按 Backspace 可回到原字碼；任一階段按 Escape 可取消。查無讀音時，可選擇保留原字。

**多國語言輸入**（[官方操作說明](https://boshiamy.com/tutorial_function.php?page=5&sub=7)）：

輸入下列指令後按**空白鍵或 Enter**，即可切換模式；指令本身不會送到文件。也可從 Rime 的方案選單切換。

| 指令 | 模式 | 範例 |
| --- | --- | --- |
| `,,c` | 簡體字碼 | `oek` → 呒；使用 `liur_TradToSimp` 碼表 |
| `,,ct` | 打繁出簡 | 繁體蝦米碼 `cofu` → 虾 |
| `,,j` | 日文 | `fqo` → 畑、`a,` → あ、`a.` → ア |
| `,,t` | 返回繁體中文 | `cofu` → 蝦 |

日文假名使用羅馬拼音加逗號（平假名）或句號（片假名），例如 `ka,` → か、`ka.` → カ。語言模式切換時會清除先前 `Ctrl+.` 的轉簡狀態；每次重新載入方案預設回到繁體。注音、拼音與反查的引導鍵維持原設定。

字碼、候選字順序和讀音依本專案碼表及地球拼音詞庫而定，與官方商業版的詞庫不一定完全相同。

Mac 開發者可執行 `python3 develop/test-rime-features.py`，在暫存目錄驗證部署、模式切換、同音字選字與原有輸入功能，不會修改正式設定或正式使用者詞庫。

### 離線繁體中文校錯提示（Mac 原型）

在繁體模式輸入「備」後，再打出「住」的蝦米碼 `pak`，候選字仍是原本的「住」，註解會顯示 **建議「註」：備註〔Tab採用〕**。

- **Tab**：採用建議，送出「註」。
- **空白／數字鍵**：照原本方式送出「住」。Enter 仍輸出原始英文碼。
- 打成「備住」後，用 **Backspace 刪掉「住」再輸入 `pak`**，仍會再次提示「備註」；刪改尚未送出的字碼或按 Escape 取消組字，也會保留已輸入的前文。
- 在 Rime 選單切換「校錯提示／關閉校錯」即可開關；簡體與日文模式不啟用。

模型使用 [CKIP ALBERT Tiny](https://huggingface.co/ckiplab/albert-tiny-chinese)，約 16.3 MB，保留官方模型來源與 GPL-3.0 授權資訊。使用同音候選、地球拼音的讀音與既有詞庫保護正常詞，模型只在分數差與信心達門檻時提出建議。這是原型，範例通過不代表能抓出所有錯字。

可連續輸入多於兩字或 32 字，只有評分使用的左上下文保留末 32 字。重複輸入錯字可能干擾小模型的長上下文判斷，因此整段評分沒有明確建議時，會另外以目前局部詞語評分，採更嚴格的分數差與信心門檻；不同局部判斷衝突時不提示。局部回退也會保護完整詞的邊界，避免將「我準備住進新家」誤拆成「備註」。這仍是選字中的單字提示，不是整篇或完整句子的校對器。

只檢查第一個候選字，且必須是單一中文字。使用本次輸入的最近最多 32 個中文字作為左上下文；Backspace 會回退相對應的字，修改字碼和候選上下選字不會清空前文。閒置超過 2 分鐘且開始新的組字、鍵盤移動文件游標、向前刪除、切換語言或非中文上屏時會清除。已顯示的提示不會因閱讀停頓而失效；與文字無關的候選視窗選項也不再清空上下文。無法得知滑鼠移動後的文件游標位置，也不讀取文件全文；不會修改已送出的文字或提供紅線標示。

日常推論只使用 **NumPy、ONNX Runtime**，在獨立的本機程序執行，沒有雲端請求或文字日誌。輸入法透過獨立的小型連線程式查詢，socket 等待上限為 50 毫秒，另有子行程啟動成本；服務不存在或逾時就維持原結果。最近的短文字經本機子行程參數傳遞，不寫入檔案或日誌。模型權重、執行環境與實際記憶體用量分開計算；PyTorch、Transformers 只用於首次匯出模型。

首次設定需要先安裝 Python 3、librime-lua 與 Mac 命令列開發工具，再於本專案執行：

```sh
# 建置環境（可在匯出完成後移除）
python3 -m venv --system-site-packages /tmp/liur-model-build
/tmp/liur-model-build/bin/python -m pip install 'torch>=2.6,<3' 'transformers>=4.51,<5' onnx
/tmp/liur-model-build/bin/python develop/export-proofreader-model.py .proofreader-model

# 日常執行環境與安裝
python3 -m pip install numpy onnxruntime
python3 develop/test-proofreader.py
python3 develop/install-proofreader.py
```

安裝程式會備份涉及的原檔、編譯小型本機連線程式、建立登入時啟動的背景服務，並重新部署；保留個人的 `.custom.yaml` 和詞庫。`Rime` 目錄本身不包含模型，單純複製方案不會下載或啟動模型，其他功能仍可正常使用。

若要連同背景服務一起停用，可執行 `python3 develop/install-proofreader.py --disable`；重新執行安裝可再次啟用。背景程序僅在模型初始化失敗等情況寫入 `~/Library/Rime/proofreader/service-errors.log`，不記錄查詢文字。

若早期原型的背景服務正常，卻始終沒有提示，請重新執行安裝程式。原廠鼠鬚管會拒絕載入不同 Team ID 的外部動態函式庫，目前已改用獨立連線程式，不再載入 `.so`，也不更動原廠程式簽章與安全設定。除了引擎測試，已在原廠鼠鬚管實際輸入並確認提示和 Tab 採用。

### 內建校錯與紅色標示：直接更新現有鼠鬚管

`develop/build-original-squirrel-underline.py` 使用官方 Squirrel 0.18 原始碼加上校錯標示修改：選取的候選附有校錯建議時，候選窗中該列的高亮底色改為紅色、字為白色，換到沒有建議的候選即恢復原本顏色。修改只在候選窗（`SquirrelPanel.m`），不再對應用程式的組字區加底線，因此不受各應用程式處理組字樣式的影響。保留原本的 App 名稱、輸入來源識別、連線名稱及 `~/Library/Rime` 設定。需要本機既有的 Apple 開發簽章憑證；程式與所有載入的函式庫使用同一份開發憑證重新簽章，保留 Hardened Runtime 與函式庫驗證，不關閉系統安全設定。

內建版本將模型（約 16 MB）、Python、NumPy 和 ONNX Runtime 一起封裝在 App，使用者不需另外安裝 Python。鼠鬚管啟動時自動開啟校錯程序，退出時一同結束；程序意外退出會限速重啟，父程序異常結束時也會自行退出。啟動暖機尚未完成時暫無建議，一般輸入可照常使用。

建置工具需先安裝 PyInstaller；這是開發端相依套件：

```sh
python3 -m venv --system-site-packages .squirrel-proofreader/bundle-tools/venv
.squirrel-proofreader/bundle-tools/venv/bin/python -m pip install 'pyinstaller==6.16.0'
```

```sh
security find-identity -v -p codesigning
python3 develop/build-original-squirrel-underline.py --identity <開發憑證的識別碼>
```

工具先逐檔核對完整 App 備份與腳本簽章屬性，再產生 `.squirrel-proofreader/original/Squirrel-Liur-Builtin.pkg`。備份位於 `~/Library/Rime/backups/squirrel-app-時間戳/`，其中 `manifest.json` 記錄原始與修改後的執行檔雜湊；`files.json` 記錄全部檔案與簽章屬性。安裝套件只更新 `/Library/Input Methods/Squirrel.app`，不包含 Rime 個人設定或使用者字庫；系統管理員認證必須在 macOS 視窗完成。原廠自動更新會覆蓋此本機修改，更新後需要重新評估相容版本。

從舊的獨立背景服務升級時，完成安裝後執行一次：

```sh
bash develop/activate-builtin-proofreader.sh
```

遷移工具先驗證已安裝 App 的簽章與實際模型推論，再備份 Lua、連線程式和 LaunchAgent、停止舊服務，然後重啟鼠鬚管並確認內建 socket 能回覆。失敗會還原設定。內建版本使用 `builtin.sock`；舊版服務的 `checker.sock` 不會被測試程序佔用。舊模型檔暫留作還原備份。

可用 `python3 develop/test-builtin-proofreader.py` 驗證封裝推論、socket 權限、崩潰重啟及父程序退出。`LIUR_BUNDLED_CHECKER` 可指定封裝後執行檔，讓 `develop/test-proofreader.py` 對它跑既有整合測試。

安裝後須用真正按鍵驗證 `備pak` 時選取列變紅、換候選後恢復與 Tab 採用；原生 helper 測試和簽章驗證不能代替實機結果。

## MAC下安裝【鼠鬚管 + 嘸蝦米】完整流程
### 自動安裝
(2021/12/26新增)
增加批次指令，一鍵安裝嘸蝦米
若曾經安裝過或有自己的客制化，請記得**備份自己的設定檔再執行指令**
或經由手動安裝步驟自行操作

1. 到[rime官方](https://rime.im/download/)下載鼠鬚管並安裝
    - 若安裝完後沒有自動帶出輸入法，先照安裝步驟登出 -> 登入後，打開鍵盤，選到【簡體中文】，就會看到【鼠鬚管】了！
2. 打開終端機(terminal)，輸入`curl -fsSL https://git.io/rime_liur_installer | bash`
3. 開始使用嘸蝦米！

### 手動安裝

1. 到[rime官方](https://rime.im/download/)下載鼠鬚管並安裝
2. 使用[plum](https://github.com/rime/plum)安裝注音輸入法包
    - **安裝方法：** 打開終端機，執行`curl -fsSL https://git.io/rime-install | bash`就會自動將注音輸入的yaml檔放進rime的`用戶設定`裡。此時尚未真正將注音安裝進RIME
    - 此安裝指令由[plum說明文件](https://github.com/rime/plum#usage)提供
    - 若不須嘸蝦米，直接跳最後一步，按`部署`就可以有注音輸入了
3. 打開鼠鬚管按`用戶設定`，將本專案 `Rime` 目錄內的檔案與資料夾放進去，包含 `lua` 資料夾及新增的相依方案；更新前先備份自己的客製設定與詞庫
4. (若不需要則跳過此步)打開`liur_customWords.dict.yaml`，將自己常用的自定義詞彙加入
    - **注意！中間須以`<tab>`隔開**。格式：`<自定義文字><tab><編碼>`
    - 如想用`tptr`打出`台北火車站`，則輸入`台北火車站<tab>tptr`
5. 鼠鬚管按`重新部署`，會開始安裝所有輸入法(約莫30秒~1分鐘)，安裝好後會出現`部署完成`，可以開始使用！

## 未來再增加自定義詞彙

1. 一樣加在`liur_customWords.dict.yaml`
2. 再按重新部署

因已安裝好注音，此時重新部署只需要3~5秒就行
除非將整個build目錄刪除使其重新產生

## 增加英文字典(預設關閉)
- 感謝 [yozian](https://github.com/yozian) 大大提供
- 英文字典來源於 [Github  dwyl/english-words](https://github.com/dwyl/english-words)
- 現行已產生出英文字典檔，預設關閉
- 若要開啟英文字典，打開`liur.extended.dict.yaml`，將`# - liur_English`改成`- liur_English`(即刪除前面的`#`)
- 或可使用 nodejs 執行以下指令後，自行手動建立或更新 `Rime/liur_English.dict.yaml` 檔案
``` bash
$ node develop/create-english.dict.js 
```

功能如下：

方便打英文時自動帶出英文單字
![rime-eng-word](https://user-images.githubusercontent.com/11897061/146645594-a41d499f-3ba6-4aab-9ab1-94074a3a7c2f.png)

英文單字， 字碼小於 3 碼者，需補上 「;」 當結束 (或可以直接按 enter )
![rime-eng-word-less-than-3](https://user-images.githubusercontent.com/11897061/146645685-66060eb2-f6d0-47c1-b5f5-abaf33217e6f.png)
## FAQ
### 更新到 Monterey 後，無法安裝鼠鬚管

若安裝完後沒有自動帶出輸入法，先照安裝步驟登出 -> 登入後，打開鍵盤，選到【簡體中文】，就會看到【鼠鬚管】了！

### 按 Caps Lock 仍會切換成英文，但想要與 Windows 習慣一致，Caps Lock 純切換大小寫、shift 切換中英打

1. 點擊右上角的輸入法
2. 打開`鍵盤偏好設定`
3. 取消勾選`使用「中/英」鍵來切換「ABC」及目前輸入方式`

### 我部署使用一段時間後，又有再增加自定義詞彙，但後面加的一直沒有出現？
請先確認是否有按重新部署。若按了仍然無效
到BUILD資料夾，將`liur`開頭的檔案刪掉，如下：
1. liur.schema.yaml
2. liur.extended.table.bin
3. liur.extended.reverse.bin
4. liur.extended.prism.bin
5. default.yaml

重按部署

懶得找也可以直接刪掉BUILD目錄，讓他全部重新產生
但也會再安裝一次注音輸入，花較多時間
