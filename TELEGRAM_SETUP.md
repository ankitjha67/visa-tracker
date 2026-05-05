# Telegram Setup (v4.0.0)

Why Telegram in addition to desktop notifications:

- **Desktop toasts only fire when you're at your laptop.** Slot opens at 3 AM Sunday → you miss it
- **Focus / Do Not Disturb mode silences toasts.** Even when you're at the laptop, late-night DND eats them
- **Telegram pushes to your phone 24/7, free, globally.** Including India
- **Required for GitHub Actions deployment.** Server-side runners can't show desktop toasts; Telegram is the canonical channel

The v4.0.0 wizard automates what used to be manual setup.

## Quick path (using the wizard)

```powershell
python visa_tracker_v3.py setup-telegram
```

The wizard walks you through:

1. **Create a bot via BotFather** — instructions on screen, ~2 minutes
2. **Paste your bot token** — wizard validates it via the Telegram API
3. **Send any message to your bot** — wizard polls `/getUpdates` to auto-detect your chat_id
4. **Receive a test message** — wizard sends one and asks you to confirm
5. **Config saved** — wizard writes `config.json` with the right structure

When done, you have a working Telegram channel. Both desktop toasts and Telegram messages will fire on every alert.

## Manual setup (if the wizard doesn't work)

### Step 1 — Create the bot

1. Open Telegram on your phone
2. Search for `@BotFather` (verified blue tick)
3. Send `/newbot`
4. Follow prompts:
   - Pick a name for your bot (any text, e.g., "My Visa Tracker")
   - Pick a username ending in `bot` (e.g., `myvisaTrackerXYZ_bot`) — must be globally unique
5. BotFather replies with a token like `1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ`

**This token is sensitive.** Don't paste it in chats, screenshots, or public repos. If you do, regenerate it via `/revoke` in BotFather.

### Step 2 — Get your chat_id

There are several ways. The wizard uses option B; option A is simpler but requires a one-time manual step.

**Option A — `@userinfobot`:**

1. In Telegram, search for `@userinfobot`
2. Press Start
3. It immediately replies with your numeric ID — that's your chat_id

**Option B — your bot's `getUpdates` API:**

1. Open Telegram, find your new bot, send any message (e.g., "hi")
2. In a browser, open `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
3. Find `"chat":{"id":NUMBERS}` in the JSON. NUMBERS is your chat_id

### Step 3 — Configure the tracker

Edit `config.json`:

```json
{
  ...existing fields...
  "telegram": {
    "bot_token": "1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ",
    "chat_ids": ["YOUR_CHAT_ID_HERE"]
  },
  ...
}
```

The `chat_ids` field is an array — you can add multiple recipients (your phone + spouse's phone + a group chat ID). Group chat IDs are negative numbers; add the bot to the group, send a message, then check `/getUpdates`.

### Step 4 — Test

Restart the tracker. Or trigger a test send manually:

```powershell
python -c @"
import json
from visa_tracker_v3 import Notifier, SlotInfo
from datetime import datetime
cfg = json.load(open('config.json', encoding='utf-8-sig'))
n = Notifier({**cfg, 'notification_dry_run': False, 'desktop_alerts': False})
slot = SlotInfo(
    country='Telegram Test',
    city='Localhost',
    visa_type='Test',
    date='2026-01-01',
    detection_method='manual',
    booking_url='https://example.com/',
    confidence='high',
)
n.send([slot])
"@
```

Check Telegram on your phone. You should see the test message within seconds.

## Using environment variables (for GitHub Actions)

GitHub Actions can't read your local `config.json`. v4.0.0 supports environment variables that override the config:

| Env var | Purpose |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Overrides `config.telegram.bot_token` |
| `TELEGRAM_CHAT_ID` | Adds to `config.telegram.chat_ids` (comma-separated for multiple) |
| `NOTIFICATION_DRY_RUN` | Set to `true` to suppress sends without changing config.json |

For GitHub Actions deployment:

1. Repo Settings → Secrets and variables → Actions → New repository secret
2. Add `TELEGRAM_BOT_TOKEN` with your bot token
3. Add `TELEGRAM_CHAT_ID` with your chat_id
4. The workflow files in `.github/workflows/` already wire these env vars in

See `GITHUB_ACTIONS.md` for the full deployment guide.

## What notifications look like

Each visa slot alert sends one Telegram message with HTML formatting:

```
🎯 Visa Slot Alert! (3 slots)

🟢 United Kingdom — New Delhi
   📋 Standard Visitor
   📅 2026-05-08 14:30
   🔍 page_change (high)
   🔗 [Book Now]

🟡 Germany — Mumbai
   📋 Schengen
   📅 2026-05-12
   🔍 api (medium)
   🔗 [Book Now]
   ...
```

The 🟢 / 🟡 indicate confidence — high (slot found via API) vs medium (page change suggests slots, not yet confirmed via API). Tap "Book Now" to open the visa portal.

## Multiple recipients

To notify your spouse too:

```json
"telegram": {
  "bot_token": "...",
  "chat_ids": ["YOUR_CHAT_ID", "SPOUSE_CHAT_ID"]
}
```

Or via env var (comma-separated):

```bash
TELEGRAM_CHAT_ID=12345,67890
```

Each recipient must individually start a conversation with the bot (Telegram bots can't initiate). One-time setup per recipient.

## Group chats

To send alerts to a Telegram group (e.g., a family group, or a workgroup of immigration applicants):

1. Add your bot to the group
2. Send any message in the group (e.g., `/start@your_bot`)
3. Open `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
4. Find the group's `chat.id` — it's negative (e.g., `-100123456789`)
5. Use that ID as a `chat_ids` entry

## Privacy & security notes

- **Your bot token is a password.** Anyone with it can send messages from your bot. Treat it like an API key.
- **The bot can only send messages — it can't read your other chats.** Telegram's API limits bots to messages they're explicitly part of.
- **The bot sees nothing on your VFS account** — it's purely a notification channel. No login info passes through Telegram.
- **GitHub Actions secrets are encrypted at rest.** Even repo collaborators can't read them after they're set; only the workflow can use them.

## Troubleshooting

**"Wizard says: Telegram rejected the token"**
You probably copy-pasted incorrectly (extra space, missing colon). Tokens look like `<numbers>:<long-string>`. Re-copy from the BotFather chat.

**"Wizard says: No messages found"**
You haven't sent a message to the bot yet. Open the bot in Telegram, tap Start (or send any message), then re-run `setup-telegram`. Telegram only stores the last 24 hours of getUpdates messages, so if you wait too long after sending, the message expires.

**"Tracker is sending Telegram messages but I'm not getting them"**
Check the chat_id is right. A common mistake is using your phone number — Telegram chat_ids are different (numeric, separate identifier). Re-run `setup-telegram` to auto-detect.

**"Messages arrive but the formatting is broken"**
The Notifier uses `parse_mode: HTML`. If you see literal `<b>` tags, your bot might be configured weirdly. Re-create it via `/newbot`.

**"Want to disable Telegram temporarily without deleting config"**
Set `bot_token` to empty string (`""`). The Notifier skips Telegram if `bot_token` is falsy.

## Comparison to other channels

| Channel | Setup time | Latency | When to use |
|---|---|---|---|
| Desktop toast | 0 (built in) | <1s | At your machine, DND off |
| Telegram | 5 min wizard | 2-3s | Always-on phone push |
| Email | 10 min (SMTP creds) | 5-30s | When Telegram blocked |
| Discord | 5 min (webhook) | 1-2s | If you live in Discord |

Telegram is the recommended primary channel. Desktop toast is the recommended secondary (instant local feedback). Both fire by default once configured. Email/Discord are optional.
