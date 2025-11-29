# API Integration Guide

## Overview

This document describes the integration with the RAWG Video Games Database API, including endpoint details, request/response patterns, rate limiting, and error handling strategies.

## RAWG API Overview

RAWG is a comprehensive video game database with over 500,000 games across 50+ platforms. The API provides free access with generous rate limits suitable for portfolio and research projects.

**Base URL**: `https://api.rawg.io/api`

**Authentication**: API Key (passed as query parameter)

**Documentation**: https://rawg.io/apidocs

## Getting an API Key

1. Visit https://rawg.io/apidocs
2. Sign up for a free account
3. Navigate to your profile to generate an API key
4. Free tier includes:
   - 20,000 requests per day
   - No credit card required
   - Full access to all endpoints

## Rate Limiting

### Official Limits

- **Daily limit**: 20,000 requests per day
- **Recommended rate**: 3 requests per second (configured in `.env`)
- **Rate limit headers**: Not provided by API

### Implementation

Our client implements **client-side rate limiting** using a token bucket algorithm:

```python
# From src/api/rawg_client.py
def _rate_limit_wait(self) -> None:
    """Enforce rate limiting between requests."""
    if self.rate_limit <= 0:
        return

    min_interval = 1.0 / self.rate_limit  # 333ms for 3 req/sec
    elapsed = time.time() - self.last_request_time

    if elapsed < min_interval:
        sleep_time = min_interval - elapsed
        time.sleep(sleep_time)

    self.last_request_time = time.time()
```

**Configuration**:
```env
RAWG_RATE_LIMIT=3  # requests per second
```

### Retry Strategy

The client uses `urllib3.Retry` with exponential backoff:

- **Total retries**: 5
- **Backoff factor**: 1 (1s, 2s, 4s, 8s, 16s)
- **Status codes retried**: 429, 500, 502, 503, 504
- **Methods**: GET only

```python
retry_strategy = Retry(
    total=5,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
    raise_on_status=False
)
```

## Endpoints Used

### 1. Games List

**Endpoint**: `GET /games`

**Purpose**: Fetch paginated list of games with filtering

**Query Parameters**:
| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `key` | string | API key (required) | `your_api_key` |
| `page` | integer | Page number (1-indexed) | `1` |
| `page_size` | integer | Results per page (max 40) | `40` |
| `dates` | string | Date range filter | `2024-01-01,2024-12-31` |
| `ordering` | string | Sort order | `-added`, `-rating`, `-released` |

**Example Request**:
```bash
curl "https://api.rawg.io/api/games?key=YOUR_KEY&page=1&page_size=40&dates=2024-01-01,2024-12-31&ordering=-added"
```

**Example Response**:
```json
{
  "count": 500000,
  "next": "https://api.rawg.io/api/games?page=2",
  "previous": null,
  "results": [
    {
      "id": 3498,
      "slug": "grand-theft-auto-v",
      "name": "Grand Theft Auto V",
      "released": "2013-09-17",
      "rating": 4.47,
      "rating_top": 5,
      "ratings_count": 6500,
      "reviews_count": 1200,
      "metacritic": 96,
      "playtime": 74,
      "added": 18500,
      "suggestions_count": 420,
      "background_image": "https://media.rawg.io/media/games/456/456dea5e1c7e3cd07060c14e96612001.jpg",
      "platforms": [
        {
          "platform": {
            "id": 4,
            "name": "PC",
            "slug": "pc"
          }
        },
        {
          "platform": {
            "id": 1,
            "name": "Xbox One",
            "slug": "xbox-one"
          }
        }
      ],
      "genres": [
        {
          "id": 4,
          "name": "Action",
          "slug": "action"
        }
      ],
      "developers": [
        {
          "id": 3524,
          "name": "Rockstar North",
          "slug": "rockstar-north"
        }
      ],
      "publishers": [
        {
          "id": 2155,
          "name": "Rockstar Games",
          "slug": "rockstar-games"
        }
      ],
      "esrb_rating": {
        "id": 4,
        "name": "Mature"
      }
    }
  ]
}
```

**Response Fields**:
- `count`: Total number of games matching filter
- `next`: URL for next page (null if last page)
- `previous`: URL for previous page (null if first page)
- `results`: Array of game objects

### 2. Game Details

**Endpoint**: `GET /games/{id}`

**Purpose**: Fetch detailed information for a specific game

**Path Parameters**:
- `id` (integer): RAWG game ID

**Example Request**:
```bash
curl "https://api.rawg.io/api/games/3498?key=YOUR_KEY"
```

**Example Response**:
```json
{
  "id": 3498,
  "name": "Grand Theft Auto V",
  "description_raw": "Rockstar Games went bigger, since their previous installment...",
  "website": "http://www.rockstargames.com/V/",
  "released": "2013-09-17",
  "background_image": "https://media.rawg.io/media/games/456/456dea5e1c7e3cd07060c14e96612001.jpg",
  "rating": 4.47,
  "metacritic": 96,
  "playtime": 74,
  "esrb_rating": {
    "id": 4,
    "name": "Mature",
    "slug": "mature"
  }
}
```

### 3. Genres

**Endpoint**: `GET /genres`

**Purpose**: Fetch list of all game genres

**Example Request**:
```bash
curl "https://api.rawg.io/api/genres?key=YOUR_KEY"
```

**Example Response**:
```json
{
  "count": 19,
  "results": [
    {
      "id": 4,
      "name": "Action",
      "slug": "action",
      "games_count": 176537,
      "image_background": "https://media.rawg.io/media/games/..."
    },
    {
      "id": 51,
      "name": "Indie",
      "slug": "indie",
      "games_count": 57232
    }
  ]
}
```

### 4. Platforms

**Endpoint**: `GET /platforms`

**Purpose**: Fetch list of gaming platforms

**Example Request**:
```bash
curl "https://api.rawg.io/api/platforms?key=YOUR_KEY"
```

**Example Response**:
```json
{
  "count": 50,
  "results": [
    {
      "id": 4,
      "name": "PC",
      "slug": "pc",
      "games_count": 452000,
      "year_start": null,
      "year_end": null,
      "image_background": "https://media.rawg.io/media/..."
    },
    {
      "id": 18,
      "name": "PlayStation 4",
      "slug": "playstation4",
      "games_count": 6544,
      "year_start": 2013,
      "year_end": null
    }
  ]
}
```

### 5. Developers

**Endpoint**: `GET /developers`

**Purpose**: Fetch list of game developers

**Example Request**:
```bash
curl "https://api.rawg.io/api/developers?key=YOUR_KEY&page=1"
```

**Example Response**:
```json
{
  "count": 35000,
  "results": [
    {
      "id": 3524,
      "name": "Rockstar North",
      "slug": "rockstar-north",
      "games_count": 29,
      "image_background": "https://media.rawg.io/media/..."
    }
  ]
}
```

### 6. Publishers

**Endpoint**: `GET /publishers`

**Purpose**: Fetch list of game publishers

**Example Request**:
```bash
curl "https://api.rawg.io/api/publishers?key=YOUR_KEY&page=1"
```

**Example Response**:
```json
{
  "count": 25000,
  "results": [
    {
      "id": 2155,
      "name": "Rockstar Games",
      "slug": "rockstar-games",
      "games_count": 85,
      "image_background": "https://media.rawg.io/media/..."
    }
  ]
}
```

## Pagination Strategy

All list endpoints use **cursor-based pagination** with page numbers.

### Implementation

```python
# From src/api/rawg_client.py
def fetch_all_pages(
    self,
    fetch_method: Callable[..., Dict[str, Any]],
    max_pages: Optional[int] = None,
    **kwargs: Any
) -> List[Dict[str, Any]]:
    """Fetch all pages from a paginated endpoint."""
    all_results: List[Dict[str, Any]] = []
    page = 1

    while True:
        if max_pages and page > max_pages:
            break

        response = fetch_method(page=page, **kwargs)
        results = response.get('results', [])

        if not results:
            break

        all_results.extend(results)

        # Check if there's a next page
        if not response.get('next'):
            break

        page += 1

    return all_results
```

### Pagination Best Practices

1. **Check `next` field**: Always check if `response['next']` is null before continuing
2. **Page size**: Use maximum page size (40) to minimize requests
3. **Early termination**: Use `max_pages` parameter to limit pagination in development
4. **Memory efficiency**: Use `extend()` instead of list concatenation

## Error Handling

### HTTP Status Codes

| Code | Meaning | Action | Example |
|------|---------|--------|---------|
| 200 | Success | Return data | Normal response |
| 400 | Bad Request | Log and raise error | Invalid date format |
| 401 | Unauthorized | Check API key | Missing/invalid key |
| 404 | Not Found | Skip resource | Game ID doesn't exist |
| 429 | Rate Limit Exceeded | Retry with backoff | Too many requests |
| 500 | Server Error | Retry with backoff | RAWG server issue |
| 503 | Service Unavailable | Retry with backoff | Temporary outage |

### Error Response Format

```json
{
  "detail": "Invalid page.",
  "error": "not_found"
}
```

### Implementation

```python
# From src/api/rawg_client.py
def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Make HTTP request with comprehensive error handling."""
    try:
        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.HTTPError as e:
        if response.status_code == 429:
            raise RAWGRateLimitError(f"Rate limit exceeded: {e}") from e
        raise RAWGAPIError(f"HTTP {response.status_code}: {e}") from e

    except requests.exceptions.Timeout as e:
        raise RAWGAPIError(f"Request timeout: {e}") from e

    except requests.exceptions.RequestException as e:
        raise RAWGAPIError(f"Request failed: {e}") from e
```

### Common Error Scenarios

#### 1. Rate Limit Exceeded (429)

**Symptom**: `RAWGRateLimitError: Rate limit exceeded`

**Causes**:
- Exceeded 20,000 daily requests
- Too many concurrent requests
- Client-side rate limiter disabled

**Solutions**:
```python
# Reduce rate limit in .env
RAWG_RATE_LIMIT=2  # Slower but safer

# Add delays between batches
time.sleep(60)  # Wait 1 minute between large batches
```

#### 2. Server Error (500)

**Symptom**: `RAWGAPIError: HTTP 500: Internal Server Error`

**Causes**:
- RAWG server issues
- Malformed request
- API endpoint down

**Solutions**:
- Retry automatically (already implemented)
- Check RAWG status page
- Verify request parameters

#### 3. Timeout

**Symptom**: `RAWGAPIError: Request timeout`

**Causes**:
- Slow network connection
- Large response payload
- Server overload

**Solutions**:
```python
# Increase timeout in client initialization
client = RAWGClient(api_key=key, timeout=60)  # 60 seconds
```

#### 4. Invalid Date Range

**Symptom**: `400 Bad Request` with date-related error

**Causes**:
- Incorrect date format
- End date before start date
- Future dates

**Solutions**:
```python
# Use ISO format: YYYY-MM-DD
dates = "2024-01-01,2024-12-31"  # Correct
dates = "01/01/2024,12/31/2024"  # Wrong
```

## Connection Pooling

The client uses **connection pooling** for optimal performance:

```python
# From src/api/rawg_client.py
adapter = HTTPAdapter(
    max_retries=retry_strategy,
    pool_connections=10,    # Pools for different hosts
    pool_maxsize=20,        # Max connections per pool
    pool_block=False        # Don't block on pool exhaustion
)
session.mount("https://", adapter)
```

**Benefits**:
- Reuses TCP connections
- Reduces latency (no handshake overhead)
- Handles concurrent requests efficiently

## Data Quality Considerations

### Missing Fields

Many API fields are **optional** and may be `null`:

```python
# Safe field extraction
developer_id = None
developers = game.get('developers', [])
if developers and isinstance(developers, list):
    developer_id = developers[0].get('id')
```

### Data Inconsistencies

1. **Empty arrays**: `genres`, `platforms`, `developers` may be `[]`
2. **Null values**: `released`, `metacritic`, `website` often null
3. **Date formats**: Always ISO 8601 (`YYYY-MM-DD`)
4. **Rating ranges**: `rating` is 0.0-5.0, `metacritic` is 0-100

## Testing the API

### Using cURL

```bash
# Test API key
curl "https://api.rawg.io/api/games?key=YOUR_KEY&page_size=1"

# Test date filtering
curl "https://api.rawg.io/api/games?key=YOUR_KEY&dates=2024-01-01,2024-01-31&page_size=5"

# Test specific game
curl "https://api.rawg.io/api/games/3498?key=YOUR_KEY"
```

### Using Python

```python
from src.api import RAWGClient

# Initialize client
client = RAWGClient(api_key="your_key_here", rate_limit=3)

# Fetch games
games = client.get_games(page=1, page_size=10)
print(f"Found {games['count']} games")

# Fetch all genres
genres = client.fetch_all_pages(client.get_genres)
print(f"Fetched {len(genres)} genres")
```

## Performance Tips

1. **Batch requests**: Fetch maximum page size (40) to minimize requests
2. **Parallel requests**: For independent data (genres + platforms), fetch in parallel
3. **Cache dimensions**: Genres/platforms rarely change - cache locally
4. **Incremental updates**: Use `dates` parameter to fetch only recent games
5. **Monitor usage**: Track daily request count to avoid limit

## API Limits Summary

| Metric | Limit | Configured |
|--------|-------|------------|
| Daily requests | 20,000 | N/A |
| Requests per second | No official limit | 3 (client-side) |
| Page size | 40 max | 40 |
| Timeout | No official limit | 30s |
| Concurrent requests | Unlimited | 10-20 (pool) |

## Related Files

- `src/api/rawg_client.py` - API client implementation
- `src/etl/extract.py` - Data extraction using client
- `.env.example` - API configuration template
- `tests/test_api_client.py` - API client tests
