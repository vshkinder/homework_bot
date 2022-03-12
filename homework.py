import logging
import os
import sys

import requests
import time
from telegram import Bot
from dotenv import load_dotenv
from http import HTTPStatus
from logging.handlers import RotatingFileHandler


logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    format='%(asctime)s, %(funcName)s, %(levelname)s, %(message)s'
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

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

UNIX_YEAR_BEGIN = 1641040337
LOG_MESSAGE = 'Сообщение "{}" отправлено'
LOG_MESSAGE_ERROR = 'Ошибка при отправке сообщения'


def send_message(bot, message):
    """Функция отправки сообщения."""
    chat_id = TELEGRAM_CHAT_ID
    bot.send_message(
        chat_id=chat_id,
        text=message,
    )
    logger.info(LOG_MESSAGE.format(message))
    logger.error(LOG_MESSAGE_ERROR)


def get_api_answer(current_timestamp):
    """Функция делает запрос к API по токену."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(url=ENDPOINT, headers=HEADERS, params=params)
    except ValueError:
        logger.error('Ошибка запроса с параметрами "{}".'.format(params))
        raise ValueError('Ошибка при формировании json(response)')
    except Exception as error:
        raise Exception(f'API ошибка запроса: {error}')
    if response.status_code != HTTPStatus.OK:
        status_code = response.status_code
        logger.error(f'Ошибка {status_code}')
        raise Exception(f'Ошибка {status_code}')
    response = response.json()
    return response


def check_response(response):
    """Проверка ответа API на корректность."""
    if not isinstance(response, dict):
        message = 'Ответ API не словарь'
        raise TypeError(message)
    elif ('homeworks' or 'current_date') not in response:
        message = 'В ответе отсутствуют необходимые ключи'
        raise IndexError(message)
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
    # в pytest словарь передается без homework_name
    # при добавлении проверки на наличие ключа
    # тесты не проходят
    homework_status = homework['status']
    if homework_status not in HOMEWORK_VERDICTS:
        message = 'Неопределенный статус: "{}"'
        raise IndexError(message.format(homework_status))
    else:
        verdict = HOMEWORK_VERDICTS[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    list_tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    if all(list_tokens) is False:
        message = 'Ошибка токена. Программа завершена'
        logging.critical(message)
        return False
    else:
        return True


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Отсутствует токен или id чата')
        sys.exit()
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = UNIX_YEAR_BEGIN
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if homework:
                homework = homework[0]
                message = parse_status(homework)
                send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        else:
            logging.error('Неопределенный сбой в работе программы')
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
