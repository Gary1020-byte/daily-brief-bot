# Daily Brief — RSS 關鍵字過濾每日簡報

一條指令把你關心的來源變成過濾後的簡報,推送到 Email 或 Telegram。

[English version](README.md)

## 為什麼這條 pipeline 裡沒有 AI

這個工具的價值在**規則明確的過濾與排序**:關鍵字比對、URL 去重、時間窗控制。
這些都不需要推理。加進 LLM 只會增加成本、讓輸出每次措辭不一樣 ——
而簡報最需要的是**可預測**。

用「確定性規則、零 API 成本」換掉不確定性,是一個刻意的選擇,不是限制。

## 特色

- **關鍵字過濾** —— 只留你真正在意的 topic
- **跨來源去重** —— 同一篇文章轉載到不同網址只出現一次
- **自訂分類軸** —— 把來源分進你自己的 lanes(例如「AI 實務」「社群熱門」)
- **純文字輸出** —— Email 與 Telegram 安全,不會有格式雜訊
- **零第三方依賴** —— 不用 `pip install`,沒有 dependency drift
- **單一來源掛掉不會全死** —— 逐來源 retry 與故障隔離

## 需求

- Python 3.11 以上(需要 `tomllib`,內建於 3.11+)
- 沒有第三方套件

## 安裝

```bash
git clone https://github.com/Gary1020-byte/daily-brief-bot.git
cd daily-brief-bot
python3 src/daily_brief.py --init
```

`--init` 會把 `config/config.example.toml` 複製成 `config/config.toml`。
接著編輯 `config/config.toml` —— 關鍵字與來源網址都在那裡,不用動程式碼。

## 設定

```toml
[meta]
title = "我的專業簡報"
keywords = [
  "agent", "llm", "docker", "automation",
]
require_all_keywords = false   # true = 每個關鍵字都要命中

[[sources]]
name = "來源名稱"
axis = "分類名稱"
url = "https://example.com/feed.xml"
enabled = true
```

**挑關鍵字**:10–30 個是合理範圍。太少會雜訊太多,太多會漏掉東西。

`require_all_keywords` 放在 `[meta]` 底下。設成 `true` 時,一篇文章必須命中
**全部**關鍵字才會被收錄。

## 使用

```bash
python3 src/daily_brief.py                    # 產生今日簡報
python3 src/daily_brief.py --check            # 只檢查設定檔
python3 src/daily_brief.py --dry-run          # 抓取但不更新去重狀態
python3 src/daily_brief.py --send telegram    # 推播到 Telegram
python3 src/daily_brief.py --send email       # 用 email 寄出
python3 src/daily_brief.py --limit 20         # 輸出幾條
```

## 推播設定

**Telegram**:

```toml
[telegram]
chat_id = "你的 chat id"
token_env = "TELEGRAM_BOT_TOKEN"
```

```bash
export TELEGRAM_BOT_TOKEN="xxx"
```

**Email**(需要 [himalaya](https://github.com/Impostork/himalaya)):

```toml
[email]
to = "you@example.com"
from = "you@example.com"
```

推播的內容是純文字,不是 HTML。標題會自動帶上日期,格式是 `[每日簡報] YYYY-MM-DD`。
`from` 留空時會用 `to` 的地址。

## 排程

```cron
# 每天早上 7 點(cron 用系統時區)
0 7 * * * cd /path/to/daily-brief-bot && python3 src/daily_brief.py --send telegram
```

## 常見問題

**Q: 抓不到東西?**
先用 `--check` 驗設定,再用 `--dry-run` 看錯誤訊息。失敗的來源會列在簡報底部。

**Q: 同一篇文章一直重複出現?**
網址尾端的追蹤參數(`?utm_source=` 之類)會被自動去掉。若仍然重複,
表示那些來源給的網址本來就不同。

**Q: state.json 會不會一直長大?**
不會,超過 90 天的紀錄會被清掉。

**Q: 可以加更多來源嗎?**
可以,複製一段 `[[sources]]` 就行。先測網址能不能讀:
`curl -sSL -o /dev/null -w '%{http_code}\n' '<url>'`。

**Q: 要安裝套件嗎?**
不用。這個工具只用 Python 標準庫。

## 設計說明

- **不用 `requests` / `urllib3`。** RSS 用 `urllib.request` 加上逐來源 timeout 就夠了,
  而且安裝量是零。
- **去重靠正規化網址。** 比對前先去掉 query string,所以帶追蹤參數的版本會收斂成一筆。
- **`state.json` 原子寫入**(先寫暫存檔再 rename),所以中途中斷不會留下寫壞的狀態檔。
- **範例設定只存在一份。** `config/config.example.toml` 是唯一來源,`--init` 複製它,
  程式碼裡不再內嵌第二份副本 —— 否則兩邊會各自漂移。

## License

MIT
