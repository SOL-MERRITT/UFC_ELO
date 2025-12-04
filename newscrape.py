import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime
import db_manager

# --- Configuration ---
# (This section is from your original script for robustness)
BASE_URL = "http://ufcstats.com/statistics/events/completed?page="
session = requests.Session()
headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/90.0.4430.93 Safari/537.36"
    )
}
retry_strategy = Retry(
    total=5,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)


# --- Helper Functions ---
def get_soup(url):
    """A helper function to fetch and parse a URL."""
    try:
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser")
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Could not fetch {url}: {e}")
        return None

def parse_strikes(text):
    """Parses text like 'X of Y' into two integers."""
    parts = text.strip().split(' of ')
    if len(parts) == 2:
        return int(parts[0]), int(parts[1])
    return 0, 0

# --- NEW Core Scraping Functions ---

def scrape_fight_details_page(fight_url):
    """
    Scrapes detailed statistics from a single fight-details page.
    This is the new function that parses the tables based on the source you provided.
    """
    soup = get_soup(fight_url)
    if not soup:
        return {}

    all_stats = {}
    
    # The stats tables are within a <section> tag.
    # We find all tables within that section. The first is Totals, the third is Sig. Strikes.
    sections = soup.find_all("section", class_="b-fight-details__section")
    
    # --- 1. Process the "Totals" Table ---
    # The Totals table is the first one on the page.
    totals_table = sections[1].find("table")
    if totals_table:
        rows = totals_table.find_all('tr')
        # The data is in the second row (index 1)
        cells = rows[1].find_all('td')
        
        # The data for both fighters is inside the same cell, in separate <p> tags.
        # This is a key insight from the source code you provided.
        
        # Prefixes for column names
        f1_prefix = "f1_"
        f2_prefix = "f2_"
        
        # Knockdowns
        all_stats[f1_prefix + 'kd'] = int(cells[1].find_all('p')[0].text.strip())
        all_stats[f2_prefix + 'kd'] = int(cells[1].find_all('p')[1].text.strip())
        
        # Significant Strikes
        f1_sig_landed, f1_sig_att = parse_strikes(cells[2].find_all('p')[0].text)
        f2_sig_landed, f2_sig_att = parse_strikes(cells[2].find_all('p')[1].text)
        all_stats[f1_prefix + 'sig_str_landed'] = f1_sig_landed
        all_stats[f1_prefix + 'sig_str_attempted'] = f1_sig_att
        all_stats[f2_prefix + 'sig_str_landed'] = f2_sig_landed
        all_stats[f2_prefix + 'sig_str_attempted'] = f2_sig_att
        
        # Total Strikes
        f1_total_landed, f1_total_att = parse_strikes(cells[4].find_all('p')[0].text)
        f2_total_landed, f2_total_att = parse_strikes(cells[4].find_all('p')[1].text)
        all_stats[f1_prefix + 'total_str_landed'] = f1_total_landed
        all_stats[f1_prefix + 'total_str_attempted'] = f1_total_att
        all_stats[f2_prefix + 'total_str_landed'] = f2_total_landed
        all_stats[f2_prefix + 'total_str_attempted'] = f2_total_att

        # Takedowns
        f1_td_landed, f1_td_att = parse_strikes(cells[5].find_all('p')[0].text)
        f2_td_landed, f2_td_att = parse_strikes(cells[5].find_all('p')[1].text)
        all_stats[f1_prefix + 'td_landed'] = f1_td_landed
        all_stats[f1_prefix + 'td_attempted'] = f1_td_att
        all_stats[f2_prefix + 'td_landed'] = f2_td_landed
        all_stats[f2_prefix + 'td_attempted'] = f2_td_att

        # Submission Attempts
        all_stats[f1_prefix + 'sub_att'] = int(cells[7].find_all('p')[0].text.strip())
        all_stats[f2_prefix + 'sub_att'] = int(cells[7].find_all('p')[1].text.strip())
        
    # --- 2. Process "Significant Strikes" Table ---
    # This is the third table on the page.
    sig_strikes_table = sections[3].find("table")
    if sig_strikes_table:
        rows = sig_strikes_table.find_all('tr')
        cells = rows[1].find_all('td')

        # Head Strikes
        f1_head_landed, f1_head_att = parse_strikes(cells[3].find_all('p')[0].text)
        f2_head_landed, f2_head_att = parse_strikes(cells[3].find_all('p')[1].text)
        all_stats['f1_head_strikes_landed'] = f1_head_landed
        all_stats['f1_head_strikes_attempted'] = f1_head_att
        all_stats['f2_head_strikes_landed'] = f2_head_landed
        all_stats['f2_head_strikes_attempted'] = f2_head_att

        # Body Strikes
        f1_body_landed, f1_body_att = parse_strikes(cells[4].find_all('p')[0].text)
        f2_body_landed, f2_body_att = parse_strikes(cells[4].find_all('p')[1].text)
        all_stats['f1_body_strikes_landed'] = f1_body_landed
        all_stats['f1_body_strikes_attempted'] = f1_body_att
        all_stats['f2_body_strikes_landed'] = f2_body_landed
        all_stats['f2_body_strikes_attempted'] = f2_body_att

        # Leg Strikes
        f1_leg_landed, f1_leg_att = parse_strikes(cells[5].find_all('p')[0].text)
        f2_leg_landed, f2_leg_att = parse_strikes(cells[5].find_all('p')[1].text)
        all_stats['f1_leg_strikes_landed'] = f1_leg_landed
        all_stats['f1_leg_strikes_attempted'] = f1_leg_att
        all_stats['f2_leg_strikes_landed'] = f2_leg_landed
        all_stats['f2_leg_strikes_attempted'] = f2_leg_att

    return all_stats

# --- Main Script Logic (Updated from your original) ---

def scrape_event_links(max_pages=40):
    """Scrapes all event links from the completed events list."""
    all_events = []
    for page in range(1, max_pages + 1):
        soup = get_soup(BASE_URL + str(page))
        if not soup: continue

        event_list = soup.find_all("a", class_="b-link b-link_style_black")
        for event in event_list:
            if 'event-details' in event.get('href', ''):
                all_events.append({"event_name": event.text.strip(), "event_url": event.get("href")})
        time.sleep(0.5)
    return all_events

def scrape_event_fights(event):
    """
    Scrapes all fight data from a single event page, including drilling
    down into each fight's details page.
    """
    event_name = event["event_name"]
    event_url = event["event_url"]
    fights = []
    
    soup = get_soup(event_url)
    if not soup: return fights

    # Extract event date
    date_text = soup.find("li", class_="b-list__box-list-item").text
    raw_date = date_text.replace("Date:", "").strip()
    event_date = datetime.strptime(raw_date, "%B %d, %Y").strftime("%Y-%m-%d")

    # Select all rows that have a 'data-link', which indicates a fight
    fight_rows = soup.select("tr.b-fight-details__table-row[data-link]")

    for row in fight_rows:
        cells = row.find_all("td")
        fighter_ps = cells[1].find_all("p")
        
        # Basic info from the event page table
        fight_info = {
            "event": event_name,
            "event_date": event_date,
            "fighter_1": fighter_ps[0].text.strip(),
            "fighter_2": fighter_ps[1].text.strip(),
            "result": cells[0].text.strip(),
            "method": cells[7].text.strip(),
            "round": cells[8].text.strip(),
            "time": cells[9].text.strip(),
        }
        
        # --- This is the key addition ---
        # Get the URL to the detailed fight page and scrape it
        fight_details_url = row['data-link']
        detailed_stats = scrape_fight_details_page(fight_details_url)
        
        # Merge the detailed stats into our main fight dictionary
        fight_info.update(detailed_stats)
        
        fights.append(fight_info)
        time.sleep(0.2) # Small delay to be polite to the server

    return fights

def main():
    print("[INFO] Starting scraping process...")
    
    # Initialize Database
    db_manager.init_db()
    
    # Get existing events to avoid duplicates
    existing_events = db_manager.get_existing_event_names()
    print(f"[INFO] Found {len(existing_events)} existing events in DB.")

    # Use max_pages=40 (or appropriate number)
    events = scrape_event_links(max_pages=40)
    if not events:
        print("[INFO] No events found. Exiting.")
        return

    # Filter out existing events
    events_to_scrape = [e for e in events if e['event_name'] not in existing_events]
    
    if not events_to_scrape:
        print("[INFO] All found events are already in the DB. Nothing new to scrape.")
        return

    print(f"[INFO] Found {len(events_to_scrape)} new events to scrape.")

    all_fights_data = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        # We submit the scraping of each event page as a separate job
        future_to_event = {executor.submit(scrape_event_fights, event): event for event in events_to_scrape}
        for future in as_completed(future_to_event):
            try:
                fights_from_event = future.result()
                all_fights_data.extend(fights_from_event)
                print(f"[SUCCESS] Scraped {len(fights_from_event)} fights from: {future_to_event[future]['event_name']}")
            except Exception as exc:
                print(f"[ERROR] An event generated an exception: {exc}")

    if all_fights_data:
        new_df = pd.DataFrame(all_fights_data)
        # Save to DB
        db_manager.save_fights_to_db(new_df)
        print(f"\n[COMPLETE] Scraping finished! Data saved to DB.")
    else:
        print("\n[INFO] No fight data was scraped.")

if __name__ == "__main__":
    main()