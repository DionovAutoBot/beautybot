"""
Планировщик напоминаний (APScheduler).
Напоминание за 24 ч до записи.
"""
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import TIMEZONE
from texts import REMINDER

logger = logging.getLogger(__name__)


class ReminderScheduler:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.tz = ZoneInfo(TIMEZONE)
        self.scheduler = AsyncIOScheduler(
            jobstores={"default": MemoryJobStore()},
            timezone=TIMEZONE
        )

    def start(self):
        self.scheduler.start()
        logger.info("Планировщик запущен")

    def stop(self):
        self.scheduler.shutdown()

    def schedule_reminder(
        self, booking_id: int, user_id: int,
        appt_date: str, appt_time: str,
        service_name: str
    ) -> bool:
        dt = datetime.strptime(f"{appt_date} {appt_time}", "%Y-%m-%d %H:%M").replace(tzinfo=self.tz)
        remind_at = dt - timedelta(hours=24)
        if remind_at <= datetime.now(tz=self.tz):
            return False

        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="❌ Отменить запись", callback_data=f"user_cancel:{booking_id}")
        ]])

        self.cancel_reminder(booking_id)
        self.scheduler.add_job(
            func=self._send,
            trigger="date",
            run_date=remind_at,
            id=f"remind_{booking_id}",
            kwargs={"user_id": user_id, "time": appt_time,
                    "service": service_name, "kb": kb},
            misfire_grace_time=3600
        )
        logger.info(f"Напоминание #{booking_id} запланировано на {remind_at}")
        return True

    def cancel_reminder(self, booking_id: int):
        job_id = f"remind_{booking_id}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)

    async def _send(self, user_id: int, time: str, service: str, kb: InlineKeyboardMarkup):
        try:
            await self.bot.send_message(
                chat_id=user_id,
                text=REMINDER.format(time=time, service=service),
                parse_mode="HTML",
                reply_markup=kb
            )
        except Exception as e:
            logger.error(f"Ошибка отправки напоминания {user_id}: {e}")

    async def restore(self, db):
        """Восстанавливает напоминания из БД при старте."""
        bookings = await db.get_all_active_bookings()
        restored = 0
        for b in bookings:
            if self.schedule_reminder(
                b["id"], b["user_id"], b["date"], b["start_time"], b["service_name"]
            ):
                restored += 1
        logger.info(f"Восстановлено {restored}/{len(bookings)} напоминаний")
