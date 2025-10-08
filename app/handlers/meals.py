"""
Meals handlers - complete meal tracking system.
"""
from aiogram import F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

from app.services.i18n import t
from app.services.meals import (
    get_user_budget, set_user_budget, get_meals_by_category, 
    get_meal_by_id, log_meal_pack, log_custom_meal, get_meal_stats
)
from app.database import SessionLocal
from app.models.user import User
from .start import router


def get_lang(user_id: int) -> str:
    """Get user language."""
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == user_id).first()
        return user.language if user and user.language else "ru"


class MealStates(StatesGroup):
    """FSM states for meal logging."""
    waiting_for_custom_description = State()
    waiting_for_health_rating = State()


# Button text collections for different languages
from app.services.i18n import T
MEALS_BTNS = {T[x]["btn_meals"] for x in T.keys()}


# Budget selection keyboard removed - budget is set during onboarding


def _build_category_kb(lang: str) -> InlineKeyboardMarkup:
    """Build category selection keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "meals.category.breakfast"), callback_data="meals:category:breakfast")],
        [InlineKeyboardButton(text=t(lang, "meals.category.lunch"), callback_data="meals:category:lunch")],
        [InlineKeyboardButton(text=t(lang, "meals.category.dinner"), callback_data="meals:category:dinner")],
    ])


def _build_pack_grid_kb(packs: list, lang: str, page: int = 0, packs_per_page: int = 6) -> InlineKeyboardMarkup:
    """Build pack grid keyboard with pagination."""
    start_idx = page * packs_per_page
    end_idx = start_idx + packs_per_page
    page_packs = packs[start_idx:end_idx]
    
    buttons = []
    for i in range(0, len(page_packs), 2):
        row = []
        for j in range(2):
            if i + j < len(page_packs):
                pack = page_packs[i + j]
                row.append(InlineKeyboardButton(
                    text=f"📦 {pack['pack_number']}",
                    callback_data=f"meals:pack:{pack['id']}"
                ))
        buttons.append(row)
    
    # Pagination buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"meals:page:{page-1}"))
    if end_idx < len(packs):
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"meals:page:{page+1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    # Custom meal button
    buttons.append([InlineKeyboardButton(text=t(lang, "meals.category.custom"), callback_data="meals:category:custom")])
    
    # Back button
    buttons.append([InlineKeyboardButton(text=t(lang, "menu.back"), callback_data="meals:back_to_categories")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _build_pack_detail_kb(pack_id: str, lang: str) -> InlineKeyboardMarkup:
    """Build pack detail keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "meals.done"), callback_data=f"meals:done:{pack_id}")],
        [InlineKeyboardButton(text=t(lang, "menu.back"), callback_data="meals:back_to_packs")],
    ])


def _build_custom_meal_kb(lang: str) -> InlineKeyboardMarkup:
    """Build custom meal category keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "meals.category.breakfast"), callback_data="meals:custom_category:breakfast")],
        [InlineKeyboardButton(text=t(lang, "meals.category.lunch"), callback_data="meals:custom_category:lunch")],
        [InlineKeyboardButton(text=t(lang, "meals.category.dinner"), callback_data="meals:custom_category:dinner")],
        [InlineKeyboardButton(text=t(lang, "menu.back"), callback_data="meals:back_to_categories")],
    ])


def _build_health_rating_kb(lang: str) -> InlineKeyboardMarkup:
    """Build health rating keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "meals.health.healthy"), callback_data="meals:health:healthy")],
        [InlineKeyboardButton(text=t(lang, "meals.health.normal"), callback_data="meals:health:normal")],
        [InlineKeyboardButton(text=t(lang, "meals.health.unhealthy"), callback_data="meals:health:unhealthy")],
        [InlineKeyboardButton(text=t(lang, "menu.back"), callback_data="meals:back_to_categories")],
    ])


def _build_back_to_menu_kb(lang: str) -> InlineKeyboardMarkup:
    """Build back to main menu keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "menu.back"), callback_data="meals:back_to_menu")],
    ])


async def open_meals_menu(message: types.Message, lang: str, reply_markup=None):
    """Open meals menu - called from main menu."""
    if reply_markup:
        await message.answer("🔽", reply_markup=reply_markup)
    
    # Show meals section with proper description
    text = f"{t(lang, 'meals.title')}\n\n{t(lang, 'meals.section_desc')}\n\n{t(lang, 'meals.choose_options')}"
    await message.answer(text, reply_markup=_build_category_kb(lang))


# Change budget handler removed - now only available in settings


# Budget selection handler removed - budget is set during onboarding


@router.callback_query(F.data.startswith("meals:category:"))
async def select_category(call: types.CallbackQuery, state: FSMContext):
    """Handle category selection."""
    lang = get_lang(call.from_user.id)
    category = call.data.split(":")[2]
    
    if category == "custom":
        # Start custom meal flow - ask what they ate directly
        await state.update_data(custom_category="breakfast")  # Default category
        await state.set_state(MealStates.waiting_for_custom_description)
        
        text = t(lang, "meals.custom.what_ate")
        
        # Delete the previous message and send new one
        try:
            await call.message.delete()
        except:
            pass
        
        await call.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "menu.back"), callback_data="meals:back_to_categories")]
        ]))
        return
    
    # Get user's budget (should always be set during onboarding)
    budget = get_user_budget(call.from_user.id)
    if not budget:
        # Fallback to mid budget if somehow not set
        budget = "mid"
        set_user_budget(call.from_user.id, budget)
    
    packs = get_meals_by_category(budget, category)
    
    if not packs:
        text = t(lang, "meals.no_packs")
        if call.message.text:
            await call.message.edit_text(text, reply_markup=_build_back_to_menu_kb(lang))
        else:
            await call.message.answer(text, reply_markup=_build_back_to_menu_kb(lang))
        return
    
    # Show pack grid
    text = f"{t(lang, 'meals.category.' + category).title()}\n\n{t(lang, 'meals.choose_pack')}"
    
    if call.message.text:
        await call.message.edit_text(text, reply_markup=_build_pack_grid_kb(packs, lang))
    else:
        await call.message.answer(text, reply_markup=_build_pack_grid_kb(packs, lang))


@router.callback_query(F.data.startswith("meals:page:"))
async def change_page(call: types.CallbackQuery):
    """Handle pagination."""
    lang = get_lang(call.from_user.id)
    page = int(call.data.split(":")[2])
    
    # Get current category from message text
    budget = get_user_budget(call.from_user.id)
    if not budget:
        budget = "mid"  # Fallback
    
    # Extract category from message text (this is a bit hacky, but works)
    message_text = call.message.text or ""
    if "breakfast" in message_text.lower():
        category = "breakfast"
    elif "lunch" in message_text.lower():
        category = "lunch"
    elif "dinner" in message_text.lower():
        category = "dinner"
    else:
        category = "breakfast"  # default
    
    packs = get_meals_by_category(budget, category)
    
    text = f"{t(lang, 'meals.category.' + category).title()}\n\n{t(lang, 'meals.choose_pack')}"
    
    if call.message.text:
        await call.message.edit_text(text, reply_markup=_build_pack_grid_kb(packs, lang, page))
    else:
        await call.message.answer(text, reply_markup=_build_pack_grid_kb(packs, lang, page))


@router.callback_query(F.data.startswith("meals:pack:"))
async def show_pack_detail(call: types.CallbackQuery):
    """Show pack detail card."""
    lang = get_lang(call.from_user.id)
    pack_id = call.data.split(":")[2]
    
    pack = get_meal_by_id(pack_id)
    if not pack:
        await call.answer(t(lang, "meals.pack_not_found"))
        return
    
    # Build pack detail text
    text = f"📦 {t(lang, 'meals.pack')} {pack['pack_number']}: {pack['name']}\n"
    text += f"✨ {pack['short_desc']}\n"
    text += f"📌 {t(lang, 'meals.ingredients')}: {pack['ingredients']}\n"
    text += f"💰 {t(lang, 'meals.price')}: ~{pack['price']} {pack['currency']}\n"
    text += f"🔥 {t(lang, 'meals.calories')}: ~{pack['calories']} kcal\n"
    text += f"✅ {t(lang, 'meals.tags')}: {pack['flags']}\n"
    text += f"🕒 {t(lang, 'meals.prep_time')}: {pack['prep_time_min']} min\n"
    text += f"💡 {pack['notes']}"
    
    # Send photo if available
    if pack.get('image'):
        try:
            await call.message.answer_photo(
                photo=pack['image'],
                caption=text,
                reply_markup=_build_pack_detail_kb(pack_id, lang)
            )
        except:
            # Fallback to text if image fails
            await call.message.answer(
                text,
                reply_markup=_build_pack_detail_kb(pack_id, lang)
            )
    else:
        await call.message.answer(
            text,
            reply_markup=_build_pack_detail_kb(pack_id, lang)
        )


@router.callback_query(F.data.startswith("meals:done:"))
async def mark_meal_done(call: types.CallbackQuery):
    """Mark meal as done."""
    lang = get_lang(call.from_user.id)
    pack_id = call.data.split(":")[2]
    
    pack = get_meal_by_id(pack_id)
    if not pack:
        await call.answer(t(lang, "meals.pack_not_found"))
        return
    
    # Log the meal
    log_meal_pack(call.from_user.id, pack_id, pack['category'])
    
    # Show confirmation
    text = f"✅ {t(lang, 'meals.logged')}\n\n"
    text += f"📦 {pack['name']}\n"
    text += f"🔥 {pack['calories']} kcal\n"
    text += f"💰 {pack['price']} {pack['currency']}"
    
    await call.message.answer(text, reply_markup=_build_back_to_menu_kb(lang))


@router.callback_query(F.data.startswith("meals:custom_category:"))
async def select_custom_category(call: types.CallbackQuery, state: FSMContext):
    """Handle custom meal category selection."""
    lang = get_lang(call.from_user.id)
    category = call.data.split(":")[2]
    
    await state.update_data(custom_category=category)
    await state.set_state(MealStates.waiting_for_custom_description)
    
    text = t(lang, "meals.custom.what_ate")
    
    if call.message.text:
        await call.message.edit_text(text, reply_markup=_build_back_to_menu_kb(lang))
    else:
        await call.message.answer(text, reply_markup=_build_back_to_menu_kb(lang))


@router.message(MealStates.waiting_for_custom_description)
async def process_custom_description(message: types.Message, state: FSMContext):
    """Process custom meal description."""
    lang = get_lang(message.from_user.id)
    
    await state.update_data(custom_description=message.text)
    await state.set_state(MealStates.waiting_for_health_rating)
    
    text = f"{t(lang, 'meals.custom.health_rating')}\n\n"
    text += f"🍎 {t(lang, 'meals.health.healthy')}\n"
    text += f"😐 {t(lang, 'meals.health.normal')}\n"
    text += f"🍔 {t(lang, 'meals.health.unhealthy')}"
    
    await message.answer(text, reply_markup=_build_health_rating_kb(lang))


@router.callback_query(F.data.startswith("meals:health:"))
async def process_health_rating(call: types.CallbackQuery, state: FSMContext):
    """Process health rating for custom meal."""
    lang = get_lang(call.from_user.id)
    health_rating = call.data.split(":")[2]
    
    data = await state.get_data()
    custom_description = data.get('custom_description')
    custom_category = data.get('custom_category')
    
    if not custom_description or not custom_category:
        await call.answer(t(lang, "meals.error.missing_data"))
        return
    
    # Log the custom meal
    log_custom_meal(call.from_user.id, custom_description, custom_category, health_rating)
    
    # Show confirmation
    text = f"✅ {t(lang, 'meals.custom.logged')}\n\n"
    text += f"🍽️ {custom_description}\n"
    text += f"📅 {t(lang, 'meals.category.' + custom_category)}\n"
    text += f"💚 {t(lang, 'meals.health.' + health_rating)}"
    
    await call.message.answer(text, reply_markup=_build_back_to_menu_kb(lang))
    
    await state.clear()


@router.callback_query(F.data == "meals:back_to_categories")
async def back_to_categories(call: types.CallbackQuery):
    """Go back to category selection."""
    lang = get_lang(call.from_user.id)
    # Delete current message
    try:
        await call.message.delete()
    except:
        pass
    
    text = f"{t(lang, 'meals.title')}\n\n{t(lang, 'meals.choose_category')}"
    await call.message.answer(text, reply_markup=_build_category_kb(lang))


@router.callback_query(F.data == "meals:back_to_packs")
async def back_to_packs(call: types.CallbackQuery):
    """Go back to pack grid."""
    lang = get_lang(call.from_user.id)
    budget = get_user_budget(call.from_user.id)
    if not budget:
        budget = "mid"  # Fallback
    
    # Delete current message
    try:
        await call.message.delete()
    except:
        pass
    
    # Default to breakfast, should be improved to remember context
    packs = get_meals_by_category(budget, "breakfast")
    
    text = f"{t(lang, 'meals.category.breakfast').title()}\n\n{t(lang, 'meals.choose_pack')}"
    await call.message.answer(text, reply_markup=_build_pack_grid_kb(packs, lang))


@router.callback_query(F.data == "meals:back_to_menu")
async def back_to_menu(call: types.CallbackQuery):
    """Go back to main menu."""
    lang = get_lang(call.from_user.id)
    # Delete current message
    try:
        await call.message.delete()
    except:
        pass
    
    text = f"{t(lang, 'meals.title')}\n\n{t(lang, 'meals.choose_category')}"
    await call.message.answer(text, reply_markup=_build_category_kb(lang))


# Meal reminder handlers
@router.callback_query(F.data.startswith("meals:reminder:"))
async def handle_meal_reminder(call: types.CallbackQuery):
    """Handle meal reminder button clicks."""
    lang = get_lang(call.from_user.id)
    action = call.data.split(":")[2]
    
    if action == "later":
        await call.answer(t(lang, "meals.reminder.later_response"))
        return
    
    # Extract meal type from action
    meal_type = action  # breakfast, lunch, or dinner
    
    # Show quick meal logging interface
    text = f"{t(lang, 'meals.reminder.quick_log')}\n\n{t(lang, 'meals.category.' + meal_type)}"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "meals.reminder.quick_pack"), callback_data=f"meals:quick_pack:{meal_type}")],
        [InlineKeyboardButton(text=t(lang, "meals.reminder.quick_custom"), callback_data=f"meals:quick_custom:{meal_type}")],
        [InlineKeyboardButton(text=t(lang, "meals.reminder.skip"), callback_data="meals:reminder:skip")]
    ])
    
    if call.message.text:
        await call.message.edit_text(text, reply_markup=kb)
    else:
        await call.message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("meals:quick_pack:"))
async def quick_pack_selection(call: types.CallbackQuery):
    """Quick pack selection for reminders."""
    lang = get_lang(call.from_user.id)
    meal_type = call.data.split(":")[2]
    
    budget = get_user_budget(call.from_user.id)
    if not budget:
        budget = "mid"  # Fallback
    
    packs = get_meals_by_category(budget, meal_type)
    
    if not packs:
        await call.answer(t(lang, "meals.no_packs"))
        return
    
    # Show first 3 packs for quick selection
    quick_packs = packs[:3]
    text = f"{t(lang, 'meals.reminder.quick_select')}\n\n"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📦 {pack['pack_number']}: {pack['name']}", callback_data=f"meals:quick_done:{pack['id']}")]
        for pack in quick_packs
    ] + [[InlineKeyboardButton(text=t(lang, "menu.back"), callback_data=f"meals:reminder:{meal_type}")]])
    
    if call.message.text:
        await call.message.edit_text(text, reply_markup=kb)
    else:
        await call.message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("meals:quick_done:"))
async def quick_pack_done(call: types.CallbackQuery):
    """Mark pack as done from reminder."""
    lang = get_lang(call.from_user.id)
    pack_id = call.data.split(":")[2]
    
    pack = get_meal_by_id(pack_id)
    if not pack:
        await call.answer(t(lang, "meals.pack_not_found"))
        return
    
    # Log the meal
    log_meal_pack(call.from_user.id, pack_id, pack['category'])
    
    # Show confirmation
    text = f"✅ {t(lang, 'meals.reminder.logged')}\n\n"
    text += f"📦 {pack['name']}\n"
    text += f"🔥 {pack['calories']} kcal"
    
    await call.message.answer(text)


@router.callback_query(F.data.startswith("meals:quick_custom:"))
async def quick_custom_meal(call: types.CallbackQuery, state: FSMContext):
    """Quick custom meal logging from reminder."""
    lang = get_lang(call.from_user.id)
    meal_type = call.data.split(":")[2]
    
    await state.update_data(custom_category=meal_type)
    await state.set_state(MealStates.waiting_for_custom_description)
    
    text = t(lang, "meals.custom.what_ate")
    
    if call.message.text:
        await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "menu.back"), callback_data=f"meals:reminder:{meal_type}")]
        ]))
    else:
        await call.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "menu.back"), callback_data=f"meals:reminder:{meal_type}")]
        ]))