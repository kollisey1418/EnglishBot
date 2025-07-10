import asyncio
import random
from datetime import datetime, time

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import aiohttp
from aiogram import F

from database import init_db, set_user_level, get_user_level

API_TOKEN = "7782841483:AAE5ZnPFN_ZA30i8vDoufUyGQpL4ihg7usA"
OPENROUTER_API_KEY = "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"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

# Клавиатура выбора уровня
def level_keyboard():
    kb = [
        [InlineKeyboardButton(text=level, callback_data=level)]
        for level in ["A1", "A2", "B1", "B2", "C1", "C2"]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# Запрос к OpenRouter
async def ask_openrouter(prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://yourapp.com",
    }
    json_data = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt}],
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=json_data) as resp:
            data = await resp.json()
            return data["choices"][0]["message"]["content"]

# Отправка рандомного сообщения
async def send_random_message():
    users = await get_all_users()
    for user_id, level in users:
        prompt = f"Write a friendly greeting and ask the user a simple question about their daily routine in English, according to CEFR level {level}."
        text = await ask_openrouter(prompt)
        await bot.send_message(user_id, text)

# Получение всех пользователей из базы
async def get_all_users():
    import aiosqlite
    DB_NAME = "englishbot.db"
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id, level FROM users") as cursor:
            return await cursor.fetchall()

# Планирование сообщений
def schedule_daily_message():
    scheduler.remove_all_jobs()
    for hour in range(10, 21):
        random_minute = random.randint(0, 59)
        scheduler.add_job(send_random_message, 'cron', hour=hour, minute=random_minute)

# /start
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("Welcome! Please choose your English level:", reply_markup=level_keyboard())

# /change
@dp.message(Command("change"))
async def change_cmd(message: types.Message):
    await message.answer("Please choose your new English level:", reply_markup=level_keyboard())

@dp.callback_query(F.data.in_(["A1", "A2", "B1", "B2", "C1", "C2"]))
async def level_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    level = callback.data
    await set_user_level(user_id, level)
    await callback.message.answer(f"Your level is set to {level}.")
    await callback.answer()

# Обработка сообщений
@dp.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    text = message.text.strip()

    if text in ["A1", "A2", "B1", "B2", "C1", "C2"]:
        await set_user_level(user_id, text)
        await message.answer(f"Your level is set to {text}.")
        return

    if not all(ord(c) < 128 for c in text):
        await message.answer("Sorry, I can only understand English. Please write in English.")
        return

    prompt = f"Answer the user's message in English: {text}"
    reply = await ask_openrouter(prompt)
    await message.answer(reply)

async def main():
    await init_db()
    scheduler.start()
    schedule_daily_message()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
