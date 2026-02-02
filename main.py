import datetime
import logging
import os
import sys
import time
from http import HTTPStatus

import requests
from deep_translator import GoogleTranslator
from dotenv import load_dotenv
from telebot import TeleBot

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
ENDPOINT_DAY = os.getenv('ENDPOINT_DAY')

POST_HOUR = 9
POST_DELAY = 15 * 60

SIGNS = {
    'Aries': '♈', 'Taurus': '♉', 'Gemini': '♊', 'Cancer': '♋',
    'Leo': '♌', 'Virgo': '♍', 'Libra': '♎', 'Scorpio': '♏',
    'Sagittarius': '♐', 'Capricorn': '♑', 'Aquarius': '♒', 'Pisces': '♓'
}

REQUIRED_TOKENS = (
    'TELEGRAM_BOT_TOKEN',
    'TELEGRAM_CHANNEL_ID',
    'TELEGRAM_CHAT_ID',
)

TOKEN_MISSING_MESSAGE = 'Отсутствуют переменные окружения: {tokens}'
API_REQUEST_ERROR = 'Ошибка запроса API: {error}'
API_STATUS_ERROR = 'API вернул код {status}'
RESPONSE_STRUCTURE_ERROR = 'Некорректная структура ответа API'
TRANSLATE_ERROR = 'Ошибка перевода: {error}'
BOT_ERROR_MESSAGE = 'Ошибка в работе бота: {error}'


def wait_until_post_time():
    """Блокирует выполнение до следующего запланированного времени постинга."""
    now = datetime.datetime.now()
    target = now.replace(hour=POST_HOUR, minute=0, second=0, microsecond=0)

    if now >= target:
        target += datetime.timedelta(days=1)

    sleep_seconds = (target - now).total_seconds()
    logging.info(f'Ожидание до времени публикации: {target}')
    time.sleep(sleep_seconds)


def check_tokens():
    """Проверяет наличие обязательных переменных окружения."""
    missing = [name for name in REQUIRED_TOKENS if not globals().get(name)]
    if missing:
        raise ValueError(TOKEN_MISSING_MESSAGE.format(tokens=missing))


def translate_text(text):
    """Переводит текст на русский язык."""
    try:
        return GoogleTranslator(source='auto', target='ru').translate(text)
    except Exception as error:
        logging.warning(TRANSLATE_ERROR.format(error=error))
        return text


def get_api_answer(sign):
    """Выполняет запрос к API и возвращает JSON."""
    try:
        response = requests.get(
            ENDPOINT_DAY.format(sign=sign)
        )
    except requests.RequestException as error:
        raise ConnectionError(API_REQUEST_ERROR.format(error=error))

    if response.status_code != HTTPStatus.OK:
        raise ConnectionError(API_STATUS_ERROR.format(
            status=response.status_code
        ))

    try:
        return response.json()
    except ValueError:
        raise ValueError(RESPONSE_STRUCTURE_ERROR)


def extract_horoscope(response):
    """Извлекает текст гороскопа из ответа API."""
    try:
        return response['data']['horoscope_data']
    except (KeyError, TypeError):
        raise ValueError(RESPONSE_STRUCTURE_ERROR)


def format_post(sign, text):
    """Формирует финальный пост для Telegram."""
    emoji = SIGNS.get(sign, '')
    sign_ru = translate_text(sign)
    translated_text = translate_text(text)

    return (
        f"{emoji} <b>{sign_ru.upper()} — Гороскоп на сегодня</b>\n\n"
        f"✨ {translated_text}\n\n"
        f"#гороскоп #{sign_ru.lower()} #астрология"
    )


def send_message(bot, chat_id, text):
    """Отправляет сообщение в Telegram."""
    try:
        bot.send_message(
            chat_id,
            text=text,
            parse_mode='HTML'
        )
        logging.info(f'Сообщение отправлено в {chat_id}')
        return True
    except Exception as error:
        logging.exception(f'Ошибка отправки: {error}')
        return False


def post_daily_horoscopes(bot):
    """Загружает и публикует гороскопы для всех знаков."""
    for sign in SIGNS.keys():
        try:
            response = get_api_answer(sign)
            horoscope = extract_horoscope(response)
            post = format_post(sign, horoscope)
            success = send_message(
                bot,
                TELEGRAM_CHANNEL_ID,
                post
            )
            if not success:
                send_message(
                    bot,
                    TELEGRAM_CHAT_ID,
                    f'Ошибка отправки поста: {sign}'
                )
            else:
                time.sleep(POST_DELAY)
        except Exception as error:
            logging.error(f'Ошибка знака {sign}: {error}')
            send_message(
                bot,
                TELEGRAM_CHAT_ID,
                f'Ошибка API для {sign}: {error}'
            )


def main():
    check_tokens()
    bot = TeleBot(TELEGRAM_BOT_TOKEN)

    logging.info('Бот запущен')

    while True:
        try:
            wait_until_post_time()
            post_daily_horoscopes(bot)
        except Exception as error:
            logging.exception(BOT_ERROR_MESSAGE.format(error=error))
            send_message(
                bot,
                TELEGRAM_CHAT_ID,
                BOT_ERROR_MESSAGE.format(error=error)
            )
            time.sleep(60)


if __name__ == '__main__':
    logging.basicConfig(
        format=('%(asctime)s: %(funcName)s - %(lineno)d '
                '[%(levelname)s] %(message)s'),
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f'{__file__}.log'),
        ],
        level=logging.DEBUG
    )
    main()
