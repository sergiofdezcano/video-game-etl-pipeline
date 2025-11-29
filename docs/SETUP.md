# Quick Start Guide

This guide will help you set up and run the Video Game ETL Pipeline on your local machine.

## Prerequisites

Before you begin, ensure you have the following installed:

- [ ] **Docker Desktop** (v20.10+)
- [ ] **Docker Compose** (v2.0+)
- [ ] **Python 3.11+**
- [ ] **Git**
- [ ] **RAWG API Key** (free at https://rawg.io/apidocs)

## Step 1: Clone the Repository

```bash
git clone <repository-url>
cd video-game-etl
```

## Step 2: Get RAWG API Key

1. Visit https://rawg.io/apidocs
2. Sign up for a free account
3. Navigate to your API settings
4. Copy your API key (allows 20,000 requests/day)

## Step 3: Configure Environment

Create your environment configuration:

```bash
cp .env.example .env
```

Edit `.env` and add your RAWG API key:

```bash
RAWG_API_KEY=your_actual_api_key_here
```

## Step 4: Start Infrastructure

Launch all services using Docker Compose:

```bash
docker-compose up -d
```

This starts:
- **PostgreSQL** on port 5432
- **Airflow Webserver** on port 8080
- **Airflow Scheduler**
- **Metabase** on port 3000

Wait ~30 seconds for services to initialize.

## Step 5: Verify Services

Check that all containers are running:

```bash
docker-compose ps
```

You should see 5 containers in "Up" state.

## Step 6: Initialize Database

Create the data warehouse schema:

```bash
# Create Python virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python scripts/init_db.py
```

Expected output:
```
✓ Table dim_games created
✓ Table dim_genres created
✓ Table dim_platforms created
...
Database initialization complete
```

## Step 7: Access Airflow

1. Open http://localhost:8080 in your browser
2. Login with default credentials:
   - Username: `airflow`
   - Password: `airflow`

## Step 8: Run the Pipeline

1. In the Airflow UI, find the `video_game_etl` DAG
2. Toggle the DAG to "On" (switch on the left)
3. Click the "Play" button → "Trigger DAG"
4. Watch the pipeline execute (should take 5-10 minutes for first run)

### Pipeline Tasks

The DAG will execute these tasks in order:
1. **extract_data** - Fetch data from RAWG API
2. **transform_data** - Normalize and clean data
3. **load_data** - Insert into PostgreSQL warehouse
4. **quality_checks** - Validate data integrity

## Step 9: Verify Data

Check that data was loaded successfully:

```bash
# Connect to PostgreSQL
docker exec -it video-game-etl-postgres-1 psql -U airflow -d gaming_analytics

# Run sample queries
SELECT COUNT(*) FROM dim_games;
SELECT COUNT(*) FROM fact_game_metrics;

# Exit
\q
```

## Step 10: Access Metabase Dashboard

1. Open http://localhost:3000
2. Complete initial setup wizard:
   - Create admin account
   - Connect to PostgreSQL:
     - **Database type**: PostgreSQL
     - **Host**: postgres
     - **Port**: 5432
     - **Database name**: gaming_analytics
     - **Username**: airflow
     - **Password**: airflow

3. Create your first dashboard with sample questions:
   - Top rated games
   - Games by genre
   - Platform statistics

## Verification Checklist

After setup, verify everything works:

- [ ] Docker containers running (`docker-compose ps`)
- [ ] Airflow UI accessible (http://localhost:8080)
- [ ] Database initialized (`dim_games` table exists)
- [ ] DAG execution successful (all tasks green)
- [ ] Data loaded (row counts > 0)
- [ ] Metabase connected (http://localhost:3000)

## Common First-Time Issues

### Issue: "API key invalid"

**Solution**: Check that you copied the API key correctly in `.env`

```bash
# Verify API key is set
cat .env | grep RAWG_API_KEY
```

### Issue: "Port 5432 already in use"

**Solution**: You have another PostgreSQL instance running

```bash
# Stop local PostgreSQL
# Windows: services.msc
# Linux: sudo systemctl stop postgresql
```

### Issue: "Airflow DAG not appearing"

**Solution**: Check for Python syntax errors

```bash
python dags/video_game_etl.py
# Should run without errors
```

### Issue: "Database initialization failed"

**Solution**: Ensure PostgreSQL container is fully started

```bash
docker-compose logs postgres
# Look for "database system is ready to accept connections"
```

## Next Steps

- Read [ARCHITECTURE.md](./ARCHITECTURE.md) to understand the pipeline design
- Read [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) to customize the pipeline
- Read [OPERATIONS.md](./OPERATIONS.md) for production deployment

## Stopping the Pipeline

```bash
# Stop all services
docker-compose down

# Stop and remove all data
docker-compose down -v
```

## Getting Help

If you encounter issues not covered here:

1. Check logs: `docker-compose logs <service-name>`
2. Review [OPERATIONS.md](./OPERATIONS.md) troubleshooting section
3. Verify environment variables in `.env`
