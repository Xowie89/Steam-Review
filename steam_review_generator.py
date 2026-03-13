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
app.resizable(True, True)

main_frame = ctk.CTkFrame(app, fg_color=STEAM_PANEL)
main_frame.pack(fill="both", expand=True, padx=12, pady=12)

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
about_action_button = None
about_update_toast_label = None
about_update_toast_after_id = None
window_state_cache = None
window_state_loaded = False
main_window_geometry_initialized = False

# ------------------ FUNCTIONS ------------------

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
        columns = 1 if compact else max_columns

        for col in range(max_columns):
            parent.grid_columnconfigure(col, weight=0)
        for col in range(columns):
            parent.grid_columnconfigure(col, weight=1)

        for idx, button in enumerate(buttons):
            if not button.winfo_exists():
                continue

            button.grid_forget()
            row = idx if compact else idx // max_columns
            column = 0 if compact else idx % max_columns
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
    """Show the login screen."""
    global current_screen
    current_screen = "login"
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
    global current_screen, preview, rating_frame, sort_mode_var, selected_game_index
    current_screen = "games"
    apply_main_window_size(WINDOW_WIDTH, WINDOW_HEIGHT)
    selected_game_index = -1
    ensure_auto_update_check()
    
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
        if current_screen == "games":
            return on_search_down(e)
    def _guard_up(e):
        if current_screen == "games":
            return on_search_up(e)
    def _guard_enter(e):
        if current_screen == "games":
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
        if current_screen != "games":
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
    
    # Game actions row
    top_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
    top_frame.pack(fill="x", padx=15, pady=(10, 6))
    
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
    title.pack(fill="x", padx=15, pady=(0, 4))
    
    # Game stats
    hours = game_playtime // 60
    stats_text = f"⏱️ {hours}h playtime"
    stats_label = ctk.CTkLabel(header_frame, text=stats_text, font=("Arial", 11), text_color="#888")
    stats_label.pack(anchor="w", padx=15, pady=(0, 10))

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
        "You will rate 6 categories. You can move forward and backward before generating the final review."
    )
    details_label = ctk.CTkLabel(
        summary_frame,
        text=details_text,
        font=("Arial", 12),
        justify="left",
        anchor="w",
        wraplength=620,
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
        hover_color="#666"
    )

    begin_btn = ctk.CTkButton(
        actions_frame,
        text="Start Rating",
        command=show_category,
        fg_color=STEAM_ACCENT
    )
    bind_responsive_button_grid(
        actions_frame,
        [back_btn, begin_btn],
        expanded_columns=2,
        breakpoint=560
    )

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

    next_label = "Generate Review" if current_index == len(category_list) - 1 else "Next"
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
    
    preview = ctk.CTkTextbox(preview_frame)
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

    save_txt_btn = ctk.CTkButton(
        secondary_actions_row,
        text="Save .txt",
        command=lambda: save_review_to_file(".txt"),
        fg_color="#2f556f"
    )

    save_md_btn = ctk.CTkButton(
        secondary_actions_row,
        text="Save .md",
        command=lambda: save_review_to_file(".md"),
        fg_color="#2f556f"
    )
    bind_responsive_button_grid(
        secondary_actions_row,
        [save_txt_btn, save_md_btn],
        expanded_columns=2,
        breakpoint=560
    )

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