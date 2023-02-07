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
    if not PRACTICUM_TOKEN or not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logging.critical('Необходимый токен не найден.')
        raise NameError('Необходимый токен не найден.')


def send_message(bot, message):
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception:
        logger.error('Отправка сообщения не удалась')
    else:
        logger.debug('Сообщение отправлено успешно')


def get_api_answer(timestamp):
    payload = {'from_date': timestamp}
    response = requests.get(url=ENDPOINT, headers=HEADERS, params=payload)
    if response.status_code != HTTPStatus.OK:
        logger.error('Ошибка получения ответа от эндпоинта')
    else:
        logger.debug('Ответ от API получен')
    return response.json()


def check_response(response):
    try:
        timestamp = response['current_date']
        homeworks = response['homeworks']
        if len(homeworks) == 0:
            homework = None
        else:
            homework = homeworks[0]
        return homework, timestamp
    except KeyError:
        logger.error('Содержание ответа от API не соответствует ожидаемому')


def parse_status(homework):
    homework_name = homework['homework_name']
    homework_status = homework['status']
    try:
        verdict = HOMEWORK_VERDICTS[homework_status]
    except Exception:
        logger.error('Hеожиданный статус домашней работы')
        verdict = homework_status

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
