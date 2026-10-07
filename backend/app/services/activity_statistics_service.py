"""Generate weekly summaries without mixing them with daily statistics."""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete, func, select, tuple_
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Activities, ActivityStatistics, ActivityWeatherSnapshots

TAIPEI_TIMEZONE = timezone(timedelta(hours=8))


def week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def previous_week_start(today: date) -> date:
    return week_start(today) - timedelta(days=7)


async def generate_weekly_statistics(db: AsyncSession, day: date) -> int:
    period_start = week_start(day)
    period_end = period_start + timedelta(days=7)
    filters = (
        Activities.status == "completed",
        Activities.user_id.is_not(None),
        Activities.start_time >= datetime.combine(period_start, datetime.min.time()),
        Activities.start_time < datetime.combine(period_end, datetime.min.time()),
    )
    totals = (await db.execute(
        select(
            Activities.user_id, Activities.mode_id,
            func.count().label("activities_count"),
            func.coalesce(func.sum(Activities.total_distance_meters), 0).label("total_distance_meters"),
            func.coalesce(func.sum(Activities.duration_seconds), 0).label("total_duration_seconds"),
            func.coalesce(func.sum(Activities.total_elevation_gain_meters), 0).label("total_elevation_gain_meters"),
        ).where(*filters).group_by(Activities.user_id, Activities.mode_id)
    )).mappings().all()
    weather = (await db.execute(
        select(
            Activities.user_id, Activities.mode_id,
            func.avg(ActivityWeatherSnapshots.temperature).label("avg_temperature"),
            func.avg(ActivityWeatherSnapshots.humidity).label("avg_humidity"),
            func.avg(ActivityWeatherSnapshots.wind_speed).label("avg_wind_speed"),
        ).join(ActivityWeatherSnapshots, ActivityWeatherSnapshots.activity_id == Activities.id)
        .where(*filters).group_by(Activities.user_id, Activities.mode_id)
    )).mappings().all()
    weather_by_key = {(row["user_id"], row["mode_id"]): row for row in weather}
    keys = [(row["user_id"], row["mode_id"]) for row in totals]
    stale = delete(ActivityStatistics).where(
        ActivityStatistics.stat_period == "weekly",
        ActivityStatistics.stat_date == period_start,
    )
    if keys:
        stale = stale.where(tuple_(ActivityStatistics.user_id, ActivityStatistics.mode_id).not_in(keys))
    await db.execute(stale)

    for row in totals:
        values = dict(row)
        key = (row["user_id"], row["mode_id"])
        weather_row = weather_by_key.get(key, {})
        values.update(
            stat_date=period_start,
            stat_period="weekly",
            avg_speed_ms=(row["total_distance_meters"] / row["total_duration_seconds"]
                          if row["total_duration_seconds"] > 0 else None),
            avg_temperature=weather_row.get("avg_temperature"),
            avg_humidity=(round(weather_row["avg_humidity"])
                          if weather_row.get("avg_humidity") is not None else None),
            avg_wind_speed=weather_row.get("avg_wind_speed"),
            updated_at=datetime.utcnow(),
        )
        if db.get_bind().dialect.name == "sqlite":
            statement = sqlite_insert(ActivityStatistics).values(**values)
            statement = statement.on_conflict_do_update(
                index_elements=["user_id", "mode_id", "stat_date", "stat_period"],
                set_={name: statement.excluded[name] for name in values},
            )
        else:
            statement = mysql_insert(ActivityStatistics).values(**values)
            statement = statement.on_duplicate_key_update(
                **{name: statement.inserted[name] for name in values}
            )
        await db.execute(statement)
    await db.commit()
    return len(totals)