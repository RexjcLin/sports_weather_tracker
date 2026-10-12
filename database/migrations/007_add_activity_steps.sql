-- Run once on an existing database before starting the updated backend.
USE sports_weather_tracker;

ALTER TABLE activities
    ADD COLUMN steps_count INT UNSIGNED NULL AFTER total_distance_meters;

ALTER TABLE activity_statistics
    ADD COLUMN total_steps BIGINT UNSIGNED NOT NULL DEFAULT 0 AFTER activities_count;

DROP PROCEDURE IF EXISTS update_user_statistics;

DELIMITER $$

CREATE PROCEDURE update_user_statistics(
    IN p_user_id INT,
    IN p_mode_id INT,
    IN p_stat_date DATE
)
BEGIN
    INSERT INTO activity_statistics (
        user_id, mode_id, stat_date,
        activities_count, total_steps, total_distance_meters,
        total_duration_seconds, avg_speed_ms,
        total_elevation_gain_meters
    )
    SELECT
        p_user_id,
        p_mode_id,
        p_stat_date,
        COUNT(*),
        COALESCE(SUM(steps_count), 0),
        COALESCE(SUM(total_distance_meters), 0),
        COALESCE(SUM(duration_seconds), 0),
        COALESCE(AVG(avg_speed_ms), 0),
        COALESCE(SUM(total_elevation_gain_meters), 0)
    FROM activities
    WHERE user_id = p_user_id
      AND mode_id = p_mode_id
      AND DATE(start_time) = p_stat_date
      AND status = 'completed'
    ON DUPLICATE KEY UPDATE
        activities_count = VALUES(activities_count),
        total_steps = VALUES(total_steps),
        total_distance_meters = VALUES(total_distance_meters),
        total_duration_seconds = VALUES(total_duration_seconds),
        avg_speed_ms = VALUES(avg_speed_ms),
        total_elevation_gain_meters = VALUES(total_elevation_gain_meters),
        updated_at = CURRENT_TIMESTAMP;
END$$

DELIMITER ;