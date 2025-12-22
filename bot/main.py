from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
import asyncio
from aiogram.types import BotCommand

from bot.handlers import router
from bot.admin.handlers import router as admin_router
from bot.config import BOT_TOKEN
from .middleware import RegistrationMiddleware


async def main():
    print("🤖 Telegram BOT is running...")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )

    dp = Dispatcher()

    dp.message.middleware(RegistrationMiddleware())
    dp.callback_query.middleware(RegistrationMiddleware())

    dp.include_router(router)
    dp.include_router(admin_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())