from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.services.i18n import t


def build_settings_menu_kb(lang: str) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "btn_change_language"), callback_data="settings:lang")
    kb.button(text=t(lang, "meals.change_budget"), callback_data="settings:budget")
    kb.adjust(1)
    return kb


def build_language_kb(lang: str) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text="🇷🇺 Русский", callback_data="lang:ru")
    kb.button(text="🇺🇿 O‘zbekcha", callback_data="lang:uz")
    kb.button(text="🇺🇸 English", callback_data="lang:en")
    kb.adjust(1)
    return kb





def build_budget_kb(lang: str) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "budget_low"), callback_data="budget:low")
    kb.button(text=t(lang, "budget_mid"), callback_data="budget:mid")
    kb.button(text=t(lang, "budget_high"), callback_data="budget:high")
    kb.adjust(1)
    return kb


def parse_profile_text(text: str) -> Optional[Tuple[int, int, int]]:
    """Parse simple 'age height weight' numbers separated by spaces or commas.

    Returns a tuple (age, height_cm, weight_kg) or None if invalid.
    """
    raw = text.replace(",", " ")
    parts = [p for p in raw.split() if p]
    if len(parts) != 3:
        return None
    try:
        age = int(parts[0])
        height = int(parts[1])
        weight = int(parts[2])
    except ValueError:
        return None
    if not (0 < age < 120 and 50 < height < 260 and 20 < weight < 400):
        return None
    return age, height, weight


def build_reminder_kb(lang: str) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "rem_morning"), callback_data="reminder:morning")
    kb.button(text=t(lang, "rem_day"), callback_data="reminder:day")
    kb.button(text=t(lang, "rem_evening"), callback_data="reminder:evening")
    kb.adjust(1)
    return kb


