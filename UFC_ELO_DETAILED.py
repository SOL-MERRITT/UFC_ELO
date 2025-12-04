import pandas as pd
import math

# --- ELO Configuration ---
DEFAULT_ELO = 1500
K_FACTOR = 40
FINISH_MULTIPLIER = 1.25


def normalize_result(result_raw: str) -> str:
    """Normalize the result text to one of: 'win', 'draw', 'nc', or the raw value.
    The rest of the logic expects 'win' to indicate fighter_1 won; anything else is treated as fighter_2 win,
    unless it's 'draw' or 'nc'.
    """
    if not isinstance(result_raw, str):
        return ""
    value = result_raw.replace("\n", "").strip().lower()
    if "win" in value:
        return "win"
    if "draw" in value:
        return "draw"
    if "nc" in value:
        return "nc"
    return value


def normalize_method(method_raw: str) -> str:
    """Map the method to the tokens used for finish bonus, preserving other values as-is."""
    if not isinstance(method_raw, str):
        return ""
    value = method_raw.replace("\n", "").strip()
    if "KO/TKO" in value:
        return "KO/TKO"
    if "SUB" in value:
        return "SUB"
    return value


def expected_score(elo_a: float, elo_b: float) -> float:
    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))


def compute_elo_for_dataframe(fights_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compute ELO across fights, preserving all original columns and adding ELO columns.

    Returns the updated fights DataFrame and a rankings DataFrame.
    """
    # Ensure date exists and sort chronologically if present
    if "event_date" in fights_df.columns:
        # Parse when possible; ignore errors so non-parseable rows become NaT but sorting still works
        fights_df["event_date"] = pd.to_datetime(fights_df["event_date"], errors="coerce")
        fights_df = fights_df.sort_values(by=["event_date"], ascending=True)

    # Normalize inputs our logic depends on
    if "result" in fights_df.columns:
        fights_df["result"] = fights_df["result"].apply(normalize_result)
    else:
        raise ValueError("Input CSV must contain a 'result' column.")

    if "method" in fights_df.columns:
        fights_df["method"] = fights_df["method"].apply(normalize_method)
    else:
        # If missing, create an empty column so finish bonus never applies
        fights_df["method"] = ""

    required_names = ["fighter_1", "fighter_2"]
    for col in required_names:
        if col not in fights_df.columns:
            raise ValueError(f"Input CSV must contain a '{col}' column.")

    # Storage for current and peak ratings
    fighter_ratings: dict[str, float] = {}
    peak_elo_ratings: dict[str, float] = {}

    def get_fighter_elo(name: str) -> float:
        return fighter_ratings.get(name, DEFAULT_ELO)

    def update_peak(name: str, new_elo: float) -> None:
        current_peak = peak_elo_ratings.get(name, 0)
        if new_elo > current_peak:
            peak_elo_ratings[name] = round(new_elo, 2)

    def update_elo_win(winner: str, loser: str, method: str) -> None:
        winner_elo = get_fighter_elo(winner)
        loser_elo = get_fighter_elo(loser)

        exp_win = expected_score(winner_elo, loser_elo)
        k = K_FACTOR * FINISH_MULTIPLIER if method in ["KO/TKO", "SUB"] else K_FACTOR

        new_winner = winner_elo + k * (1 - exp_win)
        new_loser = loser_elo + k * (0 - (1 - exp_win))

        update_peak(winner, new_winner)
        update_peak(loser, new_loser)

        fighter_ratings[winner] = round(new_winner, 2)
        fighter_ratings[loser] = round(new_loser, 2)

    def update_elo_draw(a: str, b: str) -> None:
        elo_a = get_fighter_elo(a)
        elo_b = get_fighter_elo(b)
        exp_a = expected_score(elo_a, elo_b)
        k = K_FACTOR * 0.5

        new_a = elo_a + k * (0.5 - exp_a)
        new_b = elo_b + k * (0.5 - (1 - exp_a))

        update_peak(a, new_a)
        update_peak(b, new_b)

        fighter_ratings[a] = round(new_a, 2)
        fighter_ratings[b] = round(new_b, 2)

    # Add ELO columns, preserving all existing columns
    fights_df["fighter_1_elo_start"] = 0.0
    fights_df["fighter_2_elo_start"] = 0.0
    fights_df["fighter_1_elo_end"] = 0.0
    fights_df["fighter_2_elo_end"] = 0.0

    # Iterate chronologically
    for index, row in fights_df.iterrows():
        fighter_1 = row["fighter_1"]
        fighter_2 = row["fighter_2"]
        result = row["result"]
        method = row.get("method", "")

        # Initialize unseen fighters
        if fighter_1 not in fighter_ratings:
            fighter_ratings[fighter_1] = DEFAULT_ELO
        if fighter_2 not in fighter_ratings:
            fighter_ratings[fighter_2] = DEFAULT_ELO

        # Record starting ratings
        fights_df.at[index, "fighter_1_elo_start"] = fighter_ratings[fighter_1]
        fights_df.at[index, "fighter_2_elo_start"] = fighter_ratings[fighter_2]

        # Apply result
        if result == "nc":
            fights_df.at[index, "fighter_1_elo_end"] = fighter_ratings[fighter_1]
            fights_df.at[index, "fighter_2_elo_end"] = fighter_ratings[fighter_2]
            continue
        elif result == "draw":
            update_elo_draw(fighter_1, fighter_2)
        else:
            winner = fighter_1 if result == "win" else fighter_2
            loser = fighter_2 if result == "win" else fighter_1
            update_elo_win(winner, loser, method)

        # Record ending ratings
        fights_df.at[index, "fighter_1_elo_end"] = fighter_ratings[fighter_1]
        fights_df.at[index, "fighter_2_elo_end"] = fighter_ratings[fighter_2]

    # Build rankings
    rankings_df = (
        pd.DataFrame([
            {
                "Fighter": fighter,
                "Final ELO": rating,
                "Peak ELO": peak_elo_ratings.get(fighter, rating),
            }
            for fighter, rating in fighter_ratings.items()
        ])
        .sort_values("Final ELO", ascending=False)
        .reset_index(drop=True)
    )

    return fights_df, rankings_df


def main():
    # Read detailed fights CSV generated by newscrape.py
    input_path = "ufc_fights_detailed.csv"
    output_fights_path = "ufc_fights_detailed_with_elo.csv"
    output_rankings_path = "ufc_fighter_rankings_detailed.csv"

    fights_df = pd.read_csv(input_path)

    updated_fights_df, rankings_df = compute_elo_for_dataframe(fights_df)

    # Preserve all columns and write
    updated_fights_df.to_csv(output_fights_path, index=False)
    rankings_df.to_csv(output_rankings_path, index=False)

    print("ELO calculation complete! Files saved:")
    print(f"- {output_fights_path}")
    print(f"- {output_rankings_path}")


if __name__ == "__main__":
    main()


