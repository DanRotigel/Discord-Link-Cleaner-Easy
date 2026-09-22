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


class RequireLinksTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {
                "DISCORD_BOT_TOKEN": "test-placeholder", "DATA_DIR": directory,
            }), patch.object(commands.Bot, "run"), contextlib.redirect_stdout(io.StringIO()):
                cls.app = runpy.run_path(str(Path(__file__).resolve().parents[1] / "main.py"))

    def check_message(self, require_links, content, expected=None):
        async def check():
            reply = SimpleNamespace(edit=AsyncMock())
            message = SimpleNamespace(
                author=SimpleNamespace(mention="<@123456789>", display_name="Tester"),
                content=content, reply=AsyncMock(return_value=reply), delete=AsyncMock(),
            )
            handler = self.app["on_message"]
            with patch.dict(handler.__globals__, {"require_links": require_links}), \
                    patch.object(self.app["bot"], "process_commands", new_callable=AsyncMock) as process:
                await handler(message)
            process.assert_awaited_once_with(message)
            if expected is None:
                message.reply.assert_not_awaited()
                message.delete.assert_not_awaited()
                reply.edit.assert_not_awaited()
            else:
                message.reply.assert_awaited_once_with(">>>")
                message.delete.assert_awaited_once()
                reply.edit.assert_awaited_once_with(content=expected)
        asyncio.run(check())

    def test_tracked_urls_are_cleaned_with_both_settings(self):
        for enabled in (True, False):
            with self.subTest(require_links=enabled):
                self.check_message(enabled, "Look https://example.com/page?utm_source=test&keep=yes",
                                   '<@123456789> said "Look https://example.com/page?keep=yes"')

    def test_no_url_messages_are_ignored_with_both_settings(self):
        for enabled in (True, False):
            for content in ("Hello world", "", "   \n\t"):
                with self.subTest(require_links=enabled, content=content):
                    self.check_message(enabled, content)

    def test_clean_urls_are_not_reposted_with_both_settings(self):
        for enabled in (True, False):
            with self.subTest(require_links=enabled):
                self.check_message(enabled, "Look https://example.com/page?keep=yes")


if __name__ == "__main__":
    unittest.main()
