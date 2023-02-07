from os import getenv
from dotenv import load_dotenv
import telegram
import time
import requests
import logging
import sys
from http import HTTPStatus
from exceptions import RequestError, WrongStatusCode

from logging import StreamHandler

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)
handler = StreamHandler(stream=sys.stdout)

load_dotenv()

PRACTICUM_TOKEN = getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка наличия всех необходимых токенов"""
    if not PRACTICUM_TOKEN or not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logging.critical('Необходимый токен не найден.')
        raise NameError('Необходимый токен не найден.')


def send_message(bot, message):
    """Отправка сообщения в Telegram"""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception:
        logger.error(f'Отправка сообщения не удалась: {message}')
    else:
        logger.debug(f'Сообщение отправлено успешно: {message}')


def get_api_answer(timestamp):
    """Запрашиваем информацию от API Практикума"""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(url=ENDPOINT, headers=HEADERS, params=payload)
    except requests.RequestException:
        logger.error('Ошибка запроса к API Практикума')
        raise RequestError('Ошибка запроса к API Практикума')
    else:
        if response.status_code != HTTPStatus.OK:
            logger.error(f'Ошибка {response.status_code} при получении ответа от API Практикума')
            raise WrongStatusCode(f'Ошибка {response.status_code} при получении ответа от API Практикума')
        else:
            logger.debug('Ответ от API получен')
            return response.json()


def check_response(response):
    """Проверяем ответ от API Практикума"""
    try:
        timestamp = response['current_date']
        homeworks = response['homeworks']
        if not isinstance(homeworks, list):
            logger.error('В ответе API homeworks не является списком')
            raise TypeError('В ответе API homeworks не является списком')
        if len(homeworks) == 0:
            last_homework = None
        else:
            last_homework = homeworks[0]
        return last_homework, timestamp
    except KeyError as error:
        logger.error(f'Содержание ответа от API не соответствует ожидаемому, {error}')
        raise KeyError(f'Содержание ответа от API не соответствует ожидаемому, {error}')


def parse_status(homework):
    """Парсим статус домашней работы"""
    try:
        homework_name = homework['homework_name']
        homework_status = homework['status']
    except KeyError as error:
        logger.error(f'Не найден необходимый ключ в ответе API, {error}')
        raise KeyError(f'Не найден необходимый ключ в ответе API, {error}')
    else:
        try:
            verdict = HOMEWORK_VERDICTS[homework_status]
        except KeyError:
            logger.error(f'Hеожиданный статус домашней работы, {homework_status}')
            raise KeyError(f'Hеожиданный статус домашней работы, {homework_status}')
        else:
            return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""

    check_tokens()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_error_message = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            homework, timestamp = check_response(response)
            if homework:
                message = parse_status(homework)
                send_message(bot, message)
            else:
                logger.debug('Статус без изменений.')
            last_error_message = ''

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if last_error_message != message:
                send_message(bot, message)
                last_error_message = message

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
