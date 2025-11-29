# Developer Guide

## Overview

This guide provides instructions for developers who want to contribute to, extend, or customize the Video Game ETL Pipeline. It covers development environment setup, code structure, testing, and best practices.

## Development Environment Setup

### Prerequisites

- Python 3.11 or higher
- Git
- Docker Desktop
- Code editor (VSCode recommended)
- PostgreSQL client (optional, for debugging)

### Initial Setup

```bash
# 1. Clone the repository (if not already done)
cd C:\Users\sergi\Documents\proyectos
git clone <repository_url> video-game-etl
cd video-game-etl

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Install development dependencies
pip install -r requirements-dev.txt

# 6. Setup pre-commit hooks
pre-commit install

# 7. Create .env file from template
cp .env.example .env

# 8. Edit .env and add your RAWG API key
```

### VSCode Setup (Recommended)

**Install Extensions**:
- Python (Microsoft)
- Pylance
- Docker
- PostgreSQL (Chris Kolkman)
- GitLens

**Settings** (`.vscode/settings.json`):
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"],
  "editor.formatOnSave": true,
  "editor.rulers": [88],
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true
  }
}
```

**Launch Configuration** (`.vscode/launch.json`):
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Current File",
      "type": "python",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal",
      "envFile": "${workspaceFolder}/.env"
    },
    {
      "name": "Python: Run Tests",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": ["tests/", "-v"],
      "console": "integratedTerminal"
    }
  ]
}
```

## Project Structure

```
video-game-etl/
├── dags/
│   └── video_game_etl.py          # Airflow DAG definition
│
├── src/                            # Source code
│   ├── api/                        # API client layer
│   │   ├── __init__.py
│   │   └── rawg_client.py          # RAWG API client with rate limiting
│   │
│   ├── etl/                        # ETL layer
│   │   ├── __init__.py
│   │   ├── extract.py              # Data extraction logic
│   │   ├── transform.py            # Data transformation logic
│   │   └── load.py                 # Data loading logic
│   │
│   └── utils/                      # Shared utilities
│       ├── __init__.py
│       ├── db_utils.py             # Database utilities
│       └── logging_config.py       # Logging configuration
│
├── sql/                            # SQL scripts
│   ├── ddl/
│   │   └── schema.sql              # Table definitions
│   └── dml/
│       └── quality_checks.sql      # Data quality queries
│
├── tests/                          # Test suite
│   ├── __init__.py
│   ├── test_api_client.py          # API client tests
│   ├── test_transformations.py     # Transformation tests
│   └── test_data_quality.py        # Data quality tests
│
├── scripts/                        # Utility scripts
│   └── init_db.py                  # Database initialization
│
├── docs/                           # Documentation
│   ├── API_INTEGRATION.md
│   ├── ARCHITECTURE.md
│   ├── DATA_DICTIONARY.md
│   ├── OPERATIONS.md
│   ├── DEVELOPER_GUIDE.md
│   └── SETUP.md
│
├── logs/                           # Airflow logs (gitignored)
├── plugins/                        # Airflow plugins (empty)
├── config/                         # Configuration files
│
├── .env                            # Environment variables (gitignored)
├── .env.example                    # Environment template
├── .gitignore                      # Git ignore rules
├── docker-compose.yml              # Docker services definition
├── requirements.txt                # Python dependencies
├── requirements-dev.txt            # Development dependencies
└── README.md                       # Project overview
```

### Module Responsibilities

| Module | Purpose | Key Classes/Functions |
|--------|---------|----------------------|
| `src.api.rawg_client` | RAWG API communication | `RAWGClient` |
| `src.etl.extract` | Data extraction | `GameDataExtractor` |
| `src.etl.transform` | Data transformation | `GameDataTransformer` |
| `src.etl.load` | Data loading | `GameDataLoader` |
| `src.utils.db_utils` | Database operations | `DatabaseManager` |
| `src.utils.logging_config` | Logging setup | `setup_logging()` |

## Code Style Guidelines

### PEP 8 Compliance

This project follows [PEP 8](https://pep8.org/) style guidelines:

- **Line length**: 88 characters (Black default)
- **Indentation**: 4 spaces
- **Naming conventions**:
  - Functions/variables: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPER_SNAKE_CASE`
  - Private: `_leading_underscore`

**Automated Formatting**:
```bash
# Format all code with Black
black src/ tests/ scripts/

# Check without modifying
black --check src/

# Format specific file
black src/etl/extract.py
```

### Type Hints

All functions must include **type hints** for parameters and return values:

```python
from typing import List, Dict, Any, Optional

def transform_games(raw_games: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Transform raw game data to normalized format.

    Args:
        raw_games: List of raw game dictionaries from API

    Returns:
        List of transformed game dictionaries

    Raises:
        TransformationError: If critical transformation fails
    """
    # Implementation
    pass
```

**Type Checking**:
```bash
# Run mypy type checker
mypy src/

# Check specific module
mypy src/etl/transform.py
```

### Docstrings

Use **Google-style docstrings** for all public functions and classes:

```python
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

    Example:
        >>> client = RAWGClient(api_key="key")
        >>> genres = client.fetch_all_pages(client.get_genres)
    """
    # Implementation
```

### Linting

**Flake8** configuration (`.flake8`):
```ini
[flake8]
max-line-length = 88
extend-ignore = E203, W503
exclude = .git,__pycache__,venv,logs,plugins
```

**Run Linter**:
```bash
# Check all code
flake8 src/ tests/

# Check specific file
flake8 src/etl/extract.py
```

## Adding New Features

### Adding a New Data Source

**Example**: Adding Steam API as a secondary source

**Step 1**: Create API client
```python
# src/api/steam_client.py
import logging
from typing import Dict, List, Any
import requests

logger = logging.getLogger(__name__)

class SteamAPIClient:
    """Client for Steam Web API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.steampowered.com"

    def get_app_details(self, app_id: int) -> Dict[str, Any]:
        """Fetch details for a Steam app."""
        url = f"{self.base_url}/appdetails"
        params = {"appids": app_id}
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
```

**Step 2**: Update `__init__.py`
```python
# src/api/__init__.py
from .rawg_client import RAWGClient, RAWGAPIError, RAWGRateLimitError
from .steam_client import SteamAPIClient  # Add this

__all__ = [
    'RAWGClient',
    'RAWGAPIError',
    'RAWGRateLimitError',
    'SteamAPIClient',  # Add this
]
```

**Step 3**: Create extractor
```python
# src/etl/extract.py - Add new method
def extract_steam_games(self, app_ids: List[int]) -> List[Dict[str, Any]]:
    """Extract game data from Steam API."""
    from src.api import SteamAPIClient

    steam_client = SteamAPIClient(api_key=os.getenv('STEAM_API_KEY'))
    games = []

    for app_id in app_ids:
        try:
            details = steam_client.get_app_details(app_id)
            games.append(details)
        except Exception as e:
            logger.warning(f"Failed to fetch Steam app {app_id}: {e}")
            continue

    return games
```

**Step 4**: Add transformation logic
```python
# src/etl/transform.py - Add new method
@staticmethod
def transform_steam_games(raw_steam_games: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Transform Steam game data to warehouse format."""
    transformed = []

    for game in raw_steam_games:
        # Map Steam fields to warehouse schema
        transformed_game = {
            'game_id': game['steam_appid'],
            'name': game['name'],
            # ... other mappings
        }
        transformed.append(transformed_game)

    return transformed
```

**Step 5**: Update DAG
```python
# dags/video_game_etl.py - Modify extract_data function
def extract_data(**context):
    extractor = GameDataExtractor()

    # Existing RAWG extraction
    rawg_data = extractor.extract_incremental(lookback_days=7)

    # New Steam extraction
    steam_app_ids = [440, 730, 570]  # Example: TF2, CS:GO, Dota 2
    steam_data = extractor.extract_steam_games(steam_app_ids)

    # Combine data
    context['ti'].xcom_push(key='rawg_data', value=rawg_data)
    context['ti'].xcom_push(key='steam_data', value=steam_data)
```

**Step 6**: Write tests
```python
# tests/test_steam_client.py
import pytest
from src.api import SteamAPIClient

def test_steam_client_get_app_details():
    """Test fetching Steam app details."""
    client = SteamAPIClient(api_key="test_key")
    # Mock response, assert behavior
```

### Adding a New Transformation

**Example**: Calculate derived metric (rating * playtime)

**Step 1**: Add transformation method
```python
# src/etl/transform.py
@staticmethod
def calculate_engagement_score(raw_games: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Calculate engagement score as rating * playtime.

    Higher score indicates games that are both highly rated and played extensively.

    Args:
        raw_games: List of raw game dictionaries

    Returns:
        List of games with engagement_score added
    """
    for game in raw_games:
        rating = game.get('rating', 0.0)
        playtime = game.get('playtime', 0)
        game['engagement_score'] = rating * playtime

    return raw_games
```

**Step 2**: Add database column
```sql
-- sql/ddl/schema.sql
ALTER TABLE fact_game_metrics ADD COLUMN engagement_score DECIMAL(10,2);
```

**Step 3**: Update loader
```python
# src/etl/load.py - Update load_fact_metrics
update_columns=['released', 'rating', ..., 'engagement_score']
```

**Step 4**: Update DAG transformation task
```python
# dags/video_game_etl.py - In transform_data function
transformed_games = transformer.transform_games(raw_games)
transformed_games = transformer.calculate_engagement_score(transformed_games)
```

**Step 5**: Write tests
```python
# tests/test_transformations.py
def test_calculate_engagement_score():
    """Test engagement score calculation."""
    games = [
        {'rating': 4.5, 'playtime': 100},
        {'rating': 3.0, 'playtime': 50}
    ]

    result = GameDataTransformer.calculate_engagement_score(games)

    assert result[0]['engagement_score'] == 450.0
    assert result[1]['engagement_score'] == 150.0
```

## Testing

### Test Structure

Tests are organized by component:

```
tests/
├── test_api_client.py          # API client tests
├── test_transformations.py     # Transformation logic tests
├── test_data_quality.py        # Data validation tests
└── conftest.py                 # Shared fixtures
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run specific test file
pytest tests/test_api_client.py

# Run specific test function
pytest tests/test_api_client.py::test_rate_limiting

# Run with coverage
pytest --cov=src tests/

# Generate HTML coverage report
pytest --cov=src --cov-report=html tests/
# Open htmlcov/index.html in browser
```

### Writing Unit Tests

**Example**: Testing transformation logic

```python
# tests/test_transformations.py
import pytest
from src.etl.transform import GameDataTransformer

class TestGameTransformations:
    """Test suite for game transformations."""

    def test_transform_games_basic(self):
        """Test basic game transformation."""
        # Arrange
        raw_games = [
            {
                'id': 1,
                'name': 'Test Game',
                'slug': 'test-game',
                'developers': [{'id': 100, 'name': 'Dev Studio'}],
                'publishers': [{'id': 200, 'name': 'Publisher Inc'}],
                'esrb_rating': {'name': 'Mature'}
            }
        ]

        # Act
        transformer = GameDataTransformer()
        result = transformer.transform_games(raw_games)

        # Assert
        assert len(result) == 1
        assert result[0]['game_id'] == 1
        assert result[0]['name'] == 'Test Game'
        assert result[0]['developer_id'] == 100
        assert result[0]['publisher_id'] == 200
        assert result[0]['esrb_rating'] == 'Mature'

    def test_transform_games_missing_fields(self):
        """Test transformation handles missing fields gracefully."""
        # Arrange
        raw_games = [
            {
                'id': 2,
                'name': 'Minimal Game'
                # No developers, publishers, or esrb_rating
            }
        ]

        # Act
        result = GameDataTransformer().transform_games(raw_games)

        # Assert
        assert len(result) == 1
        assert result[0]['developer_id'] is None
        assert result[0]['publisher_id'] is None
        assert result[0]['esrb_rating'] is None

    def test_transform_games_empty_list(self):
        """Test transformation with empty input."""
        # Arrange
        raw_games = []

        # Act
        result = GameDataTransformer().transform_games(raw_games)

        # Assert
        assert result == []
```

### Writing Integration Tests

**Example**: Testing end-to-end extraction

```python
# tests/test_integration.py
import pytest
from src.etl.extract import GameDataExtractor
from unittest.mock import patch, Mock

class TestExtractionIntegration:
    """Integration tests for extraction pipeline."""

    @patch('src.api.rawg_client.RAWGClient.get_games')
    def test_extract_games_with_pagination(self, mock_get_games):
        """Test extraction handles pagination correctly."""
        # Arrange
        mock_get_games.side_effect = [
            {
                'results': [{'id': 1}, {'id': 2}],
                'next': 'page2_url'
            },
            {
                'results': [{'id': 3}, {'id': 4}],
                'next': None
            }
        ]

        extractor = GameDataExtractor(api_key='test_key')

        # Act
        games = extractor.extract_games(max_pages=2)

        # Assert
        assert len(games) == 4
        assert mock_get_games.call_count == 2
```

### Test Fixtures

**Shared fixtures** (`tests/conftest.py`):

```python
import pytest
from src.utils import DatabaseManager

@pytest.fixture
def sample_game():
    """Provide sample game data for tests."""
    return {
        'id': 3498,
        'name': 'Grand Theft Auto V',
        'slug': 'grand-theft-auto-v',
        'rating': 4.47,
        'released': '2013-09-17',
        'platforms': [
            {'platform': {'id': 4, 'name': 'PC'}},
            {'platform': {'id': 18, 'name': 'PlayStation 4'}}
        ],
        'genres': [
            {'id': 4, 'name': 'Action'},
            {'id': 6, 'name': 'Adventure'}
        ]
    }

@pytest.fixture
def db_manager():
    """Provide test database manager."""
    db = DatabaseManager(
        host='localhost',
        port=5432,
        database='gaming_analytics_test',
        user='test_user',
        password='test_password'
    )
    yield db
    db.close()
```

### Mocking External APIs

```python
import responses
from src.api import RAWGClient

@responses.activate
def test_api_client_rate_limiting():
    """Test API client respects rate limits."""
    # Mock API endpoint
    responses.add(
        responses.GET,
        'https://api.rawg.io/api/games',
        json={'results': [{'id': 1}], 'next': None},
        status=200
    )

    client = RAWGClient(api_key='test_key', rate_limit=2)

    # Make requests and measure timing
    import time
    start = time.time()
    client.get_games()
    client.get_games()
    elapsed = time.time() - start

    # Should take at least 0.5s (1/rate_limit)
    assert elapsed >= 0.5
```

## Debugging

### Debugging Airflow DAGs Locally

**Option 1**: Test individual tasks
```bash
# Test extract task
python -c "
import sys
sys.path.insert(0, '.')
from dags.video_game_etl import extract_data
context = {'task_instance': None}  # Mock context
result = extract_data(**context)
print(result)
"

# Or use Airflow CLI
docker exec -it airflow-scheduler airflow tasks test video_game_etl extract_data 2024-01-01
```

**Option 2**: Run full DAG locally (without Airflow)
```python
# scripts/debug_dag.py
import sys
import os
sys.path.insert(0, '.')

from dags.video_game_etl import extract_data, transform_data, load_data

# Mock context
class MockTaskInstance:
    def __init__(self):
        self.xcom_data = {}

    def xcom_push(self, key, value):
        self.xcom_data[key] = value

    def xcom_pull(self, task_ids, key):
        return self.xcom_data.get(key)

ti = MockTaskInstance()
context = {'task_instance': ti}

# Run pipeline
print("Running extract...")
extract_data(**context)

print("Running transform...")
transform_data(**context)

print("Running load...")
load_data(**context)

print("Done!")
```

### Using Python Debugger (pdb)

```python
# Add breakpoint in code
def transform_games(raw_games):
    import pdb; pdb.set_trace()  # Debugger will pause here

    # Your code
    transformed = []
    for game in raw_games:
        # ... transformation logic
        pass

    return transformed
```

**pdb Commands**:
- `n` - Next line
- `s` - Step into function
- `c` - Continue execution
- `p variable` - Print variable value
- `l` - List current code
- `q` - Quit debugger

### Logging for Debugging

```python
import logging
logger = logging.getLogger(__name__)

def my_function(data):
    logger.debug(f"Processing {len(data)} records")
    logger.info(f"Starting transformation")

    for item in data:
        logger.debug(f"Processing item {item['id']}")
        # ... logic

    logger.info(f"Transformation complete")
```

**Set log level**:
```bash
# In .env
LOG_LEVEL=DEBUG  # Show all logs including debug

# Or programmatically
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contribution Workflow

### Branch Strategy

```bash
# Create feature branch
git checkout -b feature/add-steam-integration

# Make changes, commit frequently
git add src/api/steam_client.py
git commit -m "feat: add Steam API client"

# Push to remote
git push origin feature/add-steam-integration

# Create pull request on GitHub
```

### Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Formatting, linting
- `refactor`: Code restructuring
- `test`: Adding/updating tests
- `chore`: Maintenance tasks

**Examples**:
```
feat(api): add Steam API client with rate limiting

Implements SteamAPIClient with similar interface to RAWGClient.
Includes connection pooling and retry logic.

Closes #123

---

fix(transform): handle missing esrb_rating gracefully

Previously threw KeyError when esrb_rating was null in API response.
Now defaults to None.

---

docs(readme): update installation instructions

Added troubleshooting section for Windows users.
```

### Pre-commit Hooks

Pre-commit hooks run automatically before each commit:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]
```

**Install hooks**:
```bash
pre-commit install

# Run manually
pre-commit run --all-files
```

## Code Review Checklist

Before submitting a PR, ensure:

- [ ] Code follows PEP 8 style guidelines
- [ ] All functions have type hints
- [ ] All functions have docstrings
- [ ] New features have tests (>80% coverage)
- [ ] Tests pass: `pytest tests/`
- [ ] Linting passes: `flake8 src/`
- [ ] Type checking passes: `mypy src/`
- [ ] Documentation updated (if needed)
- [ ] Commit messages follow conventions
- [ ] No secrets or credentials in code
- [ ] `.env` not committed

## Performance Profiling

### Profiling Python Code

```python
import cProfile
import pstats

# Profile a function
profiler = cProfile.Profile()
profiler.enable()

# Your code here
result = my_expensive_function()

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(10)  # Top 10 functions
```

### Memory Profiling

```bash
# Install memory profiler
pip install memory_profiler

# Add decorator to function
from memory_profiler import profile

@profile
def my_function():
    # Your code
    pass

# Run with profiling
python -m memory_profiler script.py
```

## Useful Development Tools

### Database GUI Tools

- **DBeaver**: Free, multi-database GUI
- **pgAdmin**: PostgreSQL-specific GUI
- **DataGrip**: JetBrains paid IDE

### API Testing Tools

- **Postman**: API testing and documentation
- **Insomnia**: Alternative to Postman
- **HTTPie**: Command-line HTTP client

### Docker Tools

- **Portainer**: Docker container management UI
- **Lazydocker**: Terminal UI for Docker

## Resources

- **Python Style Guide**: https://pep8.org/
- **Type Hints**: https://mypy.readthedocs.io/
- **pytest Documentation**: https://docs.pytest.org/
- **Airflow Best Practices**: https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html
- **SQL Style Guide**: https://www.sqlstyle.guide/

## Getting Help

- Check existing documentation in `docs/`
- Review code comments and docstrings
- Search GitHub issues
- Ask in team chat or create GitHub issue

## Next Steps

After setting up your development environment:

1. Read [ARCHITECTURE.md](ARCHITECTURE.md) to understand system design
2. Review [API_INTEGRATION.md](API_INTEGRATION.md) for API details
3. Explore the codebase, starting with `dags/video_game_etl.py`
4. Run tests to ensure everything works: `pytest tests/`
5. Try making a small change and see it in action

Happy coding!
