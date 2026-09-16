"""Activity APIs that connect recorded activities to weather snapshots."""

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Activities, ActivityWeatherSnapshots, CurrentWeather, SportModes, Users

router = APIRouter(prefix="/api/v1", tags=["活動"])


class UserCreate(BaseModel):
    username: str = Field(max_length=50)
    email: str = Field(max_length=100)
    password_hash: str = Field(min_length=1, max_length=255)


class ActivityCreate(BaseModel):
    user_id: int
    mode_id: int
    title: str = Field(max_length=200)
    start_time: datetime
    end_time: datetime
    total_distance_meters: Decimal = Field(ge=0)
    start_latitude: Decimal
    start_longitude: Decimal
    end_latitude: Decimal
    end_longitude: Decimal
    location_name: str | None = Field(default=None, max_length=200)


@router.post("/users", status_code=201)
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db)) -> dict:
    if await db.scalar(select(Users).where(Users.username == payload.username)):
        raise HTTPException(status_code=409, detail="使用者名稱已存在")
    if await db.scalar(select(Users).where(Users.email == payload.email)):
        raise HTTPException(status_code=409, detail="電子郵件已存在")

    user = Users(**payload.model_dump())
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"user_id": user.id, "username": user.username}


@router.post("/activities", status_code=201)
async def create_activity(payload: ActivityCreate, db: AsyncSession = Depends(get_db)) -> dict:
    if not await db.get(Users, payload.user_id):
        raise HTTPException(status_code=404, detail="找不到使用者")
    if not await db.get(SportModes, payload.mode_id):
        raise HTTPException(status_code=404, detail="找不到運動模式")

    duration_seconds = max(0, int((payload.end_time - payload.start_time).total_seconds()))
    activity = Activities(
        **payload.model_dump(),
        duration_seconds=duration_seconds,
        status="completed",
        completion_status="completed",
    )
    db.add(activity)
    await db.flush()

    if payload.location_name:
        weather = await db.scalar(
            select(CurrentWeather)
            .where(CurrentWeather.location_name == payload.location_name)
            .order_by(CurrentWeather.fetched_at.desc())
            .limit(1)
        )
        if weather:
            db.add(ActivityWeatherSnapshots(
                activity_id=activity.id,
                weather_id=weather.id,
                captured_at=datetime.utcnow(),
                temperature=weather.temperature,
                feels_like_temp=weather.feels_like_temp,
                humidity=weather.humidity,
                wind_speed=weather.wind_speed,
                precipitation=weather.precipitation,
                precipitation_probability=weather.precipitation_probability,
                visibility=weather.visibility,
                uv_index=weather.uv_index,
                cloud_coverage=weather.cloud_coverage,
                weather_description=weather.weather_description,
            ))

    await db.commit()
    return {"activity_id": activity.id, "weather_snapshot_created": bool(payload.location_name and weather)}