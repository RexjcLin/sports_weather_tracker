"""
天氣數據 Schema 定義
使用 Pydantic 進行數據驗證和序列化
"""

from typing import List, Optional
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, validator


# ==================== 即時天氣 Schema ====================

class CurrentWeatherBase(BaseModel):
    """即時天氣基礎 Schema"""
    location_name: str = Field(..., description="位置名稱")
    latitude: Decimal = Field(..., description="緯度")
    longitude: Decimal = Field(..., description="經度")
    temperature: Decimal = Field(..., description="溫度 (°C)")
    humidity: int = Field(..., ge=0, le=100, description="濕度 (%)")
    wind_speed: Decimal = Field(..., ge=0, description="風速 (m/s)")
    wind_direction: Optional[int] = Field(None, description="風向角度 (0-360度)")
    wind_direction_description: Optional[str] = Field(
        None, description="風向文字描述"
    )
    pressure: int = Field(..., description="氣壓 (hPa)")
    visibility: Optional[int] = Field(None, description="能見度 (公尺)")
    weather_main: str = Field(..., description="天氣主分類")
    weather_description: str = Field(..., description="天氣描述")


class CurrentWeatherCreate(CurrentWeatherBase):
    """創建即時天氣 Schema"""
    pass


class CurrentWeatherResponse(CurrentWeatherBase):
    """即時天氣響應 Schema"""
    id: int
    data_time: datetime = Field(..., description="數據時間")
    fetched_at: datetime = Field(..., description="獲取時間")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "location_name": "台北市",
                "latitude": 25.0330,
                "longitude": 121.5653,
                "temperature": 28.5,
                "humidity": 75,
                "wind_speed": 3.2,
                "pressure": 1013,
                "visibility": 10000,
                "weather_main": "Partly Cloudy",
                "weather_description": "多雲",
                "data_time": "2024-09-10T12:00:00",
                "fetched_at": "2024-09-10T12:05:00"
            }
        }


# ==================== 天氣預報 Schema ====================

class WeatherForecastBase(BaseModel):
    """天氣預報基礎 Schema"""
    location_name: str = Field(..., description="位置名稱")
    latitude: Decimal = Field(..., description="緯度")
    longitude: Decimal = Field(..., description="經度")
    forecast_time: datetime = Field(..., description="預報時間")
    temperature_max: Decimal = Field(..., description="最高溫度 (°C)")
    temperature_min: Decimal = Field(..., description="最低溫度 (°C)")
    precipitation_probability: int = Field(
        ..., ge=0, le=100, description="降水機率 (%)"
    )
    wind_direction: Optional[int] = Field(None, description="風向角度 (0-360度)")
    wind_direction_description: Optional[str] = Field(None, description="風向文字描述")
    weather_main: str = Field(..., description="天氣主分類")
    weather_description: str = Field(..., description="天氣描述")


class WeatherForecastCreate(WeatherForecastBase):
    """創建天氣預報 Schema"""
    pass


class WeatherForecastResponse(WeatherForecastBase):
    """天氣預報響應 Schema"""
    id: int
    forecast_issued_at: datetime = Field(..., description="預報發布時間")
    fetched_at: datetime = Field(..., description="獲取時間")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "location_name": "台北市",
                "latitude": 25.0330,
                "longitude": 121.5653,
                "forecast_time": "2024-09-11T12:00:00",
                "temperature_max": 32.0,
                "temperature_min": 26.0,
                "precipitation_probability": 40,
                "weather_main": "Partly Cloudy",
                "weather_description": "多雲時晴",
                "forecast_issued_at": "2024-09-10T06:00:00",
                "fetched_at": "2024-09-10T06:05:00"
            }
        }


# ==================== 氣象警告 Schema ====================

class WeatherAlertsBase(BaseModel):
    """氣象警告基礎 Schema"""
    location_name: str = Field(..., description="位置名稱")
    latitude: Decimal = Field(..., description="緯度")
    longitude: Decimal = Field(..., description="經度")
    alert_type: str = Field(..., description="警告類型 (如: 豪雨, 寒流)")
    alert_level: str = Field(
        ..., description="警告等級 (Normal/Warning/Severe)"
    )
    alert_description: str = Field(..., description="警告詳細描述")
    alert_expires_at: datetime = Field(..., description="警告過期時間")


class WeatherAlertsCreate(WeatherAlertsBase):
    """創建氣象警告 Schema"""
    pass


class WeatherAlertsResponse(WeatherAlertsBase):
    """氣象警告響應 Schema"""
    id: int
    alert_issued_at: datetime = Field(..., description="警告發布時間")
    is_active: bool = Field(..., description="是否活躍")
    created_at: datetime = Field(..., description="創建時間")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "location_name": "台北市",
                "latitude": 25.0330,
                "longitude": 121.5653,
                "alert_type": "豪雨特報",
                "alert_level": "Severe",
                "alert_description": "北部地區即將有豪雨，請注意防雨。",
                "alert_issued_at": "2024-09-10T15:00:00",
                "alert_expires_at": "2024-09-10T21:00:00",
                "is_active": True,
                "created_at": "2024-09-10T15:05:00"
            }
        }


# ==================== 天氣建議 Schema ====================

class RecommendationBase(BaseModel):
    """天氣建議基礎 Schema"""
    activity_id: int = Field(..., description="運動記錄 ID")
    mode_id: int = Field(..., description="運動模式 ID")
    recommendation_level: str = Field(
        ..., description="建議等級 (safe/warning/danger)"
    )
    reasons: List[str] = Field(..., description="建議原因列表")
    suggestions: str = Field(..., description="詳細建議文字")


class RecommendationResponse(RecommendationBase):
    """天氣建議響應 Schema"""
    id: int
    temperature_status: Optional[str] = Field(None, description="溫度狀態")
    humidity_status: Optional[str] = Field(None, description="濕度狀態")
    wind_status: Optional[str] = Field(None, description="風速狀態")
    precipitation_status: Optional[str] = Field(None, description="降水狀態")
    visibility_status: Optional[str] = Field(None, description="能見度狀態")
    uv_status: Optional[str] = Field(None, description="紫外線狀態")
    created_at: datetime = Field(..., description="創建時間")
    updated_at: datetime = Field(..., description="更新時間")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "activity_id": 1,
                "mode_id": 1,
                "recommendation_level": "warning",
                "reasons": ["temperature_high", "humidity_high"],
                "suggestions": "溫度過高，容易中暑。建議選擇清晨或傍晚進行運動。濕度過高，身體散熱困難。建議縮短運動時間。",
                "temperature_status": "warning",
                "humidity_status": "warning",
                "wind_status": "optimal",
                "precipitation_status": "optimal",
                "visibility_status": "optimal",
                "uv_status": "optimal",
                "created_at": "2024-09-10T12:00:00",
                "updated_at": "2024-09-10T12:00:00"
            }
        }


# ==================== 批量請求 Schema ====================

class WeatherUpdateRequest(BaseModel):
    """天氣數據更新請求"""
    location_names: List[str] = Field(
        ..., description="要更新的位置列表"
    )
    update_type: str = Field(
        default="all",
        description="更新類型 (all/current/forecast/alerts)"
    )


class LocationCoordinates(BaseModel):
    """位置座標 Schema"""
    location_name: str = Field(..., description="位置名稱")
    latitude: Decimal = Field(..., description="緯度")
    longitude: Decimal = Field(..., description="經度")
    
    class Config:
        json_schema_extra = {
            "example": {
                "location_name": "台北市",
                "latitude": 25.0330,
                "longitude": 121.5653
            }
        }


# ==================== 統計 Schema ====================

class WeatherStatistics(BaseModel):
    """天氣統計 Schema"""
    location_name: str = Field(..., description="位置名稱")
    avg_temperature: Decimal = Field(..., description="平均溫度")
    max_temperature: Decimal = Field(..., description="最高溫度")
    min_temperature: Decimal = Field(..., description="最低溫度")
    avg_humidity: Decimal = Field(..., description="平均濕度")
    max_wind_speed: Decimal = Field(..., description="最大風速")
    data_points: int = Field(..., description="數據點數量")
    period_start: datetime = Field(..., description="統計週期開始")
    period_end: datetime = Field(..., description="統計週期結束")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "location_name": "台北市",
                "avg_temperature": 27.5,
                "max_temperature": 32.0,
                "min_temperature": 24.0,
                "avg_humidity": 75,
                "max_wind_speed": 5.2,
                "data_points": 24,
                "period_start": "2024-09-10T00:00:00",
                "period_end": "2024-09-11T00:00:00"
            }
        }


# ==================== 錯誤響應 Schema ====================

class ErrorResponse(BaseModel):
    """錯誤響應 Schema"""
    status_code: int = Field(..., description="HTTP 狀態碼")
    message: str = Field(..., description="錯誤信息")
    timestamp: datetime = Field(..., description="錯誤發生時間")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status_code": 404,
                "message": "找不到台北市的天氣數據",
                "timestamp": "2024-09-10T12:00:00"
            }
        }


# ==================== 成功響應 Wrapper ====================

class SuccessResponse(BaseModel):
    """成功響應 Wrapper"""
    status: str = Field(default="success", description="狀態")
    message: str = Field(..., description="成功信息")
    timestamp: datetime = Field(..., description="響應時間")
    data: Optional[dict] = Field(None, description="響應數據")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "數據已成功更新",
                "timestamp": "2024-09-10T12:00:00",
                "data": {
                    "location_name": "台北市",
                    "updated_items": 3
                }
            }
        }


# ==================== 批量響應 Schema ====================

class BatchWeatherResponse(BaseModel):
    """批量天氣響應 Schema"""
    total_locations: int = Field(..., description="總位置數")
    successful: int = Field(..., description="成功更新數")
    failed: int = Field(..., description="失敗更新數")
    updated_at: datetime = Field(..., description="更新時間")
    locations: List[dict] = Field(..., description="各位置更新結果")
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_locations": 18,
                "successful": 18,
                "failed": 0,
                "updated_at": "2024-09-10T12:00:00",
                "locations": [
                    {
                        "location_name": "台北市",
                        "status": "success",
                        "weather_updated": True,
                        "forecast_count": 8,
                        "alerts_count": 0
                    }
                ]
            }
        }
