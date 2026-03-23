# horoscope-bot
Daily horoscope telegram bot

Создайте файл `.env` в корне проекта и добавьте в него следующие данные:

```env
TELEGRAM_BOT_TOKEN=ваш_токен_от_botfather
TELEGRAM_CHANNEL_ID=id_вашего_канала
TELEGRAM_CHAT_ID=ваш_личный_id
ENDPOINT_DAY=ссылка_или_метод_api
```

### Как запустить бота:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 main.py
```
