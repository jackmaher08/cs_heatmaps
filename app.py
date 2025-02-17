from flask import Flask, render_template
import numpy as np
from scipy.stats import poisson
import os
import matplotlib.pyplot as plt
from data_loader import load_fixtures, load_match_data, calculate_team_statistics, calculate_recent_form, calculate_league_table

# Flask app initialization
app = Flask(__name__)

# Load data
match_data = load_match_data()
team_stats, home_field_advantage = calculate_team_statistics(match_data)
fixtures = load_fixtures().to_dict(orient="records")  # Convert DataFrame to a list of dictionaries
@app.route("/")
def home():
    return render_template("index.html", fixtures=fixtures)  # Just render, no heatmap generation


@app.route("/about")
def about():
    return render_template("about.html")


# Generate league table data at startup
league_table = calculate_league_table(match_data)

@app.route('/table')
def table():
    return render_template('table.html')  # Ensure table.html exists in templates folder

if __name__ == "__main__":
    app.run(debug=True)