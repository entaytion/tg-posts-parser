import datetime, time, asyncio, logging, os, json, re, requests
from telethon import TelegramClient, errors, types

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
CONFIG_FILENAME = 'config.json'

class ConfigManager:
    def __init__(self, filename):
        self.filename = filename
        self.config = self.load_config()

    def load_config(self):
        with open(self.filename, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_config(self):
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=4)

class FileManager:
    @staticmethod
    def download_file(url, local_filename):
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return local_filename

class MessageFormatter:
    @staticmethod
    async def format_post_message(post, source_channel, regex_patterns, channels):
        date_str = post.date.astimezone(datetime.timezone(datetime.timedelta(hours=3))).strftime("%d/%m/%Y %H:%M:%S")
        message_text = post.message if post.message else ''
        for pattern in regex_patterns:
            message_text = re.sub(pattern, '', message_text)
        post_url = f"[@{source_channel}/{post.id}](https://t.me/{channels[source_channel]['last_id']}/{post.id})"
        formatted_message = (
            f"**Channel:** {channels[source_channel]['name']}\n"
            f"**Date:** {date_str}\n"
            f"**Link:** {post_url}\n"
        )
        if len(formatted_message) + len(message_text) <= 4096:
            formatted_message += f"**Description:** {message_text}"
        else:
            formatted_message += "**Description:** too long..."
        return [formatted_message]

class TelegramManager:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.config = config_manager.config
        self.client = TelegramClient('session_name', self.config['api_id'], self.config['api_hash'])

    async def start(self):
        await self.client.start()

    async def stop(self):
        await self.client.disconnect()

    async def publish_message(self, target_channels, message):
        for channel in target_channels:
            await self.client.send_message(channel, message, link_preview=False)

    async def forward_documents(self, post, target_channels):
        for channel in target_channels:
            try:
                await self.client.send_file(
                    channel,
                    post.media.document,
                    caption=post.message,
                    link_preview=False
                )
            except errors.FloodWaitError as e:
                logging.warning(f"Flood wait error: sleeping for {e.seconds} seconds")
                await asyncio.sleep(e.seconds)
            except errors.RPCError as e:
                logging.error(f"Failed to forward document to {channel}: {e}")

    async def process_messages(self, source_channel, target_channels, mode):
        last_id = self.config['channels'][source_channel].get('last_id', 0)
        async for post in self.client.iter_messages(source_channel, min_id=last_id, reverse=True):
            if post.id <= last_id:
                continue
            self.config['channels'][source_channel]['last_id'] = post.id
            if mode == 5:
                for channel in target_channels:
                    try:
                        await self.client.forward_messages(channel, post.id, source_channel)
                    except errors.FloodWaitError as e:
                        logging.warning(f"Flood wait error: sleeping for {e.seconds} seconds")
                        await asyncio.sleep(e.seconds)
                    except errors.RPCError as e:
                        logging.error(f"Failed to forward message to {channel}: {e}")
            
            elif post.sticker:
                logging.info(f'Skipping sticker message {post.id} in channel {source_channel}')
                continue

            formatted_messages = []
            if post.media and isinstance(post.media, types.MessageMediaDocument):
                if mode == 1 or mode == 3:
                    for channel in target_channels:
                        await self.client.forward_messages(channel, post.id, source_channel)
                elif mode == 2 or mode == 4:
                    formatted_message = await MessageFormatter.format_post_message(post, source_channel, self.config['regex_patterns'], self.config['channels'])
                    formatted_message_text = formatted_message[0] if formatted_message else ''

                    for channel in target_channels:
                        try:
                            await self.client.send_file(
                                channel,
                                post.media.document,
                                caption=formatted_message_text,
                                link_preview=False
                            )
                        except errors.FloodWaitError as e:
                            logging.warning(f"Flood wait error: sleeping for {e.seconds} seconds")
                            await asyncio.sleep(e.seconds)
                        except errors.RPCError as e:
                            logging.error(f"Failed to forward document to {channel}: {e}")

        self.config_manager.save_config()
class GitHubManager:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.config = config_manager.config

    async def process_github_releases(self, client, target_channels):
        for repo, repo_info in self.config['repositories'].items():
            APP_NAME = repo_info['app_name']
            LATEST_VERSION = repo_info.get('latest_version', '')
            GITHUB_RELEASES_URL = f"https://api.github.com/repos/{repo}/releases/latest"

            response = requests.get(GITHUB_RELEASES_URL)
            release = response.json()
            assets = release.get('assets', [])
            tag_name = release.get('tag_name', 'N/A')
            body = release.get('body', 'No description provided.')
            html_url = release.get('html_url', f'https://github.com/{repo}/releases')

            if tag_name == LATEST_VERSION:
                logging.info(f"Release {tag_name} for {APP_NAME} is already up-to-date.")
                continue
            if len(body) > 1024:
                body = f"[too long]({html_url})"
            if not assets:
                logging.info(f"No assets found in the latest release for {APP_NAME}.")
                continue
            for CHANNEL_ID in target_channels:
                async for message in client.iter_messages(CHANNEL_ID, search=tag_name):
                    if tag_name in message.message:
                        logging.info(f"Release {tag_name} for {APP_NAME} already posted in {CHANNEL_ID}.")
                        break
                else:
                    asset_files = [asset for asset in assets if asset['name'].endswith(('.apk', '.apks', '.aab'))]
                    for asset in asset_files:
                        asset_url = asset['browser_download_url']
                        local_filename = asset['name']
                        logging.info(f"Downloading {local_filename}...")
                        FileManager.download_file(asset_url, local_filename)
                        logging.info(f"Downloaded {local_filename}.")
                        message = (
                            f"**Name**: [{APP_NAME}](https://github.com/{repo})\n"
                            f"**Version**: {tag_name}\n"
                            f"**Description**: {body}\n"
                            f"**Tags**: #opensource"
                        )
                        logging.info(f"Uploading {local_filename} to Telegram...")
                        await client.send_file(CHANNEL_ID, local_filename, caption=message)
                        logging.info(f"Uploaded {local_filename} to Telegram.")
                        os.remove(local_filename)
                    repo_info['latest_version'] = tag_name
                    self.config_manager.save_config()

async def initialize_new_channel(client, source_channel, channels):
    async for post in client.iter_messages(source_channel, limit=1):
        if 'last_id' not in channels[source_channel] or channels[source_channel]['last_id'] == 0:
            channels[source_channel]['last_id'] = post.id
        break

async def process_github_periodically(github_manager, client, target_channels):
    while True:
        await github_manager.process_github_releases(client, target_channels)
        await asyncio.sleep(21600)
async def main():
    config_manager = ConfigManager(CONFIG_FILENAME)
    telegram_manager = TelegramManager(config_manager)
    github_manager = GitHubManager(config_manager)
    mode = int(input("1 - repost messages\n2 - format messages\n3 - repost messages + github\n4 - format messages + github\n5 - repost all messages\nEnter mode: "))
    await telegram_manager.start()

    try:
        for source_channel in config_manager.config['channels']:
            if 'last_id' not in config_manager.config['channels'][source_channel] or config_manager.config['channels'][source_channel]['last_id'] == 0:
                await initialize_new_channel(telegram_manager.client, source_channel, config_manager.config['channels'])
        config_manager.save_config()

        while True:
            for source_channel in config_manager.config['channels']:
                await telegram_manager.process_messages(source_channel, config_manager.config['target_channel'], mode)
            if mode in [3, 4]:
               asyncio.create_task(process_github_periodically(github_manager, telegram_manager.client, config_manager.config['target_channel']))
            await asyncio.sleep(15)
    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        await telegram_manager.stop()


if __name__ == '__main__':
    asyncio.run(main())