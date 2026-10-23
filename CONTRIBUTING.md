# Contributing to daily-brief

Thanks for considering a contribution. This is a small, dependency-free tool —
the design constraint is deliberate, and contributions that break it will not
be merged.

## The constraint: standard library only

The tool ships with **zero third-party dependencies**. That is the reason it
can be installed with `git clone` and no `pip install`, and it is the reason
running it costs nothing. Please don't add a dependency.

If you think you need one, open an issue first and explain what the standard
library can't do.

## Getting set up

```bash
git clone https://github.com/Gary1020-byte/daily-brief-bot.git
cd daily-brief-bot
python3 src/daily_brief.py --init
```

Requires Python 3.11+ (the tool uses `tomllib`, which is stdlib from 3.11).

## Running the tests

```bash
python3 -m unittest discover -s tests -v
```

Every test must pass on Python 3.11, 3.12, and 3.13 — that's what CI checks.

## What a good contribution looks like

**A bug fix should come with a test.** The tests in `tests/test_daily_brief.py`
each correspond to a bug that was actually shipped. The ones that mattered most
were the silent ones: a config key read from the wrong section, an example
config that had drifted from the code's embedded copy, a push command with flags
the target CLI doesn't accept. All three produced output that looked fine.

If you fix a bug, write the test that fails before the fix and passes after.

**Don't add features that need a network call in the test suite.** CI runs
offline-ish and the feed URLs change. Tests should use inline XML fixtures —
see `TestFeedParsing` for the pattern.

**Keep the output plain text.** The digest goes into Email and Telegram, which
don't render Markdown. If you touch `render_plain`, the
`test_plain_text_has_no_markdown_or_html` test guards the format.

## Commit messages

```
<type>: <short description>
```

Types used here: `fix`, `feat`, `docs`, `test`, `ci`, `chore`, `refactor`.

## Reporting bugs

Open an issue with:

- What you ran (the exact command)
- What you expected
- What happened instead
- The output of `python3 src/daily_brief.py --check`

Please **don't paste a signed Cool URL, a token, or your `config/config.toml`**
into an issue. If a source URL needs auth, describe the shape of the URL
without the credential part.

## Pull requests

- Branch from `main`, one topic per PR.
- Make sure `python3 -m unittest discover -s tests -v` passes locally.
- Describe what changed and why. If it fixes a bug, say what the bug was.

## License

By contributing, you agree that your contributions are licensed under the MIT
License.
