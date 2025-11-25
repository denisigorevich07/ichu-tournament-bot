import os
import gspread
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters
from datetime import datetime
import logging
import json

# Увімкнути логування
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# === НАЛАШТУВАННЯ ===
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')  # ТОКЕН ТІЛЬКИ З РЕНДЕР
GOOGLE_SHEET_NAME = "Реєстрація на ІЧУ 2025"

if not TELEGRAM_TOKEN:
    print("❌ ПОМИЛКА: TELEGRAM_TOKEN не знайдено!")
    print("ℹ️  Переконайся, що додав TELEGRAM_TOKEN у Environment Variables на Render")
    exit(1)

# Стани для реєстрації
NICKNAME, CLAN, CAN_CREATE = range(3)

# === ПІДКЛЮЧЕННЯ ДО GOOGLE ТАБЛИЦІ ===
try:
    # Спосіб 1: Змінна середовища (для Render)
    google_credentials = os.environ.get('GOOGLE_CREDENTIALS')
    if google_credentials:
        print("🟢 Використовую credentials зі змінної середовища...")
        creds_dict = json.loads(google_credentials)
        gc = gspread.service_account_from_dict(creds_dict)
        sheet = gc.open(GOOGLE_SHEET_NAME).sheet1
        print("✅ Успішно підключено до Google Таблиці!")
    
    # Спосіб 2: Локальний файл (для тестування)
    elif os.path.exists('credentials.json'):
        print("🟢 Використовую локальний credentials.json...")
        gc = gspread.service_account(filename='credentials.json')
        sheet = gc.open(GOOGLE_SHEET_NAME).sheet1
        print("✅ Успішно підключено до Google Таблиці!")
    
    else:
        print("❌ Не знайдено жодних credentials!")
        sheet = None
        
except Exception as e:
    print(f"❌ Помилка підключення до Google Таблиці: {e}")
    sheet = None

# === КОМАНДИ БОТА ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = """
🎮 Вітаю в боті реєстрації на турнір ІЧУ 2025!

Доступні команди:
/register - Зареєструватися на турнір
/info - Статистика реєстрацій
/tournament_info - Інформація про турнір
    """
    await update.message.reply_text(welcome_text)

async def tournament_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info_text = """
📋 ІНФОРМАЦІЯ ПРО ТУРНІР ІЧУ 2025:

🗓 Дата: 15 Грудня 2024
⏰ Час: 18:00
🎯 Формат: 1v1
🏆 Призовий фонд: 1000 грн

📜 Правила:
• Турнір проводиться в форматі double elimination
• Максимальна кількість учасників: 32
• Реєстрація безкоштовна

❓ Питання: @username_організатора
    """
    await update.message.reply_text(info_text)

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not sheet:
        await update.message.reply_text("😔 Не вдалося підключитися до бази даних.")
        return
        
    try:
        all_records = sheet.get_all_records()
        total_players = len(all_records)
        
        # Унікальні клани
        clans = [record['Клан'] for record in all_records if record['Клан'].lower() != 'немає']
        unique_clans = len(set(clans))
        
        # Гравці, які можуть створити лігу
        can_create_count = sum(1 for record in all_records if record['Може створити лігу'] == '✅ Так')
        
        stats_text = f"""
📊 СТАТИСТИКА РЕЄСТРАЦІЙ:

👥 Зареєстровано гравців: {total_players}
🏰 Унікальних кланів: {unique_clans}
🛡 Можуть створити лігу: {can_create_count}

🎯 Залишилось місць: {32 - total_players}
        """
        await update.message.reply_text(stats_text)
        
    except Exception as e:
        await update.message.reply_text("😔 Не вдалося отримати статистику.")

# === РЕЄСТРАЦІЯ ===
async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not sheet:
        await update.message.reply_text("😔 Наразі реєстрація недоступна. Спробуй пізніше.")
        return ConversationHandler.END
        
    await update.message.reply_text("🎮 Початок реєстрації на турнір!\n\nБудь ласка, введи свій ігровий НІК:")
    return NICKNAME

async def get_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['nickname'] = update.message.text
    
    keyboard = [["📝 Ввести клан", "⏩ Пропустити"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    
    await update.message.reply_text(
        "👥 Бажаєш ввести назву свого клану?\nЯкщо немає клану - обирай 'Пропустити'",
        reply_markup=reply_markup
    )
    return CLAN

async def handle_clan_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    
    if choice == "📝 Ввести клан":
        await update.message.reply_text("👌 Добре! Введи назву свого клану:")
        return CLAN
    else:
        context.user_data['clan'] = "немає"
        keyboard = [["✅ Так", "❌ Ні"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await update.message.reply_text("🛡 Чи можеш ти створити лігу для гри?", reply_markup=reply_markup)
        return CAN_CREATE

async def get_clan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['clan'] = update.message.text
    keyboard = [["✅ Так", "❌ Ні"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text("🛡 Чи можеш ти створити лігу для гри?", reply_markup=reply_markup)
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
        
        # Додаємо новий рядок
        new_row = [timestamp, user_id, nickname, clan, can_create]
        sheet.append_row(new_row)
        
        await update.message.reply_text(
            f"✅ Реєстрація успішна!\n\n"
            f"🎮 Нік: {nickname}\n"
            f"👥 Клан: {clan}\n"
            f"🛡 Можливість створити лігу: {can_create}\n\n"
            f"Дякуємо за реєстрацію! 🎉",
            reply_markup=None
        )
    except Exception as e:
        await update.message.reply_text("😔 Сталася помилка при реєстрації. Спробуй пізніше.")
        print(f"Помилка: {e}")
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Скасування реєстрації"""
    await update.message.reply_text("❌ Реєстрацію скасовано.")
    return ConversationHandler.END

# === ОСНОВНА ФУНКЦІЯ ===
def main():
    """Запуск бота"""
    # Створюємо додаток
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Обробник реєстрації
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
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    # Додаємо обробники команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("info", info))
    application.add_handler(CommandHandler("tournament_info", tournament_info))
    application.add_handler(conv_handler)
    
    # Запускаємо бота
    print("🟢 Бот запускається...")
    application.run_polling()

if __name__ == '__main__':
    main()
