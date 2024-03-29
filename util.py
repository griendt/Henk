import logging
import random
import re
import sys
from collections.abc import Sequence
from logging.config import dictConfig
from typing import Literal, TypedDict, TypeVar

import telepot

T = TypeVar('T')

remove_emoji = re.compile(
    '[' '\U0001f300-\U0001f64f' '\U0001f680-\U0001f6ff' '\u2600-\u26ff\u2700-\u27bf]+',
    re.UNICODE,
)


def normalise(string: str) -> str:  # " Hoi   bla" -> "hoi bla"
    new_string = string.lower().strip()
    new_string = remove_emoji.sub('', new_string)
    return ' '.join(new_string.split())


def prepare_query(query: str) -> str:
    r = query.lower().strip().replace(', ', ' ').replace('?', '').replace('!', '')
    if r.endswith('.'):
        r = r[:-1]
    return r.strip()


def pick(items: Sequence[T]) -> T:  # picks random element from list
    return random.sample(items, 1)[0]


def setup_logging() -> None:
    dictConfig(
        {
            'version': 1,
            'disable_existing_loggers': True,
            'formatters': {
                'default': {
                    'format': '%(asctime)s.%(msecs)03d %(levelname)s %(pathname)s:%(lineno)s %(message)s',
                    'datefmt': '%Y-%m-%d %H:%M:%S',
                },
            },
            'handlers': {
                'app_file': {
                    'class': logging.FileHandler,
                    'filename': 'app.log',
                    'formatter': 'default',
                    'mode': 'a',
                },
                'stderr': {
                    'class': logging.StreamHandler,
                    'stream': sys.stderr,
                    'formatter': 'default',
                },
            },
            'loggers': {
                '': {
                    'level': logging.DEBUG,
                    'handlers': ['app_file', 'stderr'],
                    'propagate': False,
                },
            },
        }
    )


class TelegramUser(TypedDict):
    first_name: str
    id: int
    is_bot: bool
    language_code: str
    username: str


class TelegramChat(TypedDict, total=False):
    id: int
    type: Literal['private', 'group', 'channel']


RawTelegramMessage = TypedDict(
    'RawTelegramMessage',
    {
        'message_id': int,
        'from': TelegramUser,
        'chat': TelegramChat,
        'date': int,
        'text': Literal['1', ''],
    },
    total=False,
)


class RawTelegramUpdate(TypedDict):
    update_id: int
    message: RawTelegramMessage


class Message:
    content_type: str
    is_text: bool
    chat_id: int
    chat_type: str
    raw: Literal['1', '']
    normalised: str
    command: str
    sender: int
    sender_name: str
    date: int
    object: RawTelegramMessage

    def __init__(self, msg: RawTelegramMessage) -> None:
        content_type, chat_type, chat_id = telepot.glance(msg)
        self.content_type = content_type
        self.is_text = content_type == 'text'
        self.chat_id = chat_id
        self.chat_type = chat_type
        if self.is_text:
            self.raw = msg['text']
            self.normalised = normalise(msg['text'])
            self.command = self.normalised
        else:
            self.raw = ''
            self.normalised = ''
            self.command = ''
        try:
            self.sender = msg['from']['id']
            self.sender_name = msg['from']['first_name']
        except KeyError:
            self.sender = 0
            self.sender_name = ''
        self.date = msg['date']

        self.object = msg
