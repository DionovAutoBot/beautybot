"""
Отмена записи пользователем + статичные разделы (прайс, контакты).
"""
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from config import ADMIN_ID, TIMEZONE, SALON_NAME, SALON_ADDRESS, SALON_PHONE, SALON_WORK_HOURS, SALON_ADMIN_USERNAME
from database.queries import Database
from keyboards.user_kb import (
    confirm_cancel_kb, back_to_menu_kb, main_menu_kb, categories_kb
)
from texts import (
    CANCEL_CONFIRM, CANCEL_WARNING_24H, CANCEL_SUCCESS, CANCEL_NOT_FOUND,
    ADMIN_BOOKING_CANCELLED_BY_USER, CONTACTS, PRICELIST_HEADER, PRICELIST_FOOTER
)
from utils.formatters import format_date, escape_html

logger = logging.getLogger(__name__)
router = Router()


# ── ОТМЕНА ЗАПИСИ ────────────────────────────────────────────

@router.callback_query(F.data.startswith("user_cancel:"))
async def initiate_cancel(callback: CallbackQuery, db: Database):
    await callback.answer()
    booking_id = int(callback.data.split(":")[1])
    booking = await db.get_booking_by_id(booking_id)

    if not booking or booking["user_id"] != callback.from_user.id:
        try:
            await callback.message.edit_text(CANCEL_NOT_FOUND, reply_markup=back_to_menu_kb())
        except Exception:
            await callback.message.answer(CANCEL_NOT_FOUND, reply_markup=back_to_menu_kb())
        return

    # Проверяем 24 часа
    appt_dt = datetime.strptime(
        f"{booking['date']} {booking['start_time']}", "%Y-%m-%d %H:%M"
    ).replace(tzinfo=ZoneInfo(TIMEZONE))
    warning = ""
    if appt_dt - datetime.now(tz=ZoneInfo(TIMEZONE)) < timedelta(hours=24):
        warning = CANCEL_WARNING_24H

    text = CANCEL_CONFIRM.format(
        date=format_date(booking["date"]),
        time=booking["start_time"],
        service=escape_html(booking.get("service_name", "Услуга")),
        warning=warning
    )
    try:
        await callback.message.edit_text(
            text=text, parse_mode="HTML",
            reply_markup=confirm_cancel_kb(booking_id)
        )
    except Exception:
        await callback.message.answer(
            text=text, parse_mode="HTML",
            reply_markup=confirm_cancel_kb(booking_id)
        )


@router.callback_query(F.data.startswith("do_cancel:"))
async def do_cancel(callback: CallbackQuery, state: FSMContext, db: Database, bot: Bot, scheduler=None):
    await callback.answer()
    booking_id = int(callback.data.split(":")[1])
    data = await db.cancel_booking(booking_id)

    if not data:
        await callback.message.edit_text("❌ Запись не найдена.", reply_markup=back_to_menu_kb())
        return

    # Отменяем напоминание
    if scheduler:
        try:
            scheduler.cancel_reminder(booking_id)
        except Exception as e:
            logger.error(f"Ошибка отмены напоминания: {e}")

    # Уведомление администратору
    try:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=ADMIN_BOOKING_CANCELLED_BY_USER.format(
                date=format_date(data["date"]),
                time=data["start_time"],
                service=escape_html(data.get("service_name", "")),
                name=escape_html(data["client_name"]),
                phone=data["phone"],
                user_id=data["user_id"]
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка уведомления администратора об отмене: {e}")

    try:
        await callback.message.edit_text(
            text=CANCEL_SUCCESS.format(
                date=format_date(data["date"]),
                time=data["start_time"],
                service=escape_html(data.get("service_name", "Услуга"))
            ),
            parse_mode="HTML",
            reply_markup=main_menu_kb()
        )
    except Exception:
        await callback.message.answer(
            text=CANCEL_SUCCESS.format(
                date=format_date(data["date"]),
                time=data["start_time"],
                service=escape_html(data.get("service_name", "Услуга"))
            ),
            parse_mode="HTML",
            reply_markup=main_menu_kb()
        )

    await state.clear()
    logger.info(f"Запись #{booking_id} отменена пользователем {data['user_id']}")


# ── ПРАЙС ─────────────────────────────────────────────────────

@router.callback_query(F.data == "pricelist")
async def show_pricelist(callback: CallbackQuery, db: Database):
    await callback.answer()
    services = await db.get_all_active_services()

    # Группируем по категориям
    by_cat: dict[str, list] = {}
    for s in services:
        cat = f"{s.get('emoji','💅')} {s.get('category_name','Услуги')}"
        by_cat.setdefault(cat, []).append(s)

    lines = [PRICELIST_HEADER]
    for cat, items in by_cat.items():
        lines.append(f"\n<b>{cat}</b>")
        for s in items:
            lines.append(f"• {s['name']} — <b>{s['price']}</b> ({s['duration_minutes']} мин)")
    lines.append(f"\n{PRICELIST_FOOTER}")

    text = "\n".join(lines)
    try:
        await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=back_to_menu_kb())
    except Exception:
        await callback.message.answer(text=text, parse_mode="HTML", reply_markup=back_to_menu_kb())


# ── КОНТАКТЫ ──────────────────────────────────────────────────

@router.callback_query(F.data == "contacts")
async def show_contacts(callback: CallbackQuery):
    await callback.answer()
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(
        text="💬 Написать мастеру",
        url=f"https://t.me/{SALON_ADMIN_USERNAME.lstrip('@')}"
    ))
    b.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))

    text = CONTACTS
    try:
        await callback.message.edit_text(
            text=text, parse_mode="HTML", reply_markup=b.as_markup(),
            disable_web_page_preview=True
        )
    except Exception:
        await callback.message.answer(
            text=text, parse_mode="HTML", reply_markup=b.as_markup()
        )
