# Architecture Documentation

## System Overview

The Video Game ETL Pipeline is a **data engineering portfolio project** that demonstrates modern ETL design patterns, dimensional modeling, and workflow orchestration using free, self-hosted technologies.

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Data Pipeline Flow                              │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────┐      ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   RAWG API   │──────▶│   Extract    │──────▶│  Transform   │──────▶│     Load     │
│ (REST API)   │ JSON │  (Python)    │ Dict │  (Python)    │ Dict │ (PostgreSQL) │
└──────────────┘      └──────────────┘      └──────────────┘      └──────────────┘
       │                     │                     │                      │
       │              ┌──────▼──────┐       ┌──────▼──────┐        ┌──────▼──────┐
       │              │ Rate Limit  │       │ Validation  │        │  Upsert     │
       │              │ Pagination  │       │ Dedup       │        │  (MERGE)    │
       │              │ Error Handle│       │ Normalize   │        │  Bulk Load  │
       │              └─────────────┘       └─────────────┘        └─────────────┘
       │                                                                   │
       ▼                                                                   ▼
┌──────────────────────────────────────────────────────────────┐  ┌──────────────┐
│              Apache Airflow (Orchestration)                  │  │  Metabase    │
│  ┌────────────┐  ┌─────────────┐  ┌──────────┐  ┌─────────┐ │  │ (Analytics)  │
│  │  Extract   │─▶│  Transform  │─▶│   Load   │─▶│ Quality │ │  │              │
│  │    Task    │  │    Task     │  │   Task   │  │  Checks │ │  │  Dashboards  │
│  └────────────┘  └─────────────┘  └──────────┘  └─────────┘ │  │   Reports    │
│                                                                │  │   Ad-hoc SQL │
│  Schedule: Daily at 2 AM                                      │  └──────────────┘
│  Retry: 3x with 5min delay                                    │         │
└────────────────────────────────────────────────────────────────┘         │
                                                                           │
                                                               ┌───────────▼────────────┐
                                                               │  PostgreSQL Warehouse  │
                                                               │   Star Schema (6 tables) │
                                                               └────────────────────────┘
```

## Architecture Layers

### 1. Data Source Layer

**Component**: RAWG Video Games API

**Responsibilities**:
- Provide video game data via REST API
- Handle authentication via API key
- Paginate large result sets
- Enforce rate limits (20k/day)

**Technology**:
- REST API over HTTPS
- JSON response format
- OAuth not required (API key auth)

**Endpoints Used**:
- `/games` - Game listings with metadata
- `/games/{id}` - Detailed game information
- `/genres` - Genre taxonomy
- `/platforms` - Gaming platforms
- `/developers` - Development studios
- `/publishers` - Publishing companies

### 2. Extraction Layer

**Component**: `GameDataExtractor` (src/etl/extract.py)

**Responsibilities**:
- Fetch data from RAWG API
- Handle pagination automatically
- Enforce client-side rate limiting
- Implement retry logic with exponential backoff
- Extract incremental updates (last N days)

**Key Features**:
```python
# Incremental extraction with 7-day lookback
data = extractor.extract_incremental(lookback_days=7)

# Returns dictionary with all entities
{
    'games': [...],
    'genres': [...],
    'platforms': [...],
    'developers': [...],
    'publishers': [...]
}
```

**Error Handling**:
- Custom exceptions (`ExtractionError`)
- Automatic retries for transient failures
- Graceful degradation (skip failed items, continue)
- Detailed logging with context

**Performance**:
- Connection pooling (10-20 connections)
- Batch pagination (40 results/page)
- Rate limiting (3 req/sec)

### 3. Transformation Layer

**Component**: `GameDataTransformer` (src/etl/transform.py)

**Responsibilities**:
- Normalize raw API data
- Create star schema dimensions
- Build fact table metrics
- Handle many-to-many relationships (bridge tables)
- Validate data quality
- Deduplicate records

**Transformations**:

1. **Games Dimension** (`transform_games`)
   - Extract first developer/publisher (API returns arrays)
   - Parse ESRB rating from nested object
   - Handle null/missing fields safely

2. **Fact Metrics** (`transform_fact_metrics`)
   - Explode games by platforms (1:N relationship)
   - Create one fact row per game-platform combination
   - Extract numeric metrics (rating, playtime, etc.)

3. **Bridge Table** (`create_game_genre_bridge`)
   - Extract many-to-many game-genre relationships
   - Deduplicate pairs using sets
   - Create composite key records

4. **Data Quality** (`validate_data_quality`)
   - Check required fields presence
   - Validate threshold (default 90%)
   - Log validation failures

**Example**:
```python
# Raw API game
{
  "id": 3498,
  "name": "GTA V",
  "platforms": [{"platform": {"id": 4}}, {"platform": {"id": 1}}],
  "genres": [{"id": 4}, {"id": 5}]
}

# Transformed to:
# 1 game dimension record
# 2 fact metric records (one per platform)
# 2 bridge records (one per genre)
```

### 4. Loading Layer

**Component**: `GameDataLoader` (src/etl/load.py)

**Responsibilities**:
- Load transformed data into PostgreSQL
- Use bulk upsert for performance
- Maintain referential integrity
- Handle conflicts (duplicates)
- Track loading statistics

**Loading Strategy**:

**Order** (to maintain foreign key constraints):
1. Independent dimensions (genres, platforms, developers, publishers)
2. Games dimension (references developers/publishers)
3. Fact table (references games and platforms)
4. Bridge table (references games and genres)

**Upsert Logic**:
```sql
INSERT INTO dim_games (game_id, name, ...)
VALUES (%s, %s, ...)
ON CONFLICT (game_id)
DO UPDATE SET
  name = EXCLUDED.name,
  updated_at = EXCLUDED.updated_at
```

**Performance**:
- Batch operations (`execute_batch` with 1000 rows/batch)
- Single transaction per table
- Connection pooling via `DatabaseManager`

### 5. Data Warehouse Layer

**Component**: PostgreSQL with Star Schema

**Schema Design**:

```
                           ┌─────────────────┐
                           │  dim_developers │
                           │  PK: dev_id     │
                           └────────┬────────┘
                                    │
                           ┌────────▼────────┐
                           │ dim_publishers  │
                           │  PK: pub_id     │
                           └────────┬────────┘
                                    │
┌─────────────────┐        ┌────────▼────────┐        ┌─────────────────┐
│  dim_genres     │        │   dim_games     │        │ dim_platforms   │
│  PK: genre_id   │        │  PK: game_id    │◀───────│  PK: plat_id    │
└────────┬────────┘        │  FK: dev_id     │        └────────┬────────┘
         │                 │  FK: pub_id     │                 │
         │                 └────────┬────────┘                 │
         │                          │                          │
         │                 ┌────────▼────────────────┐         │
         │                 │  fact_game_metrics      │         │
         │                 │  PK: (game_id, plat_id) │◀────────┘
         │                 │  FK: game_id            │
         │                 │  FK: plat_id            │
         │                 │                         │
         │                 │  rating, metacritic,    │
         │                 │  playtime, added...     │
         │                 └────────┬────────────────┘
         │                          │
         │                 ┌────────▼────────────────┐
         └─────────────────▶ bridge_game_genre       │
                           │  PK: (game_id, genre_id)│
                           │  FK: game_id            │
                           │  FK: genre_id           │
                           └─────────────────────────┘
```

**Tables**:

| Table | Type | Rows (Est) | Purpose |
|-------|------|------------|---------|
| `dim_games` | Dimension | 10,000+ | Game master data |
| `dim_genres` | Dimension | ~20 | Genre taxonomy |
| `dim_platforms` | Dimension | ~50 | Platform reference |
| `dim_developers` | Dimension | 5,000+ | Developer studios |
| `dim_publishers` | Dimension | 3,000+ | Publishing companies |
| `fact_game_metrics` | Fact | 50,000+ | Metrics per game-platform |
| `bridge_game_genre` | Bridge | 30,000+ | Game-genre relationships |

**Indexing Strategy**:
- Primary keys (clustered indexes)
- Foreign keys (for joins)
- Common filter columns (released, rating, metacritic)
- Updated_at (for incremental loads)

### 6. Orchestration Layer

**Component**: Apache Airflow

**DAG Structure**:

```python
# DAG: video_game_etl
# Schedule: Daily at 2 AM (0 2 * * *)

extract_task >> transform_task >> load_task >> quality_check_task
```

**Task Details**:

| Task | Function | Duration | Retries |
|------|----------|----------|---------|
| `extract_data` | Fetch from API | 5-15 min | 3x, 5min delay |
| `transform_data` | Normalize data | 1-3 min | 3x, 5min delay |
| `load_data` | Insert to DB | 1-5 min | 3x, 5min delay |
| `quality_checks` | Validate data | < 1 min | 3x, 5min delay |

**XCom Data Sharing**:
```python
# Extract pushes raw data
context['ti'].xcom_push(key='raw_data', value=data)

# Transform pulls and pushes
raw_data = context['ti'].xcom_pull(task_ids='extract_data', key='raw_data')
context['ti'].xcom_push(key='transformed_data', value=transformed)

# Load pulls transformed data
transformed = context['ti'].xcom_pull(task_ids='transform_data', key='transformed_data')
```

**Configuration**:
- **Executor**: LocalExecutor (single-machine)
- **Max active runs**: 1 (prevent overlaps)
- **Catchup**: False (no backfilling)
- **Timeout**: 2 hours per task

### 7. Visualization Layer

**Component**: Metabase

**Purpose**:
- Business intelligence dashboards
- Ad-hoc querying
- Metric visualization
- Trend analysis

**Key Dashboards**:
- Top rated games by platform
- Genre popularity over time
- Developer/publisher rankings
- Platform market share
- Game release trends

**Views** (pre-aggregated for performance):
- `vw_game_details` - Denormalized game info
- `vw_top_rated_games` - Games with 100+ ratings
- `vw_genre_popularity` - Genre metrics
- `vw_platform_stats` - Platform statistics

## Technology Stack

### Infrastructure

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Compose                        │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  PostgreSQL  │  │   Airflow    │  │  Metabase    │  │
│  │   :5432      │  │  Webserver   │  │   :3000      │  │
│  │              │  │   :8080      │  │              │  │
│  │  Volume:     │  │              │  │  Connects to │  │
│  │  postgres-db │  │  Scheduler   │  │  PostgreSQL  │  │
│  └──────────────┘  │              │  └──────────────┘  │
│                    │  Volumes:    │                     │
│                    │  - dags/     │                     │
│                    │  - logs/     │                     │
│                    │  - plugins/  │                     │
│                    │  - src/      │                     │
│                    └──────────────┘                     │
└─────────────────────────────────────────────────────────┘
```

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Database | PostgreSQL | 15-alpine | Data warehouse |
| Orchestration | Apache Airflow | 2.8.0 | Workflow scheduling |
| ETL | Python | 3.11+ | Data processing |
| Transformation | dbt Core | 1.7.4 | SQL transformations |
| Visualization | Metabase | Latest | BI dashboards |
| Container | Docker Compose | 3.8 | Local deployment |

### Python Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| `psycopg2-binary` | 2.9.9 | PostgreSQL driver |
| `sqlalchemy` | 1.4.51 | ORM and query builder |
| `requests` | 2.31.0 | HTTP client |
| `pandas` | 2.1.4 | Data manipulation |
| `python-dotenv` | 1.0.0 | Environment config |
| `pydantic` | 2.5.3 | Data validation |
| `structlog` | 23.3.0 | Structured logging |

## Component Responsibilities

### RAWGClient (src/api/rawg_client.py)

**Responsibilities**:
- HTTP request handling
- Rate limiting enforcement
- Connection pooling management
- Error handling and retries
- Pagination logic

**Key Methods**:
- `get_games()` - Fetch paginated games
- `get_game_details()` - Fetch single game
- `fetch_all_pages()` - Auto-paginate any endpoint

### GameDataExtractor (src/etl/extract.py)

**Responsibilities**:
- API client wrapper
- Incremental extraction logic
- Multi-entity extraction
- Error aggregation

**Key Methods**:
- `extract_incremental()` - Main entry point
- `extract_games()` - Fetch games in date range
- `extract_genres()`, `extract_platforms()`, etc.

### GameDataTransformer (src/etl/transform.py)

**Responsibilities**:
- Data normalization
- Schema transformation
- Deduplication
- Data quality validation

**Key Methods**:
- `transform_games()` - Game dimension
- `transform_fact_metrics()` - Fact table
- `create_game_genre_bridge()` - Bridge table
- `validate_data_quality()` - Quality checks

### GameDataLoader (src/etl/load.py)

**Responsibilities**:
- Bulk data loading
- Conflict resolution (upsert)
- Transaction management
- Load statistics

**Key Methods**:
- `load_games()`, `load_genres()`, etc.
- `load_fact_metrics()` - Fact loading
- `get_data_warehouse_stats()` - Monitoring

### DatabaseManager (src/utils/db_utils.py)

**Responsibilities**:
- Connection pooling
- Query execution
- Transaction management
- Bulk operations

**Key Methods**:
- `execute_query()` - Run SQL
- `bulk_upsert()` - Batch upsert
- `get_row_count()` - Table stats

## Data Flow Details

### Full Pipeline Execution

```
1. EXTRACT (5-15 minutes)
   ├─ Fetch games from last 7 days
   ├─ Fetch all genres (~20 records)
   ├─ Fetch all platforms (~50 records)
   ├─ Fetch developers (10 pages = ~400 records)
   ├─ Fetch publishers (10 pages = ~400 records)
   └─ Push to XCom

2. TRANSFORM (1-3 minutes)
   ├─ Pull raw data from XCom
   ├─ Transform games → dim_games
   ├─ Transform games × platforms → fact_game_metrics
   ├─ Extract genres from games → dim_genres
   ├─ Transform platforms → dim_platforms
   ├─ Transform developers → dim_developers
   ├─ Transform publishers → dim_publishers
   ├─ Create game-genre pairs → bridge_game_genre
   ├─ Validate data quality (90% threshold)
   └─ Push to XCom

3. LOAD (1-5 minutes)
   ├─ Pull transformed data from XCom
   ├─ Load dim_genres (upsert)
   ├─ Load dim_platforms (upsert)
   ├─ Load dim_developers (upsert)
   ├─ Load dim_publishers (upsert)
   ├─ Load dim_games (upsert, FK to dev/pub)
   ├─ Load fact_game_metrics (upsert, FK to games/platforms)
   ├─ Load bridge_game_genre (upsert, FK to games/genres)
   └─ Return statistics

4. QUALITY CHECKS (< 1 minute)
   ├─ Check fact table not empty
   ├─ Check all dimensions have records
   ├─ Check no orphaned fact records
   ├─ Check data freshness (< 2 days old)
   ├─ Check no null primary keys
   └─ Raise error if any check fails
```

### Incremental Loading Strategy

**Watermark**: `released` date (game release date)

**Approach**:
1. Extract games from last 7 days (`lookback_days=7`)
2. Upsert to warehouse (updates existing, inserts new)
3. Fact metrics updated if ratings/playtime changed
4. Dimensions updated if metadata changed

**Benefits**:
- Reduces API calls (only recent data)
- Faster execution (smaller datasets)
- Captures updates to existing games
- Idempotent (safe to rerun)

**Trade-offs**:
- May miss games with backdated releases
- Relies on API's `dates` filter accuracy
- 7-day overlap to ensure completeness

## Design Patterns

### 1. Extract-Transform-Load (ETL)

**Why ETL vs ELT?**
- Transform before load (lighter on warehouse)
- Validation before persistence
- API data needs significant normalization
- Small-to-medium data volumes

### 2. Star Schema

**Why Star Schema?**
- Optimized for analytics queries
- Denormalized for query performance
- Easy to understand for BI tools
- Supports drill-down analysis

### 3. Upsert (MERGE) Pattern

**Why Upsert?**
- Idempotent loads (safe reruns)
- Handles updates to existing data
- Single operation (insert + update)
- Maintains data history via `updated_at`

### 4. Connection Pooling

**Why Connection Pool?**
- Reuse database connections
- Reduce connection overhead
- Handle concurrent requests
- Prevent connection exhaustion

### 5. Retry with Exponential Backoff

**Why Exponential Backoff?**
- Handle transient failures gracefully
- Avoid overwhelming failed services
- Respect rate limits
- Maximize success rate

## Scalability Considerations

### Current Limitations

| Resource | Current | Bottleneck |
|----------|---------|------------|
| API Rate | 3 req/sec | RAWG API limit |
| Database | Single instance | Disk I/O |
| Airflow | LocalExecutor | Single machine |
| Memory | Limited by host | Large XCom payloads |

### Scaling Options

**Horizontal Scaling**:
- Use CeleryExecutor for distributed task execution
- Multiple Airflow workers
- PostgreSQL read replicas

**Vertical Scaling**:
- Increase database resources
- More CPU for transformation tasks
- Larger memory for XCom data

**Optimization**:
- Implement S3 XCom backend (avoid database)
- Partition fact table by date
- Add materialized views
- Implement change data capture (CDC)

## Security Considerations

1. **API Key**: Stored in `.env`, never committed to git
2. **Database Credentials**: Environment variables only
3. **Network**: Docker internal network for service communication
4. **SQL Injection**: Parameterized queries throughout
5. **Secrets Management**: Use Airflow Connections/Variables for production

## Monitoring and Observability

### Logs

- **Airflow Logs**: `logs/` directory, per-task logs
- **Application Logs**: Structured JSON logging via `structlog`
- **Database Logs**: PostgreSQL logs in container

### Metrics

- Task duration (Airflow UI)
- Row counts (data warehouse stats)
- API request counts (logged)
- Error rates (exception tracking)

### Alerting

- Email on task failure (configurable)
- Data quality check failures
- Rate limit warnings

## Related Documentation

- [API Integration](API_INTEGRATION.md) - RAWG API details
- [Data Dictionary](DATA_DICTIONARY.md) - Schema reference
- [Operations Guide](OPERATIONS.md) - Deployment and troubleshooting
- [Developer Guide](DEVELOPER_GUIDE.md) - Development setup
