import logging
import os
import requests
import time
from telegram import Bot
from dotenv import load_dotenv
from http import HTTPStatus
from logging.handlers import RotatingFileHandler


logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    format='%(asctime)s, %(levelname)s, %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(
    'my_logger.log',
    maxBytes=50000000,
    backupCount=5
)
logger.addHandler(handler)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN_ENV')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN_ENV')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID_ENV')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

UNIX_YEAR_BEGIN = 1641040337


def send_message(bot, message):
    """Функция отправки сообщения."""
    chat_id = TELEGRAM_CHAT_ID
    bot.send_message(
        chat_id=chat_id,
        text=message,
    )


def get_api_answer(current_timestamp):
    """Функция делает запрос к API по токену."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(url=ENDPOINT, headers=HEADERS, params=params)
    except ValueError:
        logger.error('Ошибка при формировании json (response)')
        raise ValueError('Ошибка при формировании json(response)')
    except Exception as error:
        logger.error(f'API ошибка запроса: {error}')
        raise Exception(f'API ошибка запроса: {error}')
    if response.status_code != HTTPStatus.OK:
        status_code = response.status_code
        logger.error(f'Ошибка {status_code}')
        raise Exception(f'Ошибка {status_code}')
    response = response.json()
    return response


def check_response(response):
    """Проверка ответа API на корректность."""
    if type(response) is not dict:
        message = 'Ответ API не словарь'
        raise TypeError(message)
    elif ['homeworks'][0] not in response:
        message = 'В ответе API отсутствует домашняя работа'
        raise IndexError(message)
    elif type(response['homeworks']) is not list:
        raise ValueError('работы приходят не списком')
    homework = response['homeworks']
    return homework


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    list_tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    for token in list_tokens:
        if not token:
            message = 'Ошибка токена. Программа завершена'
            logging.critical(message)
            return False
        else:
            return True


def main():
    """Основная логика работы бота."""
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = UNIX_YEAR_BEGIN
    if not check_tokens():
        raise 'Отсутствует токен или id чата'
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if homework:
                homework = homework[0]
                message = parse_status(homework)
                send_message(bot, message)
                time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_TIME)
        else:
            logging.error('Неопределенный сбой в работе программы')


if __name__ == '__main__':
    main()
