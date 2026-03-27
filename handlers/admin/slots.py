"""Управление слотами: добавление, удаление, шаблоны."""
import logging
from datetime import date

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.queries import Database
from keyboards.admin_kb import (
    admin_panel_kb, admin_calendar_kb, admin_slots_kb,
    admin_duration_kb, admin_template_weekdays_kb
)
from texts import (
    ADMIN_SLOT_ADDED, ADMIN_SLOT_EXISTS, ADMIN_SLOT_DELETED,
    ADMIN_SLOT_BOOKED, ADMIN_DAY_CLOSED
)
from utils.formatters import format_date, validate_time
from utils.states import AdminSlotStates, AdminTemplateStates
from handlers.admin.panel import IsAdmin

logger = logging.getLogger(__name__)
router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.callback_query(F.data == "admin_slots")
async def admin_slots(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    today = date.today()
    await callback.message.edit_text(
        "⚙️ <b>Управление слотами</b>\n\nВыбери дату:",
        parse_mode="HTML",
        reply_markup=admin_calendar_kb(today.year, today.month, mode="slots")
    )


@router.callback_query(F.data.startswith("admin_cal_select:slots:"))
async def admin_select_date_slots(callback: CallbackQuery, state: FSMContext, db: Database):
    await callback.answer()
    date_str = callback.data.split(":")[2]
    await state.update_data(managing_date=date_str)
    await state.set_state(AdminSlotStates.selecting_date)

    slots = await db.get_all_slots_for_date(date_str)
    await callback.message.edit_text(
        text=f"📅 <b>Слоты на {format_date(date_str)}</b>\n\nНажми на слот чтобы удалить (если свободен):",
        parse_mode="HTML",
        reply_markup=admin_slots_kb(slots, date_str)
    )


@router.callback_query(F.data.startswith("admin_slot_toggle:"))
async def admin_slot_toggle(callback: CallbackQuery, state: FSMContext, db: Database):
    await callback.answer()
    _, slot_id_str, available_str = callback.data.split(":")
    slot_id = int(slot_id_str)
    is_available = int(available_str)

    if not is_available:
        await callback.answer("🔴 Этот слот занят — сначала отмени запись", show_alert=True)
        return

    success = await db.delete_slot(slot_id)
    if success:
        await callback.answer("✅ Слот удалён")
    else:
        await callback.answer("⚠️ Не удалось удалить", show_alert=True)

    data = await state.get_data()
    date_str = data.get("managing_date", "")
    if date_str:
        slots = await db.get_all_slots_for_date(date_str)
        await callback.message.edit_reply_markup(reply_markup=admin_slots_kb(slots, date_str))


@router.callback_query(F.data.startswith("admin_add_slot:"))
async def admin_add_slot_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    date_str = callback.data.split(":")[1]
    await state.update_data(managing_date=date_str)
    await state.set_state(AdminSlotStates.entering_time)
    await callback.message.edit_text(
        f"⏰ Введи время нового слота на <b>{format_date(date_str)}</b>\n\nФормат: ЧЧ:ММ (например 10:30)",
        parse_mode="HTML"
    )


@router.message(AdminSlotStates.entering_time)
async def admin_enter_time(message: Message, state: FSMContext):
    t = message.text.strip()
    if not validate_time(t):
        await message.answer("❌ Неверный формат. Введи время как ЧЧ:ММ (например 10:30):")
        return
    h, m = map(int, t.split(":"))
    normalized = f"{h:02d}:{m:02d}"
    await state.update_data(slot_time=normalized)
    await state.set_state(AdminSlotStates.selecting_duration)
    await message.answer(
        f"⏱ Длительность для слота <b>{normalized}</b>:",
        parse_mode="HTML",
        reply_markup=admin_duration_kb("admin_slot_dur")
    )


@router.callback_query(AdminSlotStates.selecting_duration, F.data.startswith("admin_slot_dur:"))
async def admin_slot_duration(callback: CallbackQuery, state: FSMContext, db: Database):
    await callback.answer()
    duration = int(callback.data.split(":")[1])
    data = await state.get_data()
    date_str = data["managing_date"]
    time_str = data["slot_time"]

    slot_id = await db.add_slot(date_str, time_str, duration)
    if slot_id:
        await callback.message.answer(
            ADMIN_SLOT_ADDED.format(date=format_date(date_str), time=time_str, duration=duration),
            parse_mode="HTML"
        )
    else:
        await callback.message.answer(
            ADMIN_SLOT_EXISTS.format(date=format_date(date_str), time=time_str),
            parse_mode="HTML"
        )

    slots = await db.get_all_slots_for_date(date_str)
    await callback.message.answer(
        f"📅 <b>Слоты на {format_date(date_str)}</b>",
        parse_mode="HTML",
        reply_markup=admin_slots_kb(slots, date_str)
    )
    await state.set_state(AdminSlotStates.selecting_date)


@router.callback_query(F.data.startswith("admin_close_day:"))
async def admin_close_day(callback: CallbackQuery, state: FSMContext, db: Database):
    await callback.answer()
    date_str = callback.data.split(":")[1]
    count = await db.close_day(date_str)
    await callback.message.edit_text(
        ADMIN_DAY_CLOSED.format(date=format_date(date_str), count=count),
        parse_mode="HTML",
        reply_markup=admin_panel_kb()
    )
    await state.clear()


# ── ШАБЛОН РАСПИСАНИЯ ─────────────────────────────────────────

@router.callback_query(F.data == "admin_template")
async def admin_template_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AdminTemplateStates.selecting_weekdays)
    await state.update_data(selected_weekdays=[])
    await callback.message.edit_text(
        "🗓 <b>Создание шаблона</b>\n\nВыбери рабочие дни недели:",
        parse_mode="HTML",
        reply_markup=admin_template_weekdays_kb([])
    )


@router.callback_query(AdminTemplateStates.selecting_weekdays, F.data.startswith("admin_wd:"))
async def admin_toggle_weekday(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    day = int(callback.data.split(":")[1])
    data = await state.get_data()
    selected = data.get("selected_weekdays", [])
    if day in selected:
        selected.remove(day)
    else:
        selected.append(day)
    await state.update_data(selected_weekdays=selected)
    await callback.message.edit_reply_markup(reply_markup=admin_template_weekdays_kb(selected))


@router.callback_query(AdminTemplateStates.selecting_weekdays, F.data == "admin_wd_done")
async def admin_weekdays_done(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    if not data.get("selected_weekdays"):
        await callback.answer("Выбери хотя бы один день!", show_alert=True)
        return
    await state.set_state(AdminTemplateStates.entering_start_time)
    await callback.message.edit_text(
        "⏰ Введи время начала работы (ЧЧ:ММ):",
        parse_mode="HTML"
    )


@router.message(AdminTemplateStates.entering_start_time)
async def admin_template_start_time(message: Message, state: FSMContext):
    t = message.text.strip()
    if not validate_time(t):
        await message.answer("❌ Неверный формат. Введи время как ЧЧ:ММ:")
        return
    h, m = map(int, t.split(":"))
    await state.update_data(start_time=f"{h:02d}:{m:02d}")
    await state.set_state(AdminTemplateStates.entering_end_time)
    await message.answer("⏰ Введи время окончания работы (ЧЧ:ММ):")


@router.message(AdminTemplateStates.entering_end_time)
async def admin_template_end_time(message: Message, state: FSMContext):
    t = message.text.strip()
    if not validate_time(t):
        await message.answer("❌ Неверный формат. Введи время как ЧЧ:ММ:")
        return
    h, m = map(int, t.split(":"))
    await state.update_data(end_time=f"{h:02d}:{m:02d}")
    await state.set_state(AdminTemplateStates.selecting_duration)
    await message.answer(
        "⏱ Длительность каждого слота:",
        reply_markup=admin_duration_kb("admin_tmpl_dur")
    )


@router.callback_query(AdminTemplateStates.selecting_duration, F.data.startswith("admin_tmpl_dur:"))
async def admin_template_apply(callback: CallbackQuery, state: FSMContext, db: Database):
    await callback.answer()
    duration = int(callback.data.split(":")[1])
    data = await state.get_data()

    await callback.message.edit_text("⏳ Создаю слоты...")
    count = await db.add_slots_by_template(
        weekdays=data["selected_weekdays"],
        start_time=data["start_time"],
        end_time=data["end_time"],
        duration=duration
    )
    days_ru = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]
    days_str = ", ".join(days_ru[d] for d in sorted(data["selected_weekdays"]))
    await callback.message.edit_text(
        f"✅ <b>Шаблон применён!</b>\n\n"
        f"📅 Дни: {days_str}\n"
        f"⏰ Время: {data['start_time']} – {data['end_time']}\n"
        f"⏱ Длительность: {duration} мин\n"
        f"📊 Создано слотов: <b>{count}</b>",
        parse_mode="HTML",
        reply_markup=admin_panel_kb()
    )
    await state.clear()
