"""
Telegram Bot v2.0 Pro - PvP End Timer
Features:
- Inline Buttons Interface
- Countdown Timer
- Admin Broadcasting
- Robust Error Handling
"""

import logging
import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Set

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    Defaults,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest, Forbidden

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8257436015:AAG3Wq1jkNXDxRtAhuecKaxR4MEWc7tmBfE"
ADMIN_ID = 6806144883  # Replace with YOUR Telegram ID for admin features
TIMEZONE = ZoneInfo("Europe/Moscow")

PVP_START_HOURS = [1, 4, 7, 10, 13, 16, 19, 22]

# ==================== LOGGING ====================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("PvPBot")

# ==================== DATA STORE ====================
class SubscriberStore:
    def __init__(self, filename="subscribers.txt"):
        self.filename = filename
        self.chat_ids: Set[int] = set()
        self.load()

    def load(self):
        try:
            with open(self.filename, "r") as f:
                for line in f:
                    if line.strip():
                        self.chat_ids.add(int(line.strip()))
            logger.info(f"Loaded {len(self.chat_ids)} subscribers.")
        except FileNotFoundError:
            logger.info("No subscribers file found. Creating new.")

    def save(self):
        try:
            with open(self.filename, "w") as f:
                for chat_id in self.chat_ids:
                    f.write(f"{chat_id}\n")
        except Exception as e:
            logger.error(f"Failed to save subscribers: {e}")

    def add(self, chat_id: int):
        if chat_id not in self.chat_ids:
            self.chat_ids.add(chat_id)
            self.save()
            return True
        return False

    def remove(self, chat_id: int):
        if chat_id in self.chat_ids:
            self.chat_ids.remove(chat_id)
            self.save()
            return True
        return False

    def __iter__(self):
        return iter(self.chat_ids)

store = SubscriberStore()

# ==================== KEYBOARDS ====================
def get_main_keyboard(is_subscribed: bool):
    sub_text = "🔕 Отписаться" if is_subscribed else "🔔 Подписаться"
    sub_callback = "sub_off" if is_subscribed else "sub_on"
    
    keyboard = [
        [
            InlineKeyboardButton("📊 Статус", callback_data="status"),
            InlineKeyboardButton("📅 Расписание", callback_data="schedule"),
        ],
        [InlineKeyboardButton(sub_text, callback_data=sub_callback)],
        [InlineKeyboardButton("🔄 Обновить", callback_data="refresh_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== LOGIC HELPERS ====================
def get_pvp_status():
    now = datetime.now(TIMEZONE)
    current_hour = now.hour
    
    # Check if active
    current_session_start = None
    for h in PVP_START_HOURS:
        # Handle wrap around for 22:00-00:00?
        # Schedule: 22-00 is 2 hours.
        if h <= current_hour < (h + 2) or (h == 22 and current_hour >= 22):
            current_session_start = h
            break

    if current_session_start is not None:
        # ACTIVE
        end_time_hour = (current_session_start + 2) % 24
        
        # Calculate end datetime
        end_dt = now.replace(minute=0, second=0, microsecond=0)
        if end_time_hour == 0:
             end_dt += timedelta(days=1)
        end_dt = end_dt.replace(hour=end_time_hour)
        
        remaining = end_dt - now
        # Format MM:SS
        total_seconds = int(remaining.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        end_str = f"{end_time_hour:02d}:00"
        
        return (
            f"⚔️ **PvP СЕЙЧАС АКТИВЕН!** ⚔️\n\n"
            f"🕐 Идет период: `{current_session_start:02d}:00 — {end_str}`\n"
            f"⏳ До конца: `{hours:02d}:{minutes:02d}:{seconds:02d}`\n\n"
            f"💀 Удачной охоты!"
        )
    else:
        # NOT ACTIVE - Find next
        next_start = None
        for h in sorted(PVP_START_HOURS):
            if h > current_hour:
                next_start = h
                break
        
        day_offset = 0
        if next_start is None:
            next_start = PVP_START_HOURS[0]
            day_offset = 1
            
        start_dt = now.replace(hour=next_start, minute=0, second=0, microsecond=0) + timedelta(days=day_offset)
        remaining = start_dt - now
        
        total_seconds = int(remaining.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        return (
            f"🛡️ **PvP сейчас закрыт**\n\n"
            f"🔜 Следующий: `{next_start:02d}:00`\n"
            f"⏳ Начало через: `{hours:02d}:{minutes:02d}:{seconds:02d}`"
        )

# ==================== HANDLERS ====================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    is_sub = chat_id in store.chat_ids
    
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        f"Я бот-таймер для PvP в End.\n"
        f"Я сообщу, когда начнется резня. 🩸\n\n"
        f"👇 Используй меню ниже:",
        reply_markup=get_main_keyboard(is_sub)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = update.effective_chat.id
    await query.answer()

    data = query.data
    
    if data == "status" or data == "refresh_menu":
        # Check current sub status for keyboard
        is_sub = chat_id in store.chat_ids
        
        text = get_pvp_status()
        if data == "refresh_menu":
            text = f"🔄 Данные обновлены:\n\n{text}"
            
        try:
            await query.edit_message_text(
                text=text,
                reply_markup=get_main_keyboard(is_sub),
                parse_mode=ParseMode.MARKDOWN
            )
        except BadRequest:
            pass # Message not changed

    elif data == "schedule":
        is_sub = chat_id in store.chat_ids
        schedule_text = "📅 **Расписание PvP (МСК):**\n\n"
        for h in PVP_START_HOURS:
            end = (h + 2) % 24
            schedule_text += f"• `{h:02d}:00` — `{end:02d}:00`\n"
            
        await query.edit_message_text(
            text=schedule_text,
            reply_markup=get_main_keyboard(is_sub),
            parse_mode=ParseMode.MARKDOWN
        )

    elif data == "sub_on":
        store.add(chat_id)
        await query.edit_message_reply_markup(reply_markup=get_main_keyboard(True))
        await context.bot.send_message(chat_id, "✅ Вы подписались на уведомления!")

    elif data == "sub_off":
        store.remove(chat_id)
        await query.edit_message_reply_markup(reply_markup=get_main_keyboard(False))
        await context.bot.send_message(chat_id, "❌ Подписка отключена.")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return

    msg = " ".join(context.args)
    if not msg:
        await update.message.reply_text("⚠ Использование: `/broadcast Сообщение`")
        return

    count = 0
    await update.message.reply_text(f"📤 Рассылка началась для {len(store.chat_ids)} юзеров...")
    
    for chat_id in list(store.chat_ids):
        try:
            await context.bot.send_message(chat_id, f"📢 **ОБЪЯВЛЕНИЕ:**\n\n{msg}", parse_mode=ParseMode.MARKDOWN)
            count += 1
            await asyncio.sleep(0.05) # Rate limit protection
        except Forbidden:
            store.remove(chat_id)
        except Exception as e:
            logger.error(f"Failed to send to {chat_id}: {e}")
    
    await update.message.reply_text(f"✅ Рассылка завершена. Доставлено: {count}")

# ==================== JOBS ====================
async def scheduled_pvp_alert(context: ContextTypes.DEFAULT_TYPE):
    hour = context.job.data
    end_hour = (hour + 2) % 24
    end_str = f"{end_hour:02d}:00"
    
    message = (
        f"⚔️ **ЭНД ОТКРЫТ!** ⚔️\n\n"
        f"🕐 Время PvP: `{hour:02d}:00` — `{end_str}`\n"
        f"💀 Удачной охоты!"
    )
    
    logger.info(f"Starting scheduled broadcast for {hour}:00")
    
    # Broadcast to all subs
    to_remove = []
    for chat_id in store.chat_ids:
        try:
            await context.bot.send_message(chat_id, message, parse_mode=ParseMode.MARKDOWN)
        except Forbidden:
            to_remove.append(chat_id)
        except Exception as e:
            logger.error(f"Error sending to {chat_id}: {e}")
            
    # Cleanup dead subs
    for chat_id in to_remove:
        store.remove(chat_id)

def main():
    defaults = Defaults(parse_mode=ParseMode.MARKDOWN, tzinfo=TIMEZONE)
    application = Application.builder().token(BOT_TOKEN).defaults(defaults).build()

    # Commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    
    # Callbacks
    application.add_handler(CallbackQueryHandler(button_handler))

    # Job Queue
    job_queue = application.job_queue
    for hour in PVP_START_HOURS:
        from datetime import time as dt_time
        # Schedule message exactly at XX:00
        run_time = dt_time(hour=hour, minute=0, tzinfo=TIMEZONE)
        job_queue.run_daily(scheduled_pvp_alert, time=run_time, data=hour)
        logger.info(f"Scheduled alert for {hour:02d}:00")

    print("Bot v2.0 Pro started! Press Ctrl+C to stop.")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
