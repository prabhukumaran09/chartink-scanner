"""
config.py
Loads and saves scanner configuration to config.json.
Falls back to safe defaults if the file doesn't exist.
"""

import json
import os

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    # Alert channels
    "desktop_alerts":    True,
    "telegram_alerts":   False,
    "telegram_token":    "",
    "telegram_chat_id":  "",

    # Auto-scan
    "auto_scan":         False,
    "scan_interval":     5,       # minutes

    # Filters
    "min_price":         100,     # ignore stocks below ₹100
    "min_volume_ratio":  1.5,     # volume must be 1.5x 20D avg for volume scanner

    # Built-in scanner toggles
    "scan_52w_high":     True,
    "scan_52w_low":      True,
    "scan_volume_surge": True,
    "scan_price_breakout": True,
    "scan_rsi_ob":       True,
    "scan_rsi_os":       True,
    "scan_macd_cross":   True,
    "scan_bb_squeeze":   False,

    # Custom user-defined conditions
    "custom_conditions": [],
}


def load_config() -> dict:
    """Load config from file, merging with defaults for any missing keys."""
    cfg = DEFAULT_CONFIG.copy()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                saved = json.load(f)
            cfg.update(saved)
        except Exception as e:
            print(f"[config] Failed to load config.json: {e}. Using defaults.")
    return cfg


def save_config(cfg: dict) -> None:
    """Save config dict to file."""
    try:
        # Don't save the Telegram token to file if running on Streamlit Cloud
        # (use Streamlit secrets instead)
        safe = {k: v for k, v in cfg.items()}
        with open(CONFIG_FILE, "w") as f:
            json.dump(safe, f, indent=2)
    except Exception as e:
        print(f"[config] Failed to save config.json: {e}")
