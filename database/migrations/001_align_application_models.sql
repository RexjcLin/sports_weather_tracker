-- Align the existing MariaDB schema with the SQLAlchemy models used by FastAPI.
-- Run once on the Raspberry Pi after importing database/schema.sql.

USE sports_weather_tracker;

ALTER TABLE sport_modes
    ADD COLUMN IF NOT EXISTS intensity_level VARCHAR(30) NULL AFTER description,
    ADD COLUMN IF NOT EXISTS duration_typical INT NULL AFTER intensity_level,
    ADD COLUMN IF NOT EXISTS danger_temp_max DECIMAL(5, 2) NULL AFTER duration_typical,
    ADD COLUMN IF NOT EXISTS danger_temp_min DECIMAL(5, 2) NULL AFTER danger_temp_max,
    ADD COLUMN IF NOT EXISTS warning_temp_max DECIMAL(5, 2) NULL AFTER danger_temp_min,
    ADD COLUMN IF NOT EXISTS warning_temp_min DECIMAL(5, 2) NULL AFTER warning_temp_max,
    ADD COLUMN IF NOT EXISTS danger_humidity_max INT NULL AFTER warning_temp_min,
    ADD COLUMN IF NOT EXISTS warning_humidity_max INT NULL AFTER danger_humidity_max,
    ADD COLUMN IF NOT EXISTS danger_wind_speed_max DECIMAL(5, 2) NULL AFTER warning_humidity_max,
    ADD COLUMN IF NOT EXISTS warning_wind_speed_max DECIMAL(5, 2) NULL AFTER danger_wind_speed_max,
    ADD COLUMN IF NOT EXISTS danger_precipitation_prob INT NULL AFTER warning_wind_speed_max,
    ADD COLUMN IF NOT EXISTS warning_precipitation_prob INT NULL AFTER danger_precipitation_prob,
    ADD COLUMN IF NOT EXISTS danger_visibility_min INT NULL AFTER warning_precipitation_prob,
    ADD COLUMN IF NOT EXISTS is_water_sport BOOLEAN NOT NULL DEFAULT FALSE AFTER danger_visibility_min,
    ADD COLUMN IF NOT EXISTS safety_score_coeffs JSON NULL AFTER is_water_sport;

ALTER TABLE activities
    ADD COLUMN IF NOT EXISTS planned_duration INT NULL AFTER duration_seconds,
    ADD COLUMN IF NOT EXISTS actual_duration INT NULL AFTER planned_duration,
    ADD COLUMN IF NOT EXISTS location_name VARCHAR(200) NULL AFTER actual_duration,
    ADD COLUMN IF NOT EXISTS latitude DECIMAL(10, 8) NULL AFTER location_name,
    ADD COLUMN IF NOT EXISTS longitude DECIMAL(11, 8) NULL AFTER latitude,
    ADD COLUMN IF NOT EXISTS distance_km DECIMAL(10, 2) NULL AFTER longitude,
    ADD COLUMN IF NOT EXISTS calories_burned INT NULL AFTER distance_km,
    ADD COLUMN IF NOT EXISTS completion_status VARCHAR(30) NULL AFTER calories_burned,
    ADD COLUMN IF NOT EXISTS user_notes TEXT NULL AFTER completion_status;

-- CWA warnings are system-wide. They are not tied to an individual application user.
ALTER TABLE weather_alerts
    MODIFY COLUMN user_id INT NULL;

UPDATE sport_modes
SET
    intensity_level = CASE mode_name
        WHEN '爬山' THEN 'high'
        WHEN '單車' THEN 'moderate'
        ELSE 'low'
    END,
    duration_typical = CASE mode_name
        WHEN '爬山' THEN 180
        WHEN '單車' THEN 90
        ELSE 60
    END,
    danger_temp_max = 35,
    danger_temp_min = 0,
    warning_temp_max = 32,
    warning_temp_min = 5,
    danger_humidity_max = 95,
    warning_humidity_max = 85,
    danger_wind_speed_max = 15,
    warning_wind_speed_max = 10,
    danger_precipitation_prob = 80,
    warning_precipitation_prob = 50,
    danger_visibility_min = 1000
WHERE mode_name IN ('爬山', '健走', '單車');