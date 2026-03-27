"""Обработка устаревших callback (>5 мин) — возврат в меню вместо краша."""
import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

logger = logging.getLogger(__name__)


class StaleCallbackMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[CallbackQuery, dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except TelegramBadRequest as e:
            if "query is too old" in str(e) or "query ID is invalid" in str(e):
                logger.warning(f"Stale callback user={event.from_user.id} data={event.data!r}")
                try:
                    state: FSMContext = data.get("state")
                    if state:
                        await state.clear()
                except Exception:
                    pass
                try:
                    from keyboards.user_kb import main_menu_kb
                    await event.message.answer(
                        "⏰ <b>Сессия устарела.</b>\n\nНачни заново 👇",
                        parse_mode="HTML",
                        reply_markup=main_menu_kb()
                    )
                except Exception:
                    pass
                return
            raise
