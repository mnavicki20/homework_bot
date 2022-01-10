import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (EmptyListOrDictionaryError, IndefinеStatusError,
                        RequestExceptionError, ResponseStatusCodeError)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    filemode='w',
    format='%(asctime)s - %(levelname)s - %(message)s - %(time)s'
)
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())


def send_message(bot, message):
    """Отправка сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, text=message)
        logger.info(
            f'Отправлено сообщение в Telegram: {message}')
    except telegram.TelegramError as error:
        logger.error(
            f'Сообщение в Telegram не отправлено: {error}')


def get_api_answer(current_timestamp):
    """Осуществление запроса к эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != HTTPStatus.OK:
            url_error_message = (
                f'Эндпоинт {ENDPOINT} недоступен.'
                f'Код ответа API: {response.status_code}.')
            logger.error(url_error_message)
            raise ResponseStatusCodeError(url_error_message)
        return response.json()
    except requests.exceptions.RequestException as request_error:
        request_error_message = f'Код ответа API: {request_error}'
        logger.error(request_error_message)
        raise RequestExceptionError(request_error_message)


def check_response(response):
    """Проверка ответа API на корректность."""
    try:
        homeworks = response['homeworks']
        if homeworks is None:
            api_error_message = (
                'Response имеет некорректное значение '
                'или ошибка ключа "homeworks".')
            logger.error(api_error_message)
            raise EmptyListOrDictionaryError(api_error_message)
        if homeworks == []:
            return {}
        if not isinstance(homeworks, list):
            api_error_message = 'Ответ от API не является списком'
            logger.error(api_error_message)
            raise EmptyListOrDictionaryError(api_error_message)
        return homeworks
    except KeyError:
        message = 'Запрошенный ключ отсуствует в полученном словаре'
        logger.error(message)
        raise KeyError(message)


def parse_status(homework):
    """Извлечение статуса конкретной домашней работы."""
    try:
        homework_name = homework['homework_name']
        homework_status = homework.get('status')
        if homework_status is None:
            text_error = 'Ошибка: пустое значение "status".'
            raise IndefinеStatusError(text_error)
        if homework.get('homework_name') is None:
            text_error = 'Ошибка: пустое значение "homework_name".'
            raise IndefinеStatusError(text_error)
        verdict = VERDICTS[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except KeyError:
        message = 'Запрошенный ключ отсуствует в полученном словаре'
        logger.error(message)
        raise KeyError(message)


def check_tokens():
    """Проверка наличия обязательных переменных окружения."""
    no_tokens_message = (
        'Программа остановлена, '
        'т.к. отсутствует следующая обязательная переменная')
    token_boolean = True
    if PRACTICUM_TOKEN is None:
        token_boolean = False
        logger.critical(f'{no_tokens_message}: PRACTICUM_TOKEN')
    if TELEGRAM_TOKEN is None:
        token_boolean = False
        logger.critical(f'{no_tokens_message}: TELEGRAM_TOKEN')
    if TELEGRAM_CHAT_ID is None:
        token_boolean = False
        logger.critical(f'{no_tokens_message}: TELEGRAM_CHAT_ID')
    return token_boolean


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical("Отсутствует переменная(-ные) окружения")
        exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    tmp_status = 'reviewing'
    errors = True
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if homework and tmp_status != homework['status']:
                message = parse_status(homework)
                send_message(bot, message)
                tmp_status = homework['status']
            logger.info(
                'Изменения статуса отсутствуют, через 10 минут проверим API')
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if errors:
                errors = False
                send_message(bot, message)
            logger.critical(message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
