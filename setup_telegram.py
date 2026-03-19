#!/usr/bin/env python3
# =============================================================
# setup_telegram.py
# PURPOSE:  Interactive setup for Telegram alerts bot
#           Run this once to configure your monitoring alerts
#
# USAGE:
#   python setup_telegram.py
#
# WHAT IT DOES:
#   1. Walks you through creating a Telegram bot
#   2. Gets your chat ID automatically
#   3. Tests the connection
#   4. Updates your .env file
#   5. Sends a test alert
#
# LAST UPDATED: March 2026
# =============================================================

import os
import sys
import time
import requests


def main():
    print("\n🤖 Telegram Alerts Setup")
    print("=" * 40)
    print()
    print("This sets up Telegram notifications for:")
    print("  • Price alerts you create")
    print("  • System health issues")
    print("  • Daily 9am IST market report")
    print()

    # Step 1 — create bot
    print("STEP 1 — Create your Telegram bot")
    print("-" * 35)
    print()
    print("1. Open Telegram and search for: @BotFather")
    print("2. Send: /newbot")
    print("3. Choose a name (e.g. 'Artha Finance Alerts')")
    print("4. Choose a username (e.g. 'arthafinance_bot')")
    print("5. BotFather will give you a token like:")
    print("   1234567890:ABCDEfghijklmnopqrstuvwxyz")
    print()

    token = input("Paste your bot token here: ").strip()
    if not token or ":" not in token:
        print("❌ Invalid token format. Should be like: 1234567890:ABCdef...")
        sys.exit(1)

    # Test token
    print()
    print("Testing token...")
    resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
    if resp.status_code != 200:
        print("❌ Invalid token. Check BotFather and try again.")
        sys.exit(1)

    bot_info = resp.json()["result"]
    print(f"✅ Bot verified: @{bot_info['username']} ({bot_info['first_name']})")

    # Step 2 — get chat ID
    print()
    print("STEP 2 — Get your chat ID")
    print("-" * 35)
    print()
    print(f"1. Open Telegram and start a chat with @{bot_info['username']}")
    print("2. Send any message (e.g. 'hello')")
    print()
    input("Press Enter after you've sent a message to your bot...")

    print("Getting your chat ID...")
    time.sleep(1)

    resp = requests.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=10)
    updates = resp.json().get("result", [])

    if not updates:
        print("❌ No messages found. Make sure you sent a message to your bot.")
        print("   Then run this script again.")
        sys.exit(1)

    chat_id = str(updates[-1]["message"]["chat"]["id"])
    sender  = updates[-1]["message"]["from"].get("first_name", "User")
    print(f"✅ Chat ID found: {chat_id} (sender: {sender})")

    # Step 3 — send test message
    print()
    print("STEP 3 — Sending test alert...")
    print("-" * 35)

    test_msg = (
        "🟢 ALL GOOD — Artha\n"
        "✅ Telegram alerts configured!\n\n"
        "You will receive:\n"
        "• Price alerts when your thresholds are hit\n"
        "• System warnings if anything breaks\n"
        "• Daily market report at 9am IST\n\n"
        "Not financial advice."
    )

    resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": test_msg},
        timeout=10,
    )

    if resp.status_code != 200:
        print("❌ Failed to send test message.")
        sys.exit(1)

    print("✅ Test message sent! Check your Telegram.")

    # Step 4 — update .env
    print()
    print("STEP 4 — Updating .env file...")
    print("-" * 35)

    env_path = ".env"
    if not os.path.exists(env_path):
        print("❌ .env file not found. Run: cp .env.example .env")
        sys.exit(1)

    with open(env_path, "r") as f:
        content = f.read()

    # Replace or add TELEGRAM vars
    def set_var(text, key, value):
        import re
        pattern = rf"^{key}=.*$"
        replacement = f"{key}={value}"
        if re.search(pattern, text, re.MULTILINE):
            return re.sub(pattern, replacement, text, flags=re.MULTILINE)
        else:
            return text + f"\n{replacement}\n"

    content = set_var(content, "TELEGRAM_BOT_TOKEN", token)
    content = set_var(content, "TELEGRAM_CHAT_ID", chat_id)

    with open(env_path, "w") as f:
        f.write(content)

    print("✅ .env updated with TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")

    # Done
    print()
    print("=" * 40)
    print("🎉 Telegram setup complete!")
    print()
    print("Next steps:")
    print("  1. Restart your backend: docker-compose restart backend")
    print("  2. Create a price alert in the app")
    print("  3. You'll get notified instantly on Telegram")
    print()
    print(f"Bot: @{bot_info['username']}")
    print(f"Chat ID: {chat_id}")
    print()


if __name__ == "__main__":
    main()
