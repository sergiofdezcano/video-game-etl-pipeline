"""
Database utility functions for PostgreSQL operations.
"""
import logging
from typing import List, Dict, Any, Optional, Generator, Union, Tuple
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import execute_batch, RealDictCursor
from psycopg2 import pool
from psycopg2.extensions import connection, cursor


logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Base exception for database errors."""
    pass


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails."""
    pass


class DatabaseManager:
    """Manages PostgreSQL database connections and operations."""

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        min_connections: int = 1,
        max_connections: int = 10
    ):
        """
        Initialize database manager with connection pooling.

        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password
            min_connections: Minimum connections in pool
            max_connections: Maximum connections in pool
        """
        self.connection_params = {
            'host': host,
            'port': port,
            'database': database,
            'user': user,
            'password': password
        }

        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                min_connections,
                max_connections,
                **self.connection_params
            )
            logger.info(
                f"Database connection pool created for {database} "
                f"(min={min_connections}, max={max_connections})"
            )
        except psycopg2.OperationalError as e:
            logger.error(f"Failed to connect to database {database}: {e}", exc_info=True)
            raise DatabaseConnectionError(f"Database connection failed: {e}") from e
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}", exc_info=True)
            raise DatabaseError(f"Failed to create connection pool: {e}") from e

    @contextmanager
    def get_connection(self) -> Generator[connection, None, None]:
        """
        Context manager for database connections.

        Automatically returns connection to pool when done.
        Connection is not committed or rolled back here - use get_cursor for that.

        Yields:
            psycopg2 connection object

        Raises:
            DatabaseError: If connection cannot be obtained
        """
        conn: Optional[connection] = None
        try:
            conn = self.connection_pool.getconn()
            if conn is None:
                raise DatabaseError("Failed to get connection from pool")
            yield conn
        except Exception as e:
            logger.error(f"Error with database connection: {e}", exc_info=True)
            raise DatabaseError(f"Connection error: {e}") from e
        finally:
            if conn is not None:
                self.connection_pool.putconn(conn)

    @contextmanager
    def get_cursor(
        self,
        dict_cursor: bool = False
    ) -> Generator[cursor, None, None]:
        """
        Context manager for database cursors.

        Automatically commits on success, rolls back on error, and closes cursor.
        This is the recommended way to execute database operations.

        Args:
            dict_cursor: If True, return RealDictCursor for dict-like row access

        Yields:
            psycopg2 cursor object

        Raises:
            DatabaseError: If operation fails
        """
        with self.get_connection() as conn:
            cursor_factory = RealDictCursor if dict_cursor else None
            cur: Optional[cursor] = None
            try:
                cur = conn.cursor(cursor_factory=cursor_factory)
                yield cur
                conn.commit()
            except psycopg2.Error as e:
                conn.rollback()
                logger.error(f"Database operation failed: {e}", exc_info=True)
                raise DatabaseError(f"Database operation failed: {e}") from e
            except Exception as e:
                conn.rollback()
                logger.error(f"Unexpected error during database operation: {e}", exc_info=True)
                raise DatabaseError(f"Unexpected database error: {e}") from e
            finally:
                if cur is not None:
                    cur.close()

    def execute_query(
        self,
        query: str,
        params: Optional[Union[tuple, Dict[str, Any]]] = None,
        fetch: bool = False
    ) -> Optional[List[Tuple]]:
        """
        Execute a SQL query.

        Args:
            query: SQL query string (use %s for placeholders)
            params: Query parameters (tuple or dict)
            fetch: If True, return results

        Returns:
            Query results if fetch=True, else None

        Raises:
            DatabaseError: If query execution fails
        """
        with self.get_cursor() as cur:
            cur.execute(query, params)
            if fetch:
                return cur.fetchall()
            return None

    def execute_many(
        self,
        query: str,
        data: List[Tuple],
        batch_size: int = 1000
    ) -> None:
        """
        Execute batch insert/update operations.

        Uses psycopg2's execute_batch for optimal performance with large datasets.
        Significantly faster than executemany() for bulk operations.

        Args:
            query: SQL query with placeholders (%s)
            data: List of tuples with values
            batch_size: Number of rows per batch (default: 1000)

        Raises:
            DatabaseError: If batch operation fails
        """
        if not data:
            logger.warning("No data to insert")
            return

        logger.debug(f"Executing batch operation with {len(data)} rows (batch_size={batch_size})")

        with self.get_cursor() as cur:
            execute_batch(cur, query, data, page_size=batch_size)
            logger.info(f"Batch operation completed: {len(data)} rows affected")

    def bulk_upsert(
        self,
        table: str,
        data: List[Dict[str, Any]],
        conflict_columns: List[str],
        update_columns: Optional[List[str]] = None
    ) -> None:
        """
        Perform bulk upsert (INSERT ... ON CONFLICT DO UPDATE).

        This is the most efficient way to load data that may contain duplicates.
        Uses PostgreSQL's ON CONFLICT clause for atomic upsert operations.

        Args:
            table: Target table name
            data: List of dictionaries with column:value pairs
            conflict_columns: Columns that define uniqueness (e.g., ['game_id'])
            update_columns: Columns to update on conflict (all non-conflict cols if None)

        Raises:
            DatabaseError: If upsert operation fails
            ValueError: If data is malformed
        """
        if not data:
            logger.debug("No data provided for bulk upsert")
            return

        # Validate data structure
        if not all(isinstance(row, dict) for row in data):
            raise ValueError("All data items must be dictionaries")

        # Get all columns from first record
        columns = list(data[0].keys())

        if not columns:
            raise ValueError("Data dictionaries must not be empty")

        # Columns to update (exclude conflict columns if not specified)
        if update_columns is None:
            update_columns = [col for col in columns if col not in conflict_columns]

        # Build INSERT query with parameterized values for SQL injection safety
        placeholders = ', '.join(['%s'] * len(columns))
        columns_str = ', '.join(columns)

        # Build ON CONFLICT clause
        conflict_str = ', '.join(conflict_columns)

        # Only add UPDATE clause if there are columns to update
        if update_columns:
            update_str = ', '.join([f"{col} = EXCLUDED.{col}" for col in update_columns])
            conflict_action = f"DO UPDATE SET {update_str}"
        else:
            conflict_action = "DO NOTHING"

        query = f"""
            INSERT INTO {table} ({columns_str})
            VALUES ({placeholders})
            ON CONFLICT ({conflict_str})
            {conflict_action}
        """

        # Convert dicts to tuples in correct column order for performance
        # This ensures values align with column order in query
        values: List[Tuple] = [
            tuple(record.get(col) for col in columns)
            for record in data
        ]

        self.execute_many(query, values)
        logger.info(f"Upserted {len(data)} rows into {table}")

    def get_max_value(
        self,
        table: str,
        column: str,
        where_clause: str = ""
    ) -> Any:
        """
        Get maximum value from a column.

        Useful for incremental loading to determine last processed record.

        Args:
            table: Table name
            column: Column name
            where_clause: Optional WHERE clause (without WHERE keyword)

        Returns:
            Maximum value or None if table is empty

        Raises:
            DatabaseError: If query fails
        """
        # Note: This uses string formatting which is safe for table/column names
        # but should never be used for user-provided values
        query = f"SELECT MAX({column}) FROM {table}"
        if where_clause:
            query += f" WHERE {where_clause}"

        result = self.execute_query(query, fetch=True)
        return result[0][0] if result and result[0] else None

    def get_row_count(self, table: str, where_clause: str = "") -> int:
        """
        Get row count from table.

        Args:
            table: Table name
            where_clause: Optional WHERE clause (without WHERE keyword)

        Returns:
            Number of rows

        Raises:
            DatabaseError: If query fails
        """
        query = f"SELECT COUNT(*) FROM {table}"
        if where_clause:
            query += f" WHERE {where_clause}"

        result = self.execute_query(query, fetch=True)
        return result[0][0] if result and result[0] else 0

    def table_exists(self, table_name: str, schema: str = 'public') -> bool:
        """
        Check if table exists in database.

        Uses information_schema for safe, standard SQL check.

        Args:
            table_name: Name of table
            schema: Schema name (default: public)

        Returns:
            True if table exists

        Raises:
            DatabaseError: If query fails
        """
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = %s
                AND table_name = %s
            )
        """
        result = self.execute_query(query, (schema, table_name), fetch=True)
        return result[0][0] if result and result[0] else False

    def close(self) -> None:
        """
        Close all connections in pool.

        Should be called when DatabaseManager is no longer needed.
        Releases all database connections and resources.
        """
        if self.connection_pool:
            try:
                self.connection_pool.closeall()
                logger.info("Database connection pool closed")
            except Exception as e:
                logger.warning(f"Error closing connection pool: {e}")
