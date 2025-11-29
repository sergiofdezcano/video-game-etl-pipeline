# Operations Guide

## Overview

This operational runbook provides step-by-step instructions for deploying, monitoring, and troubleshooting the Video Game ETL Pipeline. This guide is intended for data engineers and operators managing the system.

## Prerequisites

Before deploying, ensure you have:

- [ ] Docker Desktop installed and running
- [ ] Docker Compose v3.8 or higher
- [ ] Python 3.11+ installed
- [ ] At least 4GB RAM available for containers
- [ ] At least 5GB disk space for data and logs
- [ ] Network access to https://api.rawg.io
- [ ] Git (for version control)

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 cores | 4+ cores |
| RAM | 4GB | 8GB+ |
| Disk | 5GB | 20GB+ |
| OS | Windows 10/11, macOS, Linux | Any |

## Getting a RAWG API Key

### Step 1: Create Account

1. Visit https://rawg.io/apidocs
2. Click "Sign Up" in the top-right corner
3. Complete registration with email and password
4. Verify your email address

### Step 2: Generate API Key

1. Log in to your RAWG account
2. Navigate to your profile page
3. Look for "API" or "Developer" section
4. Click "Get API Key" or "Generate Key"
5. Copy the API key (starts with a long alphanumeric string)

### Step 3: Verify API Key

Test your API key with curl:

```bash
curl "https://api.rawg.io/api/games?key=YOUR_API_KEY_HERE&page_size=1"
```

Expected response: JSON with one game

**IMPORTANT**:
- Free tier: 20,000 requests/day
- No credit card required
- Keep your API key secret (never commit to git)

## Deployment Guide

### Quick Start (5 minutes)

```bash
# 1. Navigate to project directory
cd C:\Users\sergi\Documents\proyectos\video-game-etl

# 2. Create environment file from template
cp .env.example .env

# 3. Edit .env and add your RAWG API key
# Use any text editor (notepad, VSCode, etc.)
notepad .env

# 4. Start all services
docker-compose up -d

# 5. Wait for services to initialize (30-60 seconds)
docker-compose ps

# 6. Initialize database schema
python scripts/init_db.py

# 7. Access Airflow UI
# Open browser: http://localhost:8080
# Login: airflow / airflow
```

### Detailed Deployment Steps

#### 1. Environment Configuration

Edit `.env` file with your settings:

```env
# REQUIRED: Add your RAWG API key
RAWG_API_KEY=your_actual_api_key_here

# OPTIONAL: Customize these if needed
RAWG_BASE_URL=https://api.rawg.io/api
RAWG_RATE_LIMIT=3

# Database (default values work with Docker Compose)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=gaming_analytics
POSTGRES_USER=airflow
POSTGRES_PASSWORD=airflow

# Airflow (default values)
AIRFLOW_UID=50000
AIRFLOW__CORE__EXECUTOR=LocalExecutor
AIRFLOW__CORE__LOAD_EXAMPLES=False

# ETL Configuration
ETL_BATCH_SIZE=100
ETL_START_DATE=2024-01-01
ETL_LOOKBACK_DAYS=7

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

**Key Settings**:

| Variable | Default | Description |
|----------|---------|-------------|
| `RAWG_API_KEY` | (required) | Your RAWG API key |
| `RAWG_RATE_LIMIT` | 3 | Requests per second (max safe rate) |
| `ETL_LOOKBACK_DAYS` | 7 | Days to look back for incremental updates |
| `LOG_LEVEL` | INFO | Logging verbosity (DEBUG, INFO, WARNING, ERROR) |

#### 2. Start Infrastructure

```bash
# Start all services in detached mode
docker-compose up -d

# Check service status
docker-compose ps

# Expected output:
# NAME                STATUS    PORTS
# airflow-init        exited
# airflow-scheduler   running
# airflow-webserver   running   0.0.0.0:8080->8080/tcp
# metabase            running   0.0.0.0:3000->3000/tcp
# postgres            running   0.0.0.0:5432->5432/tcp
```

**Service Startup Times**:
- PostgreSQL: 5-10 seconds
- Airflow Init: 20-30 seconds
- Airflow Webserver: 30-60 seconds
- Airflow Scheduler: 30-60 seconds
- Metabase: 60-90 seconds

#### 3. Verify Services

```bash
# Check PostgreSQL
docker exec -it postgres psql -U airflow -d airflow -c "SELECT version();"

# Check Airflow webserver
curl http://localhost:8080/health

# Check Metabase
curl http://localhost:3000/api/health
```

#### 4. Initialize Database

```bash
# Install Python dependencies (if not already done)
pip install -r requirements.txt

# Run database initialization script
python scripts/init_db.py

# Expected output:
# INFO - Starting database initialization
# INFO - Reading schema from ...
# INFO - Schema created successfully
# INFO - ✓ Table dim_games created
# INFO - ✓ Table dim_genres created
# INFO - ✓ Table dim_platforms created
# INFO - ✓ Table dim_developers created
# INFO - ✓ Table dim_publishers created
# INFO - ✓ Table fact_game_metrics created
# INFO - ✓ Table bridge_game_genre created
# INFO - Database initialization complete
```

#### 5. Deploy Airflow DAG

The DAG is automatically loaded from the `dags/` directory:

```bash
# Verify DAG file exists
ls dags/video_game_etl.py

# Check DAG in Airflow UI
# 1. Open http://localhost:8080
# 2. Login: airflow / airflow
# 3. Look for "video_game_etl" DAG in list
```

**If DAG doesn't appear**:
```bash
# Check for Python syntax errors
python dags/video_game_etl.py

# Check Airflow scheduler logs
docker-compose logs airflow-scheduler

# Restart scheduler to force reload
docker-compose restart airflow-scheduler
```

#### 6. First Pipeline Run

**Option A: Manual Trigger (Recommended for first run)**

1. Open Airflow UI: http://localhost:8080
2. Find `video_game_etl` DAG
3. Toggle DAG to "On" (enable)
4. Click "Trigger DAG" button (play icon)
5. Click on run to monitor progress
6. Wait for all tasks to complete (green checkmarks)

**Option B: Command Line Trigger**

```bash
# Trigger DAG run
docker exec -it airflow-webserver airflow dags trigger video_game_etl

# Check run status
docker exec -it airflow-webserver airflow dags list-runs -d video_game_etl
```

**Expected Duration** (first run):
- Extract: 10-15 minutes (7 days of data)
- Transform: 2-3 minutes
- Load: 2-5 minutes
- Quality Checks: < 1 minute
- **Total**: ~15-25 minutes

#### 7. Verify Data Load

```bash
# Connect to PostgreSQL
docker exec -it postgres psql -U airflow -d gaming_analytics

# Check row counts
SELECT
  'dim_games' as table_name, COUNT(*) as row_count FROM dim_games
UNION ALL
SELECT 'dim_genres', COUNT(*) FROM dim_genres
UNION ALL
SELECT 'dim_platforms', COUNT(*) FROM dim_platforms
UNION ALL
SELECT 'fact_game_metrics', COUNT(*) FROM fact_game_metrics
UNION ALL
SELECT 'bridge_game_genre', COUNT(*) FROM bridge_game_genre;

# Exit psql
\q
```

Expected results (approximate):
- dim_games: 100-1000+ rows
- dim_genres: 15-20 rows
- dim_platforms: 40-50 rows
- fact_game_metrics: 500-5000+ rows
- bridge_game_genre: 300-3000+ rows

## Accessing Services

### Airflow Web UI

**URL**: http://localhost:8080

**Default Credentials**:
- Username: `airflow`
- Password: `airflow`

**Key Features**:
- View DAG runs and task status
- Trigger manual runs
- View task logs
- Monitor performance metrics

**Changing Password**:
```bash
docker exec -it airflow-webserver airflow users create \
  --username admin \
  --password your_new_password \
  --firstname Admin \
  --lastname User \
  --role Admin \
  --email admin@example.com
```

### Metabase Dashboard

**URL**: http://localhost:3000

**First-Time Setup**:

1. Open http://localhost:3000
2. Complete initial setup wizard:
   - Language: English
   - Name and email (any values)
   - Create password
3. Add database connection:
   - **Database type**: PostgreSQL
   - **Name**: Gaming Analytics
   - **Host**: `postgres` (Docker internal hostname)
   - **Port**: `5432`
   - **Database name**: `gaming_analytics`
   - **Username**: `airflow`
   - **Password**: `airflow`
4. Click "Save"
5. Explore data or create dashboards

**Sample Queries**:

1. **Top Rated Games**:
```sql
SELECT * FROM vw_top_rated_games LIMIT 20;
```

2. **Genre Popularity**:
```sql
SELECT * FROM vw_genre_popularity;
```

3. **Platform Statistics**:
```sql
SELECT * FROM vw_platform_stats;
```

### PostgreSQL Database

**Connection Details**:
- Host: `localhost` (from host machine) or `postgres` (from Docker)
- Port: `5432`
- Database: `gaming_analytics`
- User: `airflow`
- Password: `airflow`

**Connect via psql**:
```bash
docker exec -it postgres psql -U airflow -d gaming_analytics
```

**Connect via Python**:
```python
import psycopg2

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='gaming_analytics',
    user='airflow',
    password='airflow'
)
```

## Monitoring and Logging

### Log Locations

| Component | Location | Format |
|-----------|----------|--------|
| Airflow DAG logs | `logs/dag_id/run_id/task_id/` | Plain text |
| Airflow scheduler | Docker logs | Plain text |
| Airflow webserver | Docker logs | Plain text |
| PostgreSQL | Docker logs | Plain text |
| Application logs | Airflow task logs | JSON (structured) |

### Viewing Logs

**Airflow Task Logs**:
1. Open Airflow UI
2. Click on DAG run
3. Click on task
4. Click "Log" button

**Docker Service Logs**:
```bash
# All services
docker-compose logs

# Specific service
docker-compose logs airflow-scheduler
docker-compose logs postgres

# Follow logs (tail -f equivalent)
docker-compose logs -f airflow-scheduler

# Last 100 lines
docker-compose logs --tail=100 airflow-webserver
```

### Monitoring Metrics

**Key Metrics to Monitor**:

1. **DAG Success Rate**:
   - View in Airflow UI → DAGs page
   - Target: > 95% success rate

2. **Task Duration**:
   - View in Airflow UI → DAG Runs → Task Instance Details
   - Extract task: < 20 minutes
   - Transform task: < 5 minutes
   - Load task: < 10 minutes

3. **Data Freshness**:
```sql
-- Last update time
SELECT MAX(updated_at) FROM fact_game_metrics;

-- Should be within last 24 hours for daily runs
```

4. **Row Counts**:
```sql
-- Monitor growth over time
SELECT COUNT(*) FROM fact_game_metrics;
```

5. **API Request Usage**:
   - Check Airflow task logs for request counts
   - Daily limit: 20,000 requests
   - Typical daily run: 500-2000 requests

### Alerting

**Configure Email Alerts** (optional):

Edit `docker-compose.yml`:
```yaml
environment:
  AIRFLOW__SMTP__SMTP_HOST: smtp.gmail.com
  AIRFLOW__SMTP__SMTP_PORT: 587
  AIRFLOW__SMTP__SMTP_USER: your_email@gmail.com
  AIRFLOW__SMTP__SMTP_PASSWORD: your_app_password
  AIRFLOW__SMTP__SMTP_MAIL_FROM: your_email@gmail.com
```

Update DAG default_args:
```python
default_args = {
    'email': ['your_email@example.com'],
    'email_on_failure': True,
    'email_on_retry': True,
}
```

## Troubleshooting

### Issue: API Rate Limit Exceeded

**Symptoms**:
```
ERROR - RAWGRateLimitError: Rate limit exceeded
```

**Causes**:
- Exceeded 20,000 daily requests
- Too many manual DAG triggers
- Rate limit set too high

**Solutions**:

1. **Check daily usage**:
```bash
# Count API requests in logs
docker-compose logs airflow-scheduler | grep "Request successful" | wc -l
```

2. **Reduce rate limit** in `.env`:
```env
RAWG_RATE_LIMIT=2  # Slower but safer
```

3. **Reduce lookback window** in `.env`:
```env
ETL_LOOKBACK_DAYS=3  # Fewer days = fewer requests
```

4. **Wait 24 hours** for daily limit reset

5. **Add manual delays** between retries:
```python
# In DAG default_args
'retry_delay': timedelta(hours=1)  # Wait 1 hour between retries
```

---

### Issue: Database Connection Failures

**Symptoms**:
```
ERROR - DatabaseConnectionError: Database connection failed
ERROR - could not connect to server: Connection refused
```

**Causes**:
- PostgreSQL container not running
- Incorrect connection parameters
- Network issues

**Solutions**:

1. **Check PostgreSQL status**:
```bash
docker-compose ps postgres

# Should show "Up" status
```

2. **Restart PostgreSQL**:
```bash
docker-compose restart postgres

# Wait 10 seconds
docker-compose ps postgres
```

3. **Verify connection parameters**:
```bash
# From host machine
psql -h localhost -p 5432 -U airflow -d gaming_analytics

# From within Airflow container
docker exec -it airflow-scheduler psql -h postgres -p 5432 -U airflow -d gaming_analytics
```

4. **Check PostgreSQL logs**:
```bash
docker-compose logs postgres | tail -50
```

5. **Verify .env settings**:
```env
# From host machine (Python scripts)
POSTGRES_HOST=localhost

# From Airflow containers (use Docker hostname)
# No change needed - Airflow uses hardcoded 'postgres' hostname
```

---

### Issue: DAG Not Appearing in Airflow

**Symptoms**:
- DAG doesn't show in Airflow UI
- Empty DAG list

**Causes**:
- Python syntax errors in DAG file
- DAG file not in `dags/` directory
- Scheduler not running
- Import errors

**Solutions**:

1. **Check for syntax errors**:
```bash
python dags/video_game_etl.py

# Should run without errors
```

2. **Check DAG file location**:
```bash
ls -la dags/video_game_etl.py

# Should exist and be readable
```

3. **Check scheduler logs**:
```bash
docker-compose logs airflow-scheduler | grep -i error
docker-compose logs airflow-scheduler | grep "video_game_etl"
```

4. **Verify scheduler is running**:
```bash
docker-compose ps airflow-scheduler

# Should show "Up" status
```

5. **Check import paths**:
```bash
# Inside scheduler container
docker exec -it airflow-scheduler python -c "import sys; print('\n'.join(sys.path))"

# Should include /opt/airflow
```

6. **Restart scheduler**:
```bash
docker-compose restart airflow-scheduler

# Wait 30 seconds, then refresh Airflow UI
```

7. **Check Airflow configuration**:
```bash
docker exec -it airflow-scheduler airflow config get-value core dags_folder

# Should output: /opt/airflow/dags
```

---

### Issue: Out of Memory Errors

**Symptoms**:
```
ERROR - MemoryError
ERROR - Killed (exit code 137)
```

**Causes**:
- Large XCom payloads
- Too many games fetched
- Insufficient Docker memory allocation

**Solutions**:

1. **Increase Docker memory**:
   - Docker Desktop → Settings → Resources → Memory
   - Increase to 6GB or 8GB
   - Click "Apply & Restart"

2. **Reduce batch size** in `.env`:
```env
ETL_BATCH_SIZE=50  # Smaller batches
ETL_LOOKBACK_DAYS=3  # Fewer days
```

3. **Limit max pages** in extraction:
```python
# In src/etl/extract.py, modify extract_incremental
'developers': self.extract_developers(max_pages=5),  # Reduce from 10
'publishers': self.extract_publishers(max_pages=5),
```

4. **Use S3/Filesystem XCom backend** (advanced):
```python
# In airflow.cfg
[core]
xcom_backend = airflow.providers.amazon.aws.xcom_backends.s3.S3XComBackend
```

5. **Monitor memory usage**:
```bash
docker stats
```

---

### Issue: Slow Performance

**Symptoms**:
- Extract task takes > 30 minutes
- Load task takes > 15 minutes
- High CPU/memory usage

**Causes**:
- Too many API requests
- Inefficient queries
- Missing indexes
- Large data volumes

**Solutions**:

1. **Optimize API requests**:
```env
# Increase page size (max 40)
# Already set to 40 in code
```

2. **Add database indexes** (already created):
```sql
-- Verify indexes exist
\di

-- Should show idx_fact_released, idx_fact_rating, etc.
```

3. **Increase batch size** for database operations:
```python
# In src/utils/db_utils.py
# Default batch_size=1000 is optimal for most cases
```

4. **Monitor query performance**:
```sql
-- Enable query logging
ALTER DATABASE gaming_analytics SET log_min_duration_statement = 1000;

-- Slow queries will appear in PostgreSQL logs
```

5. **Use EXPLAIN ANALYZE**:
```sql
EXPLAIN ANALYZE
SELECT * FROM vw_top_rated_games;
```

---

### Issue: Data Quality Check Failures

**Symptoms**:
```
ERROR - Quality checks failed: ['no_orphaned_facts', 'data_is_fresh']
```

**Causes**:
- Referential integrity violations
- Old data not refreshed
- ETL logic errors

**Solutions**:

1. **Check specific failure**:
```bash
# View quality check task log in Airflow UI
```

2. **For orphaned facts**:
```sql
-- Find orphaned records
SELECT f.* FROM fact_game_metrics f
LEFT JOIN dim_games g ON f.game_id = g.game_id
WHERE g.game_id IS NULL;

-- Fix: Re-run full load or delete orphans
DELETE FROM fact_game_metrics
WHERE game_id NOT IN (SELECT game_id FROM dim_games);
```

3. **For stale data**:
```sql
-- Check last update
SELECT MAX(updated_at) FROM fact_game_metrics;

-- Fix: Trigger manual DAG run
```

4. **Disable specific checks** (temporary):
```python
# In dags/video_game_etl.py, comment out failing check
# checks.append({...})  # <- Comment this line
```

---

### Issue: Metabase Not Connecting

**Symptoms**:
- "Connection failed" in Metabase
- Can't query database

**Causes**:
- Wrong hostname
- PostgreSQL not accessible
- Wrong credentials

**Solutions**:

1. **Use correct hostname**:
   - Use `postgres` (not `localhost`) in Metabase config
   - Docker internal networking

2. **Verify from Metabase container**:
```bash
docker exec -it metabase nc -zv postgres 5432

# Should show "Connection succeeded"
```

3. **Re-configure connection**:
   - Settings → Admin → Databases
   - Delete old connection
   - Add new with correct hostname: `postgres`

---

### Issue: Container Won't Start

**Symptoms**:
```
ERROR - Container exited with code 1
```

**Solutions**:

1. **Check logs**:
```bash
docker-compose logs [service_name]
```

2. **Remove containers and volumes**:
```bash
docker-compose down -v
docker-compose up -d
```

3. **Check port conflicts**:
```bash
# Windows
netstat -ano | findstr :8080
netstat -ano | findstr :5432
netstat -ano | findstr :3000

# Kill process if port is in use
taskkill /PID <pid> /F
```

4. **Rebuild containers**:
```bash
docker-compose build --no-cache
docker-compose up -d
```

---

## Backup and Recovery

### Database Backup

**Manual Backup**:
```bash
# Backup all databases
docker exec postgres pg_dumpall -U airflow > backup_$(date +%Y%m%d).sql

# Backup specific database
docker exec postgres pg_dump -U airflow gaming_analytics > gaming_analytics_backup.sql

# Compressed backup
docker exec postgres pg_dump -U airflow gaming_analytics | gzip > gaming_analytics_$(date +%Y%m%d).sql.gz
```

**Automated Backup Script**:
```bash
#!/bin/bash
# save as: scripts/backup.sh

BACKUP_DIR="./backups"
mkdir -p $BACKUP_DIR

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/gaming_analytics_$DATE.sql.gz"

docker exec postgres pg_dump -U airflow gaming_analytics | gzip > $BACKUP_FILE

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_FILE"
```

**Schedule Backups** (cron):
```bash
# Edit crontab
crontab -e

# Add daily backup at 3 AM
0 3 * * * /path/to/video-game-etl/scripts/backup.sh
```

### Database Restore

**From Backup File**:
```bash
# Stop Airflow to prevent concurrent access
docker-compose stop airflow-scheduler airflow-webserver

# Restore database
gunzip -c gaming_analytics_20241129.sql.gz | \
  docker exec -i postgres psql -U airflow gaming_analytics

# Restart services
docker-compose start airflow-scheduler airflow-webserver
```

**Complete Reset**:
```bash
# WARNING: This deletes all data

# Stop all services
docker-compose down

# Remove volumes (deletes data)
docker volume rm video-game-etl_postgres-db-volume

# Restart services
docker-compose up -d

# Reinitialize database
python scripts/init_db.py
```

### Volume Backup

**Backup Docker Volume**:
```bash
# Create backup of PostgreSQL volume
docker run --rm \
  -v video-game-etl_postgres-db-volume:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/postgres_volume_$(date +%Y%m%d).tar.gz /data
```

**Restore Docker Volume**:
```bash
# Stop PostgreSQL
docker-compose stop postgres

# Restore volume
docker run --rm \
  -v video-game-etl_postgres-db-volume:/data \
  -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/postgres_volume_20241129.tar.gz -C /

# Start PostgreSQL
docker-compose start postgres
```

## Performance Tuning

### PostgreSQL Tuning

**Connection Pooling** (already configured in code):
```python
# In src/utils/db_utils.py
min_connections=1,
max_connections=10
```

**Database Configuration** (for larger datasets):
```sql
-- Increase work memory for complex queries
ALTER SYSTEM SET work_mem = '256MB';

-- Increase shared buffers
ALTER SYSTEM SET shared_buffers = '256MB';

-- Reload configuration
SELECT pg_reload_conf();
```

### Airflow Tuning

**Parallelism** (edit `docker-compose.yml`):
```yaml
environment:
  AIRFLOW__CORE__PARALLELISM: 16  # Max parallel tasks
  AIRFLOW__CORE__DAG_CONCURRENCY: 8  # Max tasks per DAG
  AIRFLOW__CORE__MAX_ACTIVE_RUNS_PER_DAG: 1  # Prevent overlaps
```

### ETL Tuning

**Batch Size** (`.env`):
```env
ETL_BATCH_SIZE=200  # Larger batches = fewer round trips
```

**Rate Limiting** (`.env`):
```env
RAWG_RATE_LIMIT=5  # Increase if API allows (test carefully)
```

## Maintenance Tasks

### Weekly Tasks

- [ ] Check disk space: `docker system df`
- [ ] Review error logs: `docker-compose logs | grep ERROR`
- [ ] Verify DAG success rate in Airflow UI
- [ ] Check data freshness: `SELECT MAX(updated_at) FROM fact_game_metrics`

### Monthly Tasks

- [ ] Backup database
- [ ] Review and clean old log files: `find logs/ -mtime +30 -delete`
- [ ] Update dependencies: `pip list --outdated`
- [ ] Check for Airflow updates
- [ ] Vacuum database: `VACUUM ANALYZE;`

### Quarterly Tasks

- [ ] Review API usage trends
- [ ] Optimize slow queries
- [ ] Update documentation
- [ ] Review and update data retention policies

## Shutdown and Startup

### Graceful Shutdown

```bash
# Stop all services (preserves data)
docker-compose stop

# Stop and remove containers (preserves volumes)
docker-compose down

# Stop and remove everything including volumes (DELETES DATA)
docker-compose down -v
```

### Startup After Shutdown

```bash
# Start all services
docker-compose up -d

# Verify services are healthy
docker-compose ps

# Check logs
docker-compose logs -f
```

## Security Best Practices

1. **Never commit `.env` to git**
   - Already in `.gitignore`

2. **Change default passwords** (production):
```bash
# Airflow
docker exec -it airflow-webserver airflow users create --username admin --password <strong_password> ...

# PostgreSQL (edit docker-compose.yml)
POSTGRES_PASSWORD: <strong_password>
```

3. **Use secrets management** (production):
   - AWS Secrets Manager
   - HashiCorp Vault
   - Airflow Connections/Variables

4. **Restrict network access**:
   - Remove port mappings for PostgreSQL in docker-compose.yml
   - Use reverse proxy (nginx) for Airflow/Metabase

5. **Enable SSL/TLS** (production):
   - Configure PostgreSQL SSL
   - Use HTTPS for Airflow/Metabase

## Support and Resources

- **Airflow Documentation**: https://airflow.apache.org/docs/
- **PostgreSQL Documentation**: https://www.postgresql.org/docs/
- **Metabase Documentation**: https://www.metabase.com/docs/
- **RAWG API Docs**: https://rawg.io/apidocs
- **Project Issues**: Check project README for contact info

## Appendix: Common Commands

```bash
# Service Management
docker-compose up -d              # Start all services
docker-compose down               # Stop and remove containers
docker-compose restart [service]  # Restart specific service
docker-compose ps                 # List service status
docker-compose logs -f [service]  # Follow service logs

# Database
docker exec -it postgres psql -U airflow -d gaming_analytics
docker exec postgres pg_dump -U airflow gaming_analytics > backup.sql

# Airflow
docker exec -it airflow-webserver airflow dags list
docker exec -it airflow-webserver airflow dags trigger video_game_etl
docker exec -it airflow-webserver airflow tasks test video_game_etl extract_data 2024-01-01

# Monitoring
docker stats                      # Container resource usage
docker system df                  # Docker disk usage
docker-compose top                # Process list
```
