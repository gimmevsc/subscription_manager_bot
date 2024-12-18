import telebot
from util.commands import *
import logging
from datetime import datetime, timedelta
from telebot.types import LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton, Message 
from threading import Thread
from util.gdrive_backup import *
from flask import Flask, request, jsonify
import stripe
from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("PRIVATE_CHAT_ID")
PAYMENT_PROVIDER_TOKEN = os.getenv("PAYMENT_PROVIDER_TOKEN")
stripe.api_key = os.getenv("STRIPE_API_KEY")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")


bot = telebot.TeleBot(BOT_TOKEN)

app = Flask(__name__)

# @app.route('/')
# def hello_world():
#     return 'Hello, World!'

# download db from Google Drive
download_database()

#create db if doesn't exist
create_database()


# #subtract 1 day from days_left every day
# update_thread = Thread(target=lambda: update_subscription_status(bot, GROUP_CHAT_ID))
# update_thread.start()

#backup db to google drive every n time
replacing_thread = Thread(target=replace_list_db_on_google_drive)
replacing_thread.start()


subscription_plans = {
    '1 Day - 1€': {
        'stripe_price_id': 'price_id',
        'duration': 1,
        'plan_name': '1 Day'
    },
    '1 Month - 5€': {
        'stripe_price_id': 'price_id',
        'duration': 30,
        'plan_name': '1 Month'
    },
    '3 Months - 14€': {
        'stripe_price_id': 'price_id',
        'duration': 90,
        'plan_name': '3 Months'
    },
    '1 Year - 49€': {
        'stripe_price_id': 'price_id',
        'duration': 365,
        'plan_name': '1 Year'
    }
}

# Handler to ignore messages in groups
@bot.message_handler(func=lambda message: message.chat.type in ['group', 'supergroup'])
def ignore_group_messages(message):
     # Do nothing if the message is in a group or supergroup
     pass

@bot.message_handler(commands=['start'])
def handle_start(message):
    start(bot, message)


@bot.message_handler(func=lambda message: message.text == 'START')
def handle_start(message):
    start(bot, message)
    

#find out GROUP_CHAT_ID
@bot.message_handler(commands=['chat_id'])
def asd(message: Message):
    chat_id = message.chat.id
    bot.send_message(message.chat.id, f'{chat_id}')



@app.route('/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
        print(event)
    except ValueError as e:
        logging.error(f"Invalid payload: {e}")
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError as e:
        logging.error(f"Invalid signature: {e}")
        return 'Invalid signature', 400

    if event['type'] == 'customer.subscription.created':
        handle_subscription_created(event['data']['object'])
    if event['type'] == 'customer.subscription.updated':
        handle_subscription_updated(event['data']['object'])
    if event['type'] == 'customer.subscription.deleted':
        handle_subscription_deleted(event['data']['object'])
    if event['type'] == 'invoice.payment_succeeded':
        handle_invoice_payment_succeeded(event['data']['object'])
    if event['type'] == 'invoice.payment_failed':
        handle_invoice_payment_failed(event['data']['object'])

    return jsonify(success=True)


@bot.callback_query_handler(func=lambda call: call.data == 'pay_for_access')
def pay_for_access(call):
    markup = InlineKeyboardMarkup()
    for plan in subscription_plans.keys():
        markup.add(InlineKeyboardButton(plan, callback_data=plan))
    markup.add(InlineKeyboardButton("GO BACK🔙", callback_data='go_back'))
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Choose a subscription plan:", reply_markup=markup)



@bot.callback_query_handler(func=lambda call: call.data in subscription_plans.keys())
def send_invoice(call):
    user_id = call.from_user.id
    username = call.from_user.username
    plan = call.data
    plan_info = subscription_plans[plan]
    stripe_price_id = plan_info['stripe_price_id']
    duration_days = plan_info['duration']
    
    if not subscription_check(user_id):  # Check if the user is not in the database
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': stripe_price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=f'https://t.me/trusov_vip_bot',  # Update to your actual success URL
            cancel_url=f'https://t.me/trusov_vip_bot',
            subscription_data={
                'metadata': {
                    'user_id': str(user_id),
                    'plan': str(plan),
                    'username': str(username),
                    'duration': str(duration_days)
                }
            }
        )

        bot.send_message(
            call.message.chat.id,
            "Click the button below to complete the payment:",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("Complete Payment", url=session.url)
            )
        )
    else:
        bot.send_message(
            user_id,
            "You already have an active subscription. You cannot purchase another one."
        )


def handle_invoice_payment_failed(event):
    
    user_id = event['subscription_details']['metadata']['user_id']
    
    try:
        member_status = bot.get_chat_member(GROUP_CHAT_ID, user_id).status
        
        if member_status in ['member', 'administrator', 'creator']:
            # Notify the user about the failed payment
            bot.send_message(user_id, "Your payment for subscription has failed")
            
            # Remove the user from the group
            remove_user(bot, GROUP_CHAT_ID, user_id)

        else:
            bot.send_message(user_id, "Your payment has failed")
    
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        

def handle_invoice_payment_succeeded(event):
    pass
    # customer_id = event['customer']
    # customer = stripe.Customer.retrieve(customer_id)
    # email = customer.email
    # subscription_id = event['id']
    # user_id = int(event['subscription_details']['metadata']['user_id'])
    # username = event['subscription_details']['metadata']['username']
    # plan = event['subscription_details']['metadata']['plan']
    # duration = event['subscription_details']['metadata']['duration']    
    
    # add_user_subscription(bot, user_id, GROUP_CHAT_ID, email, username, customer_id, subscription_id, plan, ex, pur, duration)



@bot.callback_query_handler(func=lambda call: call.data == 'more_about_channel')
def more_about_channel(call):
    user_id = call.from_user.id

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("GO BACK🔙", callback_data='go_back'))

    message_text = "🔥 Join Pavel Trusov VIP 🔥\n\nA community for those committed to transforming their lives by becoming smarter 🧠 and stronger 💪.\n\nEvery day, receive invaluable knowledge 📚 you won’t find anywhere else on the internet 🌐."

    bot.edit_message_text(
        chat_id=user_id,
        message_id=call.message.message_id,
        text=message_text,
        reply_markup=markup
    )



@bot.callback_query_handler(func=lambda call: call.data == 'unsubscribe')
def unsubscribe(call : Message):
    user_id = call.from_user.id

    if subscription_check(user_id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Yes", callback_data='confirm_unsubscribe'))
        markup.add(InlineKeyboardButton("No", callback_data='go_back'))

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text='<b>Are you sure you want to unsubscribe</b>❓',
            reply_markup=markup,
            parse_mode='html'
        )
    else:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("GO BACK🔙", callback_data='go_back'))

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="<b>You don't have any subscriptions, you better subscribe to stop being a mediocre!</b>",
            reply_markup=markup,
            parse_mode='html'
        )

# @bot.message_handler(func=lambda message: True, content_types=['new_chat_members'])
# def welcome_new_member(message):
#     for new_member in message.new_chat_members:
#         user_id = new_member.id
#         user_name = new_member.first_name
#         welcome_message = f"Welcome {user_name} to the group!"

#         # Send a welcome message
#         sent_message = bot.send_message(message.chat.id, welcome_message)
        
#         # Check for messages with invitation links and delete them
#         if 'invite' in message.text or 'Thank you for' in message.text:
#             bot.delete_message(message.chat.id, message.message_id)
#             bot.delete_message(message.chat.id, sent_message.message_id)  # Optionally delete the welcome message

#         logging.info(f"User {user_id} ({user_name}) joined the group.")


def handle_subscription_created(event):
    pass


def handle_subscription_updated(event):
    customer_id = event['customer']
    customer = stripe.Customer.retrieve(customer_id)
    email = customer.email
    subscription_id = event['id']
    user_id = int(event['metadata']['user_id'])
    username = event['metadata']['username']
    plan = event['metadata']['plan']
    purchase_time = event['current_period_start']
    expiration_date = event['current_period_end']
    duration = event['metadata']['duration']    
        
    send_invite_link_if_exists(bot, user_id, GROUP_CHAT_ID, duration)

    add_user_subscription(bot, user_id, GROUP_CHAT_ID, email, username, customer_id, subscription_id, plan, purchase_time, expiration_date, duration)


def handle_subscription_deleted(event):
    
    user_id = int(event['metadata']['user_id'])
    
    remove_user(bot, GROUP_CHAT_ID, user_id)
        
    bot.send_message(user_id, "Your subscription has been canceled. If you have any questions, feel free to contact support.")
    

@bot.callback_query_handler(func=lambda call: call.data == 'more_about_channel')
def more_about_channel(call):
    user_id = call.from_user.id

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("GO BACK🔙", callback_data='go_back'))

    message_text = "🔥 Join Pavel Trusov VIP 🔥\n\nA community for those committed to transforming their lives by becoming smarter 🧠 and stronger 💪.\n\nEvery day, receive invaluable knowledge 📚 you won’t find anywhere else on the internet 🌐."

    bot.edit_message_text(
        chat_id=user_id,
        message_id=call.message.message_id,
        text=message_text,
        reply_markup=markup
    )
    


@bot.callback_query_handler(func=lambda call: call.data == 'subscription_days_left')
def subscription_days_left(call):
    user_id = call.from_user.id

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("GO BACK🔙", callback_data='go_back'))

    expiration_timestamp = int(expiration_date_funct(user_id))  # Retrieve expiration timestamp once

    if expiration_timestamp != -1:
        expiration_dd= datetime.fromtimestamp(expiration_timestamp)
        message_text = f"<b>Your subscription expires on: {expiration_dd}</b>"
    else:
        message_text = "<b>You don't have any subscriptions</b>"

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=message_text,
        reply_markup=markup,
        parse_mode='html'
    
    )



@bot.callback_query_handler(func=lambda call: call.data == 'unsubscribe')
def unsubscribe(call : Message):
    
    user_id = call.from_user.id
    
    if subscription_check(user_id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Yes", callback_data='confirm_unsubscribe'))
        markup.add(InlineKeyboardButton("No", callback_data='go_back'))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text='<b>Are you sure you want to unsubscribe</b>❓',
            reply_markup=markup,
            parse_mode='html'
        )
    else:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("GO BACK🔙", callback_data='go_back'))
    
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="<b>You don't have any subscriptions, you better subscribe to stop being a mediocre!</b>",
            reply_markup=markup,
            parse_mode='html'
        )
        


#go_back button
@bot.callback_query_handler(func=lambda call: call.data == 'go_back')
def go_back(call):
    
    markup = create_main_menu_markup()
    
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Select option:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'confirm_unsubscribe')
def confirm_unsubscribe(call):
    
    user_id = call.from_user.id
    
    try:
        unsubscribe_user(int(user_id))
        remove_user(bot, GROUP_CHAT_ID, user_id)
        
        print(f"Subscription was canceled successfully.")
    except stripe.error.StripeError as e:
        # Handle any errors from the Stripe API
        print(f"Stripe error: {e}")
        # Notify the user about the error or log it for further investigation
    
    # Delete the confirmation message
    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    
    # Send the main menu buttons to the user
    markup = create_main_menu_markup()
    bot.send_message(user_id, text="<b>You have successfully unsubscribed😢</b>", parse_mode='html', reply_markup=markup)

    
@bot.message_handler(func=lambda message: message.text.lower() == 'glory to ukraine!')
def handle_slava_ukraini(message):
    bot.reply_to(message, 'Glory to the Heroes!')


@bot.pre_checkout_query_handler(func=lambda query: True)
def pre_checkout_query(pre_checkout_query):
    try:
        bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)
    except Exception as e:
        logging.error(f"Error answering pre-checkout query: {e}")
        bot.answer_pre_checkout_query(pre_checkout_query.id, ok=False, error_message="An error occurred. Please try again later.")

def run_flask():
    app.run(host='0.0.0.0', port=5001)

def run_bot():
    bot.infinity_polling()


if __name__ == '__main__':
    flask_thread = Thread(target=run_flask)
    bot_thread = Thread(target=run_bot)

    flask_thread.start()
    bot_thread.start()

    flask_thread.join()
    bot_thread.join()
