# **Counter-Strike 2 Pro Match Analytics Scraper**

## **📌 Project Overview**

This project is a **Counter-Strike 2 (CS2) analytics tool** designed to scrape **match, game, and player data** from HLTV and other sources, download demos, parse demo files, and analyze player performance. The goal is to help players **gain insights into maps, matchups, and player statistics** using real professional match data.

---

## **🚀 Features**

### **1️⃣ Data Scraping**

- **Match Data:** Scrapes CS2 professional match results (teams, scores, events, etc.).
- **Game Data:** Extracts detailed round-by-round statistics.
- **Player Stats:** Collects individual player performance metrics (kills, deaths, assists, ADR, etc.).

### **2️⃣ Demo File Download & Parsing**

- Automatically **downloads demos** of matches for deeper analysis.
- Parses **demo files** to extract movement, grenade usage, and combat engagements.

### **3️⃣ Player Analytics & Insights**

- **Combines scraped match/player stats with parsed demo data** for in-depth analysis.
- Helps players understand **map control, team strategies, and player efficiency.**
- Generates **matchup insights** to improve player knowledge of specific pro team playstyles.

---

## **🛠️ Tech Stack**

- **Python 3.13.1**
- **Selenium & BeautifulSoup** (for web scraping)
- **PostgreSQL** (for structured data storage)
- **Pandas & NumPy** (for analytics and data processing)
- **SeleniumBase** (for automated demo downloads)
- **HLTV API & Demo Parsing Tools**

---

## **📂 Project Structure**

```
CS2-Analytics/
│── config.py              # Configuration settings (URLs, DB credentials, etc.)
│── main_scraper.py        # Main entry point for scraping match, game, and player data
│── demo_scraper.py        # Downloads and manages demo files
│── demo_parser.py         # Parses demo files for gameplay analytics
│── player_analytics.py    # Processes parsed data for advanced insights
│── db_connection.py       # Handles PostgreSQL database operations
│── data_storage.py        # Inserts and retrieves data efficiently
│── logger_config.py       # Configures logging for debugging & monitoring
│── requirements.txt       # Required dependencies for the project
│── README.md              # Project documentation (this file)
│── __pycache__/           # Auto-generated Python cache (ignored in Git)
│── logs/                  # Log files for debugging (ignored in Git)
└── __pycache__/           # Python bytecode cache
```

---

## **⚙️ Installation & Setup**

### **🔹 1. Clone the Repository**

```sh
git clone https://github.com/yourusername/CS2-Analytics.git
cd CS2-Analytics
```

### **🔹 2. Create a Virtual Environment**

```sh
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### **🔹 3. Install Dependencies**

```sh
pip install -r requirements.txt
```

### **🔹 4. Set Up Database**

Ensure you have **PostgreSQL installed** and update `config.py` with your database credentials.

```python
DB_NAME = "cs2_db"
DB_USER = "your_user"
DB_PASS = "your_password"
DB_HOST = "localhost"
DB_PORT = "5432"
```

Run:

```sh
python db_connection.py  # Ensures tables are created
```

### **🔹 5. Run the Scraper**

```sh
python main_scraper.py
```

### **🔹 6. Run Demo Download & Parsing**

```sh
python demo_scraper.py
python demo_parser.py
```

### **🔹 7. Generate Player Analytics**

```sh
python player_analytics.py
```

---

## **📊 Data Insights & Usage**

### **🔍 Match & Player Stats**

- View **per-match player performance**.
- Compare **teams' win rates on specific maps**.
- Identify **key players in matchups**.

### **📈 Demo Analysis**

- **Heatmaps** of player movements.
- **Grenade usage patterns** and efficiency.
- **Kill zone maps** showing key engagements.

### **🤖 Future Improvements**

- AI-based **predictive modeling** for player performance.
- **Automated video highlight generation** from demos.
- **Cloud database integration** for long-term data storage.

---

## **📝 License**

This project is licensed under the **MIT License** – feel free to contribute and modify!

---

## **🙌 Contributing**

### **Want to help improve this project?**

1. **Fork the repository** on GitHub.
2. **Create a feature branch** (`git checkout -b new-feature`).
3. **Commit changes** (`git commit -m "Added new feature"`).
4. **Push to GitHub** (`git push origin new-feature`).
5. **Submit a Pull Request** – we review & merge!

---

## **📬 Contact & Support**

Have questions or want to contribute? Reach out!

- GitHub Issues: [Your Repository Issues Page](https://github.com/yourusername/CS2-Analytics/issues)
- Email: [your.email@example.com](mailto\:your.email@example.com)

🚀 **Happy Analyzing!** 🎯

