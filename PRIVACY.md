# Privacy Policy

_Last updated: September 21, 2026_

This Privacy Policy describes how Discord Link Cleaner Easy ("DLC-E") handles data when you deploy and use the software.

## 1. DLC-E is self-hosted

DLC-E is open-source software that you deploy into your own Railway project or other hosting environment.

The DLC-E project does **not** operate a shared hosted bot, does not receive your Discord bot token, and does not centrally collect messages from your Discord server.

Your deployment is operated through third-party services you choose, such as Discord and Railway. Their own privacy policies and terms also apply.

## 2. Message content

To remove tracking parameters, DLC-E must receive the contents of messages in Discord channels where the bot has access and where Discord provides message content to the bot.

DLC-E examines message text to identify URLs and tracking parameters. When a tracked URL is detected, DLC-E can delete the original message and repost a cleaned version.

The current DLC-E code does not intentionally store Discord message contents, URLs, usernames, or user IDs in a database or persistent log.

Message content is processed by the running DLC-E instance and may necessarily pass through Discord and the infrastructure of the hosting provider running your deployment.

## 3. Discord bot token

Your Discord bot token is a secret credential used to authenticate your bot with Discord.

For the recommended Railway deployment:

- The token is supplied through the `DISCORD_BOT_TOKEN` environment variable.
- DLC-E does not store the token in `config.json`.
- The token should never be committed to GitHub or shared publicly.

You are responsible for keeping your token secure and resetting it in the Discord Developer Portal if you believe it has been exposed.

## 4. Persistent configuration

DLC-E stores bot settings and tracker configuration in:

- `config.json`
- `trackers.json`

In the recommended Railway deployment, these files are stored on the persistent volume mounted at `/data`.

These files contain DLC-E configuration and tracker definitions. They are not intended to contain Discord message contents, URLs, usernames, or the Discord bot token.

## 5. External services

DLC-E communicates with Discord in order to operate the bot.

The current URL-cleaning logic does not intentionally send posted URLs to an external URL-cleaning, analytics, or tracking service.

If you deploy DLC-E using Railway, your instance runs on Railway infrastructure. Railway may process infrastructure, account, billing, network, and service data according to Railway's own policies.

Discord may process Discord account, server, message, and bot data according to Discord's own policies.

## 6. Logs

DLC-E may produce operational logs needed to run and troubleshoot the bot, such as startup messages and errors.

The project is designed to avoid intentionally logging Discord message contents, URLs, usernames, or unnecessary identifiers.

Your hosting provider may independently create infrastructure or platform logs.

## 7. Data retention

DLC-E itself is designed around minimal retention.

Persistent data is generally limited to DLC-E settings and tracker configuration. Message contents and cleaned URLs are not intentionally retained by DLC-E after processing.

Third-party providers may have their own retention practices.

## 8. Administrator responsibilities

The person who deploys DLC-E controls where the bot is installed, which Discord channels it can access, and which permissions it receives.

Server administrators should:

- Give DLC-E access only to channels where link cleaning is desired.
- Use the minimum permissions necessary.
- Inform their community about the presence and function of the bot when appropriate.
- Comply with Discord rules, applicable laws, and their own privacy obligations.

## 9. Changes to this policy

This Privacy Policy may be updated as DLC-E changes. The version in this repository applies to the corresponding version of the software.

## 10. Questions and source code

DLC-E is open source. You can inspect the software and its data-handling behavior in this repository:

https://github.com/DanRotigel/Discord-Link-Cleaner-Easy

This policy describes the DLC-E project itself. It does not replace the privacy policies or terms of Discord, Railway, or any other third-party service you use.
