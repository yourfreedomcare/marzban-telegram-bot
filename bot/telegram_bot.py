'''
File includes the main Telegram bot class 
with all the availabe message callbacks and query callbacks 
'''

from telebot import TeleBot
from logger import logger
from .utils import *
from database.user import UserRepository
from marzban_api.marzban_service import MarzbanService
import os
import time



class TelegramBot():
    print("+++TELEGRAM BOT+++")
    bot = TeleBot(os.getenv('TELEGRAM_BOT_TOKEN'))
    admin_users = os.getenv('ADMIN_USERS').split(',')
    admin_user_broadcasts = set()

    def check_if_needs_update(func):
        print("Execuitng check_if_needs_update")
        def inner(obj): 
            try:
                print("line 22")
                user, _ =  UserRepository.get_user(retrieve_username(obj.from_user))
                print("line 24")
                print("User", user) 
                if user is not None and user.is_updated:
                    return func(obj)
                else: 
                    return create_needs_update_message(TelegramBot.bot, user.chat_id)
            except Exception: 
                logger.error(f"Exception -> check_if_needs_update: ", exc_info=True)
                TelegramBot.bot.send_message(user.chat_id, messages_content['unexpected_error'])
        return inner
    
    def empty_admin_user_broadcasts(func):
        def inner(obj): 
            if len(TelegramBot.admin_user_broadcasts) > 1: 
                TelegramBot.admin_user_broadcasts.discard(retrieve_username(obj.from_user))
                logger.error("Inner -> empty_admin_user_broadcasts")
            return func(obj)
        return inner

    # Starting point of bot
    @empty_admin_user_broadcasts
    @bot.message_handler(commands=['start'])
    def entrypoint(message): 
        try:
            telegram_user_id = retrieve_username(message.from_user)
            logger.info(f"entrypoint -> telegram_user_id {telegram_user_id}")
            user, configurations = UserRepository.get_user(telegram_user_id)

            if user == None or len(configurations) == 0 : 
                if user == None:
                    logger.info(f"chat id {message.chat.id}")
                    UserRepository.create_new_user(telegram_user_id, message.chat.id)
                show_create_configurations_message(TelegramBot.bot, message, messages_content['welcome'].format(breakpoint="\n\n"))
            else:
                if not user.is_updated:
                    UserRepository.mark_user_as_updated(telegram_user_id)
                create_reply_keyboard_panel(
                    telegram_user_id in TelegramBot.admin_users, 
                    TelegramBot.bot, 
                    message.chat.id, 
                    messages_content['welcome_back']
                    )
        except Exception: 
            logger.error(f"Exception -> entrypoint: ", exc_info=True)
            TelegramBot.bot.send_message(message.chat.id, messages_content['unexpected_error'])
    
    @empty_admin_user_broadcasts
    @bot.callback_query_handler(func=lambda call: call.data in ['update'])
    def update(call):
        telegram_user_id = retrieve_username(call.from_user)
        print("UPDATE")
        UserRepository.mark_user_as_updated(telegram_user_id)
        create_reply_keyboard_panel(
            telegram_user_id in TelegramBot.admin_users,
            TelegramBot.bot, 
            call.message.chat.id, 
            messages_content['updated']
            )


    # Refresh configs function used only by the Admins 
    @empty_admin_user_broadcasts
    @bot.message_handler(func=lambda message: message.text == button_content["Refresh Configs"])
    def refresh_logic(message): 
        try:
            telegram_user_id = retrieve_username(message.from_user)
            if telegram_user_id in TelegramBot.admin_users: 
                TelegramBot.bot.send_message(message.chat.id, messages_content['refresh_started'])
                refresh_configs()
                TelegramBot.bot.send_message(message.chat.id, messages_content['refresh_done'])
            else: 
                TelegramBot.bot.send_message(message.chat.id, messages_content['default_fallback'])
        except Exception: 
            logger.error(f"Exception -> entrypoint: ", exc_info=True)
            TelegramBot.bot.send_message(message.chat.id, messages_content['unexpected_error'])

    
    # Mark users as not updated, used by admins 
    @empty_admin_user_broadcasts
    @bot.message_handler(func=lambda message: message.text == button_content["Force Update"])
    def mark_users_as_not_updated(message): 
        try:
            telegram_user_id = retrieve_username(message.from_user)
            if telegram_user_id in TelegramBot.admin_users: 
                UserRepository.mark_users_for_update() 
                TelegramBot.bot.send_message(message.chat.id, 'Success')
            else: 
                TelegramBot.bot.send_message(message.chat.id, messages_content['default_fallback'])
        except Exception: 
            logger.error(f"Exception -> entrypoint: ", exc_info=True)
            TelegramBot.bot.send_message(message.chat.id, messages_content['unexpected_error'])
            

    # User/Configs Creation
    @bot.callback_query_handler(func=lambda call: call.data in ['configurations'])
    @empty_admin_user_broadcasts
    @check_if_needs_update
    def configurations_callback_query(call):
        print("EXECUTING configurations_callback_query")
        try:
            telegram_user_id = retrieve_username(call.from_user)
            print("Line 120")
            configs = UserRepository.get_user_configurations(telegram_user_id)
            print("Config len", len(configs))
            if len(configs) > 0: 
                TelegramBot.bot.send_message(call.message.chat.id, messages_content['configs_exist'])
            else:
                print("Line 125")
                user_data, status_code, access_token = MarzbanService.create_marzaban_user(telegram_user_id)

                if status_code == 200: # marzban get api will execute only one time after user creation
                    UserRepository.insert_configurations(telegram_user_id, call.message.chat.id, user_data['links'])

                if status_code == 409: 
                    logger.warning(f"Got 409 for user {telegram_user_id}. Falling back to DB.")
                    # Fallback: get links from configurations table
                    configurations = UserRepository.get_user_configurations(telegram_user_id)
                    links = [config.vless_link for config in configurations]
                    user_data = {links: links}

                if status_code > 299: 
                    raise Exception("Failed API Call")

                # UserRepository.insert_configurations(telegram_user_id, call.message.chat.id, user_data['links'])
                create_reply_keyboard_panel(
                    telegram_user_id in TelegramBot.admin_users,
                    TelegramBot.bot, 
                    call.message.chat.id, 
                    messages_content['created_configs']
                    )
        except Exception: 
            logger.error(f"Exception -> configurations_callback_query: ", exc_info=True)
            logger.error(f"API Response -> {user_data} ")
            TelegramBot.bot.send_message(call.message.chat.id, messages_content['unexpected_error'])


    # Configs Retrieval 

    @bot.message_handler(func=lambda message: message.text == button_content['Get Configurations'])
    @empty_admin_user_broadcasts
    @check_if_needs_update
    def get_configurations(message):
        print("EXECUTING GET CONFIGURATIONS")
        try:
            telegram_user_id = retrieve_username(message.from_user)
            configurations = UserRepository.get_user_configurations(telegram_user_id)
            if len(configurations) > 0:
                prepare_configs_panel(TelegramBot.bot, message.chat.id, configurations)
            else: 
                show_create_configurations_message(TelegramBot.bot, message, messages_content['no_configs'])

        except Exception: 
            logger.error(f"Exception -> get_configurations: ", exc_info=True)
            TelegramBot.bot.send_message(message.chat.id, messages_content['unexpected_error'])

    
    # Broadcast message
    @bot.message_handler(func=lambda message: message.text == button_content["Broadcast"])
    @check_if_needs_update
    def Broadcast(message):
        print("EXECUTING BROADCAST")
        try:
            telegram_user_id = retrieve_username(message.from_user)
            if telegram_user_id in TelegramBot.admin_users: 
                TelegramBot.bot.send_message(message.chat.id, "Insert the broadcast message and send: ")
                TelegramBot.admin_user_broadcasts.add(telegram_user_id)

        except Exception: 
            logger.error(f"Exception -> Broadcast: ", exc_info=True)
            TelegramBot.bot.send_message(message.chat.id, messages_content['unexpected_error'])

    # Manuals Retrieval 
    @bot.message_handler(func=lambda message: message.text == button_content['Get Manuals'])
    @empty_admin_user_broadcasts
    @check_if_needs_update
    def get_manuals(message):
        print("EXECUTING GET MANUALS")
        try:
            manuals = messages_content['manuals'].format(link=os.getenv("MANUALS_LINK"), support=os.getenv("SUPPORT_TG"))
            TelegramBot.bot.send_message(message.chat.id, manuals, parse_mode='HTML')
        except Exception: 
            logger.error(f"Exception -> get_manuals: ", exc_info=True)
            TelegramBot.bot.send_message(message.chat.id, messages_content['unexpected_error'])

    # Vless links retrieval 

    @bot.callback_query_handler(func = lambda call: call.message.text == messages_content['configs_panel'])
    @empty_admin_user_broadcasts
    @check_if_needs_update
    def return_link_callback_query(call):
        print("EXECUTING return_link_callback_query") 
        try:
            telegram_user_id = retrieve_username(call.from_user)
            configurations = UserRepository.get_user_configurations(telegram_user_id)
            d = prepare_links_dictionary_rework(configurations)
            if d[call.data]:

                status, used_traffic, data_limit = fetch_marzban_user_data(telegram_user_id)
                data_left_gb = max(0, bytes_to_gb(data_limit - used_traffic))
                status_message = f"Status: {status.upper()} | Data Left: {data_left_gb} GB"

                TelegramBot.bot.send_message(call.message.chat.id, status_message)
                TelegramBot.bot.send_message(call.message.chat.id, messages_content['link_available_1'].format(link=os.getenv("MANUALS_LINK")), parse_mode='HTML')
                TelegramBot.bot.send_message(call.message.chat.id, messages_content['link_available_2'].format(breakpoint="\n\n", link=d[call.data]), parse_mode='Markdown')
            else: 
                TelegramBot.bot.send_message(call.message.chat.id, messages_content['link_unavailable'].format(locatuon=call.data))
        except Exception: 
            logger.error(f"Exception -> return_link_callback_query:", exc_info=True)
            TelegramBot.bot.send_message(call.message.chat.id, messages_content['unexpected_error'])


    @bot.message_handler(func=lambda message: message.text == button_content['Donate'])
    def handle_donate(message):
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("💰 Crypto", callback_data='donate_crypto'))
        keyboard.add(types.InlineKeyboardButton("⭐ TG Stars", callback_data='donate_tgstars'))
        TelegramBot.bot.send_message(message.chat.id, "Choose donation option:", reply_markup=keyboard)

    @bot.callback_query_handler(func=lambda call: call.data == 'donate_crypto')
    def handle_donate_crypto(call):
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("Bitcoin", callback_data='donate_coin_btc'))
        keyboard.add(types.InlineKeyboardButton("Litecoin", callback_data='donate_coin_ltc'))
        keyboard.add(types.InlineKeyboardButton("USDT (ERC-20)", callback_data='donate_coin_usdt_erc'))
        keyboard.add(types.InlineKeyboardButton("USDT (TRC-20)", callback_data='donate_coin_usdt_trc'))
        TelegramBot.bot.send_message(call.message.chat.id, "Choose network and coin:", reply_markup=keyboard)

    # Unified crypto handler
    @bot.callback_query_handler(func=lambda call: call.data.startswith("donate_coin_"))
    def handle_crypto_donation(call):
        coin_key = call.data.replace("donate_coin_", "")
        coin_info = get_crypto_address_info(coin_key)

        if coin_info and coin_info['address']:
            message = (
                f"*{coin_info['network']} Address:*\n"
                f"`{coin_info['address']}`\n\n"
            )
            TelegramBot.bot.send_message(call.message.chat.id, message, parse_mode="Markdown")
        else:
            TelegramBot.bot.send_message(call.message.chat.id, "❌ Address not configured. Please contact support.")

    @bot.callback_query_handler(func=lambda call: call.data == 'donate_tgstars')
    def handle_donate_tgstars(call):
        TelegramBot.bot.send_message(
            call.message.chat.id,
            "You chose ⭐ *TG Stars*.\nPlease send stars via Telegram premium gifting.",
            parse_mode='Markdown'
        )

    # Default fallback for any unrecognized message 
    @bot.message_handler(func=lambda message: True)
    @check_if_needs_update
    def default_message(message):
        print("ECXECUTING DEFAULT MESSAGE")
        telegram_user_id = retrieve_username(message.from_user)
        if telegram_user_id in TelegramBot.admin_users and telegram_user_id in TelegramBot.admin_user_broadcasts:
            users = UserRepository.get_users()
            for user in users:
                try:
                    logger.info(f"chat_id: {user.chat_id}  is_updated: {user.is_updated}")
                    TelegramBot.bot.send_message(user.chat_id, message.text)
                    logger.info(f"Done {user.chat_id}")
                except:
                    logger.error(f'Exception ->{user.chat_id}', exc_info=True)
                    continue
            TelegramBot.admin_user_broadcasts.discard(telegram_user_id)
        else:
            TelegramBot.bot.send_message(message.chat.id, messages_content['default_fallback'])

    def start_bot(self):
        while True:
            try:
                logger.info("Starting bot polling...")
                TelegramBot.bot.polling(none_stop=True, timeout=60)
            except Exception as e:
                logger.error("Bot crashed with exception:", exc_info=True)
                logger.info("Restarting bot polling in 10 seconds...")
                time.sleep(10) 
