# Daily Brief — RSS keyword-filtered daily digest

One command turns the feeds you care about into a filtered digest, pushed to Email or Telegram.

[繁體中文版](README.zh-TW.md)

## Why there's no AI in the pipeline

The value here is **deterministic filtering and ordering**: keyword matching, URL
deduplication, and a time window. None of that needs inference. Adding an LLM
would raise the cost and make the wording differ every run — and a digest's
whole job is to be **predictable**.

Trading "deterministic rules, zero API cost" for uncertainty is a deliberate
choice, not a limitation.

## Features

- **Keyword filtering** — only the topics you actually care about
- **Cross-source deduplication** — the same article reposted under different URLs appears once
- **Category axes** — group feeds into your own lanes (e.g. "AI practice", "Community")
- **Plain-text output** — safe for Email and Telegram, no formatting artefacts
- **Standard library only** — no `pip install`, no dependency drift
- **Doesn't die on one bad feed** — per-source retry and fault isolation

## Requirements

- Python 3.11 or newer (needs `tomllib`, which is built into 3.11+)
- No third-party packages

## Install

```bash
git clone https://github.com/Gary1020-byte/daily-brief-bot.git
cd daily-brief-bot
python3 src/daily_brief.py --init
```

`--init` copies `config/config.example.toml` to `config/config.toml`.
Edit `config/config.toml` — keywords and feed URLs live there, no code changes
needed.

## Configure

Edit `config/config.toml`:

```toml
[meta]
title = "My digest"
keywords = [
  "agent", "llm", "docker", "automation",
]
require_all_keywords = false   # true = every keyword must match

[[sources]]
name = "Source name"
axis = "Category name"
url = "https://example.com/feed.xml"
enabled = true
```

**Picking keywords**: 10–30 is a good range. Fewer and you get noise; more and
you start missing things.

`require_all_keywords` belongs under `[meta]`. When `true`, an article is kept
only if it matches **every** keyword.

## Use

```bash
python3 src/daily_brief.py                    # build today's digest
python3 src/daily_brief.py --check            # validate the config only
python3 src/daily_brief.py --dry-run          # fetch, but don't update dedup state
python3 src/daily_brief.py --send telegram    # push to Telegram
python3 src/daily_brief.py --send email       # send by email
python3 src/daily_brief.py --limit 20         # how many items to output
```

## Push configuration

**Telegram**:

```toml
[telegram]
chat_id = "your chat id"
token_env = "TELEGRAM_BOT_TOKEN"
```

```bash
export TELEGRAM_BOT_TOKEN="xxx"
```

**Email** (requires [himalaya](https://github.com/Impostork/himalaya)):

```toml
[email]
to = "you@example.com"
from = "you@example.com"
```

The pushed body is plain text, not HTML. The subject is generated as
`[每日簡報] YYYY-MM-DD`. If `from` is empty, `to` is used.

## Schedule

```cron
# 7am daily (cron uses the system timezone)
0 7 * * * cd /path/to/daily-brief-bot && python3 src/daily_brief.py --send telegram
```

## FAQ

**Q: Nothing is being fetched?**
Run `--check` to validate the config, then `--dry-run` to see the error
messages. A failing source is listed at the bottom of the digest.

**Q: The same article keeps appearing?**
Tracking parameters at the end of the URL (`?utm_source=` and friends) are
stripped automatically. If it still repeats, the source URLs genuinely differ.

**Q: Does state.json grow forever?**
No. Records older than 90 days are pruned.

**Q: Can I add more sources?**
Yes — copy a `[[sources]]` block. Test the URL first with
`curl -sSL -o /dev/null -w '%{http_code}\n' '<url>'`.

## Design notes

- **No `requests` / `urllib3`.** `urllib.request` with a per-source timeout is
  enough for RSS, and it keeps the install to zero.
- **Dedup is by normalised URL.** Query parameters are stripped before
  comparison, so tracking variants collapse into one entry.
- **`state.json` is written atomically** (temp file + rename), so an
  interrupted run can't leave a half-written state file behind.
- **The example config lives in exactly one place.**
  `config/config.example.toml` is the single source; `--init` copies it, and
  the code no longer embeds a second copy — otherwise the two drift apart.

## License

MIT
