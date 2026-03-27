"""
bot.py — точка входа бота записи в салон красоты.
Используем ту же логику прокси что в MusicMove (работает с VPN).
"""
import asyncio
import logging
import os
import sys
import requests
from logging.handlers import RotatingFileHandler

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import TOKEN, DB_PATH, LOG_FILE
from database.queries import Database
from middlewares.stale_callback import StaleCallbackMiddleware
from middlewares.subscription import SubscriptionMiddleware
from utils.scheduler import ReminderScheduler

from handlers.user.start import router as start_router
from handlers.user.booking import router as booking_router
from handlers.user.cancel import router as cancel_router
from handlers.admin.panel import router as admin_panel_router
from handlers.admin.slots import router as admin_slots_router
from handlers.admin.bookings import router as admin_bookings_router


def get_system_proxy() -> str | None:
    """Возвращает системный прокси от VPN или None."""
    try:
        proxies = requests.utils.get_environ_proxies("https://api.telegram.org")
        return proxies.get("https") or proxies.get("http")
    except Exception:
        return None


def setup_logging():
    fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    fh = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter(fmt, datefmt))
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter(fmt, datefmt))
    logging.basicConfig(level=logging.INFO, handlers=[fh, ch])
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)


async def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Запуск бота записи в салон...")

    # Дебаг: покажем токен (первые 10 символов) и прокси
    logger.info(f"Токен: {TOKEN[:10]}..." if TOKEN else "ТОКЕН НЕ ЗАДАН!")

    # Прокси: сначала из .env, потом системный (VPN), потом без
    telegram_proxy = os.getenv("TELEGRAM_PROXY", "").strip()
    if not telegram_proxy:
        system_proxy = get_system_proxy()
        if system_proxy:
            telegram_proxy = system_proxy
            logger.info(f"Обнаружен системный прокси: {telegram_proxy}")

    # Сессия с таймаутом 120 (int, не ClientTimeout!)
    if telegram_proxy and telegram_proxy.startswith(("http://", "https://", "socks5://")):
        session = AiohttpSession(proxy=telegram_proxy, timeout=120)
        logger.info(f"Используем прокси: {telegram_proxy}")
    else:
        session = AiohttpSession(timeout=120)
        logger.info("Работаем без прокси (через VPN/напрямую)")

    # БД
    db = Database(DB_PATH)
    await db.init()
    logger.info("База данных готова")

    # Бот с кастомной сессией
    bot = Bot(
        token=TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        session=session,
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Планировщик
    scheduler = ReminderScheduler(bot)
    scheduler.start()
    await scheduler.restore(db)

    # Зависимости
    dp.workflow_data.update(db=db, scheduler=scheduler)

    # Middleware
    dp.update.outer_middleware(SubscriptionMiddleware())
    dp.callback_query.middleware(StaleCallbackMiddleware())

    # Роутеры: admin первыми (с фильтром IsAdmin)
    dp.include_router(admin_panel_router)
    dp.include_router(admin_slots_router)
    dp.include_router(admin_bookings_router)
    dp.include_router(start_router)
    dp.include_router(booking_router)
    dp.include_router(cancel_router)

    logger.info("Бот запущен, начинаем polling...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.stop()
        await bot.session.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    asyncio.run(main())
