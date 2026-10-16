"""Small tests for the FitGuide routes using a temporary SQLite database."""

from datetime import date
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import app as fitguide


class FitGuideAppTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_database_path = fitguide.DATABASE_PATH
        fitguide.DATABASE_PATH = Path(self.temp_dir.name) / "test-fitguide.db"
        fitguide.app.config.update(TESTING=True)
        fitguide.init_db()
        self.client = fitguide.app.test_client()

    def tearDown(self):
        fitguide.DATABASE_PATH = self.original_database_path
        self.temp_dir.cleanup()

    def test_homepage_shows_plans_exercises_and_nutrition(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Workout plans", response.data)
        self.assertIn(b"Exercise library", response.data)
        self.assertIn(b"Nutrition tips", response.data)
        self.assertIn(b"Complete your first workout", response.data)

    def test_responsive_stylesheet_is_served(self):
        response = self.client.get("/static/style.css")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"@media (max-width: 600px)", response.data)
        response.close()

    def test_workout_logging_updates_points_streak_and_badge(self):
        response = self.client.post(
            "/log-workout",
            data={
                "activity": "A morning walk",
                "workout_date": date.today().isoformat(),
                "minutes": "25",
                "notes": "Felt good",
            },
        )

        self.assertEqual(response.status_code, 302)
        page = self.client.get("/")
        self.assertIn(b"A morning walk", page.data)
        self.assertIn(b"10</strong>", page.data)
        self.assertIn(b"1 <em>days</em>", page.data)
        self.assertIn(b"First step", page.data)

    def test_future_workout_date_is_rejected(self):
        response = self.client.post(
            "/log-workout",
            data={
                "activity": "Future walk",
                "workout_date": "2999-01-01",
                "minutes": "20",
            },
        )

        self.assertEqual(response.status_code, 302)
        page = self.client.get("/")
        self.assertNotIn(b"Future walk", page.data)
        self.assertIn(b"date no later than today", page.data)

    def test_measurement_requires_weight_or_note_and_is_saved(self):
        rejected = self.client.post(
            "/log-measurement",
            data={"measure_date": date.today().isoformat(), "weight": ""},
        )
        self.assertEqual(rejected.status_code, 302)

        saved = self.client.post(
            "/log-measurement",
            data={
                "measure_date": date.today().isoformat(),
                "weight": "65.5",
                "measurement_notes": "Feeling stronger",
            },
        )
        self.assertEqual(saved.status_code, 302)
        page = self.client.get("/")
        self.assertIn(b"65.5 kg", page.data)
        self.assertIn(b"Feeling stronger", page.data)

    def test_recommendation_uses_goal_level_equipment_and_time(self):
        response = self.client.post(
            "/recommend",
            data={
                "goal": "Cardio fitness",
                "level": "Intermediate",
                "equipment": "Dumbbells",
                "minutes": "30",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"30 minutes", response.data)
        self.assertIn(b"cardio intervals", response.data)
        self.assertIn(b"intermediate exerciser", response.data)
        self.assertIn(b"dumbbells", response.data)

    def test_ai_plan_sends_prompt_to_ollama_and_displays_response(self):
        ollama_response = Mock()
        ollama_response.json.return_value = {"response": "A gentle sample plan"}
        ollama_response.raise_for_status.return_value = None
        with patch.object(fitguide.requests, "post", return_value=ollama_response) as post:
            response = self.client.post(
                "/generate-plan",
                data={
                    "ai_goal": "Build strength",
                    "ai_level": "Beginner",
                    "ai_equipment": "None",
                    "ai_minutes": "30",
                    "ai_days": "3",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"A gentle sample plan", response.data)
        prompt = post.call_args.kwargs["json"]["prompt"]
        self.assertIn("Goal: Build strength", prompt)
        self.assertIn("Days per week: 3", prompt)

    def test_opening_ai_plan_url_redirects_to_dashboard(self):
        with patch.object(fitguide.requests, "post") as post:
            response = self.client.get("/generate-plan")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/#ai-coach")
        post.assert_not_called()

    def test_ai_unavailable_is_shown_to_the_user(self):
        with patch.object(
            fitguide.requests,
            "post",
            side_effect=fitguide.requests.exceptions.ConnectionError,
        ):
            response = self.client.post(
                "/generate-plan",
                data={
                    "ai_goal": "General fitness",
                    "ai_level": "Beginner",
                    "ai_equipment": "None",
                    "ai_minutes": "30",
                    "ai_days": "3",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Cannot connect to Ollama", response.data)

    def test_community_post_is_saved_and_html_is_escaped(self):
        response = self.client.post(
            "/community",
            data={"author": "<b>Riya</b>", "message": "One workout done! <script>"},
        )

        self.assertEqual(response.status_code, 302)
        page = self.client.get("/")
        self.assertIn(b"&lt;b&gt;Riya&lt;/b&gt;", page.data)
        self.assertIn(b"&lt;script&gt;", page.data)
        self.assertNotIn(b"<script>", page.data)


if __name__ == "__main__":
    unittest.main()
