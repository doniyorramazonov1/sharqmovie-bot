import asyncio
import threading
from flask import Flask
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN, PORT
import database as db
from handlers import router

app = Flask(__name__)

@app.route("/")
def health():
    return "OK"

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

async def main():
    db.init_db()
    dp = Dispatcher()
    dp.include_router(router)
    bot = Bot(token=BOT_TOKEN)
    print("Sharq Movie Bot ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(main())
