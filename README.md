# Daily Brief — RSS 智慧過濾每日簡報

一條指令，把你關注領域的新文章過濾成一份簡報，推送到 Email 或 Telegram。

## 為什麼不用 AI

這個工具的價值在**規則明確的過濾與排序**：關鍵字比對、URL 去重、時間窗控制—— 都不需要推理。加入 LLM 只會增加成本與不確定性，讓輸出每次措辭不一致，而簡報最需要的是**可預測**。

用「確定性規則 + 零 API 成本」換掉不確定性，這是刻意的取捨。

## 特色

- **關鍵字過濾** — 只收你真正關心的內容，噪音自動排除
- **跨來源去重** — 同一篇文章在不同網址轉載只出現一次
- **分類軸** — 可自訂分類（如「AI 前沿」「社群熱門」）
- **純文字輸出** — 適配 Email 與 Telegram，不會出現格式亂碼
- **零依賴** — 只用 Python 標準庫，不需要 pip install
- **不會炸** — 單一來源失敗不影響其他內容，內建 retry

## 需求

- Python 3.11 以上（需要 `tomllib`，3.11 內建）
- 不需要安裝任何第三方套件

## 安裝

```bash
git clone <你的 repo>
cd daily-brief
python3 src/daily_brief.py --init
```

## 設定

編輯 `config/config.toml`：

```toml
[meta]
title = "我的專業簡報"
keywords = [
  "agent", "llm", "docker", "automation",
]
require_all_keywords = false   # true = 必須全部命中

[[sources]]
name = "來源名稱"
axis = "分類名稱"
url = "https://example.com/feed.xml"
enabled = true
```

**關鍵字怎麼選**：建議 10–30 個。太少會雜訊多，太多會漏掉。

## 使用

```bash
python3 src/daily_brief.py                    # 產生今日簡報
python3 src/daily_brief.py --check            # 只檢查設定
python3 src/daily_brief.py --dry-run          # 抓取但不更新去重紀錄
python3 src/daily_brief.py --send telegram    # 推播 Telegram
python3 src/daily_brief.py --send email       # 寄出 Email
python3 src/daily_brief.py --limit 20         # 輸出幾條
```

## 推播設定

**Telegram**：
```toml
[telegram]
chat_id = "你的 chat id"
token_env = "TELEGRAM_BOT_TOKEN"
```
```bash
export TELEGRAM_BOT_TOKEN="xxx"
```

**Email**（需先安裝 [himalaya](https://github.com/Impostork/himalaya) 並完成設定）：
```toml
[email]
to = "you@example.com"
from = "you@example.com"
```

## 排程

```cron
# 每天早上 7 點推播（cron 用系統時區）
0 7 * * * cd /path/to/daily-brief && python3 src/daily_brief.py --send telegram
```

## 常見問題

**Q: 抓不到文章？**
先跑 `--check` 確認設定，再用 `--dry-run` 看錯誤訊息。單一來源失敗會在簡報底部列出。

**Q: 同一篇一直出現？**
URL 尾端的追蹤參數（`?utm_source=` 之類）會自動去掉。如果還是重複，代表來源網址本身不同。

**Q: state.json 會不會越來越大？**
不會。超過 90 天的紀錄會自動清除。

**Q: 可以加更多來源嗎？**
可以，複製 `[[sources]]` 區塊就行。建議先用 `curl -sSL -o /dev/null -w '%{http_code}\n' '<url>'` 測一下網址是否有效。

## 授權

MIT