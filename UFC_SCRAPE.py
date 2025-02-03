import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime

# --- Configuration ---

# Correct BASE_URL with "=" for the query parameter
BASE_URL = "http://ufcstats.com/statistics/events/completed?page="

# Create a session with a custom User-Agent and retry logic
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
    backoff_factor=1,  # Wait 1s, 2s, 4s, etc.
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET", "HEAD", "OPTIONS"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)

# --- Functions ---

def get_page_html(page_number):
    """Fetch and return a BeautifulSoup object for a given event-list page."""
    url = BASE_URL + str(page_number)
    print(f"[DEBUG] Fetching page {page_number}: {url}")
    try:
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser")
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Error fetching page {page_number}: {e}")
        return None

def scrape_event_links(max_pages=40):
    """
    Scrape event links from the event list pages.
    Set max_pages to a small number for testing.
    """
    all_events = []
    for page in range(1, max_pages + 1):
        soup = get_page_html(page)
        if not soup:
            print(f"[DEBUG] No content on page {page}. Stopping.")
            break

        event_list = soup.find_all("a", class_="b-link b-link_style_black")
        if not event_list:
            print(f"[DEBUG] No event links on page {page}. Stopping.")
            break

        print(f"[DEBUG] Page {page}: Found {len(event_list)} event links.")
        for event in event_list:
            event_name = event.text.strip()
            event_url = event.get("href")
            all_events.append({"event_name": event_name, "event_url": event_url})
        time.sleep(0.5)  # Small delay between pages
    print(f"[DEBUG] Total events scraped: {len(all_events)}")
    return all_events

def scrape_event_details(event):
    """
    Fetch a single event page and extract its fight details.
    Returns a list of fight dictionaries.
    """
    event_name = event["event_name"]
    event_url = event["event_url"]
    fights = []
    try:
        response = session.get(event_url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Skipping event '{event_name}': {e}")
        return fights

    soup = BeautifulSoup(response.content, "html.parser")
    
    # Extract event date
    event_date = None
    date_li = soup.find("li", class_="b-list__box-list-item")
    if date_li:
        date_text = date_li.text.strip()  # Example: "Date: February 01, 2025"
        if "Date:" in date_text:
            raw_date = date_text.replace("Date:", "").strip()  # Extract "February 01, 2025"
            try:
                event_date = datetime.strptime(raw_date, "%B %d, %Y").strftime("%Y-%m-%d")  # Convert to "YYYY-MM-DD"
                print(f"[INFO] Event '{event_name}' Date: {event_date}")
            except ValueError as ve:
                print(f"[ERROR] Date parsing failed for '{event_name}': {ve}")

    # Extract fight details from the fight table
    fight_table = soup.find("table", class_="b-fight-details__table")
    if fight_table:
        tbody = fight_table.find("tbody")
        if tbody:
            for row in tbody.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) < 7:
                    continue  # Skip rows with incomplete data
                try:
                    fighter_paragraphs = cells[1].find_all("p")
                    if len(fighter_paragraphs) < 2:
                        continue

                    fight_details = {
                        "event": event_name,
                        "event_date": event_date,
                        "fighter_1": fighter_paragraphs[0].text.strip(),
                        "fighter_2": fighter_paragraphs[1].text.strip(),
                        "result": cells[0].text.strip(),
                        "method": cells[7].text.strip(),  # Winning method
                        "round": cells[8].text.strip(),
                        "time": cells[9].text.strip(),
                    }
                    fights.append(fight_details)
                except Exception as e:
                    print(f"[ERROR] Skipping a fight in '{event_name}': {e}")
    else:
        print(f"[DEBUG] No fight table found for event '{event_name}'.")
    # Optionally, you might remove or reduce the sleep delay in concurrent mode.
    # time.sleep(0.5)
    return fights

def main():
    print("[INFO] Starting scraping process...")
    # Step 1: Scrape event links (adjust max_pages as needed)
    events = scrape_event_links(max_pages=40)
    if not events:
        print("[INFO] No events found. Exiting.")
        return

    # Step 2: Process event details concurrently
    all_fights = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_event = {executor.submit(scrape_event_details, event): event for event in events}
        for future in as_completed(future_to_event):
            event = future_to_event[future]
            try:
                fights = future.result()
                all_fights.extend(fights)
            except Exception as e:
                print(f"[ERROR] Error processing event '{event['event_name']}': {e}")

    # Step 3: Save to CSV if any fights were found
    if all_fights:
        df = pd.DataFrame(all_fights)
        df.to_csv("ufc_fights.csv", index=False)
        print("[INFO] Scraping complete! Data saved as 'ufc_fights.csv'")
    else:
        print("[INFO] No fight details were extracted.")

if __name__ == "__main__":
    main()
