import unittest
from datetime import date

import app


class TaskOccurrenceTests(unittest.TestCase):
    def test_weekly_recurrence_expands_within_month(self):
        task = {
            'id': 1,
            'title': 'Team standup',
            'due_date': '2026-09-02',
            'recurrence_type': 'weekly',
            'recurrence_interval': 1,
            'span_days': 1,
        }

        occurrences = app.expand_task_occurrences(task, date(2026, 9, 1), date(2026, 9, 30))
        self.assertEqual(
            [item['date'] for item in occurrences],
            [
                date(2026, 9, 2), date(2026, 9, 9), date(2026, 9, 16), date(2026, 9, 23), date(2026, 9, 30)
            ],
        )

    def test_monthly_recurrence_uses_same_day_of_month(self):
        task = {
            'id': 2,
            'title': 'Payroll',
            'due_date': '2026-09-15',
            'recurrence_type': 'monthly',
            'recurrence_interval': 1,
            'span_days': 1,
        }

        occurrences = app.expand_task_occurrences(task, date(2026, 9, 1), date(2026, 11, 30))
        self.assertIn(date(2026, 10, 15), [item['date'] for item in occurrences])
        self.assertIn(date(2026, 11, 15), [item['date'] for item in occurrences])

    def test_span_days_creates_range(self):
        task = {
            'id': 3,
            'title': 'Install update',
            'due_date': '2026-09-10',
            'recurrence_type': '',
            'recurrence_interval': 1,
            'span_days': 3,
        }

        occurrences = app.expand_task_occurrences(task, date(2026, 9, 1), date(2026, 9, 30))
        self.assertEqual([item['date'] for item in occurrences], [
            date(2026, 9, 10), date(2026, 9, 11), date(2026, 9, 12)
        ])


if __name__ == '__main__':
    unittest.main()
