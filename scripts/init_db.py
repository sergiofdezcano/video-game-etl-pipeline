"""
Database initialization script.
Creates all tables and views in the gaming_analytics database.
"""
import os
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from src.utils import DatabaseManager, setup_logging


# Load environment variables
load_dotenv()

# Configure logging
setup_logging(level='INFO')
logger = logging.getLogger(__name__)


def init_database():
    """Initialize the database with schema."""

    logger.info("Starting database initialization")

    # Connect to database
    db = DatabaseManager(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=int(os.getenv('POSTGRES_PORT', 5432)),
        database=os.getenv('POSTGRES_DB', 'gaming_analytics'),
        user=os.getenv('POSTGRES_USER', 'airflow'),
        password=os.getenv('POSTGRES_PASSWORD', 'airflow')
    )

    # Read schema SQL file
    schema_file = Path(__file__).parent.parent / 'sql' / 'ddl' / 'schema.sql'

    if not schema_file.exists():
        logger.error(f"Schema file not found: {schema_file}")
        return False

    logger.info(f"Reading schema from {schema_file}")

    with open(schema_file, 'r') as f:
        schema_sql = f.read()

    # Execute schema creation
    try:
        with db.get_cursor() as cursor:
            cursor.execute(schema_sql)

        logger.info("Schema created successfully")

        # Verify tables were created
        tables = [
            'dim_games',
            'dim_genres',
            'dim_platforms',
            'dim_developers',
            'dim_publishers',
            'fact_game_metrics',
            'bridge_game_genre'
        ]

        for table in tables:
            if db.table_exists(table):
                logger.info(f"✓ Table {table} created")
            else:
                logger.error(f"✗ Table {table} NOT created")

        db.close()
        logger.info("Database initialization complete")
        return True

    except Exception as e:
        logger.error(f"Error creating schema: {e}")
        db.close()
        return False


if __name__ == '__main__':
    success = init_database()
    sys.exit(0 if success else 1)
