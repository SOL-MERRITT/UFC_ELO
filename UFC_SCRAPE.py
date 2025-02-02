import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

# Base URL for UFC events
BASE_URL = "http://ufcstats.com/statistics/events/completed?page"

# Initialize session for efficiency
session = requests.Session()

def get_page_html(page_number):
    url = BASE_URL + str(page_number)
    response = session.get(url)
    if response.status_code == 200:
        return BeautifulSoup(response.content, "html.parser")
    return None

# Scrape all pages of completed UFC events
all_events = []
page_number = 1
has_more_pages = True

while has_more_pages:
    soup = get_page_html(page_number)
    if not soup:
        break  # Stop if request fails

    event_list = soup.find_all("a", class_="b-link b-link_style_black")
    if not event_list:
        has_more_pages = False  # Exit if no more events are found on the page
    else:
        for event in event_list:
            event_name = event.text.strip()
            event_url = event['href']
            all_events.append({"event_name": event_name, "event_url": event_url})
        page_number += 1  # Move to the next page
        time.sleep(1)  # Delay to avoid overloading the server

# Convert to DataFrame  
events_df = pd.DataFrame(all_events)

# Scrape fights for each event and include event date
all_fights = []

for index, row in events_df.iterrows():
    event_name = row['event_name']
    event_url = row['event_url']
    
    # Request the event page
    event_response = session.get(event_url)
    if event_response.status_code != 200:
        continue  # Skip if request fails
    
    event_soup = BeautifulSoup(event_response.content, "html.parser")
    
    # Scrape event date:
    # This assumes the event date is contained in a <p> tag with class "b-content__title-info"
    # and that its text is formatted like "July 10, 2021 - Las Vegas, NV".
    date_tag = event_soup.find("p", class_="b-content__title-info")
    event_date = date_tag.text.split(" - ")[0].strip() if date_tag else ""
    
    # Scrape fight details (fight table)
    fight_table = event_soup.find("table", class_="b-fight-details__table")
    if fight_table:
        tbody = fight_table.find("tbody")
        if tbody:
            for fight_row in tbody.find_all("tr"):
                fight_data = fight_row.find_all("td")
                # Ensure the correct number of columns are present
                if len(fight_data) < 7:
                    continue  # Skip invalid rows

                try:
                    fight_details = {
                        "event": event_name,
                        "event_date": event_date,   # Added event date here
                        "fighter_1": fight_data[1].find_all("p")[0].text.strip(),
                        "fighter_2": fight_data[1].find_all("p")[1].text.strip(),
                        "winner": fight_data[0].text.strip(),
                        "method": fight_data[3].text.strip(),
                        "round": fight_data[4].text.strip(),
                        "time": fight_data[5].text.strip(),
                    }
                    all_fights.append(fight_details)
                except IndexError:
                    print(f"Skipping fight in {event_name} due to missing data.")
    
    time.sleep(1)  # 1-second delay between event scrapes

# Convert the list of fights into a DataFrame and save to CSV
all_fights_df = pd.DataFrame(all_fights)
all_fights_df.to_csv("ufcfights.csv", index=False)

print("Scraping complete! Data saved as 'ufc_fights.csv'")
