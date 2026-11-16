import asyncio
import logging
import re
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    MessageEntity
)

BOT_TOKEN = "ТВОЙ_ТОКЕН_ЗДЕСЬ"   # замени
CHANNEL_ID = -1004438414275

logging.basicConfig(level=logging.INFO)

class Form(StatesGroup):
    nft_link = State()       # ссылка на NFT
    nft_name = State()       # название
    model = State()
    background = State()
    symbol = State()
    price = State()
    owner = State()          # ник + @username
    currency = State()       # инлайн-кнопки

router = Router()

CURRENCIES = {
    "gram":  "GRAM",
    "stars": "Stars",
    "rub":   "RUB",
    "usd":   "USD",
}

# ---------- СТАРТ (доступно всем) ----------
@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🎁 Создание объявления о продаже NFT.\n\n"
        "Шаг 1/8: Отправь **ссылку на NFT** (https://t.me/...):"
    )
    await state.set_state(Form.nft_link)

# ---------- ССЫЛКА ----------
@router.message(Form.nft_link)
async def process_link(message: Message, state: FSMContext):
    url = message.text.strip()
    if not re.match(r"^https?://", url):
        await message.answer("Нужна ссылка, начинающаяся с http:// или https://")
        return
    await state.update_data(nft_link=url)
    await message.answer("Шаг 2/8: Введи **название NFT**:")
    await state.set_state(Form.nft_name)

# ---------- НАЗВАНИЕ ----------
@router.message(Form.nft_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(nft_name=message.text.strip())
    await message.answer("Шаг 3/8: Введи **модель** (например, Silver):")
    await state.set_state(Form.model)

# ---------- МОДЕЛЬ ----------
@router.message(Form.model)
async def process_model(message: Message, state: FSMContext):
    await state.update_data(model=message.text.strip())
    await message.answer("Шаг 4/8: Введи **фон** (например, Shamrock Green):")
    await state.set_state(Form.background)

# ---------- ФОН ----------
@router.message(Form.background)
async def process_bg(message: Message, state: FSMContext):
    await state.update_data(background=message.text.strip())
    await message.answer("Шаг 5/8: Введи **символ** (например, Paw):")
    await state.set_state(Form.symbol)

# ---------- СИМВОЛ ----------
@router.message(Form.symbol)
async def process_symbol(message: Message, state: FSMContext):
    await state.update_data(symbol=message.text.strip())
    await message.answer("Шаг 6/8: Введи **цену** (число, например 19.99):")
    await state.set_state(Form.price)

# ---------- ЦЕНА ----------
@router.message(Form.price)
async def process_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Введи число, например 19.99")
        return
    await state.update_data(price=price)
    await message.answer("Шаг 7/8: Отправь **владельца** (ник + @username), например:\n`Иван @ivan`")
    await state.set_state(Form.owner)

# ---------- ВЛАДЕЛЕЦ ----------
@router.message(Form.owner)
async def process_owner(message: Message, state: FSMContext):
    await state.update_data(owner=message.text.strip())
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="GRAM", callback_data="cur:gram"),
         InlineKeyboardButton(text="Stars", callback_data="cur:stars")],
        [InlineKeyboardButton(text="RUB", callback_data="cur:rub"),
         InlineKeyboardButton(text="USD", callback_data="cur:usd")],
    ])
    await message.answer("Шаг 8/8: Выбери **валюту**:", reply_markup=kb)
    await state.set_state(Form.currency)

# ---------- ВАЛЮТА (кнопки) ----------
@router.callback_query(F.data.startswith("cur:"))
async def process_currency(call: CallbackQuery, state: FSMContext):
    code = call.data.split(":")[1]
    await state.update_data(currency=code)
    data = await state.get_data()

    # предпросмотр
    preview = (
        f"📋 Проверь объявление:\n\n"
        f"🎁 {data['nft_name']} ({data['nft_link']})\n"
        f"Модель: {data['model']}\n"
        f"Фон: {data['background']}\n"
        f"Символ: {data['symbol']}\n\n"
        f"💵 Цена: {data['price']}\n"
        f"👤 Владелец: {data['owner']}\n"
        f"💰 Валюта: {CURRENCIES[code]}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить и опубликовать", callback_data="publish")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])
    await call.message.edit_text(preview, reply_markup=kb)
    await call.answer()

# ---------- ПУБЛИКАЦИЯ ----------
@router.callback_query(F.data == "publish")
async def publish(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()

    # текст с гиперссылкой на NFT в названии
    text = (
        f"🎁 <a href=\"{data['nft_link']}\">{data['nft_name']}</a>\n"
        f"Модель: {data['model']}\n"
        f"Фон: {data['background']}\n"
        f"Символ: {data['symbol']}\n\n"
        f"💵 Цена: {data['price']}\n"
        f"👤 Владелец: {data['owner']}\n"
        f"💰 Валюта: {CURRENCIES[data['currency']]}"
    )

    try:
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=False
        )
        await call.message.edit_text("✅ Объявление опубликовано в канале!")
    except Exception as e:
        await call.message.edit_text(f"❌ Ошибка публикации: {e}")
    await state.clear()
    await call.answer()

@router.callback_query(F.data == "cancel")
async def cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("❌ Отменено. Начать заново: /start")
    await call.answer()

# ---------- ЗАПУСК ----------
async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())