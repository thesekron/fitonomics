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


def build_main_menu_kb(lang: str) -> types.ReplyKeyboardMarkup:
    """Build the persistent main menu reply keyboard with 8 buttons."""
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [
                types.KeyboardButton(text=t(lang, "menu.workouts")),
                types.KeyboardButton(text=t(lang, "menu.meals"))
            ],
            [
                types.KeyboardButton(text=t(lang, "menu.sleep")),
                types.KeyboardButton(text=t(lang, "menu.progress"))
            ],
            [
                types.KeyboardButton(text=t(lang, "menu.profile")),
                types.KeyboardButton(text=t(lang, "menu.settings"))
            ],
            [
                types.KeyboardButton(text=t(lang, "menu.reminders")),
                types.KeyboardButton(text=t(lang, "menu.help"))
            ]
        ],
        resize_keyboard=True,
        persistent=True
    )


def build_back_to_menu_kb(lang: str) -> types.ReplyKeyboardMarkup:
    """Build back to main menu keyboard for submenus (single button)."""
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text=t(lang, "menu.back_to_main"))]
        ],
        resize_keyboard=True,
        persistent=True
    )


@router.message(Command("menu"))
async def show_main_menu(message: types.Message):
    """Show the main menu with persistent reply keyboard."""
    lang = get_lang(message.from_user.id)
    kb = build_main_menu_kb(lang)
    await message.answer(t(lang, "menu.welcome"), reply_markup=kb)


# Button handlers for main menu
WORKOUTS_BTNS = {T[x]["menu.workouts"] for x in T.keys()}
MEALS_BTNS = {T[x]["menu.meals"] for x in T.keys()}
SLEEP_BTNS = {T[x]["menu.sleep"] for x in T.keys()}
PROGRESS_BTNS = {T[x]["menu.progress"] for x in T.keys()}
REMINDERS_BTNS = {T[x]["menu.reminders"] for x in T.keys()}
SETTINGS_BTNS = {T[x]["menu.settings"] for x in T.keys()}
HELP_BTNS = {T[x]["menu.help"] for x in T.keys()}
MAIN_BTNS = {T[x]["menu.main"] for x in T.keys()}
PROFILE_BTNS = {T[x]["menu.profile"] for x in T.keys()}


@router.message(F.text.in_(WORKOUTS_BTNS))
async def handle_workouts(message: types.Message):
    """Handle workouts button click."""
    from .workouts import open_workouts_menu
    lang = get_lang(message.from_user.id)
    # Send workouts menu with keyboard switch
    await open_workouts_menu(message, lang, reply_markup=build_back_to_menu_kb(lang))


@router.message(F.text.in_(MEALS_BTNS))
async def handle_meals(message: types.Message):
    """Handle meals button click."""
    from .meals import open_meals_menu
    lang = get_lang(message.from_user.id)
    await open_meals_menu(message, lang, reply_markup=build_back_to_menu_kb(lang))


@router.message(F.text.in_(SLEEP_BTNS))
async def handle_sleep(message: types.Message):
    """Handle sleep button click."""
    from .sleep import show_sleep_summary
    lang = get_lang(message.from_user.id)
    await show_sleep_summary(message, lang, reply_markup=build_back_to_menu_kb(lang))


@router.message(F.text.in_(PROGRESS_BTNS))
async def handle_progress(message: types.Message):
    """Handle progress button click."""
    from .progress import show_progress_summary_from_menu
    lang = get_lang(message.from_user.id)
    await show_progress_summary_from_menu(message, lang, reply_markup=build_back_to_menu_kb(lang))


@router.message(F.text.in_(REMINDERS_BTNS))
async def handle_reminders(message: types.Message):
    """Handle reminders button click."""
    from .reminders import show_reminders_menu_from_menu
    lang = get_lang(message.from_user.id)
    await show_reminders_menu_from_menu(message, lang, reply_markup=build_back_to_menu_kb(lang))


@router.message(F.text.in_(SETTINGS_BTNS))
async def handle_settings(message: types.Message):
    """Handle settings button click."""
    from .settings import open_settings_menu
    lang = get_lang(message.from_user.id)
    await open_settings_menu(message, lang, reply_markup=build_back_to_menu_kb(lang))


@router.message(F.text.in_(HELP_BTNS))
async def handle_help(message: types.Message):
    """Handle help button click."""
    from .help import show_help_from_menu
    lang = get_lang(message.from_user.id)
    await show_help_from_menu(message, lang, reply_markup=build_back_to_menu_kb(lang))


@router.message(F.text.in_(PROFILE_BTNS))
async def handle_profile(message: types.Message):
    """Handle profile button click."""
    from .profile import show_profile_from_menu
    lang = get_lang(message.from_user.id)
    await show_profile_from_menu(message, lang, reply_markup=build_back_to_menu_kb(lang))


@router.message(F.text.in_(MAIN_BTNS))
async def handle_main_menu(message: types.Message):
    """Handle main menu button click - return to main menu."""
    lang = get_lang(message.from_user.id)
    kb = build_main_menu_kb(lang)
    await message.answer(t(lang, "menu.welcome"), reply_markup=kb)
