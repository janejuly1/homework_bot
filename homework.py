import logging

import requests
import os

from dotenv import load_dotenv
import time
import telegram

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
CHAT_ID = os.getenv('ACCOUNT_SID')

logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s',
    level=logging.DEBUG)
logger = logging.getLogger(__name__)

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена, в ней нашлись ошибки.'
}

HOMEWORKS = {}


def send_message(bot, message):
    """Informs user about the status of homework."""
    bot.send_message(
        chat_id=CHAT_ID,
        message=message,
    )


def get_api_answer(url, current_timestamp):
    """Get json data from API."""
    headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    payload = {'from_date': current_timestamp}

    try:
        response = requests.get(ENDPOINT, headers=headers, params=payload)
    except Exception as error:
        logger.error(f'Ошибка при запросе к основному API: {error}')
        raise error

    if response.status_code != 200:
        logger.error('Ошибка при запросе к основному API: status_code != 200')
        raise RuntimeError(
            'Ошибка при запросе к основному API: status_code != 200')

    try:
        response = response.json()
    except Exception as error:
        logger.error(f'Ошибка парсинга JSON: {error}')
        raise error

    return response


def parse_status(homework):
    """Get a status of homework from json."""
    status = homework['status']
    homework_name = homework['homework_name']

    if homework_name in HOMEWORKS and HOMEWORKS[homework_name] == status:
        return None

    if homework_name not in HOMEWORKS or HOMEWORKS[homework_name] != status:
        HOMEWORKS[homework_name] = status

    verdict = HOMEWORK_STATUSES[status]

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_response(response):
    """Check correctness of json."""
    if 'homeworks' not in response:
        raise RuntimeError('Отсутствует обязательное поле "homeworks"')

    if 'current_date' not in response:
        raise RuntimeError('Отсутствует обязательное поле "current_date"')

    for homework in response['homeworks']:
        if 'homework_name' not in homework:
            raise RuntimeError('Отсутствует обязательное поле "homework_name"')

        if 'status' not in homework:
            raise RuntimeError('Отсутствует обязательное поле "status"')

        if homework['status'] not in HOMEWORK_STATUSES:
            status = homework['status']
            raise RuntimeError(f'Неизвестный статус "{status}"')

    return True


def main():
    """Launches check homework statuses bot ."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = 0

    while True:
        try:
            response = get_api_answer(ENDPOINT, current_timestamp)
            check_response(response)
            for homework in response['homeworks']:
                message = parse_status(homework)
                if message is not None:
                    send_message(bot, message)

            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            time.sleep(RETRY_TIME)
            continue


if __name__ == '__main__':
    main()
