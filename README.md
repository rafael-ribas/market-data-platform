# 📊 Market Data Platform

A data engineering project that implements a complete market data pipeline for financial assets.

It extracts market data from the CoinGecko API, normalizes and stores it in a PostgreSQL database, computes analytics-ready datasets, and provides a clean structure for further API/reporting layers.

---

## 🧱 Architecture Overview

This project includes:

- **Dockerized PostgreSQL** database  
- **Schema versioning** with Alembic  
- **Extract-Transform-Load (ETL)** pipeline  
- **Cache + resume** logic for robust extraction  
- **Stablecoin filtering**  
- **Idempotent upsert** with Postgres `ON CONFLICT`  
- **Execution tracking** in `etl_runs`  
- **Data Quality checks**  
- **Modular project structure**

---

## 📦 Tech Stack

- `Python 3.9+`
- `PostgreSQL`
- `SQLAlchemy (Core + ORM)`
- `Alembic`
- `Requests (HTTP API)`
- `Logging & CLI`
- `Docker & Docker Compose`

---

## 🚀 Quickstart

### 1 - Requirements

Install:

- `Python >=3.9`
- `Docker`
- `Docker Compose`
- `Git`

Clone the repo:

```bash
git clone https://github.com/rafael-ribas/market-data-platform
cd market-data-platform
```

### 2 - Environment

#### Copy `.env.example`:

`cp .env.example .env`

#### Populate .env with:

```
POSTGRES_DB=marketdata
POSTGRES_USER=marketuser
POSTGRES_PASSWORD=marketpass
POSTGRES_PORT=5432
DATABASE_URL=postgresql+psycopg://marketuser:marketpass@localhost:5432/marketdata
```

### 3 - Start Database

`docker compose up -d`

### 4 - Apply Migrations

`alembic upgrade head`

You should see tables:

`assets`, `prices` and `etl_runs`

### 5 - Run ETL

`python -m pipeline.run --limit 20 --days 30`

This performs:

- Extract top assets (excluding stablecoins)
- Fetch history (last 30 days)
- Load into database
- Record run in etl_runs

#### 📌 ETL Observability

Each run is logged in the database:

`SELECT * FROM etl_runs ORDER BY id DESC;`

Fields include:

| Column        | Description                   |
| ------------- | ----------------------------- |
| started_at    | UTC start timestamp           |
| finished_at   | UTC finish timestamp          |
| assets_loaded | number of asset rows upserted |
| prices_loaded | number of price rows upserted |
| status        | SUCCESS / FAILED              |


#### 🧪 Data Quality Checks

Before loading, the pipeline verifies:

- Non-empty asset list
- No null or non-positive prices

## 📅 Project Roadmap


| Milestone               | Status |
| ----------------------- | ------ |
| Extract historical data | ✅      |
| Load with upsert        | ✅      |
| Run tracking & DQ       | ✅      |
| Metrics & Analytics     | ⚙️     |
| API Layer (FastAPI)     | 🔜     |
| Reporting (HTML/PDF)    | 🔜     |
| Tests & CI/CD           | 🔜     |


## 📚 Next Enhancements

- Extend API layer with FastAPI
- Compute analytics (returns, volatility, correlation)
- Generate automated reports
- Add pytest tests + Github Actions
- Cloud deployment (e.g., Render / Railway)

## 🗂 Repository Structure
```
market-data-platform/
├── alembic/
├── pipeline/
├── db/
├── data/
├── docker-compose.yml
├── .env.example
├── requirements.txt
└── README.md
```

## 👨‍ Author & Connect

Rafael Ribas

- 📍 Data Engineer | Python • ETL • Analytics
- 🔗 https://rafael-ribas.github.io
- 🔗 https://www.linkedin.com/in/rrferreira/