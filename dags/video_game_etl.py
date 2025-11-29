"""
Airflow DAG for Video Game ETL Pipeline.

This DAG orchestrates the extraction, transformation, and loading of video game data
from the RAWG API into a PostgreSQL data warehouse.

DAG Schedule: Daily at 2 AM
Retry Policy: 3 retries with 5-minute delay
Timeout: 2 hours
"""
from datetime import datetime, timedelta
import logging
import sys
import os
from typing import Dict, Any

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.etl import GameDataExtractor, GameDataTransformer, GameDataLoader
from src.etl.extract import ExtractionError
from src.etl.transform import TransformationError
from src.etl.load import LoadError
from src.utils import setup_logging, DatabaseManager


# Configure logging
setup_logging(level='INFO')
logger = logging.getLogger(__name__)


# Default DAG arguments
default_args = {
    'owner': 'data-engineer',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=2)
}


def extract_data(**context: Any) -> Dict[str, int]:
    """
    Task: Extract data from RAWG API.

    Extracts games, genres, platforms, developers, and publishers from the
    RAWG API for the last 7 days. Data is pushed to XCom for downstream tasks.

    Args:
        **context: Airflow context dictionary

    Returns:
        Dictionary with extraction statistics

    Raises:
        ExtractionError: If extraction fails
    """
    logger.info("Starting data extraction")

    try:
        extractor = GameDataExtractor()

        # Extract data with 7-day lookback for incremental updates
        data = extractor.extract_incremental(lookback_days=7)

        # Validate extracted data
        if not data or not data.get('games'):
            logger.warning("No games extracted - this may be normal for quiet periods")

        # Push data to XCom for next tasks
        context['task_instance'].xcom_push(key='raw_data', value=data)

        stats = {
            'games_count': len(data.get('games', [])),
            'genres_count': len(data.get('genres', [])),
            'platforms_count': len(data.get('platforms', [])),
            'developers_count': len(data.get('developers', [])),
            'publishers_count': len(data.get('publishers', []))
        }

        logger.info(
            f"Extraction complete: "
            f"{stats['games_count']} games, "
            f"{stats['genres_count']} genres, "
            f"{stats['platforms_count']} platforms, "
            f"{stats['developers_count']} developers, "
            f"{stats['publishers_count']} publishers"
        )

        return stats

    except ExtractionError as e:
        logger.error(f"Extraction failed: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Unexpected error during extraction: {e}", exc_info=True)
        raise


def transform_data(**context: Any) -> Dict[str, int]:
    """
    Task: Transform and normalize extracted data.

    Transforms raw API data into warehouse-ready format:
    - Normalizes game dimension data
    - Creates fact metrics per game-platform combination
    - Extracts dimension data for genres, platforms, developers, publishers
    - Creates bridge table for many-to-many game-genre relationship

    Args:
        **context: Airflow context dictionary

    Returns:
        Dictionary with transformation statistics

    Raises:
        TransformationError: If transformation fails
        ValueError: If no data received from extraction
    """
    logger.info("Starting data transformation")

    try:
        # Pull raw data from XCom
        raw_data = context['task_instance'].xcom_pull(
            task_ids='extract_data',
            key='raw_data'
        )

        if not raw_data:
            raise ValueError("No data received from extraction task")

        transformer = GameDataTransformer()

        # Transform all data entities
        transformed_data: Dict[str, Any] = {
            'games': transformer.transform_games(raw_data.get('games', [])),
            'fact_metrics': transformer.transform_fact_metrics(raw_data.get('games', [])),
            'genres': transformer.transform_genres(raw_data.get('games', [])),
            'platforms': transformer.transform_platforms(raw_data.get('platforms', [])),
            'developers': transformer.transform_developers(raw_data.get('developers', [])),
            'publishers': transformer.transform_publishers(raw_data.get('publishers', [])),
            'game_genre_bridge': transformer.create_game_genre_bridge(raw_data.get('games', []))
        }

        # Data quality validation with 90% threshold
        if transformed_data['games']:
            if not transformer.validate_data_quality(
                transformed_data['games'],
                required_fields=['game_id', 'name'],
                threshold=90.0
            ):
                logger.warning("Data quality check failed for games (< 90% valid records)")
        else:
            logger.warning("No games to validate")

        # Push transformed data to XCom
        context['task_instance'].xcom_push(key='transformed_data', value=transformed_data)

        stats = {
            'games_count': len(transformed_data['games']),
            'fact_metrics_count': len(transformed_data['fact_metrics']),
            'genres_count': len(transformed_data['genres']),
            'platforms_count': len(transformed_data['platforms']),
            'bridge_count': len(transformed_data['game_genre_bridge'])
        }

        logger.info(
            f"Transformation complete: "
            f"{stats['games_count']} games, "
            f"{stats['fact_metrics_count']} fact metrics, "
            f"{stats['bridge_count']} game-genre relationships"
        )

        return stats

    except TransformationError as e:
        logger.error(f"Transformation failed: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Unexpected error during transformation: {e}", exc_info=True)
        raise


def load_data(**context: Any) -> Dict[str, int]:
    """
    Task: Load transformed data into data warehouse.

    Loads data in proper order to maintain referential integrity:
    1. Dimension tables (genres, platforms, developers, publishers)
    2. Games dimension (references developers/publishers)
    3. Fact table (references games and platforms)
    4. Bridge table (references games and genres)

    Args:
        **context: Airflow context dictionary

    Returns:
        Dictionary with loading statistics

    Raises:
        LoadError: If loading fails
        ValueError: If no data received from transformation
    """
    logger.info("Starting data loading")

    loader = None
    try:
        # Pull transformed data from XCom
        transformed_data = context['task_instance'].xcom_pull(
            task_ids='transform_data',
            key='transformed_data'
        )

        if not transformed_data:
            raise ValueError("No data received from transformation task")

        loader = GameDataLoader()

        # Load dimensions first (to maintain referential integrity)
        stats: Dict[str, int] = {}

        # Step 1: Load independent dimensions
        stats['genres'] = loader.load_genres(transformed_data.get('genres', []))
        stats['platforms'] = loader.load_platforms(transformed_data.get('platforms', []))
        stats['developers'] = loader.load_developers(transformed_data.get('developers', []))
        stats['publishers'] = loader.load_publishers(transformed_data.get('publishers', []))

        # Step 2: Load games (depends on developers/publishers)
        stats['games'] = loader.load_games(transformed_data.get('games', []))

        # Step 3: Load fact table (depends on games and platforms)
        stats['fact_metrics'] = loader.load_fact_metrics(transformed_data.get('fact_metrics', []))

        # Step 4: Load bridge table (depends on games and genres)
        stats['game_genre_bridge'] = loader.load_game_genre_bridge(
            transformed_data.get('game_genre_bridge', [])
        )

        logger.info(
            f"Loading complete: "
            f"{stats.get('games', 0)} games, "
            f"{stats.get('fact_metrics', 0)} fact metrics, "
            f"{stats.get('game_genre_bridge', 0)} bridge records"
        )

        return stats

    except LoadError as e:
        logger.error(f"Loading failed: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Unexpected error during loading: {e}", exc_info=True)
        raise
    finally:
        # Always close loader to free database connections
        if loader is not None:
            loader.close()


def run_quality_checks(**context: Any) -> Dict[str, Any]:
    """
    Task: Run data quality checks on loaded data.

    Performs comprehensive validation:
    1. Dimension and fact tables have records
    2. No orphaned fact records (referential integrity)
    3. Data freshness (updated within last 2 days)

    Args:
        **context: Airflow context dictionary

    Returns:
        Dictionary with check results

    Raises:
        ValueError: If any quality checks fail
    """
    logger.info("Running data quality checks")

    db = None
    try:
        db = DatabaseManager(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=int(os.getenv('POSTGRES_PORT', '5432')),
            database=os.getenv('POSTGRES_DB', 'gaming_analytics'),
            user=os.getenv('POSTGRES_USER', 'airflow'),
            password=os.getenv('POSTGRES_PASSWORD', 'airflow')
        )

        checks = []

        # Check 1: Fact table has records
        fact_count = db.get_row_count('fact_game_metrics')
        checks.append({
            'check': 'fact_table_not_empty',
            'passed': fact_count > 0,
            'value': fact_count
        })

        # Check 2: All critical dimensions have records
        for table in ['dim_games', 'dim_genres', 'dim_platforms']:
            count = db.get_row_count(table)
            checks.append({
                'check': f'{table}_not_empty',
                'passed': count > 0,
                'value': count
            })

        # Check 3: No orphaned fact records (referential integrity)
        query = """
            SELECT COUNT(*)
            FROM fact_game_metrics f
            LEFT JOIN dim_games g ON f.game_id = g.game_id
            WHERE g.game_id IS NULL
        """
        result = db.execute_query(query, fetch=True)
        orphaned_count = result[0][0] if result else 0
        checks.append({
            'check': 'no_orphaned_facts',
            'passed': orphaned_count == 0,
            'value': orphaned_count
        })

        # Check 4: Fact table freshness (updated in last 2 days)
        query = """
            SELECT COALESCE(MAX(updated_at) > NOW() - INTERVAL '2 days', false)
            FROM fact_game_metrics
        """
        result = db.execute_query(query, fetch=True)
        is_fresh = result[0][0] if result else False
        checks.append({
            'check': 'data_is_fresh',
            'passed': is_fresh if is_fresh is not None else False,
            'value': is_fresh
        })

        # Check 5: No null game IDs in fact table
        query = """
            SELECT COUNT(*)
            FROM fact_game_metrics
            WHERE game_id IS NULL OR platform_id IS NULL
        """
        result = db.execute_query(query, fetch=True)
        null_count = result[0][0] if result else 0
        checks.append({
            'check': 'no_null_keys',
            'passed': null_count == 0,
            'value': null_count
        })

        # Log results
        failed_checks = [c for c in checks if not c['passed']]

        for check in checks:
            status = "PASSED" if check['passed'] else "FAILED"
            logger.info(f"Quality check [{status}]: {check['check']} = {check['value']}")

        if failed_checks:
            failed_names = [c['check'] for c in failed_checks]
            logger.error(f"{len(failed_checks)} quality checks failed: {failed_names}")
            raise ValueError(f"Quality checks failed: {failed_names}")

        logger.info("All quality checks passed")

        return {
            'total_checks': len(checks),
            'passed': len(checks) - len(failed_checks),
            'failed': len(failed_checks),
            'checks': checks
        }

    except Exception as e:
        logger.error(f"Quality checks failed with error: {e}", exc_info=True)
        raise
    finally:
        # Always close database connection
        if db is not None:
            db.close()


# Define the DAG
with DAG(
    dag_id='video_game_etl',
    default_args=default_args,
    description='ETL pipeline for video game analytics from RAWG API',
    schedule_interval='0 2 * * *',  # Daily at 2 AM
    start_date=days_ago(1),
    catchup=False,
    tags=['gaming', 'etl', 'rawg'],
    max_active_runs=1
) as dag:

    # Task 1: Extract data from RAWG API
    extract_task = PythonOperator(
        task_id='extract_data',
        python_callable=extract_data,
        provide_context=True
    )

    # Task 2: Transform and normalize data
    transform_task = PythonOperator(
        task_id='transform_data',
        python_callable=transform_data,
        provide_context=True
    )

    # Task 3: Load data into warehouse
    load_task = PythonOperator(
        task_id='load_data',
        python_callable=load_data,
        provide_context=True
    )

    # Task 4: Run data quality checks
    quality_check_task = PythonOperator(
        task_id='quality_checks',
        python_callable=run_quality_checks,
        provide_context=True
    )

    # Define task dependencies
    extract_task >> transform_task >> load_task >> quality_check_task
