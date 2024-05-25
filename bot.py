import datetime, time, asyncio, logging, os, json, re
from telethon import TelegramClient, errors, types

# Налаштування Telegram API
api_id = 
api_hash = ''

# Налаштування логування
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Завантаження конфігурації каналів
with open('channels.json', 'r', encoding='utf-8') as file:
    config = json.load(file)
    namechannel = config['namechannel']
    source_channels = list(namechannel.keys())
    target_channel = config['target_channel']

# Завантаження регулярних виразів
with open('regex_patterns.json', 'r', encoding='utf-8') as file:
    regex_config = json.load(file)
    regex_patterns = regex_config['patterns']

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
    date_str = post.date.astimezone(datetime.timezone(datetime.timedelta(hours=3))).strftime("%d/%m/%Y %H:%M:%S")
    message_text = post.message if post.message else ''
    for pattern in regex_patterns:
        message_text = re.sub(pattern, '', message_text)
    
    post_url = f"[@{source_channel}/{post.id}](https://t.me/{source_channel}/{post.id})"

    formatted_message = f"""
**Channel:** {namechannel[source_channel]}
**Date:** {date_str}
**Link:** {post_url}
"""

    # Перевірка довжини перед додаванням опису
    if len(formatted_message) + len(message_text) <= 4096:
        formatted_message += f"**Description:** {message_text}"
    else:
        formatted_message += "**Description:** too long..."

    return [formatted_message]  # Повертаємо список, навіть з одним повідомленням 

# Функція публікації повідомлення в каналі
async def publish_message(client, messages, target_channel, document=None):
    try:
        for message in messages:
            try:
                if document is not None:
                    await client.send_message(target_channel, message, file=document)
                else:
                    await client.send_message(target_channel, message)
            except errors.RPCError as e:
                if "caption is too long" in str(e) or "The caption is too long (caused by SendMediaRequest)" in str(e):
                    logging.warning("Повідомлення занадто довге. Відправка без повного опису.")
                    short_message = f"{message.split('**Description:**')[0]}**Description:** too long..."
                    if document is not None:
                        await client.send_message(target_channel, short_message, file=document)  # Відправка з коротким описом
                    else:
                        await client.send_message(target_channel, short_message)  # Відправка з коротким описом
                else:
                    raise e

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
