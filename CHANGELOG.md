# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-10-23

First release. A keyword-filtered RSS digest that runs on the standard library
alone and pushes plain text to Email or Telegram.

### Added

- `daily_brief.py` — one script, zero third-party dependencies.
- `--init` — creates `config/config.toml` from the shipped example.
- `--check` — validates the config without fetching.
- `--dry-run` — fetch without updating the dedup state.
- `--send telegram` / `--send email` — plain-text push.
- Keyword filtering, cross-source URL dedup, custom category axes, per-source
  retry and fault isolation, a 30-day freshness window, 90-day state pruning.
- 26 unit tests.
- CI on Python 3.11, 3.12, 3.13.
- `CONTRIBUTING.md` and issue templates.
- `README.md` (English) and `README.zh-TW.md` (Traditional Chinese).

### Fixed

Four bugs that shipped in the first public build. All four produced output that
*looked* correct while doing the wrong thing.

- `require_all_keywords` was read from the top level of the config, but the
  docs put it under `[meta]`. A config asking for strict matching silently ran
  in loose mode — the tool looked healthy and collected exactly the articles
  the user had filtered out.
- `--send email` called `himalaya template send -s ... -M ...`. himalaya
  v1.2.0 accepts only `-a/-c/-o`, so the command died with
  `unexpected argument '-s' found` before reaching the network.
- `README.zh-TW.md` was byte-identical to `README.md` — an English file with a
  Chinese filename.
- The author's own `config/config.toml` was committed.

### Changed

- `--init` now copies `config/config.example.toml` instead of writing a second
  copy embedded in the source. The two had already drifted; the example file is
  now the single source of truth.
- The personal `config/config.toml` is untracked and gitignored.

[Unreleased]: https://github.com/Gary1020-byte/daily-brief-bot/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/Gary1020-byte/daily-brief-bot/releases/tag/v1.0.0
