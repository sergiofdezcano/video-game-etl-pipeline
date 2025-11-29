# Data Dictionary

## Overview

This document provides a comprehensive reference for all tables, columns, views, and relationships in the Video Game Analytics data warehouse. The schema follows a **star schema** design pattern optimized for analytical queries.

## Schema Diagram

```
                     ┌─────────────────────────────────────┐
                     │        dim_developers               │
                     │  ─────────────────────────          │
                     │  developer_id (PK)                  │
                     │  developer_name                     │
                     │  slug, games_count, image_bg        │
                     └──────────────┬──────────────────────┘
                                    │
                     ┌──────────────▼──────────────────────┐
                     │        dim_publishers               │
                     │  ─────────────────────────          │
                     │  publisher_id (PK)                  │
                     │  publisher_name                     │
                     │  slug, games_count, image_bg        │
                     └──────────────┬──────────────────────┘
                                    │
┌────────────────┐   ┌──────────────▼──────────────────────┐   ┌────────────────┐
│  dim_genres    │   │           dim_games                 │   │ dim_platforms  │
│  ────────────  │   │  ───────────────────────────        │   │  ────────────  │
│  genre_id (PK) │   │  game_id (PK)                       │   │  platform_id   │
│  genre_name    │   │  name, slug, description            │   │  platform_name │
│  slug          │   │  released, background_image         │   │  slug          │
│  games_count   │   │  website, esrb_rating               │   │  games_count   │
│  image_bg      │   │  developer_id (FK) ─────────────────┼───│  year_start    │
└────────┬───────┘   │  developer_name                     │   │  year_end      │
         │           │  publisher_id (FK) ─────────────────┘   └───────┬────────┘
         │           │  publisher_name                                  │
         │           │  updated_at                                      │
         │           └──────────────┬───────────────────────────────────┘
         │                          │
         │           ┌──────────────▼────────────────────────┐
         │           │      fact_game_metrics                │
         │           │  ────────────────────────────────     │
         │           │  game_id (PK, FK) ────────────────────┤
         │           │  platform_id (PK, FK) ────────────────┤
         │           │  released                             │
         │           │  rating, rating_top                   │
         │           │  ratings_count, reviews_count         │
         │           │  metacritic_score                     │
         │           │  playtime, added                      │
         │           │  suggestions_count                    │
         │           │  updated_at                           │
         │           └──────────────┬────────────────────────┘
         │                          │
         │           ┌──────────────▼────────────────────────┐
         └───────────▶     bridge_game_genre                 │
                     │  ────────────────────────────────     │
                     │  game_id (PK, FK)                     │
                     │  genre_id (PK, FK)                    │
                     └───────────────────────────────────────┘
```

## Dimension Tables

### dim_games

**Description**: Dimension table containing master data for video games. This is the primary dimension with descriptive attributes about each game.

**Grain**: One row per unique game

**Type**: Slowly Changing Dimension (SCD Type 1 - overwrite on change)

| Column | Data Type | Constraints | Description | Example |
|--------|-----------|-------------|-------------|---------|
| `game_id` | INTEGER | PRIMARY KEY | RAWG unique identifier for game | `3498` |
| `name` | VARCHAR(255) | NOT NULL | Full name of the game | `"Grand Theft Auto V"` |
| `slug` | VARCHAR(255) | | URL-friendly identifier | `"grand-theft-auto-v"` |
| `description` | TEXT | | Raw text description of game | `"Rockstar Games went bigger..."` |
| `released` | DATE | | Official release date | `2013-09-17` |
| `background_image` | VARCHAR(500) | | URL to background image | `"https://media.rawg.io/..."` |
| `website` | VARCHAR(500) | | Official game website | `"http://rockstargames.com/V/"` |
| `developer_id` | INTEGER | | Foreign key to dim_developers | `3524` |
| `developer_name` | VARCHAR(255) | | Denormalized developer name | `"Rockstar North"` |
| `publisher_id` | INTEGER | | Foreign key to dim_publishers | `2155` |
| `publisher_name` | VARCHAR(255) | | Denormalized publisher name | `"Rockstar Games"` |
| `esrb_rating` | VARCHAR(50) | | ESRB age rating | `"Mature"`, `"Everyone"` |
| `updated_at` | TIMESTAMP | DEFAULT NOW() | Last update timestamp | `2024-11-29 10:30:00` |

**Indexes**:
- `idx_games_released` on `released` - For date range queries
- `idx_games_developer` on `developer_id` - For developer analysis
- `idx_games_publisher` on `publisher_id` - For publisher analysis

**Business Rules**:
1. If a game has multiple developers, only the **first one** is stored
2. If a game has multiple publishers, only the **primary one** is stored
3. `developer_name` and `publisher_name` are denormalized for query convenience
4. `description` may be NULL for games without detailed descriptions
5. `released` may be NULL for unreleased or TBA games
6. `updated_at` is updated on every ETL run if game data changes

**Sample Queries**:
```sql
-- Get all games released in 2023
SELECT * FROM dim_games WHERE released BETWEEN '2023-01-01' AND '2023-12-31';

-- Find games by developer
SELECT * FROM dim_games WHERE developer_name = 'Rockstar North';

-- Recently updated games
SELECT * FROM dim_games WHERE updated_at > NOW() - INTERVAL '7 days';
```

---

### dim_genres

**Description**: Dimension table for game genre taxonomy. Genres are used to categorize games (Action, RPG, Strategy, etc.)

**Grain**: One row per unique genre

**Type**: Static dimension (rarely changes)

| Column | Data Type | Constraints | Description | Example |
|--------|-----------|-------------|-------------|---------|
| `genre_id` | INTEGER | PRIMARY KEY | RAWG genre identifier | `4` |
| `genre_name` | VARCHAR(100) | NOT NULL | Genre name | `"Action"` |
| `slug` | VARCHAR(100) | | URL-friendly identifier | `"action"` |
| `games_count` | INTEGER | DEFAULT 0 | Number of games in genre | `176537` |
| `image_background` | VARCHAR(500) | | Representative background image | `"https://media.rawg.io/..."` |

**Business Rules**:
1. Genres are extracted from RAWG API's master genre list
2. `games_count` reflects RAWG's total count, not warehouse count
3. Genres are linked to games via `bridge_game_genre` (many-to-many)
4. New genres are rare but handled via upsert

**Sample Queries**:
```sql
-- Most popular genres by game count
SELECT genre_name, games_count FROM dim_genres ORDER BY games_count DESC;

-- Find a genre by name
SELECT * FROM dim_genres WHERE genre_name = 'Action';
```

---

### dim_platforms

**Description**: Dimension table for gaming platforms (PC, PlayStation, Xbox, etc.)

**Grain**: One row per unique platform

**Type**: Static dimension

| Column | Data Type | Constraints | Description | Example |
|--------|-----------|-------------|-------------|---------|
| `platform_id` | INTEGER | PRIMARY KEY | RAWG platform identifier | `4` |
| `platform_name` | VARCHAR(100) | NOT NULL | Platform name | `"PC"` |
| `slug` | VARCHAR(100) | | URL-friendly identifier | `"pc"` |
| `games_count` | INTEGER | DEFAULT 0 | Number of games on platform | `452000` |
| `image_background` | VARCHAR(500) | | Representative background image | `"https://media.rawg.io/..."` |
| `year_start` | INTEGER | | Year platform was released | `2013` |
| `year_end` | INTEGER | | Year platform was discontinued | `2020` (NULL if active) |

**Business Rules**:
1. `games_count` is RAWG's total, not warehouse count
2. `year_end` is NULL for active platforms (PC, current-gen consoles)
3. `year_start` may be NULL for platforms with unknown release dates
4. Platforms are linked to games via `fact_game_metrics`

**Sample Queries**:
```sql
-- Active platforms (still being supported)
SELECT * FROM dim_platforms WHERE year_end IS NULL;

-- Platforms by release year
SELECT * FROM dim_platforms ORDER BY year_start DESC;
```

---

### dim_developers

**Description**: Dimension table for game development studios

**Grain**: One row per unique developer

**Type**: Slowly Changing Dimension (SCD Type 1)

| Column | Data Type | Constraints | Description | Example |
|--------|-----------|-------------|-------------|---------|
| `developer_id` | INTEGER | PRIMARY KEY | RAWG developer identifier | `3524` |
| `developer_name` | VARCHAR(255) | NOT NULL | Developer/studio name | `"Rockstar North"` |
| `slug` | VARCHAR(255) | | URL-friendly identifier | `"rockstar-north"` |
| `games_count` | INTEGER | DEFAULT 0 | Number of games developed | `29` |
| `image_background` | VARCHAR(500) | | Representative background image | `"https://media.rawg.io/..."` |

**Business Rules**:
1. `games_count` reflects RAWG's total count
2. Independent studios and subsidiaries are separate records
3. Name changes result in new records (not tracked as changes)

**Sample Queries**:
```sql
-- Top developers by game count
SELECT developer_name, games_count FROM dim_developers ORDER BY games_count DESC LIMIT 10;
```

---

### dim_publishers

**Description**: Dimension table for game publishers

**Grain**: One row per unique publisher

**Type**: Slowly Changing Dimension (SCD Type 1)

| Column | Data Type | Constraints | Description | Example |
|--------|-----------|-------------|-------------|---------|
| `publisher_id` | INTEGER | PRIMARY KEY | RAWG publisher identifier | `2155` |
| `publisher_name` | VARCHAR(255) | NOT NULL | Publisher name | `"Rockstar Games"` |
| `slug` | VARCHAR(255) | | URL-friendly identifier | `"rockstar-games"` |
| `games_count` | INTEGER | DEFAULT 0 | Number of games published | `85` |
| `image_background` | VARCHAR(500) | | Representative background image | `"https://media.rawg.io/..."` |

**Business Rules**:
1. `games_count` reflects RAWG's total count
2. Self-published games may have developer = publisher

**Sample Queries**:
```sql
-- Top publishers
SELECT publisher_name, games_count FROM dim_publishers ORDER BY games_count DESC LIMIT 10;
```

---

## Fact Table

### fact_game_metrics

**Description**: Fact table containing quantitative metrics for games. Uses a **composite grain** of game × platform to track platform-specific metrics.

**Grain**: One row per game-platform combination

**Type**: Periodic snapshot (daily updates via upsert)

| Column | Data Type | Constraints | Description | Example | Typical Range |
|--------|-----------|-------------|-------------|---------|---------------|
| `game_id` | INTEGER | PK, FK → dim_games | Game identifier | `3498` | |
| `platform_id` | INTEGER | PK, FK → dim_platforms | Platform identifier | `4` | |
| `released` | DATE | | Game release date | `2013-09-17` | |
| `rating` | DECIMAL(3,2) | | Average user rating (0-5 scale) | `4.47` | 0.00 - 5.00 |
| `rating_top` | INTEGER | | Maximum rating score | `5` | 1 - 5 |
| `ratings_count` | INTEGER | DEFAULT 0 | Number of user ratings | `6500` | 0 - 50000+ |
| `reviews_count` | INTEGER | DEFAULT 0 | Number of text reviews | `1200` | 0 - 10000+ |
| `metacritic_score` | INTEGER | | Metacritic score (0-100) | `96` | 0 - 100 |
| `playtime` | INTEGER | DEFAULT 0 | Average playtime (hours) | `74` | 0 - 1000+ |
| `added` | INTEGER | DEFAULT 0 | Number of users who added game | `18500` | 0 - 100000+ |
| `suggestions_count` | INTEGER | DEFAULT 0 | Number of recommendations | `420` | 0 - 5000+ |
| `updated_at` | TIMESTAMP | DEFAULT NOW() | Last update timestamp | `2024-11-29 10:30:00` | |

**Primary Key**: `(game_id, platform_id)` - Composite key

**Foreign Keys**:
- `game_id` → `dim_games(game_id)`
- `platform_id` → `dim_platforms(platform_id)`

**Indexes**:
- `idx_fact_released` on `released` - For time-series analysis
- `idx_fact_rating` on `rating` - For top-rated queries
- `idx_fact_metacritic` on `metacritic_score` - For critic score analysis
- `idx_fact_updated` on `updated_at` - For incremental processing

**Business Rules**:
1. **One row per game-platform pair**: GTA V on PC and PS4 = 2 rows
2. **Metrics are platform-agnostic** in RAWG API, so values are **duplicated** across platforms for the same game
3. `rating` is on a 0-5 scale (not 0-10)
4. `metacritic_score` may be NULL if game not reviewed by Metacritic
5. `playtime` is **average** hours, not total across all users
6. `added` represents popularity/library additions
7. All count fields default to 0 if not provided
8. `updated_at` tracks when metrics were last refreshed

**Additive Measures**:
- `ratings_count`, `reviews_count`, `added`, `suggestions_count`

**Semi-Additive Measures**:
- None (no time dimension for snapshots)

**Non-Additive Measures**:
- `rating`, `metacritic_score`, `playtime` (use AVG, not SUM)

**Sample Queries**:
```sql
-- Top rated games with significant ratings
SELECT g.name, AVG(f.rating) as avg_rating, SUM(f.ratings_count) as total_ratings
FROM fact_game_metrics f
JOIN dim_games g ON f.game_id = g.game_id
GROUP BY g.game_id, g.name
HAVING SUM(f.ratings_count) > 1000
ORDER BY avg_rating DESC
LIMIT 10;

-- Platform with most games
SELECT p.platform_name, COUNT(DISTINCT f.game_id) as game_count
FROM fact_game_metrics f
JOIN dim_platforms p ON f.platform_id = p.platform_id
GROUP BY p.platform_id, p.platform_name
ORDER BY game_count DESC;

-- Games with highest Metacritic scores
SELECT g.name, f.metacritic_score
FROM fact_game_metrics f
JOIN dim_games g ON f.game_id = g.game_id
WHERE f.metacritic_score IS NOT NULL
ORDER BY f.metacritic_score DESC
LIMIT 10;
```

---

## Bridge Tables

### bridge_game_genre

**Description**: Bridge table implementing the many-to-many relationship between games and genres. A game can have multiple genres (e.g., "Action RPG" has both Action and RPG).

**Grain**: One row per game-genre pair

**Type**: Association/junction table

| Column | Data Type | Constraints | Description | Example |
|--------|-----------|-------------|-------------|---------|
| `game_id` | INTEGER | PK, FK → dim_games | Game identifier | `3498` |
| `genre_id` | INTEGER | PK, FK → dim_genres | Genre identifier | `4` |

**Primary Key**: `(game_id, genre_id)` - Composite key

**Foreign Keys**:
- `game_id` → `dim_games(game_id)`
- `genre_id` → `dim_genres(genre_id)`

**Indexes**:
- `idx_bridge_game` on `game_id` - For finding genres of a game
- `idx_bridge_genre` on `genre_id` - For finding games in a genre

**Business Rules**:
1. **Deduplication enforced** via composite primary key
2. Games typically have 1-4 genres
3. Orphaned records not allowed (cascading foreign keys)

**Sample Queries**:
```sql
-- Find all genres for a specific game
SELECT gn.genre_name
FROM bridge_game_genre bg
JOIN dim_genres gn ON bg.genre_id = gn.genre_id
WHERE bg.game_id = 3498;

-- Find all games in "Action" genre
SELECT g.name
FROM bridge_game_genre bg
JOIN dim_games g ON bg.game_id = g.game_id
JOIN dim_genres gn ON bg.genre_id = gn.genre_id
WHERE gn.genre_name = 'Action';

-- Count games per genre
SELECT gn.genre_name, COUNT(bg.game_id) as game_count
FROM dim_genres gn
LEFT JOIN bridge_game_genre bg ON gn.genre_id = bg.genre_id
GROUP BY gn.genre_id, gn.genre_name
ORDER BY game_count DESC;
```

---

## Analytical Views

### vw_game_details

**Description**: Denormalized view joining games, platforms, and metrics for easy querying

**Type**: Standard view (not materialized)

**Definition**:
```sql
CREATE OR REPLACE VIEW vw_game_details AS
SELECT
    g.game_id,
    g.name,
    g.released,
    g.developer_name,
    g.publisher_name,
    g.esrb_rating,
    f.platform_id,
    p.platform_name,
    f.rating,
    f.metacritic_score,
    f.ratings_count,
    f.reviews_count,
    f.playtime,
    f.added as popularity_score
FROM dim_games g
JOIN fact_game_metrics f ON g.game_id = f.game_id
JOIN dim_platforms p ON f.platform_id = p.platform_id;
```

**Columns**:
| Column | Source | Description |
|--------|--------|-------------|
| `game_id` | dim_games | Game identifier |
| `name` | dim_games | Game name |
| `released` | dim_games | Release date |
| `developer_name` | dim_games | Developer name |
| `publisher_name` | dim_games | Publisher name |
| `esrb_rating` | dim_games | Age rating |
| `platform_id` | dim_platforms | Platform identifier |
| `platform_name` | dim_platforms | Platform name |
| `rating` | fact_game_metrics | User rating |
| `metacritic_score` | fact_game_metrics | Critic score |
| `ratings_count` | fact_game_metrics | Number of ratings |
| `reviews_count` | fact_game_metrics | Number of reviews |
| `playtime` | fact_game_metrics | Average playtime |
| `popularity_score` | fact_game_metrics | User additions (renamed) |

**Use Case**: Quick analysis without joining multiple tables

---

### vw_top_rated_games

**Description**: Pre-aggregated view of highly-rated games (minimum 100 ratings)

**Type**: Standard view

**Definition**:
```sql
CREATE OR REPLACE VIEW vw_top_rated_games AS
SELECT
    g.name,
    g.developer_name,
    g.released,
    AVG(f.rating) as avg_rating,
    AVG(f.metacritic_score) as avg_metacritic,
    SUM(f.ratings_count) as total_ratings
FROM dim_games g
JOIN fact_game_metrics f ON g.game_id = f.game_id
GROUP BY g.game_id, g.name, g.developer_name, g.released
HAVING SUM(f.ratings_count) > 100
ORDER BY avg_rating DESC;
```

**Columns**:
| Column | Type | Description |
|--------|------|-------------|
| `name` | VARCHAR | Game name |
| `developer_name` | VARCHAR | Developer |
| `released` | DATE | Release date |
| `avg_rating` | NUMERIC | Average rating across platforms |
| `avg_metacritic` | NUMERIC | Average Metacritic score |
| `total_ratings` | BIGINT | Total ratings across platforms |

**Business Rules**:
- Only includes games with 100+ total ratings
- Averages computed across all platforms
- Pre-sorted by rating (descending)

---

### vw_genre_popularity

**Description**: Genre-level metrics aggregated from games and facts

**Type**: Standard view

**Definition**:
```sql
CREATE OR REPLACE VIEW vw_genre_popularity AS
SELECT
    gn.genre_name,
    COUNT(DISTINCT bg.game_id) as games_count,
    AVG(f.rating) as avg_rating,
    SUM(f.added) as total_popularity
FROM dim_genres gn
JOIN bridge_game_genre bg ON gn.genre_id = bg.genre_id
JOIN fact_game_metrics f ON bg.game_id = f.game_id
GROUP BY gn.genre_id, gn.genre_name
ORDER BY total_popularity DESC;
```

**Columns**:
| Column | Type | Description |
|--------|------|-------------|
| `genre_name` | VARCHAR | Genre name |
| `games_count` | BIGINT | Unique games in warehouse |
| `avg_rating` | NUMERIC | Average rating for genre |
| `total_popularity` | BIGINT | Sum of 'added' metric |

---

### vw_platform_stats

**Description**: Platform-level statistics

**Type**: Standard view

**Definition**:
```sql
CREATE OR REPLACE VIEW vw_platform_stats AS
SELECT
    p.platform_name,
    COUNT(DISTINCT f.game_id) as games_count,
    AVG(f.rating) as avg_rating,
    AVG(f.metacritic_score) as avg_metacritic,
    SUM(f.ratings_count) as total_ratings
FROM dim_platforms p
JOIN fact_game_metrics f ON p.platform_id = f.platform_id
GROUP BY p.platform_id, p.platform_name
ORDER BY games_count DESC;
```

**Columns**:
| Column | Type | Description |
|--------|------|-------------|
| `platform_name` | VARCHAR | Platform name |
| `games_count` | BIGINT | Games on platform (in warehouse) |
| `avg_rating` | NUMERIC | Average user rating |
| `avg_metacritic` | NUMERIC | Average critic score |
| `total_ratings` | BIGINT | Total user ratings |

---

## Relationships

### Foreign Key Constraints

```sql
-- fact_game_metrics foreign keys
ALTER TABLE fact_game_metrics
  ADD CONSTRAINT fk_fact_game
    FOREIGN KEY (game_id) REFERENCES dim_games(game_id);

ALTER TABLE fact_game_metrics
  ADD CONSTRAINT fk_fact_platform
    FOREIGN KEY (platform_id) REFERENCES dim_platforms(platform_id);

-- bridge_game_genre foreign keys
ALTER TABLE bridge_game_genre
  ADD CONSTRAINT fk_bridge_game
    FOREIGN KEY (game_id) REFERENCES dim_games(game_id);

ALTER TABLE bridge_game_genre
  ADD CONSTRAINT fk_bridge_genre
    FOREIGN KEY (genre_id) REFERENCES dim_genres(genre_id);
```

### Referential Integrity

**Cascade Rules**: Not explicitly defined (rely on application logic)

**Load Order** (to maintain integrity):
1. dim_genres, dim_platforms, dim_developers, dim_publishers (independent)
2. dim_games (references developers/publishers)
3. fact_game_metrics (references games/platforms)
4. bridge_game_genre (references games/genres)

---

## Data Types and Constraints

### Naming Conventions

- **Tables**: `snake_case` with prefix (`dim_`, `fact_`, `bridge_`)
- **Columns**: `snake_case`
- **Primary Keys**: `{entity}_id` (e.g., `game_id`)
- **Foreign Keys**: Same name as referenced column
- **Indexes**: `idx_{table}_{column}`

### NULL Handling

**NULL is allowed** for:
- Optional descriptive fields (`description`, `website`, `esrb_rating`)
- Optional metrics (`metacritic_score`)
- Optional dates (`released`, `year_start`, `year_end`)

**NULL is NOT allowed** for:
- Primary keys
- Entity names (`name`, `genre_name`, `platform_name`)
- Required foreign keys in facts/bridges

### Default Values

- Numeric counts: `DEFAULT 0`
- Timestamps: `DEFAULT CURRENT_TIMESTAMP`

---

## Indexing Strategy

### Primary Key Indexes

Automatically created clustered indexes on:
- All `{entity}_id` primary keys
- Composite keys in fact and bridge tables

### Secondary Indexes

**Dimension Tables**:
- `idx_games_released` - Time-based filtering
- `idx_games_developer` - Developer analysis
- `idx_games_publisher` - Publisher analysis

**Fact Table**:
- `idx_fact_released` - Time-series queries
- `idx_fact_rating` - Top-rated queries
- `idx_fact_metacritic` - Critic score filtering
- `idx_fact_updated` - Incremental load support

**Bridge Table**:
- `idx_bridge_game` - Find genres for a game
- `idx_bridge_genre` - Find games in a genre

### Index Maintenance

- Indexes automatically updated on insert/update
- No manual VACUUM required for small datasets
- Consider REINDEX for large data volumes

---

## Storage Estimates

| Table | Estimated Rows | Avg Row Size | Est. Storage |
|-------|----------------|--------------|--------------|
| dim_games | 10,000 | 1 KB | 10 MB |
| dim_genres | 20 | 200 B | 4 KB |
| dim_platforms | 50 | 200 B | 10 KB |
| dim_developers | 5,000 | 300 B | 1.5 MB |
| dim_publishers | 3,000 | 300 B | 900 KB |
| fact_game_metrics | 50,000 | 150 B | 7.5 MB |
| bridge_game_genre | 30,000 | 16 B | 480 KB |
| **Total** | | | **~20 MB** |

**Note**: Actual storage includes indexes (approximately 2x data size)

---

## Data Quality Rules

### Validation Rules

1. **Primary Key Uniqueness**: Enforced by constraints
2. **Foreign Key Validity**: Enforced by constraints
3. **Rating Range**: 0.00 ≤ rating ≤ 5.00 (application validation)
4. **Metacritic Range**: 0 ≤ metacritic_score ≤ 100 (application validation)
5. **Date Format**: ISO 8601 (YYYY-MM-DD)
6. **Non-negative Counts**: All count fields ≥ 0

### Quality Checks (Automated in DAG)

```sql
-- Check 1: No orphaned fact records
SELECT COUNT(*) FROM fact_game_metrics f
LEFT JOIN dim_games g ON f.game_id = g.game_id
WHERE g.game_id IS NULL;

-- Check 2: No null primary keys
SELECT COUNT(*) FROM fact_game_metrics
WHERE game_id IS NULL OR platform_id IS NULL;

-- Check 3: Data freshness
SELECT MAX(updated_at) > NOW() - INTERVAL '2 days'
FROM fact_game_metrics;
```

---

## Schema Evolution

### Adding Columns

```sql
-- Safe: Add nullable column
ALTER TABLE dim_games ADD COLUMN tags TEXT[];

-- Safe: Add column with default
ALTER TABLE fact_game_metrics ADD COLUMN last_played DATE DEFAULT NULL;
```

### Dropping Columns

```sql
-- Requires code changes first
ALTER TABLE dim_games DROP COLUMN website;
```

### Renaming Tables/Columns

```sql
-- Requires view updates
ALTER TABLE dim_games RENAME COLUMN esrb_rating TO age_rating;
```

---

## Related Documentation

- [Architecture](ARCHITECTURE.md) - System design and data flow
- [API Integration](API_INTEGRATION.md) - Source data structure
- [Operations](OPERATIONS.md) - Backup and recovery procedures
