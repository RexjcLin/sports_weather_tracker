"""
天氣 API 測試用例
涵蓋單元測試、集成測試和端點測試
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import AsyncGenerator

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db, Base
from app.models import (
    CurrentWeather, Users, WeatherForecast, WeatherAlerts,
    WeatherRecommendations, SportModes, Activities
)
from app.schemas.weather import (
    CurrentWeatherCreate, WeatherForecastCreate,
    WeatherAlertsCreate, RecommendationResponse
)


# ==================== 測試配置 ====================

# 測試數據庫 URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def async_engine():
    """創建測試數據庫引擎"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest.fixture
async def async_session_maker(async_engine):
    """創建異步會話製造器"""
    async_session = sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    return async_session


@pytest.fixture
async def db_session(async_session_maker) -> AsyncGenerator[AsyncSession, None]:
    """創建測試數據庫會話"""
    async with async_session_maker() as session:
        yield session


@pytest.fixture
async def client(db_session):
    """創建測試客戶端"""
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


# ==================== 測試數據 ====================

@pytest.fixture
async def sample_current_weather(db_session):
    """創建示例即時天氣數據"""
    weather = CurrentWeather(
        location_name="台北市",
        latitude=Decimal("25.0330"),
        longitude=Decimal("121.5653"),
        temperature=Decimal("28.5"),
        humidity=75,
        wind_speed=Decimal("3.2"),
        pressure=1013,
        visibility=10000,
        weather_main="Partly Cloudy",
        weather_description="多雲",
        data_time=datetime.now(),
        fetched_at=datetime.now()
    )
    db_session.add(weather)
    await db_session.commit()
    await db_session.refresh(weather)
    return weather


@pytest.fixture
async def sample_forecast(db_session):
    """創建示例天氣預報數據"""
    forecast = WeatherForecast(
        location_name="台北市",
        latitude=Decimal("25.0330"),
        longitude=Decimal("121.5653"),
        forecast_time=datetime.now() + timedelta(days=1),
        temperature_max=Decimal("32.0"),
        temperature_min=Decimal("26.0"),
        precipitation_probability=40,
        weather_main="Partly Cloudy",
        weather_description="多雲時晴",
        forecast_issued_at=datetime.now(),
        fetched_at=datetime.now()
    )
    db_session.add(forecast)
    await db_session.commit()
    await db_session.refresh(forecast)
    return forecast


@pytest.fixture
async def sample_alert(db_session):
    """創建示例氣象警告數據"""
    alert = WeatherAlerts(
        location_name="台北市",
        latitude=Decimal("25.0330"),
        longitude=Decimal("121.5653"),
        alert_type="豪雨特報",
        alert_level="Severe",
        alert_description="北部地區即將有豪雨，請注意防雨。",
        alert_issued_at=datetime.now(),
        alert_expires_at=datetime.now() + timedelta(hours=6),
        is_active=True
    )
    db_session.add(alert)
    await db_session.commit()
    await db_session.refresh(alert)
    return alert


@pytest.fixture
async def sample_sport_mode(db_session):
    """創建示例運動模式"""
    mode = SportModes(
        mode_name="慢跑",
        intensity_level="moderate",
        duration_typical=45,
        danger_temp_max=35.0,
        danger_temp_min=0.0,
        warning_temp_max=32.0,
        warning_temp_min=5.0,
        danger_humidity_max=95,
        warning_humidity_max=85,
        danger_wind_speed_max=15.0,
        warning_wind_speed_max=10.0,
        danger_precipitation_prob=80,
        warning_precipitation_prob=50,
        danger_visibility_min=1000,
        is_water_sport=False,
        safety_score_coeffs={"temp": 0.3, "humidity": 0.2, "wind": 0.2}
    )
    db_session.add(mode)
    await db_session.commit()
    await db_session.refresh(mode)
    return mode


@pytest.fixture
async def sample_activity(db_session, sample_sport_mode):
    """創建示例運動記錄"""
    activity = Activities(
        mode_id=sample_sport_mode.id,
        start_time=datetime.now() - timedelta(hours=1),
        end_time=datetime.now(),
        planned_duration=60,
        actual_duration=45,
        location_name="台北市",
        latitude=Decimal("25.0330"),
        longitude=Decimal("121.5653"),
        distance_km=5.0,
        calories_burned=500,
        completion_status="completed",
        user_notes="早晨慢跑"
    )
    db_session.add(activity)
    await db_session.commit()
    await db_session.refresh(activity)
    return activity


# ==================== 即時天氣 API 測試 ====================

@pytest.mark.asyncio
async def test_get_current_weather_success(client, sample_current_weather):
    """測試成功獲取即時天氣"""
    response = await client.get("/api/v1/weather/current/台北市")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["location_name"] == "台北市"
    assert data["temperature"] == 28.5
    assert data["humidity"] == 75
    assert data["wind_speed"] == 3.2


@pytest.mark.asyncio
async def test_get_current_weather_not_found(client):
    """測試獲取不存在的位置天氣"""
    response = await client.get("/api/v1/weather/current/虛構城市")
    
    assert response.status_code == 404
    assert "找不到" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_all_current_weather(client, sample_current_weather, db_session):
    """測試獲取所有位置的即時天氣"""
    # 添加另一個位置的天氣
    weather2 = CurrentWeather(
        location_name="高雄市",
        latitude=Decimal("22.6163"),
        longitude=Decimal("120.3135"),
        temperature=Decimal("30.0"),
        humidity=80,
        wind_speed=Decimal("4.0"),
        pressure=1010,
        visibility=8000,
        weather_main="Cloudy",
        weather_description="陰天",
        data_time=datetime.now(),
        fetched_at=datetime.now()
    )
    db_session.add(weather2)
    await db_session.commit()
    
    response = await client.get("/api/v1/weather/current")
    
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) >= 2
    locations = [w["location_name"] for w in data]
    assert "台北市" in locations
    assert "高雄市" in locations


@pytest.mark.asyncio
async def test_get_all_current_weather_with_limit(client, sample_current_weather):
    """測試獲取所有天氣的 limit 參數"""
    response = await client.get("/api/v1/weather/current?limit=10")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 10


@pytest.mark.asyncio
async def test_create_activity_persists_steps():
    engine = create_async_engine(TEST_DATABASE_URL)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)() as db_session:
            user = Users(username="step_user", email="steps@example.com", password_hash="hashed")
            mode = SportModes(mode_name="健走")
            db_session.add_all([user, mode])
            await db_session.commit()
            await db_session.refresh(user)
            await db_session.refresh(mode)

            async def override_get_db():
                yield db_session

            app.dependency_overrides[get_db] = override_get_db
            try:
                response = await AsyncClient(app=app, base_url="http://test").post(
                    "/api/v1/activities",
                    json={
                        "user_id": user.id,
                        "mode_id": mode.id,
                        "title": "晨間健走",
                        "start_time": "2026-10-12T08:00:00",
                        "end_time": "2026-10-12T09:00:00",
                        "total_distance_meters": 4200,
                        "steps_count": 5600,
                        "start_latitude": 25.033,
                        "start_longitude": 121.5653,
                        "end_latitude": 25.04,
                        "end_longitude": 121.57,
                    },
                )
            finally:
                app.dependency_overrides.clear()

            assert response.status_code == 201
            activity = await db_session.get(Activities, response.json()["activity_id"])
            assert activity.steps_count == 5600
    finally:
        await engine.dispose()


# ==================== 天氣預報 API 測試 ====================

@pytest.mark.asyncio
async def test_get_weather_forecast_success(client, sample_forecast):
    """測試成功獲取天氣預報"""
    response = await client.get("/api/v1/weather/forecast/台北市?days=7")
    
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) > 0
    assert data[0]["location_name"] == "台北市"
    assert data[0]["temperature_max"] == 32.0
    assert data[0]["temperature_min"] == 26.0


@pytest.mark.asyncio
async def test_get_weather_forecast_not_found(client):
    """測試獲取不存在的位置預報"""
    response = await client.get("/api/v1/weather/forecast/虛構城市?days=7")
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_weather_forecast_invalid_days(client):
    """測試無效的天數參數"""
    # 測試超出範圍的天數
    response = await client.get("/api/v1/weather/forecast/台北市?days=15")
    
    # 應該被限制在最大值
    assert response.status_code in [200, 422]


# ==================== 氣象警告 API 測試 ====================

@pytest.mark.asyncio
async def test_get_weather_alerts_success(client, sample_alert):
    """測試成功獲取氣象警告"""
    response = await client.get("/api/v1/weather/alerts/台北市")
    
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) > 0
    assert data[0]["alert_type"] == "豪雨特報"
    assert data[0]["alert_level"] == "Severe"
    assert data[0]["is_active"] is True


@pytest.mark.asyncio
async def test_get_weather_alerts_active_only(client, sample_alert, db_session):
    """測試只獲取活躍警告"""
    response = await client.get(
        "/api/v1/weather/alerts/台北市?active_only=true"
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # 所有返回的警告應該是活躍的
    for alert in data:
        assert alert["is_active"] is True


@pytest.mark.asyncio
async def test_get_all_active_alerts(client, sample_alert):
    """測試獲取所有位置的活躍警告"""
    response = await client.get("/api/v1/weather/alerts")
    
    assert response.status_code == 200
    data = response.json()
    
    # 所有返回的警告應該是活躍的
    for alert in data:
        assert alert["is_active"] is True


# ==================== 天氣建議 API 測試 ====================

@pytest.mark.asyncio
async def test_get_recommendation_success(client, db_session, sample_activity):
    """測試成功獲取運動建議"""
    # 首先創建一個建議
    recommendation = WeatherRecommendations(
        activity_id=sample_activity.id,
        mode_id=sample_activity.mode_id,
        recommendation_level="safe",
        reasons=["temperature_optimal", "humidity_optimal"],
        suggestions="天氣良好，可以正常進行運動。",
        temperature_status="optimal",
        humidity_status="optimal",
        wind_status="optimal",
        precipitation_status="optimal",
        visibility_status="optimal",
        uv_status="optimal"
    )
    db_session.add(recommendation)
    await db_session.commit()
    
    response = await client.get(
        f"/api/v1/weather/recommendations/{sample_activity.id}"
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["recommendation_level"] == "safe"
    assert len(data["reasons"]) > 0


@pytest.mark.asyncio
async def test_get_recommendation_not_found(client):
    """測試獲取不存在的建議"""
    response = await client.get("/api/v1/weather/recommendations/99999")
    
    assert response.status_code == 404


# ==================== 天氣數據更新 API 測試 ====================

@pytest.mark.asyncio
async def test_update_location_weather(client, sample_current_weather):
    """測試手動更新位置天氣"""
    response = await client.post("/api/v1/weather/update/台北市")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "success"
    assert "台北市" in data["message"]


@pytest.mark.asyncio
async def test_update_all_weather(client):
    """測試批量更新所有天氣"""
    response = await client.post("/api/v1/weather/update-all")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "success"


# ==================== 健康檢查測試 ====================

@pytest.mark.asyncio
async def test_health_check(client):
    """測試健康檢查端點"""
    response = await client.get("/api/v1/weather/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "healthy"
    assert data["service"] == "weather"
    assert "timestamp" in data


# ==================== 數據模型測試 ====================

@pytest.mark.asyncio
async def test_current_weather_model(db_session):
    """測試 CurrentWeather 模型"""
    weather = CurrentWeather(
        location_name="台中市",
        latitude=Decimal("24.1372"),
        longitude=Decimal("120.6732"),
        temperature=Decimal("27.0"),
        humidity=70,
        wind_speed=Decimal("2.5"),
        pressure=1012,
        visibility=9000,
        weather_main="Sunny",
        weather_description="晴天",
        data_time=datetime.now(),
        fetched_at=datetime.now()
    )
    db_session.add(weather)
    await db_session.commit()
    
    assert weather.id is not None
    assert weather.location_name == "台中市"
    assert weather.temperature == Decimal("27.0")


@pytest.mark.asyncio
async def test_weather_forecast_model(db_session):
    """測試 WeatherForecast 模型"""
    forecast = WeatherForecast(
        location_name="台中市",
        latitude=Decimal("24.1372"),
        longitude=Decimal("120.6732"),
        forecast_time=datetime.now() + timedelta(days=2),
        temperature_max=Decimal("30.0"),
        temperature_min=Decimal("24.0"),
        precipitation_probability=30,
        weather_main="Sunny",
        weather_description="晴天",
        forecast_issued_at=datetime.now(),
        fetched_at=datetime.now()
    )
    db_session.add(forecast)
    await db_session.commit()
    
    assert forecast.id is not None
    assert forecast.temperature_max == Decimal("30.0")
    assert forecast.precipitation_probability == 30


@pytest.mark.asyncio
async def test_weather_alerts_model(db_session):
    """測試 WeatherAlerts 模型"""
    alert = WeatherAlerts(
        location_name="台中市",
        latitude=Decimal("24.1372"),
        longitude=Decimal("120.6732"),
        alert_type="寒流特報",
        alert_level="Warning",
        alert_description="中部地區即將降溫。",
        alert_issued_at=datetime.now(),
        alert_expires_at=datetime.now() + timedelta(hours=12),
        is_active=True
    )
    db_session.add(alert)
    await db_session.commit()
    
    assert alert.id is not None
    assert alert.alert_type == "寒流特報"
    assert alert.is_active is True


# ==================== 性能測試 ====================

@pytest.mark.asyncio
async def test_concurrent_weather_requests(client, sample_current_weather):
    """測試並發天氣請求"""
    import asyncio
    
    async def make_request():
        return await client.get("/api/v1/weather/current/台北市")
    
    # 並發 10 個請求
    tasks = [make_request() for _ in range(10)]
    responses = await asyncio.gather(*tasks)
    
    # 所有請求都應該成功
    for response in responses:
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_large_forecast_dataset(client, db_session):
    """測試大數據集預報查詢"""
    # 創建多天預報數據
    for day in range(10):
        forecast = WeatherForecast(
            location_name="台北市",
            latitude=Decimal("25.0330"),
            longitude=Decimal("121.5653"),
            forecast_time=datetime.now() + timedelta(days=day),
            temperature_max=Decimal("30.0"),
            temperature_min=Decimal("24.0"),
            precipitation_probability=40,
            weather_main="Variable",
            weather_description="變天",
            forecast_issued_at=datetime.now(),
            fetched_at=datetime.now()
        )
        db_session.add(forecast)
    
    await db_session.commit()
    
    response = await client.get("/api/v1/weather/forecast/台北市?days=10")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 10


# ==================== 錯誤處理測試 ====================

@pytest.mark.asyncio
async def test_invalid_endpoint(client):
    """測試無效端點"""
    response = await client.get("/api/v1/weather/invalid-endpoint")
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_method_not_allowed(client):
    """測試不允許的方法"""
    response = await client.post("/api/v1/weather/current/台北市")
    
    assert response.status_code in [405, 422]


@pytest.mark.asyncio
async def test_empty_response_handling(client):
    """測試空響應處理"""
    response = await client.get("/api/v1/weather/alerts")
    
    # 即使沒有警告，也應該返回 200
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


# ==================== 數據驗證測試 ====================

def test_current_weather_schema_validation():
    """測試 CurrentWeather Schema 驗證"""
    from app.schemas.weather import CurrentWeatherCreate
    
    # 有效數據
    valid_data = {
        "location_name": "台北市",
        "latitude": Decimal("25.0330"),
        "longitude": Decimal("121.5653"),
        "temperature": Decimal("28.5"),
        "humidity": 75,
        "wind_speed": Decimal("3.2"),
        "pressure": 1013,
        "visibility": 10000,
        "weather_main": "Cloudy",
        "weather_description": "陰天"
    }
    
    schema = CurrentWeatherCreate(**valid_data)
    assert schema.location_name == "台北市"


def test_humidity_validation():
    """測試濕度驗證"""
    from app.schemas.weather import CurrentWeatherCreate
    import pytest
    
    # 無效的濕度值（超過 100%）
    with pytest.raises(ValueError):
        CurrentWeatherCreate(
            location_name="台北市",
            latitude=Decimal("25.0330"),
            longitude=Decimal("121.5653"),
            temperature=Decimal("28.5"),
            humidity=150,  # 無效
            wind_speed=Decimal("3.2"),
            pressure=1013,
            visibility=10000,
            weather_main="Cloudy",
            weather_description="陰天"
        )


# ==================== 測試運行指南 ====================

if __name__ == "__main__":
    """
    運行測試的命令：
    
    1. 運行所有測試
       pytest tests/test_weather_api.py -v
    
    2. 運行特定測試函數
       pytest tests/test_weather_api.py::test_get_current_weather_success -v
    
    3. 運行特定類別的測試
       pytest tests/test_weather_api.py -k "current_weather" -v
    
    4. 運行並顯示 print 輸出
       pytest tests/test_weather_api.py -v -s
    
    5. 運行並生成覆蓋率報告
       pytest tests/test_weather_api.py --cov=app --cov-report=html
    
    6. 運行特定標記的測試
       pytest tests/test_weather_api.py -m asyncio -v
    """
    pass
