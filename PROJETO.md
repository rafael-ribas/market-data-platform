# Projeto - Market Data Platform


Plano de 15 dias para construir o Market Data Platform

Skills:
- `ETL + Postgres + FastAPI + Docker + Tests + CI + Report`

Stack:

- `Python + PostgreSQL + SQLAlchemy + FastAPI + Docker + Pytest + GitHub Actions`

Fonte de dados: 

- `CoinGecko`

---

Dia 1 — Setup & Esqueleto do Repo

Entrega:

- Repo criado no GitHub com estrutura profissional
- pyproject.toml (ou requirements.txt) + .gitignore
- README.md (visão geral + roadmap)

Estrutura de pastas:

market-data-platform/
  app/
  pipeline/
  db/
  reports/
  tests/
  scripts/


Checklist:

- venv .venv (Windows)
- comandos básicos no README (run, test, docker)

---

Dia 2 — Docker + PostgreSQL (ambiente de verdade)

Entrega:

- docker-compose.yml com Postgres
- .env.example com variáveis (DB_HOST, DB_USER etc.)
- conexão local funcionando

Objetivo: você conseguir rodar docker compose up -d e conectar no banco.

---

Dia 3 — Modelagem do Banco (schema inicial)

Entrega:

- SQLAlchemy models + migrations (ideal: Alembic)

tabelas mínimas:

- assets
- id, symbol, name, source
- prices
- id, asset_id, date, price, market_cap, volume
- metrics
- id, asset_id, date, return_1d, vol_30d, sharpe_30d

Checklist:

- unique constraints (asset_id + date)
- índices para consultas rápidas

---

Dia 4 — Extract (CoinGecko) robusto

Entrega:

- pipeline/extract.py puxando Top N (ex.: top 10 por market cap)
- retry simples e tratamento de erros
- logs claros (INFO/WARN/ERROR)
- Plus: salvar raw JSON opcional em data/raw/ (útil para debug)

---

Dia 5 — Transform (normalização + validação)

Entrega:

- pipeline/transform.py que:
- normaliza datas
- garante tipos numéricos
- remove duplicados
- valida campos essenciais

---

Dia 6 — Load (Postgres com upsert)

Entrega:

- pipeline/load.py com:
- inserção de assets
- inserção de prices (com UPSERT)
- transação e rollback em caso de erro
- Resultado esperado: rodar pipeline 2x sem duplicar dados.

---

Dia 7 — Pipeline Runner + CLI

Entrega:

- pipeline/run.py

- CLI com argparse/typer:

Exemplos:

- python -m pipeline.run --top 10
- python -m pipeline.run --start 2025-01-01 --end 2025-02-01
- Plus: modo “dry-run” (não grava no banco)

---

Dia 8 — Métricas (returns, vol, sharpe)

Entrega:

- pipeline/metrics.py calculando:
- retorno diário (%)
- volatilidade móvel (ex.: 30 dias)
- sharpe simplificado (assumindo rf=0)
- Salvar em metrics table.

---

Dia 9 — API FastAPI (MVP)

Entrega:

- app/main.py com FastAPI

endpoints mínimos:

- GET /health
- GET /assets
- GET /prices/{symbol}?start=&end=
- GET /metrics/{symbol}?window=30
- Plus: OpenAPI docs funcionando (Swagger).

---

Dia 10 — API: endpoints avançados (correlação)

Entrega:

- GET /correlation?asset1=BTC&asset2=ETH&window=30
- cálculo de correlação com base nos retornos
- Plus: validações e mensagens de erro limpas.

---

Dia 11 — Testes (Pytest) + Testcontainers ou DB test

Entrega:

- testes unitários (métricas e validações)
- testes de API (FastAPI TestClient)
- pelo menos 1 teste de integração com DB (pode usar Postgres do docker-compose)

Meta: pytest rodando local 100%.

---

Dia 12 — GitHub Actions (CI)

Entrega:

- workflow .github/workflows/ci.yml rodando:

- install
- lint (opcional: ruff)
- pytest

Isso dá “cara de pleno” imediatamente.

---

Dia 13 — Report automático (HTML/PDF)

Entrega:

- reports/daily_report.py gerando:
- tabela top assets
- performance 7d/30d
- correlação (top pairs)
- gráfico simples (matplotlib)
- output em reports/output/report.html (PDF opcional)

---

Dia 14 — Documentação “de recrutador”

Entrega:

README com:

- arquitetura (diagrama simples)
- como rodar local (docker + pipeline + api)
- exemplos de requests (curl)
- screenshots do report + swagger
- Plus: badges:

CI passing
Python version
Docker
Postgres
FastAPI

---

Dia 15 — Polimento + Release v1.0.0

Entrega:

- CHANGELOG.md
- makefile/taskfile opcional (no Windows pode ser scripts/*.ps1)

release no GitHub com:

- instruções
- prints
- “What’s next” (v1.1 roadmap)

---

Um projeto que mostra, na prática:

- ETL real (extract/transform/load)
- Banco relacional sério (Postgres)
- API própria (FastAPI)
- Docker compose
- Testes e CI
- Relatório automatizado (output “visível”)
- Documentação de produção