import asyncio
import contextlib
import io
import os
from pathlib import Path
import runpy
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from discord.ext import commands


FACEBOOK_URL = (
    "https://www.facebook.com/marketplace/item/963302936113470/"
    "?ref=browse_tab&referral_code=marketplace_top_picks&referral_story_type=top_picks"
)
CLEAN_URL = "https://www.facebook.com/marketplace/item/963302936113470/"


class FacebookURLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {
                "DISCORD_BOT_TOKEN": "test-placeholder", "DATA_DIR": directory,
            }), patch.object(commands.Bot, "run"), contextlib.redirect_stdout(io.StringIO()):
                cls.app = runpy.run_path(str(Path(__file__).resolve().parents[1] / "main.py"))

    def test_real_marketplace_url(self):
        result = self.app["clean_url"](FACEBOOK_URL)
        self.assertEqual(result["clean_url"], CLEAN_URL)
        self.assertEqual(result["removed_trackers"], {
            "Meta": ["ref", "referral_code", "referral_story_type"],
        })

    def test_facebook_domains_and_each_parameter(self):
        for host in ("facebook.com", "www.facebook.com", "m.facebook.com",
                     "web.facebook.com", "WWW.FACEBOOK.COM."):
            for key in ("ref", "referral_code", "referral_story_type"):
                with self.subTest(host=host, key=key):
                    url = f"https://{host}/marketplace/item/123/?{key}=x"
                    self.assertTrue(self.app["has_trackers"](url))
                    self.assertEqual(self.app["clean_url"](url)["clean_url"],
                                     f"https://{host}/marketplace/item/123/")

    def test_unrelated_and_lookalike_domains_keep_referral_parameters(self):
        for host in ("example.org", "facebook.com.example.org", "notfacebook.com",
                     "facebook.org", "facebook.com@evil.example"):
            with self.subTest(host=host):
                url = f"https://{host}/?referral_code=x&referral_story_type=y"
                self.assertFalse(self.app["has_trackers"](url))
                self.assertEqual(self.app["clean_url"](url)["clean_url"], url)

    def test_existing_meta_trackers_remain_global(self):
        for parameter in self.app["default_trackers"]["Meta"]:
            with self.subTest(parameter=parameter):
                url = f"https://example.org/?{parameter}=x&referral_code=keep"
                self.assertTrue(self.app["has_trackers"](url))
                result = self.app["clean_url"](url)
                self.assertEqual(result["clean_url"], "https://example.org/?referral_code=keep")
                self.assertEqual(result["removed_trackers"], {"Meta": [parameter]})

    def test_existing_global_ref_rule_is_unchanged(self):
        result = self.app["clean_url"]("https://example.org/?ref=x&referral_code=keep")
        self.assertEqual(result["clean_url"], "https://example.org/?referral_code=keep")
        self.assertEqual(result["removed_trackers"], {"Affiliate": ["ref"]})

    def test_case_duplicates_and_preserved_values(self):
        url = "https://m.facebook.com/item/?REFERRAL_CODE=x&referral_code=y&REFERRAL_STORY_TYPE=z&keep=&keep=yes#details"
        self.assertEqual(self.app["clean_url"](url)["clean_url"],
                         "https://m.facebook.com/item/?keep=&keep=yes#details")

    def test_schemeless_and_protocol_relative_urls(self):
        for prefix in ("m.facebook.com", "//m.facebook.com"):
            with self.subTest(prefix=prefix):
                url = f"{prefix}/item/?referral_code=x"
                self.assertTrue(self.app["has_trackers"](url))
                self.assertEqual(self.app["clean_url"](url)["clean_url"], f"{prefix}/item/")

    def test_message_handler_reposts_marketplace_url(self):
        async def check():
            reply = SimpleNamespace(edit=AsyncMock())
            message = SimpleNamespace(
                author=SimpleNamespace(mention="@tester"), content=FACEBOOK_URL,
                reply=AsyncMock(return_value=reply), delete=AsyncMock(),
            )
            with patch.object(self.app["bot"], "process_commands", new_callable=AsyncMock):
                await self.app["on_message"](message)
            message.delete.assert_awaited_once()
            reply.edit.assert_awaited_once_with(content=(
                "@tester Your message has been reposted without trackers from Meta:\n" + CLEAN_URL
            ))
        asyncio.run(check())


if __name__ == "__main__":
    unittest.main()
