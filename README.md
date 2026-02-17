# Market Data Platform

A production-oriented data engineering project that implements an end-to-end market data pipeline.

The platform extracts financial market data from external APIs, transforms and validates it, stores it in PostgreSQL with version-controlled schema migrations (Alembic), and prepares the data for analytics and API exposure.

---

## 🏗 Architecture

- Python
- PostgreSQL (Dockerized)
- SQLAlchemy ORM
- Alembic (schema versioning)
- Modular project structure

---

## 📦 Current Status

- ✅ Dockerized PostgreSQL  
- ✅ Database schema (assets, prices)  
- ✅ Alembic migrations  
- 🔄 ETL pipeline (in progress)  
- 🔜 API layer (FastAPI)  
- 🔜 Metrics computation  

---

## 🚀 How to Run

### 1. Start database

`docker compose up -d`

### 2. Apply migrations

`alembic upgrade head`

---

## 🎯 Project Goal

This project is designed to simulate a production-grade data engineering system, demonstrating:

- ETL architecture
- Relational modeling
- Migration-based schema management
- Containerized infrastructure
- Analytical data preparation