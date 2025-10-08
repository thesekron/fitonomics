from __future__ import annotations

from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.services.i18n import t
from app.config import CHANNEL_USERNAME


def _channel_url() -> str:
    return f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"


def build_gate_kb(lang: str) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "gate_join", channel=CHANNEL_USERNAME), url=_channel_url())
    kb.button(text=t(lang, "gate_joined"), callback_data="gate:joined")
    kb.adjust(1, 1)
    return kb


async def send_channel_gate(message: Message, lang: str, need_join: bool = False) -> None:
    title = t(lang, "welcome_title")
    body = t(lang, "welcome_body")
    text = f"{title}\n{body}"
    if need_join:
        text = t(lang, "gate_need_join")
    await message.answer(text, reply_markup=build_gate_kb(lang).as_markup())




