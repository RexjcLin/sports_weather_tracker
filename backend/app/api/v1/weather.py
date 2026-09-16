"""
天氣 API 路由 - FastAPI 端點
提供天氣數據查詢和建議查詢功能
"""

import logging
from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from app.database import get_db
from app.services.weather_service import CWBWeatherService
from app.services.recommendation_engine import RecommendationEngine
from app.models import (
    CurrentWeather, WeatherForecast, WeatherAlerts, 
    WeatherRecommendations, Activities
)
from app.schemas.weather import (
    CurrentWeatherResponse, WeatherForecastResponse, 
    WeatherAlertsResponse, RecommendationResponse,
    WeatherUpdateRequest
)

logger = logging.getLogger(__name__)

# 創建路由
router = APIRouter(prefix="/api/v1/weather", tags=["天氣"])


# ==================== 即時天氣端點 ====================

@router.get("/current/{location_name}", response_model=CurrentWeatherResponse)
async def get_current_weather(
    location_name: str,
    db: AsyncSession = Depends(get_db)
) -> CurrentWeatherResponse:
    """
    獲取指定位置的即時天氣
    
    Args:
        location_name: 位置名稱 (如: 台北市)
        db: 數據庫連接
        
    Returns:
        即時天氣數據
    """
    try:
        stmt = select(CurrentWeather).where(
            CurrentWeather.location_name == location_name
        ).order_by(desc(CurrentWeather.fetched_at)).limit(1)
        
        result = await db.execute(stmt)
        weather = result.scalar_one_or_none()
        
        if not weather:
            raise HTTPException(
                status_code=404,
                detail=f"找不到 {location_name} 的天氣數據"
            )
        
        return CurrentWeatherResponse.from_orm(weather)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"獲取天氣數據失敗: {str(e)}")
        raise HTTPException(status_code=500, detail="獲取天氣數據失敗")


@router.get("/current", response_model=List[CurrentWeatherResponse])
async def get_all_current_weather(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(18, ge=1, le=100)
) -> List[CurrentWeatherResponse]:
    """
    獲取所有位置的最新即時天氣
    
    Args:
        db: 數據庫連接
        limit: 返回的最大位置數
        
    Returns:
        天氣數據列表
    """
    try:
        # 子查詢：獲取每個位置最新的天氣數據
        from sqlalchemy import func
        
        stmt = select(CurrentWeather).distinct(
            CurrentWeather.location_name
        ).order_by(
            CurrentWeather.location_name, 
            desc(CurrentWeather.fetched_at)
        ).limit(limit)
        
        result = await db.execute(stmt)
        weathers = result.scalars().all()
        
        return [CurrentWeatherResponse.from_orm(w) for w in weathers]
        
    except Exception as e:
        logger.error(f"獲取所有天氣數據失敗: {str(e)}")
        raise HTTPException(status_code=500, detail="獲取天氣數據失敗")


# ==================== 天氣預報端點 ====================

@router.get("/forecast/{location_name}", response_model=List[WeatherForecastResponse])
async def get_weather_forecast(
    location_name: str,
    db: AsyncSession = Depends(get_db),
    days: int = Query(7, ge=1, le=10)
) -> List[WeatherForecastResponse]:
    """
    獲取指定位置的天氣預報
    
    Args:
        location_name: 位置名稱
        db: 數據庫連接
        days: 預報天數 (1-10)
        
    Returns:
        預報數據列表
    """
    try:
        future_date = datetime.now() + timedelta(days=days)
        
        stmt = select(WeatherForecast).where(
            and_(
                WeatherForecast.location_name == location_name,
                WeatherForecast.forecast_time <= future_date
            )
        ).order_by(WeatherForecast.forecast_time)
        
        result = await db.execute(stmt)
        forecasts = result.scalars().all()
        
        if not forecasts:
            raise HTTPException(
                status_code=404,
                detail=f"找不到 {location_name} 的預報數據"
            )
        
        return [WeatherForecastResponse.from_orm(f) for f in forecasts]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"獲取預報數據失敗: {str(e)}")
        raise HTTPException(status_code=500, detail="獲取預報數據失敗")


# ==================== 氣象警告端點 ====================

@router.get("/alerts/{location_name}", response_model=List[WeatherAlertsResponse])
async def get_weather_alerts(
    location_name: str,
    db: AsyncSession = Depends(get_db),
    active_only: bool = Query(True)
) -> List[WeatherAlertsResponse]:
    """
    獲取指定位置的氣象警告
    
    Args:
        location_name: 位置名稱
        db: 數據庫連接
        active_only: 只返回活躍警告
        
    Returns:
        警告數據列表
    """
    try:
        conditions = [WeatherAlerts.location_name == location_name]
        
        if active_only:
            conditions.append(WeatherAlerts.is_active == True)
        
        stmt = select(WeatherAlerts).where(
            and_(*conditions)
        ).order_by(desc(WeatherAlerts.alert_issued_at))
        
        result = await db.execute(stmt)
        alerts = result.scalars().all()
        
        return [WeatherAlertsResponse.from_orm(a) for a in alerts]
        
    except Exception as e:
        logger.error(f"獲取警告數據失敗: {str(e)}")
        raise HTTPException(status_code=500, detail="獲取警告數據失敗")


@router.get("/alerts", response_model=List[WeatherAlertsResponse])
async def get_all_active_alerts(
    db: AsyncSession = Depends(get_db)
) -> List[WeatherAlertsResponse]:
    """
    獲取所有位置的活躍氣象警告
    
    Args:
        db: 數據庫連接
        
    Returns:
        警告數據列表
    """
    try:
        stmt = select(WeatherAlerts).where(
            WeatherAlerts.is_active == True
        ).order_by(
            desc(WeatherAlerts.alert_issued_at)
        )
        
        result = await db.execute(stmt)
        alerts = result.scalars().all()
        
        return [WeatherAlertsResponse.from_orm(a) for a in alerts]
        
    except Exception as e:
        logger.error(f"獲取所有警告失敗: {str(e)}")
        raise HTTPException(status_code=500, detail="獲取警告數據失敗")


# ==================== 天氣建議端點 ====================

@router.get("/recommendations/{activity_id}", response_model=RecommendationResponse)
async def get_activity_recommendation(
    activity_id: int,
    db: AsyncSession = Depends(get_db)
) -> RecommendationResponse:
    """
    獲取特定運動的天氣建議
    
    Args:
        activity_id: 運動記錄 ID
        db: 數據庫連接
        
    Returns:
        天氣建議
    """
    try:
        stmt = select(WeatherRecommendations).where(
            WeatherRecommendations.activity_id == activity_id
        )
        
        result = await db.execute(stmt)
        recommendation = result.scalar_one_or_none()
        
        if not recommendation:
            raise HTTPException(
                status_code=404,
                detail=f"找不到運動 {activity_id} 的建議"
            )
        
        return RecommendationResponse.from_orm(recommendation)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"獲取建議失敗: {str(e)}")
        raise HTTPException(status_code=500, detail="獲取建議失敗")


@router.post("/recommendations/{activity_id}", response_model=RecommendationResponse)
async def generate_activity_recommendation(
    activity_id: int,
    db: AsyncSession = Depends(get_db)
) -> RecommendationResponse:
    """
    為特定運動生成天氣建議
    
    Args:
        activity_id: 運動記錄 ID
        db: 數據庫連接
        
    Returns:
        生成的天氣建議
    """
    try:
        # 檢查運動是否存在
        activity = await db.get(Activities, activity_id)
        if not activity:
            raise HTTPException(
                status_code=404,
                detail=f"找不到運動記錄 {activity_id}"
            )
        
        # 生成建議
        recommendation_engine = RecommendationEngine()
        recommendation = await recommendation_engine.generate_recommendation(
            activity_id, db
        )
        
        if not recommendation:
            raise HTTPException(
                status_code=500,
                detail="無法生成建議，可能缺少天氣數據"
            )
        
        return RecommendationResponse.from_orm(recommendation)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成建議失敗: {str(e)}")
        raise HTTPException(status_code=500, detail="生成建議失敗")


# ==================== 天氣數據更新端點 ====================

@router.post("/update/{location_name}")
async def update_location_weather(
    location_name: str,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    手動更新指定位置的天氣數據
    
    Args:
        location_name: 位置名稱
        db: 數據庫連接
        
    Returns:
        更新結果
    """
    try:
        async with CWBWeatherService() as weather_service:
            # 更新即時天氣
            current = await weather_service.get_current_weather(location_name, db)

            # 更新預報
            forecasts = await weather_service.get_weather_forecast(location_name, db)

            # 更新警告
            alerts = await weather_service.get_weather_alerts(location_name, db)
        
        return {
            "status": "success",
            "message": f"已更新 {location_name} 的天氣數據",
            "current_weather": "updated" if current else "failed",
            "forecasts_count": len(forecasts),
            "alerts_count": len(alerts)
        }
        
    except Exception as e:
        logger.error(f"更新天氣數據失敗: {str(e)}")
        raise HTTPException(status_code=500, detail="更新天氣數據失敗")


@router.post("/update-all")
async def update_all_weather(
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    手動更新所有位置的天氣數據
    
    Args:
        db: 數據庫連接
        
    Returns:
        更新結果
    """
    try:
        async with CWBWeatherService() as weather_service:
            await weather_service.update_all_locations(db)
        
        return {
            "status": "success",
            "message": "已更新所有位置的天氣數據"
        }
        
    except Exception as e:
        logger.error(f"批量更新天氣數據失敗: {str(e)}")
        raise HTTPException(status_code=500, detail="更新天氣數據失敗")


# ==================== 健康檢查 ====================

@router.get("/health")
async def health_check() -> dict:
    """
    天氣服務健康檢查
    
    Returns:
        服務狀態
    """
    return {
        "status": "healthy",
        "service": "weather",
        "timestamp": datetime.now().isoformat()
    }
