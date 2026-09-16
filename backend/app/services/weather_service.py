"""
中央氣象局 (CWB) 天氣服務模塊
提供天氣數據的獲取、存儲和查詢功能
"""

import asyncio
import logging
import ssl
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from decimal import Decimal

import aiohttp
import certifi
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CurrentWeather, WeatherForecast, WeatherHistory, WeatherAlerts
from app.config import settings

logger = logging.getLogger(__name__)
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
SSL_CONTEXT.verify_flags &= ~ssl.VERIFY_X509_STRICT


class CWBWeatherService:
    """中央氣象局天氣服務"""
    
    # 中央氣象局 API 端點
    OBSERVATION_API = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0003-001"
    FORECAST_API = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001"
    WARNING_API = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/W-C0033-001"
    
    # 台灣主要城市座標（經度, 緯度）
    MAJOR_CITIES = {
        "台北市": (121.5653, 25.0330),
        "新北市": (121.4624, 25.2048),
        "桃園市": (121.3168, 24.9937),
        "新竹市": (120.9605, 24.8148),
        "新竹縣": (121.0119, 24.8448),
        "苗栗縣": (120.8267, 24.5503),
        "台中市": (120.6724, 24.1694),
        "彰化縣": (120.5054, 24.0804),
        "南投縣": (120.7744, 23.8103),
        "雲林縣": (120.5567, 23.7185),
        "嘉義市": (120.4473, 23.4773),
        "嘉義縣": (120.6515, 23.4636),
        "台南市": (120.2108, 22.9937),
        "高雄市": (120.3113, 22.6228),
        "屏東縣": (120.5954, 22.6799),
        "宜蘭縣": (121.7497, 24.7018),
        "花蓮縣": (121.5090, 23.9727),
        "台東縣": (121.1440, 22.7692),
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化天氣服務
        
        Args:
            api_key: 中央氣象局 API Key，如果為 None 使用 settings.CWB_API_KEY
        """
        self.api_key = api_key or settings.CWB_API_KEY
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """異步上下文管理器入口"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """異步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    async def _make_request(self, url: str, params: Dict) -> Optional[Dict]:
        """
        向中央氣象局 API 發送請求
        
        Args:
            url: API 端點 URL
            params: 請求參數
            
        Returns:
            API 響應數據，失敗返回 None
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            params["Authorization"] = self.api_key
            async with self.session.get(
                url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=10),
                ssl=SSL_CONTEXT,
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    logger.error(f"CWB API 錯誤: {resp.status}")
                    return None
        except asyncio.TimeoutError:
            logger.error("CWB API 請求超時")
            return None
        except Exception as e:
            logger.error(f"CWB API 請求異常: {str(e)}")
            return None
    
    async def get_current_weather(self, location_name: str, db: AsyncSession) -> Optional[CurrentWeather]:
        """
        獲取即時天氣數據
        
        Args:
            location_name: 位置名稱（如 "台北市"）
            db: 數據庫連接
            
        Returns:
            天氣數據模型或 None
        """
        if location_name not in self.MAJOR_CITIES:
            logger.warning(f"不支持的位置: {location_name}")
            return None
        
        lon, lat = self.MAJOR_CITIES[location_name]
        
        # 調用 API 獲取資料
        params = {"locationName": location_name, "elementName": "TEMP,HUMD,WDSD,PRES,VIS,RH"}
        data = await self._make_request(self.OBSERVATION_API, params)
        
        if not data or "records" not in data:
            logger.warning(f"無法獲取 {location_name} 的天氣數據")
            return None
        
        try:
            records = data["records"]
            if records.get("location"):
                location_data = records["location"][0]
                weather_elements = {
                    elem["elementName"]: elem["elementValue"]
                    for elem in location_data["weatherElement"]
                }
            else:
                stations = records.get("Station", [])
                location_key = location_name.replace("台", "臺").replace("市", "")
                station = next(
                    (
                        item for item in stations
                        if location_key in item.get("StationName", "")
                    ),
                    None,
                )
                if station is None:
                    logger.warning(f"找不到 {location_name} 對應的觀測站")
                    return None
                weather_elements = station["WeatherElement"]
            
            # 創建天氣記錄
            weather = CurrentWeather(
                location_name=location_name,
                latitude=Decimal(str(lat)),
                longitude=Decimal(str(lon)),
                temperature=Decimal(
                    weather_elements.get("TEMP", weather_elements.get("AirTemperature", 0))
                ),
                humidity=int(
                    weather_elements.get("HUMD", weather_elements.get("RelativeHumidity", 0))
                ),
                wind_speed=Decimal(
                    weather_elements.get("WDSD", weather_elements.get("WindSpeed", 0))
                ),
                pressure=int(
                    float(weather_elements.get("PRES", weather_elements.get("AirPressure", 0)))
                ),
                visibility=(
                    int(weather_elements["VIS"])
                    if weather_elements.get("VIS")
                    else None
                ),
                weather_main="Clear",  # 需要進一步解析
                weather_description="晴天",
                data_time=datetime.now(),
                fetched_at=datetime.now()
            )
            
            # 保存到數據庫
            db.add(weather)
            await db.commit()
            
            logger.info(f"已更新 {location_name} 的天氣數據")
            return weather
            
        except Exception as e:
            logger.error(f"解析天氣數據失敗: {str(e)}")
            return None
    
    async def get_weather_forecast(self, location_name: str, db: AsyncSession) -> List[WeatherForecast]:
        """
        獲取天氣預報數據
        
        Args:
            location_name: 位置名稱
            db: 數據庫連接
            
        Returns:
            預報數據列表
        """
        if location_name not in self.MAJOR_CITIES:
            logger.warning(f"不支持的位置: {location_name}")
            return []
        
        lon, lat = self.MAJOR_CITIES[location_name]
        
        # 調用 API 獲取預報資料
        params = {
            "locationName": location_name,
            "elementName": "Wx,MaxT,MinT,CI,PoP,Wind"
        }
        data = await self._make_request(self.FORECAST_API, params)
        
        if not data or "records" not in data:
            logger.warning(f"無法獲取 {location_name} 的預報數據")
            return []
        
        forecasts = []
        try:
            records = data["records"]
            locations = records.get("location", [])
            if not locations:
                location_groups = records.get("locations", records.get("Locations", []))
                for group in location_groups:
                    locations.extend(group.get("location", group.get("Location", [])))

            normalized_location = location_name.replace("臺", "台").replace("市", "").replace("縣", "")
            location_data = next(
                (
                    item for item in locations
                    if item.get("locationName", "").replace("臺", "台").replace("市", "").replace("縣", "")
                    == normalized_location
                ),
                None,
            )
            if location_data is None:
                logger.warning(f"找不到 {location_name} 的預報位置")
                return []
            
            # 處理預報時段
            max_temps = {}
            min_temps = {}
            pops = {}
            for weather_element in location_data["weatherElement"]:
                if weather_element["elementName"] == "MaxT":
                    max_temps = {
                        item["startTime"]: item["elementValue"]
                        for item in weather_element["time"]
                    }
                elif weather_element["elementName"] == "MinT":
                    min_temps = {
                        item["startTime"]: item["elementValue"]
                        for item in weather_element["time"]
                    }
                elif weather_element["elementName"] == "PoP":
                    pops = {
                        item["startTime"]: item["elementValue"]
                        for item in weather_element["time"]
                    }
            
            # 創建預報記錄
            for time_str, max_temp in max_temps.items():
                min_temp = min_temps.get(time_str, "0")
                pop = pops.get(time_str, "0")
                
                forecast_time = datetime.fromisoformat(time_str.replace("Z", "+00:00")).replace(tzinfo=None)
                
                forecast = WeatherForecast(
                    location_name=location_name,
                    latitude=Decimal(str(lat)),
                    longitude=Decimal(str(lon)),
                    forecast_time=forecast_time,
                    temperature_max=Decimal(max_temp),
                    temperature_min=Decimal(min_temp),
                    precipitation_probability=int(pop),
                    weather_main="Forecast",
                    weather_description=f"最高 {max_temp}°C，最低 {min_temp}°C",
                    forecast_issued_at=datetime.now(),
                    fetched_at=datetime.now()
                )
                forecasts.append(forecast)
            
            # 批量保存到數據庫
            db.add_all(forecasts)
            await db.commit()
            
            logger.info(f"已更新 {location_name} 的預報數據，共 {len(forecasts)} 筆")
            return forecasts
            
        except Exception as e:
            logger.error(f"解析預報數據失敗: {str(e)}")
            return []
    
    async def get_weather_alerts(self, location_name: str, db: AsyncSession) -> List[WeatherAlerts]:
        """
        獲取氣象警告信息
        
        Args:
            location_name: 位置名稱
            db: 數據庫連接
            
        Returns:
            警告數據列表
        """
        if location_name not in self.MAJOR_CITIES:
            logger.warning(f"不支持的位置: {location_name}")
            return []
        
        lon, lat = self.MAJOR_CITIES[location_name]
        
        # 調用 API 獲取警告資料
        data = await self._make_request(self.WARNING_API, {})
        
        if not data or "records" not in data:
            logger.info(f"無警告信息 - {location_name}")
            return []
        
        alerts = []
        try:
            for warning_data in data["records"].get("warning", []):
                # 檢查警告是否適用於該位置
                if location_name in warning_data.get("areaDesc", ""):
                    alert = WeatherAlerts(
                        location_name=location_name,
                        latitude=Decimal(str(lat)),
                        longitude=Decimal(str(lon)),
                        alert_type=warning_data.get("phenomenon", "Unknown"),
                        alert_level=warning_data.get("severity", "Normal"),
                        alert_description=warning_data.get("description", ""),
                        alert_issued_at=datetime.fromisoformat(
                            warning_data.get("issueTime", datetime.now().isoformat())
                        ),
                        alert_expires_at=datetime.fromisoformat(
                            warning_data.get("expireTime", (datetime.now() + timedelta(hours=6)).isoformat())
                        ),
                        is_active=True,
                        created_at=datetime.now()
                    )
                    alerts.append(alert)
            
            if alerts:
                db.add_all(alerts)
                await db.commit()
                logger.info(f"已更新 {location_name} 的警告信息，共 {len(alerts)} 筆")
            
            return alerts
            
        except Exception as e:
            logger.error(f"解析警告數據失敗: {str(e)}")
            return []
    
    async def update_all_locations(self, db: AsyncSession) -> None:
        """
        更新所有主要城市的天氣數據
        
        Args:
            db: 數據庫連接
        """
        logger.info("開始更新所有位置的天氣數據...")
        
        for location_name in self.MAJOR_CITIES.keys():
            try:
                await self.get_current_weather(location_name, db)
                await self.get_weather_forecast(location_name, db)
                await self.get_weather_alerts(location_name, db)
                
                # 避免頻繁請求
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"更新 {location_name} 失敗: {str(e)}")
                continue
        
        logger.info("天氣數據更新完成")
    
    async def get_latest_weather(self, location_name: str, db: AsyncSession) -> Optional[CurrentWeather]:
        """
        從數據庫獲取最新天氣數據
        
        Args:
            location_name: 位置名稱
            db: 數據庫連接
            
        Returns:
            最新天氣數據或 None
        """
        stmt = select(CurrentWeather).where(
            CurrentWeather.location_name == location_name
        ).order_by(desc(CurrentWeather.fetched_at)).limit(1)
        
        result = await db.execute(stmt)
        return result.scalars().first()
    
    async def get_forecast_by_location(self, location_name: str, days: int = 7, 
                                      db: AsyncSession = None) -> List[WeatherForecast]:
        """
        獲取指定位置的預報數據
        
        Args:
            location_name: 位置名稱
            days: 預報天數
            db: 數據庫連接
            
        Returns:
            預報數據列表
        """
        if not db:
            return []
        
        future_date = datetime.now() + timedelta(days=days)
        
        stmt = select(WeatherForecast).where(
            and_(
                WeatherForecast.location_name == location_name,
                WeatherForecast.forecast_time <= future_date
            )
        ).order_by(WeatherForecast.forecast_time)
        
        result = await db.execute(stmt)
        return result.scalars().all()
    
    async def get_active_alerts(self, location_name: str, db: AsyncSession) -> List[WeatherAlerts]:
        """
        獲取指定位置的活躍警告
        
        Args:
            location_name: 位置名稱
            db: 數據庫連接
            
        Returns:
            活躍警告列表
        """
        stmt = select(WeatherAlerts).where(
            and_(
                WeatherAlerts.location_name == location_name,
                WeatherAlerts.is_active == True
            )
        ).order_by(desc(WeatherAlerts.alert_issued_at))
        
        result = await db.execute(stmt)
        return result.scalars().all()
