import pandas as pd
import matplotlib.pyplot as plt
import matplotlib

matplotlib.use("Agg")

# Constants for file paths and styling
CSV_PATH = "ufc_fights_with_elo.csv"
OUTPUT_PATH = "fighter_elo_chart_styled.png"
BG_COLOR = "#0d1b2a"      # Dark navy blue
AXIS_COLOR = "#1b263b"    # Slightly lighter dark blue
TEXT_COLOR = "#e0e1dd"    # Light grayish blue
LINE_COLOR = "#00b4d8"    # Bright cyan

# Load CSV
try:
    fights = pd.read_csv(CSV_PATH)
except Exception as e:
    print("Error loading CSV:", e)
    exit(1)

def get_result(result, is_f1):
    r = result.lower().strip()
    if r in ("nc", "no contest"):
        return "NC"
    if r == "draw":
        return "Draw"
    if r == "win":
        return "Win" if is_f1 else "Loss"
    if r == "loss":
        return "Loss" if is_f1 else "Win"
    return result.capitalize()

def process_fight(row, fighter):
    is_f1 = (row["fighter_1"] == fighter)
    opp = row["fighter_2"] if is_f1 else row["fighter_1"]
    elo_start = row["fighter_1_elo_start"] if is_f1 else row["fighter_2_elo_start"]
    elo_end   = row["fighter_1_elo_end"]   if is_f1 else row["fighter_2_elo_end"]
    return pd.Series({
        "opponent": opp,
        "elo_start": elo_start,
        "elo_end": elo_end,
        "display_result": get_result(row["result"], is_f1)
    })

def plot_fighter_elo(fighter):
    # Filter fights for the fighter and process each row
    ff = fights[(fights["fighter_1"] == fighter) | (fights["fighter_2"] == fighter)].copy()
    if ff.empty:
        print(f"No fights found for {fighter}.")
        return

    details = ff.apply(lambda row: process_fight(row, fighter), axis=1)
    ff = pd.concat([ff, details], axis=1)

    # Create labels and ELO progression
    labels = ff.apply(lambda row: f"{row['event']}\nvs {row['opponent']} ({row['display_result']})", axis=1).tolist()
    elo = ff["elo_end"].tolist()

    # Plotting
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(16, 9))
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(AXIS_COLOR)
    ax.plot(range(len(elo)), elo, marker="o", linestyle="-", linewidth=4, markersize=10, color=LINE_COLOR)
    ax.set_xlabel("Fights", fontsize=14, fontweight="bold", color=TEXT_COLOR)
    ax.set_ylabel("ELO Rating", fontsize=14, fontweight="bold", color=TEXT_COLOR)
    ax.set_title(f"{fighter} ELO Rating Progression", fontsize=16, fontweight="bold", color=TEXT_COLOR)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontweight="bold", fontsize=10, color=TEXT_COLOR)
    for spine in ax.spines.values():
        spine.set_color(TEXT_COLOR)
    if len(elo) > 1:
        ax.legend([fighter], loc="best", fontsize=12, facecolor=AXIS_COLOR, edgecolor="white")
    plt.tight_layout()
    plt.savefig(OUTPUT_PATH, facecolor=BG_COLOR, dpi=300)
    print(f"ELO progression chart saved as {OUTPUT_PATH}.")

    # Print fight history table
    history = pd.DataFrame({
        "Event": ff["event"],
        "Opponent": ff["opponent"],
        "Result": ff["display_result"],
        "ELO Before": ff.apply(lambda row: row["fighter_1_elo_start"] if row["fighter_1"] == fighter else row["fighter_2_elo_start"], axis=1),
        "ELO After": ff["elo_end"]
    })
    print("\nFight History:\n")
    print(history.to_string(index=False))

if __name__ == "__main__":
    default = "Jon Jones"
    fighter = input(f"Enter fighter name: ").strip() or default
    plot_fighter_elo(fighter)
