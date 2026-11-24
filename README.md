# Habit Tracker CLI

Command-line daily habit tracker built with the Python standard library only. Covers Levels 1 through 4 (daily check-offs, past-date logging, streaks, weekly freeze rule, Mon-Sun summary grid, monthly completion calendar, insights, JSON persistence with startup backups, and CSV export).

## Run

```bash
python app.py
```

## Run Tests

```bash
python -m unittest -v
```

## Module Layout (Group of 3 Split)

| File | Responsibility |
| :--- | :--- |
| `tracker.py` | Member A — tracking logic, validation, streak & freeze algorithms, rates, insights |
| `app.py` | Member B — CLI menu registry, input loops, tables, weekly grid, text calendar |
| `storage.py` | Member C — JSON load/save, corrupted/empty file handling, startup backups, CSV export |
| `test_tracker.py` | Standard library `unittest` suite verifying all four levels |

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
