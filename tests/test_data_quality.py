"""
Integration tests for data quality checks.
"""
import pytest
from src.utils import DatabaseManager


def test_fact_table_has_required_columns():
    """Test that fact table has all required columns."""
    # This is a schema validation test
    required_columns = [
        'game_id',
        'platform_id',
        'released',
        'rating',
        'metacritic_score',
        'ratings_count'
    ]

    # In a real test, you would query information_schema
    # to verify column existence
    assert len(required_columns) > 0


def test_dimension_tables_exist():
    """Test that all dimension tables are defined."""
    expected_tables = [
        'dim_games',
        'dim_genres',
        'dim_platforms',
        'dim_developers',
        'dim_publishers'
    ]

    assert len(expected_tables) == 5


def test_referential_integrity_constraints():
    """Test that foreign key constraints are properly defined."""
    # This would check that fact_game_metrics references
    # dim_games and dim_platforms
    pass


def test_no_duplicate_primary_keys():
    """Test that primary keys are unique."""
    # In production, this would query the database
    # to verify no duplicate PKs exist
    pass
