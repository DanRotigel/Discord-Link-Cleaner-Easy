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


URL = "https://www.instagram.com/p/DdkGhSTGjfu/?utm_source=ig_web_copy_link&stkn=NTc4MTIwNjQ2YQ=="
CLEAN_URL = "https://www.instagram.com/p/DdkGhSTGjfu/"
MESSAGE = "text text text " + URL + " text text text"


class RepostFormatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {
                "DISCORD_BOT_TOKEN": "test-placeholder", "DATA_DIR": directory,
            }), patch.object(commands.Bot, "run"), contextlib.redirect_stdout(io.StringIO()):
                cls.app = runpy.run_path(str(Path(__file__).resolve().parents[1] / "main.py"))

    def assert_repost(self, text, expected, mentions):
        async def check():
            reply = SimpleNamespace(edit=AsyncMock())
            message = SimpleNamespace(
                author=SimpleNamespace(mention="<@123456789>", display_name="Discord Display Name"),
                content=text, reply=AsyncMock(return_value=reply), delete=AsyncMock(),
            )
            handler = self.app["on_message"]
            with patch.dict(handler.__globals__, {"mention_reply_author": mentions}), \
                    patch.object(self.app["bot"], "process_commands", new_callable=AsyncMock):
                await handler(message)
            message.reply.assert_awaited_once_with(">>>")
            message.delete.assert_awaited_once()
            reply.edit.assert_awaited_once_with(content=expected)
        asyncio.run(check())

    def test_exact_input_with_author_mention(self):
        self.assert_repost(MESSAGE,
                           f'<@123456789> said "text text text {CLEAN_URL} text text text"', True)

    def test_exact_input_with_display_name(self):
        self.assert_repost(MESSAGE,
                           f'Discord Display Name said "text text text {CLEAN_URL} text text text"', False)

    def test_preserves_spacing_newlines_quotes_and_multiple_urls(self):
        text = '  before\t"quoted"\n' + URL + '   between  ' + URL + '\n after  '
        cleaned = '  before\t"quoted"\n' + CLEAN_URL + '   between  ' + CLEAN_URL + '\n after  '
        self.assert_repost(text, f'<@123456789> said "{cleaned}"', True)


if __name__ == "__main__":
    unittest.main()
