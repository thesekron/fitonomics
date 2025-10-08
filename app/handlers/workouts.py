from __future__ import annotations

from pathlib import Path

from aiogram import types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InputFile
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.user import User
from app.models.workout_log import WorkoutLog
from app.services.content import load_workouts, get_workout_media_path
from app.services.i18n import t, T
from .start import router


class WorkoutStates(StatesGroup):
    doing = State()


def get_lang(user_id: int) -> str:
    db: Session = SessionLocal()
    u = db.query(User).filter(User.tg_id == user_id).first()
    lang = u.language if u and u.language else "ru"
    db.close()
    return lang


def _exercise_caption(lang: str, group: str, index: int, total: int, ex: dict) -> str:
    title = ex.get(f"title_{lang}") or ex.get("title_en") or "Exercise"
    desc = ex.get(f"desc_{lang}") or ex.get("desc_en") or ""
    return f"{title}\n{desc}\n{t(lang, 'w_start', group=group, i=index+1, n=total)}"



def _nav_kb(lang: str, at_last: bool) -> types.InlineKeyboardMarkup:
    builder = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=t(lang, "w_next"), callback_data="w:next")],
        [types.InlineKeyboardButton(text=t(lang, "w_done"), callback_data="w:done")],
    ])
    return builder


async def open_workouts_menu(message: types.Message, lang: str, reply_markup=None) -> None:
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=t(lang, "workouts.mode_home"), callback_data="w:mode:home")],
        [types.InlineKeyboardButton(text=t(lang, "workouts.mode_gym"), callback_data="w:mode:gym")],
    ])
    if reply_markup:
        await message.answer("🔽", reply_markup=reply_markup)
    await message.answer(t(lang, "workouts.choose_mode_title"), reply_markup=kb)


@router.callback_query(F.data == "w:start_workout")
async def choose_mode(call: CallbackQuery):
    lang = get_lang(call.from_user.id)
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=t(lang, "workouts.mode_home"), callback_data="w:mode:home")],
        [types.InlineKeyboardButton(text=t(lang, "workouts.mode_gym"), callback_data="w:mode:gym")],
    ])
    await call.message.edit_text(t(lang, "workouts.choose_mode_title"), reply_markup=kb)
    await call.answer()


def _get_last_group(user_id: int) -> str | None:
    with SessionLocal() as session:
        last = (
            session.query(WorkoutLog)
            .filter(WorkoutLog.user_id == user_id)
            .order_by(WorkoutLog.created_at.desc())
            .first()
        )
        return last.group if last else None


@router.callback_query(F.data.startswith("w:mode:"))
async def choose_body_after_mode(call: CallbackQuery):
    lang = get_lang(call.from_user.id)
    last = _get_last_group(call.from_user.id)
    # map stored key to localized name
    def _loc(name: str | None) -> str:
        if not name:
            return t(lang, "none") if "none" in T[lang] else "—"
        key = {
            "arms": "group_arms",
            "legs": "group_legs",
            "chest": "group_chest",
            "back": "group_back",
            "shoulders": "group_shoulders",
            "full": "group_full",
            "core": "group_core",
        }.get(name, name)
        return t(lang, key)

    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=t(lang, "group_full"), callback_data="w:start:full")],
        [types.InlineKeyboardButton(text=t(lang, "group_chest"), callback_data="w:start:chest")],
        [types.InlineKeyboardButton(text=t(lang, "group_arms"), callback_data="w:start:arms")],
        [types.InlineKeyboardButton(text=t(lang, "group_legs"), callback_data="w:start:legs")],
        [types.InlineKeyboardButton(text=t(lang, "group_shoulders"), callback_data="w:start:shoulders")],
        [types.InlineKeyboardButton(text=t(lang, "group_back"), callback_data="w:start:back")],
    ])
    await call.message.edit_text(
        t(lang, "workouts.choose_body_with_last", last=_loc(last)),
        reply_markup=kb,
    )
    await call.answer()


# inline back to menu removed; reply keyboard handles navigation


@router.callback_query(F.data.startswith("w:start:"))
async def start_workout(call: CallbackQuery, state: FSMContext):
    group = call.data.split(":", 2)[2]
    lang = get_lang(call.from_user.id)
    exercises = load_workouts(group)
    if not exercises:
        await call.message.edit_text(t(lang, "gif_missing"))
        await call.answer()
        return
    await state.set_state(WorkoutStates.doing)
    await state.update_data(group=group, index=0, total=len(exercises))
    await _send_exercise(call, state, lang)
    await call.answer()


async def _send_exercise(call: CallbackQuery, state: FSMContext, lang: str):
    data = await state.get_data()
    group: str = data["group"]
    index: int = data["index"]
    exercises = load_workouts(group)
    total = len(exercises)
    ex = exercises[index]
    media_name = ex.get("media")
    caption = _exercise_caption(lang, group, index, total, ex)
    file_path = get_workout_media_path(media_name)
    if file_path:
        await call.message.edit_media(
            types.InputMediaAnimation(media=InputFile(file_path), caption=caption)
        )
    else:
        await call.message.edit_text(f"{t(lang, 'gif_missing')}\n\n{caption}")
    await call.message.edit_reply_markup(reply_markup=_nav_kb(lang, at_last=(index == total-1)))


@router.callback_query(WorkoutStates.doing, F.data == "w:next")
async def next_exercise(call: CallbackQuery, state: FSMContext):
    lang = get_lang(call.from_user.id)
    data = await state.get_data()
    index: int = data.get("index", 0) + 1
    total: int = data.get("total", 0)
    if index >= total:
        await done_workout(call, state)  # gracefully finish
        return
    await state.update_data(index=index)
    await _send_exercise(call, state, lang)
    await call.answer()


@router.callback_query(WorkoutStates.doing, F.data == "w:done")
async def done_workout(call: CallbackQuery, state: FSMContext):
    lang = get_lang(call.from_user.id)
    data = await state.get_data()
    group: str = data.get("group", "")
    with SessionLocal() as session:
        session.add(WorkoutLog(user_id=call.from_user.id, group=group))
        session.commit()
    await state.clear()
    await call.message.edit_text(t(lang, "w_finished", group=group))
    await call.answer()
