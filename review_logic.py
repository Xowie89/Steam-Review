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


def format_review_text(game_name, hours, category_list, category_ratings, final_score):
    """Return the formatted review output shown in the UI and copied to clipboard."""
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

    return review_text
