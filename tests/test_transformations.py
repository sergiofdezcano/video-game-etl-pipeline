"""
Unit tests for data transformations.
"""
import pytest
from src.etl import GameDataTransformer


@pytest.fixture
def sample_game_data():
    """Sample game data for testing."""
    return [
        {
            'id': 1,
            'name': 'Test Game',
            'slug': 'test-game',
            'released': '2024-01-15',
            'rating': 4.5,
            'metacritic': 85,
            'platforms': [
                {'platform': {'id': 4, 'name': 'PC'}},
                {'platform': {'id': 18, 'name': 'PS4'}}
            ],
            'genres': [
                {'id': 4, 'name': 'Action'},
                {'id': 51, 'name': 'Indie'}
            ],
            'developers': [
                {'id': 1, 'name': 'Test Studio'}
            ],
            'publishers': [
                {'id': 2, 'name': 'Test Publisher'}
            ],
            'ratings_count': 1000,
            'reviews_count': 50,
            'playtime': 10,
            'added': 5000
        }
    ]


def test_transform_games(sample_game_data):
    """Test game transformation."""
    transformer = GameDataTransformer()
    result = transformer.transform_games(sample_game_data)

    assert len(result) == 1
    assert result[0]['game_id'] == 1
    assert result[0]['name'] == 'Test Game'
    assert result[0]['slug'] == 'test-game'
    assert result[0]['developer_name'] == 'Test Studio'
    assert result[0]['publisher_name'] == 'Test Publisher'


def test_transform_fact_metrics(sample_game_data):
    """Test fact metrics transformation."""
    transformer = GameDataTransformer()
    result = transformer.transform_fact_metrics(sample_game_data)

    # Should create 2 fact records (one per platform)
    assert len(result) == 2

    # Check first fact record
    assert result[0]['game_id'] == 1
    assert result[0]['platform_id'] in [4, 18]
    assert result[0]['rating'] == 4.5
    assert result[0]['metacritic_score'] == 85
    assert result[0]['ratings_count'] == 1000


def test_transform_genres(sample_game_data):
    """Test genre extraction."""
    transformer = GameDataTransformer()
    result = transformer.transform_genres(sample_game_data)

    assert len(result) == 2
    genre_ids = [g['genre_id'] for g in result]
    assert 4 in genre_ids
    assert 51 in genre_ids


def test_create_game_genre_bridge(sample_game_data):
    """Test game-genre bridge creation."""
    transformer = GameDataTransformer()
    result = transformer.create_game_genre_bridge(sample_game_data)

    assert len(result) == 2
    assert result[0]['game_id'] == 1
    assert result[0]['genre_id'] in [4, 51]


def test_validate_data_quality_pass():
    """Test data quality validation - passing case."""
    transformer = GameDataTransformer()

    data = [
        {'id': 1, 'name': 'Game 1'},
        {'id': 2, 'name': 'Game 2'},
        {'id': 3, 'name': 'Game 3'}
    ]

    result = transformer.validate_data_quality(data, required_fields=['id', 'name'])
    assert result is True


def test_validate_data_quality_fail():
    """Test data quality validation - failing case."""
    transformer = GameDataTransformer()

    data = [
        {'id': 1, 'name': 'Game 1'},
        {'id': 2, 'name': None},  # Missing required field
        {'id': None, 'name': 'Game 3'}  # Missing required field
    ]

    result = transformer.validate_data_quality(data, required_fields=['id', 'name'])
    assert result is False


def test_transform_empty_data():
    """Test transformation with empty data."""
    transformer = GameDataTransformer()

    result = transformer.transform_games([])
    assert result == []

    result = transformer.transform_fact_metrics([])
    assert result == []
