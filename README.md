# Habit Tracker CLI

Command-line daily habit tracker built with the Python standard library only. Covers Levels 1 through 4 (daily check-offs, past-date logging, streaks, weekly freeze rule, Mon-Sun summary grid, monthly completion calendar, insights, JSON persistence with startup backups, and CSV export).

## Run

```bash
python app.py
```

## Module Layout

| File | Responsibility |
| :--- | :--- |
| `tracker.py` | Tracking logic, validation, streak & freeze algorithms, rates, insights |
| `app.py` | CLI menu registry, input loops, tables, weekly grid, text calendar |
| `storage.py` | JSON load/save, corrupted/empty file handling, startup backups, CSV export |

## Shared Data Format (`habits.json`)

```json
{
  "settings": {
    "streak_freeze": false
  },
  "habits": {
    "Read 20 minutes": {
      "target_per_week": 5,
      "done_dates": ["2026-11-20", "2026-11-21"]
    }
  }
}
```
