"""
定時任務配置
使用 APScheduler 定時更新天氣數據
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from app.database import get_db_session
from app.services.weather_service import CWBWeatherService
from app.services.recommendation_engine import RecommendationEngine

logger = logging.getLogger(__name__)


class SchedulerManager:
    """定時任務管理器"""
    
    _instance: Optional['SchedulerManager'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SchedulerManager, cls).__new__(cls)
            cls._instance.scheduler = None
        return cls._instance
    
    def __init__(self):
        if self.scheduler is None:
            self.scheduler = AsyncIOScheduler()
    
    def start(self):
        """啟動定時任務調度器"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("定時任務調度器已啟動")
    
    def stop(self):
        """停止定時任務調度器"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("定時任務調度器已停止")
    
    def get_scheduler(self) -> AsyncIOScheduler:
        """獲取調度器實例"""
        return self.scheduler


async def update_weather_data():
    """
    定時更新天氣數據任務
    每 30 分鐘執行一次
    """
    logger.info("開始定時更新天氣數據...")
    
    try:
        async with get_db_session() as db:
            async with CWBWeatherService() as weather_service:
                await weather_service.update_all_locations(db)
            logger.info("天氣數據更新完成")
    except Exception as e:
        logger.error(f"天氣數據更新失敗: {str(e)}")


async def clean_old_weather_data():
    """
    清理舊的天氣數據任務
    每天凌晨 2:00 執行一次
    """
    logger.info("開始清理舊天氣數據...")
    
    try:
        async with get_db_session() as db:
            from sqlalchemy import delete, and_
            from app.models import CurrentWeather, WeatherForecast
            
            # 刪除 7 天前的即時天氣數據
            old_date = datetime.now() - timedelta(days=7)
            stmt = delete(CurrentWeather).where(CurrentWeather.fetched_at < old_date)
            await db.execute(stmt)
            
            # 刪除已過期的預報數據
            stmt = delete(WeatherForecast).where(WeatherForecast.forecast_time < datetime.now())
            await db.execute(stmt)
            
            await db.commit()
            logger.info("舊天氣數據清理完成")
    except Exception as e:
        logger.error(f"清理舊天氣數據失敗: {str(e)}")


async def check_weather_alerts():
    """
    檢查氣象警告任務
    每 15 分鐘執行一次
    """
    logger.info("開始檢查氣象警告...")
    
    try:
        async with get_db_session() as db:
            from sqlalchemy import select, and_
            from app.models import WeatherAlerts
            
            # 查詢活躍警告
            stmt = select(WeatherAlerts).where(
                and_(
                    WeatherAlerts.is_active == True,
                    WeatherAlerts.alert_expires_at > datetime.now()
                )
            )
            result = await db.execute(stmt)
            alerts = result.scalars().all()
            
            logger.info(f"發現 {len(alerts)} 個活躍警告")
            
            # TODO: 發送推送通知給相關用戶
            # 這裡可以集成推送服務，如 Firebase Cloud Messaging
            
    except Exception as e:
        logger.error(f"檢查氣象警告失敗: {str(e)}")


async def generate_activity_recommendations():
    """
    生成運動天氣建議任務
    每 1 小時執行一次
    """
    logger.info("開始生成運動天氣建議...")
    
    try:
        async with get_db_session() as db:
            from sqlalchemy import select, and_
            from app.models import Activities
            
            # 查詢最近 24 小時內完成的運動（還沒有建議的）
            yesterday = datetime.now() - timedelta(days=1)
            stmt = select(Activities).where(
                and_(
                    Activities.created_at >= yesterday,
                    Activities.status == 'completed'
                )
            )
            result = await db.execute(stmt)
            activities = result.scalars().all()
            
            recommendation_engine = RecommendationEngine()
            
            for activity in activities:
                try:
                    await recommendation_engine.generate_recommendation(activity.id, db)
                except Exception as e:
                    logger.error(f"為活動 {activity.id} 生成建議失敗: {str(e)}")
            
            logger.info(f"已為 {len(activities)} 個運動生成建議")
            
    except Exception as e:
        logger.error(f"生成運動建議失敗: {str(e)}")


async def cleanup_expired_alerts():
    """
    清理過期警告任務
    每小時執行一次
    """
    logger.info("開始清理過期警告...")
    
    try:
        async with get_db_session() as db:
            from sqlalchemy import update
            from app.models import WeatherAlerts
            
            # 將過期的警告標記為非活躍
            stmt = update(WeatherAlerts).where(
                WeatherAlerts.alert_expires_at <= datetime.now()
            ).values(is_active=False)
            
            result = await db.execute(stmt)
            await db.commit()
            
            logger.info(f"已清理 {result.rowcount} 個過期警告")
            
    except Exception as e:
        logger.error(f"清理過期警告失敗: {str(e)}")


def configure_scheduler():
    """
    配置所有定時任務
    """
    scheduler_manager = SchedulerManager()
    scheduler = scheduler_manager.get_scheduler()
    
    # 1. 每 30 分鐘更新一次天氣數據
    scheduler.add_job(
        update_weather_data,
        trigger=IntervalTrigger(minutes=30),
        id='update_weather_data',
        name='更新天氣數據',
        replace_existing=True,
        misfire_grace_time=600  # 允許 10 分鐘的延遲
    )
    
    # 2. 每天凌晨 2:00 清理舊數據
    scheduler.add_job(
        clean_old_weather_data,
        trigger=CronTrigger(hour=2, minute=0),
        id='clean_old_weather_data',
        name='清理舊天氣數據',
        replace_existing=True,
        misfire_grace_time=600
    )
    
    # 3. 每 15 分鐘檢查一次氣象警告
    scheduler.add_job(
        check_weather_alerts,
        trigger=IntervalTrigger(minutes=15),
        id='check_weather_alerts',
        name='檢查氣象警告',
        replace_existing=True,
        misfire_grace_time=600
    )
    
    # 4. 每小時生成一次運動建議
    scheduler.add_job(
        generate_activity_recommendations,
        trigger=IntervalTrigger(hours=1),
        id='generate_activity_recommendations',
        name='生成運動建議',
        replace_existing=True,
        misfire_grace_time=600
    )
    
    # 5. 每小時清理一次過期警告
    scheduler.add_job(
        cleanup_expired_alerts,
        trigger=IntervalTrigger(hours=1),
        id='cleanup_expired_alerts',
        name='清理過期警告',
        replace_existing=True,
        misfire_grace_time=600
    )
    
    logger.info("定時任務配置完成，共 5 個任務")
    logger.info("任務列表:")
    logger.info("  1. 更新天氣數據 - 每 30 分鐘")
    logger.info("  2. 清理舊天氣數據 - 每天凌晨 2:00")
    logger.info("  3. 檢查氣象警告 - 每 15 分鐘")
    logger.info("  4. 生成運動建議 - 每小時")
    logger.info("  5. 清理過期警告 - 每小時")


def get_scheduler_manager() -> SchedulerManager:
    """獲取調度器管理器實例"""
    return SchedulerManager()
