"""
運動天氣建議引擎
根據運動模式和天氣數據生成建議
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models import (
    Activities, ActivityWeatherSnapshots, WeatherRecommendations,
    SportModes, CurrentWeather
)

logger = logging.getLogger(__name__)


class RecommendationLevel(str, Enum):
    """建議等級"""
    SAFE = "safe"
    WARNING = "warning"
    DANGER = "danger"


class WeatherStatus(str, Enum):
    """天氣因素狀態"""
    OPTIMAL = "optimal"
    WARNING = "warning"
    DANGER = "danger"


class RecommendationReason(str, Enum):
    """建議原因"""
    TEMPERATURE_HIGH = "temperature_high"
    TEMPERATURE_LOW = "temperature_low"
    HUMIDITY_HIGH = "humidity_high"
    WIND_SPEED_HIGH = "wind_speed_high"
    PRECIPITATION_HIGH = "precipitation_high"
    VISIBILITY_LOW = "visibility_low"
    UV_INDEX_HIGH = "uv_index_high"
    OPTIMAL_CONDITIONS = "optimal_conditions"


class RecommendationEngine:
    """運動天氣建議引擎"""
    
    def __init__(self):
        """初始化建議引擎"""
        self.suggestions_text = {
            RecommendationReason.TEMPERATURE_HIGH: "溫度過高，容易中暑。建議選擇清晨或傍晚進行運動，並增加水分補充。",
            RecommendationReason.TEMPERATURE_LOW: "溫度過低，容易失溫。建議穿著保暖衣物，進行充分的熱身運動。",
            RecommendationReason.HUMIDITY_HIGH: "濕度過高，身體散熱困難。建議縮短運動時間，增加休息次數。",
            RecommendationReason.WIND_SPEED_HIGH: "風速過大，可能影響運動安全。請謹慎進行戶外運動。",
            RecommendationReason.PRECIPITATION_HIGH: "降雨機率高，路面濕滑。建議穿著防滑鞋具，降低運動強度。",
            RecommendationReason.VISIBILITY_LOW: "能見度低，視線不清。建議佩戴反光裝備，提高警惕。",
            RecommendationReason.UV_INDEX_HIGH: "紫外線指數高，容易曬傷。建議塗抹防曬霜，穿著長袖衣物。",
            RecommendationReason.OPTIMAL_CONDITIONS: "天氣條件良好，適合運動！請享受您的運動時光。"
        }
    
    async def generate_recommendation(
        self,
        activity_id: int,
        db: AsyncSession
    ) -> Optional[WeatherRecommendations]:
        """
        為特定運動生成天氣建議
        
        Args:
            activity_id: 運動記錄 ID
            db: 數據庫會話
            
        Returns:
            生成的建議記錄，或無法生成時返回 None
        """
        try:
            # 1. 獲取運動記錄
            activity = await db.get(Activities, activity_id)
            if not activity:
                logger.warning(f"找不到運動記錄: {activity_id}")
                return None
            
            # 2. 獲取運動模式
            sport_mode = await db.get(SportModes, activity.mode_id)
            if not sport_mode:
                logger.warning(f"找不到運動模式: {activity.mode_id}")
                return None
            
            # 3. 獲取運動期間的天氣快照
            snapshots = await self._get_activity_weather_snapshots(activity_id, db)
            if not snapshots:
                logger.warning(f"找不到運動 {activity_id} 的天氣數據")
                return None
            
            # 4. 計算平均天氣數據
            avg_weather = self._calculate_average_weather(snapshots)
            
            # 5. 評估天氣狀況
            (
                recommendation_level,
                reasons,
                status_dict
            ) = self._evaluate_weather(avg_weather, sport_mode)
            
            # 6. 生成建議文字
            suggestions = self._generate_suggestions(reasons)
            
            # 7. 創建或更新建議記錄
            recommendation = await self._save_recommendation(
                activity_id,
                activity.mode_id,
                recommendation_level,
                reasons,
                suggestions,
                status_dict,
                db
            )
            
            logger.info(
                f"已為運動 {activity_id} 生成 {recommendation_level} 等級的建議"
            )
            return recommendation
            
        except Exception as e:
            logger.error(f"生成建議時發生錯誤: {str(e)}")
            return None
    
    async def _get_activity_weather_snapshots(
        self,
        activity_id: int,
        db: AsyncSession
    ) -> List[ActivityWeatherSnapshots]:
        """獲取運動期間的天氣快照"""
        stmt = select(ActivityWeatherSnapshots).where(
            ActivityWeatherSnapshots.activity_id == activity_id
        ).order_by(ActivityWeatherSnapshots.captured_at)
        
        result = await db.execute(stmt)
        return result.scalars().all()
    
    def _calculate_average_weather(
        self,
        snapshots: List[ActivityWeatherSnapshots]
    ) -> Dict:
        """計算平均天氣數據"""
        if not snapshots:
            return {}
        
        n = len(snapshots)
        return {
            'temperature': sum(s.temperature or 0 for s in snapshots) / n,
            'humidity': sum(s.humidity or 0 for s in snapshots) / n,
            'wind_speed': sum(s.wind_speed or 0 for s in snapshots) / n,
            'precipitation_probability': max(
                s.precipitation_probability or 0 for s in snapshots
            ),
            'visibility': min(s.visibility or 10000 for s in snapshots),
            'uv_index': max(s.uv_index or 0 for s in snapshots),
        }
    
    def _evaluate_weather(
        self,
        avg_weather: Dict,
        sport_mode: SportModes
    ) -> Tuple[RecommendationLevel, List[str], Dict]:
        """
        評估天氣狀況
        
        Returns:
            (推薦等級, 原因列表, 各因素狀態字典)
        """
        reasons = []
        status_dict = {}
        danger_count = 0
        warning_count = 0
        
        # 1. 評估溫度
        temp = avg_weather.get('temperature', 0)
        temp_status, temp_reasons = self._evaluate_temperature(
            temp, sport_mode
        )
        status_dict['temperature_status'] = temp_status
        reasons.extend(temp_reasons)
        if temp_status == WeatherStatus.DANGER:
            danger_count += 1
        elif temp_status == WeatherStatus.WARNING:
            warning_count += 1
        
        # 2. 評估濕度
        humidity = avg_weather.get('humidity', 0)
        humidity_status, humidity_reasons = self._evaluate_humidity(
            humidity, sport_mode
        )
        status_dict['humidity_status'] = humidity_status
        reasons.extend(humidity_reasons)
        if humidity_status == WeatherStatus.DANGER:
            danger_count += 1
        elif humidity_status == WeatherStatus.WARNING:
            warning_count += 1
        
        # 3. 評估風速
        wind_speed = avg_weather.get('wind_speed', 0)
        wind_status, wind_reasons = self._evaluate_wind(wind_speed, sport_mode)
        status_dict['wind_status'] = wind_status
        reasons.extend(wind_reasons)
        if wind_status == WeatherStatus.DANGER:
            danger_count += 1
        elif wind_status == WeatherStatus.WARNING:
            warning_count += 1
        
        # 4. 評估降水
        precip_prob = avg_weather.get('precipitation_probability', 0)
        precip_status, precip_reasons = self._evaluate_precipitation(
            precip_prob, sport_mode
        )
        status_dict['precipitation_status'] = precip_status
        reasons.extend(precip_reasons)
        if precip_status == WeatherStatus.DANGER:
            danger_count += 1
        elif precip_status == WeatherStatus.WARNING:
            warning_count += 1
        
        # 5. 評估能見度
        visibility = avg_weather.get('visibility', 10000)
        visibility_status, visibility_reasons = self._evaluate_visibility(
            visibility, sport_mode
        )
        status_dict['visibility_status'] = visibility_status
        reasons.extend(visibility_reasons)
        if visibility_status == WeatherStatus.DANGER:
            danger_count += 1
        elif visibility_status == WeatherStatus.WARNING:
            warning_count += 1
        
        # 6. 評估紫外線
        uv_index = avg_weather.get('uv_index', 0)
        uv_status, uv_reasons = self._evaluate_uv(uv_index, sport_mode)
        status_dict['uv_status'] = uv_status
        reasons.extend(uv_reasons)
        if uv_status == WeatherStatus.DANGER:
            danger_count += 1
        elif uv_status == WeatherStatus.WARNING:
            warning_count += 1
        
        # 7. 決定建議等級
        if danger_count > 0:
            recommendation_level = RecommendationLevel.DANGER
        elif warning_count > 0:
            recommendation_level = RecommendationLevel.WARNING
        else:
            recommendation_level = RecommendationLevel.SAFE
            if not reasons:
                reasons = [RecommendationReason.OPTIMAL_CONDITIONS.value]
        
        return recommendation_level, reasons, status_dict
    
    def _evaluate_temperature(
        self,
        temperature: float,
        sport_mode: SportModes
    ) -> Tuple[str, List[str]]:
        """評估溫度"""
        reasons = []
        
        # 檢查危險溫度
        if (sport_mode.danger_temp_max and temperature > sport_mode.danger_temp_max) or \
           (sport_mode.danger_temp_min and temperature < sport_mode.danger_temp_min):
            return WeatherStatus.DANGER, [RecommendationReason.TEMPERATURE_HIGH.value if temperature > 30 else RecommendationReason.TEMPERATURE_LOW.value]
        
        # 檢查警告溫度
        if (sport_mode.warning_temp_max and temperature > sport_mode.warning_temp_max) or \
           (sport_mode.warning_temp_min and temperature < sport_mode.warning_temp_min):
            return WeatherStatus.WARNING, [RecommendationReason.TEMPERATURE_HIGH.value if temperature > sport_mode.warning_temp_max else RecommendationReason.TEMPERATURE_LOW.value]
        
        return WeatherStatus.OPTIMAL, []
    
    def _evaluate_humidity(
        self,
        humidity: float,
        sport_mode: SportModes
    ) -> Tuple[str, List[str]]:
        """評估濕度"""
        reasons = []
        
        # 檢查警告濕度
        if sport_mode.warning_humidity_max and humidity > sport_mode.warning_humidity_max:
            return WeatherStatus.WARNING, [RecommendationReason.HUMIDITY_HIGH.value]
        
        return WeatherStatus.OPTIMAL, []
    
    def _evaluate_wind(
        self,
        wind_speed: float,
        sport_mode: SportModes
    ) -> Tuple[str, List[str]]:
        """評估風速"""
        reasons = []
        
        # 檢查危險風速
        if sport_mode.danger_wind_speed_max and wind_speed > sport_mode.danger_wind_speed_max:
            return WeatherStatus.DANGER, [RecommendationReason.WIND_SPEED_HIGH.value]
        
        # 檢查警告風速
        if sport_mode.warning_wind_speed_max and wind_speed > sport_mode.warning_wind_speed_max:
            return WeatherStatus.WARNING, [RecommendationReason.WIND_SPEED_HIGH.value]
        
        return WeatherStatus.OPTIMAL, []
    
    def _evaluate_precipitation(
        self,
        precip_prob: float,
        sport_mode: SportModes
    ) -> Tuple[str, List[str]]:
        """評估降水"""
        reasons = []
        
        # 檢查危險降水
        if sport_mode.danger_precipitation_prob and precip_prob > sport_mode.danger_precipitation_prob:
            return WeatherStatus.DANGER, [RecommendationReason.PRECIPITATION_HIGH.value]
        
        # 檢查警告降水
        if sport_mode.warning_precipitation_prob and precip_prob > sport_mode.warning_precipitation_prob:
            return WeatherStatus.WARNING, [RecommendationReason.PRECIPITATION_HIGH.value]
        
        return WeatherStatus.OPTIMAL, []
    
    def _evaluate_visibility(
        self,
        visibility: float,
        sport_mode: SportModes
    ) -> Tuple[str, List[str]]:
        """評估能見度"""
        reasons = []
        
        # 檢查危險能見度
        if sport_mode.danger_visibility_min and visibility < sport_mode.danger_visibility_min:
            return WeatherStatus.DANGER, [RecommendationReason.VISIBILITY_LOW.value]
        
        return WeatherStatus.OPTIMAL, []
    
    def _evaluate_uv(
        self,
        uv_index: float,
        sport_mode: SportModes
    ) -> Tuple[str, List[str]]:
        """評估紫外線指數"""
        reasons = []
        
        # UV 指數等級：0-2 低, 3-5 中, 6-7 高, 8-10 極高, 11+ 危險
        if uv_index >= 11:
            return WeatherStatus.DANGER, [RecommendationReason.UV_INDEX_HIGH.value]
        elif uv_index >= 8:
            return WeatherStatus.WARNING, [RecommendationReason.UV_INDEX_HIGH.value]
        
        return WeatherStatus.OPTIMAL, []
    
    def _generate_suggestions(self, reasons: List[str]) -> str:
        """根據原因生成建議文字"""
        if not reasons:
            return self.suggestions_text[RecommendationReason.OPTIMAL_CONDITIONS]
        
        suggestions = []
        for reason_str in reasons:
            try:
                reason = RecommendationReason[reason_str.upper()]
                suggestions.append(self.suggestions_text[reason])
            except (KeyError, ValueError):
                pass
        
        return " ".join(suggestions) if suggestions else "建議根據天氣條件調整運動計畫。"
    
    async def _save_recommendation(
        self,
        activity_id: int,
        mode_id: int,
        recommendation_level: RecommendationLevel,
        reasons: List[str],
        suggestions: str,
        status_dict: Dict,
        db: AsyncSession
    ) -> WeatherRecommendations:
        """保存建議到數據庫"""
        
        # 檢查是否已存在建議
        stmt = select(WeatherRecommendations).where(
            WeatherRecommendations.activity_id == activity_id
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            # 更新現有建議
            existing.recommendation_level = recommendation_level
            existing.reasons = reasons
            existing.suggestions = suggestions
            existing.temperature_status = status_dict.get('temperature_status')
            existing.humidity_status = status_dict.get('humidity_status')
            existing.wind_status = status_dict.get('wind_status')
            existing.precipitation_status = status_dict.get('precipitation_status')
            existing.visibility_status = status_dict.get('visibility_status')
            existing.uv_status = status_dict.get('uv_status')
            existing.updated_at = datetime.utcnow()
            recommendation = existing
        else:
            # 創建新建議
            recommendation = WeatherRecommendations(
                activity_id=activity_id,
                mode_id=mode_id,
                recommendation_level=recommendation_level,
                reasons=reasons,
                suggestions=suggestions,
                temperature_status=status_dict.get('temperature_status'),
                humidity_status=status_dict.get('humidity_status'),
                wind_status=status_dict.get('wind_status'),
                precipitation_status=status_dict.get('precipitation_status'),
                visibility_status=status_dict.get('visibility_status'),
                uv_status=status_dict.get('uv_status')
            )
            db.add(recommendation)
        
        await db.commit()
        return recommendation
    
    async def get_recommendation(
        self,
        activity_id: int,
        db: AsyncSession
    ) -> Optional[WeatherRecommendations]:
        """獲取運動的天氣建議"""
        stmt = select(WeatherRecommendations).where(
            WeatherRecommendations.activity_id == activity_id
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
