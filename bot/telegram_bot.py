'''
File includes the main Telegram bot class 
with all the availabe message callbacks and query callbacks 
'''

from telebot import TeleBot, types # Import 'types' for InlineKeyboardMarkup and InlineKeyboardButton
from logger import logger
from .utils import *
from database.user import UserRepository
from marzban_api.marzban_service import MarzbanService
import os
import time

# --- Constants for Stars Amounts ---
# These are the amounts in Stars (XTR currency)
STAR_AMOUNTS = {
    "select_stars_amount_1": 1,
    "select_stars_amount_100": 100,
    "select_stars_amount_500": 500,
    "select_stars_amount_1000": 1000,
    "select_stars_amount_5000": 5000,
}

# --- Callback data prefixes ---
CALLBACK_DONATE_STARS_INITIAL = "donate_tgstars" # Existing callback for the initial 'TG Stars' button
CALLBACK_SELECT_STARS_AMOUNT_PREFIX = "select_stars_amount_"


class TelegramBot():
    print("+++TELEGRAM BOT+++")
    bot = TeleBot(os.getenv('TELEGRAM_BOT_TOKEN'))
    admin_users = os.getenv('ADMIN_USERS').split(',')
    admin_user_broadcasts = set()

    def check_if_needs_update(func):
        print("Execuitng check_if_needs_update")
        def inner(obj): 
            try:
                user, _ =  UserRepository.get_user(retrieve_username(obj.from_user))
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
        try:
            telegram_user_id = retrieve_username(call.from_user)
            configs = UserRepository.get_user_configurations(telegram_user_id)
            if len(configs) > 0: 
                TelegramBot.bot.send_message(call.message.chat.id, messages_content['configs_exist'])
            else:
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
        # Using the defined constant for clarity
        keyboard.add(types.InlineKeyboardButton("⭐ TG Stars", callback_data=CALLBACK_DONATE_STARS_INITIAL))
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

    # --- NEW STARS FUNCTIONALITY ---

    @bot.callback_query_handler(func=lambda call: call.data == CALLBACK_DONATE_STARS_INITIAL)
    def handle_donate_tgstars_initial(call):
        """
        Handles the initial 'TG Stars' button click, presenting amount options.
        """
        try:
            TelegramBot.bot.answer_callback_query(call.id) # Always answer the callback query

            keyboard = types.InlineKeyboardMarkup()
            # Create buttons for each star amount
            for key, amount in STAR_AMOUNTS.items():
                keyboard.add(types.InlineKeyboardButton(f"{amount} Stars", callback_data=key))

            TelegramBot.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="Please select the amount of Stars you'd like to donate:",
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Exception in handle_donate_tgstars_initial: {e}", exc_info=True)
            TelegramBot.bot.send_message(call.message.chat.id, messages_content['unexpected_error'])


    @bot.callback_query_handler(func=lambda call: call.data.startswith(CALLBACK_SELECT_STARS_AMOUNT_PREFIX))
    def handle_select_stars_amount(call):
        """
        Handles the selection of a specific Stars amount and generates an invoice.
        """
        try:
            TelegramBot.bot.answer_callback_query(call.id) # Answer the callback query

            amount_str = call.data.replace(CALLBACK_SELECT_STARS_AMOUNT_PREFIX, "")
            try:
                amount = int(amount_str)
            except ValueError:
                TelegramBot.bot.send_message(call.message.chat.id, "Invalid amount selected. Please try again.")
                return

            if amount not in STAR_AMOUNTS.values():
                TelegramBot.bot.send_message(call.message.chat.id, "Invalid amount. Please choose from the given options.")
                return

            invoice_payload = f"stars_donation_{amount}_{call.from_user.id}_{int(time.time())}"
            prices = [types.LabeledPrice(label=f"Donation of {amount} Stars", amount=amount)]

            TelegramBot.bot.send_invoice(
                chat_id=call.message.chat.id,
                title=f"Donate {amount} Stars",
                description=f"Thank you for your generous donation of {amount} Telegram Stars!",
                invoice_payload=invoice_payload,
                provider_token="",
                currency="XTR",
                prices=prices,
                start_parameter="stars_donation",
                need_shipping_address=False,
                is_flexible=False
            )
            TelegramBot.bot.send_message(
                call.message.chat.id,
                text=f"Initiated donation for {amount} Stars. Please confirm the payment above."
            )

        except Exception as e:
            logger.error(f"Exception in handle_select_stars_amount: {e}", exc_info=True)
            TelegramBot.bot.send_message(call.message.chat.id, messages_content['unexpected_error'])

    @bot.pre_checkout_query_handler(func=lambda query: True)
    def pre_checkout_callback(pre_checkout_query):
        """
        Handles pre-checkout queries sent by Telegram before a payment is finalized.
        You MUST respond to this query.
        """
        try:
            # Here you can perform last-minute checks on the payment
            # For example, verify the invoice_payload to ensure it's a valid donation
            if pre_checkout_query.invoice_payload.startswith("stars_donation_"):
                TelegramBot.bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)
                logger.info(f"Pre-checkout query approved for user {pre_checkout_query.from_user.id} with payload {pre_checkout_query.invoice_payload}")
            else:
                # If the payload doesn't match our expected format, reject it
                TelegramBot.bot.answer_pre_checkout_query(
                    pre_checkout_query.id,
                    ok=False,
                    error_message="Something went wrong with your donation. Please try again."
                )
                logger.warning(f"Pre-checkout query rejected for unknown payload: {pre_checkout_query.invoice_payload}")
        except Exception as e:
            logger.error(f"Exception in pre_checkout_callback: {e}", exc_info=True)
            # In case of an unexpected error, it's safer to reject the payment
            TelegramBot.bot.answer_pre_checkout_query(
                pre_checkout_query.id,
                ok=False,
                error_message="An internal error occurred while processing your payment. Please try again later."
            )


    @bot.message_handler(content_types=['successful_payment'])
    def successful_payment_callback(message):
        """
        Handles successful payment messages. This is where you confirm the donation
        and update your records.
        """
        try:
            payment_info = message.successful_payment
            amount_paid_stars = payment_info.total_amount
            invoice_payload = payment_info.invoice_payload
            telegram_payment_charge_id = payment_info.telegram_payment_charge_id

            user_id = message.from_user.id
            username = retrieve_username(message.from_user) # Using your utility function

            logger.info(f"User {username} ({user_id}) successfully donated {amount_paid_stars} Stars.")
            logger.info(f"Invoice Payload: {invoice_payload}")
            logger.info(f"Telegram Charge ID: {telegram_payment_charge_id}")

            TelegramBot.bot.send_message(
                message.chat.id,
                f"🎉 Thank you, for your generous donation of {amount_paid_stars} Stars! "
                "Your support is greatly appreciated!"
            )
        except Exception as e:
            logger.error(f"Exception in successful_payment_callback: {e}", exc_info=True)
            TelegramBot.bot.send_message(message.chat.id, messages_content['unexpected_error'])


    # Default fallback for any unrecognized message 
    @bot.message_handler(func=lambda message: True)
    @check_if_needs_update
    def default_message(message):
        telegram_user_id = retrieve_username(message.from_user)
        if telegram_user_id in TelegramBot.admin_users and telegram_user_id in TelegramBot.admin_user_broadcasts:
            users = UserRepository.get_users() # Assuming this retrieves all users for broadcasting
            for user in users:
                try:
                    logger.info(f"chat_id: {user.chat_id}  is_updated: {user.is_updated}")
                    TelegramBot.bot.send_message(user.chat_id, message.text)
                    logger.info(f"Done {user.chat_id}")
                except Exception: # Catch specific exceptions like ApiTelegramException if possible
                    logger.error(f'Exception -> Failed to send broadcast to {user.chat_id}', exc_info=True)
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