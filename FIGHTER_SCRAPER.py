import requests
from bs4 import BeautifulSoup
import pandas as pd
import string
import time

def parse_height(height_str):
    """Converts height string (e.g., 5' 11") to inches."""
    if height_str in ['--', None, '']:
        return None
    try:
        feet, inches = height_str.replace('"', '').split("' ")
        return int(feet) * 12 + int(inches)
    except:
        return None

def parse_reach(reach_str):
    """Converts reach string (e.g., 72.0") to float."""
    if reach_str in ['--', None, '']:
        return None
    try:
        return float(reach_str.replace('"', ''))
    except:
        return None

def scrape_all_fighters():
    """
    Scrapes physical attributes for all fighters from ufcstats.com.
    """
    base_url = "http://www.ufcstats.com/statistics/fighters"
    all_fighters = []

    # Loop through each letter of the alphabet
    for char in string.ascii_lowercase:
        url = f"{base_url}?char={char}&page=all"
        print(f"Scraping page: {url}")

        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            # Find the fighter table and all its rows
            table = soup.find("table", class_="b-statistics__table")
            rows = table.find_all("tr", class_="b-statistics__table-row")

            for row in rows:
                cells = row.find_all("td")
                if len(cells) > 1: # Ensure it's a valid fighter row
                    first_name = cells[0].text.strip()
                    last_name = cells[1].text.strip()
                    
                    fighter_details = {
                        'full_name': f"{first_name} {last_name}",
                        'height_inches': parse_height(cells[3].text.strip()),
                        'reach_inches': parse_reach(cells[5].text.strip()),
                        'stance': cells[6].text.strip() if cells[6].text.strip() else None
                    }
                    all_fighters.append(fighter_details)
        except Exception as e:
            print(f"Could not scrape {url}: {e}")
        
        time.sleep(1) # Be polite to the server

    df = pd.DataFrame(all_fighters)
    df.to_csv("ufc_fighter_details.csv", index=False)
    print("\nScraping complete! Data saved to ufc_fighter_details.csv")

if __name__ == "__main__":
    scrape_all_fighters()