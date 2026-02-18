# 📊 Market Data Platform

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue)
![Docker](https://img.shields.io/badge/Docker-Containerized-blue)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-ORM-orange)
![Alembic](https://img.shields.io/badge/Alembic-Migrations-lightgrey)
![ETL](https://img.shields.io/badge/Architecture-ETL-green)
![Analytics](https://img.shields.io/badge/Layer-Analytics-purple)
![Reporting](https://img.shields.io/badge/Output-HTML%20%7C%20PDF-red)
![FastAPI](https://img.shields.io/badge/FastAPI-API-green)

A production-style **Data Engineering project** that implements a
complete financial market data pipeline.

The system extracts cryptocurrency data from the CoinGecko API, stores
it in PostgreSQL, computes portfolio analytics (returns, volatility,
correlation), and automatically generates HTML and PDF research reports.

------------------------------------------------------------------------

# 📑 Table of Contents

-   [Architecture Overview](#-architecture-overview)
-   [Tech Stack](#-tech-stack)
-   [Data Pipeline Flow](#-data-pipeline-flow)
-   [REST API (FastAPI)](#-rest-api-fastapi)
-   [Analytics Layer](#-analytics-layer)
-   [Automated Reporting](#-automated-reporting)
-   [Business Impact](#-business-impact)
-   [Quickstart](#-quickstart)
-   [Roadmap Status](#-roadmap-status)
-   [Repository Structure](#-repository-structure)
-   [Author](#-author)

------------------------------------------------------------------------

# 🧱 Architecture Overview

Pipeline structure:

`API → Extract → Transform → Load → Analytics → Reporting`

Core components:

-   Dockerized PostgreSQL database
-   Schema versioning with Alembic
-   Idempotent upserts (`ON CONFLICT`)
-   ETL run tracking (`etl_runs`)
-   Data quality validations
-   Analytics computation layer
-   Automated HTML + PDF report generation

------------------------------------------------------------------------

# 🛠 Tech Stack

-   Python 3.9+
-   PostgreSQL 16
-   SQLAlchemy (Core + ORM)
-   Alembic (Migrations)
-   Docker & Docker Compose
-   Pandas / NumPy (Analytics)
-   Jinja2 (HTML templating)
-   Matplotlib (Charts)
-   WeasyPrint (PDF rendering)

------------------------------------------------------------------------

# 🔄 Data Pipeline Flow

## 1 - Extract

-   Fetch Top N non-stable assets
-   Historical price data ingestion
-   Rate limit handling
-   Resume capability
-   Local caching

## 2️ - Transform

-   Daily returns
-   30-day cumulative return
-   30-day rolling volatility
-   Correlation matrix

## 3️ - Load

-   Idempotent upsert into:
    -   `assets`
    -   `prices`
    -   `asset_metrics`
-   Execution logging in `etl_runs`

------------------------------------------------------------------------

# 🌐 REST API (FastAPI)

Interactive Documentation: `http://localhost:8000/docs`

## 1 - Health

Returns API status.

`GET /health`

## 2 - Assets

Returns available tracked assets.

`GET /assets\`
`GET /assets/{symbol}`

## 3 - Prices

Returns historical daily prices.

Parameters:

- `start` (optional)
- `end` (optional)
- `limit` (default capped)

`GET /prices/{symbol}?start=YYYY-MM-DD&end=YYYY-MM-DD`

## 4 - Metrics

Returns:

- Daily return
- 30-day cumulative return
- 30-day rolling volatility

`GET /metrics/latest\`
`GET /metrics/{symbol}?window=60`

## 5 - Correlation

Returns:

- Pearson correlation of aligned daily returns
- Number of overlapping observations
- Start and end dates used
- Reference date (`as_of`)

`GET /correlation?asset1=BTC&asset2=ETH&window=60`

------------------------------------------------------------------------

# 📊 Analytics Layer

The analytics module computes:

- 📈 Performance ranking
- ⚖️ Volatility ranking
- 🔥 Correlation matrix
- 🎯 Risk vs Return positioning
- 📉 Historical price series

These analytics power both:

- REST API responses
- HTML/PDF automated reports

All outputs are saved into:

    /reports/

------------------------------------------------------------------------

# 📑 Automated Reporting

Run:

    `python -m pipeline.report`

Outputs:

-   `market_report.html`
-   `market_report.pdf`

The report includes:

-   Executive summary
-   Top gainers / losers
-   Volatility analysis
-   Correlation heatmap
-   Risk-return positioning
-   Automated insights

------------------------------------------------------------------------

# 💼 Business Impact

This project simulates a real-world financial data platform and
demonstrates:

### ✅ Production-Grade Data Engineering Practices

-   Containerized infrastructure
-   Schema migrations
-   Idempotent data loading
-   ETL run tracking & observability

### ✅ Quantitative Analytics Capabilities

-   Risk & return computation
-   Portfolio diversification analysis
-   Rolling volatility modeling
-   Automated insights generation

### ✅ End-to-End Ownership

From raw API ingestion to executive-level PDF reporting.

This mirrors workflows used in: 
- Hedge funds 
- Asset management firms 
- Crypto trading desks 
- Fintech analytics teams

The system transforms raw market data into decision-ready research
deliverables.

------------------------------------------------------------------------

# 🚀 Quickstart

### 1 - Clone

`git clone https://github.com/rafael-ribas/market-data-platform`
`cd market-data-platform`

### 2 - Start Database

`docker compose up -d`

### 3 - Apply Migrations

`alembic upgrade head`

### 4 - Run ETL

`python -m pipeline.run --limit 20 --days 45`

### 5 - Generate Report

`python -m pipeline.report`
	
### 6 - Start API Server

`uvicorn app.main:app --reload`
	
### 7 - Access 
	
`http://localhost:8000/docs`

------------------------------------------------------------------------

# 📅 Project Roadmap
  
| Milestone | Status|
| ---- | ---- |
| Historical Extract | ✅ |
| Idempotent Load | ✅ |
| ETL Tracking | ✅ |
| Analytics Engine | ✅ |
| Automated Reporting | ✅ |
| FastAPI API Layer | ✅ |
| Unit Tests (pytest) | 🔜 |
| CI/CD | 🔜 |
| Dockerized API Service | 🔜 |
| Cloud Deployment | 🔜 |

------------------------------------------------------------------------

# 🗂 Repository Structure

    market-data-platform/
    │
    ├── alembic/
	├── app/
    ├── db/
    ├── pipeline/
    ├── reports/
    ├── templates/
    ├── docker-compose.yml
    ├── README.md
    └── requirements.txt

------------------------------------------------------------------------

# ‍💻 Author

Rafael Ribas

- 📍 Data Engineer | Python • ETL • Analytics
- 🔗 https://rafael-ribas.github.io
- 🔗 https://www.linkedin.com/in/rrferreira/
