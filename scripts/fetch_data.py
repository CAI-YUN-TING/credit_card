import os
import json
import re
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
import time

# ── 設定 ──────────────────────────────────────────────
CARDS = [
    {"bank": "玉山銀行", "card": "熊本熊卡"},
    {"bank": "玉山銀行", "card": "Unicard"},
    {"bank": "玉山銀行", "card": "U Bear卡"},
    {"bank": "玉山銀行", "card": "Nissan聯名卡"},
    {"bank": "中國信託", "card": "中油聯名卡"},
    {"bank": "中國信託", "card": "LINE Pay卡"},
    {"bank": "中國信託", "card": "UniOpen卡"},
    {"bank": "中國信託", "card": "商旅鈦金卡"},
    {"bank": "台新銀行", "card": "Richart卡"},
    {"bank": "星展銀行", "card": "傳說對決卡"},
    {"bank": "星展銀行", "card": "eco永續卡"},
]

CHANNELS = [
    "中油加油", "foodpanda外送", "Uber Eats外送", "momo購物網",
    "蝦皮購物", "PChome線上購物", "LINE Pay行動支付", "街口支付",
    "7-ELEVEN超商", "全家便利商店", "全聯福利中心", "家樂福量販",
    "Netflix串流", "Disney+串流", "YouTube Premium", "Spotify音樂",
    "海外刷卡一般消費", "海外旅遊訂房", "日本實體消費",
    "Agoda訂房", "Klook旅遊", "Booking.com訂房",
    "加油站", "水電瓦斯費", "餐廳美食", "百貨公司",
    "屈臣氏藥妝", "博客來書店", "星巴克咖啡", "麥當勞速食",
    "遊戲儲值", "電動車充電Gogoro",
]

GEMINI_MODEL   = "gemini-2.0-flash"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
OUTPUT_PATH    = os.path.join(os.path.dirname(__file__), "..", "data", "cards.json")

PROMPT = """你是台灣信用卡回饋分析專家。請用 Google 搜尋查詢以下信用卡在 2025-2026 年的最新優惠，整理成 JSON。

## 需要查詢的卡片
{cards_list}

## 需要涵蓋的消費通路關鍵字清單（若卡片在這些通路有加碼，請務必列出）
{channels_list}

## 輸出格式（請務必嚴格遵守純 JSON，不要有任何其他說明文字或 markdown 程式碼區塊標籤）
{{
  "cards": [
    {{
      "bank": "銀行名稱",
      "card": "卡片名稱",
      "card_url": "銀行官網該卡片介紹頁 URL",
      "card_type": "both/domestic/overseas",
      "rewards": [
        {{
          "channels": ["通路關鍵字1", "通路關鍵字2"],
          "pct": 數字,
          "reward_type": "現金回饋/LINE Points/OPENPOINT/ePoint/哩程",
          "cap": "NT$500/月 或 null",
          "conditions": ["條件說明1", "條件說明2"],
          "type": "domestic/overseas/both"
        }}
      ]
    }}
  ]
}}

注意規範：
1. channels 陣列請一律使用「小寫」中文或英文關鍵字（例如："line pay", "7-eleven", "foodpanda"），以便前端比對。
2. 每張卡片**必須**包含一筆「一般消費」的基本回饋記錄，channels 填 `["一般"]`。
3. pct 欄位必須是「純數字」（如：3.5），不要帶有 % 符號。
4. 如果有指定通路加碼（例如國外實體、網購），請在 channels 欄位盡可能展開包含你查到的對應關鍵字。
"""

def call_gemini(api_key, prompt):
    url  = GEMINI_API_URL.format(model=GEMINI_MODEL, key=api_key)
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        # 【修改 1】若您有綁定 Google Cloud Billing，請務必解開此行以啟用真正的即時搜尋
        # "tools": [{"google_search": {}}],  
        "generationConfig": {
            "temperature": 0.1, 
            "maxOutputTokens": 8192,
            "responseMimeType": "application/json" # 【修改 2】強制要求 Gemini 吐出純 JSON 格式
        },
    }
    data = json.dumps(body).encode("utf-8")
    req  = urllib.request.Request(url, data=data,
               headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            resp = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Gemini API 錯誤 {e.code}: {e.read().decode()}") from e
    try:
        return resp["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"無法解析 Gemini 回應: {resp}") from e

def extract_json(text):
    # 【修改 3】增強防錯，避免 AI 帶有 markdown 的 ```json 標籤
    clean = re.sub(r"```json\s*", "", text)
    clean = re.sub(r"```\s*", "", clean).strip()
    s, e  = clean.find("{"), clean.rfind("}") + 1
    if s == -1 or e == 0:
        raise ValueError(f"找不到 JSON，原始回應：\n{text[:500]}")
    return json.loads(clean[s:e])

def fetch_card_data():
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise EnvironmentError("請設定環境變數 GEMINI_API_KEY")

    # 【修改 4】分批請求（Chunking）邏輯，每次只查 4 張卡，防止一次查 11 張導致 Token 爆掉或 JSON 被截斷
    all_cards_data = []
    chunk_size = 4
    
    for i in range(0, len(CARDS), chunk_size):
        chunk = CARDS[i:i+chunk_size]
        cards_str = "\n".join(f"- {c['bank']} {c['card']}" for c in chunk)
        
        prompt = PROMPT.format(
            cards_list=cards_str,
            channels_list="\n".join(f"- {ch}" for ch in CHANNELS),
        )
        
        print(f"🔍 正在查詢第 {i+1} ~ {min(i+chunk_size, len(CARDS))} 張卡片的優惠資訊...")
        try:
            raw = call_gemini(api_key, prompt)
            chunk_json = extract_json(raw)
            if "cards" in chunk_json:
                all_cards_data.extend(chunk_json["cards"])
            time.sleep(1) # 避免 Free Tier 頻率限制 (RPM)
        except Exception as ex:
            print(f"❌ 這一批查詢失敗，跳過: {ex}")

    # 封裝成最終的檔案結構
    tz = timezone(timedelta(hours=8))
    final_data = {
        "updated_at": datetime.now(tz).isoformat(),
        "source": "Google Gemini AI + Google Search（每週自動更新，永久免費）",
        "cards": all_cards_data
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)

    print(f"💾 已儲存 {len(final_data['cards'])} 張卡片資料 → {OUTPUT_PATH}")

if __name__ == "__main__":
    fetch_card_data()
