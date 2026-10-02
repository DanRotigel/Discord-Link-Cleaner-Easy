# Discord Link Cleaner Easy

> **Before deploying:** Please review the [Privacy Policy](./PRIVACY.md) and [Disclaimer & Terms of Use](./DISCLAIMER.md). By deploying DLC-E, you acknowledge that you are responsible for your own Discord bot, hosting account, permissions, and use of the software.

Discord Link Cleaner (DLC) is a Discord bot that removes common tracking parameters from links when you mention the bot.

This fork focuses on making DLC easy to deploy for nontechnical Discord administrators. The recommended setup uses Railway, so you do not need to install Python, use Linux, or run commands in a terminal.

## What DLC Does

When someone mentions the bot, DLC:
1. Looks for tracked URLs in that message.
2. If none are found and the mention is in a reply, checks the message being replied to.
3. Removes known tracking parameters such as `utm_source`, `fbclid`, and `gclid`.
4. Replies to the invocation with `Here's your link!` followed by the cleaned URL(s).

DLC never deletes or edits either message. Tracked links without a bot mention and clean links are ignored. If both messages contain tracked URLs, the invocation message takes priority.

It works at the Discord server level, so members do not need a browser extension, custom Discord client, or mobile app.

## What You Need

Before starting, you need:
- A Discord account
- Permission to add a bot to the Discord server you want to protect
- A Railway account
- About five minutes

No command-line experience is required.

## Easy Installation with Railway

This is the recommended installation method for this fork.

Railway runs your own copy of DLC continuously in the cloud. The DLC project does not operate a shared bot or host your Discord messages.

**Cost:** Railway currently lists its **Hobby plan at $5/month minimum**, which includes $5 of monthly resource usage. DLC-E is lightweight, so this is the plan we recommend for a simple always-on installation. Railway pricing can change, and usage beyond the included amount can cost extra. See [Railway pricing](https://railway.com/pricing) for current details.

**[Deploy DLC-E on Railway](https://railway.com/deploy/dlc-e)**

That link opens the public DLC-E Railway template. Railway will create your own copy of the service; you only need to supply your Discord bot token.

### Step 1: Create a Discord Application

1. Go to https://discord.com/developers/applications
2. Click **New Application**.
3. Give the application a name, such as **DLC**.
4. Click **Create**.

### Step 2: Enable the Bot

1. Open the **Bot** page for your application.
2. Under **Privileged Gateway Intents**, enable **Message Content Intent**.
3. Copy the bot token.
   - If Discord only shows **Reset Token**, use that to generate a new token.
   - Treat this token like a password. Do not post it publicly or commit it to GitHub.

DLC needs Message Content Intent so it can inspect messages for links that contain tracking parameters.

### Step 3: Configure Discord Installation Permissions

Open the **Installation** page for your Discord application.

Under **Default Install Settings → Guild Install**, include these scopes:
- `bot`
- `applications.commands`

Give the bot these permissions:
- View Channels
- Send Messages
- Send Messages in Threads
- Read Message History

Save the changes.

### Step 4: Deploy DLC to Railway

1. Open the public template: **[Deploy DLC-E on Railway](https://railway.com/deploy/dlc-e)**.
2. Sign in to Railway if prompted.
3. Click **Deploy Now**.
4. If Railway shows a **Configure** button, click it.
5. Paste your Discord bot token into `DISCORD_BOT_TOKEN`.
6. Leave `DATA_DIR` set to `/data`.
7. Start the deployment.

The template already includes the persistent volume DLC-E uses to save its settings, so you should not need to create storage manually.

Railway will build and start your private DLC-E instance. Wait until the service status shows **Online** before continuing.

If the deployment immediately crashes, first check that `DISCORD_BOT_TOKEN` contains the current token from the Discord Developer Portal.

### Step 5: Add the Bot to Your Discord Server

Return to the Discord Developer Portal.

1. Open the **Installation** page for your DLC application.
2. Find **Install Link**.
3. Make sure it is set to **Discord Provided Link**.
4. Copy the install link.
5. Open the link in your browser.
6. Select the Discord server you want to protect.
7. Authorize the bot.

### Step 6: Test DLC

Mention the bot using Discord's mention picker and include this link in the same message, in a channel the bot can access:

```text
https://example.com/?utm_source=discord&utm_campaign=dlc-test
```

DLC should leave your message intact and reply:

```text
Here's your link!
https://example.com/
```

If that happens, DLC is working.

## Using DLC

To clean a link, mention the bot and paste the tracked link in the same message. Alternatively, reply to a message containing a tracked link and mention the bot in your reply.

DLC replies to your invocation with only the cleaned URL(s), leaving both messages intact. It checks your invocation first; a clean URL in the invocation does not prevent it from checking the referenced message. If the referenced message is unavailable or the bot cannot read it, DLC does nothing.

Cleaned links are returned in one reply. If the complete response, including the heading and newlines, exceeds Discord's 2,000-character limit, DLC replies with "Holy crap, that URL is too long!" instead. It does not attach files, truncate URLs, or split the response across messages.

## Discord Commands

### `/settings`
Shows the current DLC settings.

### `/set_mention`
Retained for configuration compatibility. This legacy setting does not affect mention-triggered link replies, which do not mention the author.

### `/set_require_links`
Retained for configuration compatibility. Mention-triggered replies always require a tracked URL in the invocation or referenced message, regardless of this setting.

### `/set_regex`
Changes the pattern DLC uses to detect URLs. Most users should leave the default unchanged.

### `/trackers list`
Shows the tracking parameters DLC currently recognizes.

### `/trackers add`
Adds a tracking parameter.

### `/trackers remove`
Removes a tracking parameter.

Settings and tracker data are stored on the Railway persistent volume so they survive restarts.

## Privacy and Security

DLC must receive message content in the Discord channels it protects so it can detect tracked URLs.

This fork is designed to minimize additional data handling:
- DLC runs in your own Railway project.
- The DLC project does not operate a central hosted bot.
- Discord bot tokens are supplied through Railway environment variables.
- Bot tokens are not stored in `config.json` or committed to GitHub.
- DLC does not intentionally store Discord message contents, URLs, or usernames.
- URL cleaning is performed locally by the running DLC process rather than by sending URLs to an external cleaning API.

Railway is a third-party hosting provider, so your DLC instance runs on Railway infrastructure.

## Troubleshooting

### Railway says the service crashed
Check that `DISCORD_BOT_TOKEN` exists in Railway **Variables** and contains the current bot token.

### The bot is online but does not clean links
Check that:
- **Message Content Intent** is enabled.
- The bot has access to the channel.
- The bot has the required permissions.
- You mentioned the bot using Discord's mention picker.
- The invocation or referenced message contains a tracker DLC recognizes.
- For reply invocations, the bot can read the referenced message.

### Settings disappear after a restart
Confirm:
- `DATA_DIR=/data`
- A persistent volume is mounted at `/data`

### The bot does not clean a link from a reply
Mention the bot in the reply and confirm that the original message still exists and the bot has **Read Message History** permission in that channel.

DLC does not require **Manage Messages** permission.

## Removing DLC

To stop using DLC:
1. Remove or delete the DLC project from Railway.
2. Remove the DLC bot from your Discord server.
3. Optionally reset the bot token in the Discord Developer Portal.

## Advanced / Manual Hosting

DLC can still be hosted manually on another computer or cloud server.

This fork is primarily optimized for the browser-based Railway installation above.

Requirements:
- Python 3.12
- `discord.py`
- `DISCORD_BOT_TOKEN` environment variable

Optional:
- `DATA_DIR` controls where `config.json` and `trackers.json` are stored.

Start with:

```bash
python main.py
```

## Open Source and License

This project is open source and licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**.

This fork is based on the original [Discord-Link-Cleaner](https://github.com/StroepWafel/Discord-Link-Cleaner) project by StroepWafel.

See the `LICENSE` file for the full license text.
