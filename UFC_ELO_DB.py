# UFC_ELO_DB.py (or integrate into your existing UFC_ELO.py)
import pandas as pd
import sqlite3
from datetime import datetime

DATABASE_NAME = 'ufc_elo_data.db'
DEFAULT_ELO = 1500
K_FACTOR = 40 # Make sure these match your UFC_ELO.py
FINISH_MULTIPLIER = 1.25

def init_db():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fighters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS elo_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fighter_id INTEGER NOT NULL,
            event_date TEXT NOT NULL,
            elo_rating_after_fight REAL NOT NULL,
            opponent_name TEXT,
            event_name TEXT,
            result TEXT,
            FOREIGN KEY (fighter_id) REFERENCES fighters (id)
        )
    ''')
    # Optional: Clear data for a full rebuild (be careful)
    # cursor.execute('DELETE FROM elo_history')
    # cursor.execute('DELETE FROM fighters')
    # cursor.execute('DELETE FROM sqlite_sequence WHERE name="fighters";') # Reset autoincrement for fighters
    # cursor.execute('DELETE FROM sqlite_sequence WHERE name="elo_history";')# Reset autoincrement for elo_history
    conn.commit()
    conn.close()
    print("Database initialized/checked.")

def get_or_create_fighter_id(conn, fighter_name):
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM fighters WHERE name = ?", (fighter_name,))
    row = cursor.fetchone()
    if row:
        return row[0]
    else:
        cursor.execute("INSERT INTO fighters (name) VALUES (?)", (fighter_name,))
        conn.commit()
        return cursor.lastrowid

def store_elo_datapoint(conn, fighter_id, event_date_str, elo_after, opponent_name, event_name, fight_result):
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO elo_history
        (fighter_id, event_date, elo_rating_after_fight, opponent_name, event_name, result)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (fighter_id, event_date_str, elo_after, opponent_name, event_name, fight_result))
    conn.commit()

# --- Your ELO calculation functions (get_fighter_elo, expected_score, etc.) ---
# These will read from the `fighter_ratings` dictionary
fighter_ratings_global = {} # Use this to track current ELOs during processing

def get_fighter_elo(fighter): # Modified for global dict
    return fighter_ratings_global.get(fighter, DEFAULT_ELO)

def update_elo_win(winner, loser, method): # Modified for global dict
    winner_elo = get_fighter_elo(winner)
    loser_elo = get_fighter_elo(loser)
    expected_win = 1 / (1 + 10 ** ((loser_elo - winner_elo) / 400))
    k = K_FACTOR * FINISH_MULTIPLIER if method in ["KO/TKO", "SUB"] else K_FACTOR
    new_winner = winner_elo + k * (1 - expected_win)
    new_loser = loser_elo + k * (0 - (1 - expected_win))
    fighter_ratings_global[winner] = round(new_winner, 2)
    fighter_ratings_global[loser] = round(new_loser, 2)
    # Peak ELO logic can be added here if needed for a separate table/column

def update_elo_draw(fighter_a, fighter_b): # Modified for global dict
    elo_a = get_fighter_elo(fighter_a)
    elo_b = get_fighter_elo(fighter_b)
    expected_a = 1 / (1 + 10 ** ((elo_b - elo_a) / 400))
    k = K_FACTOR * 0.5
    new_a = elo_a + k * (0.5 - expected_a)
    new_b = elo_b + k * (0.5 - (1 - expected_a))
    fighter_ratings_global[fighter_a] = round(new_a, 2)
    fighter_ratings_global[fighter_b] = round(new_b, 2)


def process_fights_and_populate_db():
    init_db() # Ensure tables exist
    conn = sqlite3.connect(DATABASE_NAME)

    try:
        fights_df = pd.read_csv("ufc_fights.csv", parse_dates=["event_date"], dayfirst=False)
    except FileNotFoundError:
        print("ERROR: ufc_fights.csv not found. Run UFC_SCRAPE.py first.")
        return
    fights_df = fights_df.sort_values(by="event_date", ascending=True)

    # Clean results and methods (copy from your UFC_ELO.py)
    fights_df["result_original"] = fights_df["result"] # Keep original for winner determination
    fights_df["result"] = fights_df["result"].str.replace(r"\n+", "", regex=True).str.strip().str.lower()
    fights_df["result_normalized"] = fights_df["result"].apply(
        lambda x: "win" if "win" in x else ("draw" if "draw" in x else ("nc" if "nc" in x else x))
    )
    fights_df["method"] = fights_df["method"].str.replace("\n", "").str.strip()
    fights_df["method"] = fights_df["method"].apply(
        lambda x: "KO/TKO" if "KO/TKO" in x else ("SUB" if "SUB" in x else x)
    )

    fighter_ratings_global.clear() # Reset for fresh calculation

    # To store an initial ELO point before the first fight
    fighters_first_fight_date = {}
    for fighter_name in pd.concat([fights_df['fighter_1'], fights_df['fighter_2']]).unique():
        fighter_id = get_or_create_fighter_id(conn, fighter_name)
        first_fight_date = fights_df[
            (fights_df['fighter_1'] == fighter_name) | (fights_df['fighter_2'] == fighter_name)
        ]['event_date'].min()

        if pd.notna(first_fight_date):
             # Store DEFAULT_ELO one day before their actual first fight
            initial_elo_date = (first_fight_date - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
            store_elo_datapoint(conn, fighter_id, initial_elo_date, DEFAULT_ELO, "N/A", "Initial Rating", "Initial")


    for index, fight in fights_df.iterrows():
        f1_name, f2_name = fight["fighter_1"], fight["fighter_2"]
        event_date_dt = fight["event_date"] # datetime object
        event_date_str = event_date_dt.strftime('%Y-%m-%d') # String for DB
        event_name = fight["event"]
        method = fight["method"]
        
        # Determine winner based on the original 'result' field
        # This assumes 'result_original' column text ("win", "loss", "draw", "nc") refers to fighter_1
        raw_outcome_f1 = str(fight["result_original"]).lower().strip()

        # Get ELOs before the fight (from our global tracker)
        f1_elo_before = get_fighter_elo(f1_name)
        f2_elo_before = get_fighter_elo(f2_name)

        f1_result_for_history, f2_result_for_history = "", ""

        if "nc" in raw_outcome_f1 or "no contest" in raw_outcome_f1 :
            # ELOs don't change
            fighter_ratings_global[f1_name] = f1_elo_before
            fighter_ratings_global[f2_name] = f2_elo_before
            f1_result_for_history = f2_result_for_history = "NC"
        elif "draw" in raw_outcome_f1:
            update_elo_draw(f1_name, f2_name)
            f1_result_for_history = f2_result_for_history = "Draw"
        elif "win" in raw_outcome_f1: # fighter_1 won
            update_elo_win(f1_name, f2_name, method)
            f1_result_for_history = "Win"
            f2_result_for_history = "Loss"
        elif "loss" in raw_outcome_f1: # fighter_1 lost, so fighter_2 won
            update_elo_win(f2_name, f1_name, method)
            f1_result_for_history = "Loss"
            f2_result_for_history = "Win"
        else:
            print(f"Warning: Unknown result '{raw_outcome_f1}' for fight {f1_name} vs {f2_name}. Skipping ELO update.")
            fighter_ratings_global[f1_name] = f1_elo_before # No change
            fighter_ratings_global[f2_name] = f2_elo_before # No change
            f1_result_for_history = f2_result_for_history = "Unknown"


        f1_id = get_or_create_fighter_id(conn, f1_name)
        f2_id = get_or_create_fighter_id(conn, f2_name)

        # Store ELO *after* fight for both fighters
        store_elo_datapoint(conn, f1_id, event_date_str, fighter_ratings_global.get(f1_name, DEFAULT_ELO), f2_name, event_name, f1_result_for_history)
        store_elo_datapoint(conn, f2_id, event_date_str, fighter_ratings_global.get(f2_name, DEFAULT_ELO), f1_name, event_name, f2_result_for_history)

    conn.close()
    print("ELO calculation and database population complete.")
    print(f"Data stored in {DATABASE_NAME}")

if __name__ == "__main__":
    # 1. Make sure UFC_SCRAPE.py has been run to create ufc_fights.csv
    process_fights_and_populate_db()