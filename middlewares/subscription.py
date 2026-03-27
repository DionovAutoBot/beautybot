"""
Middleware проверки подписки на канал.
При каждом апдейте проверяет, подписан ли пользователь.
Если нет — блокирует и показывает кнопку подписки.
"""
import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (
    TelegramObject, Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)

from config import CHANNEL_ID, CHANNEL_LINK, CHANNEL_NAME
from texts import SUBSCRIPTION_REQUIRED, SUBSCRIPTION_NOT_FOUND

logger = logging.getLogger(__name__)

# Callback_data кнопки "Я подписался"
CHECK_SUB_CALLBACK = "check_subscription"


def subscription_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📢 Подписаться на {CHANNEL_NAME}", url=CHANNEL_LINK)],
        [InlineKeyboardButton(text="✅ Я подписался", callback_data=CHECK_SUB_CALLBACK)],
    ])


async def is_subscribed(bot: Bot, user_id: int) -> bool:
    """Проверяет подписку пользователя на канал."""
    if not CHANNEL_ID:
        return True  # Если CHANNEL_ID не задан — проверка отключена
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status not in ("left", "kicked", "banned")
    except TelegramBadRequest:
        return True  # Если не можем проверить — пропускаем
    except Exception as e:
        logger.warning(f"Ошибка проверки подписки для {user_id}: {e}")
        return True


class SubscriptionMiddleware(BaseMiddleware):
    """
    Проверяет подписку перед каждым апдейтом.
    Пропускает:
    - команду /start (нужна чтобы показать кнопку подписки)
    - callback "check_subscription" (чтобы можно было нажать "Я подписался")
    - если CHANNEL_ID не задан
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not CHANNEL_ID:
            return await handler(event, data)

        # Определяем пользователя и бота
        bot: Bot = data.get("bot")
        user = data.get("event_from_user")
        if not user or not bot:
            return await handler(event, data)

        # Пропускаем /start и кнопку проверки
        if isinstance(event, Message) and event.text and event.text.startswith("/start"):
            return await handler(event, data)
        if isinstance(event, CallbackQuery) and event.data == CHECK_SUB_CALLBACK:
            return await handler(event, data)

        # Проверяем подписку
        subscribed = await is_subscribed(bot, user.id)
        if subscribed:
            return await handler(event, data)

        # Не подписан — блокируем и показываем кнопку
        kb = subscription_kb()
        if isinstance(event, Message):
            await event.answer(
                text=SUBSCRIPTION_REQUIRED,
                parse_mode="HTML",
                reply_markup=kb
            )
        elif isinstance(event, CallbackQuery):
            await event.answer()
            await event.message.answer(
                text=SUBSCRIPTION_REQUIRED,
                parse_mode="HTML",
                reply_markup=kb
            )
        return None
