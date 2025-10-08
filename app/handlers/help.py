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
    """Inline back removed."""
    return types.InlineKeyboardMarkup(inline_keyboard=[])


@router.message(Command("help"))
async def show_help(message: types.Message):
    """Show help with FAQ and contact information."""
    lang = get_lang(message.from_user.id)
    
    text = f"{t(lang, 'help.title')}\n\n"
    text += f"{t(lang, 'help.faq')}\n\n"
    text += f"{t(lang, 'help.contact')}"
    
    await message.answer(text, reply_markup=_back_to_menu_kb(lang))


async def show_help_from_menu(message: types.Message, lang: str, reply_markup=None):
    """Show help - called from main menu."""
    text = f"{t(lang, 'help.title')}\n\n"
    text += f"{t(lang, 'help.faq')}\n\n"
    text += f"{t(lang, 'help.contact')}"

    if reply_markup:
        await message.answer("🔽", reply_markup=reply_markup)
    await message.answer(text, reply_markup=_back_to_menu_kb(lang))


# inline back removed
