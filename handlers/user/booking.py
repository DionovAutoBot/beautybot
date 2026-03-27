"""
FSM процесса записи:
услуга → дата → время → имя → телефон → комментарий → подтверждение
"""
import logging
from datetime import date as date_type

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import ADMIN_ID, SALON_ADDRESS
from database.queries import Database
from keyboards.user_kb import (
    categories_kb, services_kb, calendar_kb, time_slots_kb,
    use_tg_name_kb, skip_comment_kb, confirm_booking_kb,
    back_to_menu_kb, main_menu_kb
)
from texts import (
    BOOKING_SELECT_SERVICE, BOOKING_SELECT_DATE, BOOKING_NO_DATES,
    BOOKING_SELECT_TIME, BOOKING_NO_SLOTS, BOOKING_ENTER_NAME,
    BOOKING_ENTER_PHONE, BOOKING_PHONE_INVALID, BOOKING_ENTER_COMMENT,
    BOOKING_CONFIRM, BOOKING_SUCCESS, BOOKING_SLOT_TAKEN, BOOKING_HAS_ACTIVE,
    ADMIN_NEW_BOOKING
)
from utils.formatters import (
    format_date, format_time, validate_phone, format_comment, escape_html
)
from utils.states import BookingStates

logger = logging.getLogger(__name__)
router = Router()


# ── ВЫБОР УСЛУГИ ─────────────────────────────────────────────

@router.callback_query(F.data == "booking_start")
async def start_booking(callback: CallbackQuery, state: FSMContext, db: Database):
    await callback.answer()
    user_id = callback.from_user.id

    # Проверяем существующую запись
    existing = await db.get_active_booking(user_id)
    if existing:
        text = BOOKING_HAS_ACTIVE.format(
            date=format_date(existing["date"]),
            time=existing["start_time"],
            service=escape_html(existing.get("service_name") or "Услуга")
        )
        try:
            await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=back_to_menu_kb())
        except Exception:
            await callback.message.answer(text=text, parse_mode="HTML", reply_markup=back_to_menu_kb())
        return

    categories = await db.get_categories()
    await state.set_state(BookingStates.selecting_service)

    try:
        await callback.message.edit_text(
            text=BOOKING_SELECT_SERVICE, parse_mode="HTML",
            reply_markup=categories_kb(categories)
        )
    except Exception:
        await callback.message.answer(
            text=BOOKING_SELECT_SERVICE, parse_mode="HTML",
            reply_markup=categories_kb(categories)
        )


@router.callback_query(BookingStates.selecting_service, F.data.startswith("category:"))
async def select_category(callback: CallbackQuery, state: FSMContext, db: Database):
    await callback.answer()
    cat_id = int(callback.data.split(":")[1])
    services = await db.get_services_by_category(cat_id)
    if not services:
        await callback.answer("В этой категории нет услуг", show_alert=True)
        return
    await state.update_data(category_id=cat_id)
    await callback.message.edit_text(
        text=BOOKING_SELECT_SERVICE, parse_mode="HTML",
        reply_markup=services_kb(services, cat_id)
    )


@router.callback_query(BookingStates.selecting_service, F.data.startswith("service:"))
async def select_service(callback: CallbackQuery, state: FSMContext, db: Database):
    await callback.answer()
    service_id = int(callback.data.split(":")[1])
    service = await db.get_service(service_id)
    if not service:
        await callback.answer("Услуга не найдена", show_alert=True)
        return

    await state.update_data(service_id=service_id, service=service)

    # Получаем даты с подходящими слотами
    available_dates = await db.get_available_dates(min_duration=service["duration_minutes"])
    if not available_dates:
        try:
            await callback.message.edit_text(text=BOOKING_NO_DATES, parse_mode="HTML", reply_markup=back_to_menu_kb())
        except Exception:
            await callback.message.answer(text=BOOKING_NO_DATES, parse_mode="HTML", reply_markup=back_to_menu_kb())
        return

    await state.update_data(available_dates=available_dates)
    await state.set_state(BookingStates.selecting_date)

    today = date_type.today()
    await callback.message.edit_text(
        text=BOOKING_SELECT_DATE, parse_mode="HTML",
        reply_markup=calendar_kb(available_dates, today.year, today.month)
    )


# ── КАЛЕНДАРЬ ─────────────────────────────────────────────────

@router.callback_query(F.data.startswith("cal_nav:"))
async def nav_calendar(callback: CallbackQuery, state: FSMContext, db: Database):
    await callback.answer()
    _, y, m = callback.data.split(":")
    data = await state.get_data()
    available = data.get("available_dates", [])
    # Обновляем даты на случай изменений
    service = data.get("service", {})
    if service:
        available = await db.get_available_dates(min_duration=service.get("duration_minutes", 0))
        await state.update_data(available_dates=available)
    await callback.message.edit_reply_markup(
        reply_markup=calendar_kb(available, int(y), int(m))
    )


@router.callback_query(F.data.startswith("cal_select:"))
async def select_date(callback: CallbackQuery, state: FSMContext, db: Database):
    await callback.answer()
    date_str = callback.data[len("cal_select:"):]
    data = await state.get_data()
    service = data.get("service", {})
    duration = service.get("duration_minutes", 60)

    slots = await db.get_slots_for_date(date_str, min_duration=duration)
    if not slots:
        await callback.answer("На эту дату нет подходящих слотов", show_alert=True)
        return

    await state.update_data(selected_date=date_str)
    await state.set_state(BookingStates.selecting_time)

    text = BOOKING_SELECT_TIME.format(
        date=format_date(date_str),
        service=escape_html(service.get("name", "")),
        duration=duration
    )
    await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=time_slots_kb(slots))


@router.callback_query(F.data == "cal_ignore")
async def cal_ignore(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data == "cal_past")
async def cal_past(callback: CallbackQuery):
    await callback.answer("Эта дата уже прошла")


@router.callback_query(F.data == "cal_full")
async def cal_full(callback: CallbackQuery):
    await callback.answer("На этот день нет свободных слотов", show_alert=True)


@router.callback_query(F.data == "back_to_dates")
async def back_to_dates(callback: CallbackQuery, state: FSMContext, db: Database):
    await callback.answer()
    data = await state.get_data()
    service = data.get("service", {})
    available = await db.get_available_dates(min_duration=service.get("duration_minutes", 0))
    await state.update_data(available_dates=available)
    await state.set_state(BookingStates.selecting_date)
    today = date_type.today()
    await callback.message.edit_text(
        text=BOOKING_SELECT_DATE, parse_mode="HTML",
        reply_markup=calendar_kb(available, today.year, today.month)
    )


# ── ВЫБОР ВРЕМЕНИ ─────────────────────────────────────────────

@router.callback_query(BookingStates.selecting_time, F.data.startswith("slot:"))
async def select_slot(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    slot_id = int(callback.data.split(":")[1])
    await state.update_data(slot_id=slot_id)
    await state.set_state(BookingStates.entering_name)

    # Предлагаем имя из TG
    name = callback.from_user.first_name or ""
    await callback.message.edit_text(
        text=BOOKING_ENTER_NAME, parse_mode="HTML",
        reply_markup=use_tg_name_kb(name) if name else None
    )


@router.callback_query(BookingStates.entering_name, F.data == "use_tg_name")
async def use_tg_name(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    name = callback.from_user.first_name or "Клиент"
    await state.update_data(client_name=name)
    await state.set_state(BookingStates.entering_phone)
    await callback.message.edit_text(text=BOOKING_ENTER_PHONE, parse_mode="HTML")


@router.message(BookingStates.entering_name)
async def enter_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("❌ Слишком короткое имя. Введи ещё раз:")
        return
    await state.update_data(client_name=name)
    await state.set_state(BookingStates.entering_phone)
    await message.answer(text=BOOKING_ENTER_PHONE, parse_mode="HTML")


@router.message(BookingStates.entering_phone)
async def enter_phone(message: Message, state: FSMContext):
    phone = validate_phone(message.text.strip())
    if not phone:
        await message.answer(text=BOOKING_PHONE_INVALID, parse_mode="HTML")
        return
    await state.update_data(phone=phone)
    await state.set_state(BookingStates.entering_comment)
    await message.answer(text=BOOKING_ENTER_COMMENT, parse_mode="HTML", reply_markup=skip_comment_kb())


@router.message(BookingStates.entering_comment)
async def enter_comment(message: Message, state: FSMContext, db: Database):
    await state.update_data(comment=message.text.strip())
    await _show_confirm(message, state, db)


@router.callback_query(BookingStates.entering_comment, F.data == "skip_comment")
async def skip_comment(callback: CallbackQuery, state: FSMContext, db: Database):
    await callback.answer()
    await state.update_data(comment=None)
    await _show_confirm(callback.message, state, db)


async def _show_confirm(msg: Message, state: FSMContext, db: Database):
    data = await state.get_data()
    slot = await db.get_slot(data["slot_id"])
    service = data["service"]

    text = BOOKING_CONFIRM.format(
        date=format_date(slot["date"]),
        time=slot["start_time"],
        service=escape_html(service["name"]),
        price=service["price"],
        duration=service["duration_minutes"],
        name=escape_html(data["client_name"]),
        phone=data["phone"],
        comment=format_comment(data.get("comment"))
    )
    await state.set_state(BookingStates.confirming)
    await msg.answer(text=text, parse_mode="HTML", reply_markup=confirm_booking_kb())


# ── ПОДТВЕРЖДЕНИЕ ─────────────────────────────────────────────

@router.callback_query(BookingStates.confirming, F.data == "confirm_booking")
async def confirm_booking(callback: CallbackQuery, state: FSMContext, db: Database, bot: Bot, scheduler=None):
    await callback.answer()
    data = await state.get_data()
    user_id = callback.from_user.id

    # Финальная проверка дубля
    existing = await db.get_active_booking(user_id)
    if existing:
        await callback.message.edit_text(
            text=BOOKING_HAS_ACTIVE.format(
                date=format_date(existing["date"]),
                time=existing["start_time"],
                service=escape_html(existing.get("service_name", ""))
            ),
            parse_mode="HTML", reply_markup=back_to_menu_kb()
        )
        await state.clear()
        return

    booking_id = await db.create_booking(
        user_id=user_id,
        slot_id=data["slot_id"],
        service_id=data["service_id"],
        client_name=data["client_name"],
        phone=data["phone"],
        comment=data.get("comment")
    )

    if booking_id is None:
        await callback.message.edit_text(
            text=BOOKING_SLOT_TAKEN, parse_mode="HTML", reply_markup=back_to_menu_kb()
        )
        await state.clear()
        return

    slot = await db.get_slot(data["slot_id"])
    service = data["service"]

    # Сообщение клиенту
    from keyboards.user_kb import cancel_booking_kb
    await callback.message.edit_text(
        text=BOOKING_SUCCESS.format(
            date=format_date(slot["date"]),
            time=slot["start_time"],
            service=escape_html(service["name"]),
            address=SALON_ADDRESS
        ),
        parse_mode="HTML",
        reply_markup=cancel_booking_kb(booking_id)
    )

    # Уведомление администратору
    try:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=ADMIN_NEW_BOOKING.format(
                date=format_date(slot["date"]),
                time=slot["start_time"],
                service=escape_html(service["name"]),
                name=escape_html(data["client_name"]),
                phone=data["phone"],
                comment=format_comment(data.get("comment")),
                user_id=user_id,
                booking_id=booking_id
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка уведомления администратора: {e}")

    # Напоминание
    if scheduler:
        try:
            scheduler.schedule_reminder(
                booking_id=booking_id,
                user_id=user_id,
                appt_date=slot["date"],
                appt_time=slot["start_time"],
                service_name=service["name"]
            )
        except Exception as e:
            logger.error(f"Ошибка планирования напоминания: {e}")

    await state.clear()
    logger.info(f"Запись #{booking_id} создана для пользователя {user_id}")
