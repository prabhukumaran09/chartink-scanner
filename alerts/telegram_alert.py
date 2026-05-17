"""
alerts/telegram_alert.py
Sends a message to a Telegram chat via Bot API.
"""

import urllib.request
import urllib.parse
import json


def send_telegram_alert(token: str, chat_id: str, message: str) -> bool:
    """
    Sends `message` to the given Telegram chat.
    Returns True on success, False on failure.

    Setup steps:
    1. Message @BotFather on Telegram → /newbot → copy the token
    2. Message @userinfobot to get your Chat ID
    3. Paste both into the app sidebar
    """
    if not token or not chat_id:
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({
        "chat_id":    chat_id,
        "text":       message,
        "parse_mode": "HTML"
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            return result.get("ok", False)
    except Exception as e:
        print(f"[Telegram] Alert failed: {e}")
        return False


def send_telegram_batch(token: str, chat_id: str, signals: list[dict]) -> None:
    """Send multiple signals as a single formatted Telegram message."""
    if not signals:
        return
    lines = ["<b>📊 NSE FNO Scanner Alert</b>\n"]
    for s in signals:
        emoji = "🟢" if "bull" in s.get("badge", "") else ("🔴" if "bear" in s.get("badge", "") else "🟡")
        lines.append(
            f"{emoji} <b>{s['symbol']}</b> | ₹{s['ltp']} | {s['signal']}\n"
            f"   ↳ <i>{s.get('notes','')}</i>"
        )
    msg = "\n".join(lines)
    send_telegram_alert(token, chat_id, msg)
