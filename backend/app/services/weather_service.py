"""
中央氣象局 (CWB) 天氣服務模塊
提供天氣數據的獲取、存儲和查詢功能
"""

import asyncio
import logging
import re
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

    STATION_ALIASES = {
        "新竹縣": ("新竹",),
        "苗栗縣": ("苗栗",),
        "彰化縣": ("彰化",),
        "南投縣": ("南投",),
        "雲林縣": ("斗六", "雲林"),
        "嘉義縣": ("嘉義",),
        "屏東縣": ("屏東",),
        "宜蘭縣": ("宜蘭",),
        "花蓮縣": ("花蓮",),
        "台東縣": ("臺東", "台東"),
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化天氣服務
        
        Args:
            api_key: 中央氣象局 API Key，如果為 None 使用 settings.CWB_API_KEY
        """
        self.api_key = api_key or settings.CWB_API_KEY
        self.session: Optional[aiohttp.ClientSession] = None

    @staticmethod
    def _normalize_location_name(location_name: str) -> str:
        return location_name.replace("臺", "台").replace("市", "").replace("縣", "")

    @classmethod
    def _station_matches_location(cls, station_name: str, location_name: str) -> bool:
        normalized_station = cls._normalize_location_name(station_name)
        normalized_location = cls._normalize_location_name(location_name)
        if normalized_location in normalized_station:
            return True
        aliases = cls.STATION_ALIASES.get(location_name, ())
        return any(cls._normalize_location_name(alias) in normalized_station for alias in aliases)

    def _find_forecast_location(self, data: object, location_name: str) -> Optional[Dict]:
        """Find a CWA forecast location across legacy and current response shapes."""
        if isinstance(data, dict):
            candidate_name = data.get("locationName", data.get("LocationName"))
            weather_elements = data.get("weatherElement", data.get("WeatherElement"))
            if (
                isinstance(candidate_name, str)
                and weather_elements
                and self._normalize_location_name(candidate_name)
                == self._normalize_location_name(location_name)
            ):
                return data
            for value in data.values():
                result = self._find_forecast_location(value, location_name)
                if result is not None:
                    return result
        elif isinstance(data, list):
            for value in data:
                result = self._find_forecast_location(value, location_name)
                if result is not None:
                    return result
        return None

    @staticmethod
    def _get_forecast_value(time_period: Dict) -> Optional[str]:
        """Extract a scalar value from legacy or current CWA forecast periods."""
        value = time_period.get("elementValue") or time_period.get("ElementValue")
        if value is None:
            parameter = time_period.get("parameter", time_period.get("Parameter", {}))
            value = parameter.get("parameterName", parameter.get("ParameterName"))
        if isinstance(value, list):
            value = value[0] if value else None
        if isinstance(value, dict):
            value = next((item for item in value.values() if item is not None), None)
        return str(value) if value is not None else None

    @staticmethod
    def _number_or_none(value: object) -> Optional[Decimal]:
        """Convert CWA scalar values to Decimal without treating missing data as zero."""
        if value in (None, "", "-9", "-99", "-990", "-999", "-9999"):
            return None
        try:
            number = Decimal(str(value))
            if number in (Decimal("-9"), Decimal("-99"), Decimal("-990"), Decimal("-999"), Decimal("-9999")):
                return None
            return number
        except Exception:
            return None

    @staticmethod
    def _station_precipitation(weather_elements: Dict) -> Optional[Decimal]:
        """Read precipitation from legacy and current CWA station payloads."""
        precipitation = weather_elements.get("RAIN", weather_elements.get("Precipitation"))
        if precipitation is None:
            now = weather_elements.get("Now", {})
            if isinstance(now, dict):
                precipitation = now.get("Precipitation", now.get("Rainfall"))
        return CWBWeatherService._number_or_none(precipitation)

    @staticmethod
    def _station_visibility(weather_elements: Dict) -> Optional[int]:
        """Convert CWA legacy numeric or current text visibility values to metres."""
        visibility = weather_elements.get("VIS", weather_elements.get("VisibilityDescription"))
        numeric_value = CWBWeatherService._number_or_none(visibility)
        if numeric_value is not None:
            return int(numeric_value)
        if not isinstance(visibility, str):
            return None
        match = re.search(r"\d+(?:\.\d+)?", visibility)
        if match is None:
            return None
        value = Decimal(match.group())
        if "公里" in visibility or "km" in visibility.lower():
            value *= 1000
        return int(value)

    @staticmethod
    def _wind_direction_description(value: Optional[Decimal]) -> Optional[str]:
        if value is None:
            return None
        directions = (
            "北風", "東北風", "東風", "東南風",
            "南風", "西南風", "西風", "西北風",
        )
        return directions[int((float(value) + 22.5) // 45) % 8]
    
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
        cwa_location_name = location_name.replace("台", "臺")
        
        # 調用 API 獲取資料
        params = {"elementName": "TEMP,HUMD,WDSD,PRES,VIS,RH,RAIN"}
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
                station = next(
                    (
                        item for item in stations
                        if self._station_matches_location(
                            item.get("StationName", ""), location_name
                        )
                    ),
                    None,
                )
                if station is None:
                    logger.warning(f"找不到 {location_name} 對應的觀測站")
                    return None
                weather_elements = station["WeatherElement"]

            humidity = self._number_or_none(
                weather_elements.get("HUMD", weather_elements.get("RelativeHumidity"))
            )
            wind_direction = self._number_or_none(
                weather_elements.get("WDIR", weather_elements.get("WindDirection"))
            )
            
            # 創建天氣記錄
            weather_text = weather_elements.get("Weather", weather_elements.get("weather", "未知"))
            if isinstance(weather_text, dict):
                weather_text = weather_text.get("parameterName", weather_text.get("description", "未知"))
            weather_text = str(weather_text or "未知")
            weather_main = "Rain" if any(word in weather_text for word in ("雨", "陣雨", "雷雨")) else (
                "Cloudy" if any(word in weather_text for word in ("雲", "陰")) else "Clear"
            )

            weather = CurrentWeather(
                location_name=location_name,
                latitude=Decimal(str(lat)),
                longitude=Decimal(str(lon)),
                temperature=self._number_or_none(
                    weather_elements.get("TEMP", weather_elements.get("AirTemperature"))
                ) or Decimal("0"),
                humidity=int(humidity) if humidity is not None else 0,
                wind_speed=self._number_or_none(
                    weather_elements.get("WDSD", weather_elements.get("WindSpeed"))
                ) or Decimal("0"),
                wind_direction=int(wind_direction) if wind_direction is not None else None,
                wind_direction_description=self._wind_direction_description(wind_direction),
                pressure=(lambda value: int(value) if value is not None else None)(
                    self._number_or_none(weather_elements.get("PRES", weather_elements.get("AirPressure")))
                ),
                precipitation=self._station_precipitation(weather_elements),
                visibility=self._station_visibility(weather_elements),
                weather_main=weather_main,
                weather_description=weather_text,
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
        cwa_location_name = location_name.replace("台", "臺")
        
        # 調用 API 獲取預報資料
        params = {
            "locationName": cwa_location_name,
            "elementName": "Wx,MaxT,MinT,CI,PoP,Wind"
        }
        data = await self._make_request(self.FORECAST_API, params)
        
        if not data or "records" not in data:
            logger.warning(f"無法獲取 {location_name} 的預報數據")
            return []
        
        forecasts = []
        try:
            location_data = self._find_forecast_location(data["records"], location_name)
            if location_data is None:
                logger.warning(f"找不到 {location_name} 的預報位置")
                return []
            
            # 處理預報時段
            max_temps = {}
            min_temps = {}
            pops = {}
            wind_descriptions = {}
            for weather_element in location_data.get("weatherElement", location_data.get("WeatherElement", [])):
                element_name = weather_element.get("elementName", weather_element.get("ElementName"))
                time_periods = weather_element.get("time", weather_element.get("Time", []))
                if element_name == "MaxT":
                    max_temps = {
                        item.get("startTime", item.get("StartTime")): self._get_forecast_value(item)
                        for item in time_periods
                        if self._get_forecast_value(item) is not None
                    }
                elif element_name == "MinT":
                    min_temps = {
                        item.get("startTime", item.get("StartTime")): self._get_forecast_value(item)
                        for item in time_periods
                        if self._get_forecast_value(item) is not None
                    }
                elif element_name == "PoP":
                    pops = {
                        item.get("startTime", item.get("StartTime")): self._get_forecast_value(item)
                        for item in time_periods
                        if self._get_forecast_value(item) is not None
                    }
                elif element_name == "Wind":
                    wind_descriptions = {
                        item.get("startTime", item.get("StartTime")): self._get_forecast_value(item)
                        for item in time_periods
                        if self._get_forecast_value(item) is not None
                    }
            
            # 創建預報記錄
            for time_str, max_temp in max_temps.items():
                min_temp = min_temps.get(time_str, "0")
                pop = pops.get(time_str, "0")
                wind_description = wind_descriptions.get(time_str)
                
                forecast_time = datetime.fromisoformat(time_str.replace("Z", "+00:00")).replace(tzinfo=None)
                
                forecast = WeatherForecast(
                    location_name=location_name,
                    latitude=Decimal(str(lat)),
                    longitude=Decimal(str(lon)),
                    forecast_time=forecast_time,
                    temperature_max=Decimal(max_temp),
                    temperature_min=Decimal(min_temp),
                    precipitation_probability=int(pop),
                    wind_direction_description=wind_description,
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
