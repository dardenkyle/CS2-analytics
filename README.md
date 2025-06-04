# 🎯 CS2 Analytics – Pro Match Data Pipeline

**CS2 Analytics** is a modular backend pipeline that scrapes and analyzes **Counter-Strike 2 professional match data** from HLTV, downloads and parses demo files, and provides structured insights into players, teams, and map performance. Designed for esports analysts, bettors, and curious fans, the system emphasizes **auditability**, **modularity**, and **future API readiness**.

---

## 🚀 Features

### 🔹 Match Scraping

- Collects structured match data (teams, scores, events, map links) using **SeleniumBase** and **BeautifulSoup**
- Queues map URLs for asynchronous parsing
- Tracks scraping status and completeness via metadata fields and timestamps

### 🔹 Demo File Handling (Planned)

- Auto-downloads `.dem` files from HLTV
- Parses player POVs for movement, grenades, and engagements (under development)

### 🔹 Structured Analytics

- Normalized **PostgreSQL schema** with foreign keys and audit timestamps
- Per-map **player statistics**, team tracking, aliases, and transfers
- Designed for **reprocessing and historical accuracy**

---

## 🧱 Tech Stack

| Category           | Tools Used                                                                 |
|--------------------|----------------------------------------------------------------------------|
| **Language**       | Python 3.13+                                                               |
| **Scraping**       | SeleniumBase, BeautifulSoup                                                |
| **Database**       | PostgreSQL, SQLAlchemy, Alembic                                            |
| **Architecture**   | Queue-based scraping, modular services, OOP, structured logging            |
| **Testing**        | Pytest, CLI tools                                                          |
| **Deployment Ready** | `.env` configs, Docker-friendly structure, CI/CD ready                    |

---

## 📂 Project Structure

```
cs2_analytics/
├── match_scraper/         # Collects match pages and metadata
├── match_parser/          # Extracts structured data from soup
├── map_scrape_queue/      # Queues maps for scraping and demo download
├── player_stats/          # Handles player extraction and stat storage
├── database/              # DB session management and schema definitions
├── utils/                 # Shared utilities and logger setup
├── main.py                # Batch controller for match scraping
├── README.md
└── ...
```

---

## ⚙️ Installation & Setup

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/yourusername/cs2-analytics.git
cd cs2-analytics
```

### 2️⃣ Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
```

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 4️⃣ Configure Environment

Create a `.env` file with your PostgreSQL credentials:

```env
SQLALCHEMY_DATABASE_URL=postgresql://user:pass@localhost:5432/cs2_analytics_db
```

---

## 🔁 Usage

### Run Match Scraper

```bash
python cs2_analytics/main.py
```

### Run Map Parser (Queued)

```bash
python cs2_analytics/map_scraper/main.py
```

*(Demo file parsing module is in development)*

---

## 📈 Planned Features

- [ ] Demo file ingestion and parsed POV analytics
- [ ] REST API to expose insights
- [ ] Player performance dashboards
- [ ] Cloud deployment and long-term storage

---

## 🧠 Insights & Applications

- Compare **player stats per map**
- Track **team roster changes and aliases**
- Build custom **esports betting models**
- Analyze **demo data** for advanced positional analysis *(coming soon)*

---

## 🤝 Contributing

Pull requests are welcome! To contribute:

1. Fork the repo
2. Create a feature branch (`git checkout -b feature-xyz`)
3. Commit your changes
4. Open a PR with a clear description

---

## 📜 License

MIT License — use, fork, improve, and build on it.

---

## 📬 Contact

For questions, feedback, or collaboration:

- GitHub Issues: [Submit a Bug or Feature](https://github.com/yourusername/cs2-analytics/issues)
- Email: your.email@example.com

---

🧪 **Built with care, sweat, and lots of grenades.**
