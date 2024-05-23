import datetime
import time
import asyncio
import logging
import os
import json
import re
from telethon import TelegramClient, errors, types

# Налаштування Telegram API
api_id = id
api_hash = 'hash'

# Налаштування логування
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Завантаження конфігурації каналів
with open('channels.json', 'r', encoding='utf-8') as file:
    config = json.load(file)
    namechannel = config['namechannel']
    source_channels = list(namechannel.keys())
    target_channel = config['target_channel']

# Функція для завантаження останніх ID повідомлень з файлу
def load_last_message_ids():
    if os.path.exists('last_message_ids.json'):
        with open('last_message_ids.json', 'r', encoding='utf-8') as file:
            return {
                key: int(value) if value is not None else None
                for key, value in json.load(file).items()
            }
    else:
        return {}

# Функція для збереження останніх ID повідомлень у файлі
def save_last_message_ids(last_message_ids):
    with open('last_message_ids.json', 'w', encoding='utf-8') as file:
        json.dump({
            key: str(value) for key, value in last_message_ids.items()
        }, file, ensure_ascii=False)

# Функція форматування тексту повідомлення
async def format_post_message(post, source_channel):
    """
    Форматує повідомлення з розділенням на частини, 
    якщо підпис занадто довгий.
    """
    date_str = post.date.astimezone(datetime.timezone(datetime.timedelta(hours=3))).strftime("%d/%m/%Y %H:%M:%S")
    message_text = re.sub(r'<a.*?</a>|(@\S+)|#\S+|source|github|поддержать|Check our GitHub repo for further details about the update.', '', post.message)
    post_url = f"[@{source_channel}/{post.id}](https://t.me/{source_channel}/{post.id})"

    # Безпечна максимальна довжина для підпису
    max_length = 1024  # Залишаємо простір для інших елементів повідомлення 

    # Розділення підпису на частини 
    message_parts = [message_text[i:i+max_length] for i in range(0, len(message_text), max_length)]

    # Форматування повідомлень
    formatted_messages = []
    for i, part in enumerate(message_parts):
        if i == 0:
            formatted_message = f"""
**Channel:** {namechannel[source_channel]}
**Date:** {date_str}
**Link:** {post_url}
**Description:** {part}
"""
        else:
            formatted_message = f"""
**Description (cont'd):** {part}
"""
        formatted_messages.append(formatted_message)
    return formatted_messages

# Функція публікації повідомлення в каналі
async def publish_message(client, messages, target_channel, document=None):
    """
    Публікує повідомлення в цільовому каналі, обробляючи
    розділені повідомлення та документ (якщо є).
    """
    try:
        for message in messages:
            if document is not None:
                await client.send_message(target_channel, message, file=document)
            else:
                await client.send_message(target_channel, message)

    except errors.FloodWaitError as e:
        wait_time = datetime.timedelta(seconds=e.seconds)
        logging.warning(f"Flood wait. Sleeping for {wait_time}")
        time.sleep(e.seconds)
        await publish_message(client, messages, target_channel, document=document)

async def main():
    async with TelegramClient('session_name', api_id, api_hash) as client:
        last_message_ids = load_last_message_ids()

        while True:
            try:
                for source_channel in source_channels:
                    last_message_id = last_message_ids.get(source_channel)

                    if last_message_id is not None:
                        messages = await client.get_messages(source_channel, limit=1, min_id=last_message_id)
                    else:
                        messages = await client.get_messages(source_channel, limit=1)
                    if messages:
                        message = messages[0]
                        
                        # Перевіряємо наявність документа
                        if message.media and isinstance(message.media, types.MessageMediaDocument):
                            # Виводимо в логи канал та ID
                            logging.info(f"Отримано повідомлення з каналу: {source_channel}, ID: {message.id}") 
                            formatted_messages = await format_post_message(message, source_channel)
                            document = message.media.document
                            await publish_message(client, formatted_messages, target_channel, document=document)
                            logging.info("New message published to target channel.")
                            last_message_ids[source_channel] = message.id
            except errors.RPCError as e:
                logging.error(f"RPCError: {e}")
            except errors.FloodWaitError as e:
                logging.error(f"FloodWaitError: {e}")
            except Exception as e:
                logging.error(f"Error: {e}")

            save_last_message_ids(last_message_ids)
            await asyncio.sleep(15)

asyncio.run(main())
