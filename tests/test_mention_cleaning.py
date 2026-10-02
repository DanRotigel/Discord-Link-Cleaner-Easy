import contextlib
import io
import os
from pathlib import Path
import runpy
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import discord
from discord.ext import commands


TRACKED = "https://example.com/article?utm_source=test&keep=yes"
CLEAN = "https://example.com/article?keep=yes"
OTHER_TRACKED = "https://example.org/story?fbclid=test"
OTHER_CLEAN = "https://example.org/story"


class MentionCleaningTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {
                "DISCORD_BOT_TOKEN": "test-placeholder", "DATA_DIR": directory,
            }), patch.object(commands.Bot, "run"), contextlib.redirect_stdout(io.StringIO()):
                cls.app = runpy.run_path(str(Path(__file__).resolve().parents[1] / "main.py"))
        cls.bot_user = SimpleNamespace(id=987654321)
        cls.app["bot"]._connection.user = cls.bot_user

    def message(self, content, mentioned=True, reference=None):
        return SimpleNamespace(
            author=SimpleNamespace(id=123), content=content,
            mentions=[self.bot_user] if mentioned else [], reference=reference,
            channel=SimpleNamespace(id=42, fetch_message=AsyncMock()),
            reply=AsyncMock(), delete=AsyncMock(), edit=AsyncMock(),
        )

    def reference(self, original=None, cached=False):
        reference = discord.MessageReference(message_id=123, channel_id=42)
        if cached:
            reference._state = SimpleNamespace(_get_message=Mock(return_value=original))
        else:
            reference.resolved = original
        return reference

    async def check(self, invocation, expected=None, original=None):
        invocation_content = invocation.content
        original_content = original.content if original else None
        with patch.object(self.app["bot"], "process_commands", new_callable=AsyncMock) as process:
            await self.app["on_message"](invocation)
        process.assert_awaited_once_with(invocation)
        if expected is None:
            invocation.reply.assert_not_awaited()
        else:
            invocation.reply.assert_awaited_once()
            args, kwargs = invocation.reply.call_args
            self.assertEqual(args, ("Here's your link!\n" + expected,))
            self.assertFalse(kwargs["mention_author"])
            self.assertEqual(kwargs["allowed_mentions"].to_dict(), discord.AllowedMentions.none().to_dict())
        invocation.delete.assert_not_awaited()
        invocation.edit.assert_not_awaited()
        self.assertEqual(invocation.content, invocation_content)
        if original:
            original.delete.assert_not_awaited()
            original.edit.assert_not_awaited()
            original.reply.assert_not_awaited()
            self.assertEqual(original.content, original_content)

    async def test_tracked_url_without_mention_is_ignored(self):
        invocation = self.message(TRACKED, mentioned=False)
        await self.check(invocation)
        invocation.channel.fetch_message.assert_not_awaited()

    async def test_mention_and_tracked_url(self):
        await self.check(self.message("<@987654321> " + TRACKED), CLEAN)

    async def test_mention_in_reply_uses_resolved_message(self):
        original = self.message(TRACKED, mentioned=False)
        invocation = self.message("<@987654321>", reference=self.reference(original))
        await self.check(invocation, CLEAN, original)
        invocation.channel.fetch_message.assert_not_awaited()

    async def test_mention_in_reply_uses_cached_message(self):
        original = self.message(TRACKED, mentioned=False)
        invocation = self.message("<@987654321>", reference=self.reference(original, cached=True))
        await self.check(invocation, CLEAN, original)
        invocation.channel.fetch_message.assert_not_awaited()

    async def test_mention_in_reply_fetches_uncached_message(self):
        original = self.message(TRACKED, mentioned=False)
        invocation = self.message("<@987654321>", reference=self.reference())
        invocation.channel.fetch_message.return_value = original
        await self.check(invocation, CLEAN, original)
        invocation.channel.fetch_message.assert_awaited_once_with(123)

    async def test_reply_to_clean_url_is_ignored(self):
        original = self.message(CLEAN, mentioned=False)
        await self.check(self.message("<@987654321>", reference=self.reference(original)), original=original)

    async def test_mention_without_reply_or_tracked_url_is_ignored(self):
        await self.check(self.message("<@987654321> hello"))

    async def test_invocation_wins_over_reference(self):
        original = self.message(OTHER_TRACKED, mentioned=False)
        invocation = self.message(TRACKED, reference=self.reference(original))
        await self.check(invocation, CLEAN, original)
        invocation.channel.fetch_message.assert_not_awaited()

    async def test_invocation_wins_without_fetching_reference(self):
        invocation = self.message(TRACKED, reference=self.reference())
        await self.check(invocation, CLEAN)
        invocation.channel.fetch_message.assert_not_awaited()

    async def test_clean_invocation_falls_back_to_reference(self):
        original = self.message(OTHER_TRACKED, mentioned=False)
        await self.check(self.message(CLEAN, reference=self.reference(original)), OTHER_CLEAN, original)

    async def test_ordinary_clean_urls_are_ignored(self):
        for mentioned in (False, True):
            await self.check(self.message(CLEAN, mentioned=mentioned))

    async def test_display_name_and_raw_mention_text_do_not_count(self):
        await self.check(self.message("DLC-E <@987654321> " + TRACKED, mentioned=False))

    async def test_reference_without_bot_mention_is_ignored(self):
        invocation = self.message("clean please", mentioned=False, reference=self.reference())
        await self.check(invocation)
        invocation.channel.fetch_message.assert_not_awaited()

    async def test_multiple_tracked_urls_exclude_clean_urls(self):
        await self.check(self.message(TRACKED + " " + CLEAN + " " + OTHER_TRACKED),
                         CLEAN + "\n" + OTHER_CLEAN)

    def url_of_length(self, length):
        prefix = "https://example.com/"
        return prefix + "a" * (length - len(prefix))

    async def check_long_reply(self, links, expected):
        original = self.message(
            "\n".join(link + ("&" if "?" in link else "?") + "utm_source=test"
                      for link in links),
            mentioned=False,
        )
        invocation = self.message("<@987654321>", reference=self.reference(original))
        with patch.object(self.app["bot"], "process_commands", new_callable=AsyncMock):
            await self.app["on_message"](invocation)
        replies = [call.args[0] for call in invocation.reply.await_args_list]
        self.assertEqual(replies, expected)
        self.assertTrue(all(len(content) <= 2000 for content in replies))
        invocation.reply.assert_awaited_once()
        if expected != ["Holy crap, that URL is too long!"]:
            returned_links = "\n".join(replies).split("\n")[1:]
            self.assertEqual(returned_links, links)
        for call in invocation.reply.await_args_list:
            self.assertNotIn("file", call.kwargs)
            self.assertNotIn("files", call.kwargs)
            self.assertFalse(call.kwargs["mention_author"])
            self.assertEqual(call.kwargs["allowed_mentions"].to_dict(),
                             discord.AllowedMentions.none().to_dict())
        for message in (invocation, original):
            message.delete.assert_not_awaited()
            message.edit.assert_not_awaited()
        original.reply.assert_not_awaited()

    async def test_response_exactly_2000_characters_stays_in_one_reply(self):
        links = [self.url_of_length(900),
                 self.url_of_length(2000 - len("Here's your link!\n") - 901)]
        expected = "Here's your link!\n" + "\n".join(links)
        self.assertEqual(len(expected), 2000)
        await self.check_long_reply(links, [expected])

    async def test_response_2001_characters_returns_length_warning(self):
        links = [self.url_of_length(900),
                 self.url_of_length(2001 - len("Here's your link!\n") - 901)]
        await self.check_long_reply(links, ["Holy crap, that URL is too long!"])

    async def test_multiple_overflows_return_one_warning(self):
        links = [self.url_of_length(length) for length in (1100, 800, 1200, 700, 100)]
        await self.check_long_reply(links, ["Holy crap, that URL is too long!"])

    async def test_single_2000_character_url_with_heading_returns_warning(self):
        link = self.url_of_length(2000)
        await self.check_long_reply([link], ["Holy crap, that URL is too long!"])

    async def test_url_over_2000_characters_returns_warning_without_attachment(self):
        links = [CLEAN, self.url_of_length(2001), OTHER_CLEAN]
        await self.check_long_reply(links, ["Holy crap, that URL is too long!"])

    async def test_oversized_invocation_returns_warning(self):
        invocation = self.message(self.url_of_length(2001) + "?utm_source=test")
        with patch.object(self.app["bot"], "process_commands", new_callable=AsyncMock):
            await self.app["on_message"](invocation)
        invocation.reply.assert_awaited_once_with(
            "Holy crap, that URL is too long!",
            allowed_mentions=unittest.mock.ANY, mention_author=False,
        )
        self.assertEqual(invocation.reply.call_args.kwargs["allowed_mentions"].to_dict(),
                         discord.AllowedMentions.none().to_dict())
        invocation.delete.assert_not_awaited()
        invocation.edit.assert_not_awaited()

    async def test_fetch_failures_are_ignored_without_logging_content(self):
        for exception, status in ((discord.NotFound, 404), (discord.Forbidden, 403),
                                  (discord.HTTPException, 500)):
            invocation = self.message("<@987654321>", reference=self.reference())
            invocation.channel.fetch_message.side_effect = exception(
                SimpleNamespace(status=status, reason="test"), "test failure")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                await self.check(invocation)
            self.assertEqual(output.getvalue(), "")

    async def test_deleted_reference_is_ignored(self):
        reference = self.reference()
        reference.resolved = discord.DeletedReferencedMessage(reference)
        invocation = self.message("<@987654321>", reference=reference)
        await self.check(invocation)
        invocation.channel.fetch_message.assert_not_awaited()

    async def test_cross_channel_fetch_is_ignored(self):
        reference = self.reference()
        reference.channel_id = 999
        invocation = self.message("<@987654321>", reference=reference)
        await self.check(invocation)
        invocation.channel.fetch_message.assert_not_awaited()

    async def test_forward_reference_is_ignored(self):
        reference = self.reference()
        reference.type = discord.MessageReferenceType.forward
        invocation = self.message("<@987654321>", reference=reference)
        await self.check(invocation)
        invocation.channel.fetch_message.assert_not_awaited()

    async def test_bot_own_messages_are_ignored(self):
        invocation = self.message(TRACKED)
        invocation.author = self.bot_user
        with patch.object(self.app["bot"], "process_commands", new_callable=AsyncMock) as process:
            await self.app["on_message"](invocation)
        process.assert_not_awaited()
        invocation.reply.assert_not_awaited()
        invocation.delete.assert_not_awaited()
        invocation.edit.assert_not_awaited()

    async def test_reply_failure_never_deletes_or_edits(self):
        invocation = self.message(TRACKED)
        invocation.reply.side_effect = discord.Forbidden(
            SimpleNamespace(status=403, reason="test"), TRACKED)
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch.object(
            self.app["bot"], "process_commands", new_callable=AsyncMock,
        ):
            await self.app["on_message"](invocation)
        self.assertNotIn(TRACKED, output.getvalue())
        invocation.delete.assert_not_awaited()
        invocation.edit.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
