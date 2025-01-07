from telegram.ext import CommandHandler, Application
import db_manager.db_manager
import character_manager

import db_manager.mining.mining_manager
import db_manager.profile.profile_manager
import settings

profile = db_manager.profile.profile_manager
mining = db_manager.mining.mining_manager
db = db_manager.db_manager

application = Application.builder().token(settings.BOT_TOKEN).build()

async def register_commands():
    application.add_handler(CommandHandler("start", character_manager.start))
    await application.add_handler(CommandHandler("list", db.list_characters))
    await application.add_handler(CommandHandler("GLlist", db.glist_characters))
    await application.add_handler(CommandHandler("show", db.show_character))
    # application.add_handler(CommandHandler("profile", show_user_profile))
    application.add_handler(CommandHandler("ShowProfile", profile.show_profile))
    await application.add_handler(CommandHandler("top", db.top))
    await application.add_handler(CommandHandler("delete", db.delete_character))
    application.add_handler(CommandHandler("editStatus", profile.edit_status))
    application.add_handler(CommandHandler("balance", mining.balance))
    application.add_handler(CommandHandler("bal", mining.balance))
    application.add_handler(CommandHandler("mining", mining.mine))
    application.add_handler(CommandHandler("mine", mining.mine))
