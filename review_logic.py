DEFAULT_GENRE = "General"
DEFAULT_WEIGHT_STYLE = "Fallback"


DEFAULT_REVIEW_OPTION_LADDER = [
    ("Excellent", 10),
    ("Very Strong", 9),
    ("Strong", 8),
    ("Good", 7),
    ("Solid", 6),
    ("Average", 5),
    ("Rough", 4),
    ("Weak", 3),
    ("Poor", 2),
    ("Broken", 1),
]


DEFAULT_REVIEW_CATEGORY_ORDER = [
    "Core Gameplay",
    "Design Quality",
    "Content Variety",
    "Progression and Pacing",
    "Technical Performance",
    "Audio and Presentation",
]


DEFAULT_REVIEW_CATEGORY_WEIGHTS = {
    "Core Gameplay": 2.2,
    "Design Quality": 1.7,
    "Content Variety": 1.4,
    "Progression and Pacing": 1.6,
    "Technical Performance": 1.9,
    "Audio and Presentation": 1.2,
}


def get_default_review_profile():
    """Return the small built-in fallback profile used when AI generation is unavailable."""
    categories = {
        category_name: list(DEFAULT_REVIEW_OPTION_LADDER)
        for category_name in DEFAULT_REVIEW_CATEGORY_ORDER
    }
    category_weights = {
        category_name: float(DEFAULT_REVIEW_CATEGORY_WEIGHTS[category_name])
        for category_name in DEFAULT_REVIEW_CATEGORY_ORDER
    }

    return {
        "genre": DEFAULT_GENRE,
        "description": "Generic fallback review profile used when AI-generated categories are unavailable.",
        "categories": categories,
        "category_weights": category_weights,
        "category_list": list(DEFAULT_REVIEW_CATEGORY_ORDER),
        "weight_style": DEFAULT_WEIGHT_STYLE,
        "weight_style_description": "Built-in fallback weights used when AI review-profile generation is unavailable.",
    }


def build_category_ratings(selected_options, categories, category_weights):
    """Build category rating map and weighted final score from selected option labels."""
    scores = []
    weights = []
    category_ratings = {}

    for category, options in categories.items():
        selected_label = selected_options.get(category, "")
        for text, val in options:
            if text == selected_label:
                scores.append(val)
                weights.append(category_weights.get(category, 1.0))
                category_ratings[category] = (text, val)
                break

    if not weights:
        return category_ratings, 0

    weighted_total = sum(score * weight for score, weight in zip(scores, weights))
    final_score = round(weighted_total / sum(weights))
    return category_ratings, final_score


def format_review_text(
    game_name,
    hours,
    category_list,
    category_ratings,
    final_score,
    github_url="",
    genre_name="",
    weight_style="",
):
    """Return formatted review output shown in the UI and copied to clipboard."""
    star_rating = "★" * final_score + "☆" * (10 - final_score)
    review_text = f"""{game_name}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PLAYTIME: {hours} Hours
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RATING BREAKDOWN:

"""

    for category in category_list:
        if category in category_ratings:
            rating_text, rating_val = category_ratings[category]
            review_text += f"• {category}: {rating_val}/10 - \"{rating_text}\"\n"

    review_text += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{star_rating} {final_score}/10
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    if github_url:
        review_text += f"\nGitHub:\n{github_url}\n"

    return review_text