import pandas as pd
import math

# ELO Configuration
DEFAULT_ELO = 1500  # Start all fighters at 1500
K_FACTOR = 40  # Fixed K-Factor for all fights
FINISH_MULTIPLIER = 1.2  # 1.2× for KO/TKO and Sub wins

# Load fight data and sort from oldest to newest
fights_df = pd.read_csv("ufcfights.csv")
fights_df = fights_df.sort_index(ascending=False)  # Ensure chronological order

# Clean up `method` column
fights_df["method"] = fights_df["method"].str.replace("\n", "").str.strip()
fights_df["method"] = fights_df["method"].apply(
    lambda x: "KO" if "KO" in x else ("SUB" if "SUB" in x else x)
)

# Fighter ELO ratings storage
fighter_ratings = {}
peak_elo_ratings = {}

# Function to retrieve fighter ELO rating
def get_fighter_elo(fighter):
    return fighter_ratings.get(fighter, DEFAULT_ELO)

# Function to calculate expected score
def expected_score(elo_a, elo_b):
    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))

# Function to update ELO ratings
def update_elo(winner, loser, method):
    """Update ELO ratings based on fight result, with multipliers for KO/Sub finishes."""
    global fighter_ratings, peak_elo_ratings

    # Get current ratings
    rating_winner = get_fighter_elo(winner)
    rating_loser = get_fighter_elo(loser)

    # Compute expected scores
    expected_winner = expected_score(rating_winner, rating_loser)
    expected_loser = 1 - expected_winner

    # Determine if KO/TKO or Submission (apply 1.2× multiplier)
    k_factor = K_FACTOR * FINISH_MULTIPLIER if method in ["KO", "SUB"] else K_FACTOR

    # ELO calculation
    new_winner_rating = rating_winner + k_factor * (1 - expected_winner)
    new_loser_rating = rating_loser + k_factor * (0 - expected_loser)

    # Update peak ELO if this is their highest rating ever
    if winner not in peak_elo_ratings or new_winner_rating > peak_elo_ratings[winner]:
        peak_elo_ratings[winner] = round(new_winner_rating, 2)
    if loser not in peak_elo_ratings or new_loser_rating > peak_elo_ratings[loser]:
        peak_elo_ratings[loser] = round(new_loser_rating, 2)

    # Update fighter records
    fighter_ratings[winner] = round(new_winner_rating, 2)
    fighter_ratings[loser] = round(new_loser_rating, 2)

# Create columns for ELO history
fights_df["fighter_1_elo_start"] = 0
fights_df["fighter_2_elo_start"] = 0
fights_df["fighter_1_elo_end"] = 0
fights_df["fighter_2_elo_end"] = 0

# Process fights and update ELO
for index, fight in fights_df.iterrows():
    fighter_1 = fight["fighter_1"]
    fighter_2 = fight["fighter_2"]
    method = fight["method"]

    # Skip No Contests (no ELO change)
    if "No Contest" in method:
        continue

    # Determine winner & loser
    if fight["result"] == "win":
        winner, loser = fighter_1, fighter_2
    else:
        winner, loser = fighter_2, fighter_1  # `fighter_2` won the fight

    # Initialize fighters in the rating system if not present
    if fighter_1 not in fighter_ratings:
        fighter_ratings[fighter_1] = DEFAULT_ELO
    if fighter_2 not in fighter_ratings:
        fighter_ratings[fighter_2] = DEFAULT_ELO

    # Get starting ELO ratings
    fighter_1_elo_start = fighter_ratings[fighter_1]
    fighter_2_elo_start = fighter_ratings[fighter_2]

    # Record starting ELO ratings
    fights_df.at[index, "fighter_1_elo_start"] = fighter_1_elo_start
    fights_df.at[index, "fighter_2_elo_start"] = fighter_2_elo_start

    # Update ELO based on fight result
    update_elo(winner, loser, method)

    # Record updated ELO ratings
    fights_df.at[index, "fighter_1_elo_end"] = fighter_ratings[fighter_1]
    fights_df.at[index, "fighter_2_elo_end"] = fighter_ratings[fighter_2]

# Convert ELO dictionary to DataFrame
elo_data = [{"Fighter": fighter, "Final ELO": rating, "Peak ELO": peak_elo_ratings[fighter]} for fighter, rating in fighter_ratings.items()]
elo_df = pd.DataFrame(elo_data)

# Sort by highest ELO
elo_df = elo_df.sort_values(by="Final ELO", ascending=False)

# Save results to CSV files
fights_df.to_csv("ufc_fights_with_elo.csv", index=False)
elo_df.to_csv("ufc_fighter_rankings.csv", index=False)

print("ELO Calculation Complete! Data saved to:")
print("- 'ufc_fights_with_elo.csv' (per-fight ELO history).")
print("- 'ufc_fighter_rankings.csv' (final rankings & peak ELO).")
