import os
import mysql.connector
from telegram import Update
from telegram.ext import CallbackContext
from telegram.constants import ParseMode
import settings

class DatabaseManager:
    @staticmethod
    def get_connection():
        return mysql.connector.connect(
            host=settings.Host,
            user=settings.User,
            password=settings.Password,
            database=settings.Database
        )

    @staticmethod
    def get_user_data(user_id):
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        data = cursor.fetchone()
        cursor.close()
        conn.close()
        return data

    def update_user_field(self, user_id, field, value):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f"UPDATE users SET {field} = %s WHERE user_id = %s", (value, user_id))
        conn.commit()
        cursor.close()
        conn.close()


    def create_table(self):
        with self.get_connection() as conn:
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

    def create_user_table(self):
        with self.get_connection() as conn:
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

    def save_character_to_db(self, character, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT id FROM available_ids ORDER BY id LIMIT 1")
            available = cursor.fetchone()
            if available:
                char_id = available[0]
                cursor.execute("DELETE FROM available_ids WHERE id=%s", (char_id,))
            else:
                cursor.execute("SELECT IFNULL(MAX(id), 0) + 1 FROM characters")
                char_id = cursor.fetchone()[0]

            cursor.execute('''
                INSERT INTO characters (
                    id, user_id, name, description,
                    health, abilities, skills,
                    avatar, damage, weaknesses
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ''', (
                char_id, user_id,
                character['name'], character['description'],
                character['health'], character['abilities'],
                character['skills'], character['avatar'],
                character.get('damage',0), character.get('weaknesses')
            ))
            cursor.execute(
                "UPDATE users SET number_characters = number_characters + 1 WHERE user_id=%s",
                (user_id,)
            )
            conn.commit()
            return char_id
        finally:
            cursor.close()
            conn.close()

    async def create_profile(self, update: Update, context: CallbackContext):
        user = update.message.from_user
        user_id = user.id
        user_name = user.full_name or "Без имени"

        avatars_folder = "D:/wamp64/www/BotPerson/avatars/profile-users"
        os.makedirs(avatars_folder, exist_ok=True)
        default_avatar = os.path.join(avatars_folder, "default.jpg")
        avatar_path = os.path.join(avatars_folder, f"{user_id}.jpg")

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
        exists = cursor.fetchone()

        try:
            photos = await context.bot.get_user_profile_photos(user_id)
            if photos.total_count and photos.photos[0]:
                file_id = photos.photos[0][0].file_id
                file = await context.bot.get_file(file_id)
                await file.download_to_drive(avatar_path)
            else:
                avatar_path = default_avatar
        except Exception as e:
            print("Ошибка получения аватара:", e)
            avatar_path = default_avatar

        if not os.path.exists(avatar_path):
            avatar_path = default_avatar

        if not exists:
            cursor.execute(
                "INSERT INTO users "
                "(user_id, name, avatar, status, number_characters, carpets, newbies, cooldown, is_vip, vip_uses) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (user_id, user_name, avatar_path, "", 0, 0, 0, 0, 0, 0)
            )
            conn.commit()

        cursor.close()
        conn.close()

    async def top(self, update: Update, context: CallbackContext):
        limit = 10
        if context.args:
            try:
                n = int(context.args[0])
                if n > 0:
                    limit = n
                else:
                    raise ValueError
            except ValueError:
                return await update.message.reply_text(
                    "Пожалуйста, укажите корректное число. Пример: /top 5"
                )

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name, status, number_characters
            FROM users
            ORDER BY number_characters DESC
            LIMIT %s
        """, (limit,))
        users = cursor.fetchall()
        conn.close()

        if users:
            msg = f"<b>🏆 ТОП {limit} пользователей</b>\n\n"
            for i, (n, st, nc) in enumerate(users, 1):
                msg += f"<b>{i}. {n}</b>\nСтатус: {st}\nКарточек: {nc}\n\n"
        else:
            msg = "Нет данных для рейтинга."

        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

    async def delete_character(self, update: Update, context: CallbackContext):
        if len(context.args) != 1:
            return await update.message.reply_text("Укажите ID: /delete <id>.")
        try:
            cid = int(context.args[0])
        except ValueError:
            return await update.message.reply_text("ID должен быть числом.")

        uid = update.message.from_user.id
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM characters WHERE id=%s AND user_id=%s",
            (cid, uid)
        )
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return await update.message.reply_text(f"Персонаж {cid} не найден или не ваш.")

        cursor.execute("DELETE FROM characters WHERE id=%s", (cid,))
        cursor.execute("INSERT INTO available_ids (id) VALUES (%s)", (cid,))
        cursor.execute(
            "UPDATE users SET number_characters=number_characters-1 WHERE user_id=%s",
            (uid,)
        )
        conn.commit()
        cursor.close()
        conn.close()
        await update.message.reply_text(f"Персонаж {cid} удалён.")

    def check_admin_permission(self, user_id, permission):
        """Проверяет, есть ли у пользователя указанное разрешение в таблице admins"""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT {} FROM admins WHERE user_id=%s".format(permission),
            (user_id,)
        )
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result[permission] if result else False

    def user_exists(self, user_id):
        """Проверяет, есть ли пользователь в таблице users"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE user_id=%s", (user_id,))
        exists = cursor.fetchone() is not None
        cursor.close()
        conn.close()
        return exists


    async def list_characters(self, update: Update, context: CallbackContext):
        uid = update.message.from_user.id
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id,name FROM characters WHERE user_id=%s", (uid,))
        rows = cursor.fetchall()
        conn.close()

        if rows:
            txt = "Ваши персонажи:\n" + "\n".join(f"🆔 {r[0]} - {r[1]}" for r in rows)
        else:
            txt = "Персонажей нет. Создайте /create."
        await update.message.reply_text(txt)

    async def show_character(self, update: Update, context: CallbackContext):
        if len(context.args) != 1:
            return await update.message.reply_text("Укажите ID: /show <id>.")
        try:
            cid = int(context.args[0])
        except ValueError:
            return await update.message.reply_text("ID должен быть числом.")

        uid = update.message.from_user.id
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT can_view_all_characters FROM admins WHERE user_id=%s",
            (uid,)
        )
        admin = cursor.fetchone()
        can_view = admin[0] if admin else False

        if can_view:
            cursor.execute("SELECT * FROM characters WHERE id=%s", (cid,))
        else:
            cursor.execute(
                "SELECT * FROM characters WHERE id=%s AND user_id=%s",
                (cid, uid)
            )
        char = cursor.fetchone()
        conn.close()

        if not char:
            return await update.message.reply_text(f"Персонаж {cid} не найден или недоступен.")

        avatar = char[7] or os.path.join("D:/wamp64/www/BotPerson/avatars", "NoAvatarce.jpg")
        msg = (
            f"<b>Персонаж:</b> {char[2]}\n"
            f"🆔 ID: {char[0]}\n"
            f"❤️ Здоровье: {char[4]}\n"
            f"🔪 Урон: {char[8]}\n"
            f"🧠 Способности: {char[5]}\n"
            f"⚒ Навыки: {char[6]}\n"
            f"😵 Слабости: {char[9]}"
        )
        with open(avatar, 'rb') as img:
            await update.message.reply_photo(photo=img, caption=msg, parse_mode=ParseMode.HTML)

    async def glist_characters(self, update: Update, context: CallbackContext):
        uid = update.message.from_user.id
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT can_view_all_characters FROM admins WHERE user_id=%s",
            (uid,)
        )
        admin = cursor.fetchone()
        can_view = admin[0] if admin else False

        if not can_view:
            cursor.close()
            conn.close()
            return await update.message.reply_text("У вас нет прав.")

        cursor.execute("""
            SELECT u.name, u.user_id, c.id, c.name
            FROM characters c
            JOIN users u ON c.user_id = u.user_id
            ORDER BY u.name, c.name
        """)
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return await update.message.reply_text("Персонажей в базе нет.")

        text = "Глобальный список персонажей:\n"
        current = None
        for uname, u_id, cid, cname in rows:
            if uname != current:
                if current:
                    text += "\n"
                text += f"{uname} (ID: {u_id}):\n"
                current = uname
            text += f"  - {cname} — {cid}\n"
        await update.message.reply_text(text)
