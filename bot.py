import os
import gspread
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters
from datetime import datetime
import logging
import json
from flask import Flask
from threading import Thread
import requests
import time

# === КОД ДЛЯ САМО-ПІДТРИМКИ ===
app = Flask('')

@app.route('/')
def home():
    return "🤖 Бот Регістеренко працює!"

@app.route('/health')
def health():
    return "✅ OK"

@app.route('/ping')
def ping():
    return "pong"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    server = Thread(target=run_flask, daemon=True)
    server.start()
    print("🟢 Flask сервер запущено для само-підтримки")

def prevent_sleep():
    time.sleep(30)
    print("🟢 Anti-sleep запущено")
    while True:
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"✅ Бот працює: {current_time}")
        except Exception as e:
            print(f"⚠️ Помилка в anti-sleep: {e}")
        time.sleep(300)  # 5 хвилин

# === КІНЕЦЬ КОДУ САМО-ПІДТРИМКИ ===

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

print("🟢 Запуск бота...")

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
GOOGLE_SHEET_NAME = "Реєстрація на ІЧУ 2025"

if not TELEGRAM_TOKEN:
    print("❌ ПОМИЛКА: TELEGRAM_BOT_TOKEN не знайдено!")
    exit(1)

print(f"✅ Токен знайдено: {TELEGRAM_TOKEN[:10]}...")

try:
    google_credentials = os.environ.get('GOOGLE_CREDENTIALS')
    if google_credentials:
        print("🟢 Використовую credentials зі змінної середовища...")
        creds_dict = json.loads(google_credentials)
        gc = gspread.service_account_from_dict(creds_dict)
        sheet = gc.open(GOOGLE_SHEET_NAME).sheet1
        print("✅ Успішно підключено до Google Таблиці!")

    elif os.path.exists('credentials.json'):
        print("🟢 Використовую локальний credentials.json...")
        gc = gspread.service_account(filename='credentials.json')
        sheet = gc.open(GOOGLE_SHEET_NAME).sheet1
        print("✅ Успішно підключено до Google Таблиці!")

    else:
        print("❌ Не знайдено жодних credentials!")
        print("ℹ️  Додай GOOGLE_CREDENTIALS або credentials.json")
        sheet = None

except Exception as e:
    print(f"❌ Помилка підключення до Google Таблиці: {e}")
    sheet = None

NICKNAME, CLAN, CAN_CREATE = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = """
Вітаю! Я - бот Регістеренко 🙋‍♂️
Моя задача - допомогти вам швидко та зручно зареєструватися на Індивідуальний Чемпіонат України 🇺🇦

📝 Хочете зареєструватися? Натисніть сюди: /register

📈 Щоб переглянути інформацію щодо зареєстрованих гравців - тицніть сюди: /info

📋 Шукаєте інформацію про турнір та правила? Нажміть на цю команду: /tournament_info
    """
    await update.message.reply_text(welcome_text)

async def tournament_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info_text = """
📋 ІНФОРМАЦІЯ ПРО ТУРНІР

🗓 Дата початку буде визначена пізніше. Орієнтовно - початок або середина грудня.

🎯 Формат:
 ІЧУ - це індивідуальний турнір, у якому найсильніші гравці країни змагатимуться за звання Чемпіона України! Остаточний формат буде затверджено після завершення реєстрації та залежатиме від кількості учасників. Попередньо планується дві або три стадії, останньою з яких буде Фінал.
Окрім загальноукраїнської слави, найкращі менеджери отримають право представляти нашу спільноту на Індивідуальному Чемпіонаті Світу!

📜 Правила Індивідуального Чемпіонату України:

- Обирати можна будь-яку команду.

- Товариські матчі - дозволені.

- Миттєві продажі - дозволені.

- Купувати гравців в інших менеджерів - заборонено. Штраф: -3 очки.

- Купувати Легенд - заборонено. Штраф: -1 очко.

- Заборонені змова з іншими учасниками, образи чи провокації. Покарання визначається залежно від ступеня порушення та шляхом голосування у групі Вотсап.

- Заборонено покидати лігу до її завершення або не вступити до неї протягом 24 годин з моменту створення. У такому випадку участь у наступному розіграші буде заборонена.

- Можна відмовитися від участі у наступному раунді чемпіонату - без наслідків. У такому разі ваше місце займе наступний менеджер вашої ліги.

📎 Усі порушення мають бути підтверджені фото- або відеодоказами.  """
    await update.message.reply_text(info_text)

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not sheet:
        await update.message.reply_text("😔 Не вдалося підключитися до бази даних.")
        return

    try:
        all_records = sheet.get_all_records()
        total_players = len(all_records)

        clans = [record['Клан'] for record in all_records if record['Клан'].lower() != 'немає']
        unique_clans = len(set(clans))

        can_create_count = sum(1 for record in all_records if record['Може створити лігу'] == '✅ Так')

        stats_text = f"""
📊 СТАТИСТИКА РЕЄСТРАЦІЙ:

👥 Зареєстровано гравців: {total_players}
🏰 Унікальних кланів: {unique_clans}
🛡 Можуть створити лігу: {can_create_count}

📝 Ще не зареєстровані? Реєструйтесь самі і кличте друзів!
Щоб зареєструватися, натисніть сюди: /register
        """
        await update.message.reply_text(stats_text)

    except Exception as e:
        await update.message.reply_text("😔 Не вдалося отримати статистику.")

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not sheet:
        await update.message.reply_text("😔 Наразі реєстрація недоступна. Спробуй пізніше.")
        return ConversationHandler.END

    await update.message.reply_text("🎮 Чудово!\n\nДля початку, напишіть який у вас нік у ФОМі:")
    return NICKNAME

async def get_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['nickname'] = update.message.text

    keyboard = [["📝 Ввести клан", "⏩ Пропустити"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

    await update.message.reply_text(
        "👥 Якщо ви є гравцем одного з кланів - вкажіть якого, аби при жеребкуванні розвести вас та ваших сокланів по різним групам. \nЯкщо ви ще не знайшли собі клан - сміливо тисніть на 'Пропустити'",
        reply_markup=reply_markup)
    return CLAN

async def handle_clan_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text

    if choice == "📝 Ввести клан":
        await update.message.reply_text("👌 Добре! Введіть назву свого клану:")
        return CLAN
    else:
        context.user_data['clan'] = "немає"
        keyboard = [["✅ Так", "❌ Ні"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

        message_text = (
            "🛡 Чи могли б ви створити лігу?\n\n"
            "Створення ліги коштує до 300 монет, але дає свої переваги, а саме:\n"
            "• ви можете обрати зручний для себе час симуляції матчів\n"
            "• ви не потрапите в одну лігу з іншим створювачем")

        await update.message.reply_text(message_text, reply_markup=reply_markup)
        return CAN_CREATE

async def get_clan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['clan'] = update.message.text

    keyboard = [["✅ Так", "❌ Ні"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

    message_text = (
        "🛡 Чи могли б ви створити лігу?\n\n"
        "Створення ліги коштує до 300 монет, але дає свої переваги, а саме:\n"
        "• ви можете обрати зручний для себе час симуляції матчів\n"
        "• ви не потрапите в одну лігу з іншим створювачем")

    await update.message.reply_text(message_text, reply_markup=reply_markup)
    return CAN_CREATE

async def get_can_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not sheet:
        await update.message.reply_text("😔 Наразі реєстрація недоступна. Спробуй пізніше.")
        return ConversationHandler.END

    can_create = update.message.text

    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_id = update.effective_user.id
        nickname = context.user_data['nickname']
        clan = context.user_data['clan']

        new_row = [timestamp, user_id, nickname, clan, can_create]
        sheet.append_row(new_row)

        await update.message.reply_text(
            f"✅ Реєстрацію завершено!\n\n"
            f"🎮 Ваш нік: {nickname}\n"
            f"👥 Ваш клан: {clan}\n"
            f"🛡 Можливість створити лігу: {can_create}\n\n"
            f"Ваш шлях до чемпіонства щойно розпочався! 🎉\n\n"
            f"Що далі?\n"
            f"- Всі новини будуть публікуватися у групі Індивідуального Чемпіонату України - https://t.me/Individual_UA_Championship\n\n"
            f"- Поділитися своїми успіхами, порадіти успіхам інших або задати питання учасникам турніру можна у групі Вотсап: https://chat.whatsapp.com/EJyQsv5E8ZC42rwiQ1gv7t\n\n"
            f"Залишись питання? Задати їх можно тут:\n"
            f"Телеграм: @katyosm\n"
            f"Нік у ФОМ: sexmachine1997\n",
            reply_markup=None)
    except Exception as e:
        await update.message.reply_text("😔 Сталася помилка при реєстрації. Спробуй пізніше.")
        print(f"Помилка: {e}")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Реєстрацію скасовано.")
    return ConversationHandler.END

def main():
    keep_alive()
    
    sleep_thread = Thread(target=prevent_sleep, daemon=True)
    sleep_thread.start()
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('register', register)],
        states={
            NICKNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_nickname)],
            CLAN: [
                MessageHandler(filters.Regex('^(📝 Ввести клан|⏩ Пропустити)$'), handle_clan_choice),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_clan)
            ],
            CAN_CREATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_can_create)],
        },
        fallbacks=[CommandHandler('cancel', cancel)])

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("info", info))
    application.add_handler(CommandHandler("tournament_info", tournament_info))
    application.add_handler(conv_handler)

    print("🟢 Бот запускається...")
    
    # Автоматичний перезапуск при помилках
    max_retries = 5
    for i in range(max_retries):
        try:
            application.run_polling()
        except Exception as e:
            print(f"❌ Помилка запуску ({i+1}/{max_retries}): {e}")
            if i < max_retries - 1:
                print("♻️  Перезапуск через 30 секунд...")
                time.sleep(30)
            else:
                print("❌ Досягнуто максимальну кількість спроб")

if __name__ == '__main__':
    main()
