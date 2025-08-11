from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputFile,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
)

TOKEN = "7851494992:AAFeeAuNzI6UeIYZe9167IJfP_ZbwOLvMA0"
ADMIN_ID = 861941692

users = {}  # user_id -> dict {phone, first_name, last_name, username}
active_chats = {}  # user_id -> admin_id
active_admins = {}  # admin_id -> user_id
user_waiting_for_request = {}  # user_id -> тема заявки

phone_kb = ReplyKeyboardMarkup(
    [[KeyboardButton("Поділитись номером 📞", request_contact=True)]],
    resize_keyboard=True,
    one_time_keyboard=True,
)

user_kb = ReplyKeyboardMarkup(
    [["Створення сайту"], ["Консультації"], ["Створення міток"], ["Контекстна реклама"]],
    resize_keyboard=True,
)

admin_kb = ReplyKeyboardMarkup(
    [["Оновити список користувачів"], ["/users"], ["Завершити розмову"]],
    resize_keyboard=True,
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == ADMIN_ID:
        await update.message.reply_text(
            "Вітаю, Адміністраторе! Оберіть дію:", reply_markup=admin_kb
        )
        return

    if user_id in users:
        await update.message.reply_text(
            "Вітаю! Оберіть потрібний пункт меню:", reply_markup=user_kb
        )
    else:
        await update.message.reply_text(
            "Привіт! Будь ласка, поділіться своїм номером телефону для продовження.",
            reply_markup=phone_kb,
        )


async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    contact = update.message.contact
    if contact is None or contact.user_id != user_id:
        await update.message.reply_text("Будь ласка, надішліть саме свій контакт.")
        return
    phone = contact.phone_number
    users[user_id] = {
        "phone": phone,
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "username": user.username or "",
    }
    await update.message.reply_text(
        f"Дякую, ваш номер {phone} отримано.\nТепер ви можете обрати потрібний пункт меню.",
        reply_markup=user_kb,
    )
    try:
        await context.bot.send_message(
            ADMIN_ID,
            f"Новий користувач: {user.first_name} {user.last_name} (@{user.username or 'N/A'})\nID: {user_id}\nНомер телефону: {phone}",
        )
    except Exception as e:
        print(f"Помилка при повідомленні адміну: {e}")


async def send_users_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not users:
        await update.message.reply_text("Поки що немає зареєстрованих користувачів.")
        return
    buttons = []
    for uid, info in users.items():
        name = f"{info.get('first_name', '')} {info.get('last_name', '')}".strip()
        if not name:
            name = info.get("username", "Немає імені")
        btn_text = f"{name} (ID: {uid})"
        buttons.append(
            [
                InlineKeyboardButton(text=btn_text, callback_data=f"chat_{uid}"),
                InlineKeyboardButton(text="Видалити", callback_data=f"del_{uid}"),
            ]
        )
    keyboard = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(
        "Оберіть користувача, щоб почати чат або видалити:", reply_markup=keyboard
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("chat_"):
        target_user_id = int(data.split("_")[1])
        if target_user_id not in users:
            await query.message.reply_text("Користувача не знайдено.")
            return
        active_chats[target_user_id] = ADMIN_ID
        active_admins[ADMIN_ID] = target_user_id
        info = users[target_user_id]
        name = f"{info.get('first_name', '')} {info.get('last_name', '')}".strip()
        username = info.get("username", "")
        await query.message.reply_text(
            f"Ви почали чат з користувачем:\n{name} (@{username if username else 'N/A'})\nID: {target_user_id}\n\n"
            "Тепер надсилайте повідомлення або фото. Для завершення чату напишіть 'Завершити розмову'."
        )
        try:
            await context.bot.send_message(
                target_user_id,
                "Адміністратор розпочав з вами чат. Ви можете писати свої повідомлення або надсилати фото.",
            )
        except:
            pass

    elif data.startswith("del_"):
        target_user_id = int(data.split("_")[1])
        if target_user_id not in users:
            await query.message.reply_text("Користувача не знайдено або вже видалено.")
            return

        if target_user_id in active_chats:
            active_admin = active_chats.pop(target_user_id)
            active_admins.pop(active_admin, None)
            try:
                await context.bot.send_message(
                    target_user_id, "Вас видалили з бази користувачів, чат завершено."
                )
            except:
                pass

        users.pop(target_user_id)
        await query.message.reply_text(f"Користувача з ID {target_user_id} видалено з бази.")


async def user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Якщо користувач не підтвердив номер — не даємо писати
    if user_id != ADMIN_ID and user_id not in users:
        await update.message.reply_text(
            "Будь ласка, поділіться своїм номером телефону, натиснувши кнопку 'Поділитись номером 📞' через /start"
        )
        return

    # Обробка адміністратора
    if user_id == ADMIN_ID:
        text = update.message.text if update.message.text else None

        if text:
            if text.lower() == "оновити список користувачів" or text == "/users":
                await send_users_list(update, context)
                return

            if text.lower() == "завершити розмову":
                if ADMIN_ID in active_admins:
                    uid = active_admins.pop(ADMIN_ID)
                    active_chats.pop(uid, None)
                    await update.message.reply_text("Чат завершено.")
                    try:
                        await context.bot.send_message(uid, "Адміністратор завершив чат.")
                    except:
                        pass
                else:
                    await update.message.reply_text("Ви не ведете жодного чату.")
                return

            if ADMIN_ID in active_admins:
                uid = active_admins[ADMIN_ID]
                try:
                    await context.bot.send_message(uid, text)
                except:
                    await update.message.reply_text(
                        "Не вдалося надіслати повідомлення користувачу."
                    )
            else:
                await update.message.reply_text(
                    "Натисніть 'Оновити список користувачів' або /users, щоб почати чат."
                )
        elif update.message.photo:
            # Адмін надсилає фото користувачу
            if ADMIN_ID in active_admins:
                uid = active_admins[ADMIN_ID]
                photo = update.message.photo[-1]  # найкраща якість
                caption = update.message.caption if update.message.caption else None
                try:
                    await context.bot.send_photo(uid, photo.file_id, caption=caption)
                except:
                    await update.message.reply_text(
                        "Не вдалося надіслати фото користувачу."
                    )
            else:
                await update.message.reply_text(
                    "Немає активного чату. Спочатку почніть чат з користувачем."
                )
        return

    # Обробка клієнта — заявка після вибору кнопки меню
    if user_id in user_waiting_for_request:
        тема = user_waiting_for_request.pop(user_id)
        текст_заявки = update.message.text

        # Відповідь клієнту
        await update.message.reply_text(
            "Дякуємо! Ваша заявка прийнята. Чекайте відповіді від адміністратора."
        )

        # Повідомлення адміністратору
        info = users.get(user_id, {})
        ім'я = f"{info.get('first_name', '')} {info.get('last_name', '')}".strip()
        юзернейм = info.get("username", "")
        телефон = info.get("phone", "")

        повідомлення_для_адміна = (
            f"Нова заявка від користувача:\n"
            f"Ім'я: {ім'я}\n"
            f"Телефон: {телефон}\n"
            f"Username: @{юзернейм if юзернейм else 'N/A'}\n"
            f"ID: {user_id}\n"
            f"Тема заявки: {тема}\n"
            f"Текст заявки:\n{текст_заявки}"
        )
        try:
            await context.bot.send_message(ADMIN_ID, повідомлення_для_адміна)
        except Exception as e:
            print(f"Помилка при надсиланні адміну: {e}")
        return

    # Якщо клієнт просто натиснув кнопку меню (одна з тем)
    if update.message.text:
        текст = update.message.text.lower()

        теми = {
            "створення сайту": "Створення сайту",
            "консультації": "Консультації",
            "створення міток": "Створення міток",
            "контекстна реклама": "Контекстна реклама",
        }

        if текст in теми:
            user_waiting_for_request[user_id] = теми[текст]
            await update.message.reply_text(
                f"Ви обрали '{теми[текст]}'. Будь ласка, напишіть детальніше, що вам потрібно."
            )
            return

        # Якщо повідомлення не відповідає меню
        await update.message.reply_text(
            "Будь ласка, оберіть пункт меню або напишіть /start для початку."
        )
        return

    # Обробка фото клієнта (як було)
    if update.message.photo:
        if user_id in active_chats:
            admin_id = active_chats[user_id]
            photo = update.message.photo[-1]  # найкраща якість
            caption = update.message.caption if update.message.caption else None
            try:
                await context.bot.send_photo(admin_id, photo.file_id, caption=caption)
            except:
                pass
        else:
            await update.message.reply_text(
                "Щоб надсилати повідомлення чи фото, почніть чат з адміністратором."
            )


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("users", send_users_list))
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.add_handler(MessageHandler(filters.PHOTO | (filters.TEXT & ~filters.COMMAND), user_message))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Бот запущено...")
    app.run_polling()


if __name__ == "__main__":
    main()
