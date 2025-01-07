# bot.py
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters, CallbackQueryHandler

import settings
import character_manager
import logging

import db_manager.profile.profile_manager
import db_manager.mining.currency

#HYPNO CAT HAY & NIKO

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

currency = db_manager.mining.currency
profile = db_manager.profile.profile_manager

# Main bot logic
def main():
    # Replace with your Telegram Bot Token
    application = Application.builder().token(settings.BOT_TOKEN).build()

    shop_handler = ConversationHandler(
        entry_points=[CommandHandler("shop", currency.shop)],
        states={
            currency.CHOOSE_ITEM: [CallbackQueryHandler(currency.choose_quantity)],
            currency.ENTER_QUANTITY: [CallbackQueryHandler(currency.confirm_purchase)],
        },
        fallbacks=[CommandHandler("cancel", currency.cancel)],
        per_message=False,
    )
    
    # Add conversation handler for character creation
    create_handler = ConversationHandler(
        entry_points=[CommandHandler("create", character_manager.create)],
        states={
            character_manager.AVATAR: [MessageHandler(filters.PHOTO, character_manager.avatar)],
            character_manager.NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, character_manager.name)],
            character_manager.DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, character_manager.description)],
            character_manager.HEALTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, character_manager.health)],
            character_manager.DAMAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, character_manager.damage)],
            character_manager.ABILITIES: [MessageHandler(filters.TEXT & ~filters.COMMAND, character_manager.abilities)],
            character_manager.WEAKNESSES: [MessageHandler(filters.TEXT & ~filters.COMMAND, character_manager.weaknesses)],
            character_manager.SKILLS: [MessageHandler(filters.TEXT & ~filters.COMMAND, character_manager.skills)],
        },
        fallbacks=[CommandHandler('cancel', character_manager.cancel)],
        per_message=False,
    )

    avatar_handler = ConversationHandler(
        entry_points=[CommandHandler("profile", profile.show_user_profile)],
        states={
            profile.CHOOSE_AVATAR: [CallbackQueryHandler(profile.choose_avatar)],
            profile.UPLOAD_AVATAR: [MessageHandler(filters.PHOTO & ~filters.COMMAND, profile.handle_new_avatar)],
        },
        fallbacks=[CommandHandler("cancel", profile.cancel)]
    )

    application.add_handler(shop_handler)
    application.add_handler(create_handler)
    application.add_handler(avatar_handler)

    try:
        application.run_polling()
    except KeyboardInterrupt:
        logging.info("Bot has been stopped by user.")
    except Exception as e:
        logging.error(f"An error occurred: {e}")


if __name__ != "__main__":
    pass
else:
    main()
