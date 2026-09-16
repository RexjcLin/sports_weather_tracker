"""SQLAlchemy ORM models for activities and weather data."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Optional

from sqlalchemy import Boolean, Date, DateTime, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class shared by all database models."""


class Users(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column("user_id", Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[Optional[str]] = mapped_column(String(50))
    last_name: Mapped[Optional[str]] = mapped_column(String(50))
    city: Mapped[Optional[str]] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class SportModes(Base):
    __tablename__ = "sport_modes"

    id: Mapped[int] = mapped_column("mode_id", Integer, primary_key=True)
    mode_name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500))
    intensity_level: Mapped[Optional[str]] = mapped_column(String(30))
    duration_typical: Mapped[Optional[int]] = mapped_column(Integer)
    danger_temp_max: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    danger_temp_min: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    warning_temp_max: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    warning_temp_min: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    danger_humidity_max: Mapped[Optional[int]] = mapped_column(Integer)
    warning_humidity_max: Mapped[Optional[int]] = mapped_column(Integer)
    danger_wind_speed_max: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    warning_wind_speed_max: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    danger_precipitation_prob: Mapped[Optional[int]] = mapped_column(Integer)
    warning_precipitation_prob: Mapped[Optional[int]] = mapped_column(Integer)
    danger_visibility_min: Mapped[Optional[int]] = mapped_column(Integer)
    is_water_sport: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    safety_score_coeffs: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Activities(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column("activity_id", Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer)
    mode_id: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    planned_duration: Mapped[Optional[int]] = mapped_column(Integer)
    actual_duration: Mapped[Optional[int]] = mapped_column(Integer)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    total_distance_meters: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    start_latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 8))
    start_longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(11, 8))
    start_location_name: Mapped[Optional[str]] = mapped_column(String(200))
    end_latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 8))
    end_longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(11, 8))
    end_location_name: Mapped[Optional[str]] = mapped_column(String(200))
    location_name: Mapped[Optional[str]] = mapped_column(String(200))
    latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 8))
    longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(11, 8))
    distance_km: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    calories_burned: Mapped[Optional[int]] = mapped_column(Integer)
    completion_status: Mapped[Optional[str]] = mapped_column(String(30))
    status: Mapped[Optional[str]] = mapped_column(String(30))
    user_notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class GpsPoints(Base):
    __tablename__ = "gps_points"

    id: Mapped[int] = mapped_column("point_id", Integer, primary_key=True)
    activity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(10, 8), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(11, 8), nullable=False)
    altitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))
    speed_ms: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    accuracy_meters: Mapped[Optional[int]] = mapped_column(Integer)
    heading: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    recorded_at: Mapped[datetime] = mapped_column("timestamp", DateTime, nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CurrentWeather(Base):
    __tablename__ = "current_weather"

    id: Mapped[int] = mapped_column("weather_id", Integer, primary_key=True)
    location_name: Mapped[str] = mapped_column(String(200), nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(10, 8), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(11, 8), nullable=False)
    temperature: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    feels_like_temp: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    temp_min: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    temp_max: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    humidity: Mapped[int] = mapped_column(Integer, nullable=False)
    pressure: Mapped[Optional[int]] = mapped_column(Integer)
    wind_speed: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    wind_direction: Mapped[Optional[int]] = mapped_column(Integer)
    wind_direction_description: Mapped[Optional[str]] = mapped_column(String(20))
    wind_gust: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    precipitation: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    precipitation_probability: Mapped[Optional[int]] = mapped_column(Integer)
    visibility: Mapped[Optional[int]] = mapped_column(Integer)
    cloud_coverage: Mapped[Optional[int]] = mapped_column(Integer)
    uv_index: Mapped[Optional[int]] = mapped_column(Integer)
    weather_main: Mapped[Optional[str]] = mapped_column(String(50))
    weather_description: Mapped[Optional[str]] = mapped_column(String(200))
    weather_icon: Mapped[Optional[str]] = mapped_column(String(50))
    data_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class WeatherForecast(Base):
    __tablename__ = "weather_forecast"

    id: Mapped[int] = mapped_column("forecast_id", Integer, primary_key=True)
    location_name: Mapped[str] = mapped_column(String(200), nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(10, 8), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(11, 8), nullable=False)
    forecast_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    temperature_min: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    temperature_max: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    temperature: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    humidity: Mapped[Optional[int]] = mapped_column(Integer)
    wind_speed: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    wind_direction: Mapped[Optional[int]] = mapped_column(Integer)
    precipitation_probability: Mapped[Optional[int]] = mapped_column(Integer)
    precipitation_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    weather_main: Mapped[Optional[str]] = mapped_column(String(50))
    weather_description: Mapped[Optional[str]] = mapped_column(String(200))
    forecast_issued_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WeatherHistory(Base):
    __tablename__ = "weather_history"

    id: Mapped[int] = mapped_column("history_id", Integer, primary_key=True)
    location_name: Mapped[str] = mapped_column(String(200), nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(10, 8), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(11, 8), nullable=False)
    weather_date: Mapped[date] = mapped_column(Date, nullable=False)
    temp_max: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    temp_min: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    avg_temp: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    humidity: Mapped[Optional[int]] = mapped_column(Integer)
    wind_speed: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    precipitation: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    weather_description: Mapped[Optional[str]] = mapped_column(String(200))
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WeatherAlerts(Base):
    __tablename__ = "weather_alerts"

    id: Mapped[int] = mapped_column("alert_id", Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer)
    location_name: Mapped[str] = mapped_column(String(200), nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(10, 8), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(11, 8), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(100), nullable=False)
    alert_level: Mapped[str] = mapped_column(String(30), nullable=False)
    alert_description: Mapped[str] = mapped_column(Text, nullable=False)
    alert_issued_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    alert_expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ActivityWeatherSnapshots(Base):
    __tablename__ = "activity_weather_snapshots"

    id: Mapped[int] = mapped_column("snapshot_id", Integer, primary_key=True)
    activity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    weather_id: Mapped[Optional[int]] = mapped_column(Integer)
    captured_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    temperature: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    feels_like_temp: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    humidity: Mapped[Optional[int]] = mapped_column(Integer)
    wind_speed: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    precipitation: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    precipitation_probability: Mapped[Optional[int]] = mapped_column(Integer)
    visibility: Mapped[Optional[int]] = mapped_column(Integer)
    uv_index: Mapped[Optional[int]] = mapped_column(Integer)
    cloud_coverage: Mapped[Optional[int]] = mapped_column(Integer)
    weather_description: Mapped[Optional[str]] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WeatherRecommendations(Base):
    __tablename__ = "weather_recommendations"

    id: Mapped[int] = mapped_column("recommendation_id", Integer, primary_key=True)
    activity_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    mode_id: Mapped[int] = mapped_column(Integer, nullable=False)
    recommendation_level: Mapped[str] = mapped_column(String(20), default="safe")
    reasons: Mapped[List[str]] = mapped_column(JSON, default=list)
    suggestions: Mapped[Optional[str]] = mapped_column(Text)
    temperature_status: Mapped[Optional[str]] = mapped_column(String(50))
    humidity_status: Mapped[Optional[str]] = mapped_column(String(50))
    wind_status: Mapped[Optional[str]] = mapped_column(String(50))
    precipitation_status: Mapped[Optional[str]] = mapped_column(String(50))
    visibility_status: Mapped[Optional[str]] = mapped_column(String(50))
    uv_status: Mapped[Optional[str]] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class FavoriteLocations(Base):
    __tablename__ = "favorite_locations"

    id: Mapped[int] = mapped_column("location_id", Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    location_name: Mapped[str] = mapped_column(String(200), nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(10, 8), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(11, 8), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500))
    icon_url: Mapped[Optional[str]] = mapped_column(String(500))
    visit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ActivityStatistics(Base):
    __tablename__ = "activity_statistics"

    id: Mapped[int] = mapped_column("stat_id", Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    mode_id: Mapped[int] = mapped_column(Integer, nullable=False)
    stat_date: Mapped[date] = mapped_column(Date, nullable=False)
    activities_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_distance_meters: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    total_duration_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_speed_ms: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    total_elevation_gain_meters: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=0)
    avg_temperature: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    avg_humidity: Mapped[Optional[int]] = mapped_column(Integer)
    avg_wind_speed: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )