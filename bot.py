import datetime, time, asyncio, logging, os, json, re
from telethon import TelegramClient, errors, types
api_id = 
api_hash = ''
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

with open('channels.json', 'r', encoding='utf-8') as file:
    config = json.load(file)
    namechannel = config['namechannel']
    source_channels = list(namechannel.keys())
    target_channel = config['target_channel']

with open('regex_patterns.json', 'r', encoding='utf-8') as file:
    regex_config = json.load(file)
    regex_patterns = regex_config['patterns']
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
    formatted_message = f"""
**Channel:** {namechannel[source_channel]}
**Date:** {date_str}
**Link:** {post_url}
"""
    if len(formatted_message) + len(message_text) <= 4096:
        formatted_message += f"**Description:** {message_text}"
    else:
        formatted_message += "**Description:** too long..."
    return [formatted_message] 

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
                    logging.warning("Message is too long. Sending without full description.")
                    short_message = f"{message.split('**Description:**')[0]}**Description:** too long..."
                    if document is not None:
                        await client.send_message(target_channel, short_message, file=document)
                    else:
                        await client.send_message(target_channel, short_message)
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
                    logging.info(f"Fetching messages from {source_channel} after ID {last_message_id}")
                    if last_message_id is not None:
                        messages = await client.get_messages(source_channel, limit=2, min_id=last_message_id)
                    else:
                        messages = await client.get_messages(source_channel, limit=2)
                    if messages:
                        current_message = messages[0]
                        previous_message = messages[1] if len(messages) > 1 else None
                        if current_message.media and isinstance(current_message.media, types.MessageMediaDocument):
                            logging.info(f"Received document message from channel: {source_channel}, ID: {current_message.id}")
                            formatted_messages = await format_post_message(current_message, source_channel)
                            document = current_message.media.document
                            await publish_message(client, formatted_messages, target_channel, document=document)
                            logging.info("New document message published to target channel.")
                            last_message_ids[source_channel] = current_message.id
                        elif previous_message and previous_message.media and isinstance(previous_message.media, types.MessageMediaDocument):
                            logging.info(f"Current message is not a document. Publishing previous document message from channel: {source_channel}, ID: {previous_message.id}")
                            formatted_messages = await format_post_message(previous_message, source_channel)
                            document = previous_message.media.document
                            await publish_message(client, formatted_messages, target_channel, document=document)
                            logging.info("Previous document message published to target channel.")
                            last_message_ids[source_channel] = previous_message.id
                        else:
                            logging.info(f"No document messages found in the last two messages from channel: {source_channel}")
            except errors.RPCError as e:
                logging.error(f"RPCError: {e}")
            except errors.FloodWaitError as e:
                logging.error(f"FloodWaitError: {e}")
            except Exception as e:
                logging.error(f"Error: {e}")
            save_last_message_ids(last_message_ids)
            await asyncio.sleep(15)

asyncio.run(main())
