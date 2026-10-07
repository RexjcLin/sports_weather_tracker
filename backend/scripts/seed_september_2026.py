"""Seed September fixtures and verify their generated weekly statistics."""

import argparse
import asyncio
import sys
import tempfile
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import Activities, ActivityStatistics, ActivityWeatherSnapshots, Base, SportModes, Users
from app.services.activity_statistics_service import generate_weekly_statistics

TEST_USERNAME = "monthly_stats_test_202609"
MODE_NAMES = {"walk": "健走", "hike": "爬山", "bike": "單車"}
FIXTURES = [
    ("walk_1", "walk", "2026-09-01T07:00:00", "completed", 3000, 1800, 30),
    ("walk_2", "walk", "2026-09-15T07:00:00", "completed", 5000, 3600, 50),
    ("hike_1", "hike", "2026-09-06T08:00:00", "completed", 6000, 7200, 600),
    ("hike_cross_month", "hike", "2026-09-30T23:30:00", "completed", 4000, 4800, 400),
    ("bike_1", "bike", "2026-09-12T06:00:00", "completed", 20000, 3600, 120),
    ("bike_2", "bike", "2026-09-26T06:00:00", "completed", 30000, 5400, 180),
    ("cancelled", "walk", "2026-09-18T07:00:00", "cancelled", 100000, 3600, 0),
    ("active", "bike", "2026-09-20T07:00:00", "active", 100000, 3600, 0),
    ("august", "hike", "2026-08-31T08:00:00", "completed", 100000, 3600, 0),
    ("october", "walk", "2026-10-01T00:00:00", "completed", 100000, 3600, 0),
]
WEATHER_FIXTURES = {
    "walk_1": [(26, 60, 2), (30, 80, 4)],
    "walk_2": [(28, 70, 3)],
    "hike_1": [(20, 80, 1)],
    "hike_cross_month": [(22, 70, 3)],
    "bike_1": [(30, 60, 3)],
    "bike_2": [(32, 70, 5)],
}
EXPECTED = {
    ("walk", date(2026, 8, 31)): (1, Decimal("3000"), 1800, Decimal("30"), Decimal("1.67"), Decimal("28"), 70, Decimal("3")),
    ("hike", date(2026, 8, 31)): (2, Decimal("106000"), 10800, Decimal("600"), Decimal("9.81"), Decimal("20"), 80, Decimal("1")),
    ("bike", date(2026, 9, 7)): (1, Decimal("20000"), 3600, Decimal("120"), Decimal("5.56"), Decimal("30"), 60, Decimal("3")),
    ("walk", date(2026, 9, 14)): (1, Decimal("5000"), 3600, Decimal("50"), Decimal("1.39"), Decimal("28"), 70, Decimal("3")),
    ("bike", date(2026, 9, 21)): (1, Decimal("30000"), 5400, Decimal("180"), Decimal("5.56"), Decimal("32"), 70, Decimal("5")),
    ("hike", date(2026, 9, 28)): (1, Decimal("4000"), 4800, Decimal("400"), Decimal("0.83"), Decimal("22"), 70, Decimal("3")),
    ("walk", date(2026, 9, 28)): (1, Decimal("100000"), 3600, Decimal("0"), Decimal("27.78"), None, None, None),
}


async def seed_september_data(db: AsyncSession) -> tuple[int, dict[str, int]]:
    user = await db.scalar(select(Users).where(Users.username == TEST_USERNAME))
    if user is None:
        user = Users(username=TEST_USERNAME, email=f"{TEST_USERNAME}@example.invalid",
                     password_hash="disabled-test-account-not-a-password-hash", is_active=False)
        db.add(user)
        await db.flush()
    modes = {}
    for key, name in MODE_NAMES.items():
        mode = await db.scalar(select(SportModes).where(SportModes.mode_name == name))
        if mode is None:
            mode = SportModes(mode_name=name)
            db.add(mode)
            await db.flush()
        modes[key] = mode.id

    for label, mode_key, start, status, distance, duration, elevation in FIXTURES:
        title = f"[TEST-202609] {label}"
        activity = await db.scalar(select(Activities).where(
            Activities.user_id == user.id, Activities.title == title,
        ))
        if activity is None:
            start_time = datetime.fromisoformat(start)
            activity = Activities(
                user_id=user.id, mode_id=modes[mode_key], title=title,
                start_time=start_time, end_time=start_time + timedelta(seconds=duration),
                status=status, completion_status=status, total_distance_meters=distance,
                duration_seconds=duration, total_elevation_gain_meters=elevation,
                start_latitude=Decimal("25.0330"), start_longitude=Decimal("121.5654"),
                end_latitude=Decimal("25.0430"), end_longitude=Decimal("121.5754"),
            )
            db.add(activity)
            await db.flush()
        for index, (temperature, humidity, wind_speed) in enumerate(WEATHER_FIXTURES.get(label, [])):
            captured_at = activity.start_time + timedelta(minutes=5 * (index + 1))
            snapshot = await db.scalar(select(ActivityWeatherSnapshots).where(
                ActivityWeatherSnapshots.activity_id == activity.id,
                ActivityWeatherSnapshots.captured_at == captured_at,
            ))
            if snapshot is None:
                db.add(ActivityWeatherSnapshots(
                    activity_id=activity.id, captured_at=captured_at,
                    temperature=temperature, humidity=humidity, wind_speed=wind_speed,
                ))
                await db.flush()
    await db.commit()
    return user.id, modes


async def verify_september_statistics(db: AsyncSession, user_id: int, modes: dict[str, int]) -> None:
    rows = (await db.scalars(select(ActivityStatistics).where(
        ActivityStatistics.user_id == user_id,
        ActivityStatistics.stat_period == "weekly",
    ).execution_options(populate_existing=True))).all()
    if len(rows) != len(EXPECTED):
        raise RuntimeError(f"Expected {len(EXPECTED)} weekly records, got {len(rows)}")
    by_period = {(row.mode_id, row.stat_date): row for row in rows}
    for (mode_key, week_start), expected in EXPECTED.items():
        row = by_period[(modes[mode_key], week_start)]
        actual = (row.activities_count, row.total_distance_meters, row.total_duration_seconds,
                  row.total_elevation_gain_meters, row.avg_speed_ms, row.avg_temperature,
                  row.avg_humidity, row.avg_wind_speed)
        if actual != expected:
            raise RuntimeError(f"{mode_key} for {week_start}: expected {expected}, got {actual}")


async def run(use_configured_database: bool) -> None:
    if use_configured_database:
        from app.config import settings

        database_url = settings.DATABASE_URL
        print("Using configured database; migrations must already be applied.")
    else:
        demo_path = Path(tempfile.gettempdir()) / "sports_weather_tracker_202609_demo.db"
        database_url = f"sqlite+aiosqlite:///{demo_path.as_posix()}"
        print(f"Demo database: {demo_path}")
    engine = create_async_engine(database_url)
    try:
        if not use_configured_database:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            user_id, modes = await seed_september_data(db)
            for monday in (date(2026, 8, 31), date(2026, 9, 7), date(2026, 9, 14),
                           date(2026, 9, 21), date(2026, 9, 28)):
                await generate_weekly_statistics(db, monday)
            await verify_september_statistics(db, user_id, modes)
            print(f"PASS: user_id={user_id}, username={TEST_USERNAME}; 10 activities, 7 snapshots.")
            print("mode | week_start | count | distance_m | duration_s | elevation_m | speed_m/s | temp_C | humidity | wind_m/s")
            for (mode_key, week_start), expected in EXPECTED.items():
                print(" | ".join([mode_key, str(week_start), *(str(value) for value in expected)]))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--use-configured-database", action="store_true",
                        help="Write test fixtures to DATABASE_URL instead of the separate SQLite demo.")
    arguments = parser.parse_args()
    asyncio.run(run(arguments.use_configured_database))