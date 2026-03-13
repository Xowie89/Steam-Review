import customtkinter as ctk
import pyperclip
import requests
import json
import webbrowser
import os
import re
import sys
import tkinter as tk
from tkinter import filedialog
import importlib
import threading
from review_logic import build_category_ratings, format_review_text

try:
    keyring_spec = importlib.util.find_spec("keyring")
    keyring = importlib.import_module("keyring") if keyring_spec else None
except Exception:
    keyring = None

ctk.set_appearance_mode("dark")

STEAM_BG = "#1b2838"
STEAM_PANEL = "#16202d"
STEAM_ACCENT = "#66c0f4"
WINDOW_WIDTH = 600
WINDOW_HEIGHT = 800
LOGIN_WINDOW_HEIGHT = 920
GITHUB_REPO_URL = "https://github.com/Xowie89/Steam-Review"
GITHUB_RELEASES_URL = f"{GITHUB_REPO_URL}/releases/latest"
GITHUB_ISSUES_URL = f"{GITHUB_REPO_URL}/issues"
GITHUB_LATEST_RELEASE_API_URL = "https://api.github.com/repos/Xowie89/Steam-Review/releases/latest"

categories = {
    "Graphics":[
        ("Looks like a movie",10),
        ("This is fire 🔥🔥🔥",9),
        ("Pretty decent",8),
        ("Not bad",7),
        ("It's graphics",6),
        ("Meh graphics",5),
        ("Pixelated nightmares",4),
        ("Looks like a PowerPoint",3),
        ("Don't stare too long",2),
        ("8-bit hell",1)
    ],
    "Gameplay":[
        ("Can't stop playing",10),
        ("This game is lit",9),
        ("Good gameplay",8),
        ("Decent",7),
        ("It's okay",6),
        ("Meh",5),
        ("Painful",4),
        ("Torture",3),
        ("Sleep inducing",2),
        ("Unplayable",1)
    ],
    "Audio":[
        ("Sound so good, deaf people hear it",10),
        ("Epic soundtrack",9),
        ("Nice tunes",8),
        ("Okay sound",7),
        ("It's sound",6),
        ("Meh audio",5),
        ("Ear bleeding",4),
        ("Nails on chalkboard",3),
        ("Painful",2),
        ("Silence is better",1)
    ],
    "Story":[
        ("Story so good, I cried for days",10),
        ("Emotional rollercoaster",9),
        ("Engaging plot",8),
        ("Okay story",7),
        ("Average",6),
        ("Plot holes everywhere",5),
        ("Confusing mess",4),
        ("What story?",3),
        ("No plot",2),
        ("Book of random words",1)
    ],
    "Difficulty":[
        ("Git gud or die",10),
        ("Hard as nails",9),
        ("Brain workout",8),
        ("Challenging but fair",7),
        ("Moderate challenge",6),
        ("Easy peasy",5),
        ("Walk in the park",4),
        ("Baby mode",3),
        ("Press W to win",2),
        ("NPC level",1)
    ],
    "Bugs":[
        ("Bug-free paradise",10),
        ("Almost perfect",9),
        ("Minor annoyances",8),
        ("Some bugs",7),
        ("Buggy but playable",6),
        ("Crash fest",5),
        ("Bug city",4),
        ("Unstable mess",3),
        ("Bug terrarium",2),
        ("Glitch apocalypse",1)
    ]
}

# Category weights for rating calculation (higher = more impact on final score)
category_weights = {
    "Graphics": 1.5,      # Visual quality matters
    "Gameplay": 2.0,      # Core experience is most important
    "Audio": 1.0,         # Nice but not dealbreaking
    "Story": 1.2,         # Important for narrative games
    "Difficulty": 0.8,    # Subjective and doesn't always correlate with rating
    "Bugs": 1.8           # Technical issues heavily impact enjoyment
}

category_list = list(categories.keys())

app = ctk.CTk()
app.title("Steam Review Generator")
app.configure(fg_color=STEAM_BG)
app.resizable(False, False)

main_frame = ctk.CTkFrame(app, fg_color=STEAM_PANEL)
main_frame.pack(fill="both", expand=True, padx=20, pady=20)

title = ctk.CTkLabel(main_frame, text="", font=("Arial", 24, "bold"), text_color=STEAM_ACCENT)

container = ctk.CTkFrame(main_frame, fg_color="transparent")

rating_bar = []
rating_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
for i in range(10):
    box = ctk.CTkLabel(rating_frame, text="", width=20, height=20, fg_color="#444", corner_radius=4)
    box.pack(side="left", padx=2)
    rating_bar.append(box)

preview = None

vars_dict = {}
score_values = {}
current_index = 0
new_review_btn = None
current_game_data = {}  # Store current game info (name, appid, playtime, etc)

# Steam API variables
steam_api_key = ""
steam_id = ""
owned_games = []
selected_game = ""
APP_DATA_DIR = os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "SteamReviewGenerator")
LEGACY_DATA_DIR = os.path.dirname(os.path.abspath(__file__))
KEYRING_SERVICE = "SteamReviewGenerator"
KEYRING_API_KEY_NAME = "steam_api_key"
CREDENTIALS_FILE = os.path.join(APP_DATA_DIR, "steam_credentials.json")
CACHE_FILE = os.path.join(APP_DATA_DIR, "games_cache.json")
current_screen = "login"  # "login" or "games"
steam_username = ""
login_btn = None
login_progress = None
startup_loading_label = None
startup_progress = None
steam_api_key_entry = None
steam_id_entry = None
status_label = None
api_key_hint_label = None
steam_id_hint_label = None
search_results_label = None
no_results_label = None
sort_mode_var = None
game_buttons = []
selected_game_index = -1
next_btn = None
prev_btn = None
step_label = None
nav_hint_label = None
latest_review_text = ""
save_status_label = None
about_dialog = None
app_version_cache = None
update_check_state = "idle"
update_check_message = "Check for updates"
update_latest_version = ""
update_download_url = GITHUB_RELEASES_URL
update_check_in_progress = False
update_auto_check_started = False
update_banner_status_label = None
update_banner_action_btn = None

# ------------------ FUNCTIONS ------------------

def get_app_version():
    """Resolve app version from EXE metadata or version_info.txt."""
    global app_version_cache
    if app_version_cache:
        return app_version_cache

    # In packaged Windows builds, prefer the executable ProductVersion resource.
    if os.name == "nt" and getattr(sys, "frozen", False):
        exe_version = get_windows_product_version(sys.executable)
        if exe_version:
            app_version_cache = exe_version
            return app_version_cache

    version_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "version_info.txt")
    try:
        if os.path.exists(version_file):
            with open(version_file, "r", encoding="utf-8-sig") as f:
                content = f.read()
            match = re.search(r'StringStruct\("ProductVersion",\s*"([^"]+)"\)', content)
            if match:
                app_version_cache = match.group(1)
                return app_version_cache
    except OSError:
        pass

    app_version_cache = "dev"
    return app_version_cache

def get_windows_product_version(file_path):
    """Read ProductVersion from Windows version resources."""
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        size = ctypes.windll.version.GetFileVersionInfoSizeW(file_path, None)
        if not size:
            return None

        raw_data = ctypes.create_string_buffer(size)
        ok = ctypes.windll.version.GetFileVersionInfoW(file_path, 0, size, raw_data)
        if not ok:
            return None

        value_ptr = ctypes.c_void_p()
        value_len = wintypes.UINT(0)
        translations = []

        has_translation = ctypes.windll.version.VerQueryValueW(
            raw_data,
            r"\\VarFileInfo\\Translation",
            ctypes.byref(value_ptr),
            ctypes.byref(value_len)
        )
        if has_translation and value_len.value >= 4:
            raw_translations = ctypes.string_at(value_ptr, value_len.value)
            for idx in range(0, value_len.value, 4):
                lang = int.from_bytes(raw_translations[idx:idx + 2], byteorder="little")
                codepage = int.from_bytes(raw_translations[idx + 2:idx + 4], byteorder="little")
                translations.append(f"{lang:04X}{codepage:04X}")

        if not translations:
            translations = ["040904B0", "040904E4"]

        for translation in translations:
            block = f"\\\\StringFileInfo\\\\{translation}\\\\ProductVersion"
            found_version = ctypes.windll.version.VerQueryValueW(
                raw_data,
                block,
                ctypes.byref(value_ptr),
                ctypes.byref(value_len)
            )
            if found_version and value_len.value:
                version_text = ctypes.wstring_at(value_ptr, value_len.value).rstrip("\x00").strip()
                if version_text:
                    return version_text
    except Exception:
        return None

    return None

def add_version_footer(parent):
    """Show persistent version text at the bottom-right of a screen."""
    version_label = ctk.CTkLabel(
        parent,
        text=f"Version {get_app_version()}",
        font=("Arial", 11),
        text_color="#9fb6c4"
    )
    # Use absolute anchoring so the footer stays visible regardless of pack layout.
    version_label.place(relx=0.985, rely=0.985, anchor="se")
    version_label.lift()

def normalize_version_tuple(version_text):
    """Extract version numbers from tags like v1.2.3."""
    numbers = re.findall(r"\d+", str(version_text))
    return tuple(int(num) for num in numbers)

def set_update_banner_widgets(status_label, action_button):
    """Track active update banner controls for current screen."""
    global update_banner_status_label, update_banner_action_btn
    update_banner_status_label = status_label
    update_banner_action_btn = action_button
    refresh_update_banner_ui()

def open_update_download_page():
    """Open latest release page in browser."""
    webbrowser.open(update_download_url or GITHUB_RELEASES_URL)

def refresh_update_banner_ui():
    """Refresh update banner text and action based on current checker state."""
    if not update_banner_status_label or not update_banner_status_label.winfo_exists():
        return
    if not update_banner_action_btn or not update_banner_action_btn.winfo_exists():
        return

    text_color = "#9fb6c4"
    button_text = "Check Now"
    button_color = "#2f556f"
    button_command = lambda: start_update_check(force=True)
    button_state = "normal"

    if update_check_state == "checking":
        text_color = "#9fb6c4"
        button_text = "Checking..."
        button_color = "#41505d"
        button_command = lambda: None
        button_state = "disabled"
    elif update_check_state == "update_available":
        text_color = "#ffcc66"
        button_text = "Download"
        button_color = STEAM_ACCENT
        button_command = open_update_download_page
    elif update_check_state == "up_to_date":
        text_color = "#66d17a"
        button_text = "Check Again"
        button_color = "#2f556f"
        button_command = lambda: start_update_check(force=True)
    elif update_check_state == "error":
        text_color = "#ff7777"
        button_text = "Retry"
        button_color = "#8b3e3e"
        button_command = lambda: start_update_check(force=True)

    update_banner_status_label.configure(text=update_check_message, text_color=text_color)
    update_banner_action_btn.configure(
        text=button_text,
        command=button_command,
        fg_color=button_color,
        state=button_state
    )

def complete_update_check(state, message, latest_version="", release_url=GITHUB_RELEASES_URL):
    """Apply update check results on UI thread and refresh active banner."""
    global update_check_state, update_check_message, update_latest_version
    global update_download_url, update_check_in_progress

    update_check_state = state
    update_check_message = message
    update_latest_version = latest_version
    update_download_url = release_url
    update_check_in_progress = False
    refresh_update_banner_ui()

def update_check_worker():
    """Background worker that queries latest GitHub release and compares versions."""
    try:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Steam-Review-Generator"
        }
        response = requests.get(GITHUB_LATEST_RELEASE_API_URL, headers=headers, timeout=8)
        response.raise_for_status()

        data = response.json()
        latest_tag = data.get("tag_name") or data.get("name") or "latest"
        release_url = data.get("html_url") or GITHUB_RELEASES_URL
        current_version = get_app_version()

        latest_tuple = normalize_version_tuple(latest_tag)
        current_tuple = normalize_version_tuple(current_version)

        if latest_tuple and current_tuple:
            max_len = max(len(latest_tuple), len(current_tuple))
            latest_cmp = latest_tuple + (0,) * (max_len - len(latest_tuple))
            current_cmp = current_tuple + (0,) * (max_len - len(current_tuple))

            if latest_cmp > current_cmp:
                app.after(
                    0,
                    lambda: complete_update_check(
                        "update_available",
                        f"Update available: {latest_tag}",
                        latest_tag,
                        release_url
                    )
                )
                return

            app.after(
                0,
                lambda: complete_update_check(
                    "up_to_date",
                    f"You're up to date ({current_version})",
                    latest_tag,
                    release_url
                )
            )
            return

        if latest_tuple and not current_tuple:
            app.after(
                0,
                lambda: complete_update_check(
                    "update_available",
                    f"Latest release: {latest_tag}",
                    latest_tag,
                    release_url
                )
            )
            return

        app.after(
            0,
            lambda: complete_update_check(
                "error",
                "Could not parse release version.",
                "",
                release_url
            )
        )
    except requests.exceptions.Timeout:
        app.after(0, lambda: complete_update_check("error", "Update check timed out."))
    except requests.exceptions.HTTPError as err:
        status_code = err.response.status_code if err.response else None
        if status_code in (403, 429):
            message = "GitHub rate limit reached. Try again later."
        elif status_code and status_code >= 500:
            message = "GitHub is unavailable right now."
        else:
            message = f"Update check failed ({status_code})."
        app.after(0, lambda: complete_update_check("error", message))
    except (requests.exceptions.RequestException, ValueError, json.JSONDecodeError):
        app.after(0, lambda: complete_update_check("error", "Could not check updates."))

def start_update_check(force=False):
    """Start update check if idle or forced retry/check-again."""
    global update_check_in_progress, update_check_state, update_check_message
    if update_check_in_progress:
        return

    if not force and update_check_state in {"up_to_date", "update_available"}:
        refresh_update_banner_ui()
        return

    update_check_state = "checking"
    update_check_message = "Checking for updates..."
    update_check_in_progress = True
    refresh_update_banner_ui()
    threading.Thread(target=update_check_worker, daemon=True).start()

def ensure_auto_update_check():
    """Run one automatic update check per app launch."""
    global update_auto_check_started
    if update_auto_check_started:
        return
    update_auto_check_started = True
    start_update_check(force=True)

def create_update_banner(parent, padx=20, pady=(0, 10)):
    """Create update banner with current state and action button."""
    banner_frame = ctk.CTkFrame(parent, fg_color=STEAM_BG, corner_radius=8)
    banner_frame.pack(fill="x", padx=padx, pady=pady)

    banner_inner = ctk.CTkFrame(banner_frame, fg_color="transparent")
    banner_inner.pack(fill="x", padx=12, pady=8)

    status_label = ctk.CTkLabel(
        banner_inner,
        text=update_check_message,
        font=("Arial", 11),
        text_color="#9fb6c4"
    )
    status_label.pack(side="left")

    action_btn = ctk.CTkButton(
        banner_inner,
        text="Check Now",
        width=120,
        height=28,
        fg_color="#2f556f",
        command=lambda: start_update_check(force=True)
    )
    action_btn.pack(side="right")

    set_update_banner_widgets(status_label, action_btn)
    ensure_auto_update_check()
    return banner_frame

def close_about_dialog():
    """Close About dialog and clear shared reference."""
    global about_dialog
    if about_dialog and about_dialog.winfo_exists():
        about_dialog.destroy()
    about_dialog = None

def show_about_dialog():
    """Display release-oriented app info, version, and support links."""
    global about_dialog
    if about_dialog and about_dialog.winfo_exists():
        about_dialog.lift()
        about_dialog.focus_force()
        return

    version_value = get_app_version()
    about_dialog = ctk.CTkToplevel(app)
    about_dialog.title("About Steam Review Generator")
    about_dialog.geometry("440x360")
    about_dialog.resizable(False, False)
    about_dialog.configure(fg_color=STEAM_BG)
    about_dialog.transient(app)
    about_dialog.grab_set()
    about_dialog.protocol("WM_DELETE_WINDOW", close_about_dialog)

    about_frame = ctk.CTkFrame(about_dialog, fg_color=STEAM_PANEL, corner_radius=10)
    about_frame.pack(fill="both", expand=True, padx=18, pady=18)

    title_label = ctk.CTkLabel(
        about_frame,
        text="Steam Review Generator",
        font=("Arial", 22, "bold"),
        text_color=STEAM_ACCENT
    )
    title_label.pack(pady=(18, 8))

    version_label = ctk.CTkLabel(
        about_frame,
        text=f"Version: {version_value}",
        font=("Arial", 13),
        text_color="#d2dbe2"
    )
    version_label.pack(pady=(0, 14))

    info_label = ctk.CTkLabel(
        about_frame,
        text="Installed from GitHub release?\nUse these links for updates and support.",
        font=("Arial", 12),
        text_color="#b7c5d0",
        justify="center"
    )
    info_label.pack(pady=(0, 14))

    check_update_btn = ctk.CTkButton(
        about_frame,
        text="Check for Updates",
        command=lambda: start_update_check(force=True),
        fg_color="#2f556f",
        width=180
    )
    check_update_btn.pack(pady=(0, 12))

    links_frame = ctk.CTkFrame(about_frame, fg_color="transparent")
    links_frame.pack(pady=(0, 14))

    top_links_row = ctk.CTkFrame(links_frame, fg_color="transparent")
    top_links_row.pack(pady=(0, 8))

    bottom_links_row = ctk.CTkFrame(links_frame, fg_color="transparent")
    bottom_links_row.pack()

    release_btn = ctk.CTkButton(
        top_links_row,
        text="Latest Release",
        command=lambda: webbrowser.open(GITHUB_RELEASES_URL),
        fg_color="#2f556f",
        width=140
    )
    release_btn.pack(side="left", padx=6)

    release_notes_btn = ctk.CTkButton(
        top_links_row,
        text="Release Notes",
        command=lambda: webbrowser.open(GITHUB_RELEASES_URL),
        fg_color="#2f556f",
        width=140
    )
    release_notes_btn.pack(side="left", padx=6)

    issues_btn = ctk.CTkButton(
        bottom_links_row,
        text="Report Issue",
        command=lambda: webbrowser.open(GITHUB_ISSUES_URL),
        fg_color="#2f556f",
        width=140
    )
    issues_btn.pack(side="left", padx=6)

    repo_btn = ctk.CTkButton(
        bottom_links_row,
        text="Open GitHub",
        command=lambda: webbrowser.open(GITHUB_REPO_URL),
        fg_color="#2f556f",
        width=140
    )
    repo_btn.pack(side="left", padx=6)

    close_btn = ctk.CTkButton(
        about_frame,
        text="Close",
        command=close_about_dialog,
        fg_color=STEAM_ACCENT,
        width=120
    )
    close_btn.pack(pady=(8, 16))

def save_credentials(api_key, steam_id):
    """Save Steam ID to disk and API key to secure keyring when available."""
    try:
        ensure_app_data_dir()
        credentials = {
            "steam_id": steam_id
        }
        with open(CREDENTIALS_FILE, 'w') as f:
            json.dump(credentials, f)

        if keyring:
            keyring.set_password(KEYRING_SERVICE, KEYRING_API_KEY_NAME, api_key)
    except Exception as e:
        print(f"Failed to save credentials: {e}")

def save_games_cache(games, steam_id):
    """Cache owned games list to disk"""
    try:
        ensure_app_data_dir()
        cache = {
            "steam_id": steam_id,
            "games": games
        }
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f)
    except Exception as e:
        print(f"Failed to save games cache: {e}")

def load_games_cache():
    """Load cached games list if available"""
    try:
        ensure_app_data_dir()
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Failed to load games cache: {e}")
    return None

def load_credentials():
    """Load Steam ID from disk and API key from secure keyring.

    If a legacy plaintext API key is found, migrate it to keyring when possible.
    """
    try:
        ensure_app_data_dir()
        legacy_api_key = ""
        steam_id_value = ""

        if os.path.exists(CREDENTIALS_FILE):
            with open(CREDENTIALS_FILE, 'r') as f:
                credentials = json.load(f)

            # Backward compatibility for older versions that stored api_key in plaintext.
            legacy_api_key = credentials.get("api_key", "")
            steam_id_value = credentials.get("steam_id", "")

            if "api_key" in credentials:
                # Rewrite credentials file without plaintext API key.
                with open(CREDENTIALS_FILE, 'w') as f:
                    json.dump({"steam_id": steam_id_value}, f)

        api_key_value = ""
        if keyring:
            api_key_value = keyring.get_password(KEYRING_SERVICE, KEYRING_API_KEY_NAME) or ""
            if not api_key_value and legacy_api_key:
                keyring.set_password(KEYRING_SERVICE, KEYRING_API_KEY_NAME, legacy_api_key)
                api_key_value = legacy_api_key

        return api_key_value, steam_id_value
    except Exception as e:
        print(f"Failed to load credentials: {e}")
    return "", ""

def logout():
    """Clear saved credentials and return to login screen"""
    global steam_api_key, steam_id, owned_games, current_screen, steam_username
    try:
        if os.path.exists(CREDENTIALS_FILE):
            os.remove(CREDENTIALS_FILE)
    except Exception as e:
        print(f"Failed to remove credentials file: {e}")

    if keyring:
        try:
            keyring.delete_password(KEYRING_SERVICE, KEYRING_API_KEY_NAME)
        except Exception:
            # Ignore missing entry and keyring-specific cleanup errors.
            pass
    
    # Reset variables
    steam_api_key = ""
    steam_id = ""
    owned_games = []
    steam_username = ""
    current_screen = "login"
    
    # Switch to login screen
    show_login_screen()

def ensure_app_data_dir():
    """Create the app data directory when missing."""
    os.makedirs(APP_DATA_DIR, exist_ok=True)

def migrate_legacy_data_files():
    """Move old local JSON files to AppData storage if needed."""
    legacy_credentials = os.path.join(LEGACY_DATA_DIR, "steam_credentials.json")
    legacy_cache = os.path.join(LEGACY_DATA_DIR, "games_cache.json")

    if not os.path.exists(CREDENTIALS_FILE) and os.path.exists(legacy_credentials):
        try:
            os.replace(legacy_credentials, CREDENTIALS_FILE)
        except OSError:
            pass

    if not os.path.exists(CACHE_FILE) and os.path.exists(legacy_cache):
        try:
            os.replace(legacy_cache, CACHE_FILE)
        except OSError:
            pass

def set_login_controls_enabled(enabled):
    """Enable/disable login inputs while background auth is running."""
    state = "normal" if enabled else "disabled"
    if steam_api_key_entry and steam_api_key_entry.winfo_exists():
        steam_api_key_entry.configure(state=state)
    if steam_id_entry and steam_id_entry.winfo_exists():
        steam_id_entry.configure(state=state)
    if login_btn and login_btn.winfo_exists():
        login_btn.configure(state=state)

def set_login_loading(active):
    """Show/hide login progress indicator while network calls run."""
    if not login_progress or not login_progress.winfo_exists():
        return
    if active:
        login_progress.pack(pady=(0, 15))
        login_progress.start()
    else:
        login_progress.stop()
        login_progress.pack_forget()

def update_login_status(message, color="#ffff00"):
    """Safely update login status label text and color."""
    if status_label and status_label.winfo_exists():
        status_label.configure(text=message, text_color=color)

def set_startup_loading_text(message):
    """Safely update startup loading label text."""
    if startup_loading_label and startup_loading_label.winfo_exists():
        startup_loading_label.configure(text=message)

def clear_startup_loading_ui():
    """Stop and remove startup loading widgets before screen transition."""
    global startup_loading_label, startup_progress
    if startup_progress and startup_progress.winfo_exists():
        startup_progress.stop()
        startup_progress.destroy()
    if startup_loading_label and startup_loading_label.winfo_exists():
        startup_loading_label.destroy()
    startup_progress = None
    startup_loading_label = None

def fetch_owned_games(api_key, user_steam_id):
    """Fetch and sort owned games from Steam API."""
    url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
    params = {
        'key': api_key,
        'steamid': user_steam_id,
        'include_appinfo': 1,
        'include_played_free_games': 1,
        'format': 'json'
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()

    data = response.json()
    games = data.get('response', {}).get('games', [])
    if not games:
        raise ValueError("No games found. Make sure your profile is public.")
    return sorted(games, key=lambda x: x.get('name', '').lower())

def fetch_steam_username(api_key, user_steam_id):
    """Fetch Steam persona name; fallback to Unknown on recoverable failures."""
    try:
        summary_url = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/"
        summary_params = {
            'key': api_key,
            'steamids': user_steam_id
        }
        summary_response = requests.get(summary_url, params=summary_params, timeout=10)
        summary_response.raise_for_status()
        summary_data = summary_response.json()
        players = summary_data.get('response', {}).get('players', [])
        if players:
            return players[0].get('personaname', 'Unknown')
    except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return 'Unknown'
    return 'Unknown'

def complete_login_success(api_key, user_steam_id, games, username):
    """Apply successful login results on the UI thread."""
    global steam_api_key, steam_id, owned_games, steam_username
    steam_api_key = api_key
    steam_id = user_steam_id
    owned_games = games
    steam_username = username

    set_login_loading(False)
    save_credentials(api_key, user_steam_id)
    save_games_cache(owned_games, user_steam_id)
    show_games_screen()

def complete_login_error(error_message):
    """Show login failure feedback and re-enable controls."""
    update_login_status(error_message, "#ff5555")
    set_login_loading(False)
    set_login_controls_enabled(True)

def validate_login_inputs(api_key, user_steam_id):
    """Validate login fields and return per-field hints."""
    errors = {
        "api_key": "",
        "steam_id": ""
    }

    if not api_key:
        errors["api_key"] = "Required"
    elif len(api_key) < 24:
        errors["api_key"] = "Looks too short"

    if not user_steam_id:
        errors["steam_id"] = "Required"
    elif not user_steam_id.isdigit():
        errors["steam_id"] = "Steam ID must contain only numbers"
    elif len(user_steam_id) != 17:
        errors["steam_id"] = "Steam ID should be 17 digits"

    return errors

def update_login_validation_ui(api_key, user_steam_id):
    """Update field hints and login button state from current inputs."""
    errors = validate_login_inputs(api_key, user_steam_id)

    if api_key_hint_label and api_key_hint_label.winfo_exists():
        if errors["api_key"]:
            api_key_hint_label.configure(text=errors["api_key"], text_color="#ff7777")
        else:
            api_key_hint_label.configure(text="Looks good", text_color="#66d17a")

    if steam_id_hint_label and steam_id_hint_label.winfo_exists():
        if errors["steam_id"]:
            steam_id_hint_label.configure(text=errors["steam_id"], text_color="#ff7777")
        else:
            steam_id_hint_label.configure(text="Looks good", text_color="#66d17a")

    has_errors = bool(errors["api_key"] or errors["steam_id"])
    if login_btn and login_btn.winfo_exists():
        login_btn.configure(state="disabled" if has_errors else "normal")

def on_login_input_change(event=None):
    """Validate fields on every keypress for instant feedback."""
    if not steam_api_key_entry or not steam_id_entry:
        return
    update_login_validation_ui(steam_api_key_entry.get().strip(), steam_id_entry.get().strip())

def humanize_login_error(error):
    """Map network/API exceptions to user-friendly messages."""
    if isinstance(error, requests.exceptions.Timeout):
        return "Steam API timed out. Check your connection and try again."

    if isinstance(error, requests.exceptions.HTTPError):
        status_code = error.response.status_code if error.response else None
        if status_code == 401:
            return "Invalid Steam API key. Generate a new key and try again."
        if status_code == 403:
            return "Access denied. Verify API key and set profile/game details to public."
        if status_code == 429:
            return "Too many requests. Wait a minute and try again."
        if status_code and status_code >= 500:
            return "Steam services are currently unavailable. Try again shortly."
        return f"Steam API error ({status_code}). Please try again."

    if isinstance(error, requests.exceptions.ConnectionError):
        return "Could not reach Steam API. Check your internet connection."

    return "Login failed due to a network error. Please try again."

def login_worker(api_key, user_steam_id):
    """Background worker for login button flow."""
    try:
        app.after(0, lambda: update_login_status("Connecting to Steam..."))
        games = fetch_owned_games(api_key, user_steam_id)

        app.after(0, lambda: update_login_status("Loading profile details..."))
        username = fetch_steam_username(api_key, user_steam_id)

        app.after(0, lambda: update_login_status("Preparing your library..."))
        app.after(0, lambda: complete_login_success(api_key, user_steam_id, games, username))
    except requests.exceptions.RequestException as e:
        app.after(0, lambda: complete_login_error(humanize_login_error(e)))
    except json.JSONDecodeError:
        app.after(0, lambda: complete_login_error("Invalid response from Steam API"))
    except ValueError as e:
        app.after(0, lambda: complete_login_error(str(e)))

def complete_auto_login_success(api_key, user_steam_id, games, username):
    """Apply successful startup auto-login results."""
    global steam_api_key, steam_id, owned_games, steam_username
    steam_api_key = api_key
    steam_id = user_steam_id
    owned_games = games
    steam_username = username
    clear_startup_loading_ui()
    show_games_screen()

def complete_auto_login_error():
    """Fallback to login screen if startup auto-login fails."""
    clear_startup_loading_ui()
    show_login_screen()

def auto_login_worker(api_key, user_steam_id):
    """Background worker for startup auto-login flow."""
    try:
        app.after(0, lambda: set_startup_loading_text("Checking local cache..."))
        cache = load_games_cache()
        if cache and cache.get('steam_id') == user_steam_id and cache.get('games'):
            games = cache.get('games', [])
        else:
            app.after(0, lambda: set_startup_loading_text("Fetching your Steam games..."))
            games = fetch_owned_games(api_key, user_steam_id)
            save_games_cache(games, user_steam_id)

        app.after(0, lambda: set_startup_loading_text("Loading your Steam profile..."))
        username = fetch_steam_username(api_key, user_steam_id)

        app.after(0, lambda: set_startup_loading_text("Finalizing startup..."))
        app.after(0, lambda: complete_auto_login_success(api_key, user_steam_id, games, username))
    except (requests.exceptions.RequestException, json.JSONDecodeError, ValueError):
        app.after(0, complete_auto_login_error)

def show_login_screen():
    """Show the login screen"""
    global current_screen
    current_screen = "login"
    app.geometry(f"{WINDOW_WIDTH}x{LOGIN_WINDOW_HEIGHT}")
    
    # Clear current content
    for widget in main_frame.winfo_children():
        widget.destroy()
    
    # Login screen
    login_frame = ctk.CTkFrame(main_frame, fg_color=STEAM_PANEL)
    login_frame.pack(fill="both", expand=True, padx=20, pady=20)

    top_actions_frame = ctk.CTkFrame(login_frame, fg_color="transparent")
    top_actions_frame.pack(fill="x", padx=10, pady=(8, 0))
    about_btn = ctk.CTkButton(
        top_actions_frame,
        text="About",
        command=show_about_dialog,
        fg_color="#2f556f",
        width=80,
        height=30
    )
    about_btn.pack(side="right")
    
    login_title = ctk.CTkLabel(login_frame, text="Steam Review Generator", font=("Arial", 28, "bold"), text_color=STEAM_ACCENT)
    login_title.pack(pady=(30, 10))
    
    subtitle = ctk.CTkLabel(login_frame, text="Login with your Steam credentials", font=("Arial", 16), text_color="#cccccc")
    subtitle.pack(pady=(0, 30))

    create_update_banner(login_frame, padx=20, pady=(0, 16))

    # Instructions (move higher and give more vertical space for readability)
    instructions_frame = ctk.CTkFrame(login_frame, fg_color=STEAM_BG)
    instructions_frame.pack(fill="x", padx=20, pady=(0, 14))

    instructions_title = ctk.CTkLabel(instructions_frame, text="How to get your credentials:", font=("Arial", 14, "bold"), text_color=STEAM_ACCENT)
    instructions_title.pack(pady=(15, 10))

    instructions_text = tk.Text(instructions_frame, height=10, width=50, bg=STEAM_BG, fg="#cccccc", font=("Arial", 11), wrap="word", borderwidth=0, highlightthickness=0)
    instructions_text.pack(pady=(0, 15))

    # Insert text with clickable links
    instructions_text.insert("1.0", "1. Visit ")
    instructions_text.insert("end", "https://steamcommunity.com/dev/apikey", "link1")
    instructions_text.insert("end", "\n2. Sign in with your Steam account\n3. Create an API key for this application\n\n4. Visit ")
    instructions_text.insert("end", "https://steamid.io/", "link2")
    instructions_text.insert("end", "\n5. Enter your Steam profile URL or username\n6. Copy the 64-bit Steam ID")

    # Configure link tags
    instructions_text.tag_configure("link1", foreground="#66c0f4", underline=True)
    instructions_text.tag_configure("link2", foreground="#66c0f4", underline=True)

    # Bind clicks to open URLs
    instructions_text.tag_bind("link1", "<Button-1>", lambda e: webbrowser.open("https://steamcommunity.com/dev/apikey"))
    instructions_text.tag_bind("link2", "<Button-1>", lambda e: webbrowser.open("https://steamid.io/"))

    # Make text read-only
    instructions_text.config(state="disabled")
    
    # API Key input
    api_key_label = ctk.CTkLabel(login_frame, text="Steam API Key:", font=("Arial", 14))
    api_key_label.pack(pady=(12, 5))
    global steam_api_key_entry
    steam_api_key_entry = ctk.CTkEntry(login_frame, width=400, placeholder_text="Enter your Steam API key...")
    steam_api_key_entry.pack(pady=(0, 10))
    steam_api_key_entry.bind("<KeyRelease>", on_login_input_change)

    global api_key_hint_label
    api_key_hint_label = ctk.CTkLabel(login_frame, text="", font=("Arial", 11), text_color="#888")
    api_key_hint_label.pack(pady=(0, 8))
    
    # Steam ID input
    steam_id_label = ctk.CTkLabel(login_frame, text="Steam ID (64-bit):", font=("Arial", 14))
    steam_id_label.pack(pady=(8, 5))
    global steam_id_entry
    steam_id_entry = ctk.CTkEntry(login_frame, width=400, placeholder_text="Enter your 64-bit Steam ID...")
    steam_id_entry.pack(pady=(0, 20))
    steam_id_entry.bind("<KeyRelease>", on_login_input_change)

    global steam_id_hint_label
    steam_id_hint_label = ctk.CTkLabel(login_frame, text="", font=("Arial", 11), text_color="#888")
    steam_id_hint_label.pack(pady=(0, 12))
    
    # Login button
    global login_btn
    login_btn = ctk.CTkButton(login_frame, text="Login & Fetch Games", command=login_and_fetch, fg_color=STEAM_ACCENT, height=40)
    login_btn.pack(pady=(10, 12))
    
    # Status label
    global status_label
    status_label = ctk.CTkLabel(login_frame, text="", font=("Arial", 12))
    status_label.pack(pady=(0, 8))

    # Login progress indicator (shown only during background fetch)
    global login_progress
    login_progress = ctk.CTkProgressBar(login_frame, width=300, mode="indeterminate")
    
    # Load saved credentials
    saved_api_key, saved_steam_id = load_credentials()
    if saved_api_key:
        steam_api_key_entry.insert(0, saved_api_key)
    if saved_steam_id:
        steam_id_entry.insert(0, saved_steam_id)

    on_login_input_change()
    add_version_footer(login_frame)

def show_games_screen():
    """Show the games selection screen"""
    global current_screen, preview, rating_frame, sort_mode_var, selected_game_index
    current_screen = "games"
    app.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
    selected_game_index = -1
    
    # Destroy preview textbox if it exists
    if preview:
        preview.destroy()
        preview = None
    
    # Also remove/hide rating bar if it exists (shouldn't appear on games screen)
    try:
        if rating_frame:
            rating_frame.pack_forget()
            rating_frame.destroy()
            rating_frame = None
            # redraw immediately
            app.update()
    except NameError:
        pass
    
    # Clear current content
    for widget in main_frame.winfo_children():
        widget.destroy()
    # ensure UI refresh before rebuilding
    app.update()    
    # Games screen
    games_frame = ctk.CTkFrame(main_frame, fg_color=STEAM_PANEL)
    games_frame.pack(fill="both", expand=True, padx=20, pady=20)
    
    # Title at top
    games_title = ctk.CTkLabel(games_frame, text="Select a Game to Review", font=("Arial", 24, "bold"), text_color=STEAM_ACCENT)
    games_title.pack(pady=(0, 15), anchor="w", padx=20)
    
    # Header with username and logout
    header_frame = ctk.CTkFrame(games_frame, fg_color="transparent")
    header_frame.pack(fill="x", pady=(0, 15), padx=20)
    
    username_label = ctk.CTkLabel(header_frame, text=f"Logged in as: {steam_username}", font=("Arial", 12), text_color="#cccccc")
    username_label.pack(side="left")
    
    logout_btn = ctk.CTkButton(header_frame, text="Logout", command=logout, fg_color="#ff5555", width=80, height=30)
    logout_btn.pack(side="right")

    about_btn = ctk.CTkButton(header_frame, text="About", command=show_about_dialog, fg_color="#2f556f", width=80, height=30)
    about_btn.pack(side="right", padx=(0, 8))

    create_update_banner(games_frame, padx=20, pady=(0, 12))
    
    # Search and sort controls
    controls_frame = ctk.CTkFrame(games_frame, fg_color="transparent")
    controls_frame.pack(fill="x", pady=(0, 10), padx=20)

    global search_entry
    search_entry = ctk.CTkEntry(controls_frame, width=360, placeholder_text="Type to search games...")
    search_entry.pack(side="left")
    search_entry.bind("<KeyRelease>", filter_games)
    search_entry.bind("<Down>", on_search_down)
    search_entry.bind("<Up>", on_search_up)
    search_entry.bind("<Return>", on_search_enter)

    sort_mode_var = ctk.StringVar(value="A-Z")
    sort_menu = ctk.CTkOptionMenu(
        controls_frame,
        variable=sort_mode_var,
        values=["A-Z", "Most Played", "Least Played"],
        command=on_sort_change,
        width=170,
        fg_color="#2a475e",
        button_color="#1f3a4d",
        button_hover_color="#2f556f"
    )
    sort_menu.pack(side="right")

    global search_results_label
    search_results_label = ctk.CTkLabel(games_frame, text="", font=("Arial", 11), text_color="#9fb6c4")
    search_results_label.pack(pady=(0, 8), padx=20, anchor="w")
    
    # Stats/Info frame
    stats_frame = ctk.CTkFrame(games_frame, fg_color=STEAM_BG, corner_radius=8)
    stats_frame.pack(fill="x", pady=(0, 20), padx=20)
    
    stats_inner = ctk.CTkFrame(stats_frame, fg_color="transparent")
    stats_inner.pack(fill="x", padx=15, pady=12)
    
    # Library stats
    total_games = len(owned_games)
    stats_text = ctk.CTkLabel(
        stats_inner, 
        text=f"📚 Library: {total_games} games",
        font=("Arial", 12),
        text_color="#66c0f4"
    )
    stats_text.pack(anchor="w")
    
    # Scrollable game list
    global game_scroll_frame
    game_scroll_frame = ctk.CTkScrollableFrame(games_frame, width=560, height=380)
    game_scroll_frame.pack(pady=(0, 20), padx=20, fill="both", expand=True)

    global no_results_label
    no_results_label = ctk.CTkLabel(games_frame, text="No matching games found.", font=("Arial", 12), text_color="#ff9f7a")
    
    # Game buttons will be added here
    # Populate games
    populate_game_list()
    add_version_footer(games_frame)

def get_sorted_games(sort_mode):
    """Return owned games sorted by the selected mode."""
    if sort_mode == "Most Played":
        return sorted(owned_games, key=lambda g: g.get('playtime_forever', 0), reverse=True)
    if sort_mode == "Least Played":
        return sorted(owned_games, key=lambda g: g.get('playtime_forever', 0))
    return sorted(owned_games, key=lambda g: g.get('name', '').lower())

def update_selected_game_highlight():
    """Highlight currently selected visible game for keyboard navigation."""
    for idx, (button, _) in enumerate(game_buttons):
        if idx == selected_game_index:
            button.configure(fg_color="#264c66", text_color="#f2f8fc")
        else:
            button.configure(fg_color=STEAM_PANEL, text_color="#cccccc")

def on_sort_change(choice):
    """Refresh game list after changing sort mode."""
    search_text = search_entry.get() if search_entry and search_entry.winfo_exists() else ""
    populate_game_list(search_text)

def move_game_selection(step):
    """Move keyboard selection up/down within visible games."""
    global selected_game_index
    if not game_buttons:
        selected_game_index = -1
        return

    if selected_game_index < 0:
        selected_game_index = 0 if step >= 0 else len(game_buttons) - 1
    else:
        selected_game_index = max(0, min(len(game_buttons) - 1, selected_game_index + step))

    update_selected_game_highlight()

    # Keep selection in view in a lightweight way for large lists.
    if len(game_buttons) > 1:
        scroll_fraction = selected_game_index / max(len(game_buttons) - 1, 1)
        game_scroll_frame._parent_canvas.yview_moveto(scroll_fraction)

def on_search_down(event):
    """Select next visible game with Down key."""
    move_game_selection(1)
    return "break"

def on_search_up(event):
    """Select previous visible game with Up key."""
    move_game_selection(-1)
    return "break"

def on_search_enter(event):
    """Open selected game with Enter from search box."""
    if not game_buttons:
        return "break"

    index = selected_game_index if selected_game_index >= 0 else 0
    _, game_name = game_buttons[index]
    start_review(game_name)
    return "break"

def populate_game_list(search_filter=""):
    """Populate the game list, showing/hiding based on search"""
    global game_buttons, selected_game_index

    for widget in game_scroll_frame.winfo_children():
        widget.destroy()
    game_buttons = []

    sort_mode = sort_mode_var.get() if sort_mode_var else "A-Z"
    sorted_games = get_sorted_games(sort_mode)

    # Reset scroll position to top when filtering
    if search_filter:
        game_scroll_frame._parent_canvas.yview_moveto(0)
    
    # Build buttons for current filter/sort result
    search_lower = search_filter.lower()

    for game in sorted_games:
        game_name = game.get('name', '')
        if search_filter and search_lower not in game_name.lower():
            continue

        game_btn = ctk.CTkButton(
            game_scroll_frame,
            text=game_name,
            command=lambda name=game_name: start_review(name),
            fg_color=STEAM_PANEL,
            text_color="#cccccc",
            hover_color="#66c0f4",
            anchor="w",
            height=35
        )
        game_btn.pack(fill="x", padx=5, pady=2)
        game_buttons.append((game_btn, game_name))

    shown_count = len(game_buttons)
    total_count = len(sorted_games)

    selected_game_index = 0 if shown_count > 0 else -1
    update_selected_game_highlight()

    if search_results_label and search_results_label.winfo_exists():
        if search_filter:
            search_results_label.configure(text=f"Showing {shown_count} of {total_count} games")
        else:
            search_results_label.configure(text=f"Showing all {total_count} games")

    if no_results_label and no_results_label.winfo_exists():
        if shown_count == 0:
            no_results_label.pack(pady=(0, 14), padx=20, anchor="w")
        else:
            no_results_label.pack_forget()

def filter_games(event=None):
    """Filter games based on search input"""
    if event and event.keysym in {"Up", "Down", "Return"}:
        return
    search_text = search_entry.get()
    populate_game_list(search_text)

def login_and_fetch():
    """Handle login and game fetching"""
    
    api_key = steam_api_key_entry.get().strip()
    user_steam_id = steam_id_entry.get().strip()
    
    validation_errors = validate_login_inputs(api_key, user_steam_id)
    if validation_errors["api_key"] or validation_errors["steam_id"]:
        update_login_validation_ui(api_key, user_steam_id)
        status_label.configure(text="Please fix the highlighted fields", text_color="#ff5555")
        return
    
    status_label.configure(text="Logging in and fetching games...", text_color="#ffff00")
    set_login_controls_enabled(False)
    set_login_loading(True)
    threading.Thread(target=login_worker, args=(api_key, user_steam_id), daemon=True).start()

def start_review(game_name):
    """Start the review process for selected game"""
    global selected_game, preview, current_game_data, current_index, vars_dict
    selected_game = game_name
    current_index = 0
    vars_dict = {}
    
    # Destroy existing preview if it exists
    if preview:
        preview.destroy()
    
    # Clear current screen and show review interface
    for widget in main_frame.winfo_children():
        widget.destroy()
    
    # Get game AppID from owned_games
    game_appid = None
    game_playtime = 0
    for game in owned_games:
        if game['name'] == game_name:
            game_appid = game.get('appid')
            game_playtime = game.get('playtime_forever', 0)
            break
    
    current_game_data = {
        'name': game_name,
        'appid': game_appid,
        'playtime': game_playtime
    }
    
    # Create main review frame
    global title, container, rating_frame
    
    # Header with game info
    header_frame = ctk.CTkFrame(main_frame, fg_color=STEAM_PANEL)
    header_frame.pack(fill="x", padx=20, pady=15)
    
    # Game title and back button
    top_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
    top_frame.pack(fill="x", padx=15, pady=(10, 5))
    
    back_btn = ctk.CTkButton(top_frame, text="← Back", command=show_games_screen, width=80, height=30, fg_color="#666", hover_color="#888")
    back_btn.pack(side="left")

    about_btn = ctk.CTkButton(top_frame, text="About", command=show_about_dialog, width=80, height=30, fg_color="#2f556f")
    about_btn.pack(side="right")
    
    title = ctk.CTkLabel(top_frame, text=f"Reviewing: {game_name}", font=("Arial", 18, "bold"), text_color=STEAM_ACCENT)
    title.pack(side="left", padx=20)
    
    # Game stats
    hours = game_playtime // 60
    stats_text = f"⏱️ {hours}h playtime"
    stats_label = ctk.CTkLabel(header_frame, text=stats_text, font=("Arial", 11), text_color="#888")
    stats_label.pack(anchor="w", padx=15, pady=(0, 10))

    create_update_banner(main_frame, padx=20, pady=(0, 8))
    
    # Review container
    container = ctk.CTkFrame(main_frame, fg_color="transparent")
    container.pack(fill="both", expand=True, padx=20, pady=(0, 20))
    
    # Rating bar (visual indicator)
    rating_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    rating_frame.pack(pady=10)
    
    # Initialize rating bar
    global rating_bar
    rating_bar = []
    for i in range(10):
        box = ctk.CTkLabel(rating_frame, text="", width=20, height=20, fg_color="#444", corner_radius=4)
        box.pack(side="left", padx=2)
        rating_bar.append(box)
    
    # Show a quick game summary before starting ratings
    show_game_summary()
    add_version_footer(main_frame)

def show_game_summary():
    """Show selected game metadata before starting category ratings."""
    for widget in container.winfo_children():
        widget.destroy()

    game_name = current_game_data.get('name', 'Unknown Game')
    game_appid = current_game_data.get('appid', 'Unknown')
    playtime_minutes = current_game_data.get('playtime', 0)
    playtime_hours = playtime_minutes // 60

    summary_frame = ctk.CTkFrame(container, fg_color=STEAM_PANEL, corner_radius=8)
    summary_frame.pack(fill="both", expand=True, pady=10)

    summary_title = ctk.CTkLabel(
        summary_frame,
        text="Ready to review this game?",
        font=("Arial", 18, "bold"),
        text_color=STEAM_ACCENT
    )
    summary_title.pack(pady=(22, 18), padx=20, anchor="w")

    details_text = (
        f"Game: {game_name}\n"
        f"AppID: {game_appid}\n"
        f"Playtime: {playtime_hours}h ({playtime_minutes} minutes)\n\n"
        "You will rate 6 categories. You can move forward and backward\n"
        "before generating the final review."
    )
    details_label = ctk.CTkLabel(
        summary_frame,
        text=details_text,
        font=("Arial", 12),
        justify="left",
        text_color="#d2dbe2"
    )
    details_label.pack(pady=(0, 26), padx=22, anchor="w")

    actions_frame = ctk.CTkFrame(summary_frame, fg_color="transparent")
    actions_frame.pack(fill="x", padx=20, pady=(0, 20))

    back_btn = ctk.CTkButton(
        actions_frame,
        text="Choose Another Game",
        command=show_games_screen,
        fg_color="#555",
        hover_color="#666",
        width=170
    )
    back_btn.pack(side="left")

    begin_btn = ctk.CTkButton(
        actions_frame,
        text="Start Rating",
        command=show_category,
        fg_color=STEAM_ACCENT,
        width=140
    )
    begin_btn.pack(side="right")

def animate_rating_bar(score):
    """Fill the rating bar one by one with animation"""
    for i, box in enumerate(rating_bar):
        box.configure(fg_color="#444")  # Reset all boxes

    def fill_box(index):
        if index >= score:
            return
        # Set color based on score
        if score >= 7:
            color = "#00ff00"  # Green for positive
        elif score <= 4:
            color = "#ff5555"  # Red for negative
        else:
            color = "#ffcc00"  # Yellow for average
        rating_bar[index].configure(fg_color=color)
        # Call next box after 100ms
        app.after(50, lambda: fill_box(index + 1))

    fill_box(0)

def slide_frame(new_frame):
    new_frame.place(x=750, y=0, relwidth=1, relheight=1)
    def animate(pos):
        if pos <= 0:
            new_frame.place(x=0, y=0)
            return
        new_frame.place(x=pos, y=0)
        app.after(10, lambda: animate(pos-30))
    animate(750)

def show_category():
    global current_index, new_review_btn, next_btn, prev_btn, step_label, nav_hint_label
    for widget in container.winfo_children():
        widget.destroy()
    if new_review_btn:
        new_review_btn.destroy()
        new_review_btn = None

    if current_index >= len(category_list):
        generate_review()
        return

    category = category_list[current_index]
    options = categories[category]
    
    # Update title
    current = current_index + 1
    total = len(category_list)
    title.configure(text=f"{category} ({current}/{total})")

    # Progress and guidance
    progress_percent = int((current / total) * 100)
    step_label = ctk.CTkLabel(
        container,
        text=f"Step {current} of {total} ({progress_percent}%)",
        font=("Arial", 12, "bold"),
        text_color="#9fb6c4"
    )
    step_label.pack(anchor="w", padx=8, pady=(0, 8))

    # Create category frame with scrollable options
    frame = ctk.CTkFrame(container, fg_color=STEAM_PANEL, corner_radius=8)
    frame.pack(fill="both", expand=True, pady=10)
    
    # Category description
    desc_label = ctk.CTkLabel(frame, text=f"Rate the {category.lower()} of this game", font=("Arial", 12), text_color="#aaa")
    desc_label.pack(pady=(15, 10), padx=20, anchor="w")
    
    # Options frame
    options_frame = ctk.CTkScrollableFrame(frame)
    options_frame.pack(fill="both", expand=True, padx=20, pady=(0, 15))
    
    if category in vars_dict:
        var = vars_dict[category]
    else:
        var = ctk.StringVar(value="")
        vars_dict[category] = var

    for text, val in options:
        score_values[text] = val
        
        # Create a frame for each option to style it better
        option_container = ctk.CTkFrame(options_frame, fg_color="transparent")
        option_container.pack(fill="x", pady=4)
        
        btn = ctk.CTkRadioButton(
            option_container,
            text=f"{text} ({val}/10)",
            variable=var,
            value=text,
            command=update_nav_state,
            font=("Arial", 11),
            text_color="#ccc"
        )
        btn.pack(anchor="w")

    # Navigation controls
    nav_frame = ctk.CTkFrame(container, fg_color="transparent")
    nav_frame.pack(fill="x", pady=(8, 0))

    prev_btn = ctk.CTkButton(
        nav_frame,
        text="Previous",
        command=go_previous_category,
        fg_color="#555",
        hover_color="#666",
        width=110
    )
    prev_btn.pack(side="left")

    next_label = "Generate Review" if current_index == len(category_list) - 1 else "Next"
    next_btn = ctk.CTkButton(
        nav_frame,
        text=next_label,
        command=go_next_category,
        fg_color=STEAM_ACCENT,
        width=130
    )
    next_btn.pack(side="right")

    nav_hint_label = ctk.CTkLabel(nav_frame, text="", font=("Arial", 11), text_color="#ff9999")
    nav_hint_label.pack(side="right", padx=(0, 12))

    update_nav_state()

def update_nav_state():
    """Enable/disable navigation controls based on current step and selection."""
    category = category_list[current_index]
    selected_value = vars_dict.get(category).get() if category in vars_dict else ""

    if prev_btn and prev_btn.winfo_exists():
        prev_btn.configure(state="normal" if current_index > 0 else "disabled")

    if next_btn and next_btn.winfo_exists():
        next_btn.configure(state="normal" if selected_value else "disabled")

    if nav_hint_label and nav_hint_label.winfo_exists():
        if selected_value:
            nav_hint_label.configure(text="")
        else:
            nav_hint_label.configure(text="Select a rating to continue")

def go_next_category():
    """Move to the next category or generate final review on last step."""
    global current_index

    category = category_list[current_index]
    selected_value = vars_dict.get(category).get() if category in vars_dict else ""
    if not selected_value:
        if nav_hint_label and nav_hint_label.winfo_exists():
            nav_hint_label.configure(text="Select a rating to continue")
        return

    current_index += 1
    show_category()

def go_previous_category():
    """Move back one category while keeping already selected ratings."""
    global current_index
    if current_index <= 0:
        return
    current_index -= 1
    show_category()

def save_review_to_file(file_ext):
    """Save the latest generated review text to a user-selected file."""
    if save_status_label and save_status_label.winfo_exists():
        save_status_label.configure(text="", text_color="#9fb6c4")

    if not latest_review_text:
        return

    game_name = current_game_data.get('name', 'steam_review').strip()
    safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in game_name).strip()
    safe_name = safe_name.replace(' ', '_') or "steam_review"
    default_filename = f"{safe_name}_review{file_ext}"

    file_path = filedialog.asksaveasfilename(
        title="Save Review",
        defaultextension=file_ext,
        initialfile=default_filename,
        filetypes=[("Text Files", "*.txt"), ("Markdown Files", "*.md"), ("All Files", "*.*")]
    )

    if not file_path:
        return

    try:
        with open(file_path, "w", encoding="utf-8") as output_file:
            output_file.write(latest_review_text)
        if save_status_label and save_status_label.winfo_exists():
            save_status_label.configure(text=f"Saved: {os.path.basename(file_path)}", text_color="#66d17a")
    except OSError:
        if save_status_label and save_status_label.winfo_exists():
            save_status_label.configure(text="Could not save file. Please try another location.", text_color="#ff7777")

def copy_review_again():
    """Copy the latest review to clipboard from the result screen."""
    if not latest_review_text:
        return

    try:
        pyperclip.copy(latest_review_text)
        if save_status_label and save_status_label.winfo_exists():
            save_status_label.configure(text="Copied to clipboard.", text_color="#66d17a")
    except Exception:
        if save_status_label and save_status_label.winfo_exists():
            save_status_label.configure(text="Could not access clipboard.", text_color="#ff7777")

def edit_ratings_from_result():
    """Return to rating flow with previous selections preserved."""
    global current_index, preview, save_status_label
    current_index = 0

    if preview and preview.winfo_exists():
        preview.destroy()
    preview = None
    save_status_label = None

    for box in rating_bar:
        box.configure(fg_color="#444")

    show_category()

def generate_review():
    global new_review_btn, latest_review_text, preview, save_status_label

    selected_options = {
        category: vars_dict[category].get()
        for category in category_list
    }
    category_ratings, final_score = build_category_ratings(
        selected_options,
        categories,
        category_weights
    )

    hours = current_game_data.get('playtime', 0) // 60
    game_name = current_game_data.get('name', 'Unknown Game')
    review_text = format_review_text(game_name, hours, category_list, category_ratings, final_score)
    latest_review_text = review_text
    
    # Update the UI to show completion
    title.configure(text=f"Review Complete: {final_score}/10")
    
    # Animate the rating bar
    animate_rating_bar(final_score)
    
    # Clear container and show preview
    for widget in container.winfo_children():
        widget.destroy()
    
    # Create review preview frame
    preview_frame = ctk.CTkFrame(container, fg_color=STEAM_PANEL, corner_radius=8)
    preview_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    preview = ctk.CTkTextbox(preview_frame, height=350, width=500)
    preview.pack(fill="both", expand=True, padx=15, pady=15)
    preview.insert("0.0", review_text)
    preview.configure(state="disabled")  # Make read-only
    
    # Copy to clipboard
    pyperclip.copy(review_text)
    
    # Create footer frame with separate rows so action buttons are never clipped.
    buttons_frame = ctk.CTkFrame(preview_frame, fg_color="transparent")
    buttons_frame.pack(fill="x", padx=15, pady=(0, 15))

    status_row = ctk.CTkFrame(buttons_frame, fg_color="transparent")
    status_row.pack(fill="x", pady=(0, 8))

    copy_label = ctk.CTkLabel(status_row, text="✓ Review copied to clipboard!", font=("Arial", 10), text_color="#00ff00")
    copy_label.pack(side="left", padx=10)

    save_status_label = ctk.CTkLabel(status_row, text="", font=("Arial", 10), text_color="#9fb6c4")
    save_status_label.pack(side="left", padx=(8, 0))

    primary_actions_row = ctk.CTkFrame(buttons_frame, fg_color="transparent")
    primary_actions_row.pack(fill="x", pady=(0, 8))

    # Add "New Review" button
    new_review_btn = ctk.CTkButton(
        primary_actions_row,
        text="Start New Review",
        command=start_new_review,
        fg_color=STEAM_ACCENT,
        width=140
    )
    new_review_btn.pack(side="left")

    edit_ratings_btn = ctk.CTkButton(
        primary_actions_row,
        text="Edit Ratings",
        command=edit_ratings_from_result,
        fg_color="#4f6a2a",
        hover_color="#5f7c32",
        width=120
    )
    edit_ratings_btn.pack(side="left", padx=(8, 0))

    copy_again_btn = ctk.CTkButton(
        primary_actions_row,
        text="Copy Again",
        command=copy_review_again,
        fg_color="#2f556f",
        width=110
    )
    copy_again_btn.pack(side="left", padx=(8, 0))

    secondary_actions_row = ctk.CTkFrame(buttons_frame, fg_color="transparent")
    secondary_actions_row.pack(fill="x")

    save_txt_btn = ctk.CTkButton(
        secondary_actions_row,
        text="Save .txt",
        command=lambda: save_review_to_file(".txt"),
        fg_color="#2f556f",
        width=95
    )
    save_txt_btn.pack(side="left")

    save_md_btn = ctk.CTkButton(
        secondary_actions_row,
        text="Save .md",
        command=lambda: save_review_to_file(".md"),
        fg_color="#2f556f",
        width=95
    )
    save_md_btn.pack(side="left", padx=(8, 0))

def start_new_review():
    global current_index, vars_dict, selected_game, preview, current_game_data, rating_frame, latest_review_text, save_status_label
    current_index = 0
    vars_dict = {}
    selected_game = ""
    current_game_data = {}
    latest_review_text = ""
    save_status_label = None
    
    if preview:
        preview.destroy()
        preview = None
    
    # clear rating bar widgets if present
    for box in rating_bar:
        box.configure(fg_color="#444")
    try:
        if rating_frame:
            rating_frame.destroy()
            rating_frame = None
    except NameError:
        pass
    
    # Go back to games screen
    show_games_screen()
    
# ------------------ START ------------------
# Check if user is already logged in
ensure_app_data_dir()
migrate_legacy_data_files()
saved_api_key, saved_steam_id = load_credentials()
if saved_api_key and saved_steam_id:
    # Show loading screen briefly
    startup_loading_label = ctk.CTkLabel(main_frame, text="Loading your games...", font=("Arial", 16), text_color=STEAM_ACCENT)
    startup_loading_label.pack(expand=True)
    startup_progress = ctk.CTkProgressBar(main_frame, width=280, mode="indeterminate")
    startup_progress.pack(pady=(0, 40))
    startup_progress.start()
    app.update()
    threading.Thread(target=auto_login_worker, args=(saved_api_key, saved_steam_id), daemon=True).start()
else:
    # Show login screen
    show_login_screen()

# Set initial window size based on the active startup screen.
if current_screen == "login":
    app.geometry(f"{WINDOW_WIDTH}x{LOGIN_WINDOW_HEIGHT}")
else:
    app.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")

app.mainloop()