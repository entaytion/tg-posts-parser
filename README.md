# 📩 Telegram Posts Parser

📲 Цей проєкт надає можливість пересилати та форматувати повідомлення з каналів Telegram на інші канали. Він також дозволяє автоматично публікувати оновлення з GitHub-репозиторіїв.

## ✨ Особливості

* **Автоматичне форматування повідомлень**: Видаляє небажані елементи з повідомлень за допомогою регулярних виразів.
* **Автоматичне пересилання**: Автоматично пересилає повідомлення з визначених каналів на цільові канали.
* **Інтеграція з GitHub**: Автоматично публікує оновлення з GitHub-репозиторіїв у цільові канали Telegram.
* **Легке налаштування**: Простий у налаштуванні через конфігураційний файл `config.json`.

## 🚀 Початок роботи


1. Клонуйте репозиторій:

   ```bash
   git clone https://github.com/entaytion/tg-posts-parser
   cd tg-posts-parser
   ```
2. Встановіть залежності:

   ```bash
   pip install -r requirements.txt
   ```
3. Налаштуйте `config.json` згідно ваших потреб (див. нижче для деталей конфігурації).
4. Запустіть бота:

   ```bash
   python bot.py
   ```
5. Оберіть режим роботи при запуску:
   * Введіть `1` для простого репосту.
   * Введіть `2` для режиму форматування.
   * Введіть `3` для простого репосту + Github.
   * Введіть `4` для режиму форматування + Github.

## 📝 Опис полів

* **api_id**: Ваш унікальний API ID, отриманий від [Telegram](https://my.telegram.org).
* **api_hash**: Ваш унікальний API Hash, отриманий від [Telegram](https://my.telegram.org).
* **channels**: Список каналів, з яких будуть пересилатися повідомлення.
  * `name`: Назва каналу.
  * `last_id`: ID останнього обробленого повідомлення. Встановлюється автоматично.
* **target_channel**: Список каналів, куди будуть пересилатися повідомлення.
* **regex_patterns**: Список регулярних виразів для видалення з повідомлень непотрібного контенту.
* **repositories**: Список GitHub-репозиторіїв для автоматичного публікування оновлень.
  * `app_name`: Назва додатку. Використовується для режимів `3` та `4`.
  * `latest_version`: Остання відома версія додатку. Встановлюється автоматично.

## 🔄 Оновлення конфігурації

### ➕ Додавання нового каналу

Щоб додати новий канал для моніторингу:

```javascript
"channels": {
    "new_channel": {
        "name": "Channel Name",
        "last_id": 0
    }
}
```

Додайте канал, куди буде відправляти повідомлення, у `target_channel`:

```javascript
"target_channel": [
    "new_target_channel"
]
```

### 🔍 Оновлення регулярних виразів

Щоб додати новий регулярний вираз для видалення з повідомлень:

```javascript
"regex_patterns": [
    "<a.*?</a>",
    "@\\S+",
    "#\\S+",
    ...
]
```

### 🗂️ Додавання GitHub-репозиторію

Щоб додати новий GitHub-репозиторій для автоматичного публікування оновлень:

```javascript
"repositories": {
    "user/new_repository": {
        "app_name": "App Name",
        "latest_version": "v1.0.0"
    }
}
```

## 🌟 Внесок

Ви можете зробити внесок у розвиток проекту, відкривши Pull Request або створивши Issue.

З будь-якими питаннями або пропозиціями звертайтесь до нас на [GitHub Issues](https://github.com/entaytion/tg-posts-parser/issues).


💡 **Примітка**: Переконайтесь, що у вас є доступ до всіх необхідних каналів та правильні налаштування доступу до API Telegram.