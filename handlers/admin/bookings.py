"""Отмена записей администратором."""
import logging

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from config import ADMIN_ID
from database.queries import Database
from keyboards.admin_kb import admin_panel_kb, admin_cancel_confirm_kb
from texts import ADMIN_CANCEL_CONFIRM, ADMIN_BOOKING_CANCELLED_BY_ADMIN
from utils.formatters import format_date, escape_html
from handlers.admin.panel import IsAdmin

logger = logging.getLogger(__name__)
router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.callback_query(F.data.startswith("admin_cancel_confirm:"))
async def admin_cancel_confirm(callback: CallbackQuery, db: Database):
    await callback.answer()
    booking_id = int(callback.data.split(":")[1])
    bk = await db.get_booking_by_id(booking_id)
    if not bk:
        await callback.answer("Запись не найдена", show_alert=True)
        return

    text = ADMIN_CANCEL_CONFIRM.format(
        date=format_date(bk["date"]),
        time=bk["start_time"],
        service=escape_html(bk.get("service_name", "?")),
        name=escape_html(bk["client_name"]),
        phone=bk["phone"]
    )
    try:
        await callback.message.edit_text(
            text=text, parse_mode="HTML",
            reply_markup=admin_cancel_confirm_kb(booking_id)
        )
    except Exception:
        await callback.message.answer(
            text=text, parse_mode="HTML",
            reply_markup=admin_cancel_confirm_kb(booking_id)
        )


@router.callback_query(F.data.startswith("admin_do_cancel:"))
async def admin_do_cancel(callback: CallbackQuery, state: FSMContext, db: Database, bot: Bot, scheduler=None):
    await callback.answer()
    booking_id = int(callback.data.split(":")[1])
    data = await db.cancel_booking(booking_id)

    if not data:
        await callback.message.edit_text("❌ Запись не найдена.", reply_markup=admin_panel_kb())
        return

    # Отменяем напоминание
    if scheduler:
        try:
            scheduler.cancel_reminder(booking_id)
        except Exception as e:
            logger.error(f"Ошибка отмены напоминания: {e}")

    # Уведомляем клиента
    try:
        await bot.send_message(
            chat_id=data["user_id"],
            text=ADMIN_BOOKING_CANCELLED_BY_ADMIN.format(
                date=format_date(data["date"]),
                time=data["start_time"],
                service=escape_html(data.get("service_name", "")),
                name=escape_html(data["client_name"]),
                phone=data["phone"]
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка уведомления клиента: {e}")

    await callback.message.edit_text(
        f"✅ Запись #{booking_id} отменена.",
        reply_markup=admin_panel_kb()
    )
    await state.clear()
    logger.info(f"Администратор отменил запись #{booking_id}")
