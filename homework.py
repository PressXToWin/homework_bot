from os import getenv
from dotenv import load_dotenv
import telegram
import time
import requests
import logging
import sys
from http import HTTPStatus

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
    """TODO: сделать докстринг. Формально докстринг есть"""
    if not PRACTICUM_TOKEN or not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logging.critical('Необходимый токен не найден.')
        raise NameError('Необходимый токен не найден.')


def send_message(bot, message):
    """TODO: сделать докстринг. Формально докстринг есть"""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception:
        logger.error('Отправка сообщения не удалась')
    else:
        logger.debug('Сообщение отправлено успешно')


def get_api_answer(timestamp):
    """TODO: сделать докстринг. Формально докстринг есть"""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(url=ENDPOINT, headers=HEADERS, params=payload)
    except requests.RequestException:
        raise Exception
    else:
        if response.status_code != 200:
            logger.error('Ошибка получения ответа от эндпоинта')
            raise Exception
        else:
            logger.debug('Ответ от API получен')
        return response.json()


def check_response(response):
    """TODO: сделать докстринг. Формально докстринг есть"""
    try:
        timestamp = response['current_date']
        homeworks = response['homeworks']
        if not isinstance(homeworks, list):
            raise TypeError
        if len(homeworks) == 0:
            homework = None
        else:
            homework = homeworks[0]
        return homework, timestamp
    except KeyError:
        logger.error('Содержание ответа от API не соответствует ожидаемому')
        raise KeyError


def parse_status(homework):
    """TODO: сделать докстринг. Формально докстринг есть"""
    try:
        homework_name = homework['homework_name']
        homework_status = homework['status']
    except KeyError:
        logger.error('Ключ не найден')
    else:
        try:
            verdict = HOMEWORK_VERDICTS[homework_status]
        except Exception:
            logger.error('Hеожиданный статус домашней работы')
            verdict = homework_status
            raise Exception

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""

    check_tokens()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            homework, timestamp = check_response(response)
            if homework:
                message = parse_status(homework)
                send_message(bot, message)
            else:
                logger.debug('Статус без изменений.')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
