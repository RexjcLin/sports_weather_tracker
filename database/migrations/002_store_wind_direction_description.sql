USE sports_weather_tracker;

ALTER TABLE current_weather
    ADD COLUMN IF NOT EXISTS wind_direction_description VARCHAR(20)
    NULL AFTER wind_direction;

UPDATE current_weather
SET wind_direction_description = CASE
    WHEN wind_direction IS NULL THEN NULL
    WHEN wind_direction >= 337.5 OR wind_direction < 22.5 THEN '北風'
    WHEN wind_direction < 67.5 THEN '東北風'
    WHEN wind_direction < 112.5 THEN '東風'
    WHEN wind_direction < 157.5 THEN '東南風'
    WHEN wind_direction < 202.5 THEN '南風'
    WHEN wind_direction < 247.5 THEN '西南風'
    WHEN wind_direction < 292.5 THEN '西風'
    ELSE '西北風'
END;