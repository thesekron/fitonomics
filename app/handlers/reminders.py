from __future__ import annotations

from aiogram import F, types
from aiogram.filters import Command
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.user import User
from app.services.i18n import t, T
from .start import router


def get_lang(user_id: int) -> str:
    db: Session = SessionLocal()
    u = db.query(User).filter(User.tg_id == user_id).first()
    lang = u.language if u and u.language else "ru"
    db.close()
    return lang


def _back_to_menu_kb(lang: str) -> types.InlineKeyboardMarkup:
    """Build back to menu inline keyboard."""
    return types.InlineKeyboardMarkup(inline_keyboard=[])


@router.message(Command("reminders"))
async def show_reminders_menu(message: types.Message):
    """Show reminders menu - stub implementation."""
    lang = get_lang(message.from_user.id)
    text = t(lang, "reminders.title") + "\n\n" + t(lang, "reminders.coming_soon")
    await message.answer(text, reply_markup=_back_to_menu_kb(lang))


async def show_reminders_menu_from_menu(message: types.Message, lang: str, reply_markup=None):
    """Show reminders menu - called from main menu."""
    text = t(lang, "reminders.title") + "\n\n" + t(lang, "reminders.coming_soon")
    if reply_markup:
        await message.answer("🔽", reply_markup=reply_markup)
    await message.answer(text, reply_markup=_back_to_menu_kb(lang))


@router.callback_query(F.data == "reminders:back_to_menu")
async def back_to_main_menu(call: types.CallbackQuery):
    """Deprecated: inline back removed."""
    await call.answer()
