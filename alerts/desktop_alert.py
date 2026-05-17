"""
alerts/desktop_alert.py
Cross-platform desktop notifications.
Works on Windows (win10toast / plyer), macOS (plyer / osascript), Linux (plyer / notify-send).
"""

import subprocess
import sys
import os


def send_desktop_alert(symbol: str, signal: str, ltp: float) -> bool:
    """
    Show a desktop notification.
    Tries plyer first (cross-platform), then platform-specific fallbacks.
    Returns True if notification was sent successfully.
    """
    title   = f"FNO Alert: {symbol}"
    message = f"{signal} | ₹{ltp}"

    # 1. Try plyer (works on Windows, macOS, Linux)
    try:
        from plyer import notification
        notification.notify(
            title=title,
            message=message,
            app_name="NSE FNO Scanner",
            timeout=8
        )
        return True
    except Exception:
        pass

    # 2. macOS fallback via osascript
    if sys.platform == "darwin":
        try:
            subprocess.run([
                "osascript", "-e",
                f'display notification "{message}" with title "{title}"'
            ], check=True, capture_output=True)
            return True
        except Exception:
            pass

    # 3. Linux fallback via notify-send
    if sys.platform.startswith("linux"):
        try:
            subprocess.run(
                ["notify-send", title, message],
                check=True, capture_output=True
            )
            return True
        except Exception:
            pass

    # 4. Windows fallback via win10toast
    if sys.platform == "win32":
        try:
            from win10toast import ToastNotifier
            ToastNotifier().show_toast(title, message, duration=8, threaded=True)
            return True
        except Exception:
            pass

    # 5. Last resort: print to console
    print(f"[ALERT] {title} — {message}")
    return False
