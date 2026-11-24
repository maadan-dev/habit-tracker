"""Display and input (Member B): menus, tables, weekly grid, and text calendar."""

import calendar
from datetime import date
from functools import wraps

from storage import REPORT_FILE, backup_data, export_csv, load_data, save_data
from tracker import (
    WEEKDAYS,
    add_habit,
    all_completed_days,
    current_week_dates,
    find_habit,
    get_insights,
    mark_done,
    parse_iso_date,
    ranked_stats,
    remove_habit,
    rename_habit,
)


def autosave(func):
    """Decorator that saves habits.json automatically whenever an action succeeds."""

    @wraps(func)
    def wrapper(data):
        changed = func(data)
        if changed is not False:
            save_data(data)
        return changed

    return wrapper


def ask(prompt, validator=None, allow_blank=False):
    """Keep prompting until the user enters valid input."""
    while True:
        raw = input(prompt).strip()
        if not raw and allow_blank:
            return None
        try:
            return validator(raw) if validator else raw
        except ValueError as err:
            print(f"  ! {err}")


def parse_number(raw, low, high):
    if not raw.isdigit() or not (low <= int(raw) <= high):
        raise ValueError(f"Enter a number between {low} and {high}.")
    return int(raw)


def parse_year_month(raw):
    parts = raw.split("-")
    valid = (
        len(parts) == 2
        and len(parts[0]) == 4
        and len(parts[1]) == 2
        and parts[0].isdigit()
        and parts[1].isdigit()
    )
    if not valid or not (1 <= int(parts[1]) <= 12):
        raise ValueError("Use YYYY-MM format (e.g., 2026-11).")
    return int(parts[0]), int(parts[1])


def pick_habit(data, action):
    """Show the streak-sorted habit list and return the chosen habit name."""
    rows = ranked_stats(data)
    if not rows:
        print("No habits yet. Add one first.")
        return None

    for i, s in enumerate(rows, 1):
        mark = "[x]" if s["done_today"] else "[ ]"
        print(f"  {i}. {s['name']} {mark} ({s['streak']}d streak)")

    choice = ask(
        f"Habit number to {action} (blank to cancel): ",
        lambda text: parse_number(text, 1, len(rows)),
        allow_blank=True,
    )
    if choice is None:
        return None
    return rows[choice - 1]["name"]


def show_status(data, today=None):
    today = today or date.today()
    rows = ranked_stats(data, today)
    freeze = "ON" if data["settings"].get("streak_freeze") else "OFF"
    print(f"\nToday: {today:%a %d %b %Y}   |   Streak Freeze: {freeze}\n")

    if not rows:
        print("No habits tracked yet. Choose option 1 to add one.")
        return

    width = max(20, max(len(s["name"]) + 4 for s in rows))
    print(
        f"{'Habit':<{width}} {'Today':^7} {'Streak':>8} "
        f"{'Best':>7} {'7d':>6} {'30d':>6}   Week Target"
    )
    print("-" * (width + 52))

    for i, s in enumerate(rows, 1):
        label = f"{i}. {s['name']}"
        mark = "[x]" if s["done_today"] else "[ ]"
        unit = "day" if s["streak"] == 1 else "days"
        streak_txt = f"{s['streak']} {unit}"
        best_txt = f"{s['longest']}d"
        status = "MET" if s["target_met"] else "in progress"
        print(
            f"{label:<{width}} {mark:^7} {streak_txt:>8} {best_txt:>7} "
            f"{s['rate_7d']:>5.0f}% {s['rate_30d']:>5.0f}%   "
            f"{s['week_done']}/{s['target']} ({status})"
        )


@autosave
def handle_add(data):
    def check_name(raw):
        if not raw:
            raise ValueError("Habit name cannot be empty.")
        if find_habit(data["habits"], raw):
            raise ValueError(f"Habit '{raw}' already exists.")
        return raw

    name = ask("Habit name: ", check_name)
    target = ask(
        "Weekly target 1-7 [default 7]: ",
        lambda text: parse_number(text, 1, 7),
        allow_blank=True,
    )
    ok, msg = add_habit(data, name, target or 7)
    print(msg)
    return ok


@autosave
def handle_mark_today(data):
    name = pick_habit(data, "mark done")
    if not name:
        return False
    ok, msg = mark_done(data, name)
    print(msg)
    if ok:
        show_status(data)
    return ok


@autosave
def handle_mark_past(data):
    name = pick_habit(data, "mark for a past date")
    if not name:
        return False
    past_day = ask("Date (YYYY-MM-DD): ", parse_iso_date)
    ok, msg = mark_done(data, name, past_day)
    print(msg)
    return ok


@autosave
def handle_rename(data):
    old_name = pick_habit(data, "rename")
    if not old_name:
        return False

    def check_new_name(raw):
        existing = find_habit(data["habits"], raw)
        if existing and existing != old_name:
            raise ValueError(f"Habit '{existing}' already exists.")
        return raw

    current_target = data["habits"][old_name]["target_per_week"]
    new_name = (
        ask(
            f"New name [Enter to keep '{old_name}']: ", check_new_name, allow_blank=True
        )
        or old_name
    )
    new_target = ask(
        f"Weekly target 1-7 [Enter to keep {current_target}]: ",
        lambda text: parse_number(text, 1, 7),
        allow_blank=True,
    )
    ok, msg = rename_habit(data, old_name, new_name, new_target)
    print(msg)
    return ok


@autosave
def handle_remove(data):
    name = pick_habit(data, "remove")
    if not name:
        return False
    ok, msg = remove_habit(data, name)
    print(msg)
    return ok


def handle_weekly_grid(data):
    rows = ranked_stats(data)
    if not rows:
        print("No habits tracked yet.")
        return

    days = current_week_dates()
    width = max(20, max(len(s["name"]) for s in rows) + 2)
    day_headers = " ".join(f"{d:>3}" for d in WEEKDAYS)

    print(f"\nWeek of {days[0]:%d %b} - {days[-1]:%d %b %Y}\n")
    print(f"{'Habit':<{width}} {day_headers}   Target")
    print("-" * (width + 42))

    for s in rows:
        cells = " ".join(f"{mark:>3}" for mark in s["week_grid"])
        flag = "MET" if s["target_met"] else ""
        print(f"{s['name']:<{width}} {cells}   {s['week_done']}/{s['target']} {flag}")


def handle_calendar(data):
    if not data["habits"]:
        print("Add at least one habit first to view the calendar.")
        return

    today = date.today()
    chosen = ask(
        f"Month YYYY-MM [default {today:%Y-%m}]: ",
        parse_year_month,
        allow_blank=True,
    )
    year, month = chosen or (today.year, today.month)
    perfect_days = all_completed_days(data, year, month)

    print(f"\n   {calendar.month_name[month]} {year}  (* = all habits done)")
    print(" " + " ".join(f"{d:>3}" for d in WEEKDAYS))

    for week in calendar.monthcalendar(year, month):
        line = []
        for day_num in week:
            if day_num == 0:
                line.append("   ")
            elif day_num in perfect_days:
                line.append(f"{day_num:>2}*")
            else:
                line.append(f"{day_num:>2} ")
        print(" " + " ".join(line))

    print(f"\nPerfect days this month: {len(perfect_days)}")


def handle_insights(data):
    info = get_insights(data)
    if not info:
        print("No habits tracked yet.")
        return

    print("\n--- Habit Insights ---")
    print("Strongest weekday per habit:")
    for name, weekday in info["top_weekdays"]:
        print(f"  - {name}: {weekday}")

    best = info["most_consistent"]
    worst = info["most_missed"]
    print(
        f"\nMost consistent (30d): {best['name']} "
        f"({best['rate_30d']:.0f}%, best streak {best['longest']}d)"
    )
    print(f"Most missed (30d):     {worst['name']} ({worst['missed_30d']}/30 missed)")


def handle_export(data):
    rows = ranked_stats(data)
    if not rows:
        print("No habits to export.")
        return

    custom_path = ask(f"CSV filename [default {REPORT_FILE}]: ", allow_blank=True)
    saved_to = export_csv(rows, custom_path or REPORT_FILE)
    print(f"Exported {len(rows)} habit(s) to {saved_to}.")


@autosave
def handle_settings(data):
    enabled = not data["settings"].get("streak_freeze", False)
    data["settings"]["streak_freeze"] = enabled
    desc = "ON (1 missed day/week allowed)" if enabled else "OFF (strict streaks)"
    print(f"Streak Freeze is now {desc}.")


MENU = {
    "1": ("Add habit", handle_add),
    "2": ("Mark habit done (today)", handle_mark_today),
    "3": ("Mark habit done (past date)", handle_mark_past),
    "4": ("Rename habit / change target", handle_rename),
    "5": ("Remove habit", handle_remove),
    "6": ("Show status", show_status),
    "7": ("Weekly summary grid (Mon-Sun)", handle_weekly_grid),
    "8": ("Monthly completion calendar", handle_calendar),
    "9": ("Insights", handle_insights),
    "10": ("Export report to CSV", handle_export),
    "11": ("Settings (toggle streak freeze)", handle_settings),
}


def main():
    backup_path = backup_data()
    if backup_path:
        print(f"Backup created: {backup_path}")

    data, message = load_data()
    print(message)

    rows = ranked_stats(data)
    not_done = [s["name"] for s in rows if not s["done_today"]]
    if not_done:
        print(f"\nStill not done today ({len(not_done)}): {', '.join(not_done)}")
    elif rows:
        print("\nAll habits completed for today!")

    show_status(data)

    while True:
        print("\n--- Menu ---")
        for key, (label, _) in MENU.items():
            if key == "11":
                flag = "ON" if data["settings"].get("streak_freeze") else "OFF"
                print(f"  {key:>2}. {label} [{flag}]")
            else:
                print(f"  {key:>2}. {label}")
        print("   0. Quit")

        choice = input("\nMenu choice: ").strip()
        if choice == "0":
            save_data(data)
            print("Saved. Goodbye!")
            break

        if choice in MENU:
            _, handler = MENU[choice]
            handler(data)
        else:
            print("  ! Invalid choice. Pick a number from the menu.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nExiting.")
