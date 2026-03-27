"""Клавиатуры для администратора."""
import calendar
from datetime import date
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def admin_panel_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="📅 Записи сегодня", callback_data="admin_today"),
        InlineKeyboardButton(text="📅 Записи завтра", callback_data="admin_tomorrow"),
    )
    b.row(InlineKeyboardButton(text="🗓 Записи на дату", callback_data="admin_bookings_date"))
    b.row(InlineKeyboardButton(text="⚙️ Управление слотами", callback_data="admin_slots"))
    b.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
    return b.as_markup()


def admin_calendar_kb(year: int, month: int, mode: str = "slots") -> InlineKeyboardMarkup:
    months_ru = ["","Январь","Февраль","Март","Апрель","Май","Июнь",
                 "Июль","Август","Сентябрь","Октябрь","Ноябрь","Декабрь"]
    b = InlineKeyboardBuilder()
    pm = month - 1 if month > 1 else 12
    py = year if month > 1 else year - 1
    nm = month + 1 if month < 12 else 1
    ny = year if month < 12 else year + 1
    b.row(
        InlineKeyboardButton(text="◀️", callback_data=f"admin_cal_nav:{mode}:{py}:{pm}"),
        InlineKeyboardButton(text=f"📅 {months_ru[month]} {year}", callback_data="cal_ignore"),
        InlineKeyboardButton(text="▶️", callback_data=f"admin_cal_nav:{mode}:{ny}:{nm}"),
    )
    b.row(*[InlineKeyboardButton(text=d, callback_data="cal_ignore")
            for d in ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]])
    today = date.today()
    for week in calendar.monthcalendar(year, month):
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="cal_ignore"))
            else:
                d = date(year, month, day)
                label = f"[{day}]" if d == today else str(day)
                row.append(InlineKeyboardButton(
                    text=label,
                    callback_data=f"admin_cal_select:{mode}:{d.isoformat()}"
                ))
        b.row(*row)
    b.row(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel"))
    return b.as_markup()


def admin_slots_kb(slots: list[dict], date_str: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for s in slots:
        status = "✅" if s["is_available"] else "🔴"
        b.row(InlineKeyboardButton(
            text=f"{status} {s['start_time']} ({s['duration_minutes']} мин)",
            callback_data=f"admin_slot_toggle:{s['id']}:{int(s['is_available'])}"
        ))
    b.row(InlineKeyboardButton(text="➕ Добавить слот", callback_data=f"admin_add_slot:{date_str}"))
    b.row(InlineKeyboardButton(text="🚫 Закрыть день", callback_data=f"admin_close_day:{date_str}"))
    b.row(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_slots"))
    return b.as_markup()


def admin_duration_kb(prefix: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="30 мин", callback_data=f"{prefix}:30"),
        InlineKeyboardButton(text="60 мин", callback_data=f"{prefix}:60"),
        InlineKeyboardButton(text="90 мин", callback_data=f"{prefix}:90"),
        InlineKeyboardButton(text="120 мин", callback_data=f"{prefix}:120"),
    )
    b.row(InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel"))
    return b.as_markup()


def admin_bookings_kb(bookings: list[dict]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for bk in bookings:
        b.row(InlineKeyboardButton(
            text=f"🕐 {bk['start_time']} — {bk['client_name']} ({bk.get('service_name','?')})",
            callback_data=f"admin_booking_detail:{bk['id']}"
        ))
    b.row(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel"))
    return b.as_markup()


def admin_booking_detail_kb(booking_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(
        text="❌ Отменить запись",
        callback_data=f"admin_cancel_confirm:{booking_id}"
    ))
    b.row(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel"))
    return b.as_markup()


def admin_cancel_confirm_kb(booking_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✅ Да, отменить", callback_data=f"admin_do_cancel:{booking_id}"),
        InlineKeyboardButton(text="❌ Нет", callback_data="admin_panel"),
    )
    return b.as_markup()


def admin_template_weekdays_kb(selected: list[int]) -> InlineKeyboardMarkup:
    days = [(0,"Пн"),(1,"Вт"),(2,"Ср"),(3,"Чт"),(4,"Пт"),(5,"Сб"),(6,"Вс")]
    b = InlineKeyboardBuilder()
    row = []
    for idx, name in days:
        pref = "✅" if idx in selected else "⬜"
        row.append(InlineKeyboardButton(
            text=f"{pref}{name}", callback_data=f"admin_wd:{idx}"
        ))
    b.row(*row)
    b.row(
        InlineKeyboardButton(text="✅ Готово", callback_data="admin_wd_done"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel"),
    )
    return b.as_markup()
