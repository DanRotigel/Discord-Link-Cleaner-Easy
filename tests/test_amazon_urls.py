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


AMAZON_URL = (
    "https://www.amazon.com/dp/B0HJBCX8VS/?_encoding=UTF8&th=1"
    "&ref_=pd_hp_d_r_atf_unk&pd_rd_w=pAcuf"
    "&content-id=amzn1.sym.20569031-4b89-41e8-aa05-ba558249c33c"
    "&pf_rd_p=20569031-4b89-41e8-aa05-ba558249c33c"
    "&pf_rd_r=R7E7T5PYFS0R155WHG3B&pd_rd_wg=Vk7fS"
    "&pd_rd_r=b664dfaf-7f08-4945-8d88-2e5cf9bf4eba"
)


class AmazonURLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Load the actual app with temporary configuration and no Discord login.
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {
                "DISCORD_BOT_TOKEN": "test-placeholder", "DATA_DIR": directory,
            }), patch.object(commands.Bot, "run"), contextlib.redirect_stdout(io.StringIO()):
                cls.app = runpy.run_path(str(Path(__file__).resolve().parents[1] / "main.py"))

    def test_real_amazon_url(self):
        result = self.app["clean_url"](AMAZON_URL)
        self.assertEqual(result["clean_url"], "https://www.amazon.com/dp/B0HJBCX8VS/")
        self.assertEqual(set(result["removed_trackers"]), {"Amazon"})

    def test_amazon_domains_and_subdomains(self):
        for host in ("amazon.com", "www.amazon.co.uk", "smile.amazon.de",
                     "amazon.co.jp", "amazon.com.au", "amazon.com.be",
                     "amazon.ie", "amazon.co.za", "WWW.AMAZON.COM."):
            with self.subTest(host=host):
                url = f"https://{host}/dp/item?pd_rd_new=x&pf_rd_new=y&ref_=z"
                self.assertTrue(self.app["has_trackers"](url))
                self.assertEqual(self.app["clean_url"](url)["clean_url"], f"https://{host}/dp/item")

    def test_amazon_rules_do_not_apply_to_other_hosts(self):
        query = "pd_rd_w=x&pf_rd_p=y&ref_=z&content-id=a&_encoding=UTF8&tag=t&th=1"
        for host in ("example.com", "notamazon.com", "amazon.com.example.org",
                     "amazon.invalid", "amazon.com@evil.example"):
            with self.subTest(host=host):
                url = f"https://{host}/dp/item?{query}"
                self.assertFalse(self.app["has_trackers"](url))
                self.assertEqual(self.app["clean_url"](url)["clean_url"], url)

    def test_existing_amazon_parameters_are_scoped(self):
        for parameter in self.app["default_trackers"]["Amazon"]:
            with self.subTest(parameter=parameter):
                amazon = f"https://amazon.com/?{parameter}=x"
                other = f"https://example.com/?{parameter}=x"
                self.assertEqual(self.app["clean_url"](amazon)["clean_url"], "https://amazon.com/")
                self.assertEqual(self.app["clean_url"](other)["clean_url"], other)

    def test_retains_product_parameters_duplicates_blanks_and_fragment(self):
        url = "https://amazon.com/dp/item?pd_rd_w=x&quantity=2&keep=&keep=yes#details"
        self.assertEqual(self.app["clean_url"](url)["clean_url"],
                         "https://amazon.com/dp/item?quantity=2&keep=&keep=yes#details")

    def test_case_insensitive_and_repeated_amazon_parameters(self):
        url = "https://amazon.com/?PD_RD_W=x&pf_rd_p=y&REF_=z&CONTENT-ID=a&_ENCODING=b&TH=1&TH=2"
        self.assertEqual(self.app["clean_url"](url)["clean_url"], "https://amazon.com/")

    def test_global_tracking_rules_are_unchanged(self):
        for host in ("example.com", "amazon.com"):
            with self.subTest(host=host):
                url = f"https://{host}/?utm_source=x&fbclid=y&ref=z&keep=yes"
                self.assertTrue(self.app["has_trackers"](url))
                result = self.app["clean_url"](url)
                self.assertEqual(result["clean_url"], f"https://{host}/?keep=yes")
                self.assertEqual(set(result["removed_trackers"]), {"Google", "Meta", "Affiliate"})

    def test_schemeless_and_protocol_relative_amazon_urls(self):
        for prefix in ("www.amazon.com", "//www.amazon.com"):
            with self.subTest(prefix=prefix):
                url = f"{prefix}/dp/item?pd_rd_w=x"
                self.assertTrue(self.app["has_trackers"](url))
                self.assertEqual(self.app["clean_url"](url)["clean_url"], f"{prefix}/dp/item")

    def test_message_handler_reposts_real_amazon_url(self):
        async def check():
            reply = SimpleNamespace(edit=AsyncMock())
            message = SimpleNamespace(
                author=SimpleNamespace(mention="@tester"), content=AMAZON_URL,
                reply=AsyncMock(return_value=reply), delete=AsyncMock(),
            )
            with patch.object(self.app["bot"], "process_commands", new_callable=AsyncMock):
                await self.app["on_message"](message)
            message.delete.assert_awaited_once()
            reply.edit.assert_awaited_once_with(content=(
                '@tester said "https://www.amazon.com/dp/B0HJBCX8VS/"'
            ))
        asyncio.run(check())


if __name__ == "__main__":
    unittest.main()
