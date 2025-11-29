# Video Game Sales ETL Pipeline

A data engineering portfolio project that demonstrates ETL pipeline design, orchestration, and data warehousing using video game data from the RAWG API.

## 🎯 Project Overview

This project implements an end-to-end ETL pipeline that:
- Extracts video game data from the RAWG Video Games Database API
- Transforms and models data into a star schema data warehouse
- Orchestrates daily incremental loads using Apache Airflow
- Provides analytics dashboards via Metabase

## 🏗️ Architecture

```
RAWG API → Python ETL → PostgreSQL Data Warehouse → Metabase Dashboards
                ↓
         Apache Airflow (Orchestration)
```

### Data Model (Star Schema)
- **Fact Table**: `fact_game_metrics` - Game ratings, scores, playtime
- **Dimension Tables**:
  - `dim_games` - Game metadata
  - `dim_genres` - Genre taxonomy
  - `dim_platforms` - Gaming platforms
  - `dim_developers` - Game developers
  - `dim_publishers` - Game publishers

## 🛠️ Tech Stack

All technologies are **free** and **self-hosted**:

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Orchestration | Apache Airflow | DAG scheduling & monitoring |
| Data Warehouse | PostgreSQL | Relational database |
| ETL | Python 3.11+ | Data processing |
| Transformation | dbt Core | SQL-based transformations |
| Visualization | Metabase | BI dashboards |
| Container | Docker & Docker Compose | Local deployment |

## 📋 Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Git
- RAWG API Key (free at https://rawg.io/apidocs)

## 🚀 Quick Start

### 1. Clone and Setup

```bash
cd Documents/proyectos/video-game-etl
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your RAWG API key
```

### 3. Start Infrastructure

```bash
docker-compose up -d
```

This will start:
- PostgreSQL (port 5432)
- Airflow Webserver (port 8080)
- Airflow Scheduler
- Metabase (port 3000)

### 4. Initialize Database

```bash
python scripts/init_db.py
```

### 5. Run Pipeline

Access Airflow UI at http://localhost:8080 (default credentials: airflow/airflow)
- Enable the `video_game_etl` DAG
- Trigger a manual run

### 6. View Dashboards

Access Metabase at http://localhost:3000 and connect to PostgreSQL:
- Host: postgres
- Database: gaming_analytics
- User: airflow
- Password: airflow

## 📁 Project Structure

```
video-game-etl/
├── dags/
│   └── video_game_etl.py          # Airflow DAG definition
├── src/
│   ├── api/
│   │   └── rawg_client.py         # RAWG API client
│   ├── etl/
│   │   ├── extract.py             # Data extraction logic
│   │   ├── transform.py           # Data transformations
│   │   └── load.py                # Data loading to warehouse
│   └── utils/
│       ├── db_utils.py            # Database utilities
│       └── logging_config.py      # Logging configuration
├── sql/
│   ├── ddl/
│   │   └── schema.sql             # Table definitions
│   └── dml/
│       └── quality_checks.sql     # Data quality queries
├── dbt/
│   └── models/                    # dbt transformation models
├── tests/
│   ├── test_api_client.py
│   ├── test_transformations.py
│   └── test_data_quality.py
├── scripts/
│   └── init_db.py                 # Database initialization
├── config/
│   └── airflow.cfg                # Airflow configuration
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## 🔄 Pipeline Flow

1. **Extract**: Fetch games from RAWG API with pagination and rate limiting
2. **Staging**: Load raw data into staging tables
3. **Transform**: Apply business logic and create star schema
4. **Quality Checks**: Validate data integrity
5. **Load**: Upsert into production tables

## 📊 Data Engineering Concepts Demonstrated

- ✅ **ETL Pipeline Design**: Modular, testable extraction and transformation
- ✅ **Incremental Loading**: Track watermarks to avoid reprocessing
- ✅ **Data Modeling**: Star schema with fact and dimension tables
- ✅ **Orchestration**: Airflow DAGs with task dependencies
- ✅ **Data Quality**: Automated validation and monitoring
- ✅ **Idempotency**: Safe to rerun without side effects
- ✅ **Error Handling**: Retry logic and alerting
- ✅ **Documentation**: Comprehensive inline and external docs

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=src tests/
```

## 📈 Monitoring

- **Airflow UI**: DAG runs, task status, logs
- **PostgreSQL**: Row counts, data freshness
- **Logs**: Structured logging with timestamps

## 🐛 Troubleshooting

### API Rate Limit Exceeded
- RAWG API allows 20,000 requests/day
- Pipeline respects rate limits with exponential backoff

### Airflow DAG Not Showing
- Check `dags/` folder is in AIRFLOW_HOME
- Verify no Python syntax errors: `python dags/video_game_etl.py`

### Database Connection Failed
- Ensure PostgreSQL container is running: `docker ps`
- Check connection string in `.env`

## 📝 Future Enhancements

- [ ] Add more data sources (Steam API, IGDB)
- [ ] Implement CDC (Change Data Capture)
- [ ] Add real-time streaming with Kafka
- [ ] ML model for game popularity prediction
- [ ] Data lakehouse layer with DuckDB

## 📄 License

MIT License - feel free to use for your portfolio!

## 🤝 Contributing

This is a portfolio project, but suggestions are welcome via issues.

## 👤 Author

Your Name - [LinkedIn](your-linkedin) - [GitHub](your-github)
