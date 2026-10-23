#!/usr/bin/env python3
"""Tests for daily-brief.

Run:  python3 -m unittest discover -s tests -v

Every test here corresponds to a bug that was actually shipped and fixed, or
to a behaviour the README promises. The point of this file is that the
"strict mode does nothing" bug — which produced well-formed output and
silently collected everything — can never come back unnoticed.
"""
import importlib.util
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "daily_brief", os.path.join(ROOT, "src", "daily_brief.py")
)
db = importlib.util.module_from_spec(spec)
spec.loader.exec_module(db)


def item(title, summary="", url="https://example.com/a", date=None):
    return {"title": title, "summary": summary, "url": url, "date": date}


class TestKeywordMatching(unittest.TestCase):
    def test_any_keyword_matches_by_default(self):
        it = item("Agent news")
        self.assertTrue(db.matches(it, ["agent", "llm"], require_all=False))

    def test_strict_mode_requires_every_keyword(self):
        it = item("Agent news")
        self.assertFalse(db.matches(it, ["agent", "llm"], require_all=True))

    def test_strict_mode_passes_when_all_match(self):
        it = item("Agent and LLM news")
        self.assertTrue(db.matches(it, ["agent", "llm"], require_all=True))

    def test_empty_keyword_list_matches_everything(self):
        self.assertTrue(db.matches(item("anything"), []))

    def test_matching_is_case_insensitive(self):
        self.assertTrue(db.matches(item("AGENT"), ["agent"]))


class TestRequireAllConfigKey(unittest.TestCase):
    """`require_all_keywords` is documented under [meta].

    Regression test: the code read it from the top level, so a config that
    asked for strict mode silently behaved like loose mode. The tool looked
    healthy and collected articles the user had filtered out.
    """

    def test_read_from_meta_section(self):
        cfg = {
            "meta": {"keywords": ["ai", "llm"], "require_all_keywords": True},
            "sources": [],
        }
        self.assertTrue(db._require_all(cfg))

    def test_meta_wins_over_top_level(self):
        cfg = {
            "meta": {"keywords": ["ai"], "require_all_keywords": True},
            "require_all_keywords": False,
        }
        self.assertTrue(db._require_all(cfg))

    def test_top_level_still_accepted_for_backward_compat(self):
        cfg = {"meta": {"keywords": ["ai"]}, "require_all_keywords": True}
        self.assertTrue(db._require_all(cfg))

    def test_defaults_to_loose(self):
        cfg = {"meta": {"keywords": ["ai"]}}
        self.assertFalse(db._require_all(cfg))


class TestDedup(unittest.TestCase):
    def test_tracking_params_are_stripped(self):
        a = db.item_key("https://example.com/post?utm_source=rss")
        b = db.item_key("https://example.com/post")
        self.assertEqual(a, b)

    def test_trailing_slash_is_stripped(self):
        a = db.item_key("https://example.com/post/")
        b = db.item_key("https://example.com/post")
        self.assertEqual(a, b)

    def test_different_paths_are_different_items(self):
        a = db.item_key("https://example.com/a")
        b = db.item_key("https://example.com/b")
        self.assertNotEqual(a, b)


class TestFeedParsing(unittest.TestCase):
    def test_rss_item(self):
        raw = b"""<?xml version="1.0"?>
        <rss version="2.0"><channel>
          <item>
            <title>Hello &amp; World</title>
            <link>https://example.com/1</link>
            <description>&lt;p&gt;Body&lt;/p&gt;</description>
            <pubDate>Mon, 20 Oct 2025 10:00:00 +0000</pubDate>
          </item>
        </channel></rss>"""
        items = db.parse_feed(raw)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Hello & World")
        self.assertEqual(items[0]["url"], "https://example.com/1")
        self.assertNotIn("<p>", items[0]["summary"])
        self.assertIsNotNone(items[0]["date"])

    def test_atom_entry(self):
        raw = b"""<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <title>Atom Title</title>
            <link href="https://example.com/atom"/>
            <summary>Some summary</summary>
            <published>2025-10-20T10:00:00Z</published>
          </entry>
        </feed>"""
        items = db.parse_feed(raw)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Atom Title")
        self.assertEqual(items[0]["url"], "https://example.com/atom")

    def test_malformed_xml_returns_empty_not_raises(self):
        self.assertEqual(db.parse_feed(b"not xml at all <<<"), [])

    def test_item_without_link_is_skipped(self):
        raw = b"""<rss version="2.0"><channel>
          <item><title>No link</title></item>
        </channel></rss>"""
        self.assertEqual(db.parse_feed(raw), [])


class TestConfigLoading(unittest.TestCase):
    def test_example_config_is_valid_toml(self):
        import tomllib
        path = os.path.join(ROOT, "config", "config.example.toml")
        with open(path, "rb") as f:
            cfg = tomllib.load(f)
        self.assertIn("meta", cfg)
        self.assertIn("keywords", cfg["meta"])
        self.assertIn("require_all_keywords", cfg["meta"])
        self.assertGreaterEqual(len(cfg["sources"]), 3)

    def test_example_config_sources_have_required_fields(self):
        import tomllib
        path = os.path.join(ROOT, "config", "config.example.toml")
        with open(path, "rb") as f:
            cfg = tomllib.load(f)
        for src in cfg["sources"]:
            for field in ("name", "axis", "url"):
                self.assertIn(field, src, f"source missing {field}")
            self.assertTrue(src["url"].startswith("http"))

    def test_init_creates_config_from_example(self):
        import tempfile, shutil
        with tempfile.TemporaryDirectory() as tmp:
            saved_root, saved_cfg = db.ROOT, db.CONFIG
            saved_ex, saved_state = db.EXAMPLE_CONFIG_PATH, db.STATE
            try:
                os.makedirs(os.path.join(tmp, "config"))
                shutil.copy(
                    os.path.join(ROOT, "config", "config.example.toml"),
                    os.path.join(tmp, "config", "config.example.toml"),
                )
                db.ROOT = tmp
                db.CONFIG = os.path.join(tmp, "config", "config.toml")
                db.EXAMPLE_CONFIG_PATH = os.path.join(
                    tmp, "config", "config.example.toml"
                )
                db.STATE = os.path.join(tmp, "config", "state.json")
                db.init()
                self.assertTrue(os.path.exists(db.CONFIG))
                # and it must not overwrite an existing file
                with open(db.CONFIG, "w") as f:
                    f.write("SENTINEL")
                db.init()
                with open(db.CONFIG) as f:
                    self.assertEqual(f.read(), "SENTINEL")
            finally:
                db.ROOT, db.CONFIG = saved_root, saved_cfg
                db.EXAMPLE_CONFIG_PATH, db.STATE = saved_ex, saved_state


class TestEmailPath(unittest.TestCase):
    """The `--send email` path used `himalaya template send -s ... -M ...`.

    himalaya v1.2.0 has no -s/-M flags, so the command died with
    "unexpected argument '-s' found" before ever reaching the network.
    """

    def test_builds_valid_mime_message(self):
        msg = db.build_email_message(
            "2026-10-23",
            to_addr="a@example.com",
            from_addr="b@example.com",
            body="Hello",
        )
        self.assertIn("From: b@example.com", msg)
        self.assertIn("To: a@example.com", msg)
        self.assertIn("Subject: [每日簡報] 2026-10-23", msg)
        self.assertIn("Content-Type: text/plain; charset=UTF-8", msg)
        self.assertIn("Hello", msg)
        # headers, one blank line, then the body
        head, _, body = msg.partition("\n\n")
        self.assertIn("Subject:", head)
        self.assertEqual(body.strip(), "Hello")

    def test_from_falls_back_to_to(self):
        msg = db.build_email_message(
            "2026-10-23", to_addr="a@example.com", from_addr="", body="x"
        )
        self.assertIn("From: a@example.com", msg)

    def test_command_has_no_unsupported_flags(self):
        cmd = db.himalaya_send_command(account=None)
        self.assertEqual(cmd, ["himalaya", "template", "send"])
        for bad in ("-s", "-M", "-t"):
            self.assertNotIn(bad, cmd)

    def test_account_flag_is_subcommand_level(self):
        cmd = db.himalaya_send_command(account="gmail")
        self.assertEqual(cmd, ["himalaya", "template", "send", "-a", "gmail"])
        self.assertNotIn("-a", cmd[:3])


class TestRender(unittest.TestCase):
    def test_plain_text_has_no_markdown_or_html(self):
        items = [
            {"title": "T1", "url": "https://e.com/1", "summary": "",
             "date": db.datetime.now(db.TAIPEI), "axis": "A", "source": "S",
             "key": "k1"},
        ]
        text = db.render_plain(items, [], {}, 10)
        for marker in ("**", "##", "```", "<b>", "<sub>", "- ["):
            self.assertNotIn(marker, text, f"plain text leaked {marker!r}")

    def test_empty_digest_says_so(self):
        text = db.render_plain([], [], {}, 10)
        self.assertIn("沒有符合關鍵字", text)

    def test_errors_are_reported_but_not_fatal(self):
        text = db.render_plain([], [("Bad Feed", "timeout")], {}, 10)
        self.assertIn("抓取失敗", text)
        self.assertIn("Bad Feed", text)


if __name__ == "__main__":
    unittest.main()
