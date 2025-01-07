from telegram import Update
from telegram.ext import CallbackContext
from telegram.constants import ParseMode
import mysql.connector
import settings

import os

class DatabaseManager:
    def get_user_data(user_id):
        conn = mysql.connector.connect(
            host=settings.Host,
            user=settings.User,
            password=settings.Password,
            database=settings.Database
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE user_id = %s", user_id)
        user_data = cursor.fetchone()
        conn.close()
        return user_data

    def create_table(self):
        conn = mysql.connector.connect(
            host=settings.Host,
            user=settings.User,       # Логин MySQL
            password=settings.Password,       # Пароль MySQL
            database=settings.Database  # Название базы данных
        )
        cursor = conn.cursor()
        cursor.execute(''' 
            CREATE TABLE IF NOT EXISTS characters (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                health INT,
                abilities TEXT,
                skills TEXT,
                avatar VARCHAR(255),
                damage INT DEFAULT 0,
                weaknesses TEXT
            )
        ''')
        conn.commit()
        conn.close()
        
    def create_user_table(self):
        conn = mysql.connector.connect(
            host=settings.Host,
            user=settings.User,       # Логин MySQL
            password=settings.Password,       # Пароль MySQL
            database=settings.Database  # Название базы данных
        )
        cursor = conn.cursor()
        cursor.execute(''' 
            CREATE TABLE IF NOT EXISTS users (                
                user_id BIGINT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                avatar VARCHAR(255) NOT NULL,
                status TEXT,
                number_characters INT
            )
        ''')
        conn.commit()
        conn.close()
        
    def save_character_to_db(character, user_id):
        conn = mysql.connector.connect(
            host=settings.Host,
            user=settings.User,
            password=settings.Password,
            database=settings.Database
        )
        cursor = conn.cursor()
    
        try:
            # Проверяем, есть ли доступные ID
            cursor.execute("SELECT id FROM available_ids ORDER BY id LIMIT 1")
            available_id = cursor.fetchone()
    
            if available_id:
                character_id = available_id[0]
                # Удаляем этот ID из таблицы доступных
                cursor.execute("DELETE FROM available_ids WHERE id = %s", (character_id,))
            else:
                # Если доступных ID нет, создаём новый автоматически
                cursor.execute("SELECT IFNULL(MAX(id), 0) + 1 FROM characters")
                character_id = cursor.fetchone()[0]
    
            # Вставляем нового персонажа с выбранным ID
            cursor.execute('''INSERT INTO characters (id, user_id, name, description, health, abilities, skills, avatar, damage, weaknesses)
                              VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                           (character_id, user_id, character['name'], character['description'], character['health'],
                            character['abilities'], character['skills'], character['avatar'], character['damage'], character['weaknesses']))
            conn.commit()
    
            # Обновляем количество персонажей
            cursor.execute("UPDATE users SET number_characters = number_characters + 1 WHERE user_id = %s", (user_id,))
            conn.commit()
    
            return character_id
        finally:
            cursor.close()
            conn.close()

    async def create_profile(update: Update, context: CallbackContext):
        user = update.message.from_user  # Получаем данные пользователя
        user_id = user.id
        user_name = user.full_name or "Без имени"
        
        # Указываем директорию для хранения аватарок
        avatars_folder = "D:/wamp64/www/BotPerson/avatars/profile-users"
        os.makedirs(avatars_folder, exist_ok=True)  # Создаём директорию, если её нет
        default_avatar_path = os.path.join(avatars_folder, "default.jpg")
        avatar_path = os.path.join(avatars_folder, f"{user_id}.jpg")
        
        # Подключение к базе данных
        conn = mysql.connector.connect(
            host=settings.Host,
            user=settings.User,
            password=settings.Password,
            database=settings.Database
        )
        cursor = conn.cursor()
        
        # Проверяем, существует ли профиль пользователя
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user_data = cursor.fetchone()
        
        try:
            # Получаем аватарку пользователя
            photos = await context.bot.get_user_profile_photos(user_id)
            if photos.total_count > 0 and len(photos.photos[0]) > 0:
                file_id = photos.photos[0][0].file_id
                file = await context.bot.get_file(file_id)
                await file.download_to_drive(avatar_path)
            else:
                avatar_path = default_avatar_path  # Используем путь по умолчанию
        except Exception as e:
            print(f"Ошибка при получении или скачивании аватарки: {e}")
            avatar_path = default_avatar_path
    
        # Проверяем существование файла аватарки
        if not os.path.exists(avatar_path):
            avatar_path = default_avatar_path
    
        if not user_data:
            # Если профиль не существует, создаём его
            cursor.execute(
                "INSERT INTO users (user_id, name, avatar, status, number_characters) VALUES (%s, %s, %s, %s, %s)",
                (user_id, user_name, avatar_path, "active", 0)
            )
            conn.commit()
        
        # Закрытие соединения с базой данных
        cursor.close()
        conn.close()

    async def top(update: Update, context: CallbackContext):
        # По умолчанию показываем топ-10
        default_limit = 10
    
        # Получаем количество пользователей из аргументов команды
        try:
            limit = int(context.args[0]) if context.args else default_limit
            if limit < 1:
                raise ValueError("Limit must be greater than 0.")
        except ValueError:
            await update.message.reply_text("Пожалуйста, укажите корректное число. Пример: /top 5")
            return
    
        # Подключение к базе данных
        conn = mysql.connector.connect(
            host=settings.Host,
            user=settings.User,
            password=settings.Password,
            database=settings.Database
        )
        cursor = conn.cursor()
    
        # Запрос для выборки пользователей, ограничение по `limit`
        cursor.execute("""
            SELECT name, status, number_characters
            FROM users
            ORDER BY number_characters DESC
            LIMIT %s
        """, (limit,))
        users = cursor.fetchall()
        conn.close()
    
        # Формирование сообщения с топом
        if users:
            message = f"<b>🏆 ТОП {limit} Пользователей по Количеству Карточек 🏆</b>\n\n"
            for rank, user in enumerate(users, start=1):
                name, status, number_characters = user
                message += (
                    f"<b>{rank}. {name}</b>\n"
                    f"   Статус: {status}\n"
                    f"   Количество карточек: {number_characters}\n\n"
                )
        else:
            message = "Нет данных о пользователях для отображения рейтинга."
    
        # Отправка сообщения
        await update.message.reply_text(
            message,
            parse_mode=ParseMode.HTML
        )

    #/delete - 
    async def delete_character(update: Update, context: CallbackContext):
        if len(context.args) != 1:
            await update.message.reply_text("Пожалуйста, укажите ID персонажа с помощью /delete <id>.")
            return
    
        try:
            character_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("ID персонажа должно быть числом.")
            return
    
        user_id = update.message.from_user.id
    
        conn = mysql.connector.connect(
            host=settings.Host,
            user=settings.User,
            password=settings.Password,
            database=settings.Database
        )
        cursor = conn.cursor()
    
        try:
            # Проверяем, существует ли персонаж
            cursor.execute("SELECT id FROM characters WHERE id=%s AND user_id=%s", (character_id, user_id))
            character = cursor.fetchone()
    
            if character is None:
                await update.message.reply_text(f"Персонаж с ID {character_id} не существует или вам не принадлежит.")
                return
    
            # Удаляем персонажа
            cursor.execute("DELETE FROM characters WHERE id=%s AND user_id=%s", (character_id, user_id))
            conn.commit()
    
            # Добавляем удалённый ID в таблицу доступных ID
            cursor.execute("INSERT INTO available_ids (id) VALUES (%s)", (character_id,))
            conn.commit()
    
            # Обновляем количество персонажей
            cursor.execute("UPDATE users SET number_characters = number_characters - 1 WHERE user_id = %s", (user_id,))
            conn.commit()
    
            await update.message.reply_text(f"Персонаж с ID {character_id} был успешно удалён.")
        finally:
            cursor.close()
            conn.close()

    #/list
    async def list_characters(update: Update, context: CallbackContext):
    
        user_id = update.message.from_user.id  # Get the user ID of the person making the request
    
        conn = mysql.connector.connect(
            host=settings.Host,
            user=settings.User,
            password=settings.Password,
            database=settings.Database
        )
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM characters WHERE user_id=%s", (user_id,))
        characters = cursor.fetchall()
        conn.close()
    
        if characters:
            response = "Список ваших персонажей:\n"
            for character in characters:
                response += f"🆔 {character[0]} - {character[1]}\n"
            await update.message.reply_text(response)
        else:
            await update.message.reply_text("Персонажи не найдены. Создайте персонажа с помощью /create.")
    #/show -
    async def show_character(update: Update, context: CallbackContext):
        if len(context.args) != 1:
            await update.message.reply_text("Пожалуйста, укажите ID персонажа с помощью /show <id>.")
            return
    
        try:
            character_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("ID персонажа должно быть числом.")
            return
    
        user_id = update.message.from_user.id  # ID пользователя, вызвавшего команду
        conn = mysql.connector.connect(
            host=settings.Host,
            user=settings.User,
            password=settings.Password,
            database=settings.Database
        )
        cursor = conn.cursor()
    
        # Проверяем, есть ли пользователь в таблице администраторов и может ли он видеть всех персонажей
        cursor.execute("SELECT can_view_all_characters FROM admins WHERE user_id = %s", (user_id,))
        admin_data = cursor.fetchone()
        can_view_all = admin_data[0] if admin_data else False
    
        # Если пользователь не администратор, проверяем его статус в `users`
        cursor.execute("SELECT status FROM users WHERE user_id = %s", (user_id,))
        user_status = cursor.fetchone()
        if user_status:
            user_status = user_status[0]
        else:
            user_status = None
    
        # Условия доступа
        if can_view_all:
            # Может видеть все персонажи
            cursor.execute("SELECT * FROM characters WHERE id=%s", (character_id,))
        else:
            # Может видеть только свои персонажи
            cursor.execute("SELECT * FROM characters WHERE id=%s AND user_id=%s", (character_id, user_id))
    
        character = cursor.fetchone()
        conn.close()
    
        if character:
            avatar_path = character[7]  # 8-й столбец — путь к аватару
            user_folder = "D:/wamp64/www/BotPerson/avatars/"
            no_avatar_path = os.path.join(user_folder, "NoAvatarce.jpg")
    
            message = (
                f"<b>Персонаж:</b> {character[2]}\n\n"
                f"<b>🆔ID:</b> {character[0]}\n"
                f"<b>🏷️Имя:</b> {character[2]}\n"
                f"<b>📝Описание:</b> {character[3]}\n"
                f"<b>❤️Здоровье:</b> {character[4]}\n"
                f"<b>🔪Урон:</b> {character[8]}\n"
                f"<b>🧠Способности:</b> {character[5]}\n"
                f"<b>⚒️Навыки:</b> {character[6]}\n"
                f"<b>😵Слабости:</b> {character[9]}\n"
            )
    
            if os.path.exists(avatar_path):
                with open(avatar_path, 'rb') as avatar_file:
                    await update.message.reply_photo(
                        photo=avatar_file,
                        caption=message,
                        parse_mode=ParseMode.HTML
                    )
            else:
                with open(no_avatar_path, 'rb') as no_avatar_file:
                    await update.message.reply_photo(
                        photo=no_avatar_file,
                        caption=message,
                        parse_mode=ParseMode.HTML
                    )
        else:
            await update.message.reply_text(f"Персонаж с ID {character_id} не найден или недоступен для вас.")

    async def glist_characters(update: Update, context: CallbackContext):
        user_id = update.message.from_user.id  # Get the user ID of the person making the request
        
        conn = mysql.connector.connect(
            host=settings.Host,
            user=settings.User,
            password=settings.Password,
            database=settings.Database
        )
        cursor = conn.cursor()
    
        # Retrieve the user's name (nickname) from the users table
        cursor.execute("SELECT name, status FROM users WHERE user_id=%s", (user_id,))
        user_name = cursor.fetchone()
        
        # Проверяем, есть ли пользователь в таблице администраторов и может ли он видеть всех персонажей
        cursor.execute("SELECT can_view_all_characters FROM admins WHERE user_id = %s", (user_id,))
        admin_data = cursor.fetchone()
        can_view_all = admin_data[0] if admin_data else False
        user_status = cursor.fetchone()
        
        if can_view_all:
            if user_status:
                user_status = user_status[0]
            else:
                user_status = None
            
            if user_name:
                # Get the list of characters for the user
                cursor.execute("""
                    SELECT users.name, users.user_id, characters.id, characters.name 
                    FROM characters 
                    JOIN users ON characters.user_id = users.user_id
                    ORDER BY users.name, characters.name
                """)
                characters = cursor.fetchall()
                
                if characters:
                    response = "Глобальный список всех персонажей:\n"
                    current_user = None  # To track when the user changes
                    
                    for character in characters:
                        user_name, user_id, character_id, character_name = character
                        
                        # If the user changes, add their name as a header
                        if user_name != current_user:
                            if current_user:  # Add a separator for the next user
                                response += "\n"
                            response += f"{user_name} (ID: {user_id}):\n"
                            current_user = user_name
                        
                        # List the character under the user, including the character's ID
                        response += f"  - {character_name} - {character_id}\n"
                    
                    await update.message.reply_text(response)
                else:
                    await update.message.reply_text("Персонажи не найдены в базе данных.")
            else:
                await update.message.reply_text("У вас нет прав.")
        conn.close()
