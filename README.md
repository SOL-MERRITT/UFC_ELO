# **🥊 UFC ELO Rating System**
#### **Scrape, Analyze, and Visualize UFC Fighter Rankings Over Time**

This project scrapes fight data from **UFCStats.com**, calculates **ELO ratings** for all fighters, and provides visualization tools to track and compare fighter performance over time. The system produces both **current and peak ELO rankings** and allows users to **compare fighter ELO progressions**.

---

## **📌 Features**
✔ **Web Scraper** – Collects fight history from [UFCStats.com](http://ufcstats.com/)  
✔ **ELO Rating System** – Dynamically updates fighter ratings based on wins, losses, and finishes  
✔ **Current & Peak ELO Leaderboards** – Generates an up-to-date ranking of all UFC fighters ever 
✔ **Fighter ELO Timeline** – Displays the historical progression of a fighter’s ELO rating  
✔ **Fighter Comparison** – Plots two fighters' ELO ratings over time on the same graph  

---

## **🚀 Usage Guide**

### **1️⃣ Scrape Fight Data**
This script collects fight history from [UFCStats.com](http://ufcstats.com/).
```sh
python UFC_SCRAPE.py
```
✔ Outputs: `ufc_fights.csv` (Raw fight data)  

---

### **2️⃣ Calculate ELO Ratings**
Process the scraped data and compute **current & peak ELO scores** for all fighters.
```sh
python UFC_ELO.py
```
✔ Outputs:
- `ufc_fights_with_elo.csv` – Fight data including ELO scores  
- `ufc_fighter_rankings.csv` – **Current and Peak ELO Leaderboards**  

---

### **3️⃣ View Fighter’s ELO Timeline**
Visualize how a specific fighter’s ELO rating has changed over time.
```sh
python FIGHTER_TIMELINE.py
```
✔ Enter a fighter’s name when prompted.  
✔ Generates a graph showing their ELO evolution.  

---

### **4️⃣ Compare Two Fighters’ ELO Progression**
Compare the historical ELO ratings of two fighters on the same graph.
```sh
python compare_fighters.py
```
✔ Enter two fighter names when prompted.  
✔ Generates a **side-by-side ELO progression chart**.  

---

## **📊 Example Outputs**
### **🔹 ELO Leaderboard (`ufc_fighter_rankings.csv`)**
| Fighter         | Final ELO | Peak ELO |
|----------------|-----------|-----------|
| Jon Jones      | 1870      | 1870      |
| George St-Pierre | 1824      | 1824      |
| Islam Makhachev     | 1823      | 1823      |

---

### **🔹 Fighter’s ELO Timeline**
> **Example:** Jon Jones' ELO progression over time  
📈 **Output: `fighter_elo_chart.png`**  

---

### **🔹 Fighter Comparison**
> **Example:** Jon Jones vs Daniel Cormier ELO over time  
📈 **Output: `fighter_elo_comparison_chart.png`**  

---

## **📌 How the ELO System Works**
- **Base ELO:** All fighters start at **1500**.  
- **K-Factor:** Adjusts how much ELO changes after a fight (**40** by default).  
- **Finishes (KO/TKO, Submission):** Rewarded with a **1.25x ELO boost**.  
- **ELO Adjustments:**  
  - **Win:** Fighter gains ELO, loser loses ELO.  
  - **Loss:** Fighter loses ELO, opponent gains ELO.  
  - **Draw:** Both fighters' ELO ratings adjust slightly.  
  - **No Contest (NC):** No ELO change.  

---

## **🛠️ Dependencies**
Ensure you have the following Python libraries installed:
```
pip install requests beautifulsoup4 pandas matplotlib datetime
```

---

## **📜 To-Do & Future Improvements**
- [ ] **Track different weight classes separately**  
- [ ] **Improve fight data accuracy & filtering**  

---

## **💬 Contributions & Feedback**
Got suggestions or want to contribute? Feel free to:
- **Submit a pull request** 🛠️
- **Report an issue** 🐛
- **Reach out on GitHub** 📨

---

📌 **Enjoy tracking UFC ELO Ratings?** Give this project a ⭐ on GitHub! 🚀🥊

---
