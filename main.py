import asyncio
import json
import logging
import os

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"), override=True)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

if not BOT_TOKEN:
    raise RuntimeError("Укажи BOT_TOKEN в .env или переменных окружения")


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

last_url_dict = {}


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Расписание")],
            [
                KeyboardButton(text="Оценки 4 триместр"),
                KeyboardButton(text="Оценки 5 триместр"),
                KeyboardButton(text="Оценки 6 триместр"),
            ],
            [
                KeyboardButton(text="План обучения"),
                KeyboardButton(text="Преподаватели"),
            ],
        ],
        resize_keyboard=True,
    )
    await message.answer(
        'Привет! Я бот-помощник для эл.дневника "Etis".\n'
        "Команды:\n"
        "/last - открыть последнюю сохранённую вкладку\n"
        "/help - помощь\n"
        "Выберите действие⬇\n\nby MonkyMagic",
        reply_markup=markup,
    )


BUTTONS = {
    "Расписание": (
        "Расписание:",
        "https://student.psu.ru/pls/stu_cus_et/stu.timetable",
    ),
    "Оценки 4 триместр": (
        "Оценки 4 триместр:",
        "https://student.psu.ru/pls/stu_cus_et/stu.signs?p_mode=current&p_term=4",
    ),
    "Оценки 5 триместр": (
        "Оценки 5 триместр:",
        "https://student.psu.ru/pls/stu_cus_et/stu.signs?p_mode=current&p_term=5",
    ),
    "Оценки 6 триместр": (
        "Оценки 6 триместр:",
        "https://student.psu.ru/pls/stu_cus_et/stu.signs?p_mode=current&p_term=6",
    ),
    "План обучения": (
        "План обучения:",
        "https://student.psu.ru/pls/stu_cus_et/stu.teach_plan",
    ),
    "Преподаватели": (
        "Преподаватели:",
        "https://student.psu.ru/pls/stu_cus_et/stu.teachers",
    ),
}


@dp.message(F.text.in_(BUTTONS.keys()))
async def handle_buttons(message: types.Message):
    text, url = BUTTONS[message.text]
    add_stat(message.from_user.id, message.text)
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Открыть", web_app=WebAppInfo(url=url))]
        ]
    )
    await message.answer(text, reply_markup=markup)
    last_url_dict[message.from_user.id] = url
    save_last_url()


stats = {"users": set(), "commands": {}}


def add_stat(user_id, command):
    stats["users"].add(user_id)
    stats["commands"][command] = stats["commands"].get(command, 0) + 1
    save_stats()


ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))


@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔️ Доступ запрещён.")
        return
    add_stat(message.from_user.id, "/stats")
    users_count = len(stats["users"])
    commands_info = "\n".join(f"{cmd}: {cnt}" for cmd, cnt in stats["commands"].items())
    await message.answer(
        f"Статистика:\n"
        f"Пользователей: {users_count}\n"
        f"Команды:\n{commands_info if commands_info else 'Нет данных'}"
    )


@dp.message(Command("clearstats"))
async def cmd_clearstats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔️ Доступ запрещён.")
        return
    stats["users"].clear()
    stats["commands"].clear()
    await message.answer("Статистика очищена.")
    save_stats()


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    add_stat(message.from_user.id, "/help")
    await message.answer("Команды:\n" "/last - открыть последнюю сохранённую вкладку\n")


STATS_FILE = "stats.json"


def save_stats():
    stats_to_save = {"users": list(stats["users"]), "commands": stats["commands"]}
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats_to_save, f)


def load_stats():
    global stats
    try:
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)
            stats["users"] = set(loaded.get("users", []))
            stats["commands"] = loaded.get("commands", {})
    except Exception:  # noqa: BLE001
        stats = {"users": set(), "commands": {}}


@dp.message(Command("last"))
async def cmd_last(message: types.Message):
    add_stat(message.from_user.id, "/last")
    url = last_url_dict.get(message.from_user.id)
    if not url:
        await message.reply("Последняя сохранённая вкладка не найдена.")
        return
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Открыть последнюю", web_app=WebAppInfo(url=url)
                )
            ]
        ]
    )
    await message.answer("Последняя вкладка:", reply_markup=kb)


@dp.message()
async def unknown(message: types.Message):
    await message.answer(
        "Я не понимаю эту команду. Пожалуйста, выберите команду из меню или используйте /help"
    )


LAST_URL_FILE = "last_url.json"


def save_last_url():
    with open(LAST_URL_FILE, "w", encoding="utf-8") as f:
        json.dump(last_url_dict, f)


def load_last_url():
    global last_url_dict

    try:
        with open(LAST_URL_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        last_url_dict = {int(user_id): url for user_id, url in loaded.items()}
    except FileNotFoundError:
        last_url_dict = {}
    except (OSError, ValueError, AttributeError):
        logger.exception("Не удалось загрузить последние разделы")
        last_url_dict = {}


async def main():
    load_stats()
    load_last_url()
    logger.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:  # noqa: BLE001
        logger.error(f"An error occurred: {e}")
