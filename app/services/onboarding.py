from __future__ import annotations

import re
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.services.i18n import t


def build_budget_kb(lang: str) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔘 Under 200,000 UZS" if lang == "en" else ("🔘 200 000 so‘mdan kam" if lang == "uz" else "🔘 До 200 000 UZS"), callback_data="onb:budget:low")
    kb.button(text="🔘 200,000–800,000 UZS" if lang == "en" else ("🔘 200 000–800 000 so‘m" if lang == "uz" else "🔘 200 000–800 000 UZS"), callback_data="onb:budget:mid")
    kb.button(text="🔘 800,000+ UZS" if lang == "en" else ("🔘 800 000+ so‘m" if lang == "uz" else "🔘 800 000+ UZS"), callback_data="onb:budget:high")
    kb.adjust(1)
    return kb


def build_workout_time_kb(lang: str) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text=("🔘 Morning" if lang == "en" else ("🔘 Ertalab" if lang == "uz" else "🔘 Утро")), callback_data="onb:workout:morning")
    kb.button(text=("🔘 Afternoon" if lang == "en" else ("🔘 Kunduzi" if lang == "uz" else "🔘 День")), callback_data="onb:workout:day")
    kb.button(text=("🔘 Evening" if lang == "en" else ("🔘 Kechqurun" if lang == "uz" else "🔘 Вечер")), callback_data="onb:workout:evening")
    kb.adjust(1)
    return kb


_TIME_RE = re.compile(r"^(?:[01]?\d|2[0-3]):[0-5]\d$")


def parse_time_hhmm(text: str) -> tuple[int, int] | None:
    text = (text or "").strip()
    if not _TIME_RE.match(text):
        return None
    hh, mm = text.split(":")
    return int(hh), int(mm)




