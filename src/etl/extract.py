"""
Data extraction module for fetching data from RAWG API.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

from src.api import RAWGClient, RAWGAPIError

load_dotenv()
logger = logging.getLogger(__name__)


class ExtractionError(Exception):
    """Base exception for extraction errors."""
    pass


class GameDataExtractor:
    """Extract game data from RAWG API."""

    def __init__(self, api_key: Optional[str] = None, rate_limit: Optional[float] = None):
        """
        Initialize extractor.

        Args:
            api_key: RAWG API key (uses env var if not provided)
            rate_limit: Request rate limit (uses env var if not provided)

        Raises:
            ValueError: If API key is not provided or found in environment
        """
        api_key = api_key or os.getenv('RAWG_API_KEY')
        if not api_key:
            raise ValueError("RAWG_API_KEY not found in environment")

        # Allow override of rate limit, otherwise use env var or default
        if rate_limit is None:
            rate_limit = float(os.getenv('RAWG_RATE_LIMIT', '3'))

        self.client = RAWGClient(api_key=api_key, rate_limit=rate_limit)
        logger.info(f"GameDataExtractor initialized with rate_limit={rate_limit}")

    def extract_games(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_pages: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract games within date range.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            max_pages: Maximum pages to fetch

        Returns:
            List of game dictionaries

        Raises:
            ExtractionError: If extraction fails
        """
        logger.info(f"Extracting games from {start_date} to {end_date}")

        # Build date filter
        dates_filter: Optional[str] = None
        if start_date and end_date:
            dates_filter = f"{start_date},{end_date}"
        elif start_date:
            dates_filter = f"{start_date},{datetime.now().strftime('%Y-%m-%d')}"

        try:
            games = self.client.fetch_all_pages(
                self.client.get_games,
                max_pages=max_pages,
                dates=dates_filter,
                ordering="-added"
            )

            logger.info(f"Extracted {len(games)} games")
            return games

        except RAWGAPIError as e:
            logger.error(f"API error extracting games: {e}", exc_info=True)
            raise ExtractionError(f"Failed to extract games: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error extracting games: {e}", exc_info=True)
            raise ExtractionError(f"Unexpected extraction error: {e}") from e

    def extract_game_details(
        self,
        game_ids: List[int],
        fail_fast: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Extract detailed information for specific games.

        Args:
            game_ids: List of RAWG game IDs
            fail_fast: If True, raise on first error; if False, skip failed games

        Returns:
            List of detailed game dictionaries

        Raises:
            ExtractionError: If fail_fast=True and any game fails
        """
        if not game_ids:
            logger.warning("No game IDs provided for detail extraction")
            return []

        logger.info(f"Extracting details for {len(game_ids)} games")
        detailed_games: List[Dict[str, Any]] = []
        failed_ids: List[int] = []

        for game_id in game_ids:
            try:
                details = self.client.get_game_details(game_id)
                detailed_games.append(details)
            except RAWGAPIError as e:
                failed_ids.append(game_id)
                logger.warning(f"Failed to fetch details for game {game_id}: {e}")
                if fail_fast:
                    raise ExtractionError(f"Failed to extract game {game_id}") from e
                continue
            except Exception as e:
                failed_ids.append(game_id)
                logger.warning(f"Unexpected error for game {game_id}: {e}")
                if fail_fast:
                    raise ExtractionError(f"Unexpected error for game {game_id}") from e
                continue

        success_rate = (len(detailed_games) / len(game_ids)) * 100 if game_ids else 0
        logger.info(
            f"Successfully extracted {len(detailed_games)}/{len(game_ids)} game details "
            f"({success_rate:.1f}% success rate)"
        )

        if failed_ids:
            logger.warning(f"Failed to extract {len(failed_ids)} games: {failed_ids[:10]}...")

        return detailed_games

    def extract_genres(self) -> List[Dict[str, Any]]:
        """
        Extract all genres.

        Returns:
            List of genre dictionaries

        Raises:
            ExtractionError: If extraction fails
        """
        logger.info("Extracting genres")

        try:
            genres = self.client.fetch_all_pages(self.client.get_genres)
            logger.info(f"Extracted {len(genres)} genres")
            return genres
        except RAWGAPIError as e:
            logger.error(f"API error extracting genres: {e}", exc_info=True)
            raise ExtractionError(f"Failed to extract genres: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error extracting genres: {e}", exc_info=True)
            raise ExtractionError(f"Unexpected extraction error: {e}") from e

    def extract_platforms(self) -> List[Dict[str, Any]]:
        """
        Extract all platforms.

        Returns:
            List of platform dictionaries

        Raises:
            ExtractionError: If extraction fails
        """
        logger.info("Extracting platforms")

        try:
            platforms = self.client.fetch_all_pages(self.client.get_platforms)
            logger.info(f"Extracted {len(platforms)} platforms")
            return platforms
        except RAWGAPIError as e:
            logger.error(f"API error extracting platforms: {e}", exc_info=True)
            raise ExtractionError(f"Failed to extract platforms: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error extracting platforms: {e}", exc_info=True)
            raise ExtractionError(f"Unexpected extraction error: {e}") from e

    def extract_developers(self, max_pages: Optional[int] = 10) -> List[Dict[str, Any]]:
        """
        Extract developers.

        Args:
            max_pages: Maximum pages to fetch (None for all pages)

        Returns:
            List of developer dictionaries

        Raises:
            ExtractionError: If extraction fails
        """
        logger.info("Extracting developers")

        try:
            developers = self.client.fetch_all_pages(
                self.client.get_developers,
                max_pages=max_pages
            )
            logger.info(f"Extracted {len(developers)} developers")
            return developers
        except RAWGAPIError as e:
            logger.error(f"API error extracting developers: {e}", exc_info=True)
            raise ExtractionError(f"Failed to extract developers: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error extracting developers: {e}", exc_info=True)
            raise ExtractionError(f"Unexpected extraction error: {e}") from e

    def extract_publishers(self, max_pages: Optional[int] = 10) -> List[Dict[str, Any]]:
        """
        Extract publishers.

        Args:
            max_pages: Maximum pages to fetch (None for all pages)

        Returns:
            List of publisher dictionaries

        Raises:
            ExtractionError: If extraction fails
        """
        logger.info("Extracting publishers")

        try:
            publishers = self.client.fetch_all_pages(
                self.client.get_publishers,
                max_pages=max_pages
            )
            logger.info(f"Extracted {len(publishers)} publishers")
            return publishers
        except RAWGAPIError as e:
            logger.error(f"API error extracting publishers: {e}", exc_info=True)
            raise ExtractionError(f"Failed to extract publishers: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error extracting publishers: {e}", exc_info=True)
            raise ExtractionError(f"Unexpected extraction error: {e}") from e

    def extract_incremental(
        self,
        lookback_days: int = 7
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract data incrementally (last N days).

        This is the primary method for incremental ETL runs. It extracts:
        - Games updated/added in the last N days
        - All genres (typically small dataset)
        - All platforms (typically small dataset)
        - Recent developers and publishers

        Args:
            lookback_days: Number of days to look back (default: 7)

        Returns:
            Dictionary with all extracted data

        Raises:
            ExtractionError: If any extraction step fails
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)

        logger.info(f"Incremental extraction: last {lookback_days} days")

        try:
            # Extract all data - genres and platforms are typically small
            data: Dict[str, List[Dict[str, Any]]] = {
                'games': self.extract_games(
                    start_date=start_date.strftime('%Y-%m-%d'),
                    end_date=end_date.strftime('%Y-%m-%d'),
                    max_pages=None  # Fetch all pages for complete coverage
                ),
                'genres': self.extract_genres(),
                'platforms': self.extract_platforms(),
                'developers': self.extract_developers(max_pages=10),
                'publishers': self.extract_publishers(max_pages=10)
            }

            logger.info(
                f"Incremental extraction complete: "
                f"{len(data['games'])} games, "
                f"{len(data['genres'])} genres, "
                f"{len(data['platforms'])} platforms, "
                f"{len(data['developers'])} developers, "
                f"{len(data['publishers'])} publishers"
            )

            return data

        except ExtractionError:
            # Re-raise extraction errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error in incremental extraction: {e}", exc_info=True)
            raise ExtractionError(f"Incremental extraction failed: {e}") from e
