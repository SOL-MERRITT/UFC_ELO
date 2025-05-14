# app.py
from flask import Flask, jsonify, render_template
import sqlite3

app = Flask(__name__)
DATABASE = 'ufc_elo_data.db' # Path to your SQLite DB

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row # Allows accessing columns by name
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/fighters')
def get_all_fighters_api():
    conn = get_db_connection()
    fighters_db = conn.execute('SELECT id, name FROM fighters ORDER BY name ASC').fetchall()
    conn.close()
    return jsonify([dict(f) for f in fighters_db])

@app.route('/api/elo_history/<int:fighter_id>')
def get_fighter_elo_history_api(fighter_id):
    conn = get_db_connection()
    fighter_info = conn.execute('SELECT name FROM fighters WHERE id = ?', (fighter_id,)).fetchone()
    if not fighter_info:
        return jsonify({"error": "Fighter not found"}), 404
    fighter_name = fighter_info['name']

    # Fetch ELO history, ensuring chronological order by date, then by original insert order (id) for same-day events
    history_db = conn.execute('''
        SELECT event_date, elo_rating_after_fight
        FROM elo_history
        WHERE fighter_id = ?
        ORDER BY event_date ASC, id ASC
    ''', (fighter_id,)).fetchall()
    conn.close()

    labels = [row['event_date'] for row in history_db]
    data_points = [row['elo_rating_after_fight'] for row in history_db]

    return jsonify({
        'fighter_name': fighter_name,
        'labels': labels,      # Dates
        'data': data_points    # ELO ratings
    })

if __name__ == '__main__':
    # IMPORTANT: Before running for the first time,
    # 1. Run UFC_SCRAPE.py to generate ufc_fights.csv
    # 2. Run UFC_ELO_DB.py to populate ufc_elo_data.db
    app.run(debug=True)