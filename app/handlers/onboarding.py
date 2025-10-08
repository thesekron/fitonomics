from __future__ import annotations

import asyncio
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from .start import router
from app.config import CHANNEL_USERNAME
from app.database import SessionLocal
from app.models.user import User
from app.models.user_settings import UserSettings
from app.services.i18n import t
from app.services.channel_gate import build_gate_kb
from app.services.onboarding import (
    build_budget_kb,
    build_workout_time_kb,
    parse_time_hhmm,
)
from app.services.reminders import schedule_sleep_notifications


class OnbStates(StatesGroup):
    waiting_name = State()
    waiting_age = State()
    waiting_height = State()
    waiting_weight = State()
    waiting_budget = State()
    waiting_workout_time = State()


def _get_user_lang(user_id: int) -> str:
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == user_id).first()
        return (user.language or "ru") if user else "ru"


def _ensure_user(user_id: int) -> User:
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == user_id).first()
        if user is None:
            user = User(tg_id=user_id)
            session.add(user)
            session.commit()
            session.refresh(user)
        return user


async def _edit_step(message: Message, lang: str, step_text: str) -> None:
    try:
        await message.edit_text(step_text)
    except Exception:
        await message.answer(step_text)


@router.callback_query(F.data == "gate:joined")
async def gate_joined(call: CallbackQuery, state: FSMContext) -> None:
    lang = _get_user_lang(call.from_user.id)
    try:
        member = await call.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=call.from_user.id)
        status = getattr(member, "status", None)
        if status in {"member", "administrator", "creator"}:
            await call.message.edit_text(t(lang, "gate_ok"))
            await call.answer()
            # Start onboarding step 1 in same message thread
            await asyncio.sleep(0.3)
            await state.set_state(OnbStates.waiting_name)
            await _edit_step(call.message, lang, t(lang, "onb_q1_name", step="1 | 6"))
            return
    except Exception:
        pass

    await call.message.edit_text(
        t(lang, "gate_need_join"),
        reply_markup=build_gate_kb(lang).as_markup(),
    )
    await call.answer()


@router.message(OnbStates.waiting_name)
async def onb_name(message: Message, state: FSMContext) -> None:
    lang = _get_user_lang(message.from_user.id)
    name = (message.text or "").strip()
    if not name:
        await message.answer("✏️")
        return
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == message.from_user.id).first()
        if user:
            user.name = name
            session.commit()
    await state.update_data(name=name)
    await state.set_state(OnbStates.waiting_age)
    await _edit_step(message, lang, t(lang, "onb_q2_age", step="2 | 6"))


@router.message(OnbStates.waiting_age)
async def onb_age(message: Message, state: FSMContext) -> None:
    lang = _get_user_lang(message.from_user.id)
    try:
        age = int((message.text or "").strip())
        if age <= 0 or age > 120:
            raise ValueError
    except Exception:
        await message.answer(t(lang, "onb_invalid_age"))
        return
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == message.from_user.id).first()
        if user:
            user.age = age
            session.commit()
    await state.update_data(age=age)
    await state.set_state(OnbStates.waiting_height)
    await _edit_step(message, lang, t(lang, "onb_q3_height", step="3 | 6"))


@router.message(OnbStates.waiting_height)
async def onb_height(message: Message, state: FSMContext) -> None:
    lang = _get_user_lang(message.from_user.id)
    try:
        height = int((message.text or "").strip())
        if height < 80 or height > 250:
            raise ValueError
    except Exception:
        await message.answer(t(lang, "onb_invalid_height"))
        return
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == message.from_user.id).first()
        if user:
            user.height = height
            session.commit()
    await state.update_data(height=height)
    await state.set_state(OnbStates.waiting_weight)
    await _edit_step(message, lang, t(lang, "onb_q4_weight", step="4 | 6"))


@router.message(OnbStates.waiting_weight)
async def onb_weight(message: Message, state: FSMContext) -> None:
    lang = _get_user_lang(message.from_user.id)
    try:
        weight = float((message.text or "").replace(",", ".").strip())
        if weight < 20 or weight > 400:
            raise ValueError
    except Exception:
        await message.answer(t(lang, "onb_invalid_weight"))
        return
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == message.from_user.id).first()
        if user:
            user.weight = int(weight)
            session.commit()
    await state.update_data(weight=weight)
    await state.set_state(OnbStates.waiting_budget)
    await message.answer(
        t(lang, "onb_q5_budget", step="5 | 6"),
        reply_markup=build_budget_kb(lang).as_markup(),
    )


@router.callback_query(OnbStates.waiting_budget, F.data.startswith("onb:budget:"))
async def onb_budget(call: CallbackQuery, state: FSMContext) -> None:
    lang = _get_user_lang(call.from_user.id)
    budget_key = call.data.split(":", 2)[2]
    
    # Save budget to both User and UserMealSettings
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == call.from_user.id).first()
        if user:
            user.budget = budget_key
            session.commit()
            
            # Also save to meals budget system
            from app.services.meals import set_user_budget
            set_user_budget(user.id, budget_key)
    
    await state.update_data(budget=budget_key)
    await state.set_state(OnbStates.waiting_workout_time)
    await call.message.answer(
        t(lang, "onb_q6_workout_time", step="6 | 6"),
        reply_markup=build_workout_time_kb(lang).as_markup(),
    )
    await call.answer()


# Removed wake and sleep time questions - now only 6 questions total


@router.callback_query(OnbStates.waiting_workout_time, F.data.startswith("onb:workout:"))
async def onb_workout_time(call: CallbackQuery, state: FSMContext) -> None:
    lang = _get_user_lang(call.from_user.id)
    pref = call.data.split(":", 2)[2]
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == call.from_user.id).first()
        if user:
            user.reminder_time = pref
            session.commit()
    await state.update_data(workout_time=pref)

    # Calculating message
    await call.message.edit_text(t(lang, "onb_calculating"))
    await call.answer()
    await asyncio.sleep(3)

    data = await state.get_data()
    
    # Calculate BMI
    try:
        height_m = float(data.get("height", 0)) / 100.0
        weight = float(data.get("weight", 0))
        bmi = round(weight / (height_m ** 2), 1) if height_m > 0 else 0.0
    except Exception:
        bmi = 0.0

    # Determine BMI category text
    if bmi < 18:
        bmi_note = t(lang, "onb_bmi_under")
    elif 18.5 <= bmi <= 24.9:
        bmi_note = t(lang, "onb_bmi_normal")
    elif 25 <= bmi <= 29.9:
        bmi_note = t(lang, "onb_bmi_over")
    else:
        bmi_note = t(lang, "onb_bmi_other")

    # Build final message without sleep analysis (removed sleep questions)
    final_text = t(lang, "onb_final", name=data.get("name", "Friend"))
    final_text += "\n\n" + t(lang, "onb_bmi_title", bmi=bmi)
    final_text += "\n" + t(lang, "onb_bmi_desc")
    final_text += "\n\n" + bmi_note

    await call.message.edit_text(final_text)
    
    # Show main menu keyboard
    from .menu import build_main_menu_kb
    
    keyboard = build_main_menu_kb(lang)
    await call.message.answer(t(lang, "menu.welcome"), reply_markup=keyboard)
    
    await state.clear()
