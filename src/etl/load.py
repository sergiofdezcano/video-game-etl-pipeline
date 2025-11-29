"""
Data loading module for inserting data into PostgreSQL data warehouse.
"""
import logging
from typing import List, Dict, Any, Optional
import os
from dotenv import load_dotenv

from src.utils import DatabaseManager


load_dotenv()
logger = logging.getLogger(__name__)


class LoadError(Exception):
    """Base exception for data loading errors."""
    pass


class GameDataLoader:
    """Load transformed data into PostgreSQL data warehouse."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Initialize loader.

        Args:
            db_manager: DatabaseManager instance (creates one if not provided)

        Raises:
            LoadError: If database connection cannot be established
        """
        try:
            if db_manager:
                self.db = db_manager
            else:
                self.db = DatabaseManager(
                    host=os.getenv('POSTGRES_HOST', 'localhost'),
                    port=int(os.getenv('POSTGRES_PORT', '5432')),
                    database=os.getenv('POSTGRES_DB', 'gaming_analytics'),
                    user=os.getenv('POSTGRES_USER', 'airflow'),
                    password=os.getenv('POSTGRES_PASSWORD', 'airflow')
                )

            logger.info("GameDataLoader initialized")

        except Exception as e:
            logger.error(f"Failed to initialize GameDataLoader: {e}", exc_info=True)
            raise LoadError(f"Failed to initialize loader: {e}") from e

    def load_games(self, games: List[Dict[str, Any]]) -> int:
        """
        Load game dimension data.

        Uses bulk upsert for optimal performance with large datasets.
        Updates existing records and inserts new ones atomically.

        Args:
            games: List of game dictionaries

        Returns:
            Number of rows loaded

        Raises:
            LoadError: If loading fails
        """
        if not games:
            logger.warning("No games to load")
            return 0

        logger.info(f"Loading {len(games)} games into dim_games")

        try:
            self.db.bulk_upsert(
                table='dim_games',
                data=games,
                conflict_columns=['game_id'],
                update_columns=['name', 'slug', 'description', 'released',
                              'background_image', 'website', 'developer_id',
                              'developer_name', 'publisher_id', 'publisher_name',
                              'esrb_rating', 'updated_at']
            )

            logger.info(f"Successfully loaded {len(games)} games")
            return len(games)

        except Exception as e:
            logger.error(f"Failed to load games: {e}", exc_info=True)
            raise LoadError(f"Failed to load games into dim_games: {e}") from e

    def load_genres(self, genres: List[Dict[str, Any]]) -> int:
        """
        Load genre dimension data.

        Args:
            genres: List of genre dictionaries

        Returns:
            Number of rows loaded

        Raises:
            LoadError: If loading fails
        """
        if not genres:
            logger.warning("No genres to load")
            return 0

        logger.info(f"Loading {len(genres)} genres into dim_genres")

        try:
            self.db.bulk_upsert(
                table='dim_genres',
                data=genres,
                conflict_columns=['genre_id']
            )

            logger.info(f"Successfully loaded {len(genres)} genres")
            return len(genres)

        except Exception as e:
            logger.error(f"Failed to load genres: {e}", exc_info=True)
            raise LoadError(f"Failed to load genres into dim_genres: {e}") from e

    def load_platforms(self, platforms: List[Dict[str, Any]]) -> int:
        """
        Load platform dimension data.

        Args:
            platforms: List of platform dictionaries

        Returns:
            Number of rows loaded

        Raises:
            LoadError: If loading fails
        """
        if not platforms:
            logger.warning("No platforms to load")
            return 0

        logger.info(f"Loading {len(platforms)} platforms into dim_platforms")

        try:
            self.db.bulk_upsert(
                table='dim_platforms',
                data=platforms,
                conflict_columns=['platform_id']
            )

            logger.info(f"Successfully loaded {len(platforms)} platforms")
            return len(platforms)

        except Exception as e:
            logger.error(f"Failed to load platforms: {e}", exc_info=True)
            raise LoadError(f"Failed to load platforms into dim_platforms: {e}") from e

    def load_developers(self, developers: List[Dict[str, Any]]) -> int:
        """
        Load developer dimension data.

        Args:
            developers: List of developer dictionaries

        Returns:
            Number of rows loaded

        Raises:
            LoadError: If loading fails
        """
        if not developers:
            logger.warning("No developers to load")
            return 0

        logger.info(f"Loading {len(developers)} developers into dim_developers")

        try:
            self.db.bulk_upsert(
                table='dim_developers',
                data=developers,
                conflict_columns=['developer_id']
            )

            logger.info(f"Successfully loaded {len(developers)} developers")
            return len(developers)

        except Exception as e:
            logger.error(f"Failed to load developers: {e}", exc_info=True)
            raise LoadError(f"Failed to load developers into dim_developers: {e}") from e

    def load_publishers(self, publishers: List[Dict[str, Any]]) -> int:
        """
        Load publisher dimension data.

        Args:
            publishers: List of publisher dictionaries

        Returns:
            Number of rows loaded

        Raises:
            LoadError: If loading fails
        """
        if not publishers:
            logger.warning("No publishers to load")
            return 0

        logger.info(f"Loading {len(publishers)} publishers into dim_publishers")

        try:
            self.db.bulk_upsert(
                table='dim_publishers',
                data=publishers,
                conflict_columns=['publisher_id']
            )

            logger.info(f"Successfully loaded {len(publishers)} publishers")
            return len(publishers)

        except Exception as e:
            logger.error(f"Failed to load publishers: {e}", exc_info=True)
            raise LoadError(f"Failed to load publishers into dim_publishers: {e}") from e

    def load_fact_metrics(self, metrics: List[Dict[str, Any]]) -> int:
        """
        Load fact table metrics.

        Bulk loads game metrics with composite key (game_id, platform_id).
        This is typically the largest table, so batch performance is critical.

        Args:
            metrics: List of metric dictionaries

        Returns:
            Number of rows loaded

        Raises:
            LoadError: If loading fails
        """
        if not metrics:
            logger.warning("No metrics to load")
            return 0

        logger.info(f"Loading {len(metrics)} metrics into fact_game_metrics")

        try:
            self.db.bulk_upsert(
                table='fact_game_metrics',
                data=metrics,
                conflict_columns=['game_id', 'platform_id'],
                update_columns=['released', 'rating', 'rating_top', 'ratings_count',
                              'reviews_count', 'metacritic_score', 'playtime',
                              'added', 'suggestions_count', 'updated_at']
            )

            logger.info(f"Successfully loaded {len(metrics)} fact metrics")
            return len(metrics)

        except Exception as e:
            logger.error(f"Failed to load fact metrics: {e}", exc_info=True)
            raise LoadError(f"Failed to load metrics into fact_game_metrics: {e}") from e

    def load_game_genre_bridge(self, bridge_records: List[Dict[str, Any]]) -> int:
        """
        Load game-genre bridge table.

        Handles many-to-many relationship between games and genres.

        Args:
            bridge_records: List of game_id-genre_id pairs

        Returns:
            Number of rows loaded

        Raises:
            LoadError: If loading fails
        """
        if not bridge_records:
            logger.warning("No bridge records to load")
            return 0

        logger.info(f"Loading {len(bridge_records)} records into bridge_game_genre")

        try:
            self.db.bulk_upsert(
                table='bridge_game_genre',
                data=bridge_records,
                conflict_columns=['game_id', 'genre_id']
            )

            logger.info(f"Successfully loaded {len(bridge_records)} bridge records")
            return len(bridge_records)

        except Exception as e:
            logger.error(f"Failed to load bridge records: {e}", exc_info=True)
            raise LoadError(f"Failed to load bridge_game_genre: {e}") from e

    def get_data_warehouse_stats(self) -> Dict[str, int]:
        """
        Get row counts for all tables.

        Useful for monitoring data warehouse size and validating load operations.

        Returns:
            Dictionary with table names and row counts
        """
        tables = [
            'dim_games',
            'dim_genres',
            'dim_platforms',
            'dim_developers',
            'dim_publishers',
            'fact_game_metrics',
            'bridge_game_genre'
        ]

        stats: Dict[str, int] = {}
        for table in tables:
            try:
                count = self.db.get_row_count(table)
                stats[table] = count
                logger.debug(f"Table {table}: {count} rows")
            except Exception as e:
                logger.warning(f"Could not get count for {table}: {e}")
                stats[table] = -1

        logger.info(f"Data warehouse stats: {sum(v for v in stats.values() if v > 0)} total rows")
        return stats

    def close(self) -> None:
        """
        Close database connections.

        Should be called when loader is no longer needed to free resources.
        """
        try:
            self.db.close()
            logger.info("GameDataLoader closed successfully")
        except Exception as e:
            logger.warning(f"Error closing GameDataLoader: {e}")
