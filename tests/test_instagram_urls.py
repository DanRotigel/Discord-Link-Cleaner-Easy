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


INSTAGRAM_URL = (
    "https://www.instagram.com/p/DdjsB7vC-gS/"
    "?utm_source=ig_web_copy_link&stkn=NTc4MTIwNjQ2YQ=="
)
INSTAGRAM_PARAMS = ("stkn", "igsh", "igshid", "igsi", "ig_rid")


class InstagramURLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {
                "DISCORD_BOT_TOKEN": "test-placeholder", "DATA_DIR": directory,
            }), patch.object(commands.Bot, "run"), contextlib.redirect_stdout(io.StringIO()):
                cls.app = runpy.run_path(str(Path(__file__).resolve().parents[1] / "main.py"))

    def test_real_instagram_url(self):
        result = self.app["clean_url"](INSTAGRAM_URL)
        self.assertEqual(result["clean_url"], "https://www.instagram.com/p/DdjsB7vC-gS/")
        self.assertEqual(result["removed_trackers"], {"Google": ["utm_source"], "Meta": ["stkn"]})

    def test_message_handler_reposts_exact_instagram_url(self):
        self.assertEqual(self.app["extract_urls"](INSTAGRAM_URL), [INSTAGRAM_URL])
        async def check():
            reply = SimpleNamespace(edit=AsyncMock())
            message = SimpleNamespace(
                author=SimpleNamespace(mention="@tester"), content=INSTAGRAM_URL,
                reply=AsyncMock(return_value=reply), delete=AsyncMock(),
            )
            with patch.object(self.app["bot"], "process_commands", new_callable=AsyncMock):
                await self.app["on_message"](message)
            message.delete.assert_awaited_once()
            content = reply.edit.call_args.kwargs["content"]
            self.assertEqual(content.split("\n", 1)[1], "https://www.instagram.com/p/DdjsB7vC-gS/")
        asyncio.run(check())

    def test_padded_url_extraction_preserves_surrounding_punctuation(self):
        for suffix in (".", ",", ")", ">", "\nnext", " next"):
            with self.subTest(suffix=suffix):
                self.assertEqual(self.app["extract_urls"]("Look: " + INSTAGRAM_URL + suffix),
                                 [INSTAGRAM_URL])

    def test_padding_and_legitimate_query_values_in_reposts(self):
        async def check():
            for padding in ("=", "==", "%3D%3D"):
                with self.subTest(padding=padding):
                    url = "https://www.instagram.com/p/item/?stkn=abc" + padding
                    reply = SimpleNamespace(edit=AsyncMock())
                    message = SimpleNamespace(
                        author=SimpleNamespace(mention="@tester"),
                        content="Look: (" + url + ").",
                        reply=AsyncMock(return_value=reply), delete=AsyncMock(),
                    )
                    with patch.object(self.app["bot"], "process_commands", new_callable=AsyncMock):
                        await self.app["on_message"](message)
                    reply.edit.assert_awaited_once()
                    self.assertEqual(reply.edit.call_args.kwargs["content"].split("\n", 1)[1],
                                     "Look: (https://www.instagram.com/p/item/).")
        asyncio.run(check())
        url = "https://www.instagram.com/p/item/?stkn=x&keep=abc=="
        self.assertEqual(self.app["extract_urls"](url), [url])
        self.assertEqual(self.app["clean_url"](url)["clean_url"],
                         "https://www.instagram.com/p/item/?keep=abc%3D%3D")

    def test_extraction_does_not_extend_paths_or_fragments(self):
        for url in ("https://example.org/path==", "https://example.org/?keep=x#fragment=="):
            with self.subTest(url=url):
                self.assertEqual(self.app["extract_urls"](url), [url[:-2]])

    def test_domains_and_each_parameter(self):
        for host in ("instagram.com", "www.instagram.com", "m.instagram.com", "WWW.INSTAGRAM.COM."):
            for key in INSTAGRAM_PARAMS:
                with self.subTest(host=host, key=key):
                    url = f"https://{host}/p/item/?{key}=x"
                    self.assertTrue(self.app["has_trackers"](url))
                    self.assertEqual(self.app["clean_url"](url)["clean_url"], f"https://{host}/p/item/")

    def test_unrelated_and_lookalike_hosts_preserve_each_parameter(self):
        for host in ("example.org", "instagram.com.example.org", "notinstagram.com",
                     "instagram.org", "instagram.com@evil.example", "facebook.com"):
            for key in INSTAGRAM_PARAMS:
                with self.subTest(host=host, key=key):
                    url = f"https://{host}/?{key}=x"
                    self.assertFalse(self.app["has_trackers"](url))
                    self.assertEqual(self.app["clean_url"](url)["clean_url"], url)

    def test_utm_cleaning_remains_global(self):
        for host in ("instagram.com", "example.org"):
            with self.subTest(host=host):
                url = f"https://{host}/?utm_source=x&utm_medium=y&img_index=2"
                self.assertEqual(self.app["clean_url"](url)["clean_url"], f"https://{host}/?img_index=2")

    def test_unrelated_domains_keep_instagram_parameters_alongside_global_trackers(self):
        url = "https://example.org/?utm_source=x&fbclid=y&igsh=keep&stkn=keep"
        self.assertEqual(self.app["clean_url"](url)["clean_url"],
                         "https://example.org/?igsh=keep&stkn=keep")

    def test_legitimate_parameters_and_fragment_are_preserved(self):
        url = "https://instagram.com/p/item/?stkn=x&img_index=2&hl=en&keep=&keep=yes#details"
        self.assertEqual(self.app["clean_url"](url)["clean_url"],
                         "https://instagram.com/p/item/?img_index=2&hl=en&keep=&keep=yes#details")
        clean = "https://instagram.com/p/item/?img_index=2&hl=en"
        self.assertFalse(self.app["has_trackers"](clean))
        self.assertEqual(self.app["clean_url"](clean)["clean_url"], clean)

    def test_case_duplicates_and_encoded_values(self):
        url = "https://instagram.com/?STKN=a%3D%3D&stkn=b==&IGSH=c&IGSHID=d&IGSI=e&IG_RID=f"
        self.assertEqual(self.app["clean_url"](url)["clean_url"], "https://instagram.com/")

    def test_schemeless_and_protocol_relative_urls(self):
        for prefix in ("www.instagram.com", "//www.instagram.com"):
            with self.subTest(prefix=prefix):
                url = f"{prefix}/p/item/?stkn=x"
                self.assertTrue(self.app["has_trackers"](url))
                self.assertEqual(self.app["clean_url"](url)["clean_url"], f"{prefix}/p/item/")


if __name__ == "__main__":
    unittest.main()
