"""
Data transformation module for cleaning and normalizing game data.
"""
import logging
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
import pandas as pd


logger = logging.getLogger(__name__)


class TransformationError(Exception):
    """Base exception for transformation errors."""
    pass


class GameDataTransformer:
    """Transform and normalize game data for data warehouse."""

    @staticmethod
    def transform_games(raw_games: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform raw game data to normalized format.

        Optimized for memory efficiency using list comprehension when possible
        and explicit type handling.

        Args:
            raw_games: List of raw game dictionaries from API

        Returns:
            List of transformed game dictionaries

        Raises:
            TransformationError: If critical transformation fails
        """
        if not raw_games:
            logger.warning("No games provided for transformation")
            return []

        logger.info(f"Transforming {len(raw_games)} games")
        transformed: List[Dict[str, Any]] = []
        failed_count = 0
        current_time = datetime.now()  # Single timestamp for all records

        for game in raw_games:
            try:
                # Validate required fields
                if 'id' not in game or 'name' not in game:
                    logger.warning(f"Game missing required fields: {game}")
                    failed_count += 1
                    continue

                # Extract developers (take first if multiple)
                developers = game.get('developers', [])
                developer_id: Optional[int] = developers[0].get('id') if developers else None
                developer_name: Optional[str] = developers[0].get('name') if developers else None

                # Extract publishers (take first if multiple)
                publishers = game.get('publishers', [])
                publisher_id: Optional[int] = publishers[0].get('id') if publishers else None
                publisher_name: Optional[str] = publishers[0].get('name') if publishers else None

                # Extract ESRB rating safely
                esrb_rating: Optional[str] = None
                esrb = game.get('esrb_rating')
                if esrb and isinstance(esrb, dict):
                    esrb_rating = esrb.get('name')

                transformed_game: Dict[str, Any] = {
                    'game_id': game['id'],
                    'name': game['name'],
                    'slug': game.get('slug'),
                    'description': game.get('description_raw'),
                    'released': game.get('released'),
                    'background_image': game.get('background_image'),
                    'website': game.get('website'),
                    'developer_id': developer_id,
                    'developer_name': developer_name,
                    'publisher_id': publisher_id,
                    'publisher_name': publisher_name,
                    'esrb_rating': esrb_rating,
                    'updated_at': current_time
                }

                transformed.append(transformed_game)

            except KeyError as e:
                logger.warning(f"Missing key in game {game.get('id', 'unknown')}: {e}")
                failed_count += 1
                continue
            except Exception as e:
                logger.warning(f"Error transforming game {game.get('id', 'unknown')}: {e}")
                failed_count += 1
                continue

        success_rate = (len(transformed) / len(raw_games)) * 100 if raw_games else 0
        logger.info(
            f"Successfully transformed {len(transformed)}/{len(raw_games)} games "
            f"({success_rate:.1f}% success rate)"
        )

        if failed_count > 0:
            logger.warning(f"{failed_count} games failed transformation")

        return transformed

    @staticmethod
    def transform_fact_metrics(raw_games: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform games into fact table metrics.

        Creates one fact record per game-platform combination for proper
        dimensional modeling. Uses pre-allocated list for better memory efficiency.

        Args:
            raw_games: List of raw game dictionaries

        Returns:
            List of fact metrics dictionaries
        """
        if not raw_games:
            logger.warning("No games provided for fact metrics transformation")
            return []

        logger.info(f"Transforming {len(raw_games)} games to fact metrics")
        fact_metrics: List[Dict[str, Any]] = []
        failed_count = 0
        current_time = datetime.now()

        for game in raw_games:
            try:
                game_id = game.get('id')
                if not game_id:
                    logger.warning("Game missing ID, skipping fact metrics")
                    failed_count += 1
                    continue

                # Extract platforms and create one fact row per platform
                platforms = game.get('platforms', [])

                if not platforms:
                    logger.debug(f"Game {game_id} has no platforms, skipping fact metrics")
                    continue

                for platform_info in platforms:
                    if not isinstance(platform_info, dict):
                        continue

                    platform = platform_info.get('platform', {})
                    platform_id = platform.get('id')

                    if not platform_id:
                        logger.debug(f"Platform missing ID for game {game_id}, skipping")
                        continue

                    fact: Dict[str, Any] = {
                        'game_id': game_id,
                        'platform_id': platform_id,
                        'released': game.get('released'),
                        'rating': game.get('rating'),
                        'rating_top': game.get('rating_top'),
                        'ratings_count': game.get('ratings_count', 0),
                        'reviews_count': game.get('reviews_count', 0),
                        'metacritic_score': game.get('metacritic'),
                        'playtime': game.get('playtime', 0),
                        'added': game.get('added', 0),
                        'suggestions_count': game.get('suggestions_count', 0),
                        'updated_at': current_time
                    }

                    fact_metrics.append(fact)

            except KeyError as e:
                logger.warning(f"Missing key creating fact for game {game.get('id', 'unknown')}: {e}")
                failed_count += 1
                continue
            except Exception as e:
                logger.warning(f"Error creating fact for game {game.get('id', 'unknown')}: {e}")
                failed_count += 1
                continue

        logger.info(f"Created {len(fact_metrics)} fact metric records")

        if failed_count > 0:
            logger.warning(f"{failed_count} games failed fact metrics transformation")

        return fact_metrics

    @staticmethod
    def transform_genres(raw_games: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract and transform genre data.

        Uses dict for deduplication to ensure we only keep unique genres.
        Memory-efficient: only stores unique genres, not all genre references.

        Args:
            raw_games: List of raw game dictionaries

        Returns:
            List of unique genre dictionaries
        """
        if not raw_games:
            logger.warning("No games provided for genre extraction")
            return []

        logger.info("Extracting genres from games")
        genres_dict: Dict[int, Dict[str, Any]] = {}

        for game in raw_games:
            genres_list = game.get('genres', [])
            if not isinstance(genres_list, list):
                continue

            for genre in genres_list:
                if not isinstance(genre, dict):
                    continue

                try:
                    genre_id = genre.get('id')
                    if not genre_id:
                        continue

                    # Only add if not already present (deduplication)
                    if genre_id not in genres_dict:
                        genres_dict[genre_id] = {
                            'genre_id': genre_id,
                            'genre_name': genre.get('name'),
                            'slug': genre.get('slug'),
                            'games_count': genre.get('games_count', 0),
                            'image_background': genre.get('image_background')
                        }
                except Exception as e:
                    logger.debug(f"Error processing genre: {e}")
                    continue

        genres = list(genres_dict.values())
        logger.info(f"Extracted {len(genres)} unique genres")
        return genres

    @staticmethod
    def transform_platforms(raw_platforms: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform platform data.

        Args:
            raw_platforms: List of raw platform dictionaries

        Returns:
            List of transformed platform dictionaries
        """
        logger.info(f"Transforming {len(raw_platforms)} platforms")
        transformed = []

        for platform in raw_platforms:
            try:
                transformed_platform = {
                    'platform_id': platform['id'],
                    'platform_name': platform['name'],
                    'slug': platform.get('slug'),
                    'games_count': platform.get('games_count', 0),
                    'image_background': platform.get('image_background'),
                    'year_start': platform.get('year_start'),
                    'year_end': platform.get('year_end')
                }
                transformed.append(transformed_platform)

            except Exception as e:
                logger.warning(f"Error transforming platform {platform.get('id')}: {e}")
                continue

        logger.info(f"Successfully transformed {len(transformed)} platforms")
        return transformed

    @staticmethod
    def transform_developers(raw_developers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform developer data.

        Args:
            raw_developers: List of raw developer dictionaries

        Returns:
            List of transformed developer dictionaries
        """
        logger.info(f"Transforming {len(raw_developers)} developers")
        transformed = []

        for dev in raw_developers:
            try:
                transformed_dev = {
                    'developer_id': dev['id'],
                    'developer_name': dev['name'],
                    'slug': dev.get('slug'),
                    'games_count': dev.get('games_count', 0),
                    'image_background': dev.get('image_background')
                }
                transformed.append(transformed_dev)

            except Exception as e:
                logger.warning(f"Error transforming developer {dev.get('id')}: {e}")
                continue

        logger.info(f"Successfully transformed {len(transformed)} developers")
        return transformed

    @staticmethod
    def transform_publishers(raw_publishers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform publisher data.

        Args:
            raw_publishers: List of raw publisher dictionaries

        Returns:
            List of transformed publisher dictionaries
        """
        logger.info(f"Transforming {len(raw_publishers)} publishers")
        transformed = []

        for pub in raw_publishers:
            try:
                transformed_pub = {
                    'publisher_id': pub['id'],
                    'publisher_name': pub['name'],
                    'slug': pub.get('slug'),
                    'games_count': pub.get('games_count', 0),
                    'image_background': pub.get('image_background')
                }
                transformed.append(transformed_pub)

            except Exception as e:
                logger.warning(f"Error transforming publisher {pub.get('id')}: {e}")
                continue

        logger.info(f"Successfully transformed {len(transformed)} publishers")
        return transformed

    @staticmethod
    def create_game_genre_bridge(raw_games: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Create bridge table for many-to-many game-genre relationship.

        Uses set for deduplication to avoid duplicate relationships.
        Memory-efficient list comprehension alternative available for simple cases.

        Args:
            raw_games: List of raw game dictionaries

        Returns:
            List of game_id-genre_id pairs
        """
        if not raw_games:
            logger.warning("No games provided for bridge table creation")
            return []

        logger.info("Creating game-genre bridge table")
        bridge_records: List[Dict[str, Any]] = []
        seen_pairs: Set[tuple[int, int]] = set()  # Deduplication set

        for game in raw_games:
            try:
                game_id = game.get('id')
                if not game_id:
                    continue

                genres_list = game.get('genres', [])
                if not isinstance(genres_list, list):
                    continue

                for genre in genres_list:
                    if not isinstance(genre, dict):
                        continue

                    genre_id = genre.get('id')
                    if not genre_id:
                        continue

                    # Use tuple for deduplication check
                    pair = (game_id, genre_id)
                    if pair not in seen_pairs:
                        seen_pairs.add(pair)
                        bridge_records.append({
                            'game_id': game_id,
                            'genre_id': genre_id
                        })

            except Exception as e:
                logger.debug(f"Error processing game-genre bridge for game {game.get('id', 'unknown')}: {e}")
                continue

        logger.info(f"Created {len(bridge_records)} unique game-genre relationships")
        return bridge_records

    @staticmethod
    def validate_data_quality(
        data: List[Dict[str, Any]],
        required_fields: List[str],
        threshold: float = 90.0
    ) -> bool:
        """
        Validate data quality by checking required fields.

        Uses efficient iteration to count invalid records and provides
        detailed logging for debugging data quality issues.

        Args:
            data: List of dictionaries to validate
            required_fields: List of required field names
            threshold: Minimum validation rate percentage (default: 90.0)

        Returns:
            True if validation passes threshold

        Raises:
            ValueError: If threshold is not between 0 and 100
        """
        if not 0 <= threshold <= 100:
            raise ValueError(f"Threshold must be between 0 and 100, got {threshold}")

        if not data:
            logger.warning("Empty dataset provided for validation")
            return False

        if not required_fields:
            logger.warning("No required fields specified for validation")
            return True

        invalid_count = 0
        sample_issues: List[str] = []  # Track first few issues for logging

        for idx, record in enumerate(data):
            # Use generator expression for memory efficiency
            missing_fields = [
                field for field in required_fields
                if field not in record or record[field] is None
            ]

            if missing_fields:
                invalid_count += 1
                # Log first 5 issues for debugging
                if len(sample_issues) < 5:
                    sample_issues.append(
                        f"Record {idx}: missing {missing_fields}"
                    )

        validation_rate = ((len(data) - invalid_count) / len(data)) * 100

        logger.info(
            f"Data quality: {validation_rate:.2f}% valid records "
            f"({len(data) - invalid_count}/{len(data)} passed, {invalid_count} invalid)"
        )

        if sample_issues:
            logger.debug(f"Sample validation issues: {sample_issues}")

        passed = validation_rate >= threshold

        if not passed:
            logger.warning(
                f"Data quality check failed: {validation_rate:.2f}% < {threshold}% threshold"
            )

        return passed
