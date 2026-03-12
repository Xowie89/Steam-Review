import unittest

from review_logic import build_category_ratings, format_review_text


class ReviewLogicTests(unittest.TestCase):
    def test_weighted_score_uses_category_weights(self):
        categories = {
            "Graphics": [("Great", 8), ("Bad", 2)],
            "Gameplay": [("Fun", 10), ("Dull", 3)],
        }
        weights = {
            "Graphics": 1.0,
            "Gameplay": 2.0,
        }
        selected = {
            "Graphics": "Great",
            "Gameplay": "Dull",
        }

        ratings, score = build_category_ratings(selected, categories, weights)

        self.assertEqual(ratings["Graphics"], ("Great", 8))
        self.assertEqual(ratings["Gameplay"], ("Dull", 3))
        self.assertEqual(score, 5)

    def test_missing_selections_return_zero_score(self):
        categories = {
            "Graphics": [("Great", 8)],
        }
        weights = {
            "Graphics": 1.0,
        }
        selected = {
            "Graphics": "",
        }

        ratings, score = build_category_ratings(selected, categories, weights)

        self.assertEqual(ratings, {})
        self.assertEqual(score, 0)

    def test_review_text_contains_expected_sections(self):
        category_list = ["Graphics", "Gameplay"]
        ratings = {
            "Graphics": ("Great", 8),
            "Gameplay": ("Fun", 10),
        }

        text = format_review_text("Half-Life 2", 24, category_list, ratings, 9)

        self.assertIn("Half-Life 2", text)
        self.assertIn("PLAYTIME: 24 Hours", text)
        self.assertIn("• Graphics: 8/10 - \"Great\"", text)
        self.assertIn("• Gameplay: 10/10 - \"Fun\"", text)
        self.assertIn("9/10", text)


if __name__ == "__main__":
    unittest.main()
