from datetime import date, datetime
from decimal import Decimal
from unittest.mock import Mock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import Activities, ActivityStatistics, ActivityWeatherSnapshots, Base
from app.services.activity_statistics_service import generate_weekly_statistics, previous_week_start


@pytest.mark.parametrize("today, expected", [
    (date(2026, 10, 5), date(2026, 9, 28)),
    (date(2026, 10, 4), date(2026, 9, 21)),
    (date(2026, 1, 5), date(2025, 12, 29)),
])
def test_previous_week(today, expected):
    assert previous_week_start(today) == expected


def test_weekly_scheduler_registration(monkeypatch):
    from app.tasks import scheduler

    fake_scheduler = Mock()
    monkeypatch.setattr(scheduler, "SchedulerManager", lambda: Mock(get_scheduler=lambda: fake_scheduler))
    scheduler.configure_scheduler()
    weekly_job = next(call for call in fake_scheduler.add_job.call_args_list
                      if call.kwargs["id"] == "generate_weekly_activity_statistics")
    assert weekly_job.args[0] is scheduler.generate_weekly_activity_statistics
    assert weekly_job.kwargs["next_run_time"] is not None
    assert weekly_job.kwargs["max_instances"] == 1
    trigger = weekly_job.kwargs["trigger"]
    next_fire = trigger.get_next_fire_time(None, datetime(2026, 9, 15, tzinfo=scheduler.TAIPEI_TIMEZONE))
    assert next_fire == datetime(2026, 9, 21, 0, 10, tzinfo=scheduler.TAIPEI_TIMEZONE)


@pytest.mark.asyncio
async def test_weekly_statistics_boundaries_weather_and_reruns():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            for activity_id, user_id, mode_id, started, status, distance, duration in [
                (1, 1, 2, datetime(2026, 9, 1), "completed", 1000, 1000),
                (2, 1, 2, datetime(2026, 9, 30, 23, 59), "completed", 3000, 1000),
                (3, 1, 2, datetime(2026, 10, 1), "completed", 9000, 1000),
                (4, 1, 2, datetime(2026, 8, 31), "completed", 9000, 1000),
                (5, 1, 2, datetime(2026, 9, 15), "active", 9000, 1000),
                (6, 2, 1, datetime(2026, 9, 15), "completed", 2000, 0),
                (7, None, 2, datetime(2026, 9, 15), "completed", 9000, 1000),
            ]:
                db.add(Activities(id=activity_id, user_id=user_id, mode_id=mode_id,
                                  start_time=started, end_time=started, status=status,
                                  total_distance_meters=distance, duration_seconds=duration,
                                  total_elevation_gain_meters=100))
            db.add(ActivityStatistics(user_id=1, mode_id=2, stat_date=date(2026, 9, 1),
                                      activities_count=1, stat_period="daily"))
            for snapshot_id, temperature in [(1, 20), (2, 30)]:
                db.add(ActivityWeatherSnapshots(id=snapshot_id, activity_id=1,
                                                captured_at=datetime(2026, 9, 1),
                                                temperature=temperature, humidity=70, wind_speed=2))
            await db.commit()

            assert await generate_weekly_statistics(db, date(2026, 9, 3)) == 1
            rows = (await db.scalars(select(ActivityStatistics).order_by(ActivityStatistics.id))).all()
            assert len(rows) == 2
            weekly = next(row for row in rows if row.user_id == 1 and row.stat_period == "weekly")
            assert weekly.stat_date == date(2026, 8, 31)
            assert weekly.activities_count == 2
            assert weekly.total_distance_meters == Decimal("10000")
            assert weekly.total_duration_seconds == 2000
            assert weekly.total_elevation_gain_meters == Decimal("200")
            assert weekly.avg_speed_ms == Decimal("5")
            assert weekly.avg_temperature == Decimal("25")
            assert weekly.avg_humidity == 70
            assert weekly.avg_wind_speed == Decimal("2")

            assert await generate_weekly_statistics(db, date(2026, 9, 15)) == 1
            other = await db.scalar(select(ActivityStatistics).where(
                ActivityStatistics.user_id == 2,
                ActivityStatistics.stat_period == "weekly",
            ))
            assert other.stat_date == date(2026, 9, 14)
            assert other.avg_speed_ms is None
            assert other.avg_temperature is None

            activity = await db.get(Activities, 1)
            activity.total_distance_meters = Decimal("2000")
            await db.commit()
            await generate_weekly_statistics(db, date(2026, 9, 1))
            await db.refresh(weekly)
            assert weekly.total_distance_meters == Decimal("11000")

            for activity in (await db.scalars(select(Activities))).all():
                activity.status = "cancelled"
            await db.commit()
            assert await generate_weekly_statistics(db, date(2026, 9, 1)) == 0
            assert await generate_weekly_statistics(db, date(2026, 9, 15)) == 0
            remaining = (await db.scalars(select(ActivityStatistics))).all()
            assert len(remaining) == 1
            assert remaining[0].stat_period == "daily"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_september_seed_is_repeatable():
    from scripts.seed_september_2026 import seed_september_data, verify_september_statistics
    from sqlalchemy import func
    from app.models import Users

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            user_id, modes = await seed_september_data(db)
            repeated_user_id, repeated_modes = await seed_september_data(db)
            assert repeated_user_id == user_id
            assert repeated_modes == modes
            assert await db.scalar(select(func.count()).select_from(Activities)) == 10
            assert await db.scalar(select(func.count()).select_from(ActivityWeatherSnapshots)) == 7
            assert (await db.get(Users, user_id)).is_active is False
            for monday in (date(2026, 8, 31), date(2026, 9, 7), date(2026, 9, 14),
                           date(2026, 9, 21), date(2026, 9, 28)):
                await generate_weekly_statistics(db, monday)
            await verify_september_statistics(db, user_id, modes)
            assert await db.scalar(select(func.count()).select_from(ActivityStatistics).where(
                ActivityStatistics.stat_period == "weekly")) == 7
            for monday in (date(2026, 8, 31), date(2026, 9, 7), date(2026, 9, 14),
                           date(2026, 9, 21), date(2026, 9, 28)):
                await generate_weekly_statistics(db, monday)
            await verify_september_statistics(db, user_id, modes)
            assert await db.scalar(select(func.count()).select_from(ActivityStatistics).where(
                ActivityStatistics.stat_period == "weekly")) == 7
    finally:
        await engine.dispose()