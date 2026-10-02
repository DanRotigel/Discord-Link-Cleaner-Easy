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


class ReplyFormatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {
                "DISCORD_BOT_TOKEN": "test-placeholder", "DATA_DIR": directory,
            }), patch.object(commands.Bot, "run"), contextlib.redirect_stdout(io.StringIO()):
                cls.app = runpy.run_path(str(Path(__file__).resolve().parents[1] / "main.py"))
        cls.bot_user = SimpleNamespace(id=987654321)
        cls.app["bot"]._connection.user = cls.bot_user

    def assert_reply(self, text, expected, mentions):
        async def check():
            reply = SimpleNamespace(edit=AsyncMock())
            message = SimpleNamespace(
                author=SimpleNamespace(mention="<@123456789>", display_name="Discord Display Name"),
                content=text, mentions=[self.bot_user], reference=None,
                reply=AsyncMock(return_value=reply), delete=AsyncMock(), edit=AsyncMock(),
            )
            handler = self.app["on_message"]
            with patch.dict(handler.__globals__, {"mention_reply_author": mentions}), \
                    patch.object(self.app["bot"], "process_commands", new_callable=AsyncMock):
                await handler(message)
            message.reply.assert_awaited_once_with(
                expected, allowed_mentions=unittest.mock.ANY, mention_author=False,
            )
            message.delete.assert_not_awaited()
            message.edit.assert_not_awaited()
            reply.edit.assert_not_awaited()
        asyncio.run(check())

    def test_exact_input_with_author_mention(self):
        self.assert_reply(MESSAGE,
                           f"Here's your link!\n{CLEAN_URL}", True)

    def test_exact_input_with_display_name(self):
        self.assert_reply(MESSAGE,
                           f"Here's your link!\n{CLEAN_URL}", False)

    def test_returns_only_cleaned_links_from_surrounding_text(self):
        text = '  before\t"quoted"\n' + URL + '   between  ' + URL + '\n after  '
        self.assert_reply(text, f"Here are your links!\n{CLEAN_URL}\n{CLEAN_URL}", True)


if __name__ == "__main__":
    unittest.main()
