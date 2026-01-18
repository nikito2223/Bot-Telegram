from db_manager.db_manager import DatabaseManager
from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler
from telegram.constants import ParseMode
import os
import settings
import datetime

db = DatabaseManager()
AVATAR, NAME, DESCRIPTION, HEALTH, DAMAGE, WEAKNESSES, ABILITIES, SKILLS = range(8)


def is_action_allowed(user_id, action, limit, vip_status):
    """Проверка лимита действий пользователя."""
    if vip_status:
        return True, "Вы можете выполнять это действие без ограничений благодаря VIP-статусу."

    conn = db.get_connection()
    cursor = conn.cursor(dictionary=True)

    limit_time = datetime.datetime.now() - datetime.timedelta(hours=24)
    cursor.execute(
        "SELECT COUNT(*) AS action_count FROM user_actions "
        "WHERE user_id=%s AND action=%s AND timestamp > %s",
        (user_id, action, limit_time)
    )
    result = cursor.fetchone()
    cursor.close()
    conn.close()

    count = result["action_count"] if result else 0
    if count >= limit:
        return False, "Вы превысили лимит действий за 24 часа."
    return True, "Вы можете выполнить это действие."


def log_user_action(user_id, action):
    """Логирование действия пользователя."""
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO user_actions (user_id, action, timestamp) VALUES (%s, %s, %s)",
        (user_id, action, datetime.datetime.now())
    )
    conn.commit()
    cursor.close()
    conn.close()


async def start(update: Update, context: CallbackContext):
    """Приветствие и создание профиля пользователя."""
    await update.message.reply_text(
        "👋 Привет! Добро пожаловать!\n"
        "/profile - Просмотр профиля 👤\n"
        "/create - Создать персонажа ✍️\n"
        "/list - Посмотреть персонажей 📜\n"
        "/show <id> - Подробности о персонаже 📖\n"
        "/delete <id> - Удалить персонажа ❌\n"
        "/top - Топ пользователей 👥"
    )
    await db.create_profile(update, context)


async def create(update: Update, context: CallbackContext):
    """Начало создания персонажа."""
    user_id = update.message.from_user.id
    action = "create_character"
    limit = 10

    user_data = DatabaseManager.get_user_data(user_id)
    vip_status = user_data.get("is_vip", False) if user_data else False

    allowed, message = is_action_allowed(user_id, action, limit, vip_status)
    if not allowed:
        await update.message.reply_text(message)
        return ConversationHandler.END

    log_user_action(user_id, action)
    await update.message.reply_text("Давайте создадим вашего персонажа! Отправьте аватарку.")
    return AVATAR


async def avatar(update: Update, context: CallbackContext):
    """Обработка аватара персонажа."""
    if not update.message.photo:
        await update.message.reply_text("Пожалуйста, отправьте изображение для аватара.")
        return AVATAR

    file = await update.message.photo[-1].get_file()
    user_id = update.message.from_user.id
    temp_folder = f"D:/wamp64/www/BotPerson/avatars/temp/temp_{user_id}"
    os.makedirs(temp_folder, exist_ok=True)
    temp_path = os.path.join(temp_folder, f"temp_{user_id}_avatar.jpg")
    await file.download_to_drive(temp_path)

    context.user_data['temp_avatar'] = temp_path
    await update.message.reply_text("Введите имя персонажа:")
    return NAME


async def name(update: Update, context: CallbackContext):
    """Обработка имени персонажа."""
    name_text = update.message.text.strip()
    user_id = update.message.from_user.id

    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM characters WHERE name=%s AND user_id=%s",
        (name_text, user_id)
    )
    if cursor.fetchone()[0] > 0:
        await update.message.reply_text(f"Персонаж с именем '{name_text}' уже существует. Введите другое имя.")
        cursor.close()
        conn.close()
        return NAME

    context.user_data['name'] = name_text

    temp_avatar = context.user_data.get('temp_avatar')
    if temp_avatar:
        user_folder = f"D:/wamp64/www/BotPerson/avatars/{user_id}"
        os.makedirs(user_folder, exist_ok=True)
        avatar_path = os.path.join(user_folder, f"{name_text}_avatar.jpg")
        if os.path.exists(avatar_path):
            os.remove(avatar_path)
        os.rename(temp_avatar, avatar_path)
        context.user_data['avatar'] = avatar_path
    else:
        await update.message.reply_text("Аватар не найден. Начните процесс заново.")
        cursor.close()
        conn.close()
        return AVATAR

    cursor.close()
    conn.close()
    await update.message.reply_text("Введите описание персонажа:")
    return DESCRIPTION


async def description(update: Update, context: CallbackContext):
    context.user_data['description'] = update.message.text
    await update.message.reply_text("Введите количество здоровья персонажа:")
    return HEALTH


async def health(update: Update, context: CallbackContext):
    try:
        health_val = int(update.message.text)
        if health_val > settings.MAX_HEALTH:
            await update.message.reply_text(f"Лимит здоровья: {settings.MAX_HEALTH}. Введите снова:")
            return HEALTH
        context.user_data['health'] = health_val
        await update.message.reply_text("Введите урон персонажа:")
        return DAMAGE
    except ValueError:
        await update.message.reply_text("Введите корректное число для здоровья.")
        return HEALTH


async def damage(update: Update, context: CallbackContext):
    try:
        damage_val = int(update.message.text)
        if damage_val > settings.MAX_DAMAGE:
            await update.message.reply_text(f"Лимит урона: {settings.MAX_DAMAGE}. Введите снова:")
            return DAMAGE
        context.user_data['damage'] = damage_val
        await update.message.reply_text("Введите слабости персонажа:")
        return WEAKNESSES
    except ValueError:
        await update.message.reply_text("Введите корректное число для урона.")
        return DAMAGE


async def weaknesses(update: Update, context: CallbackContext):
    context.user_data['weaknesses'] = update.message.text
    await update.message.reply_text("Введите способности персонажа:")
    return ABILITIES


async def abilities(update: Update, context: CallbackContext):
    context.user_data['abilities'] = update.message.text
    await update.message.reply_text("Введите навыки персонажа:")
    return SKILLS


async def skills(update: Update, context: CallbackContext):
    """Финальный шаг — сохранение персонажа в базе."""
    context.user_data['skills'] = update.message.text
    user_id = update.message.from_user.id
    char_id = db.save_character_to_db(context.user_data, user_id)

    msg = (
        f"<b>Персонаж создан!</b>\n\n"
        f"🆔 ID: {char_id}\n"
        f"🏷️ Имя: {context.user_data['name']}\n"
        f"📝 Описание: {context.user_data['description']}\n"
        f"❤️ Здоровье: {context.user_data['health']}\n"
        f"🔪 Урон: {context.user_data['damage']}\n"
        f"🧠 Способности: {context.user_data['abilities']}\n"
        f"⚒️ Навыки: {context.user_data['skills']}\n"
        f"😵 Слабости: {context.user_data['weaknesses']}"
    )

    with open(context.user_data['avatar'], 'rb') as img:
        await update.message.reply_photo(photo=img, caption=msg, parse_mode=ParseMode.HTML)

    await update.message.reply_text("Персонаж успешно создан! /create — чтобы создать нового.")
    return ConversationHandler.END


async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text("Создание персонажа отменено.")
    return ConversationHandler.END
