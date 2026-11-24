"""Tracking logic (Member A): habits, dates, streaks, freeze rule, rates, insights."""

from datetime import date, timedelta

ONE_DAY = timedelta(days=1)
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def parse_iso_date(text, today=None):
    """Validate YYYY-MM-DD format and reject future dates."""
    today = today or date.today()
    parts = text.split("-")
    valid_lengths = len(parts) == 3 and [len(p) for p in parts] == [4, 2, 2]
    if not valid_lengths or not all(p.isdigit() for p in parts):
        raise ValueError("Use YYYY-MM-DD format (e.g., 2026-11-20).")

    try:
        parsed = date.fromisoformat(text)
    except ValueError:
        raise ValueError(f"Invalid calendar date: '{text}'.") from None

    if parsed > today:
        raise ValueError("Future dates are not allowed.")
    return parsed


def to_date_set(date_strings):
    """Convert ISO strings to a set of date objects for fast O(1) lookups."""
    result = set()
    for text in date_strings:
        try:
            result.add(date.fromisoformat(text))
        except ValueError:
            continue
    return result


def find_habit(habits, name):
    """Find an existing habit name ignoring letter case."""
    target = name.strip().lower()
    for existing in habits:
        if existing.lower() == target:
            return existing
    return None


def add_habit(data, name, target_per_week=7):
    clean = name.strip()
    if not clean:
        return False, "Habit name cannot be empty."
    if find_habit(data["habits"], clean):
        return False, f"Habit '{clean}' already exists."
    if not (1 <= target_per_week <= 7):
        return False, "Weekly target must be between 1 and 7."

    data["habits"][clean] = {
        "target_per_week": target_per_week,
        "done_dates": [],
    }
    return True, f"Added '{clean}' (target: {target_per_week} days/week)."


def rename_habit(data, old_name, new_name, target_per_week=None):
    clean = new_name.strip()
    if not clean:
        return False, "Habit name cannot be empty."

    existing = find_habit(data["habits"], clean)
    if existing and existing != old_name:
        return False, f"Habit '{existing}' already exists."

    if target_per_week is not None and not (1 <= target_per_week <= 7):
        return False, "Weekly target must be between 1 and 7."

    entry = data["habits"].pop(old_name)
    if target_per_week is not None:
        entry["target_per_week"] = target_per_week
    data["habits"][clean] = entry

    t = entry["target_per_week"]
    return True, f"Updated '{old_name}' -> '{clean}' (target: {t}/week)."


def remove_habit(data, name):
    if name not in data["habits"]:
        return False, f"Habit '{name}' not found."
    del data["habits"][name]
    return True, f"Removed '{name}'."


def mark_done(data, name, day=None, today=None):
    today = today or date.today()
    day = day or today
    if day > today:
        return False, "Future dates are not allowed."

    iso = day.isoformat()
    dates = data["habits"][name]["done_dates"]
    if iso in dates:
        return False, f"'{name}' is already marked done for {iso}."

    dates.append(iso)
    dates.sort()
    return True, f"Marked '{name}' done for {iso}."


def current_streak(done, freeze=False, today=None):
    """Count consecutive days back from today (or yesterday if today isn't done yet)."""
    today = today or date.today()
    valid = {d for d in done if d <= today}
    if not valid:
        return 0

    day = today if today in valid else today - ONE_DAY
    earliest = min(valid)
    streak = 0
    frozen_weeks = set()

    while day >= earliest:
        if day in valid:
            streak += 1
        elif freeze:
            week = day.isocalendar()[:2]  # (iso_year, iso_week)
            if week in frozen_weeks:
                break
            frozen_weeks.add(week)
        else:
            break
        day -= ONE_DAY

    return streak


def longest_streak(done, freeze=False):
    """Find the longest streak ever, starting only from the beginning of each run."""
    if not done:
        return 0

    latest = max(done)
    best = 0

    for start in done:
        # Skip days that continue an earlier day (same trick as Longest Consecutive Seq)
        if start - ONE_DAY in done:
            continue

        day = start
        streak = 0
        frozen_weeks = set()

        while day <= latest:
            if day in done:
                streak += 1
            elif freeze:
                week = day.isocalendar()[:2]
                if week in frozen_weeks:
                    break
                frozen_weeks.add(week)
            else:
                break
            day += ONE_DAY

        best = max(best, streak)

    return best


def completion_rate(done, days, today=None):
    """Completion percentage over the last `days` days (including today)."""
    today = today or date.today()
    completed = 0
    for offset in range(days):
        if today - timedelta(days=offset) in done:
            completed += 1
    return (completed / days) * 100


def current_week_dates(today=None):
    """Return the 7 dates from Monday to Sunday for the week containing today."""
    today = today or date.today()
    monday = today - timedelta(days=today.weekday())
    return [monday + timedelta(days=i) for i in range(7)]


def most_frequent_weekday(done):
    """Return the weekday name (Mon..Sun) this habit is completed most often."""
    if not done:
        return None

    counts = {}
    for day in done:
        wd = day.weekday()
        counts[wd] = counts.get(wd, 0) + 1

    top_day = max(counts, key=lambda wd: counts[wd])
    return WEEKDAYS[top_day]


def habit_stats(name, entry, freeze=False, today=None):
    today = today or date.today()
    done = {d for d in to_date_set(entry["done_dates"]) if d <= today}
    week = current_week_dates(today)
    grid = ["x" if d in done else "-" for d in week]

    week_done = grid.count("x")
    target = entry["target_per_week"]
    rate_30d = completion_rate(done, 30, today)
    done_30d = round(rate_30d * 30 / 100)

    return {
        "name": name,
        "done_today": today in done,
        "streak": current_streak(done, freeze, today),
        "longest": longest_streak(done, freeze),
        "rate_7d": completion_rate(done, 7, today),
        "rate_30d": rate_30d,
        "week_done": week_done,
        "target": target,
        "target_met": week_done >= target,
        "week_grid": grid,
        "best_weekday": most_frequent_weekday(done),
        "missed_30d": 30 - done_30d,
        "total": len(done),
    }


def ranked_stats(data, today=None):
    """Return stats for every habit, sorted by current streak (highest first)."""
    freeze = data["settings"].get("streak_freeze", False)
    rows = [
        habit_stats(name, entry, freeze, today)
        for name, entry in data["habits"].items()
    ]
    return sorted(rows, key=lambda s: (-s["streak"], s["name"].lower()))


def get_insights(data, today=None):
    rows = ranked_stats(data, today)
    if not rows:
        return None

    most_consistent = max(rows, key=lambda s: (s["rate_30d"], s["longest"], s["total"]))
    most_missed = max(rows, key=lambda s: (s["missed_30d"], -s["total"]))

    return {
        "top_weekdays": [(s["name"], s["best_weekday"] or "No data") for s in rows],
        "most_consistent": most_consistent,
        "most_missed": most_missed,
    }


def all_completed_days(data, year, month):
    """Return day numbers in (year, month) when EVERY habit was completed."""
    if not data["habits"]:
        return set()

    per_habit_days = []
    for entry in data["habits"].values():
        days = {
            d.day
            for d in to_date_set(entry["done_dates"])
            if d.year == year and d.month == month
        }
        per_habit_days.append(days)

    return set.intersection(*per_habit_days)
