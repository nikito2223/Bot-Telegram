import os
import mysql.connector
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import CallbackContext, ConversationHandler
from telegram import InputFile
import settings
from db_manager.db_manager import DatabaseManager

from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import random

db = DatabaseManager()

CHOOSE_AVATAR, UPLOAD_AVATAR = range(2)

# ------------------ Пользовательские функции ------------------

def get_total_characters(user_id: int) -> int:
    """Возвращает количество персонажей пользователя."""
    conn = mysql.connector.connect(
        host=settings.Host,
        user=settings.User,
        password=settings.Password,
        database=settings.Database
    )
    cursor = conn.cursor()
    cursor.execute("SELECT number_characters FROM users WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def get_vip_status(is_vip: int) -> str:
    return "Имеется" if is_vip else "Отсутствует"


# ------------------ Изменение аватара ------------------

async def choose_avatar(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    await query.edit_message_caption("Пожалуйста, отправьте новый аватар в формате изображения.")
    return UPLOAD_AVATAR

async def handle_new_avatar(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    photo = update.message.photo

    if not photo:
        await update.message.reply_text("Это не изображение. Пожалуйста, отправьте изображение.")
        return UPLOAD_AVATAR

    photo_file = photo[-1]
    file = await context.bot.get_file(photo_file.file_id)

    avatar_folder = "D:/wamp64/www/BotPerson/avatars/profile-users"
    os.makedirs(avatar_folder, exist_ok=True)
    new_avatar_path = os.path.join(avatar_folder, f"{user_id}.jpg")

    await file.download_to_drive(new_avatar_path)
    db.update_user_field(user_id, "avatar", new_avatar_path)

    await update.message.reply_text("Ваш аватар был успешно обновлён!", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# ------------------ Изменение статуса ------------------

async def edit_status(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    if len(context.args) != 2:
        await update.message.reply_text("Использование: /editStatus <user_id> <new_status>")
        return

    target_user_id, new_status = context.args
    try:
        target_user_id = int(target_user_id)
    except ValueError:
        await update.message.reply_text("ID пользователя должен быть числом.")
        return

    can_edit_status = db.check_admin_permission(user_id, "can_edit_status")
    if not can_edit_status:
        await update.message.reply_text("У вас нет прав на изменения статуса!")
        return

    if not db.user_exists(target_user_id):
        await update.message.reply_text(f"Пользователь с ID {target_user_id} не найден.")
        return

    db.update_user_field(target_user_id, "status", new_status)

    await update.message.reply_text(f"Статус пользователя с ID {target_user_id} успешно изменен на '{new_status}'.")

# ------------------ Просмотр чужого профиля ------------------

async def show_profile(update: Update, context: CallbackContext):
    requester_id = update.message.from_user.id
    target_user_id = None

    # ----------------- Определяем цель -----------------
    if context.args:
        arg = context.args[0]

        # Попытка по ID
        try:
            target_user_id = int(arg)
        except ValueError:
            # Если указали @username
            target_user_id = db.get_user_id_by_username(arg.lstrip("@"))
            if not target_user_id:
                await update.message.reply_text("Пользователь с таким именем не найден.")
                return

        # Если чужой профиль, проверяем права
        if target_user_id != requester_id:
            if not db.check_admin_permission(requester_id, "can_profile_check"):
                await update.message.reply_text("У вас нет прав для просмотра чужих профилей.")
                return
    else:
        # Если аргументов нет — свой профиль
        target_user_id = requester_id

    # ----------------- Получаем данные пользователя -----------------
    user_data = db.get_user_data(target_user_id)
    if not user_data:
        await update.message.reply_text(f"Пользователь с ID {target_user_id} не найден.")
        return

    avatar_path = user_data.get("avatar")
    vip_status = get_vip_status(user_data["is_vip"])

    message = (
        f"👤 <b>Имя пользователя:</b> {user_data['name']}\n"
        f"👑 <b>Статус:</b> {user_data['status']}\n"
        f"💎 <b>Вип:</b> {vip_status}\n"
        f"👥 <b>Количество персонажей:</b> {user_data['number_characters']}\n"
        f"🦊 <b>Ковики:</b> {user_data['carpets']}\n"
    )

    # ----------------- Кнопка смены аватарки -----------------
    is_own_profile = target_user_id == requester_id
    keyboard = None
    if target_user_id == requester_id:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Изменить аватарку", callback_data="change_avatar")]
        ])


    if avatar_path and os.path.exists(avatar_path):
        photo_to_send = open(avatar_path, 'rb')
    # иначе генерируем аватар на лету с инициалами
    else:
        photo_to_send = generate_avatar(user_data['name'])
        photo_to_send.seek(0)
    
    await update.message.reply_photo(
        photo=photo_to_send,
        caption=message,
        reply_markup=keyboard,
        parse_mode="HTML"
    )


    # ----------------- Возвращаем состояние для смены аватарки -----------------
    if target_user_id == requester_id: 
        return CHOOSE_AVATAR if is_own_profile else ConversationHandler.END 
    return ConversationHandler.END


# ------------------ Отмена действия ------------------

async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text("Действие отменено.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def generate_avatar(name: str, size=200) -> BytesIO:
    """Генерирует аватар с цветным фоном и первыми 2 буквами имени"""
    
    # Цвет фона (по ID или случайный)
    random.seed(name)  # чтобы один и тот же пользователь всегда один цвет
    r = random.randint(0, 255)
    g = random.randint(0, 255)
    b = random.randint(0, 255)
    bg_color = (r, g, b)

    # Создаём картинку
    img = Image.new("RGB", (size, size), color=bg_color)
    draw = ImageDraw.Draw(img)

    # Текст — первые 2 символа имени
    initials = name[:2].upper()

    # Шрифт (можно использовать стандартный PIL)
    try:
        font = ImageFont.truetype("arial.ttf", size // 2)
    except:
        font = ImageFont.load_default()

    # Размер текста
    text_width, text_height = draw.textsize(initials, font=font)

    # Позиция по центру
    x = (size - text_width) / 2
    y = (size - text_height) / 2

    draw.text((x, y), initials, fill="white", font=font)

    # Сохраняем в BytesIO
    bio = BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    return bio
