import mysql.connector

from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram import ReplyKeyboardRemove

import settings
import os

CHOOSE_AVATAR, UPLOAD_AVATAR = range(2)

def get_total_characters(user_id):
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

    if result:
        return result[0]  # Возвращает количество персонажей
    return 0  # Если пользователя нет в таблице

async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text("Действие отменено.")
    return ConversationHandler.END

async def show_user_profile(update: Update, context: CallbackContext):
        user_id = update.message.from_user.id  # Получаем ID пользователя
        vip_status = ''
        # Подключение к базе данных
        conn = mysql.connector.connect(
            host=settings.Host,
            user=settings.User,
            password=settings.Password,
            database=settings.Database
        )
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data:
            avatar_path = user_data[2]
            if user_data[8] == 0:
                vip_status = 'Отсуствует' 
            elif user_data[8] == 1:
                vip_status = "Имеется"
            # Отправляем аватарку и имя пользователя
            with open(avatar_path, 'rb') as avatar_file:
                message = (
                        f"👤 **<b>Имя пользователя: {user_data[1]}</b>\n"
                        f"👑**<b>Статус: {user_data[3]}</b>\n"
                        f"💎**<b>Вип: {vip_status}</b>\n"
                        f"👥**<b>Количество персонажей: {user_data[4]}</b>\n"
                        f"🦊**<b>Ковики: {user_data[5]}</b>\n"
                    )
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("Изменить аватарку", callback_data="change_avatar")],
                ])
                #reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
                await update.message.reply_photo(
                    photo=avatar_file,
                    reply_markup=keyboard,
                    caption = message,   
                    parse_mode="HTML"
                )

                return CHOOSE_AVATAR
        else:
            # Если пользователь не найден в базе
            await update.message.reply_text("Ваш профиль не найден в базе данных.\nПожалуста введите в личных сообщениях бота - **/start**")

    
async def choose_avatar(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()  # Ответ на callback обязательный!
    await query.edit_message_text("Пожалуйста, отправьте новый аватар в формате изображения.")
    return UPLOAD_AVATAR

async def handle_new_avatar(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    photo = update.message.photo

    if not photo:
        await update.message.reply_text("Это не изображение. Пожалуйста, отправьте изображение.")
        return UPLOAD_AVATAR

    # Получаем файл изображения
    photo_file = photo[-1]
    file = await context.bot.get_file(photo_file.file_id)

    # Сохраняем аватар в папку
    avatar_folder = "D:/wamp64/www/BotPerson/avatars/profile-users"
    os.makedirs(avatar_folder, exist_ok=True)
    new_avatar_path = os.path.join(avatar_folder, f"{user_id}.jpg")

    await file.download_to_drive(new_avatar_path)

    # Обновляем базу данных
    conn = mysql.connector.connect(
        host=settings.Host, user=settings.User, password=settings.Password, database=settings.Database
    )
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET avatar = %s WHERE user_id = %s", (new_avatar_path, user_id))
    conn.commit()
    conn.close()

    # Уведомляем пользователя об успехе
    await update.message.reply_text("Ваш аватар был успешно обновлён!")
    return ConversationHandler.END


async def remove_buttons(update: Update):
        # Удаляем все кнопки на экране
        await update.message.reply_text("Ваш аватар был успешно обновлён!", reply_markup=ReplyKeyboardRemove())

async def edit_status(update: Update, context: CallbackContext):
    
        userId = update.message.from_user.id
        conn = mysql.connector.connect(
            host=settings.Host,
            user=settings.User,
            password=settings.Password,
            database=settings.Database
        )
        cursor = conn.cursor()
        
        cursor.execute("SELECT can_edit_status FROM admins WHERE user_id = %s", (userId,))
        admin_data = cursor.fetchone()
        can_edit_status = admin_data[0] if admin_data else False
        user_status = cursor.fetchone()
    
        if len(context.args) != 2:
            await update.message.reply_text("Использование команды: /editStatus <user_id> <new_status>")
            return
    
        try:
            user_id = int(context.args[0])  # Получаем user_id
            new_status = context.args[1]  # Получаем новый статус
        except ValueError:
            await update.message.reply_text("Неверный формат. Использование команды: /editStatus <user_id> <new_status>")
            return
    
        # Подключение к базе данных для обновления статуса
        
        if can_edit_status:
            # Проверим, существует ли пользователь с таким ID
            cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            user_data = cursor.fetchone()
        
            if user_data:
                # Обновляем статус пользователя в базе данных
                cursor.execute("UPDATE users SET status = %s WHERE user_id = %s", (new_status, user_id))
                conn.commit()
                await update.message.reply_text(f"Статус пользователя с ID {user_id} успешно изменен на '{new_status}'.")
            else:
                await update.message.reply_text(f"Пользователь с ID {user_id} не найден в базе данных.")
        else:
            await update.message.reply_text("У вас нет прав на изменения статуса!")
    
        conn.close()

async def show_profile(update: Update, context: CallbackContext):
    userId = update.message.from_user.id
    vip_status = ''
    # Определяем целевого пользователя
    target_user_id = None

    # Если команда выполняется как ответ на сообщение
    if update.message.reply_to_message:
        target_user_id = update.message.reply_to_message.from_user.id

    # Если указан аргумент в команде
    elif context.args:
        try:
            target_user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("ID пользователя должен быть числом. Пример: /ShowProfile 12345")
            return

    # Если упомянули пользователя через @
    elif update.message.entities:
        for entity in update.message.entities:
            if entity.type == "mention":
                mentioned_username = update.message.text[entity.offset + 1:entity.offset + entity.length]
                target_user = await context.bot.get_chat_member(update.effective_chat.id, userId)
                if target_user and target_user.user.username == mentioned_username:
                    target_user_id = target_user.user.id
                    break

    # Если не удалось определить целевого пользователя
    if not target_user_id:
        await update.message.reply_text("Пожалуйста, ответьте на сообщение пользователя, укажите его ID или упомяните его через @.")
        return

    # Подключение к базе данных
    conn = mysql.connector.connect(
        host=settings.Host,
        user=settings.User,
        password=settings.Password,
        database=settings.Database
    )
    cursor = conn.cursor(dictionary=True)

    # Проверка прав
    cursor.execute("SELECT can_profile_check FROM admins WHERE user_id = %s", (userId,))
    admin_data = cursor.fetchone()
    can_profile_check = admin_data["can_profile_check"] if admin_data else False

    if not can_profile_check:
        await update.message.reply_text("У вас нет прав для просмотра чужих профилей.")
        conn.close()
        return

    # Получение данных пользователя
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (target_user_id,))
    user_data = cursor.fetchone()
    conn.close()

    if user_data:
        avatar_path = user_data.get("avatar", None)

        if user_data['is_vip'] == 0:
            vip_status = 'Отсуствует'
        elif user_data['is_vip'] == 1:
            vip_status = "Имеется"

        # Отправляем аватар и данные профиля
        message = (
            f"👤 <b>Имя пользователя:</b> {user_data['name']}\n"
            f"👑 <b>Статус:</b> {user_data['status']}\n"
            f"💎 <b>Вип :</b> {vip_status}\n"
            f"👥 <b>Количество персонажей:</b> {user_data['number_characters']}"
        )

        if avatar_path:
            with open(avatar_path, 'rb') as avatar_file:
                await update.message.reply_photo(
                    photo=avatar_file,
                    caption=message,
                    parse_mode="HTML"
                )
        else:
            await update.message.reply_text(message, parse_mode="HTML")
    else:
        await update.message.reply_text(f"Пользователь с ID {target_user_id} не найден в базе данных.")

async def button_handler(update: Update, context):
    query = update.callback_query
    await query.answer()  # Обязательно отвечаем на callback
    
    if query.data == "change_avatar":
        await query.message.reply_text("Отправьте новое фото для аватара.")
    elif query.data == "view_profile":
        await query.message.reply_text("Ваш профиль: ...")
