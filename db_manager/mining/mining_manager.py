import random
import time
from telegram import Update
from telegram.ext import CallbackContext
from telegram.constants import ParseMode

from db_manager.db_manager import DatabaseManager

db = DatabaseManager()

COOLDOWN_HOURS = 2  # 2 часа

# ------------------ Функция добычи ------------------

async def mine(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_data = db.get_user_data(user_id)

    if not user_data:
        await update.message.reply_text("Пользователь не найден в базе данных.\nПожалуйста, введите /start")
        return

    current_time = int(time.time())
    cooldown = user_data.get("cooldown", 0)
    vip_uses = user_data.get("vip_uses", 0)
    is_vip = user_data.get("is_vip", 0) == 1

    if is_vip:
        # VIP-добыча
        if current_time >= cooldown:
            vip_uses = 0  # сброс после кулдауна

        if vip_uses < 2:
            vip_uses += 1
        else:
            remaining_time = cooldown - current_time
            hours = remaining_time // 3600
            minutes = (remaining_time % 3600) // 60
            await update.message.reply_text(
                f"VIP-добыча исчерпана. Следующая добыча через {hours}ч {minutes}м."
            )
            return

        # Если это первая добыча после кулдауна, ставим новый кулдаун
        if vip_uses == 1 and current_time >= cooldown:
            cooldown = current_time + COOLDOWN_HOURS * 3600

    else:
        # обычный пользователь
        if current_time < cooldown:
            remaining_time = cooldown - current_time
            hours = remaining_time // 3600
            minutes = (remaining_time % 3600) // 60
            await update.message.reply_text(
                f"Добывать можно раз в {COOLDOWN_HOURS} часа.\nСледующая добыча через {hours}ч {minutes}м."
            )
            return
        cooldown = current_time + COOLDOWN_HOURS * 3600

    # Генерация добычи
    mined_newbies = random.randint(5, 55)
    mined_carpets = 1 if random.random() <= 0.05 else 0

    # Обновляем данные
    db.update_user_resources(
        user_id,
        newbies=mined_newbies,
        carpets=mined_carpets,
        cooldown=cooldown,
        vip_uses=vip_uses
    )

    msg = f"Вы добыли 👾{mined_newbies} новиков."
    if mined_carpets:
        msg += "\nВы получили 1 ковик!"

    await update.message.reply_text(msg)

# ------------------ Функция баланса ------------------

async def balance(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_data = db.get_user_data(user_id)

    if not user_data:
        await update.message.reply_text(
            "Пользователь не найден в базе данных.\n"
            "Пожалуйста, введите /start"
        )
        return

    message = (
        f"🦊 <b>Ковики:</b> {user_data.get('carpets', 0)}\n"
        f"👾 <b>Новики:</b> {user_data.get('newbies', 0)}"
    )
    await update.message.reply_text(message, parse_mode=ParseMode.HTML)
