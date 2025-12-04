import pandas as pd
import os
import db_manager
from elo_engine import EloRatingSystem

# --- Helper Functions (Preserved from original) ---

def normalize_result(result_raw):
    """Normalize the result text."""
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

def normalize_method(method_raw):
    """Normalize the method text."""
    if not isinstance(method_raw, str):
        return ""
    value = method_raw.replace("\n", "").strip()
    if "KO/TKO" in value:
        return "KO/TKO"
    if "SUB" in value:
        return "SUB"
    return value

def migrate_csv_to_db_if_needed():
    """
    If the database is empty but the legacy CSV exists, migrate data to DB.
    """
    csv_path = "ufc_fights_detailed.csv"
    if not os.path.exists(db_manager.DB_NAME) or db_manager.load_fights().empty:
        if os.path.exists(csv_path):
            print(f"[INFO] Migrating existing data from {csv_path} to database...")
            try:
                df = pd.read_csv(csv_path)
                # Ensure columns match schema roughly by saving
                # (db_manager handles it, provided columns match names)
                db_manager.init_db() # ensure table exists
                db_manager.save_fights_to_db(df)
                print("[SUCCESS] Migration complete.")
            except Exception as e:
                print(f"[ERROR] Migration failed: {e}")

def main():
    # 1. Initialize / Migrate Data
    db_manager.init_db()
    migrate_csv_to_db_if_needed()

    # 2. Load Data from DB
    print("[INFO] Loading fights from database...")
    fights_df = db_manager.load_fights()
    
    if fights_df.empty:
        print("[WARNING] No fights found in database. Run the scraper first.")
        return

    # 3. Pre-process / Normalize
    # (We do this here to ensure the engine gets clean data)
    if "result" in fights_df.columns:
        fights_df["result"] = fights_df["result"].apply(normalize_result)
    
    if "method" in fights_df.columns:
        fights_df["method"] = fights_df["method"].apply(normalize_method)
    else:
        fights_df["method"] = ""

    # 4. Calculate ELO
    print("[INFO] Calculating ELO ratings...")
    engine = EloRatingSystem()
    fights_df_with_elo = engine.process_fights(fights_df)
    
    # 5. Generate Rankings
    rankings_df = engine.get_rankings()

    # 6. Save Outputs
    output_fights_path = "ufc_fights_detailed_with_elo.csv"
    output_rankings_path = "ufc_fighter_rankings_detailed.csv"
    
    fights_df_with_elo.to_csv(output_fights_path, index=False)
    rankings_df.to_csv(output_rankings_path, index=False)
    
    print("ELO calculation complete! Files saved:")
    print(f"- {output_fights_path}")
    print(f"- {output_rankings_path}")

    # 7. Update DB with calculated ELOs
    # (Optional but good for persistence)
    print("[INFO] Updating database with calculated ELOs...")
    db_manager.update_elo_columns(fights_df_with_elo)

if __name__ == "__main__":
    main()
