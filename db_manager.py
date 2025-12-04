import sqlite3
import pandas as pd
import os

DB_NAME = "ufc_data.db"

def init_db(db_name=DB_NAME):
    """Initialize the SQLite database with the fights table."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # Create Fights Table with comprehensive schema
    # We map pandas dtypes to SQLite types implicitly where possible, but explicit is better.
    # Most stats are Integers.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event TEXT,
            event_date TEXT,
            fighter_1 TEXT,
            fighter_2 TEXT,
            result TEXT,
            method TEXT,
            round TEXT,
            time TEXT,
            
            -- Fighter 1 Stats
            f1_kd INTEGER,
            f1_sig_str_landed INTEGER,
            f1_sig_str_attempted INTEGER,
            f1_total_str_landed INTEGER,
            f1_total_str_attempted INTEGER,
            f1_td_landed INTEGER,
            f1_td_attempted INTEGER,
            f1_sub_att INTEGER,
            f1_head_strikes_landed INTEGER,
            f1_head_strikes_attempted INTEGER,
            f1_body_strikes_landed INTEGER,
            f1_body_strikes_attempted INTEGER,
            f1_leg_strikes_landed INTEGER,
            f1_leg_strikes_attempted INTEGER,
            
            -- Fighter 2 Stats
            f2_kd INTEGER,
            f2_sig_str_landed INTEGER,
            f2_sig_str_attempted INTEGER,
            f2_total_str_landed INTEGER,
            f2_total_str_attempted INTEGER,
            f2_td_landed INTEGER,
            f2_td_attempted INTEGER,
            f2_sub_att INTEGER,
            f2_head_strikes_landed INTEGER,
            f2_head_strikes_attempted INTEGER,
            f2_body_strikes_landed INTEGER,
            f2_body_strikes_attempted INTEGER,
            f2_leg_strikes_landed INTEGER,
            f2_leg_strikes_attempted INTEGER,
            
            -- ELO Columns (calculated later)
            f1_elo_start REAL,
            f1_elo_end REAL,
            f2_elo_start REAL,
            f2_elo_end REAL
        )
    ''')
    
    # Create an index on event_date for sorting
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_event_date ON fights(event_date)')
    # Create an index on fighter names for lookups
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_fighter_1 ON fights(fighter_1)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_fighter_2 ON fights(fighter_2)')
    
    conn.commit()
    conn.close()
    print(f"[INFO] Database initialized at {db_name}")

def get_existing_event_names(db_name=DB_NAME):
    """Returns a set of event names already in the database."""
    if not os.path.exists(db_name):
        return set()
    
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT DISTINCT event FROM fights")
        events = {row[0] for row in cursor.fetchall()}
    except sqlite3.OperationalError:
        # Table might not exist yet
        events = set()
    conn.close()
    return events

def save_fights_to_db(df, db_name=DB_NAME):
    """Appends a DataFrame of fights to the database."""
    if df.empty:
        return

    conn = sqlite3.connect(db_name)
    
    # Ensure columns exist in DF before writing (fill missing with 0 or None)
    # We need to handle the case where the scraper might miss some columns if they weren't on the page
    # (though the scraper logic seems to init them).
    
    # Write to DB
    # if_exists='append' will append rows. 
    # Note: to_sql doesn't automatically handle schema changes (new columns). 
    # We assume the table schema matches the DF or is a superset.
    try:
        df.to_sql("fights", conn, if_exists="append", index=False)
        print(f"[SUCCESS] Saved {len(df)} fights to database.")
    except Exception as e:
        print(f"[ERROR] Failed to save to DB: {e}")
    finally:
        conn.close()

def load_fights(db_name=DB_NAME):
    """Loads all fights from the database into a DataFrame."""
    if not os.path.exists(db_name):
        print("[WARNING] Database does not exist.")
        return pd.DataFrame()
    
    conn = sqlite3.connect(db_name)
    try:
        df = pd.read_sql("SELECT * FROM fights ORDER BY event_date", conn)
    except Exception as e:
        print(f"[ERROR] Failed to load from DB: {e}")
        df = pd.DataFrame()
    finally:
        conn.close()
    
    return df

def update_elo_columns(df, db_name=DB_NAME):
    """
    Updates the ELO columns in the database based on a DataFrame that contains the calculated ELOs.
    This is a bit complex in SQLite without a unique ID for every row in the DF matching the DB.
    Ideally, we assume the DF was loaded from the DB and has the 'id' column.
    """
    if 'id' not in df.columns:
        print("[WARNING] DataFrame missing 'id' column. Cannot update specific rows in DB.")
        return

    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # We'll update row by row or use executemany.
    # We want to update f1_elo_start, f1_elo_end, f2_elo_start, f2_elo_end
    
    data_to_update = []
    for _, row in df.iterrows():
        data_to_update.append((
            row.get('f1_elo_start'), row.get('f1_elo_end'),
            row.get('f2_elo_start'), row.get('f2_elo_end'),
            row['id']
        ))
    
    cursor.executemany('''
        UPDATE fights 
        SET f1_elo_start = ?, f1_elo_end = ?, f2_elo_start = ?, f2_elo_end = ?
        WHERE id = ?
    ''', data_to_update)
    
    conn.commit()
    conn.close()
    print(f"[INFO] Updated ELO columns for {len(data_to_update)} rows in DB.")

