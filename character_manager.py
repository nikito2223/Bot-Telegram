from db_manager.db_manager import DatabaseManager
from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler
from telegram.constants import ParseMode
import settings
import mysql.connector
import os

import datetime

db = DatabaseManager()
AVATAR, NAME, DESCRIPTION, HEALTH, ABILITIES, SKILLS, DAMAGE, WEAKNESSES = range(8)

def is_action_allowed(user_id, action, limit, vip_status):

    if vip_status:
        return True, "Вы можете выполнять это действие без ограничений благодаря VIP-статусу."

    conn = mysql.connector.connect(
        host=settings.Host,
        user=settings.User,
        password=settings.Password,
        database=settings.Database
    )
    cursor = conn.cursor(dictionary=True)

    # Получаем время 24 часа назад
    limit_time = datetime.datetime.now() - datetime.timedelta(hours=24)

    # Проверяем количество действий за последние 24 часа
    cursor.execute(
        """
        SELECT COUNT(*) as action_count 
        FROM user_actions 
        WHERE user_id = %s AND action = %s AND timestamp > %s
        """,
        (user_id, action, limit_time)
    )
    result = cursor.fetchone()
    conn.close()

    action_count = result["action_count"] if result else 0

    if action_count >= limit:
        return False, "Вы превысили лимит выполнения этого действия. Попробуйте снова через 24 часа."

    return True, "Вы можете выполнить это действие."

def log_user_action(user_id, action):
    """
    Логирует действие пользователя.

    :param user_id: ID пользователя
    :param action: Название действия (например, "buy_card")
    """
    conn = mysql.connector.connect(
        host=settings.Host,
        user=settings.User,
        password=settings.Password,
        database=settings.Database
    )
    cursor = conn.cursor()

    # Логируем действие
    cursor.execute(
        "INSERT INTO user_actions (user_id, action, timestamp) VALUES (%s, %s, %s)",
        (user_id, action, datetime.datetime.now())
    )
    conn.commit()
    conn.close()


async def create(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    action = "create_character"
    limit = 10

    # Получение данных пользователя
    user_data = DatabaseManager.get_user_data(user_id)
    vip_status = user_data[8] = False

    # Проверяем, может ли пользователь выполнить действие
    allowed, message = is_action_allowed(user_id, action, limit, vip_status)

    if not allowed:
        await update.message.reply_text(message)
        return ConversationHandler.END

    # Логируем действие, так как пользователь может его выполнить
    log_user_action(user_id, action)

    await update.message.reply_text("Давайте создадим вашего персонажа! Пожалуйста, укажите аватарку будущего персонажа.")
    return AVATAR

    
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "👋 Привет! Добро пожаловать в нашего бота для создания персонажей! Здесь ты можешь создавать уникальных персонажей с использованием разных характеристик.\n"
        "/profile - Для просмотра профиля 👤\n"
        "/create - Начать создание персонажа ✍️\n"
        "/list - Посмотреть всех созданных персонажей 📜\n"
        "/show <id> - Показать подробности о персонаже 📖\n"
        "/delete <id> - Удалить персонажа ❌\n"
        "/top - Топ по персонажам 👥"
    )
    await DatabaseManager.create_profile(update,context)         

async def avatar(update: Update, context: CallbackContext):
    # Ensure the user sent an image
    if update.message.photo:
        # Get the highest quality photo (last in the list of photo sizes)
        file = await update.message.photo[-1].get_file()

        # Create a folder for the user's ID
        user_id = update.message.from_user.id
        user_folder = f"D:/wamp64/www/BotPerson/avatars/temp/temp_{user_id}"
        os.makedirs(user_folder, exist_ok=True)

        # Specify a temporary name for the file path
        temp_avatar_path = os.path.join(user_folder, f"temp_{user_id}_avatar.jpg")

        # Download the file asynchronously and save it to the specified path
        await file.download_to_drive(temp_avatar_path)

        # Store the temporary file path in the user data for later use
        context.user_data['temp_avatar'] = temp_avatar_path

        # Prompt for name next
        await update.message.reply_text("Пожалуйста, укажите имя персонажа.")
        return NAME
    else:
        await update.message.reply_text("Пожалуйста, отправьте изображение для аватара персонажа.")
        return AVATAR

# Handle the character name input
async def name(update: Update, context: CallbackContext):
    user_name = update.message.text.strip()
    user_id = update.message.from_user.id

    # Подключение к базе данных
    conn = mysql.connector.connect(
        host=settings.Host,
        user=settings.User,
        password=settings.Password,
        database=settings.Database
    )
    cursor = conn.cursor()

    # Проверка на наличие персонажа с таким именем у пользователя
    cursor.execute(
        "SELECT COUNT(*) FROM characters WHERE name = %s AND user_id = %s",
        (user_name, user_id)
    )
    result = cursor.fetchone()
    if result[0] > 0:
        # Если имя уже существует, отправляем сообщение об ошибке
        # Если имя уже существует, отправляем сообщение об ошибке
        await update.message.reply_text(
            f"У вас уже есть персонаж с именем '{user_name}'. Пожалуйста, выберите другое имя."
        )
        conn.close()
        return NAME

    # Если имя уникально, продолжаем
    context.user_data['name'] = user_name

    # Get the temporary avatar path
    temp_avatar_path = context.user_data.get('temp_avatar')
    if temp_avatar_path:
        # Создаём папку пользователя
        user_folder = f"D:/wamp64/www/BotPerson/avatars/{user_id}"
        os.makedirs(user_folder, exist_ok=True)

        # Определяем путь для нового аватара
        new_avatar_path = os.path.join(user_folder, f"{user_name}_avatar.jpg")

        # Удаляем существующий файл, если он есть
        if os.path.exists(new_avatar_path):
            os.remove(new_avatar_path)

        # Переименовываем временный файл
        os.rename(temp_avatar_path, new_avatar_path)

        # Сохраняем путь к аватару
        context.user_data['avatar'] = new_avatar_path

    else:
        await update.message.reply_text("Аватар не найден. Пожалуйста, начните процесс заново.")
        conn.close()
        return AVATAR

    # Закрываем соединение с базой
    conn.close()

    # Переходим к следующему шагу (описание персонажа)
    await update.message.reply_text("Теперь, пожалуйста, введите описание персонажа.")
    return DESCRIPTION

# Handle the character description input
async def description(update: Update, context: CallbackContext):
    user_description = update.message.text
    context.user_data['description'] = user_description
    await update.message.reply_text(f"Теперь введите количество здоровья персонажа.")
    return HEALTH

# Handle the character health input
async def health(update: Update, context: CallbackContext):
    try:
        user_health = int(update.message.text)
        context.user_data['health'] = user_health
        if(user_health > settings.MAX_HEALTH):
            await update.message.reply_text(f"Лимит превышен, пожалуста укажите здоровья до {settings.MAX_HEALTH}.")
            return HEALTH
        else:
            await update.message.reply_text("Теперь введите количество урона персонажа.")
            return DAMAGE
        
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите правильное значение для здоровья. Не буками")
        return HEALTH

async def damage(update: Update, context: CallbackContext):
    try:
        user_damage = int(update.message.text)
        context.user_data['damage'] = user_damage
        if(user_damage > settings.MAX_HEALTH):
            await update.message.reply_text(f"Лимит превышен, пожалуста укажите урона до {settings.MAX_DAMAGE}.")
            return DAMAGE
        else:
            await update.message.reply_text("Теперь, пожалуйста, укажите слабости вашего персонажа.")
            return WEAKNESSES
            
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите правильное значение для урон. Не буками")
        return DAMAGE
        
# Handle the character abilities input
async def abilities(update: Update, context: CallbackContext):
    user_abilities = update.message.text
    context.user_data['abilities'] = user_abilities
    await update.message.reply_text(f"Теперь, пожалуйста, укажите навыки вашего персонажа.")
    return SKILLS
    
async def weaknesses(update: Update, context: CallbackContext):
    user_weaknesses = update.message.text
    context.user_data['weaknesses'] = user_weaknesses
    await update.message.reply_text(f"Теперь, пожалуйста, укажите способности вашего персонажа.")
    return ABILITIES

# Handle the character skills input
async def skills(update: Update, context: CallbackContext):
    user_skills = update.message.text
    context.user_data['skills'] = user_skills

    # Save the character to the database
    character = context.user_data
    user_id = update.message.from_user.id  # Get the user ID for saving the character
    character_id = DatabaseManager.save_character_to_db(character, user_id)  # Передача user_id в функцию


    # Send confirmation message with the character info
    message = (
        f"<b>Персонаж создан!</b>\n\n"
        f"<b>🆔ID:</b> {character_id}\n"  # Include the new ID in the message
        f"<b>🏷️Имя:</b> {character['name']}\n"
        f"<b>📝Описание:</b> {character['description']}\n"
        f"<b>❤️Здоровье:</b> {character['health']}\n"
        f"<b>🔪Урон:</b> {character['damage']}\n"
        f"<b>🧠Способности:</b> {character['abilities']}\n"
        f"<b>⚒️Навыки:</b> {character['skills']}\n\n"
        f"<b>😵Слабости:</b> {character['weaknesses']}\n\n"
    )

    # Send the avatar image first
    with open(character['avatar'], 'rb') as avatar_file:
        await update.message.reply_photo(
            photo=avatar_file,
            caption=message,  # Include the character info message
            parse_mode=ParseMode.HTML  # Use HTML for rich text formatting
        )

    await update.message.reply_text(
        "Ваш персонаж успешно создан!\n"
        "Используйте команду /create, чтобы создать другого персонажа."
    )

    return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text("Создание персонажа отменено.")
    return ConversationHandler.END
