import pandas as pd
from flask import Flask, render_template, request
import numpy as np
from scipy.stats import poisson
import os
import matplotlib.pyplot as plt
from data_loader import load_fixtures, load_match_data, calculate_team_statistics, load_next_gw_fixtures, get_player_data
import datetime
from datetime import datetime

# Flask app initialization
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')


# Load data
match_data = load_match_data()
team_stats, home_field_advantage = calculate_team_statistics(match_data)
fixtures = load_fixtures().to_dict(orient="records")  # Convert DataFrame to a list of dictionaries
@app.route("/epl_fixtures")
def home():
    next_gw_fixtures = load_next_gw_fixtures()

    # Get the current gameweek number dynamically
    current_gw = next_gw_fixtures[0]["round_number"] if next_gw_fixtures else "Unknown"

    return render_template("epl_fixtures.html", fixtures=next_gw_fixtures, current_gw=current_gw)



@app.route("/about")
def about():
    return render_template("about.html")

@app.route('/epl_table')
def table():
    try:
        league_table_file_path = "data/tables/league_table_data.csv"

        if os.path.exists(league_table_file_path):
            league_table_df = pd.read_csv(league_table_file_path)
            league_table = league_table_df.to_dict(orient="records")  # Convert DataFrame to list of dictionaries
        else:
            league_table = []

        return render_template('epl_table.html', league_table=league_table)

    except Exception as e:
        print(f"❌ Error loading league table data: {e}")
        return render_template('epl_table.html', league_table=[])


@app.route('/epl-players')
def epl_players():
    try:
        players = get_player_data()  # Load from the saved file
        next_gw_fixtures = load_next_gw_fixtures()
        current_gw = next_gw_fixtures[0]["round_number"] if next_gw_fixtures else "Unknown"

        # Ensure data is properly structured
        if not isinstance(players, list) or not all(isinstance(player, dict) for player in players):
            print("⚠️ Unexpected player data format")
            players = []

        # Extract unique positions and teams
        unique_positions = sorted(set(player.get("POS", "Unknown") for player in players if isinstance(player, dict)))
        unique_teams = sorted(set(player.get("Team", "Unknown") for player in players if isinstance(player, dict)))

        return render_template('epl_player.html', players=players, positions=unique_positions, teams=unique_teams, current_gw=current_gw)

    except Exception as e:
        print(f"❌ Error loading player data: {e}")
        return render_template('epl_player.html', players=[], positions=[], teams=[], current_gw="Unknown")



@app.route('/filter-players', methods=['POST'])
def filter_players():
    players = get_player_data()
    
    pos_filter = request.json.get("pos", "")
    team_filter = request.json.get("team", "")

    # Apply filtering
    filtered_players = [
        player for player in players 
        if (not pos_filter or pos_filter in player["POS"]) and 
           (not team_filter or team_filter == player["Team"])
    ]

    return jsonify(filtered_players)

# Load fixtures
fixtures_df = load_fixtures()


# this lets us determine the current gameweek along with all completed gameweeks
def get_fixtures_for_week(week_offset=0):
    """ Returns fixtures for the selected completed round. """
    
    # Load fixture data
    fixture_file_path = "data/tables/fixture_data.csv"
    fixtures_df = pd.read_csv(fixture_file_path)

    # Ensure 'round_number' is numeric
    fixtures_df['round_number'] = pd.to_numeric(fixtures_df['round_number'], errors='coerce')

    # Count occurrences of isResult == True per round
    result_counts = fixtures_df[fixtures_df['isResult'] == True].groupby('round_number').size()

    # Get list of completed rounds (where at least 3 results exist)
    completed_rounds = result_counts[result_counts >= 3].index.tolist()
    completed_rounds.sort()  # Ensure they are sorted

    if not completed_rounds:
        raise ValueError("No completed gameweeks with at least 10 results found in fixture_data.")

    # Determine the latest completed gameweek
    latest_round = max(completed_rounds)

    # Adjust for previous/next navigation
    selected_round = latest_round + week_offset

    # Prevent navigation past valid rounds
    selected_round = max(min(completed_rounds), min(max(completed_rounds), selected_round))

    # Filter fixtures for selected round
    weekly_fixtures = fixtures_df[fixtures_df['round_number'] == selected_round].to_dict(orient='records')

    return weekly_fixtures, selected_round, min(completed_rounds), max(completed_rounds)







from datetime import datetime
@app.route('/epl_results')
def results():
    """ Renders the results page with shotmaps and league table """
    try:
        week_offset = int(request.args.get('week_offset', 0))

        # ✅ Get completed fixtures and limits
        weekly_fixtures, current_week, first_gw, last_gw = get_fixtures_for_week(week_offset)

        # ✅ Define shotmap directory
        shotmap_dir = os.path.join("static", "shotmaps")

        # ✅ Filter fixtures where the shotmap image exists
        filtered_fixtures = []
        for fixture in weekly_fixtures:
            shotmap_filename = f"{fixture['home_team']}_{fixture['away_team']}_shotmap.png"
            shotmap_path = os.path.join(shotmap_dir, shotmap_filename)

            if os.path.exists(shotmap_path):  # ✅ Only add if file exists
                filtered_fixtures.append(fixture)

        # ✅ Load League Table Data
        league_table_file_path = "data/tables/league_table_data.csv"

        if os.path.exists(league_table_file_path):
            league_table_df = pd.read_csv(league_table_file_path)
            league_table = league_table_df.to_dict(orient="records")  # Convert DataFrame to list of dictionaries
        else:
            league_table = []

        return render_template(
            "epl_results.html",
            fixtures=filtered_fixtures,  # ✅ Pass filtered fixtures
            week_offset=current_week,
            first_gw=first_gw,
            last_gw=last_gw,
            league_table=league_table  # ✅ Pass league table data
        )

    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return render_template("results.html", fixtures=[], league_table=[], week_offset=0, first_gw=0, last_gw=0)



@app.route('/methodology')
def methodology():
    return render_template('methodology.html')


if __name__ == "__main__":
    app.run(debug=True)