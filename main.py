import os
import random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiohttp import web
import aiohttp
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



from database import init_db, set_user_level, get_user_level
from dotenv import load_dotenv
load_dotenv()



API_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST")
WEBHOOK_PATH = f"/bot/{API_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

print("🔑 API_TOKEN =", API_TOKEN)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

def level_keyboard():
    kb = [[InlineKeyboardButton(text=level, callback_data=level)] for level in ["A1", "A2", "B1", "B2", "C1", "C2"]]
    return InlineKeyboardMarkup(inline_keyboard=kb)

async def check_openrouter_connection():
    url = "https://openrouter.ai/api/v1/models"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    logger.info("Checking connection to OpenRouter...")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()
                logger.info(f"OpenRouter connection OK. Models available: {list(model['id'] for model in data.get('data', []))}")
    except Exception as e:
        logger.error(f"Failed to connect to OpenRouter: {e}")


async def ask_openrouter(prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://englishbot-production.up.railway.app",
    }
    json_data = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt}],
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=json_data) as resp:
            data = await resp.json()
            print("OpenRouter response:", data)
            return data.get("choices", [{}])[0].get("message", {}).get("content", "No response")

async def send_random_message():
    users = await get_all_users()
    for user_id, level in users:
        prompt = f"Write a friendly greeting and ask the user a simple question about their daily routine in English, according to CEFR level {level}."
        text = await ask_openrouter(prompt)
        await bot.send_message(user_id, text)

async def get_all_users():
    import aiosqlite
    DB_NAME = "englishbot.db"
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id, level FROM users") as cursor:
            return await cursor.fetchall()

def schedule_daily_message():
    scheduler.remove_all_jobs()
    for hour in range(10, 21):
        random_minute = random.randint(0, 59)
        scheduler.add_job(send_random_message, 'cron', hour=hour, minute=random_minute)

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    print("Received /start command")
    await message.answer("Welcome! Please choose your English level:", reply_markup=level_keyboard())

@dp.message(Command("change"))
async def change_cmd(message: types.Message):
    await message.answer("Please choose your new English level:", reply_markup=level_keyboard())

@dp.callback_query()
async def level_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    level = callback.data
    if level in ["A1", "A2", "B1", "B2", "C1", "C2"]:
        await set_user_level(user_id, level)
        await callback.message.answer(f"Your level is set to {level}.")
        prompt = f"Write a friendly greeting and ask the user a simple question about their daily routine in English, according to CEFR level {level}."
        text = await ask_openrouter(prompt)
        await callback.message.answer(text)
        await callback.answer()

@dp.message()
async def handle_message(message: types.Message):
    text = message.text.strip()
    if not all(ord(c) < 128 for c in text):
        await message.answer("Sorry, I can only understand English. Please write in English.")
        return
    prompt = f"Answer the user's message in English: {text}"
    reply = await ask_openrouter(prompt)
    await message.answer(reply)

async def handle(request):
    data = await request.json()
    print("Received webhook:", data)
    update = types.Update(**data)
    await dp.feed_update(bot, update)
    return web.Response()



async def on_startup(app):
    await init_db()
    await check_openrouter_connection()
    scheduler.start()
    schedule_daily_message()
    await bot.set_webhook(WEBHOOK_URL)
    print(f"✅ Webhook set: {WEBHOOK_URL}")

async def on_shutdown(app):
    await bot.delete_webhook()
    await bot.session.close()
    print("🛑 Webhook deleted and bot session closed")

app = web.Application()
app.router.add_post(WEBHOOK_PATH, handle)
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    web.run_app(app, host="0.0.0.0", port=port)
