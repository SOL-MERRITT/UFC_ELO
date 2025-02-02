import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import concurrent.futures

# Base URL for UFC events
BASE_URL = "http://ufcstats.com/statistics/events/completed?page"

# Create a global session for all requests
session = requests.Session()

def get_page_html(page_number):
    """Fetch and return a BeautifulSoup object for a given event list page."""
    url = BASE_URL + str(page_number)
    response = session.get(url)
    if response.status_code == 200:
        return BeautifulSoup(response.content, "html.parser")
    return None

# ----------------------------
# Step 1: Scrape all event links
# ----------------------------
all_events = []
page_number = 1

while True:
    soup = get_page_html(page_number)
    if not soup:
        break  # Stop if request fails
    event_list = soup.find_all("a", class_="b-link b-link_style_black")
    if not event_list:
        break  # No more events on this page
    for event in event_list:
        event_name = event.text.strip()
        event_url = event['href']
        all_events.append({"event_name": event_name, "event_url": event_url})
    page_number += 1
    time.sleep(0.5)  # Reduced delay between pages

# ----------------------------
# Step 2: Process each event concurrently
# ----------------------------
def process_event(event):
    """Fetch an event page, extract its date and fight details, and return a list of fight records."""
    event_name = event["event_name"]
    event_url = event["event_url"]
    try:
        response = session.get(event_url)
        if response.status_code != 200:
            print(f"Failed to fetch event: {event_name}")
            return []
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Extract event date; adjust the selector if needed.
        date_tag = soup.find("p", class_="b-content__title-info")
        event_date = date_tag.text.split(" - ")[0].strip() if date_tag else ""
        
        # Extract fight details from the fight table.
        fights = []
        fight_table = soup.find("table", class_="b-fight-details__table")
        if fight_table:
            tbody = fight_table.find("tbody")
            if tbody:
                for row in tbody.find_all("tr"):
                    cells = row.find_all("td")
                    if len(cells) < 7:
                        continue  # Skip incomplete rows
                    try:
                        fight_details = {
                            "event": event_name,
                            "event_date": event_date,
                            "fighter_1": cells[1].find_all("p")[0].text.strip(),
                            "fighter_2": cells[1].find_all("p")[1].text.strip(),
                            "winner": cells[0].text.strip(),
                            "method": cells[3].text.strip(),
                            "round": cells[4].text.strip(),
                            "time": cells[5].text.strip(),
                        }
                        fights.append(fight_details)
                    except Exception as e:
                        print(f"Skipping a fight in {event_name} due to error: {e}")
        return fights

    except Exception as e:
        print(f"Error processing event {event_name}: {e}")
        return []

# Use a ThreadPoolExecutor to process events concurrently.
all_fights = []
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    results = executor.map(process_event, all_events)
    for fights in results:
        all_fights.extend(fights)

# ----------------------------
# Step 3: Save data to CSV
# ----------------------------
df = pd.DataFrame(all_fights)
df.to_csv("ufc_fights.csv", index=False)
print("Scraping complete! Data saved as 'ufc_fights.csv'")
