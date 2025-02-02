import pandas as pd
import math

# ELO Configuration
DEFAULT_ELO = 1500
K_FACTOR = 40
FINISH_MULTIPLIER = 1.25

# Load and prepare data
fights_df = pd.read_csv("ufcfights.csv")
fights_df = fights_df.sort_index(ascending=False)

# Clean results and methods
fights_df["result"] = fights_df["result"].str.replace(r"\n+", "", regex=True).str.strip().str.lower()
fights_df["result"] = fights_df["result"].apply(
    lambda x: "win" if "win" in x else "draw" if "draw" in x else "nc" if "nc" in x else x
)

fights_df["method"] = fights_df["method"].str.replace("\n", "").str.strip()
fights_df["method"] = fights_df["method"].apply(
    lambda x: "KO/TKO" if "KO/TKO" in x else ("SUB" if "SUB" in x else x)
)

# ELO storage
fighter_ratings = {}
peak_elo_ratings = {}

def get_fighter_elo(fighter):
    return fighter_ratings.get(fighter, DEFAULT_ELO)

def expected_score(elo_a, elo_b):
    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))

def update_elo_win(winner, loser, method):
    winner_elo = get_fighter_elo(winner)
    loser_elo = get_fighter_elo(loser)
    
    expected_win = expected_score(winner_elo, loser_elo)
    k = K_FACTOR * FINISH_MULTIPLIER if method in ["KO/TKO", "SUB"] else K_FACTOR
    
    new_winner = winner_elo + k * (1 - expected_win)
    new_loser = loser_elo + k * (0 - (1 - expected_win))
    
    update_peak_elo(winner, new_winner)
    update_peak_elo(loser, new_loser)
    
    fighter_ratings[winner] = round(new_winner, 2)
    fighter_ratings[loser] = round(new_loser, 2)

def update_elo_draw(fighter_a, fighter_b):
    elo_a = get_fighter_elo(fighter_a)
    elo_b = get_fighter_elo(fighter_b)
    
    expected_a = expected_score(elo_a, elo_b)
    k = K_FACTOR * 0.5  # Reduced K-factor for draws
    
    new_a = elo_a + k * (0.5 - expected_a)
    new_b = elo_b + k * (0.5 - (1 - expected_a))
    
    update_peak_elo(fighter_a, new_a)
    update_peak_elo(fighter_b, new_b)
    
    fighter_ratings[fighter_a] = round(new_a, 2)
    fighter_ratings[fighter_b] = round(new_b, 2)

def update_peak_elo(fighter, new_elo):
    current_peak = peak_elo_ratings.get(fighter, 0)
    if new_elo > current_peak:
        peak_elo_ratings[fighter] = round(new_elo, 2)

# Initialize ELO tracking columns
fights_df["fighter_1_elo_start"] = 0.0
fights_df["fighter_2_elo_start"] = 0.0
fights_df["fighter_1_elo_end"] = 0.0
fights_df["fighter_2_elo_end"] = 0.0

# Process fights
for index, fight in fights_df.iterrows():
    f1, f2 = fight["fighter_1"], fight["fighter_2"]
    result = fight["result"]
    
    # Initialize ratings if needed
    for fighter in [f1, f2]:
        if fighter not in fighter_ratings:
            fighter_ratings[fighter] = DEFAULT_ELO
    
    # Record starting ELOs
    fights_df.at[index, "fighter_1_elo_start"] = fighter_ratings[f1]
    fights_df.at[index, "fighter_2_elo_start"] = fighter_ratings[f2]
    
    # Handle different result types
    if result == "nc":
        # No ELO changes, just copy start to end
        fights_df.at[index, "fighter_1_elo_end"] = fighter_ratings[f1]
        fights_df.at[index, "fighter_2_elo_end"] = fighter_ratings[f2]
        continue
        
    elif result == "draw":
        update_elo_draw(f1, f2)
    else:
        winner = f1 if result == "win" else f2
        loser = f2 if result == "win" else f1
        update_elo_win(winner, loser, fight["method"])
    
    # Record ending ELOs
    fights_df.at[index, "fighter_1_elo_end"] = fighter_ratings[f1]
    fights_df.at[index, "fighter_2_elo_end"] = fighter_ratings[f2]

# Generate final rankings
elo_df = pd.DataFrame([
    {
        "Fighter": fighter,
        "Final ELO": rating,
        "Peak ELO": peak_elo_ratings.get(fighter, rating)
    }
    for fighter, rating in fighter_ratings.items()
]).sort_values("Final ELO", ascending=False)

# Save results
fights_df.to_csv("ufc_fights_with_elo.csv", index=False)
elo_df.to_csv("ufc_fighter_rankings.csv", index=False)

print("ELO calculation complete! Files saved:")
print("- ufc_fights_with_elo.csv")
print("- ufc_fighter_rankings.csv")