"""Автотести Flask-маршрутів без реальних викликів Gemini API."""
import unittest
from unittest.mock import patch
from app import app


class AppTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_home(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Startup Spark", response.get_data(as_text=True))

    def test_css(self):
        response = self.client.get("/static/style.css")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/css", response.content_type)

    def test_invalid_topic(self):
        response = self.client.post("/generate", json={"topic": "unknown"})
        self.assertEqual(response.status_code, 400)

    def test_missing_body(self):
        response = self.client.post("/generate", data="no-json")
        self.assertEqual(response.status_code, 400)

    @patch("app.generate_idea")
    def test_generation_mock(self, mocked):
        mocked.return_value = {
            "name": "ОсвітаПлюс", "idea": "Сервіс навчання", "slogan": "Вчитися цікаво!"
        }
        response = self.client.post("/generate", json={"topic": "education"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["name"], "ОсвітаПлюс")
        mocked.assert_called_once_with("освіта")

    @patch("app.generate_idea", side_effect=RuntimeError("Не задано GEMINI_API_KEY."))
    def test_missing_api_key(self, _mocked):
        response = self.client.post("/generate", json={"topic": "games"})
        self.assertEqual(response.status_code, 503)


if __name__ == "__main__":
    unittest.main()
