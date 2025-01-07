from telegram import Update
from telegram.ext import CallbackContext
import random
import time
import mysql.connector
import settings
from telegram.constants import ParseMode

async def mine(update: Update):
    user_id = update.effective_user.id
    conn = mysql.connector.connect(
        host=settings.Host,
        user=settings.User,
        password=settings.Password,
        database=settings.Database
    )
    carpets = 1
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))    
    user_data = cursor.fetchone()
    conn.close()
    current_time = int(time.time())

    cooldown_time = current_time + 2 * 60 * 60  # 2 часа в секундах

    if user_data:
        cooldown = user_data[7]
        newbies = user_data[6]
        is_vip = user_data[8] == 1  # Проверка на VIP-статус
        vip_uses = user_data[9] if is_vip else 0

        if current_time < cooldown:
            remaining_time = cooldown - current_time
            if is_vip and vip_uses < 1:
                vip_uses += 1
                # Генерируем добычу для VIP без изменения времени восстановления
                amount = random.randint(5, 60)
                update_user(user_id, amount, 0, cooldown, vip_uses)  # Не обновляем cooldown для VIP
                await update.message.reply_text(
                    f"Вы добыли 👾{amount} новиков."
                )

                if random.random() <= 0.05:
                   update_user(user_id, amount, carpets, cooldown_time, vip_uses)
                   await update.message.reply_text(
                       f"Вы получили 1 ковик!"
                   )                   

                return
            else:
                await update.message.reply_text(
                    f"Добывать можно раз в 2 часа. \nСледующая добыча через {remaining_time // 120 // 30} час(ов) {remaining_time // 120 } мин(ут)."
                )
                return

        # Генерируем случайное количество валюты
        amount = random.randint(5, 55)



        if random.random() <= 0.05:
            update_user(user_id, amount, carpets, cooldown_time, 0)
            await update.message.reply_text(
                f"Вы получили 1 ковик!"
            )

        await update.message.reply_text(
            f"Вы добыли 👾{amount} новиков."
        )

        # Обновляем данные пользователя
        update_user(user_id, amount, 0, cooldown_time, 0)
    else:
        await update.message.reply_text("Пользователь не найден в базе данных.\nПожалуста введите в личных сообщениях бота - **/start**")


def update_user(user_id, newbies, carpets, cooldown_time, vip_uses):
    conn = mysql.connector.connect(
        host=settings.Host,
        user=settings.User,
        password=settings.Password,
        database=settings.Database
    )
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO users (user_id, newbies, carpets, cooldown, vip_uses)
    VALUES (%s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        newbies = newbies + VALUES(newbies),
        carpets = carpets + VALUES(carpets),
        vip_uses = vip_uses + VALUES(vip_uses),
        cooldown = VALUES(cooldown) 
    """, (user_id, newbies, carpets, cooldown_time, vip_uses))
    conn.commit()
    conn.close()

async def balance(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id  # Получаем ID пользователя
    
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
    message = (
        f"🦊**<b>Ковики: {user_data[5]}</b>\n"
        f"👾**<b>Новики: {user_data[6]}</b>\n"
    )
    await update.message.reply_text(
            message,
            parse_mode=ParseMode.HTML
    )