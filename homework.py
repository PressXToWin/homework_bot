import logging
import sys
import time
from http import HTTPStatus
from logging import StreamHandler
from os import getenv

import requests
import telegram
from dotenv import load_dotenv

from exceptions import RequestError, WrongStatusCode

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s'
)
handler = StreamHandler(stream=sys.stdout)
handler.setFormatter(formatter)
logger.addHandler(handler)

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
    """Проверка наличия всех необходимых токенов."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def send_message(bot, message):
    """Отправка сообщения в Telegram."""
    try:
        logger.debug(f'Пытаемся отправить сообщение: {message}')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception:
        logger.error(f'Отправка сообщения не удалась: {message}')
    else:
        logger.debug(f'Сообщение отправлено успешно: {message}')


def get_api_answer(timestamp):
    """Запрашиваем информацию от API Практикума."""
    logger.debug('Запрашиваем информацию по API')
    kwargs = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp}
    }
    try:
        response = requests.get(**kwargs)
    except requests.RequestException:
        raise RequestError('Ошибка запроса к API Практикума')
    else:
        if response.status_code != HTTPStatus.OK:
            raise WrongStatusCode(f'Ошибка {response.status_code} '
                                  f'при получении ответа от API Практикума')
        else:
            logger.debug('Ответ от API получен')
            return response.json()


def check_response(response):
    """Проверяем ответ от API Практикума."""
    logger.debug('Проверяем ответ')
    if not isinstance(response, dict):
        raise TypeError('Ответ API не является словарём')
    if 'current_date' in response and 'homeworks' in response:
        timestamp = response['current_date']
        homeworks = response['homeworks']
        if not isinstance(homeworks, list):
            raise TypeError('В ответе API homeworks не является списком')
        if len(homeworks) == 0:
            last_homework = None
        else:
            last_homework = homeworks[0]
        return last_homework, timestamp
    else:
        raise KeyError('Содержание ответа от API не '
                       'соответствует ожидаемому.')


def parse_status(homework):
    """Парсим статус домашней работы."""
    logger.debug('Парсим статус')
    if 'homework_name' in homework and 'status' in homework:
        homework_name = homework['homework_name']
        homework_status = homework['status']
        try:
            verdict = HOMEWORK_VERDICTS[homework_status]
        except KeyError:
            raise KeyError(f'Hеожиданный статус домашней '
                           f'работы, {homework_status}')
        else:
            return (f'Изменился статус проверки '
                    f'работы "{homework_name}". {verdict}')
    else:
        raise KeyError('Не найден необходимый ключ в ответе API.')


def main():
    """Основная логика работы бота."""
    logger.debug('Бот запущен')
    if check_tokens():
        logger.debug('Все токены на месте')
    else:
        logger.critical('Необходимый токен не найден.')
        sys.exit('Необходимый токен не найден.')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_message = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            homework, timestamp = check_response(response)
            if homework:
                message = parse_status(homework)
                if last_message != message:
                    send_message(bot, message)
                    last_message = message
                else:
                    logger.debug('Сообщение не изменилось.')
            else:
                logger.debug('Статус без изменений.')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(error)
            if last_message != message:
                send_message(bot, message)
                last_message = message

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
