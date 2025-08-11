import os
import telebot
from telebot import types

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "123456789"))

bot = telebot.TeleBot(TOKEN)

users = {}
pending_phone = {}

# Старт
@bot.message_handler(commands=['start'])
def start(message):
    kb = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    btn = types.KeyboardButton("📱 Надати номер телефону", request_contact=True)
    kb.add(btn)
    bot.send_message(message.chat.id, "Будь ласка, підтвердіть свій номер телефону, щоб почати чат", reply_markup=kb)
    pending_phone[message.chat.id] = True

# Отримання телефону
@bot.message_handler(content_types=['contact'])
def contact_handler(message):
    if pending_phone.get(message.chat.id):
        users[message.chat.id] = {
            "name": message.from_user.first_name,
            "phone": message.contact.phone_number
        }
        pending_phone.pop(message.chat.id, None)
        bot.send_message(message.chat.id, "Дякую! Ви можете писати повідомлення.", reply_markup=types.ReplyKeyboardRemove())

# Адмін меню
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.chat.id == ADMIN_ID:
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("📋 Список користувачів", "🗑 Видалити користувача")
        bot.send_message(message.chat.id, "Адмін панель", reply_markup=kb)

# Список користувачів
@bot.message_handler(func=lambda m: m.chat.id == ADMIN_ID and m.text == "📋 Список користувачів")
def list_users(message):
    if not users:
        bot.send_message(message.chat.id, "Список пустий.")
        return
    text = "👥 Список користувачів:
"
    for uid, data in users.items():
        text += f"{data['name']} — {data['phone']} (ID: {uid})
"
    bot.send_message(message.chat.id, text)

# Видалення користувача
@bot.message_handler(func=lambda m: m.chat.id == ADMIN_ID and m.text == "🗑 Видалити користувача")
def delete_user_prompt(message):
    bot.send_message(message.chat.id, "Введіть ID користувача для видалення:")
    bot.register_next_step_handler(message, delete_user)

def delete_user(message):
    try:
        uid = int(message.text)
        if uid in users:
            users.pop(uid)
            bot.send_message(message.chat.id, "Користувач видалений.")
        else:
            bot.send_message(message.chat.id, "Користувач не знайдений.")
    except ValueError:
        bot.send_message(message.chat.id, "Невірний ID.")

# Фото
@bot.message_handler(content_types=['photo'])
def photo_handler(message):
    if message.chat.id == ADMIN_ID:
        bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
    else:
        bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)

# Пересилка повідомлень
@bot.message_handler(func=lambda m: not pending_phone.get(m.chat.id))
def forward_message(message):
    if message.chat.id == ADMIN_ID:
        # Якщо адміністратор відповідає на повідомлення користувача
        if message.reply_to_message and message.reply_to_message.forward_from:
            bot.send_message(message.reply_to_message.forward_from.id, message.text)
    else:
        bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)

bot.polling(none_stop=True)
