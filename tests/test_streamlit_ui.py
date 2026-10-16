"""Streamlit UI smoke and interaction tests with an isolated SQLite file."""

from contextlib import redirect_stderr, redirect_stdout
import io
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

from streamlit.testing.v1 import AppTest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class StreamlitDashboardTests(unittest.TestCase):
    def test_dashboard_renders_and_forms_save_to_sqlite(self):
        original_database = os.environ.get("FITGUIDE_DB")
        with tempfile.TemporaryDirectory() as folder:
            database_path = Path(folder) / "streamlit-test.db"
            os.environ["FITGUIDE_DB"] = str(database_path)
            try:
                with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
                    dashboard = AppTest.from_file(
                        str(PROJECT_ROOT / "app.py"), default_timeout=30
                    ).run()
                self.assertFalse(
                    dashboard.exception,
                    [str(exception.value) for exception in dashboard.exception],
                )
                button_labels = [button.label for button in dashboard.button]
                self.assertIn("📝 Log Beginner workout", button_labels)
                self.assertIn("✨ Generate plan with Gemma", button_labels)
                self.assertIn("✅ Save workout +10 points", button_labels)
                self.assertIn("📨 Post update", button_labels)

                activity = next(
                    widget for widget in dashboard.text_input if widget.label == "Activity"
                )
                activity.set_value("Streamlit test walk")
                save_workout = next(
                    button
                    for button in dashboard.button
                    if button.label == "✅ Save workout +10 points"
                )
                with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
                    dashboard = save_workout.click().run()
                self.assertFalse(dashboard.exception)

                author = next(
                    widget for widget in dashboard.text_input if widget.label == "Your name"
                )
                author.set_value("Test Friend")
                message = dashboard.text_area[0]
                message.set_value("One step at a time!")
                post_button = next(
                    button for button in dashboard.button if button.label == "📨 Post update"
                )
                with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
                    dashboard = post_button.click().run()
                self.assertFalse(dashboard.exception)

                connection = sqlite3.connect(database_path)
                try:
                    workouts = connection.execute(
                        "SELECT activity, minutes FROM workouts"
                    ).fetchall()
                    posts = connection.execute(
                        "SELECT author, message FROM posts"
                    ).fetchall()
                finally:
                    connection.close()
                self.assertEqual(workouts, [("Streamlit test walk", 20)])
                self.assertEqual(posts, [("Test Friend", "One step at a time!")])
            finally:
                if original_database is None:
                    os.environ.pop("FITGUIDE_DB", None)
                else:
                    os.environ["FITGUIDE_DB"] = original_database


if __name__ == "__main__":
    unittest.main()
