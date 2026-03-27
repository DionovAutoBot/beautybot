"""Главная панель администратора + фильтр IsAdmin."""
import logging
from datetime import date, timedelta

from aiogram import Router, F
from aiogram.filters import Filter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import ADMIN_ID
from database.queries import Database
from keyboards.admin_kb import (
    admin_panel_kb, admin_bookings_kb, admin_calendar_kb
)
from texts import ADMIN_PANEL, ADMIN_NO_BOOKINGS
from utils.formatters import format_date, escape_html

logger = logging.getLogger(__name__)
router = Router()


class IsAdmin(Filter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        return event.from_user.id == ADMIN_ID


router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.callback_query(F.data == "admin_panel")
async def show_admin_panel(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    try:
        await callback.message.edit_text(
            text=ADMIN_PANEL, parse_mode="HTML", reply_markup=admin_panel_kb()
        )
    except Exception:
        await callback.message.answer(
            text=ADMIN_PANEL, parse_mode="HTML", reply_markup=admin_panel_kb()
        )


async def _show_bookings(callback: CallbackQuery, db: Database, date_str: str, label: str):
    bookings = await db.get_bookings_for_date(date_str)
    if not bookings:
        text = f"📅 <b>{label}</b>\n\n" + ADMIN_NO_BOOKINGS.format(date=format_date(date_str))
        try:
            await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=admin_panel_kb())
        except Exception:
            await callback.message.answer(text=text, parse_mode="HTML", reply_markup=admin_panel_kb())
        return

    text = f"📅 <b>{label} — {format_date(date_str)}</b>\nЗаписей: {len(bookings)}"
    try:
        await callback.message.edit_text(
            text=text, parse_mode="HTML", reply_markup=admin_bookings_kb(bookings)
        )
    except Exception:
        await callback.message.answer(
            text=text, parse_mode="HTML", reply_markup=admin_bookings_kb(bookings)
        )


@router.callback_query(F.data == "admin_today")
async def admin_today(callback: CallbackQuery, db: Database):
    await callback.answer()
    await _show_bookings(callback, db, date.today().isoformat(), "Сегодня")


@router.callback_query(F.data == "admin_tomorrow")
async def admin_tomorrow(callback: CallbackQuery, db: Database):
    await callback.answer()
    await _show_bookings(callback, db, (date.today() + timedelta(days=1)).isoformat(), "Завтра")


@router.callback_query(F.data == "admin_bookings_date")
async def admin_bookings_date(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    today = date.today()
    await callback.message.edit_text(
        text="📅 Выбери дату для просмотра записей:",
        parse_mode="HTML",
        reply_markup=admin_calendar_kb(today.year, today.month, mode="bookings")
    )


@router.callback_query(F.data.startswith("admin_cal_nav:"))
async def admin_cal_nav(callback: CallbackQuery):
    await callback.answer()
    _, mode, y, m = callback.data.split(":")
    await callback.message.edit_reply_markup(
        reply_markup=admin_calendar_kb(int(y), int(m), mode=mode)
    )


@router.callback_query(F.data.startswith("admin_cal_select:bookings:"))
async def admin_select_date_bookings(callback: CallbackQuery, db: Database):
    await callback.answer()
    date_str = callback.data.split(":")[2]
    await _show_bookings(callback, db, date_str, "Записи")


@router.callback_query(F.data.startswith("admin_booking_detail:"))
async def admin_booking_detail(callback: CallbackQuery, db: Database):
    await callback.answer()
    booking_id = int(callback.data.split(":")[1])
    bk = await db.get_booking_by_id(booking_id)
    if not bk:
        await callback.answer("Запись не найдена", show_alert=True)
        return

    text = (
        f"📋 <b>Запись #{booking_id}</b>\n\n"
        f"📅 {format_date(bk['date'])} в {bk['start_time']}\n"
        f"✂️ {escape_html(bk.get('service_name','?'))}\n"
        f"💰 {bk.get('price','?')}\n"
        f"👤 {escape_html(bk['client_name'])}\n"
        f"📞 {bk['phone']}\n"
        f"💬 {escape_html(bk.get('comment') or 'нет')}\n"
        f"🆔 TG: <code>{bk['user_id']}</code>"
    )
    from keyboards.admin_kb import admin_booking_detail_kb
    try:
        await callback.message.edit_text(
            text=text, parse_mode="HTML",
            reply_markup=admin_booking_detail_kb(booking_id)
        )
    except Exception:
        await callback.message.answer(
            text=text, parse_mode="HTML",
            reply_markup=admin_booking_detail_kb(booking_id)
        )
