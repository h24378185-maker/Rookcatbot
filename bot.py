import asyncio
import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery
import firebase_admin
from firebase_admin import credentials, db

# --- НАСТРОЙКИ ---
BOT_TOKEN = "9037921441:AAFzsKK34ZKQXLzpU51gL3l1M1HLittH1OA"
DATABASE_URL = "https://rukchat-75cca-default-rtdb.firebaseio.com"

FIREBASE_CRED_PATH = "/etc/secrets/firebase_key.json" 

PRICE_STARS = 100
COINS_AMOUNT = 50

# Инициализация Firebase
if os.path.exists(FIREBASE_CRED_PATH):
    cred = credentials.Certificate(FIREBASE_CRED_PATH)
else:
    cred = credentials.Certificate("firebase_key.json")

firebase_admin.initialize_app(cred, {'databaseURL': DATABASE_URL})

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Оплатить {PRICE_STARS} ⭐", callback_data="pay_stars")]
    ])
    await message.answer(
        f"👋 Привет! Здесь ты можешь пополнить баланс в Rukchat.\n\n"
        f"Курс: {PRICE_STARS} Stars = {COINS_AMOUNT} RukCoins.",
        reply_markup=kb
    )

@dp.callback_query(lambda c: c.data == "pay_stars")
async def process_pay(callback: types.CallbackQuery):
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="Пополнение RukCoins",
        description=f"Покупка {COINS_AMOUNT} RukCoins",
        payload=f"coins_{COINS_AMOUNT}_{callback.from_user.username}",
        provider_token="", 
        currency="XTR", 
        prices=[LabeledPrice(label="RukCoins", amount=PRICE_STARS)],
    )
    await callback.answer()

@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_q: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)

@dp.message(lambda message: message.successful_payment)
async def successful_payment(message: types.Message):
    username = message.from_user.username
    if not username:
        await message.answer("Ошибка: У тебя не установлен @username в Telegram. Начисление невозможно.")
        return

    user_key = f"@{username.lower()}"
    
    try:
        user_ref = db.reference(f'accounts/{user_key}')
        user_data = user_ref.get()

        if not user_data:
            await message.answer(f"❌ Пользователь {user_key} не найден в Rukchat. Зарегистрируйся в мессенджере с таким же ником!")
            return

        current_coins = user_data.get('coins', 0)
        user_ref.update({'coins': current_coins + COINS_AMOUNT})

        await message.answer(f"✅ Успешно! Тебе начислено {COINS_AMOUNT} RukCoins. Твой новый баланс: {current_coins + COINS_AMOUNT}")
    except Exception as e:
        logging.error(f"Ошибка Firebase: {e}")
        await message.answer("❌ Ошибка базы данных. Напиши в поддержку.")

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
