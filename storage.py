"""Data and persistence: JSON load/save, startup backup, CSV export."""

import csv
import json
import os
from datetime import datetime

DATA_FILE = "habits.json"
BACKUP_DIR = "backups"
REPORT_FILE = "habit_report.csv"


def empty_data():
    return {
        "settings": {"streak_freeze": False},
        "habits": {},
    }


def _validate_data(raw):
    """Check that loaded JSON matches our expected tracker structure."""
    if not isinstance(raw, dict):
        raise TypeError("Data file must contain a JSON object.")

    if "habits" in raw and isinstance(raw["habits"], dict):
        settings = raw.get("settings", {})
        if not isinstance(settings, dict):
            raise TypeError("Settings must be a JSON object.")
        freeze = bool(settings.get("streak_freeze", False))
        raw_habits = raw["habits"]
    else:
        freeze = False
        raw_habits = raw

    habits = {}
    for name, entry in raw_habits.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Habit name must be a non-empty string.")

        # Support both Level 1 format (list of dates) and full format (dict)
        if isinstance(entry, list):
            target = 7
            dates = entry
        elif isinstance(entry, dict) and isinstance(entry.get("done_dates", []), list):
            target = entry.get("target_per_week", 7)
            dates = entry.get("done_dates", [])
        else:
            raise TypeError(f"Invalid entry for habit '{name}'.")

        is_valid_target = (
            isinstance(target, int)
            and not isinstance(target, bool)
            and 1 <= target <= 7
        )
        if not is_valid_target or not all(isinstance(d, str) for d in dates):
            raise ValueError(f"Invalid target or dates for habit '{name}'.")

        habits[name.strip()] = {
            "target_per_week": target,
            "done_dates": sorted(set(dates)),
        }

    return {
        "settings": {"streak_freeze": freeze},
        "habits": habits,
    }


def backup_data():
    """Create a timestamped backup copy of the data file on startup."""
    if not os.path.exists(DATA_FILE) or os.path.getsize(DATA_FILE) == 0:
        return None

    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"habits_{stamp}.json")

    with open(DATA_FILE, encoding="utf-8") as src:
        content = src.read()
    with open(backup_path, "w", encoding="utf-8") as dst:
        dst.write(content)

    return backup_path


def load_data():
    """Load habits from JSON, handling missing, empty, or corrupted files."""
    if not os.path.exists(DATA_FILE):
        return empty_data(), f"No data file found ({DATA_FILE}). Starting fresh."

    with open(DATA_FILE, encoding="utf-8") as file:
        text = file.read().strip()

    if not text:
        return empty_data(), f"Data file ({DATA_FILE}) is empty. Starting fresh."

    try:
        raw = json.loads(text)
        data = _validate_data(raw)
        return data, f"Loaded data from {DATA_FILE}."
    except (json.JSONDecodeError, TypeError, ValueError) as err:
        return (
            empty_data(),
            f"Warning: {DATA_FILE} is corrupted ({err}). Starting fresh.",
        )


def save_data(data):
    """Save habits and settings to JSON."""
    for entry in data["habits"].values():
        entry["done_dates"] = sorted(set(entry["done_dates"]))

    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def export_csv(rows, filepath=REPORT_FILE):
    """Export the full habit report to a CSV file."""
    headers = [
        "Habit",
        "Done Today",
        "Current Streak",
        "Longest Streak",
        "7-Day Rate (%)",
        "30-Day Rate (%)",
        "Week Progress",
        "Target Met",
        "Best Weekday",
        "Missed (30d)",
        "Total Done",
    ]

    with open(filepath, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        for s in rows:
            writer.writerow(
                [
                    s["name"],
                    "Yes" if s["done_today"] else "No",
                    s["streak"],
                    s["longest"],
                    f"{s['rate_7d']:.1f}",
                    f"{s['rate_30d']:.1f}",
                    f"{s['week_done']}/{s['target']}",
                    "Yes" if s["target_met"] else "No",
                    s["best_weekday"] or "N/A",
                    s["missed_30d"],
                    s["total"],
                ]
            )

    return filepath
