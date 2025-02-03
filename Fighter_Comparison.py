import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from datetime import datetime

matplotlib.use("Agg")  # Prevents GUI issues when running in some environments

# Constants for file paths and styling
CSV_PATH = "ufc_fights_with_elo.csv"
OUTPUT_PATH = "fighter_elo_comparison_chart.png"
BG_COLOR = "#0d1b2a"      # Dark navy blue
AXIS_COLOR = "#1b263b"    # Slightly lighter dark blue
TEXT_COLOR = "#e0e1dd"    # Light grayish blue
COLORS = ["#00b4d8", "#f77f00"]  # Bright cyan & orange

# Load CSV
try:
    fights = pd.read_csv(CSV_PATH, parse_dates=["event_date"])
    fights.sort_values(by="event_date", inplace=True)  # Ensure fights are in chronological order
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

def plot_fighter_elo_comparison(fighter1, fighter2):
    # Filter fights for both fighters
    ff1 = fights[(fights["fighter_1"] == fighter1) | (fights["fighter_2"] == fighter1)].copy()
    ff2 = fights[(fights["fighter_1"] == fighter2) | (fights["fighter_2"] == fighter2)].copy()

    if ff1.empty or ff2.empty:
        print(f"Insufficient data for comparison: {fighter1} ({len(ff1)} fights), {fighter2} ({len(ff2)} fights)")
        return

    # Process fight history for both fighters
    details1 = ff1.apply(lambda row: process_fight(row, fighter1), axis=1)
    details2 = ff2.apply(lambda row: process_fight(row, fighter2), axis=1)

    ff1 = pd.concat([ff1, details1], axis=1)
    ff2 = pd.concat([ff2, details2], axis=1)

    # Ensure dates are datetime and sort chronologically
    ff1["event_date"] = pd.to_datetime(ff1["event_date"])
    ff2["event_date"] = pd.to_datetime(ff2["event_date"])
    ff1.sort_values(by="event_date", inplace=True)
    ff2.sort_values(by="event_date", inplace=True)

    # Extract values for plotting
    dates1, elo1 = ff1["event_date"].tolist(), ff1["elo_end"].tolist()
    dates2, elo2 = ff2["event_date"].tolist(), ff2["elo_end"].tolist()

    # Plotting
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(16, 9))
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(AXIS_COLOR)

    ax.plot(dates1, elo1, marker="o", linestyle="-", linewidth=4, markersize=10, color=COLORS[0], label=fighter1)
    ax.plot(dates2, elo2, marker="o", linestyle="-", linewidth=4, markersize=10, color=COLORS[1], label=fighter2)

    ax.set_xlabel("Date", fontsize=14, fontweight="bold", color=TEXT_COLOR)
    ax.set_ylabel("ELO Rating", fontsize=14, fontweight="bold", color=TEXT_COLOR)
    ax.set_title(f"ELO Rating Comparison: {fighter1} vs {fighter2}", fontsize=16, fontweight="bold", color=TEXT_COLOR)
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%Y-%m-%d"))
    ax.tick_params(axis='x', rotation=45, labelsize=10, colors=TEXT_COLOR)
    ax.tick_params(axis='y', labelsize=12, colors=TEXT_COLOR)

    for spine in ax.spines.values():
        spine.set_color(TEXT_COLOR)

    ax.legend(fontsize=12, facecolor=AXIS_COLOR, edgecolor="white")

    plt.tight_layout()
    plt.savefig(OUTPUT_PATH, facecolor=BG_COLOR, dpi=300)
    print(f"ELO comparison chart saved as {OUTPUT_PATH}.")

    # Print fight history for both fighters
    history1 = pd.DataFrame({
        "Event": ff1["event"],
        "Date": ff1["event_date"].dt.strftime("%Y-%m-%d"),
        "Opponent": ff1["opponent"],
        "Result": ff1["display_result"],
        "ELO Before": ff1.apply(lambda row: row["fighter_1_elo_start"] if row["fighter_1"] == fighter1 else row["fighter_2_elo_start"], axis=1),
        "ELO After": ff1["elo_end"]
    })

    history2 = pd.DataFrame({
        "Event": ff2["event"],
        "Date": ff2["event_date"].dt.strftime("%Y-%m-%d"),
        "Opponent": ff2["opponent"],
        "Result": ff2["display_result"],
        "ELO Before": ff2.apply(lambda row: row["fighter_1_elo_start"] if row["fighter_1"] == fighter2 else row["fighter_2_elo_start"], axis=1),
        "ELO After": ff2["elo_end"]
    })

    print(f"\n{fighter1} Fight History:\n")
    print(history1.to_string(index=False))
    print(f"\n{fighter2} Fight History:\n")
    print(history2.to_string(index=False))

if __name__ == "__main__":
    default1 = "Jon Jones"
    default2 = "Daniel Cormier"
    
    fighter1 = input(f"Enter first fighter name: ").strip() or default1
    fighter2 = input(f"Enter second fighter name: ").strip() or default2
    
    plot_fighter_elo_comparison(fighter1, fighter2)
