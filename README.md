# 卡省力｜信用卡回饋最佳化

> 輸入消費通路，立刻找出你手上最划算的信用卡。
> 資料由 **Google Gemini AI + Google Search 每週自動更新**，使用者完全不需要任何 API Key。
> **永久免費** — Gemini Free Tier 每天 1,500 次請求，遠超本專案所需。

---

## 架構說明

```
GitHub Repo（你的）
├── .github/workflows/update.yml   ← 每週一自動執行
├── scripts/fetch_data.py          ← 向 Gemini 查詢並更新資料
├── data/cards.json                ← 快取的優惠資料（由 CI 自動更新）
└── index.html                     ← 網頁（從 cards.json 讀取，使用者不需任何 Key）
```

**流程：**
1. 每週一凌晨，GitHub Actions 自動執行 `fetch_data.py`
2. Python 腳本向 Gemini API（含 Google Search grounding）查詢最新信用卡優惠
3. 將結果存為 `data/cards.json` 並 commit 回 repo
4. 使用者開啟網頁時，直接讀取 `cards.json`，零延遲、不需任何 Key

---

## 部署步驟（約 10 分鐘）

### 第一步：Fork 這個 repo
點右上角 **Fork**，複製到你的 GitHub 帳號。

### 第二步：取得 Google Gemini API Key（免費）

1. 前往 [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. 點 **Create API key** → 選任意 Google 專案（或建立新專案）
3. 複製產生的 Key（格式：`AIza...`）

> 💡 完全免費，不需要信用卡，Google 帳號即可。

### 第三步：設定 GitHub Secret

1. 你 Fork 的 repo → **Settings** → **Secrets and variables** → **Actions**
2. 點 **New repository secret**
3. Name 填 `GEMINI_API_KEY`，Value 貼上剛才的 Key
4. 點 **Add secret**

### 第四步：啟用 GitHub Pages

1. repo → **Settings** → **Pages**
2. Source 選 **Deploy from a branch**
3. Branch 選 **main**，資料夾選 **/ (root)**
4. 點 **Save**

幾分鐘後網址就會是：
```
https://你的帳號.github.io/你的repo名稱/
```

### 第五步：立即執行一次更新

1. repo → **Actions** → **每週更新信用卡優惠資料**
2. 點 **Run workflow** → **Run workflow**
3. 等約 1 分鐘，`data/cards.json` 就會是最新資料

---

## 新增或修改信用卡

編輯 `scripts/fetch_data.py` 中的 `CARDS` 清單：

```python
CARDS = [
    {"bank": "玉山銀行", "card": "熊本熊卡"},
    # 新增你的卡片：
    {"bank": "國泰世華", "card": "CUBE卡"},
    {"bank": "富邦銀行", "card": "J卡"},
]
```

修改後 commit，下次自動更新就會包含新卡片。
或手動觸發 Actions 立即更新。

---

## 費用說明

| 項目 | 費用 |
|------|------|
| GitHub（public repo + Pages + Actions） | 永久免費 |
| Google Gemini API（Free Tier） | 永久免費 |
| 使用者瀏覽網頁 | 免費（無任何 API 呼叫） |
| **合計** | **$0** |

---

## 常見問題

**Q：使用者看到的資料有多新？**
A：最多落後 7 天。網頁右上角顯示最後更新時間，超過 10 天會出現警告。

**Q：Gemini Free Tier 有限制嗎？**
A：每分鐘 15 次、每天 1,500 次請求。本專案每週只用 1 次，完全不會觸及上限。

**Q：本地開發怎麼做？**
```bash
# 啟動本地伺服器（需要 server 才能讀取 JSON）
python3 -m http.server 8080
# 開啟 http://localhost:8080

# 手動執行資料更新
export GEMINI_API_KEY=AIza...
python scripts/fetch_data.py
```
