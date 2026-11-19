"""Учебный Telegram-бот для разбора заданий ЦДЗ.

Установка: pip install aiogram==3.*
Запуск: BOT_TOKEN=токен python cдз_bot.py

Бот принимает текст/фото задач и объясняет решение через OpenAI-совместимый
API (по умолчанию OpenAI). Без API-ключа отвечает заготовкой и просит задачу.
"""
import asyncio
import base64
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from openai import AsyncOpenAI

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("Задайте переменную окружения BOT_TOKEN")

API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
client = AsyncOpenAI(api_key=API_KEY) if API_KEY else None
bot = Bot(BOT_TOKEN)
dp = Dispatcher()
SYSTEM = (
    "Ты внимательный репетитор. Помогай решать школьные задания, присланные "
    "учеником. Объясняй ход решения по шагам, затем выдели итоговый ответ. "
    "Если условие неполное или изображение нечитаемо, задай уточняющий вопрос. "
    "Не выдумывай данные. Отвечай на русском языке."
)

@dp.message(CommandStart())
async def start(m: Message):
    await m.answer("Привет! Пришли текст задания ЦДЗ или фото — разберём решение по шагам.\n"
                   "Команда /help покажет подсказку.")

@dp.message(Command("help"))
async def help_cmd(m: Message):
    await m.answer("Отправь условие текстом или фотографию задания. Я объясню решение и ответ.\n"
                   "Для работы нужен OPENAI_API_KEY; токен Telegram задаётся через BOT_TOKEN.")

async def ask_ai(prompt, image_b64=None):
    if client is None:
        return "Для разбора подключите API: задайте переменную OPENAI_API_KEY и перезапустите бота."
    content = [{"type": "text", "text": prompt or "Реши и объясни задание с изображения."}]
    if image_b64:
        content.append({"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + image_b64}})
    result = await client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": content}],
        temperature=0.2,
    )
    return result.choices[0].message.content or "Не удалось получить ответ. Попробуй ещё раз."

@dp.message(F.photo)
async def photo(m: Message):
    status = await m.answer("Читаю условие и разбираю…")
    try:
        file = await bot.get_file(m.photo[-1].file_id)
        raw = await bot.download_file(file.file_path)
        encoded = base64.b64encode(raw.read()).decode("ascii")
        answer = await ask_ai(m.caption or "Реши задание с изображения.", encoded)
        await status.edit_text(answer[:4000])
    except Exception as e:
        await status.edit_text("Не получилось обработать фото. Проверь настройки API и попробуй ещё раз.")
        print("photo error:", repr(e))

@dp.message(F.text)
async def text(m: Message):
    if m.text.startswith("/"):
        return
    status = await m.answer("Разбираю задачу…")
    try:
        answer = await ask_ai(m.text)
        await status.edit_text(answer[:4000])
    except Exception as e:
        await status.edit_text("Ошибка при получении решения. Проверь API-ключ и попробуй снова.")
        print("text error:", repr(e))

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
