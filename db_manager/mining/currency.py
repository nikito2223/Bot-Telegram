from telegram import Update
from telegram.ext import ConversationHandler
import mysql.connector
import settings
from telegram.ext import ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Подключение к базе данных
def get_user_data(user_id):
    conn = mysql.connector.connect(
        host=settings.Host,
        user=settings.User,
        password=settings.Password,
        database=settings.Database
    )
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    return user_data

# Каталог товаров
ITEMS_CATALOG = {
    "1": {"name": "🦊Ковики", "price": 1000, "currency": "newbies", "buy-count": "yes", "action": "buy-carpet", "currency-trasform": "Новиков👾"},
    "2": {"name": "Вип", "price": 100, "currency": "carpets", "buy-count": "no", "action": "buy-vip", "currency-trasform": "Ковиков🦊"}
}

CHOOSE_ITEM, ENTER_QUANTITY, BUY_VIP = range(3)

# Обработчик команды /shop
async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for item_id, item in ITEMS_CATALOG.items():
        button_text = f"{item['name']} - {item['price']} {item['currency-trasform']}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=item_id)])

    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    if not user_data:
        await update.message.reply_text("Ошибка: пользователь не найден.\nПожалуста введите в личных сообщениях бота - **/start**")
        return

    newbies = user_data.get("newbies", 0)
    carpets = user_data.get("carpets", 0)

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"Ваш баланс:\n👾Новики: {newbies}\n🦊Ковики: {carpets}\n\nДобро пожаловать в магазин! Выберите товар:", reply_markup=reply_markup)
    return CHOOSE_ITEM

# Выбор товара
async def choose_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    item_id = query.data
    item = ITEMS_CATALOG.get(item_id)

    if not item:
        await query.edit_message_text("Ошибка: товар не найден.")
        return ConversationHandler.END

    context.user_data["item_id"] = item_id
    context.user_data["action"] = item["action"]
    context.user_data["price"] = item["price"]
    context.user_data["currency"] = item["currency"]

    if item["buy-count"] == "no":
        await query.edit_message_text(
            f"Вы уверены, что хотите купить {item['name']} за {item['price']} {item['currency']}? Ответьте 'да' или 'нет'."
        )
        return ENTER_QUANTITY
    else:
        await query.edit_message_text(f"Сколько вы хотите купить {item['name']}? Введите число.")
        return ENTER_QUANTITY

# Подтверждение покупки
async def confirm_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    if not user_data:
        await update.message.reply_text("Ошибка: пользователь не найден.")
        return ConversationHandler.END

    currency = context.user_data["currency"]
    balance = user_data[currency]
    price = context.user_data["price"]
    action = context.user_data["action"]

    user_response = update.message.text.lower()

    if action == "buy-vip":
        if user_response == "да":
            if balance < price:
                await update.message.reply_text(f"У вас недостаточно {currency} для этой покупки.")
                return ConversationHandler.END
            if user_data['is_vip'] == 0:
                await execute_action(user_id, action, 1)
                await update_balance(user_id, -price, currency)
                await assign_vip_status(user_id)
                await update.message.reply_text("Вы успешно приобрели VIP статус!")
            else:
                await update.message.reply_text("У вас уже есть вип.")

        elif user_response == "нет":
            await update.message.reply_text("Покупка отменена.")
        else:
            await update.message.reply_text("Пожалуйста, ответьте 'да' или 'нет'.")
            return ENTER_QUANTITY


        return ConversationHandler.END
    else:
        # Логика для товаров с указанием количества
        try:
            quantity = int(update.message.text)
            if quantity <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("Введите корректное число.")
            return ENTER_QUANTITY
    
        total_cost = price * quantity
    
        if balance < total_cost:
            await update.message.reply_text(f"У вас недостаточно {currency} для этой покупки.")
            return ConversationHandler.END

        await execute_action(user_id, action, quantity)
        await update_balance(user_id, -total_cost, currency)
        await update.message.reply_text(f"Вы успешно купили {quantity} {ITEMS_CATALOG[context.user_data['item_id']]['name']}.")
        return ConversationHandler.END


# Отмена покупки
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Покупка отменена.")
    return ConversationHandler.END

# Выполнение действия
async def execute_action(user_id, action, amount):
    if action == "buy-carpet":
        await update_balance(user_id, amount, "carpets")
        return True
    elif action == "buy-vip":
        await assign_vip_status(user_id)
        return True
    return False

async def assign_vip_status(user_id):
    conn = mysql.connector.connect(
        host=settings.Host,
        user=settings.User,
        password=settings.Password,
        database=settings.Database
    )
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_vip = 1 WHERE user_id = %s", (user_id,))
    conn.commit()
    conn.close()


# Обновление баланса
async def update_balance(user_id, amount, currency):
    conn = mysql.connector.connect(
        host=settings.Host,
        user=settings.User,
        password=settings.Password,
        database=settings.Database
    )
    cursor = conn.cursor()

    if currency == "newbies":
        cursor.execute("UPDATE users SET newbies = newbies + %s WHERE user_id = %s", (amount, user_id))
    elif currency == "carpets":
        cursor.execute("UPDATE users SET carpets = carpets + %s WHERE user_id = %s", (amount, user_id))

    conn.commit()
    conn.close()
