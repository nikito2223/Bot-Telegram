from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler, CallbackContext
from db_manager.db_manager import DatabaseManager
import mysql.connector
import settings

CHOOSE_ITEM, ENTER_QUANTITY, CONFIRM_PURCHASE = range(3)

db = DatabaseManager()

# --- Универсальные функции для действий ---
async def add_carpets(user_id, amount):
    db.update_user_resources(user_id, carpets=amount)  # убрал await

async def add_newbies(user_id, amount):
    db.update_user_resources(user_id, newbies=amount)  # убрал await

async def grant_vip(user_id, _=None):
    db.update_user_field(user_id, 'is_vip', 1)  # убрал await


# --- Каталог товаров ---
ITEMS_CATALOG = {
    "1": {"name": "🦊Ковики", "price": 1000, "currency": "newbies", "requires_quantity": False, "action": add_carpets},
    "2": {"name": "VIP статус", "price": 100, "currency": "carpets", "requires_quantity": False, "action": grant_vip},
    "3": {"name": "Обмен ковиков → новики (17%)", "price": 0, "currency": "carpets", "requires_quantity": False, "action": lambda uid, qty: exchange_currency(uid, "carpets", "newbies", qty)}

}

COST_PER_CARPET = 1000  # новиков за 1 ковик
FEE_PERCENT = 17         # комиссия

# --- Магазин ---
async def shop(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_data = db.get_user_data(user_id)
    if not user_data:
        await update.message.reply_text(
            "Ошибка: пользователь не найден. Напишите /start"
        )
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton(f"{item['name']} - {item['price']} {item['currency']}", callback_data=item_id)]
        for item_id, item in ITEMS_CATALOG.items()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Ваш баланс:\n👾Новики: {user_data['newbies']}\n🦊Ковики: {user_data['carpets']}\n\n"
        "Добро пожаловать в магазин! Выберите товар:",
        reply_markup=reply_markup
    )
    return CHOOSE_ITEM

# --- Выбор товара ---
async def choose_item(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    item_id = query.data
    item = ITEMS_CATALOG.get(item_id)
    if not item:
        await query.edit_message_text("Товар не найден.")
        return ConversationHandler.END

    context.user_data['item'] = item
    context.user_data['item_id'] = item_id

    if item['requires_quantity']:
        await query.edit_message_text(f"Сколько вы хотите купить {item['name']}? Введите число.")
        return ENTER_QUANTITY
    else:
        keyboard = [
            [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_purchase")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel_purchase")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"Вы уверены, что хотите купить {item['name']} за {item['price']} {item['currency']}?",
            reply_markup=reply_markup
        )
        return CONFIRM_PURCHASE

# --- Ввод количества ---
async def enter_quantity(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    item = context.user_data['item']

    try:
        quantity = int(update.message.text)
        if quantity <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Введите корректное число.")
        return ENTER_QUANTITY

    user_data = db.get_user_data(user_id)

    # Если это обмен валют
    if item['action'].__name__ == "<lambda>" and "Обмен" in item['name']:
        success, exchanged_amount = item['action'](user_id, quantity)
        if not success:
            await update.message.reply_text(f"У вас недостаточно {item['currency']} для обмена. Нужно {exchanged_amount}.")
            return ConversationHandler.END
        await update.message.reply_text(f"Вы обменяли {quantity} {item['currency']} на {exchanged_amount} новиков (с комиссией 17%)")
        return ConversationHandler.END

    total_price = item['price'] * quantity
    if user_data[item['currency']] < total_price:
        await update.message.reply_text(f"У вас недостаточно {item['currency']} для этой покупки.")
        return ConversationHandler.END

    item['action'](user_id, quantity)
    db.update_user_resources(user_id, **{item['currency']: -total_price})
    await update.message.reply_text(f"Вы купили {quantity} {item['name']}!")
    return ConversationHandler.END

# --- Подтверждение покупки без количества ---
async def confirm_purchase(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    item = context.user_data['item']

    if query.data == "cancel_purchase":
        await query.edit_message_text("Покупка отменена.")
        return ConversationHandler.END

    # Проверка VIP
    user_data = db.get_user_data(user_id)
    if item['action'] == grant_vip and user_data.get('is_vip', 0) == 1:
        await query.edit_message_text("У вас уже есть VIP статус. Повторно купить нельзя.")
        return ConversationHandler.END

    if user_data[item['currency']] < item['price']:
        await query.edit_message_text(f"У вас недостаточно {item['currency']} для этой покупки.")
        return ConversationHandler.END

    await item['action'](user_id)  # если функция async
    db.update_user_resources(user_id, **{item['currency']: -item['price']})
    await query.edit_message_text(f"Вы успешно купили {item['name']}!")
    return ConversationHandler.END



def exchange_currency(user_id, from_currency, to_currency, amount):
    user_data = db.get_user_data(user_id)
    
    # Рассчитываем сколько новиков получаем за amount ковиков с комиссией
    exchanged_amount = int(amount * COST_PER_CARPET * (100 - FEE_PERCENT) / 100)
    
    if user_data[from_currency] < amount:
        return False, amount  # недостаточно ковиков
    
    db.update_user_resources(user_id, **{from_currency: -amount})
    db.update_user_resources(user_id, **{to_currency: exchanged_amount})
    
    return True, exchanged_amount


async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text("Покупка отменена.")
    return ConversationHandler.END