import customtkinter as ctk
import pyperclip
import requests
import json
import html
import io
import webbrowser
import os
import re
import sys
import tkinter as tk
from tkinter import filedialog
import importlib
import threading
import time
from review_logic import (
    DEFAULT_GENRE,
    DEFAULT_WEIGHT_STYLE,
    build_category_ratings,
    format_review_text,
    get_default_review_profile,
)

try:
    keyring_spec = importlib.util.find_spec("keyring")
    keyring = importlib.import_module("keyring") if keyring_spec else None
except Exception:
    keyring = None

try:
    pil_image_spec = importlib.util.find_spec("PIL.Image")
    Image = importlib.import_module("PIL.Image") if pil_image_spec else None
except Exception:
    Image = None

ctk.set_appearance_mode("dark")

STEAM_BG = "#1b2838"
STEAM_PANEL = "#16202d"
STEAM_ACCENT = "#66c0f4"
WINDOW_WIDTH = 760
WINDOW_HEIGHT = 860
LOGIN_WINDOW_HEIGHT = 940
WINDOW_MIN_WIDTH = 520
WINDOW_MIN_HEIGHT = 560
WINDOW_SCREEN_PADDING_X = 80
WINDOW_SCREEN_PADDING_Y = 100
ABOUT_WINDOW_WIDTH = 460
ABOUT_WINDOW_HEIGHT = 380
ABOUT_WINDOW_MIN_WIDTH = 360
ABOUT_WINDOW_MIN_HEIGHT = 300
GAME_ROW_HEIGHT = 39
GITHUB_REPO_URL = "https://github.com/Xowie89/Steam-Review"
GITHUB_RELEASES_URL = f"{GITHUB_REPO_URL}/releases/latest"
GITHUB_ISSUES_URL = f"{GITHUB_REPO_URL}/issues"
GITHUB_LATEST_RELEASE_API_URL = "https://api.github.com/repos/Xowie89/Steam-Review/releases/latest"
OLLAMA_DOWNLOAD_WINDOWS_URL = "https://ollama.com/download/windows"
OLLAMA_LIBRARY_URL = "https://ollama.com/library"
STEAM_STORE_APP_DETAILS_URL = "https://store.steampowered.com/api/appdetails"
STEAM_STORE_TIMEOUT_SECONDS = 8
SUMMARY_IMAGE_WIDTH = 440
CATEGORY_OPTION_ROW_DEFAULT = "#2b2f34"
CATEGORY_OPTION_ROW_HOVER = "#38424c"
CATEGORY_OPTION_ROW_SELECTED = "#3a6684"
NETWORK_RETRY_ATTEMPTS = 3
NETWORK_RETRY_INITIAL_DELAY_SECONDS = 0.5
NETWORK_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
NETWORK_RETRYABLE_SERVER_STATUS_CODES = {500, 502, 503, 504}


def request_with_retry(
    method,
    url,
    retry_status_codes=None,
    retry_attempts=NETWORK_RETRY_ATTEMPTS,
    retry_initial_delay=NETWORK_RETRY_INITIAL_DELAY_SECONDS,
    **request_kwargs,
):
    """Perform an HTTP request with short backoff for transient failures."""
    status_codes = set(
        retry_status_codes
        if retry_status_codes is not None
        else NETWORK_RETRYABLE_STATUS_CODES
    )
    attempts = max(1, int(retry_attempts))
    base_delay = max(0.0, float(retry_initial_delay))
    last_error = None

    for attempt_index in range(attempts):
        is_last_attempt = attempt_index >= attempts - 1
        try:
            response = requests.request(method, url, **request_kwargs)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as error:
            last_error = error
            if is_last_attempt:
                raise
            if base_delay > 0:
                time.sleep(base_delay * (2 ** attempt_index))
            continue

        if response.status_code in status_codes and not is_last_attempt:
            if base_delay > 0:
                time.sleep(base_delay * (2 ** attempt_index))
            continue

        return response

    if last_error:
        raise last_error
    raise requests.exceptions.RequestException("Request failed without a response.")


def read_env_flag(name, default=False):
    """Read a boolean environment flag with tolerant truthy parsing."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return bool(default)
    return str(raw_value).strip().lower() in {"1", "true", "yes", "on"}


def read_env_float(name, default):
    """Read a float environment value with safe fallback."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return float(default)
    try:
        return float(raw_value)
    except (TypeError, ValueError):
        return float(default)


LOCAL_AI_ASSIST_ENABLED = read_env_flag("STEAM_REVIEW_AI_ASSIST", True)
LOCAL_AI_OLLAMA_URL = os.getenv("STEAM_REVIEW_OLLAMA_URL", "http://127.0.0.1:11434/api/generate").strip()
LOCAL_AI_MODEL = os.getenv("STEAM_REVIEW_OLLAMA_MODEL", "qwen2.5:7b-instruct").strip()
LOCAL_AI_DETECTION_MODEL = os.getenv("STEAM_REVIEW_AI_DETECTION_MODEL", LOCAL_AI_MODEL).strip()
LOCAL_AI_TIMEOUT_SECONDS = max(5.0, read_env_float("STEAM_REVIEW_AI_TIMEOUT_SECONDS", 45.0))
LOCAL_AI_MAX_DESCRIPTION_CHARS = 1200
LOCAL_AI_STATUS_CACHE_SECONDS = 45.0
LOCAL_AI_STATUS_TIMEOUT_SECONDS = max(2.0, min(LOCAL_AI_TIMEOUT_SECONDS, 5.0))
AI_REVIEW_CATEGORY_COUNT = 6
AI_REVIEW_OPTION_COUNT = 10
AI_REVIEW_FALLBACK_OPTIONS = [
    "Genre-defining quality",
    "Excellent execution",
    "Very strong overall",
    "Good with minor issues",
    "Solid but uneven",
    "Average quality",
    "Noticeably rough",
    "Frequently frustrating",
    "Major design problems",
    "Fundamentally broken",
]

AI_REVIEW_FALLBACK_CATEGORY_NAMES = [
    "Core Gameplay",
    "Design Quality",
    "Content Variety",
    "Progression and Pacing",
    "Technical Performance",
    "Audio and Presentation",
]

AI_REVIEW_QUALITY_OPTION_TEMPLATES = [
    "Outstanding",
    "Excellent",
    "Very strong",
    "Good with minor issues",
    "Solid but uneven",
    "Average",
    "Noticeably rough",
    "Frequently frustrating",
    "Major problems",
    "Fundamentally broken",
]

AI_REVIEW_QUALITY_CUES = (
    "outstanding",
    "excellent",
    "very strong",
    "strong",
    "good",
    "solid",
    "average",
    "rough",
    "frustrating",
    "weak",
    "poor",
    "bad",
    "broken",
    "terrible",
    "awful",
    "unplayable",
)

AI_REVIEW_FEATURE_AVAILABILITY_CUES = (
    "single player only",
    "multiplayer only",
    "co op only",
    "co-op only",
    "no co op",
    "no co-op",
    "no multiplayer",
    "no online",
    "no pvp",
    "lacks",
)

AI_REVIEW_CATEGORY_AXIS_CUES = (
    "gameplay",
    "mechanic",
    "mechanics",
    "core loop",
    "loop",
    "progression",
    "pacing",
    "balance",
    "difficulty",
    "controls",
    "control",
    "interface",
    "ui",
    "ux",
    "feedback",
    "performance",
    "stability",
    "optimization",
    "audio",
    "sound",
    "music",
    "visual",
    "graphics",
    "presentation",
    "content",
    "variety",
    "replayability",
    "polish",
    "accessibility",
    "clarity",
    "systems",
    "economy",
    "customization",
    "challenge",
    "exploration",
    "story",
    "narrative",
    "writing",
    "flow",
    "responsiveness",
)

AI_REVIEW_OPTION_EVALUATIVE_CUES = (
    "rewarding",
    "satisfying",
    "engaging",
    "responsive",
    "smooth",
    "consistent",
    "clear",
    "balanced",
    "fair",
    "polished",
    "stable",
    "refined",
    "clunky",
    "sluggish",
    "unresponsive",
    "unbalanced",
    "unfair",
    "rough",
    "buggy",
    "repetitive",
    "tedious",
    "shallow",
    "deep",
    "confusing",
    "frustrating",
    "immersive",
    "cohesive",
    "impactful",
)

AI_REVIEW_OPTION_FREQUENCY_CUES = (
    "rare",
    "occasional",
    "sometimes",
    "frequent",
    "frequently",
    "constant",
    "often",
    "seldom",
)

AI_REVIEW_OPTION_TOPIC_STOPWORDS = {
    "and",
    "or",
    "the",
    "a",
    "an",
    "to",
    "of",
    "in",
    "for",
    "with",
    "on",
    "from",
    "this",
    "that",
    "game",
    "overall",
    "quality",
    "issues",
    "problem",
    "problems",
    "good",
    "excellent",
    "outstanding",
    "strong",
    "solid",
    "average",
    "rough",
    "broken",
    "very",
    "major",
    "minor",
}

AI_REVIEW_GENRE_THEME_RULES = [
    {
        "theme": "puzzle",
        "category_cues": ("puzzle", "riddle", "logic"),
        "context_cues": ("puzzle", "logic", "brain teaser"),
    },
    {
        "theme": "racing",
        "category_cues": ("racing", "driving", "track", "car handling", "vehicle"),
        "context_cues": ("racing", "driving", "car", "vehicle", "motorsport"),
    },
    {
        "theme": "sports",
        "category_cues": ("sports", "team play", "matchday", "league", "season mode"),
        "context_cues": ("sports", "football", "soccer", "basketball", "baseball", "hockey"),
    },
    {
        "theme": "horror",
        "category_cues": ("horror", "terror", "scare", "fear"),
        "context_cues": ("horror", "terror", "scary", "survival horror"),
    },
    {
        "theme": "platformer",
        "category_cues": ("platforming", "jump timing", "jumping"),
        "context_cues": ("platformer", "platforming", "jump"),
    },
]

active_profile = get_default_review_profile()
active_genre = active_profile["genre"]
active_weight_style = active_profile.get("weight_style", DEFAULT_WEIGHT_STYLE)
active_categories = active_profile["categories"]
active_category_weights = active_profile["category_weights"]
active_category_list = active_profile["category_list"]
active_genre_description = active_profile.get("description", "")
active_weight_style_description = active_profile.get("weight_style_description", "")

app = ctk.CTk()
app.title("Steam Review Generator")
app.configure(fg_color=STEAM_BG)
app.resizable(True, True)

main_frame = ctk.CTkFrame(app, fg_color=STEAM_PANEL)
main_frame.pack(fill="both", expand=True, padx=12, pady=12)

title = ctk.CTkLabel(main_frame, text="", font=("Arial", 24, "bold"), text_color=STEAM_ACCENT)

container = ctk.CTkFrame(main_frame, fg_color="transparent")

preview = None

vars_dict = {}
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
UI_STATE_FILE = os.path.join(APP_DATA_DIR, "ui_state.json")
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
game_virtual_canvas = None
game_virtual_data = []
game_hover_index = -1
_game_canvas_redraw_after = None
selected_game_index = -1
next_btn = None
prev_btn = None
step_label = None
nav_hint_label = None
category_option_rows = {}
category_option_buttons = {}
category_score_shortcuts = {}
category_shortcuts_bound = False
latest_review_text = ""
save_status_label = None
ai_status_summary_label = None
ai_status_refresh_btn = None
ai_status_setup_btn = None
ai_status_copy_pull_btn = None
ai_service_status_cache = {
    "state": "disabled" if not LOCAL_AI_ASSIST_ENABLED else "unknown",
    "message": (
        "Disabled (set STEAM_REVIEW_AI_ASSIST=1 to enable local AI assist)."
        if not LOCAL_AI_ASSIST_ENABLED
        else "Checking local Ollama availability..."
    ),
    "checked_at": 0.0,
    "missing_models": [],
}
ai_service_status_check_in_progress = False
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
about_action_button = None
about_update_toast_label = None
about_update_toast_after_id = None
window_state_cache = None
window_state_loaded = False
main_window_geometry_initialized = False
current_review_step = ""
review_session_token = 0

# ------------------ FUNCTIONS ------------------

def set_active_fallback_review_profile():
    """Load the built-in fallback review profile used when AI generation is unavailable."""
    global active_genre, active_categories, active_category_weights
    global active_category_list, active_genre_description
    global active_weight_style, active_weight_style_description

    profile = get_default_review_profile()
    active_genre = profile["genre"]
    active_categories = profile["categories"]
    active_category_weights = profile["category_weights"]
    active_category_list = profile["category_list"]
    active_genre_description = profile.get("description", "")
    active_weight_style = profile.get("weight_style", DEFAULT_WEIGHT_STYLE)
    active_weight_style_description = profile.get("weight_style_description", "")


def start_detected_rating_flow(lock_selection=True):
    """Start category ratings using the AI profile when available, else the fallback profile."""
    global current_index, vars_dict
    del lock_selection

    if not current_game_data:
        return False

    if current_game_data.get("review_profile_loading", False):
        current_game_data["genre_detection_status"] = (
            "Generating AI review profile from Steam tags. "
            "Please wait..."
        )
        if current_review_step == "summary":
            show_game_summary()
        return False

    ai_review_profile = current_game_data.get("ai_review_profile", {})
    if isinstance(ai_review_profile, dict) and ai_review_profile.get("category_list"):
        set_active_ai_review_profile(ai_review_profile)
    else:
        set_active_fallback_review_profile()

    current_index = 0
    vars_dict = {}
    show_category()
    return True


def retry_ai_review_profile_generation():
    """Retry AI review profile generation for the current game from the summary screen."""
    if not current_game_data:
        return False

    if current_game_data.get("review_profile_loading", False):
        return False

    game_appid = current_game_data.get("appid")
    if not game_appid:
        current_game_data["genre_detection_status"] = "Genre auto-detect unavailable."
        current_game_data["genre_detection_error"] = "Retry unavailable because this game has no Steam AppID."
        if current_review_step == "summary":
            show_game_summary()
        return False

    retry_count = int(current_game_data.get("review_profile_retry_count", 0) or 0) + 1
    current_game_data["review_profile_retry_count"] = retry_count
    current_game_data["genre_detection_status"] = (
        f"Retrying AI review profile generation (attempt {retry_count + 1})..."
    )
    current_game_data["review_profile_loading_started_at"] = time.time()
    current_game_data["genre_detection_error"] = ""
    current_game_data["review_profile_loading"] = True
    current_game_data["review_profile_ready"] = False
    current_game_data["ai_review_profile"] = {}

    # Keep a valid profile active while retrying so scoring is still available if needed.
    set_active_fallback_review_profile()

    if current_review_step == "summary":
        show_game_summary()

    session_token = review_session_token
    threading.Thread(
        target=detect_game_genre_worker,
        args=(game_appid, current_game_data.get("name", ""), session_token),
        daemon=True,
    ).start()
    return True

def parse_geometry(geometry_text):
    """Parse a Tk geometry string into numeric parts."""
    match = re.match(r"^(\d+)x(\d+)\+(-?\d+)\+(-?\d+)$", str(geometry_text or ""))
    if not match:
        return None
    return tuple(int(value) for value in match.groups())

def clamp_window_position(widget, width, height, x_pos, y_pos):
    """Keep a window fully visible on the current primary display."""
    max_x = max(widget.winfo_screenwidth() - width, 0)
    max_y = max(widget.winfo_screenheight() - height, 0)
    clamped_x = max(0, min(x_pos, max_x))
    clamped_y = max(0, min(y_pos, max_y))
    return clamped_x, clamped_y

def load_window_state():
    """Load persisted main-window geometry from disk once per launch."""
    global window_state_loaded, window_state_cache
    if window_state_loaded:
        return window_state_cache

    window_state_loaded = True
    try:
        if os.path.exists(UI_STATE_FILE):
            with open(UI_STATE_FILE, "r", encoding="utf-8") as state_file:
                state = json.load(state_file)

            width = int(state.get("width", 0))
            height = int(state.get("height", 0))
            x_pos = int(state.get("x", 0))
            y_pos = int(state.get("y", 0))

            if width > 0 and height > 0:
                window_state_cache = {
                    "width": width,
                    "height": height,
                    "x": x_pos,
                    "y": y_pos
                }
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        window_state_cache = None

    return window_state_cache

def save_window_state():
    """Persist current main-window geometry for next launch."""
    global window_state_cache, window_state_loaded

    geometry = parse_geometry(app.geometry())
    if not geometry:
        return

    width, height, x_pos, y_pos = geometry
    try:
        ensure_app_data_dir()
        state = {
            "width": width,
            "height": height,
            "x": x_pos,
            "y": y_pos
        }
        with open(UI_STATE_FILE, "w", encoding="utf-8") as state_file:
            json.dump(state, state_file)

        window_state_cache = state
        window_state_loaded = True
    except OSError:
        pass

def on_app_close():
    """Persist UI state and close the app."""
    save_window_state()
    app.destroy()

def get_screen_constrained_size(preferred_width, preferred_height, min_width, min_height, padding_x=WINDOW_SCREEN_PADDING_X, padding_y=WINDOW_SCREEN_PADDING_Y):
    """Clamp preferred window size to available screen space."""
    screen_width = app.winfo_screenwidth()
    screen_height = app.winfo_screenheight()
    max_width = max(320, screen_width - padding_x)
    max_height = max(320, screen_height - padding_y)

    width = min(max(preferred_width, min_width), max_width)
    height = min(max(preferred_height, min_height), max_height)
    return int(width), int(height)

def center_window(widget, width, height):
    """Center a toplevel widget on the active screen."""
    screen_width = widget.winfo_screenwidth()
    screen_height = widget.winfo_screenheight()
    x_pos = max((screen_width - width) // 2, 0)
    y_pos = max((screen_height - height) // 2, 0)
    widget.geometry(f"{width}x{height}+{x_pos}+{y_pos}")

def apply_main_window_size(preferred_width, preferred_height):
    """Apply responsive sizing while restoring saved geometry when available."""
    global main_window_geometry_initialized

    app.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

    if not main_window_geometry_initialized:
        saved_state = load_window_state()
        if saved_state:
            width, height = get_screen_constrained_size(
                saved_state.get("width", preferred_width),
                saved_state.get("height", preferred_height),
                WINDOW_MIN_WIDTH,
                WINDOW_MIN_HEIGHT
            )
            x_pos, y_pos = clamp_window_position(
                app,
                width,
                height,
                saved_state.get("x", 0),
                saved_state.get("y", 0)
            )
            app.geometry(f"{width}x{height}+{x_pos}+{y_pos}")
        else:
            width, height = get_screen_constrained_size(
                preferred_width,
                preferred_height,
                WINDOW_MIN_WIDTH,
                WINDOW_MIN_HEIGHT
            )
            center_window(app, width, height)

        main_window_geometry_initialized = True
        return

    current_geometry = parse_geometry(app.geometry())
    if not current_geometry:
        return

    current_width, current_height, current_x, current_y = current_geometry
    width, height = get_screen_constrained_size(
        current_width,
        current_height,
        WINDOW_MIN_WIDTH,
        WINDOW_MIN_HEIGHT
    )
    x_pos, y_pos = clamp_window_position(app, width, height, current_x, current_y)
    app.geometry(f"{width}x{height}+{x_pos}+{y_pos}")

def apply_dialog_size(dialog, preferred_width, preferred_height):
    """Apply responsive sizing to dialogs so they stay usable on short screens."""
    width, height = get_screen_constrained_size(
        preferred_width,
        preferred_height,
        ABOUT_WINDOW_MIN_WIDTH,
        ABOUT_WINDOW_MIN_HEIGHT,
        padding_x=120,
        padding_y=120
    )
    dialog.minsize(min(ABOUT_WINDOW_MIN_WIDTH, width), min(ABOUT_WINDOW_MIN_HEIGHT, height))
    center_window(dialog, width, height)

def bind_responsive_button_grid(parent, buttons, expanded_columns, breakpoint):
    """Lay out button rows in columns on wide screens and stack on narrow widths."""
    if not buttons:
        return

    max_columns = max(1, expanded_columns)

    def apply_layout(event=None):
        frame_width = parent.winfo_width()
        compact = frame_width > 0 and frame_width < breakpoint
        visible_buttons = []

        for button in buttons:
            if not button.winfo_exists():
                continue

            if bool(getattr(button, "_grid_hidden", False)):
                button.grid_forget()
                continue

            visible_buttons.append(button)

        visible_count = len(visible_buttons)
        if compact:
            columns = 1
        else:
            columns = min(max_columns, max(1, visible_count))

        for col in range(max_columns):
            parent.grid_columnconfigure(col, weight=0)
        for col in range(columns):
            parent.grid_columnconfigure(col, weight=1)

        for idx, button in enumerate(visible_buttons):
            button.grid_forget()
            row = idx if compact else idx // columns
            column = 0 if compact else idx % columns
            if compact:
                button.grid(row=row, column=column, padx=0, pady=(0, 6), sticky="ew")
            else:
                button.grid(row=row, column=column, padx=4, pady=4, sticky="ew")

    parent.bind("<Configure>", apply_layout, add="+")
    app.after(0, apply_layout)

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

def clear_about_update_toast():
    """Remove the temporary About-button update toast if visible."""
    global about_update_toast_label, about_update_toast_after_id

    if about_update_toast_after_id:
        try:
            app.after_cancel(about_update_toast_after_id)
        except Exception:
            pass
    about_update_toast_after_id = None

    if about_update_toast_label and about_update_toast_label.winfo_exists():
        about_update_toast_label.destroy()
    about_update_toast_label = None

def show_about_update_toast():
    """Show a short toast near the About button when an update is available."""
    global about_update_toast_label, about_update_toast_after_id

    if not about_action_button or not about_action_button.winfo_exists():
        return

    clear_about_update_toast()

    toast_parent = about_action_button.master
    about_update_toast_label = ctk.CTkLabel(
        toast_parent,
        text="Update available - open About",
        font=("Arial", 11, "bold"),
        text_color="#ffe8b5",
        fg_color="#8b5a1e",
        corner_radius=8
    )
    # Place toast directly under the About button so the call-to-action is obvious.
    about_update_toast_label.place(in_=about_action_button, relx=0.5, rely=1.0, y=8, anchor="n")
    about_update_toast_label.lift()
    about_update_toast_after_id = app.after(5000, clear_about_update_toast)

def refresh_about_button_attention(show_toast=False):
    """Update About button styling and optional toast from update checker state."""
    if not about_action_button or not about_action_button.winfo_exists():
        clear_about_update_toast()
        return

    if update_check_state == "update_available":
        about_action_button.configure(text="About !", fg_color="#8b5a1e", hover_color="#a36b27")
        if show_toast:
            show_about_update_toast()
    else:
        about_action_button.configure(text="About", fg_color="#2f556f", hover_color="#3a6684")
        clear_about_update_toast()

def set_about_button_widget(button):
    """Track active About button on the current screen."""
    global about_action_button
    about_action_button = button
    refresh_about_button_attention(show_toast=(update_check_state == "update_available"))

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
    refresh_about_button_attention(show_toast=(state == "update_available"))

def update_check_worker():
    """Background worker that queries latest GitHub release and compares versions."""
    try:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Steam-Review-Generator"
        }
        response = request_with_retry(
            "GET",
            GITHUB_LATEST_RELEASE_API_URL,
            headers=headers,
            timeout=8,
            retry_status_codes=NETWORK_RETRYABLE_SERVER_STATUS_CODES,
        )
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
    refresh_about_button_attention(show_toast=False)
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
    clear_about_update_toast()
    if about_dialog and about_dialog.winfo_exists():
        about_dialog.lift()
        about_dialog.focus_force()
        return

    version_value = get_app_version()
    about_dialog = ctk.CTkToplevel(app)
    about_dialog.title("About Steam Review Generator")
    about_dialog.resizable(True, True)
    about_dialog.configure(fg_color=STEAM_BG)
    about_dialog.transient(app)
    about_dialog.grab_set()
    about_dialog.protocol("WM_DELETE_WINDOW", close_about_dialog)
    apply_dialog_size(about_dialog, ABOUT_WINDOW_WIDTH, ABOUT_WINDOW_HEIGHT)

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

    create_update_banner(about_frame, padx=14, pady=(0, 12))

    links_frame = ctk.CTkFrame(about_frame, fg_color="transparent")
    links_frame.pack(fill="x", padx=8, pady=(0, 14))

    release_btn = ctk.CTkButton(
        links_frame,
        text="Latest Release",
        command=lambda: webbrowser.open(GITHUB_RELEASES_URL),
        fg_color="#2f556f"
    )

    release_notes_btn = ctk.CTkButton(
        links_frame,
        text="Release Notes",
        command=lambda: webbrowser.open(GITHUB_RELEASES_URL),
        fg_color="#2f556f"
    )

    issues_btn = ctk.CTkButton(
        links_frame,
        text="Report Issue",
        command=lambda: webbrowser.open(GITHUB_ISSUES_URL),
        fg_color="#2f556f"
    )

    repo_btn = ctk.CTkButton(
        links_frame,
        text="Open GitHub",
        command=lambda: webbrowser.open(GITHUB_REPO_URL),
        fg_color="#2f556f"
    )
    bind_responsive_button_grid(
        links_frame,
        [release_btn, release_notes_btn, issues_btn, repo_btn],
        expanded_columns=2,
        breakpoint=420
    )

    close_btn = ctk.CTkButton(
        about_frame,
        text="Close",
        command=close_about_dialog,
        fg_color=STEAM_ACCENT
    )
    close_btn.pack(fill="x", padx=20, pady=(8, 16))

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
        login_progress.pack(fill="x", pady=(0, 15))
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

def polish_store_copy_text(raw_text):
    """Apply lightweight punctuation and sentence-case cleanup for Store descriptions."""
    text = str(raw_text or "").strip()
    if not text:
        return ""

    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"([.!?]){2,}", r"\1", text)
    text = re.sub(r"([.!?])([A-Za-z])", r"\1 \2", text)

    # Fix sentence-start casing when HTML fragments collapse into lowercase starts.
    text = re.sub(
        r"(^|[.!?]\s+)([a-z])",
        lambda match: f"{match.group(1)}{match.group(2).upper()}",
        text,
    )

    # Remove occasional trailing orphan pronoun fragments (example: "...weapon. you.").
    text = re.sub(r"([.!?])\s+(?:you|it|they|he|she)\.$", r"\1", text, flags=re.IGNORECASE)
    return text.strip()

def normalize_store_text(raw_text):
    """Normalize Steam Store HTML/whitespace text to plain readable content."""
    if not raw_text:
        return ""
    stripped = re.sub(r"<[^>]+>", " ", str(raw_text))
    collapsed = re.sub(r"\s+", " ", stripped).strip()
    return polish_store_copy_text(html.unescape(collapsed))


def extract_json_object_from_text(raw_text):
    """Parse the first JSON object from model output text."""
    cleaned = str(raw_text or "").strip()
    if not cleaned:
        raise ValueError("Model output was empty.")

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start_index = cleaned.find("{")
    end_index = cleaned.rfind("}")
    if start_index == -1 or end_index == -1 or end_index <= start_index:
        raise ValueError("Model output did not contain a JSON object.")

    snippet = cleaned[start_index:end_index + 1]
    parsed = json.loads(snippet)
    if not isinstance(parsed, dict):
        raise ValueError("Model JSON response must be an object.")
    return parsed


def request_local_ai_json(model_name, prompt_text):
    """Call a local Ollama-compatible endpoint and parse a JSON object response."""
    if not LOCAL_AI_OLLAMA_URL:
        raise ValueError("AI endpoint URL is not configured.")
    if not model_name:
        raise ValueError("AI model name is not configured.")

    payload = {
        "model": model_name,
        "prompt": prompt_text,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.1,
        },
    }
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    response = requests.post(
        LOCAL_AI_OLLAMA_URL,
        headers=headers,
        json=payload,
        timeout=LOCAL_AI_TIMEOUT_SECONDS,
    )
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as error:
        error_text = ""
        try:
            error_payload = response.json()
            if isinstance(error_payload, dict):
                error_text = str(error_payload.get("error") or error_payload.get("message") or "").strip()
        except (ValueError, TypeError, json.JSONDecodeError):
            pass

        if not error_text:
            error_text = str(response.text or "").strip()

        normalized_error_text = error_text.lower()
        is_missing_model = (
            "model" in normalized_error_text
            and (
                "not found" in normalized_error_text
                or "missing" in normalized_error_text
                or "pull" in normalized_error_text
            )
        )
        if is_missing_model:
            raise ValueError(f"Missing Ollama model '{model_name}'. Run: ollama pull {model_name}") from error
        if error_text:
            raise ValueError(f"Ollama request failed: {error_text}") from error
        raise

    try:
        body = response.json()
    except (ValueError, TypeError, json.JSONDecodeError) as error:
        raise ValueError("Ollama returned invalid JSON.") from error

    response_text = body.get("response", "")
    return extract_json_object_from_text(response_text)


def build_ai_review_profile_prompt(game_name, store_genres, store_categories, description_text):
    """Build strict JSON prompt for AI-generated review categories and weights."""
    safe_description = str(description_text or "")[:LOCAL_AI_MAX_DESCRIPTION_CHARS]
    genre_list = ", ".join(store_genres or []) or "None"
    category_list = ", ".join(store_categories or []) or "None"

    return (
        "You generate a review profile for a Steam game.\n"
        "Return JSON only with schema:\n"
        "{\"genre\":\"...\",\"categories\":[{\"name\":\"...\",\"weight\":1.2,\"options\":[\"...\"]}]}\n"
        "Rules:\n"
        f"- categories must contain exactly {AI_REVIEW_CATEGORY_COUNT} items\n"
        f"- each category options list must contain exactly {AI_REVIEW_OPTION_COUNT} short choices\n"
        "- options must be ordered best to worst\n"
        "- each option must describe quality for the category, not a feature or mode description\n"
        "- option labels must be concise and should not repeat the category name\n"
        "- each option must capture a distinct nuance (depth, pacing, feedback, polish, consistency, frustration, etc.)\n"
        "- do not use the same wording pattern for all ten options\n"
        "- each weight must be a number between 0.6 and 3.0\n"
        "- genre field must be the primary Steam genre from the list provided\n"
        "- every category must align with one or more provided Steam genres/categories\n"
        "- category names must be evaluative review dimensions, not lore/theme flavor names\n"
        "- category names must be invented specifically for this game based on its genres and description\n"
        "- ask yourself: what are the most important things a reviewer would judge in THIS game?\n"
        "- use the store description and genre tags to identify what this game actually involves\n"
        "- do not reuse a fixed template; every game should get unique category names\n"
        "- options must be evaluative quality judgments, not event/lore observations\n"
        "- option ladders must differ across categories and reflect each category's specific dimension\n"
        "- do not include markdown or explanations, JSON only\n\n"
        f"Game name: {game_name or 'Unknown'}\n"
        f"Steam genres: {genre_list}\n"
        f"Steam categories: {category_list}\n"
        f"Store description: {safe_description}\n"
    )


def _build_category_quality_option_ladder(category_name):
    """Build a consistent quality ladder without repeating category text."""
    del category_name
    return list(AI_REVIEW_QUALITY_OPTION_TEMPLATES[:AI_REVIEW_OPTION_COUNT])


def _build_store_semantic_context_text(store_genres, store_categories, description_text):
    """Build a lowercase text blob used to validate AI category theme alignment."""
    parts = []
    for genre_name in list(store_genres or []):
        cleaned = str(genre_name or "").strip()
        if cleaned:
            parts.append(cleaned)
    for category_name in list(store_categories or []):
        cleaned = str(category_name or "").strip()
        if cleaned:
            parts.append(cleaned)
    cleaned_description = str(description_text or "").strip()
    if cleaned_description:
        parts.append(cleaned_description)
    return " ".join(parts).lower()


def collect_ai_profile_semantic_mismatches(ai_review_profile, store_genres, store_categories, description_text):
    """Return mismatch reasons when AI categories imply themes missing from Steam metadata."""
    context_text = _build_store_semantic_context_text(store_genres, store_categories, description_text)
    mismatch_reasons = []

    for category_name in list(ai_review_profile.get("category_list", []) or []):
        cleaned_name = str(category_name or "").strip()
        if not cleaned_name:
            continue

        normalized_category_name = cleaned_name.lower()
        for rule in AI_REVIEW_GENRE_THEME_RULES:
            has_theme_cue = False
            for cue in rule["category_cues"]:
                cue_pattern = re.compile(rf"\b{re.escape(cue)}\b", flags=re.IGNORECASE)
                if cue_pattern.search(normalized_category_name):
                    has_theme_cue = True
                    break

            if not has_theme_cue:
                continue

            has_context_cue = any(context_cue in context_text for context_cue in rule["context_cues"])
            if not has_context_cue:
                mismatch_reasons.append(
                    (
                        f"Category '{cleaned_name}' appears {rule['theme']}-specific, "
                        f"but Steam genres/categories do not indicate {rule['theme']}."
                    )
                )
                break

    return mismatch_reasons


def _looks_like_evaluative_option(option_text):
    """Return True when an option reads as evaluative feedback (not just factual flavor)."""
    normalized = str(option_text or "").strip().lower()
    if not normalized:
        return False
    return any(cue in normalized for cue in AI_REVIEW_OPTION_EVALUATIVE_CUES)


def _looks_like_observation_option(option_text):
    """Return True when an option looks like a factual/event observation instead of an evaluation."""
    normalized = str(option_text or "").strip().lower()
    if not normalized:
        return False

    if _looks_like_quality_option(normalized) or _looks_like_evaluative_option(normalized):
        return False

    first_word = normalized.split()[0] if normalized.split() else ""
    if first_word in AI_REVIEW_OPTION_FREQUENCY_CUES:
        return True

    if normalized.startswith(("contains ", "includes ", "features ", "has ")):
        return True

    return False


def _category_name_looks_evaluative(category_name):
    """Return True when a category name appears to be a review axis."""
    normalized = str(category_name or "").strip().lower()
    if not normalized:
        return False

    return any(cue in normalized for cue in AI_REVIEW_CATEGORY_AXIS_CUES)


def collect_ai_profile_quality_mismatches(ai_review_profile):
    """Return mismatch reasons when categories/options are not evaluative review dimensions."""
    mismatch_reasons = []
    option_signature_map = {}

    categories_map = ai_review_profile.get("categories", {})
    for category_name in list(ai_review_profile.get("category_list", []) or []):
        cleaned_category_name = str(category_name or "").strip()
        if not cleaned_category_name:
            continue

        if not _category_name_looks_evaluative(cleaned_category_name):
            mismatch_reasons.append(
                (
                    f"Category '{cleaned_category_name}' is not a clear evaluative review axis "
                    "(it reads like flavor/theme wording)."
                )
            )

        raw_options = categories_map.get(cleaned_category_name, [])
        option_labels = []
        for option_entry in list(raw_options or []):
            if isinstance(option_entry, (list, tuple)) and option_entry:
                option_label = str(option_entry[0] or "").strip()
            else:
                option_label = str(option_entry or "").strip()

            if option_label:
                option_labels.append(option_label)

        if not option_labels:
            mismatch_reasons.append(
                f"Category '{cleaned_category_name}' has no usable option labels."
            )
            continue

        option_signature = tuple(option_label.lower() for option_label in option_labels[:AI_REVIEW_OPTION_COUNT])
        option_signature_map.setdefault(option_signature, []).append(cleaned_category_name)

        quality_like_count = sum(
            1
            for option_label in option_labels
            if _looks_like_quality_option(option_label) or _looks_like_evaluative_option(option_label)
        )
        observation_like_count = sum(
            1 for option_label in option_labels if _looks_like_observation_option(option_label)
        )
        feature_toggle_count = sum(
            1 for option_label in option_labels if _looks_like_feature_availability_option(option_label)
        )
        unique_option_count = len({option_label.lower() for option_label in option_labels})
        first_word_count = len({option_label.split()[0].lower() for option_label in option_labels if option_label.split()})

        if quality_like_count < 6:
            mismatch_reasons.append(
                (
                    f"Category '{cleaned_category_name}' options are not evaluative enough "
                    f"({quality_like_count}/{len(option_labels)} look like quality judgments)."
                )
            )

        if observation_like_count >= 4:
            mismatch_reasons.append(
                (
                    f"Category '{cleaned_category_name}' options read like event observations "
                    f"({observation_like_count}/{len(option_labels)}), not quality judgments."
                )
            )

        if feature_toggle_count > 2:
            mismatch_reasons.append(
                (
                    f"Category '{cleaned_category_name}' has too many feature-availability options "
                    f"({feature_toggle_count}/{len(option_labels)})."
                )
            )

        if unique_option_count < max(6, len(option_labels) - 1):
            mismatch_reasons.append(
                (
                    f"Category '{cleaned_category_name}' options are too repetitive "
                    f"({unique_option_count}/{len(option_labels)} unique)."
                )
            )

        if first_word_count < 4:
            mismatch_reasons.append(
                (
                    f"Category '{cleaned_category_name}' options follow one wording pattern "
                    f"({first_word_count} distinct starters)."
                )
            )

    for option_signature, category_names in option_signature_map.items():
        if not option_signature:
            continue
        if len(category_names) < 2:
            continue

        mismatch_reasons.append(
            (
                "Option ladders are duplicated across categories: "
                f"{', '.join(category_names)}."
            )
        )

    return mismatch_reasons


def build_ai_review_profile_correction_prompt(
    game_name,
    store_genres,
    store_categories,
    description_text,
    previous_profile,
    mismatch_reasons,
):
    """Build a correction-pass prompt when AI profile output is misaligned."""
    safe_description = str(description_text or "")[:LOCAL_AI_MAX_DESCRIPTION_CHARS]
    genre_list = ", ".join(store_genres or []) or "None"
    category_list = ", ".join(store_categories or []) or "None"
    prior_profile_json = json.dumps(previous_profile or {}, ensure_ascii=True)

    mismatch_lines = []
    for reason in list(mismatch_reasons or [])[:6]:
        cleaned_reason = str(reason or "").strip()
        if cleaned_reason:
            mismatch_lines.append(f"- {cleaned_reason}")
    mismatch_block = "\n".join(mismatch_lines) if mismatch_lines else "- Categories/options must align with review-quality rules."

    return (
        "Your previous response had quality/genre mismatches. Generate a corrected review profile.\n"
        "Return JSON only with schema:\n"
        "{\"genre\":\"...\",\"categories\":[{\"name\":\"...\",\"weight\":1.2,\"options\":[\"...\"]}]}\n"
        "Rules:\n"
        f"- categories must contain exactly {AI_REVIEW_CATEGORY_COUNT} items\n"
        f"- each category options list must contain exactly {AI_REVIEW_OPTION_COUNT} short choices\n"
        "- options must be ordered best to worst\n"
        "- options must be unique and should not repeat the category name\n"
        "- options must be evaluative quality judgments, not lore/event observations\n"
        "- each weight must be a number between 0.6 and 3.0\n"
        "- genre field must be the primary Steam genre from the list provided\n"
        "- every category must align with one or more provided Steam genres/categories\n"
        "- category names must be evaluative review dimensions, not flavor-only labels\n"
        "- remove category themes that are unrelated to the provided Steam metadata\n"
        "- option ladders for different categories must not be identical\n"
        "- do not include markdown or explanations, JSON only\n\n"
        "Issues to correct:\n"
        f"{mismatch_block}\n\n"
        f"Previous profile JSON: {prior_profile_json}\n"
        f"Game name: {game_name or 'Unknown'}\n"
        f"Steam genres: {genre_list}\n"
        f"Steam categories: {category_list}\n"
        f"Store description: {safe_description}\n"
    )


def _looks_like_quality_option(option_text):
    """Return True when an option reads like a quality judgment."""
    normalized = str(option_text or "").strip().lower()
    if not normalized:
        return False
    return any(cue in normalized for cue in AI_REVIEW_QUALITY_CUES)


def _looks_like_feature_availability_option(option_text):
    """Return True when an option is mostly a mode/feature availability statement."""
    normalized = str(option_text or "").strip().lower()
    if not normalized:
        return False
    return any(cue in normalized for cue in AI_REVIEW_FEATURE_AVAILABILITY_CUES)


def _remove_category_phrase_from_option(option_text, category_name):
    """Strip repeated category-name text from an option label."""
    cleaned_option = re.sub(r"\s+", " ", str(option_text or "").strip())
    category_phrase = re.sub(r"\s+", " ", str(category_name or "").strip())

    if not cleaned_option:
        return ""

    if category_phrase:
        category_pattern = re.compile(rf"\b{re.escape(category_phrase)}\b", flags=re.IGNORECASE)
        stripped_option = category_pattern.sub("", cleaned_option)
        stripped_option = re.sub(r"\s+", " ", stripped_option).strip(" -:;,.\"'")

        # Keep original wording if stripping collapses the option into a generic short label.
        if len(stripped_option.split()) >= 3:
            cleaned_option = stripped_option

    return cleaned_option


def _extract_option_text(option_item):
    """Extract text from AI option items that may be strings, dicts, or tuples."""
    if isinstance(option_item, str):
        return option_item.strip()

    if isinstance(option_item, dict):
        for key_name in ("text", "label", "option", "name", "value"):
            candidate_text = str(option_item.get(key_name, "") or "").strip()
            if candidate_text:
                return candidate_text
        return ""

    if isinstance(option_item, (list, tuple)):
        for candidate in option_item:
            candidate_text = _extract_option_text(candidate)
            if candidate_text:
                return candidate_text
        return ""

    return str(option_item or "").strip()


def _derive_option_topic_suffix(category_name, candidate_options):
    """Derive a short category-specific suffix used when padding incomplete ladders."""
    source_text = f"{str(category_name or '')} {' '.join(candidate_options or [])}".strip().lower()
    if not source_text:
        return ""

    topic_terms = []
    for token in re.findall(r"[a-zA-Z][a-zA-Z0-9'-]*", source_text):
        cleaned_token = token.strip("'\"").lower()
        if not cleaned_token:
            continue
        if cleaned_token in AI_REVIEW_OPTION_TOPIC_STOPWORDS:
            continue
        if cleaned_token in AI_REVIEW_QUALITY_CUES:
            continue
        if cleaned_token in topic_terms:
            continue
        topic_terms.append(cleaned_token)
        if len(topic_terms) >= 2:
            break

    return " ".join(topic_terms)


def _expand_ai_option_ladder(category_name, candidate_options):
    """Expand partial AI ladders to full length using category-aware padding."""
    expanded_options = []
    seen_options = set()

    for option_text in list(candidate_options or []):
        cleaned_option = str(option_text or "").strip()
        if not cleaned_option:
            continue
        normalized_key = cleaned_option.lower()
        if normalized_key in seen_options:
            continue
        seen_options.add(normalized_key)
        expanded_options.append(cleaned_option)

    topic_suffix = _derive_option_topic_suffix(category_name, expanded_options)

    for template in AI_REVIEW_QUALITY_OPTION_TEMPLATES:
        if len(expanded_options) >= AI_REVIEW_OPTION_COUNT:
            break

        candidate_text = template if not topic_suffix else f"{template} {topic_suffix}"
        normalized_key = candidate_text.lower()
        if normalized_key in seen_options:
            continue
        seen_options.add(normalized_key)
        expanded_options.append(candidate_text)

    for template in AI_REVIEW_QUALITY_OPTION_TEMPLATES:
        if len(expanded_options) >= AI_REVIEW_OPTION_COUNT:
            break

        normalized_key = template.lower()
        if normalized_key in seen_options:
            continue
        seen_options.add(normalized_key)
        expanded_options.append(template)

    return expanded_options[:AI_REVIEW_OPTION_COUNT]


def _build_ai_option_ladder(category_name, raw_options):
    """Normalize AI options and force a clear good-to-bad quality ladder when needed."""
    cleaned_options = []
    seen_options = set()
    if isinstance(raw_options, list):
        for item in raw_options:
            raw_option_text = _extract_option_text(item)
            option_text = _remove_category_phrase_from_option(raw_option_text, category_name)
            if not option_text:
                option_text = raw_option_text
            if not option_text:
                continue

            normalized_option_key = option_text.lower()
            if normalized_option_key in seen_options:
                continue

            seen_options.add(normalized_option_key)
            cleaned_options.append(option_text)
            if len(cleaned_options) >= AI_REVIEW_OPTION_COUNT:
                break

    if cleaned_options:
        candidate_options = cleaned_options[:AI_REVIEW_OPTION_COUNT]
        feature_toggle_count = sum(
            1 for option_text in candidate_options if _looks_like_feature_availability_option(option_text)
        )
        # Prefer AI-authored unique wording unless the ladder is mostly feature-toggle statements.
        if feature_toggle_count <= 4:
            return _expand_ai_option_ladder(category_name, candidate_options)

    return _build_category_quality_option_ladder(category_name)


def sanitize_ai_review_profile_payload(raw_payload, fallback_genre):
    """Validate and normalize AI-generated review profile payload."""
    if not isinstance(raw_payload, dict):
        raise ValueError("AI review profile payload must be a JSON object.")

    genre_name = str(raw_payload.get("genre") or fallback_genre or DEFAULT_GENRE).strip()
    if not genre_name:
        genre_name = DEFAULT_GENRE

    raw_categories = raw_payload.get("categories", [])
    if not isinstance(raw_categories, list):
        raise ValueError("AI review profile must include a categories list.")

    category_list = []
    category_name_set = set()
    categories = {}
    category_weights = {}

    for raw_category in raw_categories:
        if len(category_list) >= AI_REVIEW_CATEGORY_COUNT:
            break
        if not isinstance(raw_category, dict):
            continue

        category_name = re.sub(r"\s+", " ", str(raw_category.get("name", "")).strip())
        if not category_name:
            continue
        normalized_name = category_name.lower()
        if normalized_name in category_name_set:
            continue

        try:
            category_weight = float(raw_category.get("weight", 1.0))
        except (TypeError, ValueError):
            category_weight = 1.0
        category_weight = round(max(0.6, min(3.0, category_weight)), 2)

        option_texts = _build_ai_option_ladder(category_name, raw_category.get("options", []))
        options = [
            (option_text, AI_REVIEW_OPTION_COUNT - index)
            for index, option_text in enumerate(option_texts)
        ]

        category_name_set.add(normalized_name)
        category_list.append(category_name)
        categories[category_name] = options
        category_weights[category_name] = category_weight

    fallback_index = 0
    while len(category_list) < AI_REVIEW_CATEGORY_COUNT:
        fallback_name = AI_REVIEW_FALLBACK_CATEGORY_NAMES[fallback_index % len(AI_REVIEW_FALLBACK_CATEGORY_NAMES)]
        fallback_index += 1

        candidate_name = fallback_name
        suffix_counter = 2
        while candidate_name.lower() in category_name_set:
            candidate_name = f"{fallback_name} {suffix_counter}"
            suffix_counter += 1

        category_name_set.add(candidate_name.lower())
        category_list.append(candidate_name)
        categories[candidate_name] = [
            (option_text, AI_REVIEW_OPTION_COUNT - index)
            for index, option_text in enumerate(_build_category_quality_option_ladder(candidate_name))
        ]
        category_weights[candidate_name] = 1.0

    return {
        "genre": genre_name,
        "description": str(raw_payload.get("description", "")).strip(),
        "category_list": category_list,
        "categories": categories,
        "category_weights": category_weights,
    }


def set_active_ai_review_profile(ai_review_profile):
    """Apply an AI-generated review profile to active category state."""
    global active_genre, active_categories, active_category_weights
    global active_category_list, active_genre_description
    global active_weight_style, active_weight_style_description

    genre_name = str(ai_review_profile.get("genre", "")).strip() or DEFAULT_GENRE
    category_list = list(ai_review_profile.get("category_list", []))
    categories = {
        category_name: list(ai_review_profile.get("categories", {}).get(category_name, []))
        for category_name in category_list
    }
    category_weights = {
        category_name: float(ai_review_profile.get("category_weights", {}).get(category_name, 1.0))
        for category_name in category_list
    }

    if not category_list or not categories:
        set_active_fallback_review_profile()
        return

    active_genre = genre_name
    active_categories = categories
    active_category_weights = category_weights
    active_category_list = category_list

    generated_description = str(ai_review_profile.get("description", "")).strip()
    if generated_description:
        active_genre_description = generated_description
    else:
        active_genre_description = "AI-generated review profile from Steam tags and game description."

    active_weight_style = "AI Generated"
    active_weight_style_description = "Weights generated automatically from Steam tags and game description."


def get_ai_status_text_color():
    """Return status text color for the local AI health indicator."""
    state = str(ai_service_status_cache.get("state", "unknown") or "unknown")
    if state == "available":
        return "#66d17a"
    if state == "unavailable":
        return "#ffb26b"
    if state == "checking":
        return "#9fb6c4"
    return "#9fb6c4"


def get_ai_status_line():
    """Return user-facing local AI status line for summary UI."""
    status_message = str(ai_service_status_cache.get("message", "") or "").strip()
    if not status_message:
        status_message = "Status unavailable."
    return f"AI Assist: {status_message}"


def get_missing_ai_models():
    """Return missing model names currently reported by AI status checks."""
    missing_models = []
    for model_name in list(ai_service_status_cache.get("missing_models", []) or []):
        cleaned_name = str(model_name or "").strip()
        if cleaned_name:
            missing_models.append(cleaned_name)
    return missing_models


def get_missing_ai_pull_command_text():
    """Return one or more ollama pull commands for currently missing models."""
    missing_models = get_missing_ai_models()
    if not missing_models:
        return ""
    return "\n".join(f"ollama pull {model_name}" for model_name in missing_models)


def get_local_ai_status_tags_url():
    """Return Ollama /api/tags URL based on configured generate endpoint."""
    endpoint = str(LOCAL_AI_OLLAMA_URL or "").strip()
    if not endpoint:
        return ""
    if "/api/" in endpoint:
        base_url = endpoint.split("/api/", 1)[0].rstrip("/")
        return f"{base_url}/api/tags"
    return endpoint.rstrip("/") + "/api/tags"


def update_ai_status_summary_label(session_token):
    """Update summary-screen AI status widgets when visible for active session."""
    if session_token != review_session_token:
        return
    if current_review_step != "summary":
        return

    if ai_status_summary_label and ai_status_summary_label.winfo_exists():
        ai_status_summary_label.configure(
            text=get_ai_status_line(),
            text_color=get_ai_status_text_color(),
        )

    if ai_status_refresh_btn and ai_status_refresh_btn.winfo_exists():
        if ai_service_status_check_in_progress:
            ai_status_refresh_btn.configure(text="Checking...", state="disabled")
        elif not LOCAL_AI_ASSIST_ENABLED:
            ai_status_refresh_btn.configure(text="AI Disabled", state="disabled")
        else:
            ai_status_refresh_btn.configure(text="Refresh AI Status", state="normal")

    if ai_status_setup_btn and ai_status_setup_btn.winfo_exists():
        status_state = str(ai_service_status_cache.get("state", "unknown") or "unknown")
        if status_state == "available":
            ai_status_setup_btn.configure(text="Manage Ollama", state="normal")
        else:
            ai_status_setup_btn.configure(text="Setup Ollama", state="normal")

    if ai_status_copy_pull_btn and ai_status_copy_pull_btn.winfo_exists():
        pull_command_text = get_missing_ai_pull_command_text()
        show_copy_pull_btn = bool(pull_command_text) and not ai_service_status_check_in_progress
        was_hidden = bool(getattr(ai_status_copy_pull_btn, "_grid_hidden", False))
        ai_status_copy_pull_btn._grid_hidden = not show_copy_pull_btn

        if show_copy_pull_btn:
            ai_status_copy_pull_btn.configure(text="Copy Pull Cmd", state="normal")
        else:
            ai_status_copy_pull_btn.configure(text="Copy Pull Cmd", state="disabled")

        if was_hidden != ai_status_copy_pull_btn._grid_hidden:
            actions_parent = ai_status_copy_pull_btn.master
            if actions_parent and actions_parent.winfo_exists():
                actions_parent.event_generate("<Configure>")


def on_refresh_ai_status_click():
    """Handle manual local-AI status refresh from the summary screen."""
    refresh_ai_service_status_async(review_session_token, force=True)


def on_setup_ollama_click():
    """Open Ollama setup/resources and trigger a fresh local AI status check."""
    status_state = str(ai_service_status_cache.get("state", "unknown") or "unknown")
    target_url = OLLAMA_LIBRARY_URL if status_state == "available" else OLLAMA_DOWNLOAD_WINDOWS_URL

    try:
        webbrowser.open(target_url)
    except Exception:
        pass

    if ai_status_summary_label and ai_status_summary_label.winfo_exists():
        if status_state == "available":
            ai_status_summary_label.configure(
                text="AI Assist: Opened Ollama library. Running a live status re-check...",
                text_color="#9fb6c4",
            )
        else:
            ai_status_summary_label.configure(
                text=(
                    "AI Assist: Opened Ollama setup page. "
                    "Install/pull model, then checking status..."
                ),
                text_color="#9fb6c4",
            )

    refresh_ai_service_status_async(review_session_token, force=True)
    app.after(1800, lambda: refresh_ai_service_status_async(review_session_token, force=True))


def on_copy_pull_command_click():
    """Copy Ollama pull commands for missing models from current AI status."""
    pull_command_text = get_missing_ai_pull_command_text()
    if not pull_command_text:
        if ai_status_summary_label and ai_status_summary_label.winfo_exists():
            ai_status_summary_label.configure(
                text="AI Assist: No missing models detected right now.",
                text_color="#9fb6c4",
            )
        return

    try:
        pyperclip.copy(pull_command_text)
        if ai_status_summary_label and ai_status_summary_label.winfo_exists():
            ai_status_summary_label.configure(
                text="AI Assist: Copied model pull command(s). Run them, then click Refresh AI Status.",
                text_color="#66d17a",
            )
    except Exception:
        fallback_command = pull_command_text.replace("\n", " ; ")
        if ai_status_summary_label and ai_status_summary_label.winfo_exists():
            ai_status_summary_label.configure(
                text=f"AI Assist: Copy unavailable. Run: {fallback_command}",
                text_color="#ffb26b",
            )


def complete_ai_service_status_probe(session_token, state, message, missing_models=None):
    """Finalize async AI service probe on UI thread and refresh summary label."""
    global ai_service_status_cache, ai_service_status_check_in_progress

    cleaned_missing_models = []
    for model_name in list(missing_models or []):
        cleaned_name = str(model_name or "").strip()
        if cleaned_name:
            cleaned_missing_models.append(cleaned_name)

    ai_service_status_cache = {
        "state": str(state or "unknown"),
        "message": str(message or "Status unavailable."),
        "checked_at": time.time(),
        "missing_models": cleaned_missing_models,
    }
    ai_service_status_check_in_progress = False
    update_ai_status_summary_label(session_token)


def probe_ai_service_worker(session_token):
    """Background probe for local Ollama availability and required model presence."""
    if not LOCAL_AI_ASSIST_ENABLED:
        app.after(
            0,
            lambda: complete_ai_service_status_probe(
                session_token,
                "disabled",
                "Disabled (set STEAM_REVIEW_AI_ASSIST=1 to enable local AI assist).",
            ),
        )
        return

    tags_url = get_local_ai_status_tags_url()
    headers = {
        "Accept": "application/json",
        "User-Agent": "Steam-Review-Generator",
    }

    try:
        if not tags_url:
            raise ValueError("Ollama URL is not configured.")

        response = requests.get(
            tags_url,
            headers=headers,
            timeout=LOCAL_AI_STATUS_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        models_payload = payload.get("models", [])

        available_model_names = set()
        for model_entry in models_payload:
            if not isinstance(model_entry, dict):
                continue
            model_name = str(model_entry.get("model") or model_entry.get("name") or "").strip()
            if model_name:
                available_model_names.add(model_name)

        required_models = {LOCAL_AI_DETECTION_MODEL}

        missing_models = sorted(
            model_name for model_name in required_models
            if model_name and model_name not in available_model_names
        )

        if missing_models:
            pull_hint = f" Run: ollama pull {missing_models[0]}"
            if len(missing_models) > 1:
                pull_hint += " (repeat for each missing model)."
            message = f"Connected, missing model(s): {', '.join(missing_models)}.{pull_hint}"
            app.after(
                0,
                lambda: complete_ai_service_status_probe(
                    session_token,
                    "unavailable",
                    message,
                    missing_models=missing_models,
                ),
            )
            return

        active_models = sorted(model_name for model_name in required_models if model_name)
        model_text = ", ".join(active_models) if active_models else LOCAL_AI_MODEL
        app.after(
            0,
            lambda: complete_ai_service_status_probe(
                session_token,
                "available",
                f"Connected ({model_text})",
            ),
        )
    except requests.exceptions.Timeout:
        app.after(
            0,
            lambda: complete_ai_service_status_probe(
                session_token,
                "unavailable",
                "Unavailable (local Ollama status check timed out).",
            ),
        )
    except requests.exceptions.RequestException:
        app.after(
            0,
            lambda: complete_ai_service_status_probe(
                session_token,
                "unavailable",
                "Unavailable (could not reach local Ollama).",
            ),
        )
    except (ValueError, TypeError, json.JSONDecodeError):
        app.after(
            0,
            lambda: complete_ai_service_status_probe(
                session_token,
                "unavailable",
                "Unavailable (invalid status response from Ollama).",
            ),
        )


def refresh_ai_service_status_async(session_token, force=False):
    """Refresh local AI status in background with cached TTL to avoid excessive requests."""
    global ai_service_status_check_in_progress, ai_service_status_cache

    if not LOCAL_AI_ASSIST_ENABLED:
        complete_ai_service_status_probe(
            session_token,
            "disabled",
            "Disabled (set STEAM_REVIEW_AI_ASSIST=1 to enable local AI assist).",
        )
        return

    update_ai_status_summary_label(session_token)
    if ai_service_status_check_in_progress:
        return

    last_checked = float(ai_service_status_cache.get("checked_at", 0.0) or 0.0)
    status_state = str(ai_service_status_cache.get("state", "unknown") or "unknown")
    cache_age_seconds = time.time() - last_checked if last_checked > 0 else LOCAL_AI_STATUS_CACHE_SECONDS + 1
    is_cache_fresh = cache_age_seconds < LOCAL_AI_STATUS_CACHE_SECONDS
    should_probe = bool(force) or status_state in {"unknown", "checking"} or not is_cache_fresh
    if not should_probe:
        return

    ai_service_status_check_in_progress = True
    ai_service_status_cache["state"] = "checking"
    ai_service_status_cache["message"] = "Checking local Ollama availability..."
    ai_service_status_cache["missing_models"] = []
    update_ai_status_summary_label(session_token)

    threading.Thread(
        target=probe_ai_service_worker,
        args=(session_token,),
        daemon=True,
    ).start()


def fetch_store_game_details(app_id):
    """Fetch Steam Store details used for genre detection and summary display."""
    params = {
        "appids": str(app_id),
        "cc": "us",
        "l": "english",
    }
    headers = {
        "Accept": "application/json",
        "User-Agent": "Steam-Review-Generator",
    }

    response = request_with_retry(
        "GET",
        STEAM_STORE_APP_DETAILS_URL,
        params=params,
        headers=headers,
        timeout=STEAM_STORE_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    payload = response.json()
    app_entry = payload.get(str(app_id), {})
    if not app_entry.get("success"):
        raise ValueError("Steam Store details unavailable for this game.")

    app_data = app_entry.get("data", {})
    genres = app_data.get("genres", [])
    categories = app_data.get("categories", [])
    genre_labels = [
        item.get("description", "").strip()
        for item in genres
        if item.get("description")
    ]
    category_labels = [
        item.get("description", "").strip()
        for item in categories
        if item.get("description")
    ]

    short_description = normalize_store_text(app_data.get("short_description", ""))
    if not short_description:
        short_description = normalize_store_text(app_data.get("detailed_description", ""))

    return {
        "genres": genre_labels,
        "categories": category_labels,
        "description": short_description,
        "header_image_url": str(app_data.get("header_image", "") or "").strip(),
    }


def fetch_store_image_bytes(image_url):
    """Download Steam Store image bytes for summary preview."""
    if not image_url:
        return b""

    headers = {
        "Accept": "image/*",
        "User-Agent": "Steam-Review-Generator",
    }
    response = request_with_retry(
        "GET",
        image_url,
        headers=headers,
        timeout=STEAM_STORE_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.content

def complete_genre_detection(
    session_token,
    detected_genre,
    store_genres,
    store_categories,
    status_message,
    error_message="",
    description_text="",
    image_url="",
    image_bytes=b"",
    image_error="",
    ai_review_profile=None,
):
    """Apply genre auto-detection result on the UI thread for active review session."""
    if session_token != review_session_token:
        return
    if not current_game_data:
        return

    current_game_data["detected_genre"] = detected_genre or ""
    current_game_data["store_genres"] = list(store_genres or [])
    current_game_data["store_categories"] = list(store_categories or [])
    current_game_data["genre_detection_status"] = status_message
    current_game_data["genre_detection_error"] = error_message
    current_game_data["ai_review_profile"] = dict(ai_review_profile or {})
    current_game_data["review_profile_loading"] = False
    current_game_data["review_profile_ready"] = True
    if description_text:
        current_game_data["store_description"] = description_text
    if image_url:
        current_game_data["store_image_url"] = image_url
    if image_bytes:
        current_game_data["store_image_bytes"] = image_bytes
    if image_error:
        current_game_data["store_image_error"] = image_error

    if current_review_step in {"", "summary"}:
        if current_game_data.get("ai_review_profile", {}).get("category_list"):
            set_active_ai_review_profile(current_game_data.get("ai_review_profile", {}))
        else:
            set_active_fallback_review_profile()

    if current_review_step == "summary":
        show_game_summary()

def detect_game_genre_worker(app_id, game_name, session_token):
    """Background genre detection using Steam Store API appdetails endpoint."""
    try:
        details = fetch_store_game_details(app_id)
        store_genres = details.get("genres", [])
        store_categories = details.get("categories", [])
        description_text = details.get("description", "")
        image_url = details.get("header_image_url", "")
        image_bytes = b""
        image_error = ""

        if image_url:
            try:
                image_bytes = fetch_store_image_bytes(image_url)
            except requests.exceptions.RequestException:
                image_error = "Could not load game image preview."

        if not store_genres and not store_categories and not description_text:
            app.after(
                0,
                lambda: complete_genre_detection(
                    session_token,
                    "",
                    [],
                    [],
                    "Steam Store did not return genre labels.",
                    description_text=description_text,
                    image_url=image_url,
                    image_bytes=image_bytes,
                    image_error=image_error,
                ),
            )
            return

        ai_review_profile = {}
        detected_genre = store_genres[0] if store_genres else ""
        fallback_reason = ""
        used_profile_correction = False

        if LOCAL_AI_ASSIST_ENABLED:
            try:
                ai_prompt = build_ai_review_profile_prompt(
                    game_name,
                    store_genres,
                    store_categories,
                    description_text,
                )
                ai_raw_payload = request_local_ai_json(LOCAL_AI_DETECTION_MODEL, ai_prompt)
                ai_review_profile = sanitize_ai_review_profile_payload(ai_raw_payload, DEFAULT_GENRE)

                semantic_mismatches = collect_ai_profile_semantic_mismatches(
                    ai_review_profile,
                    store_genres,
                    store_categories,
                    description_text,
                )
                quality_mismatches = collect_ai_profile_quality_mismatches(ai_review_profile)
                profile_mismatches = list(semantic_mismatches) + list(quality_mismatches)

                if profile_mismatches:
                    correction_prompt = build_ai_review_profile_correction_prompt(
                        game_name,
                        store_genres,
                        store_categories,
                        description_text,
                        ai_review_profile,
                        profile_mismatches,
                    )
                    corrected_raw_payload = request_local_ai_json(LOCAL_AI_DETECTION_MODEL, correction_prompt)
                    corrected_profile = sanitize_ai_review_profile_payload(corrected_raw_payload, DEFAULT_GENRE)

                    corrected_semantic_mismatches = collect_ai_profile_semantic_mismatches(
                        corrected_profile,
                        store_genres,
                        store_categories,
                        description_text,
                    )
                    corrected_quality_mismatches = collect_ai_profile_quality_mismatches(corrected_profile)
                    corrected_profile_mismatches = list(corrected_semantic_mismatches) + list(corrected_quality_mismatches)
                    if corrected_profile_mismatches:
                        raise ValueError(
                            "AI profile remained misaligned after correction pass."
                        )
                    ai_review_profile = corrected_profile
                    used_profile_correction = True

                detected_genre = str(ai_review_profile.get("genre", "")).strip() or detected_genre
            except requests.exceptions.Timeout:
                timeout_seconds = int(round(LOCAL_AI_TIMEOUT_SECONDS))
                fallback_reason = (
                    f"AI profile generation timed out after {timeout_seconds}s; using the built-in fallback review profile. "
                    "If this keeps happening, increase STEAM_REVIEW_AI_TIMEOUT_SECONDS."
                )
            except ValueError as error:
                error_text = str(error or "").strip().rstrip(".")
                if error_text:
                    fallback_reason = f"AI profile generation unavailable; {error_text}."
                else:
                    fallback_reason = "AI profile generation returned an invalid response; using the built-in fallback review profile."
            except requests.exceptions.RequestException as error:
                error_text = str(error or "").strip().rstrip(".")
                if error_text:
                    fallback_reason = f"AI profile generation unavailable; {error_text}."
                else:
                    fallback_reason = "AI profile generation unavailable; could not reach Ollama endpoint."
            except (TypeError, json.JSONDecodeError) as error:
                error_text = str(error or "").strip().rstrip(".")
                if error_text:
                    fallback_reason = (
                        f"AI profile generation returned an invalid response; {error_text}."
                    )
                else:
                    fallback_reason = "AI profile generation returned an invalid response; using the built-in fallback review profile."

        if ai_review_profile:
            category_count = len(ai_review_profile.get("category_list", []))
            if used_profile_correction and detected_genre:
                detection_status_message = (
                    f"AI-generated review profile corrected for quality/genre alignment ({detected_genre})."
                )
            elif used_profile_correction:
                detection_status_message = (
                    f"AI-generated review profile corrected for quality/genre alignment with {category_count} categories."
                )
            elif detected_genre:
                detection_status_message = f"AI-generated review profile ready for {detected_genre}."
            else:
                detection_status_message = f"AI-generated review profile ready with {category_count} categories."
        else:
            detection_status_message = "Using the built-in fallback review profile."
            if fallback_reason:
                detection_status_message = f"{detection_status_message} {fallback_reason}"
            if LOCAL_AI_ASSIST_ENABLED:
                detection_status_message = (
                    f"{detection_status_message} Click Retry AI Profile to try generation again."
                )

        app.after(
            0,
            lambda: complete_genre_detection(
                session_token,
                detected_genre,
                store_genres,
                store_categories,
                detection_status_message,
                description_text=description_text,
                image_url=image_url,
                image_bytes=image_bytes,
                image_error=image_error,
                ai_review_profile=ai_review_profile,
            ),
        )
    except requests.exceptions.Timeout:
        app.after(
            0,
            lambda: complete_genre_detection(
                session_token,
                "",
                [],
                [],
                "Genre auto-detect unavailable.",
                "Steam Store request timed out.",
            ),
        )
    except requests.exceptions.RequestException:
        app.after(
            0,
            lambda: complete_genre_detection(
                session_token,
                "",
                [],
                [],
                "Genre auto-detect unavailable.",
                "Could not reach Steam Store API.",
            ),
        )
    except (ValueError, json.JSONDecodeError, KeyError, TypeError):
        app.after(
            0,
            lambda: complete_genre_detection(
                session_token,
                "",
                [],
                [],
                "Genre auto-detect unavailable.",
                "Steam Store returned unexpected data.",
            ),
        )

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

    response = request_with_retry("GET", url, params=params, timeout=10)
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
        summary_response = request_with_retry(
            "GET",
            summary_url,
            params=summary_params,
            timeout=10,
        )
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
    """Show the login screen."""
    global current_screen, current_review_step, ai_status_summary_label, ai_status_refresh_btn
    global ai_status_setup_btn, ai_status_copy_pull_btn
    current_screen = "login"
    current_review_step = ""
    ai_status_summary_label = None
    ai_status_refresh_btn = None
    ai_status_setup_btn = None
    ai_status_copy_pull_btn = None
    apply_main_window_size(WINDOW_WIDTH, LOGIN_WINDOW_HEIGHT)
    ensure_auto_update_check()
    
    # Clear current content
    for widget in main_frame.winfo_children():
        widget.destroy()
    
    # Login screen
    login_frame = ctk.CTkFrame(main_frame, fg_color=STEAM_PANEL)
    login_frame.pack(fill="both", expand=True, padx=12, pady=12)

    top_actions_frame = ctk.CTkFrame(login_frame, fg_color="transparent")
    top_actions_frame.pack(fill="x", padx=10, pady=(8, 0))
    about_btn = ctk.CTkButton(
        top_actions_frame,
        text="About",
        command=show_about_dialog,
        fg_color="#2f556f",
        width=90,
        height=30
    )
    about_btn.pack(side="right")
    set_about_button_widget(about_btn)

    content_frame = ctk.CTkScrollableFrame(login_frame, fg_color="transparent")
    content_frame.pack(fill="both", expand=True, padx=8, pady=(8, 10))
    
    login_title = ctk.CTkLabel(content_frame, text="Steam Review Generator", font=("Arial", 28, "bold"), text_color=STEAM_ACCENT)
    login_title.pack(pady=(30, 10))
    
    subtitle = ctk.CTkLabel(content_frame, text="Login with your Steam credentials", font=("Arial", 16), text_color="#cccccc")
    subtitle.pack(pady=(0, 30))

    # Keep instructions and form inside a scrollable body for short screens.
    instructions_frame = ctk.CTkFrame(content_frame, fg_color=STEAM_BG)
    instructions_frame.pack(fill="x", padx=16, pady=(0, 14))

    instructions_title = ctk.CTkLabel(instructions_frame, text="How to get your credentials:", font=("Arial", 14, "bold"), text_color=STEAM_ACCENT)
    instructions_title.pack(pady=(15, 10))

    instructions_text = tk.Text(
        instructions_frame,
        height=8,
        bg=STEAM_BG,
        fg="#cccccc",
        font=("Arial", 11),
        wrap="word",
        borderwidth=0,
        highlightthickness=0
    )
    instructions_text.pack(fill="x", padx=12, pady=(0, 15))

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
    instructions_text.config(state="disabled", cursor="arrow")

    form_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    form_frame.pack(fill="x", padx=18, pady=(0, 10))
    
    # API Key input
    api_key_label = ctk.CTkLabel(form_frame, text="Steam API Key:", font=("Arial", 14))
    api_key_label.pack(anchor="w", pady=(12, 5))
    global steam_api_key_entry
    steam_api_key_entry = ctk.CTkEntry(form_frame, placeholder_text="Enter your Steam API key...")
    steam_api_key_entry.pack(fill="x", pady=(0, 10))
    steam_api_key_entry.bind("<KeyRelease>", on_login_input_change)

    global api_key_hint_label
    api_key_hint_label = ctk.CTkLabel(form_frame, text="", font=("Arial", 11), text_color="#888")
    api_key_hint_label.pack(anchor="w", pady=(0, 8))
    
    # Steam ID input
    steam_id_label = ctk.CTkLabel(form_frame, text="Steam ID (64-bit):", font=("Arial", 14))
    steam_id_label.pack(anchor="w", pady=(8, 5))
    global steam_id_entry
    steam_id_entry = ctk.CTkEntry(form_frame, placeholder_text="Enter your 64-bit Steam ID...")
    steam_id_entry.pack(fill="x", pady=(0, 20))
    steam_id_entry.bind("<KeyRelease>", on_login_input_change)

    global steam_id_hint_label
    steam_id_hint_label = ctk.CTkLabel(form_frame, text="", font=("Arial", 11), text_color="#888")
    steam_id_hint_label.pack(anchor="w", pady=(0, 12))
    
    # Login button
    global login_btn
    login_btn = ctk.CTkButton(form_frame, text="Login & Fetch Games", command=login_and_fetch, fg_color=STEAM_ACCENT, height=40)
    login_btn.pack(fill="x", pady=(10, 12))
    
    # Status label
    global status_label
    status_label = ctk.CTkLabel(form_frame, text="", font=("Arial", 12))
    status_label.pack(anchor="w", pady=(0, 8))

    # Login progress indicator (shown only during background fetch)
    global login_progress
    login_progress = ctk.CTkProgressBar(form_frame, mode="indeterminate")
    
    # Load saved credentials
    saved_api_key, saved_steam_id = load_credentials()
    if saved_api_key:
        steam_api_key_entry.insert(0, saved_api_key)
    if saved_steam_id:
        steam_id_entry.insert(0, saved_steam_id)

    on_login_input_change()
    add_version_footer(login_frame)

def show_games_screen():
    """Show the games selection screen."""
    global current_screen, preview, sort_mode_var, selected_game_index, current_review_step
    global ai_status_summary_label, ai_status_refresh_btn, ai_status_setup_btn, ai_status_copy_pull_btn
    current_screen = "games"
    current_review_step = ""
    ai_status_summary_label = None
    ai_status_refresh_btn = None
    ai_status_setup_btn = None
    ai_status_copy_pull_btn = None
    apply_main_window_size(WINDOW_WIDTH, WINDOW_HEIGHT)
    selected_game_index = -1
    ensure_auto_update_check()
    
    # Destroy preview textbox if it exists
    if preview:
        preview.destroy()
        preview = None
    
    # Clear current content
    for widget in main_frame.winfo_children():
        widget.destroy()
    # ensure UI refresh before rebuilding
    app.update()    
    # Games screen
    games_frame = ctk.CTkFrame(main_frame, fg_color=STEAM_PANEL)
    games_frame.pack(fill="both", expand=True, padx=12, pady=12)
    
    # Title at top
    games_title = ctk.CTkLabel(games_frame, text="Select a Game to Review", font=("Arial", 24, "bold"), text_color=STEAM_ACCENT)
    games_title.pack(pady=(0, 15), anchor="w", padx=20)
    
    # Header with username and logout
    header_frame = ctk.CTkFrame(games_frame, fg_color="transparent")
    header_frame.pack(fill="x", pady=(0, 15), padx=20)

    header_actions = ctk.CTkFrame(header_frame, fg_color="transparent")
    header_actions.pack(side="right")

    logout_btn = ctk.CTkButton(header_actions, text="Logout", command=logout, fg_color="#ff5555", width=80, height=30)
    logout_btn.pack(side="right")

    about_btn = ctk.CTkButton(header_actions, text="About", command=show_about_dialog, fg_color="#2f556f", width=80, height=30)
    about_btn.pack(side="right", padx=(0, 8))
    set_about_button_widget(about_btn)
    
    username_label = ctk.CTkLabel(header_frame, text=f"Logged in as: {steam_username}", font=("Arial", 12), text_color="#cccccc")
    username_label.pack(side="left", fill="x", expand=True, padx=(0, 12), anchor="w")

    # Search and sort controls
    controls_frame = ctk.CTkFrame(games_frame, fg_color="transparent")
    controls_frame.pack(fill="x", pady=(0, 10), padx=20)

    global search_entry
    search_entry = ctk.CTkEntry(controls_frame, placeholder_text="Type to search games...")
    search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
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
    
    # Canvas-based virtual game list — only visible rows are drawn, no per-row widgets
    global game_virtual_canvas, game_hover_index
    game_hover_index = -1
    _list_wrapper = tk.Frame(games_frame, bg=STEAM_PANEL)
    _list_wrapper.pack(pady=(0, 20), padx=(20, 0), fill="both", expand=True)

    _game_vscrollbar = ctk.CTkScrollbar(_list_wrapper, command=_on_game_scrollbar_cmd)
    _game_vscrollbar.pack(side="right", fill="y", padx=(0, 4))

    game_virtual_canvas = tk.Canvas(_list_wrapper, bg=STEAM_PANEL, highlightthickness=0, cursor="hand2", takefocus=1)
    game_virtual_canvas.configure(yscrollcommand=_game_vscrollbar.set)
    game_virtual_canvas.pack(side="left", fill="both", expand=True)

    game_virtual_canvas.bind("<Configure>", on_game_canvas_configure)
    game_virtual_canvas.bind("<MouseWheel>", on_game_canvas_scroll)
    game_virtual_canvas.bind("<Button-4>", on_game_canvas_scroll)
    game_virtual_canvas.bind("<Button-5>", on_game_canvas_scroll)
    game_virtual_canvas.bind("<Motion>", on_game_canvas_motion)
    game_virtual_canvas.bind("<Leave>", on_game_canvas_leave)
    game_virtual_canvas.bind("<Button-1>", on_game_canvas_click)

    # App-level bindings so Up/Down/Return work regardless of which widget is focused.
    def _guard_down(e):
        if current_screen == "games" and current_review_step == "":
            return on_search_down(e)
    def _guard_up(e):
        if current_screen == "games" and current_review_step == "":
            return on_search_up(e)
    def _guard_enter(e):
        if current_screen == "games" and current_review_step == "":
            return on_search_enter(e)

    def _is_descendant_widget(widget, ancestor):
        """Return True if widget is ancestor or a descendant of ancestor."""
        while widget:
            if widget == ancestor:
                return True
            try:
                parent_name = widget.winfo_parent()
            except Exception:
                return False
            if not parent_name:
                return False
            try:
                widget = widget.nametowidget(parent_name)
            except Exception:
                return False
        return False

    def _defocus_search_entry(e):
        """Move focus away from search entry when clicking elsewhere on games screen."""
        if current_screen != "games" or current_review_step != "":
            return
        if search_entry and search_entry.winfo_exists() and _is_descendant_widget(e.widget, search_entry):
            return
        if game_virtual_canvas and game_virtual_canvas.winfo_exists():
            game_virtual_canvas.focus_set()
        else:
            app.focus_set()

    app.bind_all("<Down>", _guard_down, add="+")
    app.bind_all("<Up>", _guard_up, add="+")
    app.bind_all("<Return>", _guard_enter, add="+")
    app.bind_all("<Button-1>", _defocus_search_entry, add="+")

    # Clicking anywhere on the list wrapper (between rows, scrollbar area) defocuses the search entry.
    _list_wrapper.bind("<Button-1>", lambda e: game_virtual_canvas.focus_set(), add="+")

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

def _game_canvas_index_at(canvas_y):
    """Convert a canvas-relative y coordinate to a game_virtual_data index."""
    if not game_virtual_data or not game_virtual_canvas or not game_virtual_canvas.winfo_exists():
        return -1
    total_height = len(game_virtual_data) * GAME_ROW_HEIGHT
    yview = game_virtual_canvas.yview()
    y_abs = yview[0] * total_height + canvas_y
    idx = int(y_abs / GAME_ROW_HEIGHT)
    return idx if 0 <= idx < len(game_virtual_data) else -1

def draw_game_canvas_rows():
    """Redraw only the rows currently visible in the game canvas viewport."""
    global _game_canvas_redraw_after
    _game_canvas_redraw_after = None
    if not game_virtual_canvas or not game_virtual_canvas.winfo_exists():
        return

    canvas_width = game_virtual_canvas.winfo_width()
    canvas_height = game_virtual_canvas.winfo_height()
    if canvas_width <= 1 or canvas_height <= 1:
        return

    game_virtual_canvas.delete("all")

    total_items = len(game_virtual_data)
    if total_items == 0:
        return

    total_height = total_items * GAME_ROW_HEIGHT
    game_virtual_canvas.configure(scrollregion=(0, 0, canvas_width, total_height))

    yview = game_virtual_canvas.yview()
    y_abs_top = yview[0] * total_height
    y_abs_bottom = min(yview[1] * total_height, total_height)

    first_idx = max(0, int(y_abs_top / GAME_ROW_HEIGHT) - 1)
    last_idx = min(total_items, int(y_abs_bottom / GAME_ROW_HEIGHT) + 2)

    for i in range(first_idx, last_idx):
        y_top = i * GAME_ROW_HEIGHT + 2
        y_bot = (i + 1) * GAME_ROW_HEIGHT - 2
        y_mid = i * GAME_ROW_HEIGHT + GAME_ROW_HEIGHT // 2

        if i == selected_game_index:
            bg, fg = "#264c66", "#f2f8fc"
        elif i == game_hover_index:
            bg, fg = "#1d4a6b", "#f2f8fc"
        else:
            bg, fg = STEAM_PANEL, "#cccccc"

        game_virtual_canvas.create_rectangle(
            5, y_top, canvas_width - 5, y_bot,
            fill=bg, outline=""
        )
        game_virtual_canvas.create_text(
            16, y_mid,
            text=game_virtual_data[i],
            fill=fg,
            font=("Arial", 11),
            anchor="w"
        )

def on_game_canvas_configure(event):
    """Update scrollregion on canvas resize and schedule a redraw."""
    global _game_canvas_redraw_after
    total_height = len(game_virtual_data) * GAME_ROW_HEIGHT
    game_virtual_canvas.configure(
        scrollregion=(0, 0, event.width, max(total_height, event.height))
    )
    if _game_canvas_redraw_after:
        app.after_cancel(_game_canvas_redraw_after)
    _game_canvas_redraw_after = app.after(30, draw_game_canvas_rows)

def _on_game_scrollbar_cmd(*args):
    """Route scrollbar drag to canvas and redraw visible rows."""
    if game_virtual_canvas and game_virtual_canvas.winfo_exists():
        game_virtual_canvas.yview(*args)
        draw_game_canvas_rows()

def on_game_canvas_scroll(event):
    """Handle mouse-wheel scrolling on the game canvas."""
    if not game_virtual_canvas or not game_virtual_canvas.winfo_exists():
        return
    if event.delta:
        game_virtual_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    elif event.num == 4:
        game_virtual_canvas.yview_scroll(-3, "units")
    elif event.num == 5:
        game_virtual_canvas.yview_scroll(3, "units")
    draw_game_canvas_rows()

def on_game_canvas_motion(event):
    """Update hover highlight as the mouse moves across game rows."""
    global game_hover_index
    idx = _game_canvas_index_at(event.y)
    if idx != game_hover_index:
        game_hover_index = idx
        draw_game_canvas_rows()

def on_game_canvas_leave(event):
    """Clear hover highlight when the mouse exits the canvas."""
    global game_hover_index
    if game_hover_index != -1:
        game_hover_index = -1
        draw_game_canvas_rows()

def on_game_canvas_click(event):
    """Start a review for the clicked game row."""
    idx = _game_canvas_index_at(event.y)
    if game_virtual_canvas and game_virtual_canvas.winfo_exists():
        game_virtual_canvas.focus_set()
    if 0 <= idx < len(game_virtual_data):
        start_review(game_virtual_data[idx])

def update_selected_game_highlight():
    """Redraw game canvas to reflect the current keyboard selection."""
    if game_virtual_canvas and game_virtual_canvas.winfo_exists():
        draw_game_canvas_rows()

def on_sort_change(choice):
    """Refresh game list after changing sort mode."""
    search_text = search_entry.get() if search_entry and search_entry.winfo_exists() else ""
    populate_game_list(search_text)

def move_game_selection(step):
    """Move keyboard selection up/down within visible games."""
    global selected_game_index
    if not game_virtual_data:
        selected_game_index = -1
        return

    if selected_game_index < 0:
        selected_game_index = 0 if step >= 0 else len(game_virtual_data) - 1
    else:
        selected_game_index = max(0, min(len(game_virtual_data) - 1, selected_game_index + step))

    update_selected_game_highlight()

    if game_virtual_canvas and game_virtual_canvas.winfo_exists():
        total_height = len(game_virtual_data) * GAME_ROW_HEIGHT
        canvas_height = game_virtual_canvas.winfo_height()

        if total_height > canvas_height:
            yview = game_virtual_canvas.yview()
            view_top = yview[0] * total_height
            view_bottom = yview[1] * total_height

            row_top = selected_game_index * GAME_ROW_HEIGHT
            row_bottom = row_top + GAME_ROW_HEIGHT

            if row_top < view_top:
                # Row scrolled above viewport — bring it to the top edge
                new_fraction = row_top / total_height
                game_virtual_canvas.yview_moveto(max(0.0, new_fraction))
            elif row_bottom > view_bottom:
                # Row scrolled below viewport — bring it to the bottom edge
                new_fraction = (row_bottom - canvas_height) / total_height
                game_virtual_canvas.yview_moveto(max(0.0, min(1.0, new_fraction)))

        draw_game_canvas_rows()

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
    if not game_virtual_data:
        return "break"

    index = selected_game_index if selected_game_index >= 0 else 0
    if 0 <= index < len(game_virtual_data):
        start_review(game_virtual_data[index])
    return "break"

def populate_game_list(search_filter=""):
    """Populate the virtual game canvas with the filtered and sorted game list."""
    global game_virtual_data, selected_game_index, game_hover_index

    sort_mode = sort_mode_var.get() if sort_mode_var else "A-Z"
    sorted_games = get_sorted_games(sort_mode)

    search_lower = search_filter.lower()
    game_virtual_data = [
        g.get('name', '')
        for g in sorted_games
        if not search_filter or search_lower in g.get('name', '').lower()
    ]

    shown_count = len(game_virtual_data)
    total_count = len(sorted_games)

    selected_game_index = 0 if shown_count > 0 else -1
    game_hover_index = -1

    if game_virtual_canvas and game_virtual_canvas.winfo_exists():
        if search_filter:
            game_virtual_canvas.yview_moveto(0)
        draw_game_canvas_rows()

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
    global review_session_token
    selected_game = game_name
    current_index = 0
    vars_dict = {}
    review_session_token += 1
    session_token = review_session_token
    set_active_fallback_review_profile()
    
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
        'playtime': game_playtime,
        'detected_genre': '',
        'store_genres': [],
        'store_categories': [],
        'genre_detection_status': 'Generating AI review profile from Steam tags...',
        'review_profile_loading_started_at': time.time(),
        'genre_detection_error': '',
        'store_description': '',
        'store_image_url': '',
        'store_image_bytes': b'',
        'store_image_error': '',
        'ai_review_profile': {},
        'review_profile_loading': bool(game_appid),
        'review_profile_ready': not bool(game_appid),
        'review_profile_retry_count': 0,
    }

    if game_appid:
        threading.Thread(
            target=detect_game_genre_worker,
            args=(game_appid, game_name, session_token),
            daemon=True,
        ).start()
    else:
        current_game_data['genre_detection_status'] = 'Genre auto-detect unavailable.'
        current_game_data['genre_detection_error'] = 'No Steam AppID was found for this game.'
        current_game_data['review_profile_loading'] = False
        current_game_data['review_profile_ready'] = True
    
    # Create main review frame
    global title, container
    
    # Header with game info
    header_frame = ctk.CTkFrame(main_frame, fg_color=STEAM_PANEL)
    header_frame.pack(fill="x", padx=20, pady=(12, 8))
    
    # Game actions row
    top_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
    top_frame.pack(fill="x", padx=15, pady=(8, 4))
    
    back_btn = ctk.CTkButton(top_frame, text="← Back", command=show_games_screen, width=80, height=30, fg_color="#666", hover_color="#888")
    back_btn.pack(side="left")

    about_btn = ctk.CTkButton(top_frame, text="About", command=show_about_dialog, width=80, height=30, fg_color="#2f556f")
    about_btn.pack(side="right")
    set_about_button_widget(about_btn)
    
    title = ctk.CTkLabel(
        header_frame,
        text=f"Reviewing: {game_name}",
        font=("Arial", 18, "bold"),
        text_color=STEAM_ACCENT,
        anchor="w",
        justify="left"
    )
    title.pack(fill="x", padx=15, pady=(0, 2))
    
    # Game stats
    hours = game_playtime // 60
    stats_text = f"⏱️ {hours}h playtime"
    stats_label = ctk.CTkLabel(header_frame, text=stats_text, font=("Arial", 11), text_color="#888")
    stats_label.pack(anchor="w", padx=15, pady=(0, 6))

    # Review container
    container = ctk.CTkFrame(main_frame, fg_color="transparent")
    container.pack(fill="both", expand=True, padx=20, pady=(0, 12))
    
    # Show a quick game summary before starting ratings
    show_game_summary()
    add_version_footer(main_frame)

def show_game_summary():
    """Show selected game metadata before starting category ratings."""
    global current_review_step, ai_status_summary_label, ai_status_refresh_btn
    global ai_status_setup_btn, ai_status_copy_pull_btn
    current_review_step = "summary"
    ai_status_summary_label = None
    ai_status_refresh_btn = None
    ai_status_setup_btn = None
    ai_status_copy_pull_btn = None

    for widget in container.winfo_children():
        widget.destroy()

    game_name = current_game_data.get('name', 'Unknown Game')
    game_appid = current_game_data.get('appid', 'Unknown')
    playtime_minutes = current_game_data.get('playtime', 0)
    playtime_hours = playtime_minutes // 60
    detected_genre = current_game_data.get('detected_genre', '')
    store_genres = current_game_data.get('store_genres', [])
    store_categories = current_game_data.get('store_categories', [])
    detection_status = current_game_data.get('genre_detection_status', '')
    detection_error = current_game_data.get('genre_detection_error', '')
    ai_review_profile = current_game_data.get('ai_review_profile', {})
    review_profile_loading = bool(current_game_data.get('review_profile_loading', False))
    review_profile_retry_count = int(current_game_data.get('review_profile_retry_count', 0) or 0)
    store_description = current_game_data.get('store_description', '')
    store_image_bytes = current_game_data.get('store_image_bytes', b'')
    store_image_url = current_game_data.get('store_image_url', '')
    store_image_error = current_game_data.get('store_image_error', '')

    detected_genre_line = ""
    status_line = ""
    profile_line = ""

    if detected_genre:
        detected_genre_line = f"Detected genre: {detected_genre}"

    if detection_error:
        status_line = f"Review profile: {detection_error}"
    else:
        status_line = detection_status or "Generating review profile from Steam tags..."

    ai_profile_categories = list(ai_review_profile.get('category_list', []) or [])
    can_retry_ai_profile = bool(
        LOCAL_AI_ASSIST_ENABLED
        and game_appid
        and not review_profile_loading
        and not ai_profile_categories
    )
    if ai_profile_categories:
        profile_line = f"AI generated {len(ai_profile_categories)} review categories and weights automatically."
    elif active_category_list:
        profile_line = f"Using the built-in fallback profile with {len(active_category_list)} review categories."

    store_genre_line = ""
    if store_genres:
        preview_genres = ", ".join(store_genres[:4])
        store_genre_line = f"Steam genres: {preview_genres}"

    store_category_line = ""
    if store_categories:
        preview_categories = ", ".join(store_categories[:4])
        store_category_line = f"Steam categories: {preview_categories}"

    status_block = f"{status_line}\n" if status_line else ""
    detected_genre_block = f"{detected_genre_line}\n" if detected_genre_line else ""
    profile_block = f"{profile_line}\n" if profile_line else ""
    store_genre_block = f"{store_genre_line}\n" if store_genre_line else ""
    store_category_block = f"{store_category_line}\n" if store_category_line else ""

    title.configure(text=f"Reviewing: {game_name}")

    summary_wraplength = container.winfo_width() - 90
    if summary_wraplength <= 0:
        summary_wraplength = 420
    summary_wraplength = max(320, min(620, summary_wraplength))

    summary_frame = ctk.CTkFrame(container, fg_color=STEAM_PANEL, corner_radius=8)
    summary_frame.pack(fill="both", expand=True, pady=6)

    summary_title = ctk.CTkLabel(
        summary_frame,
        text="Ready to review this game?",
        font=("Arial", 18, "bold"),
        text_color=STEAM_ACCENT
    )
    summary_title.pack(pady=(16, 12), padx=20, anchor="w")

    content_frame = ctk.CTkScrollableFrame(summary_frame, fg_color="transparent")
    content_frame.pack(fill="both", expand=True, padx=20, pady=(0, 12))

    if store_image_bytes and Image is not None:
        try:
            pil_image = Image.open(io.BytesIO(store_image_bytes)).convert("RGB")
            ratio = pil_image.height / pil_image.width if pil_image.width else 0.47
            image_width = max(260, min(SUMMARY_IMAGE_WIDTH, summary_wraplength))
            image_height = max(160, int(image_width * ratio))
            cover_image = ctk.CTkImage(
                light_image=pil_image,
                dark_image=pil_image,
                size=(image_width, image_height),
            )
            cover_label = ctk.CTkLabel(content_frame, text="", image=cover_image)
            cover_label.image = cover_image
            cover_label.pack(anchor="w", pady=(0, 12))
        except Exception:
            pass
    elif store_image_url and Image is None:
        no_pil_label = ctk.CTkLabel(
            content_frame,
            text="Game image available, but Pillow is not installed in this Python environment.",
            font=("Arial", 11),
            text_color="#ffb26b",
            justify="left",
            anchor="w",
            wraplength=summary_wraplength,
        )
        no_pil_label.pack(fill="x", pady=(0, 8))

    if store_image_error:
        image_error_label = ctk.CTkLabel(
            content_frame,
            text=store_image_error,
            font=("Arial", 11),
            text_color="#ff9f7a",
            justify="left",
            anchor="w",
            wraplength=summary_wraplength,
        )
        image_error_label.pack(fill="x", pady=(0, 8))

    next_step_line = (
        "Generating your review profile now. Start Review will unlock automatically when ready."
        if review_profile_loading
        else "Start the review now, or retry AI profile generation for a fresh attempt."
        if can_retry_ai_profile
        else "Start the review when ready."
    )

    retry_attempt_line = ""
    if can_retry_ai_profile and review_profile_retry_count > 0:
        retry_attempt_line = f"AI retry attempts in this session: {review_profile_retry_count}\n"

    details_text = (
        f"Game: {game_name}\n"
        f"AppID: {game_appid}\n"
        f"Playtime: {playtime_hours}h ({playtime_minutes} minutes)\n\n"
        f"{status_block}"
        f"{detected_genre_block}"
        f"{profile_block}"
        f"{store_genre_block}"
        f"{store_category_block}"
        f"{retry_attempt_line}"
        f"{next_step_line}"
        " The app will score the final rating using the generated category weights automatically."
    )
    details_label = ctk.CTkLabel(
        content_frame,
        text=details_text,
        font=("Arial", 12),
        justify="left",
        anchor="w",
        wraplength=summary_wraplength,
        text_color="#d2dbe2"
    )
    details_label.pack(fill="x", pady=(0, 12), anchor="w")

    if review_profile_loading:
        loading_frame = ctk.CTkFrame(content_frame, fg_color="#20384e", corner_radius=8)
        loading_frame.pack(fill="x", pady=(0, 12), anchor="w")

        loading_label = ctk.CTkLabel(
            loading_frame,
            text="Generating AI review profile...",
            font=("Arial", 12, "bold"),
            text_color="#d2e7ff",
            anchor="w",
            justify="left",
        )
        loading_label.pack(fill="x", padx=12, pady=(10, 4))

        loading_started_at = float(
            current_game_data.get("review_profile_loading_started_at") or time.time()
        )

        loading_timer_label = ctk.CTkLabel(
            loading_frame,
            text="⏱ 0s",
            font=("Arial", 11),
            text_color="#b8d4ea",
            anchor="w",
            justify="left",
        )
        loading_timer_label.pack(fill="x", padx=12, pady=(0, 8))

        loading_progress = ctk.CTkProgressBar(loading_frame, mode="indeterminate")
        loading_progress.pack(fill="x", padx=12, pady=(0, 10))
        loading_progress.start()

        def _tick_loading_timer():
            if not loading_timer_label.winfo_exists():
                return
            if not current_game_data.get("review_profile_loading", False):
                return
            elapsed = int(time.time() - loading_started_at)
            loading_timer_label.configure(text=f"⏱ {elapsed}s")
            app.after(1000, _tick_loading_timer)

        app.after(1000, _tick_loading_timer)

    ai_status_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    ai_status_frame.pack(fill="x", pady=(0, 10), anchor="w")

    ai_status_summary_label = ctk.CTkLabel(
        ai_status_frame,
        text="",
        font=("Arial", 11),
        text_color="#9fb6c4",
        justify="left",
        anchor="w",
        wraplength=summary_wraplength,
    )
    ai_status_summary_label.pack(fill="x", anchor="w", pady=(0, 6))

    ai_status_actions_frame = ctk.CTkFrame(ai_status_frame, fg_color="transparent")
    ai_status_actions_frame.pack(fill="x", anchor="w")

    ai_status_setup_btn = ctk.CTkButton(
        ai_status_actions_frame,
        text="Setup Ollama",
        width=130,
        height=28,
        command=on_setup_ollama_click,
        fg_color="#2f556f",
        hover_color="#3a6684",
    )

    ai_status_copy_pull_btn = ctk.CTkButton(
        ai_status_actions_frame,
        text="Copy Pull Cmd",
        width=122,
        height=28,
        command=on_copy_pull_command_click,
        fg_color="#3f5f2c",
        hover_color="#4f7438",
    )
    ai_status_copy_pull_btn._grid_hidden = True

    ai_status_refresh_btn = ctk.CTkButton(
        ai_status_actions_frame,
        text="Refresh AI Status",
        width=145,
        height=28,
        command=on_refresh_ai_status_click,
        fg_color="#2f556f",
        hover_color="#3a6684",
    )

    bind_responsive_button_grid(
        ai_status_actions_frame,
        [ai_status_setup_btn, ai_status_copy_pull_btn, ai_status_refresh_btn],
        expanded_columns=3,
        breakpoint=760,
    )

    update_ai_status_summary_label(review_session_token)
    refresh_ai_service_status_async(review_session_token)

    if store_description:
        description_title = ctk.CTkLabel(
            content_frame,
            text="Game Description",
            font=("Arial", 13, "bold"),
            text_color=STEAM_ACCENT,
            anchor="w",
            justify="left",
        )
        description_title.pack(fill="x", pady=(4, 6))

        description_label = ctk.CTkLabel(
            content_frame,
            text=store_description,
            font=("Arial", 12),
            text_color="#d2dbe2",
            justify="left",
            anchor="w",
            wraplength=summary_wraplength,
        )
        description_label.pack(fill="x", pady=(0, 8))

    actions_frame = ctk.CTkFrame(summary_frame, fg_color="transparent")
    actions_frame.pack(fill="x", padx=20, pady=(0, 14))

    back_btn = ctk.CTkButton(
        actions_frame,
        text="Choose Another Game",
        command=show_games_screen,
        fg_color="#555",
        hover_color="#666"
    )

    start_btn = ctk.CTkButton(
        actions_frame,
        text="Start Review",
        command=start_detected_rating_flow,
        fg_color=STEAM_ACCENT
    )

    action_buttons = [back_btn]
    if can_retry_ai_profile:
        retry_btn = ctk.CTkButton(
            actions_frame,
            text="Retry AI Profile",
            command=retry_ai_review_profile_generation,
            fg_color="#2f556f",
            hover_color="#3a6684",
        )
        action_buttons.append(retry_btn)

    if review_profile_loading:
        start_btn.configure(text="Generating Review Profile...", state="disabled")

    action_buttons.append(start_btn)

    bind_responsive_button_grid(
        actions_frame,
        action_buttons,
        expanded_columns=min(3, max(1, len(action_buttons))),
        breakpoint=620
    )


def slide_frame(new_frame):
    new_frame.place(x=750, y=0, relwidth=1, relheight=1)
    def animate(pos):
        if pos <= 0:
            new_frame.place(x=0, y=0)
            return
        new_frame.place(x=pos, y=0)
        app.after(10, lambda: animate(pos-30))
    animate(750)

def ensure_category_shortcuts_bound():
    """Bind category-rating keyboard shortcuts once for the app lifetime."""
    global category_shortcuts_bound
    if category_shortcuts_bound:
        return

    for digit in "0123456789":
        app.bind_all(f"<Key-{digit}>", on_category_digit_shortcut, add="+")
        app.bind_all(f"<KP_{digit}>", on_category_digit_shortcut, add="+")
    app.bind_all("<Return>", on_category_enter_shortcut, add="+")
    app.bind_all("<KP_Enter>", on_category_enter_shortcut, add="+")
    category_shortcuts_bound = True

def set_category_option_value(option_label):
    """Select an option label for the currently visible category step."""
    if current_review_step != "category":
        return
    if not active_category_list or current_index >= len(active_category_list):
        return

    category_name = active_category_list[current_index]
    selected_var = vars_dict.get(category_name)
    if selected_var is None:
        selected_var = ctk.StringVar(value="")
        vars_dict[category_name] = selected_var

    selected_var.set(str(option_label or ""))
    update_nav_state()

def set_category_option_hover(option_label, hovered):
    """Apply hover highlight to unselected category option rows."""
    if current_review_step != "category":
        return
    if not active_category_list or current_index >= len(active_category_list):
        return

    option_row = category_option_rows.get(option_label)
    if not option_row or not option_row.winfo_exists():
        return

    category_name = active_category_list[current_index]
    selected_value = vars_dict.get(category_name).get() if category_name in vars_dict else ""
    if option_label == selected_value:
        return

    option_row.configure(fg_color=CATEGORY_OPTION_ROW_HOVER if hovered else CATEGORY_OPTION_ROW_DEFAULT)

def refresh_category_option_styles():
    """Refresh option row/button styling to reflect the current selection."""
    if current_review_step != "category":
        return
    if not active_category_list or current_index >= len(active_category_list):
        return

    category_name = active_category_list[current_index]
    selected_value = vars_dict.get(category_name).get() if category_name in vars_dict else ""

    for option_label, option_row in category_option_rows.items():
        if not option_row or not option_row.winfo_exists():
            continue
        option_row.configure(
            fg_color=CATEGORY_OPTION_ROW_SELECTED if option_label == selected_value else CATEGORY_OPTION_ROW_DEFAULT
        )

    for option_label, option_button in category_option_buttons.items():
        if not option_button or not option_button.winfo_exists():
            continue
        option_button.configure(text_color="#f2f8fc" if option_label == selected_value else "#d2dbe2")

def _extract_shortcut_score(event):
    """Translate number key events into 1-10 score values (0 maps to 10)."""
    key_name = str(getattr(event, "keysym", "") or "")
    if key_name.isdigit():
        return 10 if key_name == "0" else int(key_name)

    if key_name.startswith("KP_"):
        keypad_digit = key_name[3:]
        if keypad_digit.isdigit():
            return 10 if keypad_digit == "0" else int(keypad_digit)

    typed_char = str(getattr(event, "char", "") or "")
    if typed_char.isdigit():
        return 10 if typed_char == "0" else int(typed_char)
    return None

def on_category_digit_shortcut(event):
    """Select a rating using number keys while category step is visible."""
    if current_review_step != "category":
        return

    shortcut_score = _extract_shortcut_score(event)
    if shortcut_score is None:
        return

    option_label = category_score_shortcuts.get(shortcut_score)
    if option_label:
        set_category_option_value(option_label)
    return "break"

def on_category_enter_shortcut(event):
    """Advance to next category step on Enter while rating flow is visible."""
    if current_review_step != "category":
        return
    go_next_category()
    return "break"

def show_category():
    global current_index, new_review_btn, next_btn, prev_btn, step_label, nav_hint_label
    global current_review_step, ai_status_summary_label, ai_status_refresh_btn
    global ai_status_setup_btn, ai_status_copy_pull_btn
    global category_option_rows, category_option_buttons, category_score_shortcuts
    current_review_step = "category"
    ai_status_summary_label = None
    ai_status_refresh_btn = None
    ai_status_setup_btn = None
    ai_status_copy_pull_btn = None
    ensure_category_shortcuts_bound()

    for widget in container.winfo_children():
        widget.destroy()
    if new_review_btn:
        new_review_btn.destroy()
        new_review_btn = None

    if not active_category_list:
        set_active_fallback_review_profile()
        if not active_category_list:
            return

    if current_index >= len(active_category_list):
        generate_review()
        return

    category = active_category_list[current_index]
    options = active_categories.get(category, [])
    
    # Update title
    current = current_index + 1
    total = len(active_category_list)
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
    desc_label = ctk.CTkLabel(
        frame,
        text=f"Rate the {category.lower()} of this game",
        font=("Arial", 12),
        text_color="#aaa"
    )
    desc_label.pack(pady=(15, 10), padx=20, anchor="w")
    
    # Options frame
    options_frame = ctk.CTkScrollableFrame(frame)
    options_frame.pack(fill="both", expand=True, padx=20, pady=(0, 15))
    
    if category in vars_dict:
        var = vars_dict[category]
    else:
        var = ctk.StringVar(value="")
        vars_dict[category] = var

    category_option_rows = {}
    category_option_buttons = {}
    category_score_shortcuts = {}

    for text, val in options:
        # Create a frame for each option to style it better
        option_container = ctk.CTkFrame(options_frame, fg_color=CATEGORY_OPTION_ROW_DEFAULT, corner_radius=7)
        option_container.pack(fill="x", pady=5, padx=2)
        option_container.bind(
            "<Button-1>",
            lambda event, option_label=text: set_category_option_value(option_label),
            add="+",
        )
        option_container.bind(
            "<Enter>",
            lambda event, option_label=text: set_category_option_hover(option_label, True),
            add="+",
        )
        option_container.bind(
            "<Leave>",
            lambda event, option_label=text: set_category_option_hover(option_label, False),
            add="+",
        )
        category_option_rows[text] = option_container

        try:
            option_score = int(val)
            category_score_shortcuts[option_score] = text
        except (TypeError, ValueError):
            pass
        
        btn = ctk.CTkRadioButton(
            option_container,
            text=f"{text} ({val}/10)",
            variable=var,
            value=text,
            command=lambda option_label=text: set_category_option_value(option_label),
            height=34,
            font=("Arial", 13),
            text_color="#d2dbe2"
        )
        btn.pack(anchor="w", padx=10, pady=5)
        category_option_buttons[text] = btn

    # Navigation controls
    nav_frame = ctk.CTkFrame(container, fg_color="transparent")
    nav_frame.pack(fill="x", pady=(8, 0))

    nav_buttons_row = ctk.CTkFrame(nav_frame, fg_color="transparent")
    nav_buttons_row.pack(fill="x")

    prev_btn = ctk.CTkButton(
        nav_buttons_row,
        text="Previous",
        command=go_previous_category,
        fg_color="#555",
        hover_color="#666",
        width=110
    )
    prev_btn.pack(side="left")

    next_label = "Generate Review" if current_index == len(active_category_list) - 1 else "Next"
    next_btn = ctk.CTkButton(
        nav_buttons_row,
        text=next_label,
        command=go_next_category,
        fg_color=STEAM_ACCENT,
        width=130
    )
    next_btn.pack(side="right")

    nav_hint_label = ctk.CTkLabel(nav_frame, text="", font=("Arial", 11), text_color="#ff9999")
    nav_hint_label.pack(anchor="w", pady=(6, 0))

    update_nav_state()

def update_nav_state():
    """Enable/disable navigation controls based on current step and selection."""
    if not active_category_list or current_index >= len(active_category_list):
        return

    category = active_category_list[current_index]
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

    refresh_category_option_styles()

def go_next_category():
    """Move to the next category or generate final review on last step."""
    global current_index

    if not active_category_list or current_index >= len(active_category_list):
        return

    category = active_category_list[current_index]
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

    show_category()

def generate_review():
    global new_review_btn, latest_review_text, preview, save_status_label, current_review_step
    current_review_step = "result"

    if not active_category_list:
        set_active_fallback_review_profile()
        if not active_category_list:
            return

    selected_options = {
        category: vars_dict[category].get()
        for category in active_category_list
        if category in vars_dict
    }
    category_ratings, final_score = build_category_ratings(
        selected_options,
        active_categories,
        active_category_weights
    )

    hours = current_game_data.get('playtime', 0) // 60
    game_name = current_game_data.get('name', 'Unknown Game')
    review_text = format_review_text(
        game_name,
        hours,
        active_category_list,
        category_ratings,
        final_score,
        github_url=GITHUB_REPO_URL,
    )
    latest_review_text = review_text
    
    # Update the UI to show completion
    title.configure(text=f"Review Complete: {final_score}/10")
    
    # Clear container and show preview
    for widget in container.winfo_children():
        widget.destroy()
    
    # Create review preview frame
    preview_frame = ctk.CTkFrame(container, fg_color=STEAM_PANEL, corner_radius=8)
    preview_frame.pack(fill="both", expand=True, padx=10, pady=6)
    
    preview = ctk.CTkTextbox(preview_frame)
    preview.pack(fill="both", expand=True, padx=15, pady=12)
    preview.insert("0.0", review_text)
    preview.configure(state="disabled")  # Make read-only
    
    # Copy to clipboard
    pyperclip.copy(review_text)
    
    # Create footer frame with separate rows so action buttons are never clipped.
    buttons_frame = ctk.CTkFrame(preview_frame, fg_color="transparent")
    buttons_frame.pack(fill="x", padx=15, pady=(0, 10))

    status_row = ctk.CTkFrame(buttons_frame, fg_color="transparent")
    status_row.pack(fill="x", pady=(0, 6))

    copy_label = ctk.CTkLabel(status_row, text="✓ Review copied to clipboard!", font=("Arial", 10), text_color="#00ff00")
    copy_label.pack(side="left", padx=10)

    save_status_label = ctk.CTkLabel(status_row, text="", font=("Arial", 10), text_color="#9fb6c4")
    save_status_label.pack(side="left", padx=(8, 0))

    primary_actions_row = ctk.CTkFrame(buttons_frame, fg_color="transparent")
    primary_actions_row.pack(fill="x", pady=(0, 6))

    # Add "New Review" button
    new_review_btn = ctk.CTkButton(
        primary_actions_row,
        text="Start New Review",
        command=start_new_review,
        fg_color=STEAM_ACCENT
    )

    edit_ratings_btn = ctk.CTkButton(
        primary_actions_row,
        text="Edit Ratings",
        command=edit_ratings_from_result,
        fg_color="#4f6a2a",
        hover_color="#5f7c32"
    )

    copy_again_btn = ctk.CTkButton(
        primary_actions_row,
        text="Copy Again",
        command=copy_review_again,
        fg_color="#2f556f"
    )
    bind_responsive_button_grid(
        primary_actions_row,
        [new_review_btn, edit_ratings_btn, copy_again_btn],
        expanded_columns=3,
        breakpoint=700
    )

    secondary_actions_row = ctk.CTkFrame(buttons_frame, fg_color="transparent")
    secondary_actions_row.pack(fill="x")

    secondary_action_buttons = []

    save_txt_btn = ctk.CTkButton(
        secondary_actions_row,
        text="Save .txt",
        command=lambda: save_review_to_file(".txt"),
        fg_color="#2f556f"
    )
    secondary_action_buttons.append(save_txt_btn)

    save_md_btn = ctk.CTkButton(
        secondary_actions_row,
        text="Save .md",
        command=lambda: save_review_to_file(".md"),
        fg_color="#2f556f"
    )
    secondary_action_buttons.append(save_md_btn)

    bind_responsive_button_grid(
        secondary_actions_row,
        secondary_action_buttons,
        expanded_columns=min(3, max(1, len(secondary_action_buttons))),
        breakpoint=560
    )

def start_new_review():
    global current_index, vars_dict, selected_game, preview, current_game_data
    global latest_review_text, save_status_label, current_review_step
    global ai_status_summary_label, ai_status_refresh_btn
    global ai_status_setup_btn, ai_status_copy_pull_btn
    current_index = 0
    vars_dict = {}
    selected_game = ""
    current_game_data = {}
    latest_review_text = ""
    save_status_label = None
    ai_status_summary_label = None
    ai_status_refresh_btn = None
    ai_status_setup_btn = None
    ai_status_copy_pull_btn = None
    current_review_step = ""
    
    if preview:
        preview.destroy()
        preview = None
    
    # Go back to games screen
    show_games_screen()

app.protocol("WM_DELETE_WINDOW", on_app_close)
    
# ------------------ START ------------------
# Check if user is already logged in
ensure_app_data_dir()
migrate_legacy_data_files()
saved_api_key, saved_steam_id = load_credentials()
if saved_api_key and saved_steam_id:
    # Show loading screen briefly
    startup_loading_label = ctk.CTkLabel(main_frame, text="Loading your games...", font=("Arial", 16), text_color=STEAM_ACCENT)
    startup_loading_label.pack(expand=True)
    startup_progress = ctk.CTkProgressBar(main_frame, mode="indeterminate")
    startup_progress.pack(fill="x", padx=60, pady=(0, 40))
    startup_progress.start()
    app.update()
    threading.Thread(target=auto_login_worker, args=(saved_api_key, saved_steam_id), daemon=True).start()
else:
    # Show login screen
    show_login_screen()

# Set initial window size based on the active startup screen.
if current_screen == "login":
    apply_main_window_size(WINDOW_WIDTH, LOGIN_WINDOW_HEIGHT)
else:
    apply_main_window_size(WINDOW_WIDTH, WINDOW_HEIGHT)

app.mainloop()