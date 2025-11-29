"""
Unit tests for RAWG API client.
"""
import pytest
import responses
from src.api import RAWGClient


@pytest.fixture
def api_client():
    """Create RAWGClient instance for testing."""
    return RAWGClient(api_key='test_key', rate_limit=0)


@responses.activate
def test_get_games_success(api_client):
    """Test successful games retrieval."""
    # Mock API response
    responses.add(
        responses.GET,
        'https://api.rawg.io/api/games',
        json={
            'count': 2,
            'results': [
                {'id': 1, 'name': 'Game 1'},
                {'id': 2, 'name': 'Game 2'}
            ],
            'next': None
        },
        status=200
    )

    response = api_client.get_games(page=1)

    assert response['count'] == 2
    assert len(response['results']) == 2
    assert response['results'][0]['name'] == 'Game 1'


@responses.activate
def test_get_game_details(api_client):
    """Test game details retrieval."""
    game_id = 123

    responses.add(
        responses.GET,
        f'https://api.rawg.io/api/games/{game_id}',
        json={
            'id': game_id,
            'name': 'Test Game',
            'rating': 4.5
        },
        status=200
    )

    response = api_client.get_game_details(game_id)

    assert response['id'] == game_id
    assert response['name'] == 'Test Game'
    assert response['rating'] == 4.5


@responses.activate
def test_rate_limiting(api_client):
    """Test that rate limiting is applied."""
    import time

    api_client.rate_limit = 2  # 2 requests per second

    responses.add(
        responses.GET,
        'https://api.rawg.io/api/games',
        json={'results': []},
        status=200
    )

    start_time = time.time()
    api_client.get_games()
    api_client.get_games()
    elapsed = time.time() - start_time

    # Should take at least 0.5 seconds for 2 requests at 2 req/s
    assert elapsed >= 0.4


@responses.activate
def test_fetch_all_pages(api_client):
    """Test pagination handling."""
    # Mock first page
    responses.add(
        responses.GET,
        'https://api.rawg.io/api/games',
        json={
            'results': [{'id': 1}, {'id': 2}],
            'next': 'https://api.rawg.io/api/games?page=2'
        },
        status=200
    )

    # Mock second page
    responses.add(
        responses.GET,
        'https://api.rawg.io/api/games',
        json={
            'results': [{'id': 3}, {'id': 4}],
            'next': None
        },
        status=200
    )

    results = api_client.fetch_all_pages(api_client.get_games, max_pages=2)

    assert len(results) == 4
    assert results[0]['id'] == 1
    assert results[3]['id'] == 4


@responses.activate
def test_http_error_handling(api_client):
    """Test HTTP error handling."""
    responses.add(
        responses.GET,
        'https://api.rawg.io/api/games',
        status=500
    )

    with pytest.raises(Exception):
        api_client.get_games()
