
import os
import logging

from telegram import Update, MessageEntity
from telegram.ext import (
    Application,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.error import TelegramError

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

# Railway Variables
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
TARGET_CHANNEL_ID = os.getenv("TARGET_CHANNEL_ID", "").strip()

# Сілтеме мәтіні
LINK_TEXT = "𝗪𝗵𝗶𝘁𝗹𝗲𝘀𝘀 | 𝗢𝗦𝗜𝗡𝗧"

# Сілтеме апаратын канал
LINK_URL = os.getenv(
    "LINK_URL",
    "https://t.me/+NdeRmhn-9s40Nzc0",
).strip()


def utf16_length(text: str) -> int:
    """Telegram мәтініндегі entity offset-ын есептеу."""
    return len(text.encode("utf-16-le")) // 2


async def process_post(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    message = update.channel_post or update.edited_channel_post

    if message is None:
        return

    logger.info(
        "Жаңа пост: channel_id=%s, message_id=%s",
        message.chat.id,
        message.message_id,
    )

    # Тек таңдалған каналды өңдеу
    if not TARGET_CHANNEL_ID:
        logger.warning("TARGET_CHANNEL_ID орнатылмаған.")
        return

    if str(message.chat.id) != TARGET_CHANNEL_ID:
        return

    is_text = message.text is not None

    if is_text:
        original = message.text or ""
        entities = list(message.entities or [])
    else:
        original = message.caption or ""
        entities = list(message.caption_entities or [])

    # Қайтадан сілтеме қоспау
    if LINK_TEXT in original:
        return

    # Мәтіні де, caption-ы да жоқ посттарды өткізу
    if not original and not (
        message.photo
        or message.video
        or message.document
        or message.animation
        or message.audio
        or message.voice
    ):
        return

    separator = "\n\n" if original else ""
    new_content = original + separator + LINK_TEXT

    # Telegram лимиттері
    limit = 4096 if is_text else 1024

    if len(new_content) > limit:
        logger.warning("Пост ұзын болғандықтан өңделмеді.")
        return

    link_entity = MessageEntity(
        type=MessageEntity.TEXT_LINK,
        offset=utf16_length(original + separator),
        length=utf16_length(LINK_TEXT),
        url=LINK_URL,
    )

    new_entities = entities + [link_entity]

    try:
        if is_text:
            await context.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=message.message_id,
                text=new_content,
                entities=new_entities,
            )
        else:
            await context.bot.edit_message_caption(
                chat_id=message.chat.id,
                message_id=message.message_id,
                caption=new_content,
                caption_entities=new_entities,
            )

        logger.info("Сілтеме сәтті қосылды.")

    except TelegramError:
        logger.exception(
            "Постты өңдеу қатесі: %s",
            message.message_id,
        )


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN енгізілмеген.")

    if not LINK_URL.startswith(("https://", "http://")):
        raise RuntimeError("LINK_URL қате.")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(
        MessageHandler(
            filters.UpdateType.CHANNEL_POST
            | filters.UpdateType.EDITED_CHANNEL_POST,
            process_post,
        )
    )

    logger.info("Бот іске қосылды.")

    app.run_polling(
        allowed_updates=[
            "channel_post",
            "edited_channel_post",
        ]
    )


if __name__ == "__main__":
    main()
