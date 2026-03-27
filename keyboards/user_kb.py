"""Клавиатуры для пользователей."""
import calendar
from datetime import date
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb(has_booking: bool = False) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="📅 Записаться", callback_data="booking_start"))
    b.row(
        InlineKeyboardButton(text="💰 Прайс", callback_data="pricelist"),
        InlineKeyboardButton(text="📍 Контакты", callback_data="contacts"),
    )
    if has_booking:
        b.row(InlineKeyboardButton(text="❌ Моя запись / Отмена", callback_data="my_booking"))
    else:
        b.row(InlineKeyboardButton(text="📋 Моя запись", callback_data="my_booking"))
    return b.as_markup()


def back_to_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
    ]])


def cancel_flow_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="❌ Отмена", callback_data="main_menu")
    ]])


# ── ВЫБОР УСЛУГИ ─────────────────────────────────────────────

def categories_kb(categories: list[dict]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for cat in categories:
        b.row(InlineKeyboardButton(
            text=f"{cat['emoji']} {cat['name']}",
            callback_data=f"category:{cat['id']}"
        ))
    b.row(InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu"))
    return b.as_markup()


def services_kb(services: list[dict], category_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for s in services:
        b.row(InlineKeyboardButton(
            text=f"{s['name']} — {s['price']} ({s['duration_minutes']} мин)",
            callback_data=f"service:{s['id']}"
        ))
    b.row(InlineKeyboardButton(text="🔙 К категориям", callback_data="booking_start"))
    return b.as_markup()


# ── КАЛЕНДАРЬ ─────────────────────────────────────────────────

def calendar_kb(available_dates: list[str], year: int, month: int) -> InlineKeyboardMarkup:
    months_ru = ["","Январь","Февраль","Март","Апрель","Май","Июнь",
                 "Июль","Август","Сентябрь","Октябрь","Ноябрь","Декабрь"]
    b = InlineKeyboardBuilder()

    pm = month - 1 if month > 1 else 12
    py = year if month > 1 else year - 1
    nm = month + 1 if month < 12 else 1
    ny = year if month < 12 else year + 1

    b.row(
        InlineKeyboardButton(text="◀️", callback_data=f"cal_nav:{py}:{pm}"),
        InlineKeyboardButton(text=f"📅 {months_ru[month]} {year}", callback_data="cal_ignore"),
        InlineKeyboardButton(text="▶️", callback_data=f"cal_nav:{ny}:{nm}"),
    )
    b.row(*[InlineKeyboardButton(text=d, callback_data="cal_ignore")
            for d in ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]])

    available_set = set(available_dates)
    today = date.today()
    for week in calendar.monthcalendar(year, month):
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="cal_ignore"))
            else:
                d = date(year, month, day)
                ds = d.isoformat()
                if d < today:
                    row.append(InlineKeyboardButton(text=f"✗{day}", callback_data="cal_past"))
                elif ds in available_set:
                    row.append(InlineKeyboardButton(text=f"✅{day}", callback_data=f"cal_select:{ds}"))
                else:
                    row.append(InlineKeyboardButton(text=f"🔴{day}", callback_data="cal_full"))
        b.row(*row)

    b.row(InlineKeyboardButton(text="🔙 Назад", callback_data="booking_start"))
    return b.as_markup()


def time_slots_kb(slots: list[dict]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for s in slots:
        b.row(InlineKeyboardButton(
            text=f"🕐 {s['start_time']} ({s['duration_minutes']} мин)",
            callback_data=f"slot:{s['id']}"
        ))
    b.row(InlineKeyboardButton(text="🔙 Назад к датам", callback_data="back_to_dates"))
    return b.as_markup()


# ── ДАННЫЕ КЛИЕНТА ────────────────────────────────────────────

def use_tg_name_kb(name: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(
        text=f"✅ Использовать «{name}»",
        callback_data="use_tg_name"
    ))
    b.row(InlineKeyboardButton(text="❌ Отмена", callback_data="main_menu"))
    return b.as_markup()


def skip_comment_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip_comment"))
    b.row(InlineKeyboardButton(text="❌ Отмена", callback_data="main_menu"))
    return b.as_markup()


def confirm_booking_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_booking"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="main_menu"),
    )
    return b.as_markup()


def cancel_booking_kb(booking_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(
        text="❌ Отменить запись",
        callback_data=f"user_cancel:{booking_id}"
    ))
    b.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
    return b.as_markup()


def confirm_cancel_kb(booking_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✅ Да, отменить", callback_data=f"do_cancel:{booking_id}"),
        InlineKeyboardButton(text="❌ Нет", callback_data="main_menu"),
    )
    return b.as_markup()
