-- Video Game Analytics Data Warehouse Schema
-- Star schema with fact and dimension tables

-- ============================================================================
-- DIMENSION TABLES
-- ============================================================================

-- Dimension: Games
CREATE TABLE IF NOT EXISTS dim_games (
    game_id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255),
    description TEXT,
    released DATE,
    background_image VARCHAR(500),
    website VARCHAR(500),
    developer_id INTEGER,
    developer_name VARCHAR(255),
    publisher_id INTEGER,
    publisher_name VARCHAR(255),
    esrb_rating VARCHAR(50),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_games_released ON dim_games(released);
CREATE INDEX idx_games_developer ON dim_games(developer_id);
CREATE INDEX idx_games_publisher ON dim_games(publisher_id);


-- Dimension: Genres
CREATE TABLE IF NOT EXISTS dim_genres (
    genre_id INTEGER PRIMARY KEY,
    genre_name VARCHAR(100) NOT NULL,
    slug VARCHAR(100),
    games_count INTEGER DEFAULT 0,
    image_background VARCHAR(500)
);


-- Dimension: Platforms
CREATE TABLE IF NOT EXISTS dim_platforms (
    platform_id INTEGER PRIMARY KEY,
    platform_name VARCHAR(100) NOT NULL,
    slug VARCHAR(100),
    games_count INTEGER DEFAULT 0,
    image_background VARCHAR(500),
    year_start INTEGER,
    year_end INTEGER
);


-- Dimension: Developers
CREATE TABLE IF NOT EXISTS dim_developers (
    developer_id INTEGER PRIMARY KEY,
    developer_name VARCHAR(255) NOT NULL,
    slug VARCHAR(255),
    games_count INTEGER DEFAULT 0,
    image_background VARCHAR(500)
);


-- Dimension: Publishers
CREATE TABLE IF NOT EXISTS dim_publishers (
    publisher_id INTEGER PRIMARY KEY,
    publisher_name VARCHAR(255) NOT NULL,
    slug VARCHAR(255),
    games_count INTEGER DEFAULT 0,
    image_background VARCHAR(500)
);


-- ============================================================================
-- FACT TABLE
-- ============================================================================

-- Fact: Game Metrics (grain: game per platform)
CREATE TABLE IF NOT EXISTS fact_game_metrics (
    game_id INTEGER NOT NULL,
    platform_id INTEGER NOT NULL,
    released DATE,
    rating DECIMAL(3,2),
    rating_top INTEGER,
    ratings_count INTEGER DEFAULT 0,
    reviews_count INTEGER DEFAULT 0,
    metacritic_score INTEGER,
    playtime INTEGER DEFAULT 0,
    added INTEGER DEFAULT 0,
    suggestions_count INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (game_id, platform_id),
    FOREIGN KEY (game_id) REFERENCES dim_games(game_id),
    FOREIGN KEY (platform_id) REFERENCES dim_platforms(platform_id)
);

CREATE INDEX idx_fact_released ON fact_game_metrics(released);
CREATE INDEX idx_fact_rating ON fact_game_metrics(rating);
CREATE INDEX idx_fact_metacritic ON fact_game_metrics(metacritic_score);
CREATE INDEX idx_fact_updated ON fact_game_metrics(updated_at);


-- ============================================================================
-- BRIDGE TABLES (Many-to-Many Relationships)
-- ============================================================================

-- Bridge: Game-Genre (many-to-many)
CREATE TABLE IF NOT EXISTS bridge_game_genre (
    game_id INTEGER NOT NULL,
    genre_id INTEGER NOT NULL,

    PRIMARY KEY (game_id, genre_id),
    FOREIGN KEY (game_id) REFERENCES dim_games(game_id),
    FOREIGN KEY (genre_id) REFERENCES dim_genres(genre_id)
);

CREATE INDEX idx_bridge_game ON bridge_game_genre(game_id);
CREATE INDEX idx_bridge_genre ON bridge_game_genre(genre_id);


-- ============================================================================
-- VIEWS FOR ANALYTICS
-- ============================================================================

-- View: Game details with metrics
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


-- View: Top rated games
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


-- View: Genre popularity
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


-- View: Platform statistics
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


-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE dim_games IS 'Dimension table containing game master data';
COMMENT ON TABLE dim_genres IS 'Dimension table for game genres';
COMMENT ON TABLE dim_platforms IS 'Dimension table for gaming platforms';
COMMENT ON TABLE dim_developers IS 'Dimension table for game developers';
COMMENT ON TABLE dim_publishers IS 'Dimension table for game publishers';
COMMENT ON TABLE fact_game_metrics IS 'Fact table containing game metrics per platform';
COMMENT ON TABLE bridge_game_genre IS 'Bridge table for game-genre many-to-many relationship';
