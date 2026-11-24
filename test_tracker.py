"""Unit tests covering Levels 1 through 4 (standard library unittest only)."""

import csv
import os
import tempfile
import unittest
from datetime import date

from storage import backup_data, empty_data, export_csv, load_data, save_data
from tracker import (
    add_habit,
    all_completed_days,
    completion_rate,
    current_streak,
    get_insights,
    longest_streak,
    mark_done,
    parse_iso_date,
    ranked_stats,
    remove_habit,
    rename_habit,
)

TODAY = date(2026, 11, 24)  # Tuesday


class TestHabitTracker(unittest.TestCase):
    def setUp(self):
        self.data = empty_data()

    def test_add_rename_remove_and_reject_invalid(self):
        self.assertTrue(add_habit(self.data, "Read 20 minutes", 5)[0])
        self.assertFalse(add_habit(self.data, "   ")[0])
        self.assertFalse(add_habit(self.data, "read 20 minutes")[0])
        self.assertFalse(add_habit(self.data, "Water", 0)[0])
        self.assertFalse(add_habit(self.data, "Water", 8)[0])

        self.assertTrue(add_habit(self.data, "Drink water", 7)[0])
        self.assertFalse(rename_habit(self.data, "Drink water", "read 20 minutes")[0])
        self.assertFalse(rename_habit(self.data, "Drink water", "")[0])
        self.assertTrue(rename_habit(self.data, "Drink water", "Hydrate", 6)[0])
        self.assertEqual(self.data["habits"]["Hydrate"]["target_per_week"], 6)

        self.assertTrue(remove_habit(self.data, "Hydrate")[0])
        self.assertNotIn("Hydrate", self.data["habits"])

    def test_mark_done_and_past_date_validation(self):
        add_habit(self.data, "Exercise")
        self.assertTrue(mark_done(self.data, "Exercise", TODAY, TODAY)[0])
        self.assertFalse(mark_done(self.data, "Exercise", TODAY, TODAY)[0])

        past = parse_iso_date("2026-11-20", TODAY)
        self.assertTrue(mark_done(self.data, "Exercise", past, TODAY)[0])
        self.assertFalse(mark_done(self.data, "Exercise", past, TODAY)[0])

        with self.assertRaises(ValueError):
            parse_iso_date("2026-11-25", TODAY)
        with self.assertRaises(ValueError):
            parse_iso_date("2026-2-5", TODAY)
        with self.assertRaises(ValueError):
            parse_iso_date("2026-02-30", TODAY)

    def test_current_streak_today_vs_yesterday(self):
        done_today = {date(2026, 11, 22), date(2026, 11, 23), date(2026, 11, 24)}
        done_yesterday = {date(2026, 11, 22), date(2026, 11, 23)}
        broken = {date(2026, 11, 21), date(2026, 11, 22)}

        self.assertEqual(current_streak(done_today, False, TODAY), 3)
        self.assertEqual(current_streak(done_yesterday, False, TODAY), 2)
        self.assertEqual(current_streak(broken, False, TODAY), 0)

    def test_streak_freeze_weekly_rule(self):
        # Missed Sun 22 (1 miss in W47), done Mon 23 & Tue 24 (W48)
        done = {
            date(2026, 11, 20),
            date(2026, 11, 21),
            date(2026, 11, 23),
            date(2026, 11, 24),
        }
        self.assertEqual(current_streak(done, freeze=False, today=TODAY), 2)
        self.assertEqual(current_streak(done, freeze=True, today=TODAY), 4)

        # Two misses in the same week (Tue 17 & Thu 19 in W47) must break
        same_week = {
            date(2026, 11, 16),  # Mon
            date(2026, 11, 18),  # Wed (missed Tue)
            date(2026, 11, 20),  # Fri (missed Thu)
            date(2026, 11, 21),  # Sat
        }
        self.assertEqual(longest_streak(same_week, freeze=False), 2)
        self.assertEqual(longest_streak(same_week, freeze=True), 3)

        # Cross-week 2-day gap: Sun W47 (22) and Mon W48 (23) -> 1 miss each week
        cross_week = {date(2026, 11, 20), date(2026, 11, 21), date(2026, 11, 24)}
        self.assertEqual(longest_streak(cross_week, freeze=True), 3)
        self.assertEqual(current_streak(cross_week, freeze=True, today=TODAY), 3)

    def test_rates_weekly_grid_ranking_insights_and_calendar(self):
        add_habit(self.data, "Read", 2)
        add_habit(self.data, "Run", 5)
        mark_done(self.data, "Read", date(2026, 11, 23), TODAY)
        mark_done(self.data, "Read", date(2026, 11, 24), TODAY)
        mark_done(self.data, "Run", date(2026, 11, 24), TODAY)

        rows = ranked_stats(self.data, TODAY)
        self.assertEqual([r["name"] for r in rows], ["Read", "Run"])
        self.assertTrue(rows[0]["target_met"])
        self.assertFalse(rows[1]["target_met"])
        self.assertEqual(rows[0]["week_grid"], ["x", "x", "-", "-", "-", "-", "-"])
        self.assertAlmostEqual(completion_rate({TODAY}, 7, TODAY), 100 / 7)

        info = get_insights(self.data, TODAY)
        self.assertEqual(info["most_consistent"]["name"], "Read")
        self.assertEqual(info["most_missed"]["name"], "Run")

        self.assertEqual(all_completed_days(self.data, 2026, 11), {24})
        self.assertEqual(all_completed_days(empty_data(), 2026, 11), set())

    def test_storage_resilience_backup_and_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_file = os.path.join(tmp, "habits.json")
            backup_dir = os.path.join(tmp, "backups")
            csv_file = os.path.join(tmp, "report.csv")

            loaded, msg = load_data(data_file)
            self.assertEqual(loaded["habits"], {})
            self.assertIn("No data file", msg)

            with open(data_file, "w", encoding="utf-8") as fh:
                fh.write("   ")
            loaded, msg = load_data(data_file)
            self.assertIn("empty", msg.lower())

            with open(data_file, "w", encoding="utf-8") as fh:
                fh.write("{bad json")
            loaded, msg = load_data(data_file)
            self.assertIn("corrupted", msg.lower())

            add_habit(self.data, "Read", 5)
            mark_done(self.data, "Read", TODAY, TODAY)
            self.data["settings"]["streak_freeze"] = True
            save_data(self.data, data_file)

            bak = backup_data(data_file, backup_dir)
            self.assertIsNotNone(bak)
            self.assertTrue(os.path.exists(bak))

            reloaded, _ = load_data(data_file)
            self.assertTrue(reloaded["settings"]["streak_freeze"])
            self.assertEqual(reloaded["habits"]["Read"]["done_dates"], ["2026-11-24"])

            export_csv(ranked_stats(reloaded, TODAY), csv_file)
            with open(csv_file, encoding="utf-8") as fh:
                csv_rows = list(csv.DictReader(fh))
            self.assertEqual(len(csv_rows), 1)
            self.assertEqual(csv_rows[0]["Habit"], "Read")
            self.assertEqual(csv_rows[0]["Done Today"], "Yes")


if __name__ == "__main__":
    unittest.main()
