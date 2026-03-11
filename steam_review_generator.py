import customtkinter as ctk
import pyperclip
import requests
import json
import webbrowser
import os
import tkinter as tk

ctk.set_appearance_mode("dark")

STEAM_BG = "#1b2838"
STEAM_PANEL = "#16202d"
STEAM_ACCENT = "#66c0f4"
WINDOW_WIDTH = 600
WINDOW_HEIGHT = 800

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
CREDENTIALS_FILE = "steam_credentials.json"
CACHE_FILE = "games_cache.json"
current_screen = "login"  # "login" or "games"
steam_username = ""

# ------------------ FUNCTIONS ------------------

def save_credentials(api_key, steam_id):
    """Save API credentials to file"""
    try:
        credentials = {
            "api_key": api_key,
            "steam_id": steam_id
        }
        with open(CREDENTIALS_FILE, 'w') as f:
            json.dump(credentials, f)
    except Exception as e:
        print(f"Failed to save credentials: {e}")

def save_games_cache(games, steam_id):
    """Cache owned games list to disk"""
    try:
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
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Failed to load games cache: {e}")
    return None

def load_credentials():
    """Load API credentials from file"""
    try:
        if os.path.exists(CREDENTIALS_FILE):
            with open(CREDENTIALS_FILE, 'r') as f:
                credentials = json.load(f)
            return credentials.get("api_key", ""), credentials.get("steam_id", "")
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
    
    # Reset variables
    steam_api_key = ""
    steam_id = ""
    owned_games = []
    steam_username = ""
    current_screen = "login"
    
    # Switch to login screen
    show_login_screen()

def show_login_screen():
    """Show the login screen"""
    global current_screen
    current_screen = "login"
    
    # Clear current content
    for widget in main_frame.winfo_children():
        widget.destroy()
    
    # Login screen
    login_frame = ctk.CTkFrame(main_frame, fg_color=STEAM_PANEL)
    login_frame.pack(fill="both", expand=True, padx=20, pady=20)
    
    login_title = ctk.CTkLabel(login_frame, text="Steam Review Generator", font=("Arial", 28, "bold"), text_color=STEAM_ACCENT)
    login_title.pack(pady=(30, 10))
    
    subtitle = ctk.CTkLabel(login_frame, text="Login with your Steam credentials", font=("Arial", 16), text_color="#cccccc")
    subtitle.pack(pady=(0, 30))
    
    # API Key input
    api_key_label = ctk.CTkLabel(login_frame, text="Steam API Key:", font=("Arial", 14))
    api_key_label.pack(pady=(20, 5))
    global steam_api_key_entry
    steam_api_key_entry = ctk.CTkEntry(login_frame, width=400, placeholder_text="Enter your Steam API key...")
    steam_api_key_entry.pack(pady=(0, 10))
    
    # Steam ID input
    steam_id_label = ctk.CTkLabel(login_frame, text="Steam ID (64-bit):", font=("Arial", 14))
    steam_id_label.pack(pady=(10, 5))
    global steam_id_entry
    steam_id_entry = ctk.CTkEntry(login_frame, width=400, placeholder_text="Enter your 64-bit Steam ID...")
    steam_id_entry.pack(pady=(0, 20))
    
    # Login button
    login_btn = ctk.CTkButton(login_frame, text="Login & Fetch Games", command=login_and_fetch, fg_color=STEAM_ACCENT, height=40)
    login_btn.pack(pady=(10, 20))
    
    # Status label
    global status_label
    status_label = ctk.CTkLabel(login_frame, text="", font=("Arial", 12))
    status_label.pack(pady=(0, 20))
    
    # Instructions
    instructions_frame = ctk.CTkFrame(login_frame, fg_color=STEAM_BG)
    instructions_frame.pack(fill="x", padx=20, pady=10)
    
    instructions_title = ctk.CTkLabel(instructions_frame, text="How to get your credentials:", font=("Arial", 14, "bold"), text_color=STEAM_ACCENT)
    instructions_title.pack(pady=(15, 10))
    
    instructions_text = tk.Text(instructions_frame, height=8, width=50, bg=STEAM_BG, fg="#cccccc", font=("Arial", 11), wrap="word", borderwidth=0, highlightthickness=0)
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
    
    # Load saved credentials
    saved_api_key, saved_steam_id = load_credentials()
    if saved_api_key:
        steam_api_key_entry.insert(0, saved_api_key)
    if saved_steam_id:
        steam_id_entry.insert(0, saved_steam_id)

def show_games_screen():
    """Show the games selection screen"""
    global current_screen, preview, rating_frame
    current_screen = "games"
    
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
    
    # Search bar (without label)
    global search_entry
    search_entry = ctk.CTkEntry(games_frame, width=400, placeholder_text="Type to search games...")
    search_entry.pack(pady=(0, 15), padx=20, anchor="w")
    search_entry.bind("<KeyRelease>", filter_games)
    
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
    
    # Game buttons will be added here
    global game_buttons
    game_buttons = []
    
    # Populate games
    populate_game_list()

def populate_game_list(search_filter=""):
    """Populate the game list, showing/hiding based on search"""
    # Create buttons for all games on first run
    if not game_buttons:
        for game in owned_games:
            game_name = game['name']
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
    
    # Reset scroll position to top when filtering
    if search_filter:
        game_scroll_frame._parent_canvas.yview_moveto(0)
    
    # Show/hide buttons based on search filter
    shown_count = 0
    search_lower = search_filter.lower()
    
    for button, game_name in game_buttons:
        if search_filter and search_lower not in game_name.lower():
            button.pack_forget()
        else:
            button.pack(fill="x", padx=5, pady=2)
            shown_count += 1
    
    # Show count only if filtering

def filter_games(event=None):
    """Filter games based on search input"""
    search_text = search_entry.get()
    populate_game_list(search_text)

def login_and_fetch():
    """Handle login and game fetching"""
    global steam_api_key, steam_id, owned_games
    
    api_key = steam_api_key_entry.get().strip()
    user_steam_id = steam_id_entry.get().strip()
    
    if not api_key or not user_steam_id:
        status_label.configure(text="Please enter both API key and Steam ID", text_color="#ff5555")
        return
    
    status_label.configure(text="Logging in and fetching games...", text_color="#ffff00")
    app.update()
    
    try:
        # Steam API endpoint for owned games
        url = f"http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
        params = {
            'key': api_key,
            'steamid': user_steam_id,
            'include_appinfo': 1,
            'include_played_free_games': 1,
            'format': 'json'
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        games = data.get('response', {}).get('games', [])
        
        if not games:
            status_label.configure(text="No games found. Make sure your profile is public.", text_color="#ff5555")
            return
        
        # Sort games by name
        owned_games = sorted(games, key=lambda x: x.get('name', '').lower())
        
        # Update global variables
        steam_api_key = api_key
        steam_id = user_steam_id
        
        # Save credentials and cache games
        save_credentials(api_key, user_steam_id)
        save_games_cache(owned_games, user_steam_id)
        
        # Fetch username
        try:
            summary_url = "http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/"
            summary_params = {
                'key': api_key,
                'steamids': user_steam_id
            }
            summary_response = requests.get(summary_url, params=summary_params)
            summary_response.raise_for_status()
            summary_data = summary_response.json()
            players = summary_data.get('response', {}).get('players', [])
            if players:
                global steam_username
                steam_username = players[0].get('personaname', 'Unknown')
        except:
            steam_username = 'Unknown'
        
        # Switch to games screen
        show_games_screen()
        
    except requests.exceptions.RequestException as e:
        status_label.configure(text=f"Login failed: {str(e)}", text_color="#ff5555")
    except json.JSONDecodeError:
        status_label.configure(text="Invalid response from Steam API", text_color="#ff5555")

def start_review(game_name):
    """Start the review process for selected game"""
    global selected_game, preview, current_game_data
    selected_game = game_name
    
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
    
    title = ctk.CTkLabel(top_frame, text=f"Reviewing: {game_name}", font=("Arial", 18, "bold"), text_color=STEAM_ACCENT)
    title.pack(side="left", padx=20)
    
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
    
    # Start review process
    show_category()

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
    global current_index, new_review_btn
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

    # Create category frame with scrollable options
    frame = ctk.CTkFrame(container, fg_color=STEAM_PANEL, corner_radius=8)
    frame.pack(fill="both", expand=True, pady=10)
    
    # Category description
    desc_label = ctk.CTkLabel(frame, text=f"Rate the {category.lower()} of this game", font=("Arial", 12), text_color="#aaa")
    desc_label.pack(pady=(15, 10), padx=20, anchor="w")
    
    # Options frame
    options_frame = ctk.CTkScrollableFrame(frame)
    options_frame.pack(fill="both", expand=True, padx=20, pady=(0, 15))
    
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
            command=next_category,
            font=("Arial", 11),
            text_color="#ccc"
        )
        btn.pack(anchor="w")

def next_category():
    global current_index
    current_index += 1
    show_category()

def generate_review():
    global new_review_btn
    
    scores = []
    weights = []
    category_ratings = {}
    
    # Calculate scores and build review
    for category, options in categories.items():
        selected = vars_dict[category].get()
        for text, val in options:
            if text == selected:
                scores.append(val)
                weights.append(category_weights[category])
                category_ratings[category] = (text, val)
                break
    
    # Calculate weighted average
    if weights:
        final_score = round(sum(s * w for s, w in zip(scores, weights)) / sum(weights))
    else:
        final_score = 0
    
    # Build professional review text
    hours = current_game_data.get('playtime', 0) // 60
    game_name = current_game_data.get('name', 'Unknown Game')
    
    # Star rating
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
    
    # Create buttons frame
    buttons_frame = ctk.CTkFrame(preview_frame, fg_color="transparent")
    buttons_frame.pack(fill="x", padx=15, pady=(0, 15))
    
    copy_label = ctk.CTkLabel(buttons_frame, text="✓ Review copied to clipboard!", font=("Arial", 10), text_color="#00ff00")
    copy_label.pack(side="left", padx=10)
    
    # Add "New Review" button
    new_review_btn = ctk.CTkButton(buttons_frame, text="Start New Review", command=start_new_review, fg_color=STEAM_ACCENT, width=150)
    new_review_btn.pack(side="right")

def start_new_review():
    global current_index, vars_dict, selected_game, preview, current_game_data, rating_frame
    current_index = 0
    vars_dict = {}
    selected_game = ""
    current_game_data = {}
    
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
saved_api_key, saved_steam_id = load_credentials()
if saved_api_key and saved_steam_id:
    # Try to auto-login
    steam_api_key = saved_api_key
    steam_id = saved_steam_id
    
    # Show loading screen briefly
    loading_label = ctk.CTkLabel(main_frame, text="Loading your games...", font=("Arial", 16), text_color=STEAM_ACCENT)
    loading_label.pack(expand=True)
    app.update()
    
    try:
        # Try loading cached games first
        cache = load_games_cache()
        if cache and cache.get('steam_id') == saved_steam_id:
            owned_games = cache.get('games', [])
        else:
            # Quick fetch of games from API
            url = f"http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
            params = {
                'key': saved_api_key,
                'steamid': saved_steam_id,
                'include_appinfo': 1,
                'include_played_free_games': 1,
                'format': 'json'
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            games = data.get('response', {}).get('games', [])
            if games:
                owned_games = sorted(games, key=lambda x: x.get('name', '').lower())
                save_games_cache(owned_games, saved_steam_id)
        
        if owned_games:
            # Fetch username
            try:
                summary_url = "http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/"
                summary_params = {
                    'key': saved_api_key,
                    'steamids': saved_steam_id
                }
                summary_response = requests.get(summary_url, params=summary_params, timeout=10)
                summary_response.raise_for_status()
                summary_data = summary_response.json()
                players = summary_data.get('response', {}).get('players', [])
                if players:
                    steam_username = players[0].get('personaname', 'Unknown')
            except:
                steam_username = 'Unknown'
            
            show_games_screen()
        else:
            show_login_screen()
    except:
        # If auto-login fails, show login screen
        show_login_screen()
else:
    # Show login screen
    show_login_screen()

# Set window size
app.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")

app.mainloop()