from telegram.ext import CommandHandler, Application
import db_manager.db_manager
import character_manager

import db_manager.mining.mining_manager
import db_manager.profile.profile_manager
import db_manager.mining.currency

async def register_commands(application):
    db = db_manager.db_manager.DatabaseManager()  # экземпляр класса
    profile = db_manager.profile.profile_manager
    mining = db_manager.mining.mining_manager  
    shop = db_manager.mining.currency

    application.add_handler(CommandHandler("start", character_manager.start))
    application.add_handler(CommandHandler("list", db.list_characters))
    application.add_handler(CommandHandler("GLlist", db.glist_characters))
    application.add_handler(CommandHandler("show", db.show_character))
    #application.add_handler(CommandHandler("profile", profile.show_user_profile))
    #application.add_handler(CommandHandler("profileS", profile.show_profile))
    application.add_handler(CommandHandler("top", db.top))
    application.add_handler(CommandHandler("delete", db.delete_character))
    application.add_handler(CommandHandler("editStatus", profile.edit_status))
    application.add_handler(CommandHandler("balance", mining.balance))
    application.add_handler(CommandHandler("bal", mining.balance))
    application.add_handler(CommandHandler("mining", mining.mine))
    application.add_handler(CommandHandler("mine", mining.mine))
    #application.add_handler(CommandHandler("shop", shop.shop))