import os
import re
import json
import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import poisson
import matplotlib.colors as mcolors
from bs4 import BeautifulSoup
from mplsoccer import Pitch
from mplsoccer import VerticalPitch
from matplotlib.colors import LinearSegmentedColormap
import random
import matplotlib.image as mpimg
import seaborn as sns

# Function to load fixture data from multiple sources
def load_fixtures():
    fixture_file_path = "data/tables/fixture_data.csv"
    if os.path.exists(fixture_file_path):
        fixtures_df = pd.read_csv(fixture_file_path)
    else:
        raise FileNotFoundError(f"⚠️ Fixture file not found: {fixture_file_path}. Ensure it's saved before running.")

    return fixtures_df

print("Fixtures loaded successfully!")

# Function to load historical match data
def load_match_data(start_year=2016, end_year=2024):
    historical_fixture_file_path = "data/tables/historical_fixture_data.csv"
    
    if os.path.exists(historical_fixture_file_path):
        historical_fixtures_df = pd.read_csv(historical_fixture_file_path)
    else:
        raise FileNotFoundError(f"⚠️ Fixture file not found: {historical_fixture_file_path}. Ensure it's saved before running.")

    return historical_fixtures_df

print("Match data loaded successfully!")

def load_next_gw_fixtures():
    """Loads the next gameweek fixtures from the saved file."""
    next_gw_file_path = "data/tables/next_gw_fixtures.csv"

    if os.path.exists(next_gw_file_path):
        next_gw_fixtures_df = pd.read_csv(next_gw_file_path)
        return next_gw_fixtures_df.to_dict(orient="records")  # Convert DataFrame to list of dictionaries
    else:
        raise FileNotFoundError(f"⚠️ Next gameweek fixtures file not found: {next_gw_file_path}. Ensure it's saved before running.")

print("Next GW data loaded successfully!")

def get_player_data():
    player_file_path = "data/tables/player_data.csv"
    
    if os.path.exists(player_file_path):
        player_data_df = pd.read_csv(player_file_path)
    else:
        raise FileNotFoundError(f"⚠️ Player data file not found: {player_file_path}. Ensure it's saved before running.")

    return player_data_df.to_dict(orient="records")  # Convert DataFrame to list of dictionaries


print("Player data loaded successfully!")


# Function to calculate team statistics
def calculate_team_statistics(historical_fixture_data):
    team_names = historical_fixture_data['Home Team'].unique()
    home_field_advantage = historical_fixture_data['home_goals'].mean() - historical_fixture_data['away_goals'].mean()
    team_data = {}

    for team in team_names:
        home_games = historical_fixture_data[historical_fixture_data['Home Team'] == team]
        away_games = historical_fixture_data[historical_fixture_data['Away Team'] == team]

        avg_home_goals_for = home_games['home_goals'].mean()
        avg_away_goals_for = away_games['away_goals'].mean()
        avg_home_goals_against = home_games['away_goals'].mean()
        avg_away_goals_against = away_games['home_goals'].mean()

        team_data[team] = {
            'Home Goals For': avg_home_goals_for,
            'Away Goals For': avg_away_goals_for,
            'Home Goals Against': avg_home_goals_against,
            'Away Goals Against': avg_away_goals_against,
            'ATT Rating': (avg_home_goals_for + avg_away_goals_for) / 2,
            'DEF Rating': (avg_home_goals_against + avg_away_goals_against) / 2
        }

    return team_data, home_field_advantage

print("Team statistics calculated!")

# Function to calculate recent form ratings
def calculate_recent_form(historical_fixture_data, team_data, recent_matches=20, alpha=0.65):
    recent_form_att = {}
    recent_form_def = {}

    for team in historical_fixture_data['Home Team'].unique():
        recent_matches_df = historical_fixture_data[(historical_fixture_data['Home Team'] == team) | (historical_fixture_data['Away Team'] == team)].tail(recent_matches)
        
        home_matches = recent_matches_df[recent_matches_df['Home Team'] == team]
        away_matches = recent_matches_df[recent_matches_df['Away Team'] == team]

        avg_home_att = home_matches['home_goals'].mean()
        avg_away_att = away_matches['away_goals'].mean()
        avg_home_def = home_matches['away_goals'].mean()
        avg_away_def = away_matches['home_goals'].mean()

        recent_form_att[team] = ((1 - alpha) * team_data[team]['ATT Rating']) + (alpha * ((avg_home_att + avg_away_att) / 2))
        recent_form_def[team] = ((1 - alpha) * team_data[team]['DEF Rating']) + (alpha * ((avg_home_def + avg_away_def) / 2))

    return recent_form_att, recent_form_def

print("Team recent form calculated!")

# Function to simulate a match using Poisson distribution
def simulate_poisson_distribution(home_xg, away_xg, max_goals=12):
    result_matrix = np.zeros((max_goals, max_goals))
    for home_goals in range(max_goals):
        for away_goals in range(max_goals):
            home_prob = poisson.pmf(home_goals, home_xg)
            away_prob = poisson.pmf(away_goals, away_xg)
            result_matrix[home_goals, away_goals] = home_prob * away_prob
    # Normalize the matrix so the probabilities sum to 1
    result_matrix /= result_matrix.sum()

    # Calculate overall probabilities
    home_win_prob = np.sum(np.tril(result_matrix, -1))  # Below diagonal
    away_win_prob = np.sum(np.triu(result_matrix, 1))   # Above diagonal
    draw_prob = np.sum(np.diag(result_matrix))          # Diagonal elements

    return result_matrix, home_win_prob, draw_prob, away_win_prob

import os
import matplotlib.pyplot as plt

print("Poisson Dist Calculated!")

# Function to generate a heatmap
def display_heatmap(result_matrix, home_team, away_team, gw_number, home_prob, draw_prob, away_prob, save_path):
    fig, axes = plt.subplots(2, 1, figsize=(6, 8), gridspec_kw={'height_ratios': [3, 1]}, facecolor="#f4f4f9")

    # --- Heatmap (Top) ---
    heatmap_ax = axes[0]
    display_matrix = result_matrix[:6, :6]  # Limit to 6x6 grid
    heatmap_ax.imshow(display_matrix, cmap="Purples", origin='upper')

    # Move x-axis labels and ticks to the top
    heatmap_ax.xaxis.set_label_position('top')
    heatmap_ax.xaxis.tick_top()

    # Labeling
    heatmap_ax.set_xlabel(f"{away_team} Goals")
    heatmap_ax.set_ylabel(f"{home_team} Goals")
    
    # Add percentage text inside each cell
    for i in range(6):
        for j in range(6):
            heatmap_ax.text(j, i, f"{display_matrix[i, j] * 100:.1f}%", 
                            ha='center', va='center', color='black', fontsize=8)

    # Hide spines
    for spine in heatmap_ax.spines.values():
        spine.set_visible(False)

    # --- Bar Chart (Bottom) ---
    bar_ax = axes[1]
    bar_ax.set_facecolor('#f4f4f9')  # Background color

    categories = [f"{home_team}", "Draw", f"{away_team}"]
    values = [home_prob * 100, draw_prob * 100, away_prob * 100]

    # **Change from horizontal to vertical bars**
    bars = bar_ax.bar(categories, values, color='#3f007d', alpha=0.9, width=0.6)

    # Title for the bar chart
    bar_ax.set_title("Projected Win %'s:")

    # Add text labels on bars (above each bar)
    for bar in bars:
        height = bar.get_height()
        bar_ax.text(bar.get_x() + bar.get_width()/2, height + 2, f"{height:.1f}%", 
                    ha='center', fontsize=10, fontweight='bold')

    # Remove unnecessary spines
    bar_ax.spines['top'].set_visible(False)
    bar_ax.spines['right'].set_visible(False)
    bar_ax.spines['left'].set_visible(False)
    bar_ax.spines['bottom'].set_visible(False)
    bar_ax.set_yticks([])

    # Add "FiveStat" watermark in the bottom-left corner
    fig.text(0.97, 0.60, "FiveStat", fontsize=8, color="black", fontweight="bold", ha="left", va="bottom", alpha=0.4, rotation=90)
    #f"FiveStat", ha='center', va='center', fontsize=8, fontweight='bold', color='black', alpha=0.4

    # Adjust layout
    plt.tight_layout()

    # 📌 **Save the combined figure using Team IDs**
    heatmap_filename = f"{home_team}_{away_team}_heatmap.png"
    plt.savefig(os.path.join(save_path, heatmap_filename))
    plt.close()

    heatmap_path = os.path.join(save_path, heatmap_filename)


    # ✅ **Check if the heatmap already exists**
    if os.path.exists(heatmap_path):
        print(f"Heatmap for {home_team} vs {away_team} already exists.")
        return  # 🔄 Skip generating this heatmap

print(f"Heatmaps saved!")



def generate_all_heatmaps(team_stats, recent_form_att, recent_form_def, alpha=0.65, save_path="static/heatmaps/"):
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    # ✅ Load the next gameweek fixtures
    next_gw_file_path = "data/tables/next_gw_fixtures.csv"
    if os.path.exists(next_gw_file_path):
        next_gw_fixtures = pd.read_csv(next_gw_file_path)
    else:
        raise FileNotFoundError(f"⚠️ Next gameweek fixture file not found: {next_gw_file_path}. Ensure it's saved before running.")

    # ✅ Generate heatmaps only for next gameweek fixtures
    for _, fixture in next_gw_fixtures.iterrows():
        home_team = fixture['home_team']
        away_team = fixture['away_team']
        gw_number = fixture['round_number']

        if pd.isna(home_team) or pd.isna(away_team):
            continue  # Skip if IDs are missing

        if home_team not in team_stats or away_team not in team_stats:
            continue

        # Blend overall ratings with recent form using alpha weighting
        home_att_rating = (1 - alpha) * team_stats[home_team]['ATT Rating'] + alpha * recent_form_att[home_team]
        away_att_rating = (1 - alpha) * team_stats[away_team]['ATT Rating'] + alpha * recent_form_att[away_team]
        home_def_rating = (1 - alpha) * team_stats[home_team]['DEF Rating'] + alpha * recent_form_def[home_team]
        away_def_rating = (1 - alpha) * team_stats[away_team]['DEF Rating'] + alpha * recent_form_def[away_team]

        # Adjusted expected goals (xG)
        home_xg = home_att_rating * away_def_rating
        away_xg = away_att_rating * home_def_rating
        
        result_matrix, home_prob, draw_prob, away_prob = simulate_poisson_distribution(home_xg, away_xg)

        # ✅ Generate heatmap for the next gameweek fixture
        display_heatmap(result_matrix, home_team, away_team, gw_number, home_prob, draw_prob, away_prob, save_path)






print("Heatmaps generated successfully!")

# generating & saving shotmaps

# Directory to save shotmaps
shotmap_save_path = "static/shotmaps/"
os.makedirs(shotmap_save_path, exist_ok=True)

# Fetch the latest fixtures (Merged from FixtureDownload & Understat)
fixtures_df = load_fixtures()

# Filter only completed matches
completed_fixtures = fixtures_df[(fixtures_df["isResult"] == True)]

# Dict for shotmap table team names
TEAM_NAME_MAPPING = {
    "WolverhamptonWanderers": "Wolves",
    "CrystalPalace": "Crystal Palace",
    "NottinghamForest": "Forest",
    "Tottenham": "Spurs",
    "ManchesterCity": "Man City",
    "Man Utd": "ManchesterUnited",
    "NewcastleUnited": "Newcastle",
    "WestHam": "West Ham"
}

# Function to generate and save shot maps
def generate_shot_map(understat_match_id):
    try:
        url = f'https://understat.com/match/{understat_match_id}'
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        ugly_soup = str(soup)

        # Extract JSON shot data
        match = re.search("var shotsData .*= JSON.parse\\('(.*)'\\)", ugly_soup)
        if not match:
            print(f"Skipping match {understat_match_id}: No shot data found")
            return

        shots_data = match.group(1)
        data = shots_data.encode('utf8').decode('unicode_escape')
        data = json.loads(data)

        # Create DataFrames
        home_df = pd.DataFrame(data['h'])
        away_df = pd.DataFrame(data['a'])

        # Extract and update team names
        home_team_name = home_df.iloc[0]['h_team'] if not home_df.empty else "Unknown"
        away_team_name = away_df.iloc[0]['a_team'] if not away_df.empty else "Unknown"

        # Scale coordinates to StatsBomb pitch (120x80)
        home_df['x_scaled'] = home_df['X'].astype(float) * 120
        home_df['y_scaled'] = home_df['Y'].astype(float) * 80
        away_df['x_scaled'] = away_df['X'].astype(float) * 120
        away_df['y_scaled'] = away_df['Y'].astype(float) * 80

        # Adjust positions for correct plotting
        home_df['x_scaled'] = 120 - home_df['x_scaled']
        away_df['y_scaled'] = 80 - away_df['y_scaled']

        # Calculate total goals and xG
        goal_keywords = ['Goal', 'PenaltyGoal']
        own_goal_keyword = 'OwnGoal'  # Special case

        # Count regular & penalty goals normally
        home_goals = home_df['result'].apply(lambda x: any(kw in str(x) for kw in goal_keywords)).sum()
        away_goals = away_df['result'].apply(lambda x: any(kw in str(x) for kw in goal_keywords)).sum()

        # Count own goals (but assign them to the **other** team)
        home_own_goals = home_df['result'].apply(lambda x: own_goal_keyword in str(x)).sum()
        away_own_goals = away_df['result'].apply(lambda x: own_goal_keyword in str(x)).sum()

        # Correct final goal counts
        total_goals_home = home_goals + away_own_goals - home_own_goals  # Home goals + own goals scored by away team
        total_goals_away = away_goals + home_own_goals - away_own_goals  # Away goals + own goals scored by home team

        total_xg_home = home_df['xG'].astype(float).sum()
        total_xg_away = away_df['xG'].astype(float).sum()
    
            # Compute stats for table
        def calculate_match_stats(team_df):
            team_df['xG'] = pd.to_numeric(team_df['xG'], errors='coerce')  # Ensure xG is numeric
            return {
                'Goals': len(team_df[team_df['result'] == 'Goal']),  
                'xG': round(team_df['xG'].sum(), 2),  
                'Shots': len(team_df),  
                'SOT': len(team_df[team_df['result'].isin(['Goal', 'SavedShot'])])  
            }

        home_stats = calculate_match_stats(home_df)
        away_stats = calculate_match_stats(away_df)

        # Initialize pitch
        pitch = Pitch(pitch_type='statsbomb', pitch_color='#f4f4f9', line_color='black', line_zorder=2)
        fig, axs = plt.subplots(2, 1, figsize=(10, 10), gridspec_kw={'height_ratios': [3, 1]})


        # Set background color
        fig.patch.set_facecolor('#f4f4f9')
        axs[0].set_facecolor('#f4f4f9')

        # Plot heatmap
        all_shots = pd.concat([home_df, away_df])
        cmap = LinearSegmentedColormap.from_list('custom_cmap', ['#f4f4f9', '#3f007d'])
        pitch.kdeplot(
            all_shots['x_scaled'], all_shots['y_scaled'], ax=axs[0], fill=True, cmap=cmap,
            n_levels=100, thresh=0, zorder=1
        )

        # Draw pitch
        pitch.draw(ax=axs[0])

        # Plot shots for both teams
        for df in [home_df, away_df]:  
            for _, shot in df.iterrows():
                x, y = shot['x_scaled'], shot['y_scaled']
                color = 'gold' if "goal" in str(shot['result']).lower() else 'white'
                zorder = 3 if shot['result'] == 'Goal' else 2
                axs[0].scatter(x, y, s=1000 * float(shot['xG']) if pd.notna(shot['xG']) else 100, 
                           ec='black', c=color, zorder=zorder)

        # Define the base path (where data_loader.py is located)
        base_path = os.path.dirname(os.path.abspath(__file__))  # Gets the directory of data_loader.py

        # Construct full paths for the logos
        home_logo_path = os.path.join(base_path, "static", "team_logos", f"{home_team_name.lower()}_logo.png")
        away_logo_path = os.path.join(base_path, "static", "team_logos", f"{away_team_name.lower()}_logo.png")

        def add_team_logo(ax, logo_path, y_min, y_max, x_center):
            """Loads and displays a team logo at a given position, keeping aspect ratio and flipping it if necessary."""
            if os.path.exists(logo_path):
                logo_img = mpimg.imread(logo_path)
                
                # Flip the image vertically so it appears correctly
                logo_img = np.flipud(logo_img)  # Prevents upside-down images
                
                # Get image aspect ratio (height / width)
                aspect_ratio = logo_img.shape[0] / logo_img.shape[1]  # Height / Width
                
                # Set width dynamically based on height
                height = y_max - y_min  # Define height of the image
                width = height / aspect_ratio  # Maintain aspect ratio
                
                x_min = x_center - (width / 2)  # Centered positioning
                x_max = x_center + (width / 2)

                # Display the flipped image with transparency (alpha)
                ax.imshow(logo_img, extent=(x_min, x_max, y_min, y_max), alpha=0.1, zorder=1)

        # 🎯 Add team logos with automatic width adjustment
        add_team_logo(axs[0], home_logo_path, y_min=20, y_max=60, x_center=30)  # Home team
        add_team_logo(axs[0], away_logo_path, y_min=20, y_max=60, x_center=90)  # Away team


        # Add match info
        #axs[0].text(30, 10, f"{home_team_name}", ha='center', va='center', fontsize=25, fontweight='bold', color='black')
        #axs[0].text(90, 10, f"{away_team_name}", ha='center', va='center', fontsize=25, fontweight='bold', color='black')
        axs[0].text(30, 40, f"{total_goals_home}", ha='center', va='center', fontsize=180, fontweight='bold', color='black', alpha=0.5)
        axs[0].text(90, 40, f"{total_goals_away}", ha='center', va='center', fontsize=180, fontweight='bold', color='black', alpha=0.5)
        axs[0].text(30, 60, f"{total_xg_home:.2f}", ha='center', va='center', fontsize=45, fontweight='bold', color='black', alpha=0.6)
        axs[0].text(90, 60, f"{total_xg_away:.2f}", ha='center', va='center', fontsize=45, fontweight='bold', color='black', alpha=0.6)
        axs[0].text(105,78, f"Respective Team XG values", ha='center', va='center', fontsize=8, fontweight='bold', color='black', alpha=0.4)
        axs[0].text(6,78,   f"FiveStat", ha='center', va='center', fontsize=8, fontweight='bold', color='black', alpha=0.4)


        # 📊 Generate Table
        ax_table = axs[1]
        column_labels = [f"{home_team_name}", "", f"{away_team_name}"]
        table_vals = [
            [total_goals_home, 'Goals', total_goals_away],  # Use corrected scores here
            [home_stats['xG'], 'xG', away_stats['xG']],  
            [home_stats['Shots'], 'Shots', away_stats['Shots']],  
            [home_stats['SOT'], 'SOT', away_stats['SOT']]  
        ]
        table = ax_table.table(
            cellText=table_vals,
            cellLoc='center',
            colLabels=column_labels,
            bbox=[0, 0, 1, 1]
        )

        for i in range(len(table_vals) + 1):  # +1 to include header row
            for j in range(len(column_labels)):
                cell = table[(i, j)]
                cell.set_facecolor("#f4f4f9")  # Background color

        column_widths = [0.4, 0.2, 0.4]

        for j, width in enumerate(column_widths):
            for i in range(len(table_vals) + 1):  # +1 includes header row
                cell = table[i, j]
                cell.set_width(width)

        for (i, j), cell in table.get_celld().items():
            if j == 0:
                table.get_celld()[(i, j)].visible_edges = 'R'
            elif j == 2:
                table.get_celld()[(i, j)].visible_edges = 'L'
            else:
                table.get_celld()[(i, j)].visible_edges = 'LR'

        ax_table.axis('off')  # Hide axes for the table
        table.set_fontsize(16)

        # Save figure
        plt.tight_layout()
        shotmap_file = os.path.join(shotmap_save_path, f"{home_team}_{away_team}_shotmap.png")
        plt.savefig(shotmap_file)
        plt.close(fig)

    except Exception as e:
        print(f"❌ Error processing match {understat_match_id}: {e}")

# Loop through completed fixtures only and generate shotmaps
for _, row in completed_fixtures.iterrows():
    home_team = row['home_team']
    away_team = row['away_team']
    match_id = row['id']
    shotmap_file = os.path.join(shotmap_save_path, f"{home_team}_{away_team}_shotmap.png")

    # Skip if shotmap already exists
    if os.path.exists(shotmap_file):
        continue

    generate_shot_map(match_id)

print("Fixture Shotmaps Generated!")






# Now generating Team & ALL shots shotmaps
print("Starting to process all shotmap data (this may take a while)")

# Ensure directories exist
SHOTMAP_DIR = "static/shotmaps/"
ALL_SHOTMAP_DIR = os.path.join(SHOTMAP_DIR, "all/")
TEAM_SHOTMAP_DIR = os.path.join(SHOTMAP_DIR, "team/")

os.makedirs(ALL_SHOTMAP_DIR, exist_ok=True)
os.makedirs(TEAM_SHOTMAP_DIR, exist_ok=True)

# ✅ Define the path for saving shots_data.csv
SHOTS_DATA_PATH = "data/tables/shots_data.csv"

# ✅ Load existing shot data if available
if os.path.exists(SHOTS_DATA_PATH):
    print("📂 Loading existing shot data...")
    existing_shots_df = pd.read_csv(SHOTS_DATA_PATH)
else:
    print("🚀 No existing shot data found, processing all matches...")
    existing_shots_df = pd.DataFrame()

# ✅ Get processed match IDs
processed_match_ids = set(existing_shots_df["match_id"].unique()) if not existing_shots_df.empty else set()

# ✅ Get new match IDs that haven't been processed
new_match_ids = set(completed_fixtures["id"].unique()) - processed_match_ids

print(f"🆕 Found {len(new_match_ids)} new matches to process.")

# ✅ Process only new matches
team_shots = {}  # Store new shots

def process_match_shots(understat_match_id):
    """Fetch and process shot data for a match."""
    try:
        url = f'https://understat.com/match/{understat_match_id}'
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.content, 'html.parser')
        match = re.search(r"var shotsData\s*=\s*JSON.parse\('(.*)'\)", str(soup))

        if not match:
            print(f"⚠️ Skipping match {understat_match_id}: No shot data found")
            return
        
        data = json.loads(match.group(1).encode('utf8').decode('unicode_escape'))

        # Get team names
        match_info = completed_fixtures[completed_fixtures["id"] == understat_match_id]
        if match_info.empty:
            print(f"⚠️ Match {understat_match_id} not found in fixture list")
            return
        
        home_team, away_team = match_info["home_team"].values[0], match_info["away_team"].values[0]

        # Process shots for both teams
        for team, shots in [('home', data['h']), ('away', data['a'])]:
            df = pd.DataFrame(shots)
            if df.empty:
                continue

            df['team'] = home_team if team == 'home' else away_team
            df['x_scaled'] = df['X'].astype(float) * 120
            df['y_scaled'] = df['Y'].astype(float) * 80

            # Flip coordinates **only for away teams** (so all shots face the same goal)
            if team == 'away':
                df['x_scaled'] = 120 - df['x_scaled']

            team_shots.setdefault(df['team'].iloc[0], pd.DataFrame())
            team_shots[df['team'].iloc[0]] = pd.concat([team_shots[df['team'].iloc[0]], df], ignore_index=True)

    except Exception as e:
        print(f"❌ Error processing match {understat_match_id}: {e}")

# ✅ Process ONLY new matches
for i, match_id in enumerate(new_match_ids, start=1):
    process_match_shots(match_id)  # ✅ Keep and use this function!
    print(f"📊 Progress: {i}/{len(new_match_ids)} matches processed.")

# ✅ Merge new shot data with existing data
if team_shots:
    new_shots_df = pd.concat(team_shots.values(), ignore_index=True)
    all_shots_df = pd.concat([existing_shots_df, new_shots_df], ignore_index=True)
else:
    print("⚠️ No new shot data found. Using existing shots_data.csv.")
    all_shots_df = existing_shots_df  # Keep existing data if no new matches

# Ensure all_shots_df doesn't have duplicate 'id' before merging
if 'id' in all_shots_df.columns:
    all_shots_df.drop(columns=['id'], inplace=True)

all_shots_df['match_id'] = all_shots_df['match_id'].astype(str)
completed_fixtures['id'] = completed_fixtures['id'].astype(str)

# Merge completed_fixtures with all_shots_df
all_shots_df = all_shots_df.merge(
    completed_fixtures[['id', 'home_team', 'away_team']], 
    left_on='match_id', 
    right_on='id', 
    how='left'
)

# ✅ Remove duplicate ID columns
all_shots_df.drop(columns=['id'], errors='ignore', inplace=True)

# ✅ Rename merged columns correctly
all_shots_df.rename(columns={'home_team_y': 'home_team', 'away_team_y': 'away_team'}, inplace=True)

# ✅ Ensure 'home_team' exists before proceeding
if 'home_team' not in all_shots_df.columns:
    print("⚠️ 'home_team' is missing after merging! Merge may have failed.")
else:
    print("✅ 'home_team' column exists. Proceeding with calculations.")

# Drop duplicate home/away team columns
all_shots_df = all_shots_df.loc[:, ~all_shots_df.columns.duplicated()].copy()

# ✅ Assign home/away indicator
all_shots_df['h_a'] = all_shots_df.apply(lambda row: 'h' if str(row['team']).strip() == str(row['home_team']).strip() else 'a', axis=1)

# ✅ Save updated shots_data.csv
all_shots_df.to_csv(SHOTS_DATA_PATH, index=False, columns=['match_id', 'team', 'x_scaled', 'y_scaled', 'xG', 'result', 'h_a', 'home_team', 'away_team'])
print(f"✅ Shot data saved to {SHOTS_DATA_PATH}")


# ✅ Create All-Shots Shotmap
pitch = VerticalPitch(pitch_type='statsbomb', pitch_color='#f4f4f9', line_color='black', line_zorder=2, half=True)
fig, ax = pitch.draw(figsize=(13, 9))
fig.patch.set_facecolor("#f4f4f9")
goals_df = all_shots_df[all_shots_df['result'].str.lower() == 'goal']
# 🔥 Add Heatmap
#if not goals_df.empty:
#    cmap = LinearSegmentedColormap.from_list('custom_cmap', ['#f4f4f9', '#3f007d']) 
#    pitch.kdeplot(
#        goals_df['x_scaled'], goals_df['y_scaled'], ax=ax, fill=True, cmap=cmap,
#        n_levels=100, thresh=0, zorder=1, alpha=0.6
#    )
for _, shot in all_shots_df.iterrows():
    x, y = shot['x_scaled'], shot['y_scaled']
    color = 'gold' if "goal" in str(shot['result']).lower() else 'white'
    zorder = 3 if shot['result'].lower() == 'goal' else 2
    size = 500 * float(shot['xG']) if pd.notna(shot['xG']) else 100

    pitch.scatter(x, y, s=size, c=color, edgecolors='black', ax=ax, zorder=zorder)


plt.savefig(os.path.join(ALL_SHOTMAP_DIR, "all_shots.png"), facecolor=fig.get_facecolor())
plt.close(fig)



def plot_team_shotmap(team_name):
    """Generate and save a shotmap for a specific team."""
    df = all_shots_df[all_shots_df['team'] == team_name]

    if df.empty:
        print(f"⚠️ No shots found for {team_name}")
        return
    
    # Create pitch
    pitch = VerticalPitch(pitch_type='statsbomb', pitch_color='#f4f4f9', line_color='black', line_zorder=2, half=True)
    fig, ax = pitch.draw(figsize=(12, 9))
    fig.patch.set_facecolor("#f4f4f9")

    print(f"🔍 {team_name} Shot Data for KDE:\n", df[['x_scaled', 'y_scaled']].head())
    
    for _, shot in df.iterrows():
        x, y = shot['x_scaled'], shot['y_scaled']
        color = 'gold' if shot['result'].lower() == 'goal' else 'white'
        zorder = 3 if shot['result'].lower() == 'goal' else 2
        size = 500 * float(shot['xG']) if pd.notna(shot['xG']) else 100

        pitch.scatter(x, y, s=size, c=color, edgecolors='black', ax=ax, zorder=zorder)

    plt.title(f"{team_name} Shotmap", fontsize=15)

    # ✅ Save shotmap
    team_filename = f"{team_name.replace(' ', '_').lower()}_shotmap.png"
    plt.savefig(os.path.join(TEAM_SHOTMAP_DIR, team_filename))
    plt.close(fig)
    print(f"✅ Saved {team_name} shotmap to {TEAM_SHOTMAP_DIR}{team_filename}")

# Generate team shotmaps
for team in team_shots.keys():
    plot_team_shotmap(team)

print("✅ All Shotmaps Generated! 🎯⚽")

    # Initialize a half-pitch
pitch = VerticalPitch(pitch_type='statsbomb', pitch_color='#f4f4f9', line_color='black', line_zorder=2, half=True)





print("✅ Team Shotmaps Generated!")
print("✅ All Shots Shotmaps Generated!")




















print("All Shotmaps Generated!")


if __name__ == "__main__":
    fixtures_df = load_fixtures()
    historical_fixtures_df = load_match_data()  
    team_data, home_field_advantage = calculate_team_statistics(historical_fixtures_df) 

    # Calculate recent form
    recent_form_att, recent_form_def = calculate_recent_form(historical_fixtures_df, team_data, recent_matches=20, alpha=0.65)  # ✅ Use correct variable

    # Generate heatmaps with blended ratings
    generate_all_heatmaps(team_data, recent_form_att, recent_form_def, alpha=0.65)