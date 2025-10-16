"""
Meals handlers - complete meal tracking system.
"""
from aiogram import F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, InputMediaPhoto, FSInputFile

from app.services.i18n import t
from app.services.meals import (
    get_user_budget, set_user_budget, get_meals_by_category, 
    get_meal_by_id, log_meal_pack, log_custom_meal, get_meal_stats,
    _extract_calories_from_text, _extract_price_from_text
)
from app.database import SessionLocal
from app.models.user import User
from .start import router


def get_lang(user_id: int) -> str:
    """Get user language."""
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == user_id).first()
        return user.language if user and user.language else "ru"


def extract_calories_from_text(pack: dict) -> str:
    """Extract calories from meal text content."""
    try:
        text_content = pack.get('text_en', '')
        if 'Calories:' in text_content:
            # Find the line with calories
            for line in text_content.split('\n'):
                if 'Calories:' in line:
                    # Extract everything after "Calories:"
                    calories_text = line.split('Calories:')[1].strip()
                    return calories_text
        return 'N/A'
    except Exception as e:
        print(f"Error extracting calories: {e}")
        return 'N/A'


def extract_price_from_text(pack: dict) -> str:
    """Extract price from meal text content."""
    try:
        text_content = pack.get('text_en', '')
        if 'Price:' in text_content:
            # Find the line with price
            for line in text_content.split('\n'):
                if 'Price:' in line:
                    # Extract everything after "Price:"
                    price_text = line.split('Price:')[1].strip()
                    return price_text
        return 'N/A'
    except Exception as e:
        print(f"Error extracting price: {e}")
        return 'N/A'


def get_localized_name(pack: dict, lang: str) -> str:
    """Get localized meal name based on user language."""
    try:
        name_key = f"name_{lang}" if f"name_{lang}" in pack else "name_en"
        name = pack.get(name_key, pack.get("name_en", "Unknown"))
        return name
    except Exception as e:
        print(f"Error getting localized name: {e}")
        return "Unknown"


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


def _build_pack_grid_kb(packs: list, lang: str, page: int = 0, packs_per_page: int = 10) -> InlineKeyboardMarkup:
    """Build pack grid keyboard with pagination."""
    start_idx = page * packs_per_page
    end_idx = start_idx + packs_per_page
    page_packs = packs[start_idx:end_idx]
    
    buttons = []
    for i in range(0, len(page_packs), 5):
        row = []
        for j in range(5):
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
        # Show custom meal category selection
        text = f"{t(lang, 'meals.custom.category')}\n\n{t(lang, 'meals.choose_category')}"
        
        # Delete the previous message and send new one
        try:
            await call.message.delete()
        except:
            pass
        
        await call.message.answer(text, reply_markup=_build_custom_meal_kb(lang))
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
    
    # Get localized name and text
    name_key = f"name_{lang}" if lang in ['en', 'ru', 'uz'] else "name_en"
    text_key = f"text_{lang}" if lang in ['en', 'ru', 'uz'] else "text_en"
    
    name = pack.get(name_key, pack.get("name_en", "Unknown"))
    description = pack.get(text_key, pack.get("text_en", ""))
    
    # Build pack detail text
    text = f"📦 {t(lang, 'meals.pack')} {pack['pack_number']}: {name}\n\n"
    text += description
    
    # Delete the previous message and send new one with pack details
    try:
        await call.message.delete()
    except:
        pass  # Ignore if deletion fails
    
    # Send new message with pack details
    if pack.get('image'):

        try:
            # Create FSInputFile for local image
            image_path = pack['image']
            photo = FSInputFile(image_path)
            await call.message.answer_photo(
                photo=photo,
                caption=text,
                reply_markup=_build_pack_detail_kb(pack_id, lang)
            )
        except Exception as e:
            print(f"Error sending photo: {e}")
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
    try:
        lang = get_lang(call.from_user.id)
        pack_id = call.data.split(":")[2]
        
        pack = get_meal_by_id(pack_id)
        if not pack:
            await call.answer(t(lang, "meals.pack_not_found"))
            return
        
        # Log the meal
        try:
            log_meal_pack(call.from_user.id, pack_id, pack.get('category', 'unknown'))
        except Exception as e:
            print(f"Error logging meal: {e}")
            # Continue anyway, don't fail the whole operation
        
        # Show confirmation
        text = f"✅ {t(lang, 'meals.logged')}\n\n"
        
        # Get localized name
        name = get_localized_name(pack, lang)
        
        # Extract calories and price from text
        calories_text = extract_calories_from_text(pack)
        price_text = extract_price_from_text(pack)
        
        text += f"📦 {name}\n"
        text += f"🔥 {calories_text}"
        text += f"\n💰 {price_text}"
        
        # Delete the old message with buttons and send new confirmation
        try:
            await call.message.delete()
        except Exception as e:
            print(f"Error deleting message: {e}")
            # Continue anyway
        
        await call.message.answer(text, reply_markup=_build_back_to_menu_kb(lang))
        
    except Exception as e:
        print(f"Error in mark_meal_done: {e}")
        lang = get_lang(call.from_user.id) if 'lang' not in locals() else "ru"
        await call.message.answer(
            f"❌ {t(lang, 'meals.error.missing_data')}",
            reply_markup=_build_back_to_menu_kb(lang)
        )


@router.callback_query(F.data.startswith("meals:custom_category:"))
async def select_custom_category(call: types.CallbackQuery, state: FSMContext):
    """Handle custom meal category selection."""
    lang = get_lang(call.from_user.id)
    category = call.data.split(":")[2]
    
    await state.update_data(custom_category=category)
    await state.set_state(MealStates.waiting_for_custom_description)
    
    text = t(lang, "meals.custom.what_ate")
    
    if call.message.text:
        await call.message.edit_text(text)  # No buttons, just text
    else:
        await call.message.answer(text)  # No buttons, just text


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
    
    # Delete user's message and try to delete recent bot messages
    try:
        # Delete user's message
        await message.delete()
        
        # Try to delete the last few messages from bot (in case the question message is still there)
        # We'll try to delete messages with IDs close to the user's message
        for i in range(1, 4):  # Try to delete 3 previous messages
            try:
                await message.bot.delete_message(
                    chat_id=message.chat.id, 
                    message_id=message.message_id - i
                )
            except:
                # If we can't delete a message, just continue
                pass
    except Exception as e:
        # Log error for debugging but don't fail
        print(f"Error deleting messages: {e}")
        pass
    
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
    
    # Delete the previous message and send new one
    try:
        await call.message.delete()
    except:
        pass  # Ignore if deletion fails
    
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
    from .menu import build_main_menu_kb
    
    lang = get_lang(call.from_user.id)
    # Delete current message
    try:
        await call.message.delete()
    except:
        pass
    
    # Return to main menu with ReplyKeyboard
    kb = build_main_menu_kb(lang)
    await call.message.answer(t(lang, "menu.welcome"), reply_markup=kb)


# Meal reminder handlers - connected to new reminder system
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
    category_text = t(lang, f'meals.category.{meal_type}')
    text = f"{t(lang, 'meals.reminder.quick_log')}\n\n{category_text}"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "meals.reminder.quick_pack"), callback_data=f"meals:quick_pack:{meal_type}")],
        [InlineKeyboardButton(text=t(lang, "meals.reminder.quick_custom"), callback_data=f"meals:quick_custom:{meal_type}")],
        [InlineKeyboardButton(text=t(lang, "meals.reminder.skip"), callback_data="meals:reminder:skip")]
    ])
    
    try:
        if call.message.text:
            await call.message.edit_text(text, reply_markup=kb)
        else:
            await call.message.answer(text, reply_markup=kb)
    except Exception as e:
        # If edit fails (e.g., same content), just send new message
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
    
    # Show all packs for quick selection
    text = f"{t(lang, 'meals.reminder.quick_select')}\n\n"
    
    # Create keyboard with all packs (max 10 per page)
    kb_rows = []
    for pack in packs:
        pack_name = pack.get(f'name_{lang}', pack.get('name_en', 'Unknown'))
        kb_rows.append([InlineKeyboardButton(text=f"📦 {pack['pack_number']}: {pack_name}", callback_data=f"meals:quick_done:{pack['id']}")])
    
    # Add back button
    kb_rows.append([InlineKeyboardButton(text=t(lang, "menu.back"), callback_data=f"meals:reminder:{meal_type}")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)
    
    try:
        if call.message.text:
            await call.message.edit_text(text, reply_markup=kb)
        else:
            await call.message.answer(text, reply_markup=kb)
    except Exception as e:
        # If edit fails (e.g., same content), just send new message
        await call.message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("meals:quick_done:"))
async def quick_pack_done(call: types.CallbackQuery):
    """Mark pack as done from reminder."""
    try:
        lang = get_lang(call.from_user.id)
        pack_id = call.data.split(":")[2]
        
        pack = get_meal_by_id(pack_id)
        if not pack:
            await call.answer(t(lang, "meals.pack_not_found"))
            return
        
        # Log the meal
        try:
            log_meal_pack(call.from_user.id, pack_id, pack.get('category', 'unknown'))
            
            # Log notification response
            from app.services.reminders import log_notification
            log_notification(call.from_user.id, pack.get('category', 'unknown'), 'logged')
        except Exception as e:
            print(f"Error logging meal in reminder: {e}")
            # Continue anyway
        
        # Show confirmation
        text = f"✅ {t(lang, 'meals.reminder.logged')}\n\n"
        
        # Get localized name
        name = get_localized_name(pack, lang)
        
        # Extract calories from text
        calories_text = extract_calories_from_text(pack)
        
        text += f"📦 {name}\n"
        text += f"🔥 {calories_text}"
        
        # Delete the old message with buttons and send new confirmation
        try:
            await call.message.delete()
        except Exception as e:
            print(f"Error deleting message in reminder: {e}")
            # Continue anyway
        
        await call.message.answer(text)
        
    except Exception as e:
        print(f"Error in quick_pack_done: {e}")
        lang = get_lang(call.from_user.id) if 'lang' not in locals() else "ru"
        await call.message.answer(f"❌ {t(lang, 'meals.error.missing_data')}")


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


@router.callback_query(F.data == "meals:reminder:skip")
async def skip_meal_reminder(call: types.CallbackQuery):
    """Skip meal reminder."""
    lang = get_lang(call.from_user.id)
    
    # Log notification response
    try:
        from app.services.reminders import log_notification
        # Determine meal type from callback data or message text
        meal_type = "unknown"
        if "breakfast" in call.message.text.lower():
            meal_type = "breakfast"
        elif "lunch" in call.message.text.lower():
            meal_type = "lunch"
        elif "dinner" in call.message.text.lower():
            meal_type = "dinner"
        
        log_notification(call.from_user.id, meal_type, 'skipped')
    except Exception as e:
        print(f"Error logging skip: {e}")
    
    await call.answer(t(lang, "meals.reminder.skipped"))
    await call.message.delete()