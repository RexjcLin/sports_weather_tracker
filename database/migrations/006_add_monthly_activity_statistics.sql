-- Run once on an existing database before starting the updated backend.
USE sports_weather_tracker;

ALTER TABLE activity_statistics
    ADD COLUMN stat_period VARCHAR(10) NOT NULL DEFAULT 'daily' AFTER stat_date,
    DROP INDEX idx_user_mode_date,
    ADD UNIQUE INDEX idx_user_mode_date (user_id, mode_id, stat_date, stat_period);