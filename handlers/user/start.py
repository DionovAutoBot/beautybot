"""
/start, главное меню, проверка подписки, мои записи.
"""
import logging
from datetime import date as date_type

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from config import ADMIN_ID
from database.queries import Database
from keyboards.user_kb import main_menu_kb, back_to_menu_kb, cancel_booking_kb
from keyboards.admin_kb import admin_panel_kb
from middlewares.subscription import (
    is_subscribed, subscription_kb, CHECK_SUB_CALLBACK
)
from texts import (
    WELCOME, WELCOME_WITH_BOOKING, SUBSCRIPTION_NOT_FOUND
)
from utils.formatters import format_date, format_time, escape_html

logger = logging.getLogger(__name__)
router = Router()


async def show_main_menu(target, db: Database, state: FSMContext):
    """Показывает главное меню с учётом активной записи."""
    await state.clear()
    if isinstance(target, CallbackQuery):
        user_id = target.from_user.id
        send = target.message.answer
        try_edit = target.message.edit_text
    else:
        user_id = target.from_user.id
        send = target.answer
        try_edit = None

    booking = await db.get_active_booking(user_id)
    if booking:
        text = WELCOME_WITH_BOOKING.format(
            date=format_date(booking["date"]),
            time=format_time(booking["start_time"]),
            service=escape_html(booking.get("service_name") or "Услуга")
        )
    else:
        text = WELCOME

    kb = main_menu_kb(has_booking=bool(booking))

    if try_edit:
        try:
            await try_edit(text=text, parse_mode="HTML", reply_markup=kb)
            return
        except Exception:
            pass
    await send(text=text, parse_mode="HTML", reply_markup=kb)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot, db: Database):
    await state.clear()
    await db.upsert_user(
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.first_name or ""
    )

    # Проверяем подписку — показываем кнопку если нет
    from config import CHANNEL_ID
    if CHANNEL_ID and not await is_subscribed(bot, message.from_user.id):
        from texts import SUBSCRIPTION_REQUIRED
        await message.answer(
            text=SUBSCRIPTION_REQUIRED,
            parse_mode="HTML",
            reply_markup=subscription_kb()
        )
        return

    await show_main_menu(message, db, state)


@router.callback_query(F.data == CHECK_SUB_CALLBACK)
async def check_subscription(callback: CallbackQuery, bot: Bot, state: FSMContext, db: Database):
    """Пользователь нажал 'Я подписался'."""
    await callback.answer()
    subscribed = await is_subscribed(bot, callback.from_user.id)
    if not subscribed:
        await callback.message.answer(
            text=SUBSCRIPTION_NOT_FOUND,
            parse_mode="HTML",
            reply_markup=subscription_kb()
        )
        return
    await show_main_menu(callback, db, state)


@router.callback_query(F.data == "main_menu")
async def back_to_main(callback: CallbackQuery, state: FSMContext, db: Database):
    await callback.answer()
    await show_main_menu(callback, db, state)


@router.callback_query(F.data == "my_booking")
async def my_booking(callback: CallbackQuery, db: Database):
    await callback.answer()
    user_id = callback.from_user.id
    booking = await db.get_active_booking(user_id)

    if not booking:
        try:
            await callback.message.edit_text(
                "📋 У тебя нет активных записей.",
                reply_markup=back_to_menu_kb()
            )
        except Exception:
            await callback.message.answer(
                "📋 У тебя нет активных записей.",
                reply_markup=back_to_menu_kb()
            )
        return

    text = (
        f"📋 <b>Твоя запись:</b>\n\n"
        f"📅 {format_date(booking['date'])}\n"
        f"🕐 {booking['start_time']}\n"
        f"✂️ {escape_html(booking.get('service_name') or 'Услуга')}\n"
        f"💬 {escape_html(booking.get('comment') or 'нет комментария')}"
    )
    try:
        await callback.message.edit_text(
            text=text, parse_mode="HTML",
            reply_markup=cancel_booking_kb(booking["id"])
        )
    except Exception:
        await callback.message.answer(
            text=text, parse_mode="HTML",
            reply_markup=cancel_booking_kb(booking["id"])
        )


@router.message(F.text == "/admin")
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Нет доступа.")
        return
    await message.answer("👨‍💼 Панель администратора", reply_markup=admin_panel_kb())
