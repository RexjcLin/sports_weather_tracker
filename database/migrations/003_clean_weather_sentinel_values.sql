USE sports_weather_tracker;

UPDATE current_weather
SET
    feels_like_temp = NULLIF(feels_like_temp, -990),
    temp_min = NULLIF(temp_min, -990),
    temp_max = NULLIF(temp_max, -990),
    pressure = NULLIF(pressure, -99),
    wind_direction = NULLIF(wind_direction, -99),
    wind_gust = NULLIF(wind_gust, -990),
    precipitation = NULLIF(precipitation, -990),
    precipitation_probability = NULLIF(precipitation_probability, -99),
    visibility = NULLIF(visibility, -99);