"""FSM-состояния всех диалогов."""
from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    selecting_service = State()
    selecting_date    = State()
    selecting_time    = State()
    entering_name     = State()
    entering_phone    = State()
    entering_comment  = State()
    confirming        = State()


class CancelStates(StatesGroup):
    confirming = State()


class AdminSlotStates(StatesGroup):
    selecting_date    = State()
    entering_time     = State()
    selecting_duration = State()


class AdminTemplateStates(StatesGroup):
    selecting_weekdays  = State()
    entering_start_time = State()
    entering_end_time   = State()
    selecting_duration  = State()


class AdminBookingStates(StatesGroup):
    selecting_date      = State()
    cancel_confirming   = State()
