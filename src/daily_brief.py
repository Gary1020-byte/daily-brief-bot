#!/usr/bin/env python3
"""
daily-brief — RSS 智慧過濾 + 每日精簡簡報

一條指令產生你的專業資訊簡報,推送到 Email 或 Telegram。

為什麼不用 AI:這個工具的價值在「規則明確的過濾與排序」,
關鍵字比對、去重、時間窗控制都不需要推理。加入 LLM 只會增加成本
與不確定性,讓輸出每次不一致 —— 而簡報最需要的是可預測。

用法:
  python3 daily_brief.py                      # 產生今日簡報並輸出
  python3 daily_brief.py --limit 15           # 每天最多幾條
  python3 daily_brief.py --send telegram      # 推播到 Telegram
  python3 daily_brief.py --send email         # 用 email 寄出
  python3 daily_brief.py --check              # 檢查設定檔,不抓資料
  python3 daily_brief.py --init               # 產生範例設定檔
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import tomllib
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

# 以套件根目錄(上一層)為基準,這樣不管從哪裡執行都找得到 config/
PKG_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(PKG_DIR)
CONFIG = os.path.join(ROOT, "config", "config.toml")
STATE = os.path.join(ROOT, "config", "state.json")

TAIPEI = timezone(timedelta(hours=8))
UA = "Mozilla/5.0 (X11; Linux x86_64) daily-brief/1.0"

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
}


# ─────────────────────────────────────────────────────────────
# 記錄與設定
# ─────────────────────────────────────────────────────────────

def load_config():
    if not os.path.exists(CONFIG):
        die(f"找不到設定檔:{CONFIG}\n先執行:python3 {os.path.basename(__file__)} --init")
    with open(CONFIG, "rb") as f:
        return tomllib.load(f)


def load_state():
    if os.path.exists(STATE):
        with open(STATE) as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {"seen": {}, "runs": 0}
    return {"seen": {}, "runs": 0}


def save_state(st):
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)
    os.replace(tmp, STATE)


def die(msg):
    print(f"[錯誤] {msg}", file=sys.stderr)
    sys.exit(1)


# ─────────────────────────────────────────────────────────────
# 抓取 —— urllib 偶爾會卡住,所以要 retry + 明確 timeout
# ─────────────────────────────────────────────────────────────

def fetch(url, timeout=25, retries=3):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": UA,
                    "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.8",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
            last = e
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
    raise last if last else RuntimeError("unknown fetch error")


# ─────────────────────────────────────────────────────────────
# 解析 —— RSS 2.0 與 Atom 都要能處理
# ─────────────────────────────────────────────────────────────

def unescape_all(s):
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", " ", s)
    for ent, ch in (
        ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'),
        ("&#39;", "'"), ("&apos;", "'"), ("&nbsp;", " "),
        ("&amp;", "&"),
    ):
        s = s.replace(ent, ch)
    return re.sub(r"\s+", " ", s).strip()


def parse_date(s):
    if not s:
        return None
    s = s.strip()
    try:
        dt = parsedate_to_datetime(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(TAIPEI)
    except (ValueError, TypeError, IndexError):
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=TAIPEI)
        except ValueError:
            continue
    return None


def first_text(el, paths):
    for p in paths:
        found = el.find(p, NS)
        if found is not None:
            if found.text:
                return found.text.strip()
            href = found.get("href")
            if href:
                return href.strip()
    return ""


def parse_feed(raw):
    """回傳 [{title, url, summary, date}]"""
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return []

    items = []
    nodes = root.findall(".//item") or root.findall(".//atom:entry", NS)

    for it in nodes:
        title = unescape_all(first_text(it, ["title", "atom:title"]))
        url = first_text(it, ["link", "atom:link"])
        if not url:
            link = it.find("atom:link", NS)
            url = link.get("href", "") if link is not None else ""
        summary = unescape_all(
            first_text(it, ["description", "atom:summary", "content:encoded"])
        )
        raw_date = first_text(it, ["pubDate", "atom:published", "atom:updated", "dc:date"])

        if not title or not url:
            continue
        items.append({
            "title": title[:300],
            "url": url,
            "summary": summary[:600],
            "date": parse_date(raw_date),
        })
    return items


# ─────────────────────────────────────────────────────────────
# 過濾 —— 關鍵字比對是這個工具的核心價值
# ─────────────────────────────────────────────────────────────

def item_key(url):
    """去掉追蹤參數,讓同一篇文章的不同網址版本視為同一篇"""
    base = url.split("?")[0].rstrip("/")
    return hashlib.sha1(base.encode()).hexdigest()[:16]


def matches(item, keywords, require_all=False):
    if not keywords:
        return True
    haystack = (item["title"] + " " + item["summary"]).lower()
    hits = [k for k in keywords if k.lower() in haystack]
    if require_all:
        return len(hits) == len(keywords)
    return bool(hits)


def collect(cfg, state, limit_per_source=10, max_age_days=30):
    keywords = [k.lower() for k in cfg.get("meta", {}).get("keywords", [])]
    require_all = cfg.get("require_all_keywords", False)
    cutoff = datetime.now(TAIPEI) - timedelta(days=max_age_days)

    fresh, errors = [], []

    for src in cfg.get("sources", []):
        if not src.get("enabled", True):
            continue
        name = src.get("name", src.get("url", "?"))
        try:
            items = parse_feed(fetch(src["url"]))
        except Exception as e:
            errors.append((name, str(e)[:90]))
            continue

        kept = 0
        for it in items:
            if kept >= limit_per_source:
                break
            if it["date"] and it["date"] < cutoff:
                continue
            key = item_key(it["url"])
            if key in state["seen"]:
                continue
            if not matches(it, keywords, require_all):
                continue
            it["axis"] = src.get("axis", "其他")
            it["source"] = name
            it["key"] = key
            fresh.append(it)
            kept += 1

    fresh.sort(key=lambda x: x["date"] or datetime.min.replace(tzinfo=TAIPEI), reverse=True)
    return fresh, errors


# ─────────────────────────────────────────────────────────────
# 輸出 —— 純文字,適配 Email 與 Telegram
# ─────────────────────────────────────────────────────────────

def render_plain(items, errors, cfg, limit):
    now = datetime.now(TAIPEI)
    lines = []
    lines.append(f"{now:%Y-%m-%d} 每日資訊簡報")
    lines.append("=" * 30)
    lines.append("")

    if not items:
        lines.append("今天沒有符合關鍵字的新文章。")
        lines.append("(可以到 config/config.toml 調整關鍵字或增加來源)")
    else:
        by_axis = {}
        for it in items[:limit]:
            by_axis.setdefault(it["axis"], []).append(it)

        for axis in sorted(by_axis):
            lines.append(axis)
            lines.append("-" * 30)
            for it in by_axis[axis]:
                stamp = f"{it['date']:%m-%d %H:%M}" if it["date"] else "日期未知"
                lines.append(f"  {it['title']}")
                lines.append(f"  {stamp}  ·  {it['source']}")
                lines.append(f"  {it['url']}")
                lines.append("")

    if errors:
        lines.append("")
        lines.append(f"抓取失敗 {len(errors)} 個來源(不影響其他內容)")
        for name, msg in errors[:5]:
            lines.append(f"  {name}: {msg}")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# 推播
# ─────────────────────────────────────────────────────────────

def send_telegram(text, cfg):
    token = os.environ.get(cfg.get("telegram", {}).get("token_env", "TELEGRAM_BOT_TOKEN"), "")
    chat_id = cfg.get("telegram", {}).get("chat_id", "")
    if not token or not chat_id:
        die("推播 Telegram 需要設定 config.toml 的 [telegram] 區段,並提供 token 環境變數")

    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps({"chat_id": chat_id, "text": text}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=25) as r:
        if r.status == 200:
            print("已推播 Telegram", file=sys.stderr)
        else:
            die(f"Telegram 回應 {r.status}")


def send_email(text, cfg):
    """用 himalaya 寄出。需要先安裝並設定好 himalaya。"""
    ecfg = cfg.get("email", {})
    if not ecfg.get("to"):
        die("寄信需要在 config.toml 設定 [email] 的 to")

    cmd = [
        "himalaya", "template", "send",
        "-s", f"[每日簡報] {datetime.now(TAIPEI):%Y-%m-%d}",
        "-M", ecfg.get("from", ""),
        ecfg["to"],
    ]
    proc = subprocess.run(
        cmd,
        input=text.encode(),
        capture_output=True,
    )
    if proc.returncode == 0:
        print("已寄出 Email", file=sys.stderr)
    else:
        die(f"寄信失敗:{proc.stderr.decode()[:300]}")


# ─────────────────────────────────────────────────────────────
# 設定檔產生
# ─────────────────────────────────────────────────────────────

# 內附三個 2026-10-21 實測 HTTP 200 的來源,可以直接跑
EXAMPLE_CONFIG = '''# daily-brief 設定檔
# 改這個檔就能調整行為,不用動程式碼。

[meta]
title = "我的專業簡報"

# 關鍵字:標題或摘要命中就收錄。留空 = 不過濾,收全部。
# 建議 10-30 個,太少會雜訊太多,太多會漏掉。
# 下面是 AI 與自架相關的範例,請換成你自己關心的字。
keywords = [
  "agent", "llm", "mcp", "model", "ai", "docker", "automation", "self-host",
]

# true = 必須全部命中(極嚴格);false = 任一命中即可(預設)
require_all_keywords = false

# ─────────────────────────────────────────────────────
# 來源:下面三個是 2026-10-21 實測可用的,可直接跑
# ─────────────────────────────────────────────────────
[[sources]]
name = "Simon Willison"
axis = "AI 實務"
url = "https://simonwillison.net/atom/everything/"
enabled = true

[[sources]]
name = "Hacker News"
axis = "社群熱門"
url = "https://news.ycombinator.com/rss"
enabled = true

[[sources]]
name = "Google AI Blog"
axis = "AI 前沿"
url = "https://blog.google/technology/ai/rss/"
enabled = true

# ─────────────────────────────────────────────────────
# 推播設定(兩個都可以不填,只輸出到畫面)
# ─────────────────────────────────────────────────────
[telegram]
chat_id = ""
token_env = "TELEGRAM_BOT_TOKEN"

[email]
to = ""
from = ""
'''


def init():
    os.makedirs(os.path.join(ROOT, "config"), exist_ok=True)
    if os.path.exists(CONFIG):
        print(f"設定檔已存在,未覆寫:{CONFIG}")
        return
    with open(CONFIG, "w") as f:
        f.write(EXAMPLE_CONFIG)
    print(f"已建立範例設定檔:{CONFIG}")
    print("請先編輯這個檔,填入你的關鍵字與來源網址。")


# ─────────────────────────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="RSS 智慧過濾 + 每日精簡簡報")
    ap.add_argument("--limit", type=int, default=15, help="輸出幾條(預設 15)")
    ap.add_argument("--send", choices=["telegram", "email", "none"], default="none")
    ap.add_argument("--per-source", type=int, default=10, help="每個來源最多取幾條")
    ap.add_argument("--max-age", type=int, default=30, help="只看多少天內的文章")
    ap.add_argument("--check", action="store_true", help="只檢查設定檔")
    ap.add_argument("--init", action="store_true", help="產生範例設定檔")
    ap.add_argument("--dry-run", action="store_true", help="抓取但不更新狀態(測試用)")
    args = ap.parse_args()

    if args.init:
        init()
        return

    cfg = load_config()

    if args.check:
        srcs = cfg.get("sources", [])
        print(f"設定檔檢查通過")
        print(f"  關鍵字:{len(cfg.get('meta', {}).get('keywords', []))} 個")
        print(f"  來源  :{len(srcs)} 個(啟用中 {sum(1 for s in srcs if s.get('enabled', True))})")
        print(f"  嚴格比對:{cfg.get('require_all_keywords', False)}")
        return

    state = load_state()
    items, errors = collect(cfg, state, args.per_source, args.max_age)
    text = render_plain(items, errors, cfg, args.limit)

    print(text)

    if args.dry_run:
        print(f"\n[dry-run] 抓到 {len(items)} 則,未更新狀態", file=sys.stderr)
        return

    for it in items:
        state["seen"][it["key"]] = datetime.now(TAIPEI).isoformat()
    state["seen"] = {k: v for k, v in state["seen"].items()
                      if (datetime.now(TAIPEI) - datetime.fromisoformat(v)).days < 90}
    state["runs"] = state.get("runs", 0) + 1
    save_state(state)

    if args.send == "telegram":
        send_telegram(text, cfg)
    elif args.send == "email":
        send_email(text, cfg)


if __name__ == "__main__":
    main()