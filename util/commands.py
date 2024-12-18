import sqlite3
from datetime import datetime, timedelta
from telebot.apihelper import ApiException
import time
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton 
import stripe
from dotenv import load_dotenv
import os

db_path = os.getenv("DATABASE_PATH")

def create_database():
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute('CREATE TABLE IF NOT EXISTS "users" ("id" INTEGER NOT NULL, "user_id" blob, "username" blob, "user_email" blob, "customer_id" blob, "subscription_id" blob, "plan" blob, "purchase_time" blob, "is_valid" bool, "expiration_date" blob, PRIMARY KEY("id" AUTOINCREMENT));')
    conn.commit()
    
    cur.close()
    conn.close()


def start(bot, message):
    # Send the welcome message with the START button
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    btn_start = KeyboardButton('START')
    markup.add(btn_start)
    bot.send_message(message.chat.id, "Welcome! Please click the button below to proceed:", reply_markup=markup)

    # Send the main menu options
    markup = create_main_menu_markup()
    bot.send_message(message.chat.id, "Select option:", reply_markup=markup)


#send main menu buttons
def create_main_menu_markup():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("💸PAY FOR ACCESS💸", callback_data='pay_for_access'))
    markup.add(InlineKeyboardButton("🔍MORE ABOUT THE CHANNEL🔍", callback_data='more_about_channel'))
    markup.add(InlineKeyboardButton("❓ASK A QUESTION❓", url='tg://resolve?domain=anthony42145'))
    markup.add(InlineKeyboardButton("📆SUBSCRIPTION DAYS LEFT📆", callback_data='subscription_days_left'))
    markup.add(InlineKeyboardButton("UNSUBSCRIBE", callback_data='unsubscribe'))
    
    return markup


def add_user_subscription(bot, user_id, GROUP_CHAT_ID, email, username, customer_id, subscription_id, plan, purchase_time, expiration_date, duration):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if the user already exists in the database
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    existing_user = cursor.fetchone()
    
    if existing_user:
        
        bot.send_message(user_id, purchase_time, expiration_date)
        # User exists, update the subscription information
        cursor.execute('''
            UPDATE users
            SET customer_id = ?, subscription_id = ?, plan = ?, purchase_time = ?, expiration_date = ?
            WHERE user_id = ?
        ''', (customer_id, subscription_id, plan, purchase_time, expiration_date, user_id))
        
        conn.commit()
        conn.close()
        
        bot.send_message(user_id, f"Your subscription has been updated. Thank you for your continued support!")
    else:
        # User doesn't exist, add them to the database
        cursor.execute('''
            INSERT INTO users (user_id, username, user_email, customer_id, subscription_id, plan, purchase_time, is_valid, expiration_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, email, customer_id, subscription_id, plan, purchase_time, 1, expiration_date))
        
        conn.commit()
        conn.close()

def generate_link(bot, GROUP_CHAT_ID, user_id, duration):
    try:
        # Link will expire after 3 hours
        invite_link = bot.create_chat_invite_link(GROUP_CHAT_ID, member_limit=1, expire_date=link_expiration_date)

        
    except Exception as e:
        print(f"An error occurred while generating or sending the invite link: {e}")
      

def send_invite_link_if_exists(bot, user_id, GROUP_CHAT_ID, duration):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the user exists in the database
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        existing_user = cursor.fetchone()

        cursor.close()
        conn.close()
        
        if not existing_user:
            link_expiration_date = int(time.time()) + (3 * 60 * 60)
            invite_link = bot.create_chat_invite_link(GROUP_CHAT_ID, member_limit=1, expire_date=link_expiration_date)
            
            bot.send_message(user_id, f"Thank you for buying the subscription for {duration} days!")
            bot.send_message(user_id, f"Here is your invite link🔗: {invite_link.invite_link}\nYour link will expire after 3 hours⌛")
        else:
            bot.send_message(user_id, f"Your payment was recieved")
    except Exception as e:
        print(f"An error occurred while checking user in the database: {e}")
        
              
def unsubscribe_user(user_id):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT subscription_id FROM users WHERE user_id = ?', (user_id,))
        subscription_id = cursor.fetchone()
        
        if subscription_id is not None:
            
            subscription = stripe.Subscription.retrieve(subscription_id[0])
            subscription.delete()

            cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
            conn.commit()

            cursor.close()
            conn.close()
            return True  # Return True if the update was successful
    
    except Exception as e:
        print("Error:", e)
        return False  # Return False if there was an error


def remove_user(bot, group_chat_id, user_id):
    try:
        # Kick the user from the chat
        bot.kick_chat_member(group_chat_id, user_id)
        
        # Optionally, unban the user to allow them to rejoin the chat
        bot.unban_chat_member(group_chat_id, user_id)
        
        # Connect to the SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Delete the user from the database
        cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
        
        conn.commit()
        conn.close()
        
        return True  # Return True if the user was successfully kicked and deleted from the database
    except telebot.apihelper.ApiException as e:
        print(f"ApiException error: {e}")
        return False  # Return False if there was an API error (e.g., user not found in the chat or bot lacks permissions)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False  # Return False if there was an unexpected error


def subscription_check(user_id):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT EXISTS(SELECT 1 FROM users WHERE user_id = ?)', (user_id,))
        exists = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return exists == 1
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return False



def expiration_date_funct(user_id):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
    
        cursor.execute('SELECT expiration_date FROM users WHERE user_id = ?', (user_id,))
        expiration_date = cursor.fetchone()
        
        expiration_date = expiration_date[0]
        
        if expiration_date is not None:
                        
            return expiration_date
    
        else:
            return -1
        
    except Exception as e:
        return -1

    
# def update_subscription_status(bot, group_chat_id):
#     while True:
        
#         # Sleep for n seconds
#         n = 60 * 60 * 24
#         time.sleep(n)
#         # Connect to the database
#         conn = sqlite3.connect(db_path)
#         cursor = conn.cursor()

#         # Fetch users whose subscription is still valid
#         cursor.execute('SELECT * FROM users')
#         users = cursor.fetchall()

#         for user in users:
            
#             days_left = user[7]
#             user_id = user[1]
#             is_valid = user[5]
            
#             if days_left <= 3 and days_left > 0 and is_valid:
                
#                 markup = InlineKeyboardMarkup()
#                 markup.add(InlineKeyboardButton("Re-subscription", callback_data='pay_for_access'))
                
#                 bot.send_message(user_id, f"Your subscription will expire after {days_left} days", reply_markup=markup)
            
#             if days_left > 0 and is_valid:
#                 days_left -= 1  
#                 cursor.execute('UPDATE users SET days_left = ? WHERE user_id = ?', (days_left, user_id,))
                
#             elif days_left == 0 and is_valid:
#                 cursor.execute('UPDATE users SET is_valid = 0 WHERE user_id = ?', (user_id,))
#                 remove_user(bot, group_chat_id, user_id)
                
#                 markup = InlineKeyboardMarkup()
#                 markup.add(InlineKeyboardButton("Re-subscription", callback_data='pay_for_access'))
                
#                 bot.send_message(user_id, f"You have been removed from the chat bacause your subscription has expired", reply_markup=markup)
#         # Commit changes to the database
#         conn.commit()
#         conn.close()
    
