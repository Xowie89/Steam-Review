# Steam Review Generator

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)

[![Download](https://img.shields.io/badge/Download-Latest%20Release-blue?style=for-the-badge&logo=github)](https://github.com/Xowie89/Steam-Review/releases/latest)

A Steam-styled desktop app built with **CustomTkinter** that lets you log in with your Steam API credentials, load your game library, select a game, and generate a formatted review based on category ratings.

The app automatically calculates a final score using weighted categories, shows an animated rating bar, and copies the finished review straight to your clipboard.

---

## Features

- Steam-inspired dark UI
- Login using your **Steam API key** and **64-bit Steam ID**
- Automatically fetches your owned Steam games
- Search your library quickly
- Review games category by category with explicit **Previous/Next** step navigation
- Pre-review game summary screen (name, AppID, and playtime)
- Weighted score calculation for more meaningful ratings
- Animated 10-box rating bar
- Automatically copies the completed review to clipboard
- Copy the review again with one click from the result screen
- Save generated reviews as **.txt** or **.md**
- Edit category ratings from the result screen without restarting
- In-app **About** dialog with version, latest release/release notes, and issue links
- Automatic update checker banner with one-click download when updates are available
- Visible in-app version footer on main screens (matches packaged EXE version)
- Saves credentials locally for quick relogin
- Caches your game list for faster loading

---

## Categories Rated

The review system scores games across these categories:

- **Graphics**
- **Gameplay**
- **Audio**
- **Story**
- **Difficulty**
- **Bugs**

Each category has its own weight in the final score:

| Category   | Weight |
|------------|--------|
| Graphics   | 1.5    |
| Gameplay   | 2.0    |
| Audio      | 1.0    |
| Story      | 1.2    |
| Difficulty | 0.8    |
| Bugs       | 1.8    |

This means **Gameplay** and **Bugs** have the biggest impact on the final rating.

---

## Screenshot / Workflow

1. Launch the app
2. Enter your Steam API key and 64-bit Steam ID
3. Fetch your Steam library
4. Search and select a game
5. Confirm game details on the summary screen
6. Rate each category with Previous/Next controls
7. View the generated review
8. The review is automatically copied to your clipboard
9. Optionally use **Copy Again**, **Edit Ratings**, or save it as `.txt` / `.md`

---

## Example Output

```text
Half-Life 2

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PLAYTIME: 24 Hours
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RATING BREAKDOWN:

• Graphics: 8/10 - "Pretty decent"
• Gameplay: 10/10 - "Can't stop playing"
• Audio: 9/10 - "Epic soundtrack"
• Story: 10/10 - "Story so good, I cried for days"
• Difficulty: 7/10 - "Challenging but fair"
• Bugs: 8/10 - "Minor annoyances"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
★★★★★★★★★☆ 9/10
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
