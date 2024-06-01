import datetime, time, asyncio, logging, os, json, re
from telethon import TelegramClient, errors, types

api_id = id
api_hash = 'hash'
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

with open('channels.json', 'r', encoding='utf-8') as file:
    config = json.load(file)
    namechannel = config['namechannel']
    source_channels = list(namechannel.keys())
    target_channel = config['target_channel']

with open('regex_patterns.json', 'r', encoding='utf-8') as file:
    regex_config = json.load(file)
    regex_patterns = regex_config['patterns']

def load_last_message_ids():
    if os.path.exists('last_message_ids.json'):
        with open('last_message_ids.json', 'r', encoding='utf-8') as file:
            return {
                key: int(value) if value is not None else None
                for key, value in json.load(file).items()
            }
    else:
        return {}

def save_last_message_ids(last_message_ids):
    with open('last_message_ids.json', 'w', encoding='utf-8') as file:
        json.dump({
            key: str(value) for key, value in last_message_ids.items()
        }, file, ensure_ascii=False)

async def format_post_message(post, source_channel):
    date_str = post.date.astimezone(datetime.timezone(datetime.timedelta(hours=3))).strftime("%d/%m/%Y %H:%M:%S")
    message_text = post.message if post.message else ''
    for pattern in regex_patterns:
        message_text = re.sub(pattern, '', message_text)
    post_url = f"[@{source_channel}/{post.id}](https://t.me/{source_channel}/{post.id})"
    formatted_message = (
        f"**Channel:** {namechannel[source_channel]}\n"
        f"**Date:** {date_str}\n"
        f"**Link:** {post_url}\n"
    )
    if len(formatted_message) + len(message_text) <= 4096:
        formatted_message += f"**Description:** {message_text}"
    else:
        formatted_message += "**Description:** too long..."
    return [formatted_message]

async def publish_message(client, target_channel, message):
    await client.send_message(target_channel, message, link_preview=False)

async def forward_documents(client, post, target_channel):
    documents = [message for message in post.media.document if message]
    for document in documents:
        await client.send_file(target_channel, document)

async def process_messages(client, source_channel, target_channel, last_message_ids, mode):
    async for post in client.iter_messages(source_channel, min_id=last_message_ids.get(source_channel, 0), reverse=True):
        if post.media and isinstance(post.media, types.MessageMediaDocument):
            if mode == 1:
                await client.forward_messages(target_channel, post.id, source_channel)
            elif mode == 2:
                await forward_documents(client, post, target_channel)
                formatted_messages = await format_post_message(post, source_channel)
                for message in formatted_messages:
                    await publish_message(client, target_channel, message)
        last_message_ids[source_channel] = max(last_message_ids.get(source_channel, 0), post.id)

async def main():
    mode = int(input("Введіть режим роботи (1 - простий репост, 2 - форматування повідомлення): "))
    client = TelegramClient('session_name', api_id, api_hash)
    await client.start()
    last_message_ids = load_last_message_ids()
    try:
        while True:
            for source_channel in source_channels:
                await process_messages(client, source_channel, target_channel, last_message_ids, mode)
            save_last_message_ids(last_message_ids)
            await asyncio.sleep(15)
    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
