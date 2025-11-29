"""
RAWG API Client with rate limiting and error handling.
"""
import time
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


logger = logging.getLogger(__name__)


class RAWGAPIError(Exception):
    """Base exception for RAWG API errors."""
    pass


class RAWGRateLimitError(RAWGAPIError):
    """Raised when rate limit is exceeded."""
    pass


class RAWGClient:
    """Client for interacting with RAWG Video Games Database API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.rawg.io/api",
        rate_limit: float = 3.0,  # requests per second
        timeout: int = 30
    ):
        """
        Initialize RAWG API client.

        Args:
            api_key: RAWG API key
            base_url: Base URL for API endpoints
            rate_limit: Maximum requests per second
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.rate_limit = rate_limit
        self.timeout = timeout
        self.last_request_time: float = 0.0

        # Setup session with retry strategy and connection pooling
        self.session = self._create_session()
        logger.info(f"RAWGClient initialized with rate_limit={rate_limit} req/s")

    def _create_session(self) -> requests.Session:
        """
        Create requests session with retry logic and connection pooling.

        Connection pooling improves performance by reusing TCP connections.
        Retry strategy handles transient failures automatically.
        """
        session = requests.Session()

        retry_strategy = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            raise_on_status=False  # Let us handle status codes
        )

        # Connection pooling: pool_connections=10, pool_maxsize=20
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20,
            pool_block=False
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _rate_limit_wait(self) -> None:
        """
        Enforce rate limiting between requests.

        Implements a simple token bucket algorithm to ensure we don't
        exceed the configured rate limit.
        """
        if self.rate_limit <= 0:
            return

        min_interval = 1.0 / self.rate_limit
        elapsed = time.time() - self.last_request_time

        if elapsed < min_interval:
            sleep_time = min_interval - elapsed
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to RAWG API.

        Args:
            endpoint: API endpoint (e.g., '/games')
            params: Query parameters

        Returns:
            JSON response as dictionary

        Raises:
            requests.exceptions.RequestException: On request failure
        """
        self._rate_limit_wait()

        url = f"{self.base_url}{endpoint}"
        params = params or {}
        params['key'] = self.api_key

        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()

            logger.debug(f"Request successful: {endpoint}")
            return response.json()

        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                logger.error(f"Rate limit exceeded for {endpoint}: {e}")
                raise RAWGRateLimitError(f"Rate limit exceeded: {e}") from e
            logger.error(f"HTTP error {response.status_code} for {endpoint}: {e}")
            raise RAWGAPIError(f"HTTP {response.status_code}: {e}") from e
        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout for {endpoint}: {e}")
            raise RAWGAPIError(f"Request timeout: {e}") from e
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {endpoint}: {e}")
            raise RAWGAPIError(f"Request failed: {e}") from e

    def get_games(
        self,
        page: int = 1,
        page_size: int = 40,
        dates: Optional[str] = None,
        ordering: str = "-added",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Fetch games from RAWG API.

        Args:
            page: Page number (1-indexed)
            page_size: Number of results per page (max 40)
            dates: Date range filter (e.g., '2024-01-01,2024-12-31')
            ordering: Sort order (-added, -rating, -released)
            **kwargs: Additional query parameters

        Returns:
            API response with games list
        """
        params = {
            'page': page,
            'page_size': min(page_size, 40),
            'ordering': ordering,
            **kwargs
        }

        if dates:
            params['dates'] = dates

        return self._make_request('/games', params)

    def get_game_details(self, game_id: int) -> Dict[str, Any]:
        """
        Fetch detailed information for a specific game.

        Args:
            game_id: RAWG game ID

        Returns:
            Game details
        """
        return self._make_request(f'/games/{game_id}')

    def get_genres(self, page: int = 1) -> Dict[str, Any]:
        """
        Fetch list of game genres.

        Args:
            page: Page number

        Returns:
            Genres list
        """
        return self._make_request('/genres', {'page': page})

    def get_platforms(self, page: int = 1) -> Dict[str, Any]:
        """
        Fetch list of gaming platforms.

        Args:
            page: Page number

        Returns:
            Platforms list
        """
        return self._make_request('/platforms', {'page': page})

    def get_developers(self, page: int = 1) -> Dict[str, Any]:
        """
        Fetch list of game developers.

        Args:
            page: Page number

        Returns:
            Developers list
        """
        return self._make_request('/developers', {'page': page})

    def get_publishers(self, page: int = 1) -> Dict[str, Any]:
        """
        Fetch list of game publishers.

        Args:
            page: Page number

        Returns:
            Publishers list
        """
        return self._make_request('/publishers', {'page': page})

    def fetch_all_pages(
        self,
        fetch_method: Callable[..., Dict[str, Any]],
        max_pages: Optional[int] = None,
        **kwargs: Any
    ) -> List[Dict[str, Any]]:
        """
        Fetch all pages from a paginated endpoint.

        Uses memory-efficient iteration by extending results list in-place
        rather than creating intermediate collections.

        Args:
            fetch_method: Method to call (e.g., self.get_games)
            max_pages: Maximum number of pages to fetch
            **kwargs: Arguments to pass to fetch_method

        Returns:
            List of all results across pages

        Raises:
            RAWGAPIError: If API request fails
        """
        all_results: List[Dict[str, Any]] = []
        page = 1

        while True:
            if max_pages and page > max_pages:
                logger.info(f"Reached max_pages limit: {max_pages}")
                break

            try:
                response = fetch_method(page=page, **kwargs)
                results = response.get('results', [])

                if not results:
                    logger.info(f"No more results at page {page}")
                    break

                # Memory-efficient: extend in-place instead of concatenation
                all_results.extend(results)
                logger.info(f"Fetched page {page}, total results: {len(all_results)}")

                # Check if there's a next page
                if not response.get('next'):
                    logger.info("No next page available")
                    break

                page += 1

            except RAWGAPIError:
                # Re-raise API errors for proper handling upstream
                raise
            except Exception as e:
                logger.error(f"Unexpected error fetching page {page}: {e}", exc_info=True)
                raise RAWGAPIError(f"Failed to fetch page {page}") from e

        logger.info(f"Completed pagination: {len(all_results)} total results across {page} pages")
        return all_results
