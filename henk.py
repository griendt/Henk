import logging
import random
import threading
import time
from collections import OrderedDict
from typing import Any

import telepot
from telepot.loop import MessageLoop

import modules
from managedata import ManageData
from util import Message, RawTelegramMessage, setup_logging, RawTelegramUpdate


class Henk:
    MAX_MESSAGE_LENGTH = 4096  # as specified in https://limits.tginfo.me/en

    telebot: telepot.Bot
    answerer: telepot.helper.Answerer

    commands: list
    responses: list
    sender_name: Any
    slashcommands: OrderedDict
    callback_query_types: OrderedDict

    def __init__(self, bot: telepot.Bot, *, is_dummy: bool = False) -> None:
        self.telebot = bot  # the bot interface for Telegram
        self.answerer = telepot.helper.Answerer(self.telebot)
        self.dataManager = ManageData()  # interface to the database
        self.dataManager.dummy = is_dummy
        self.message_lock = threading.Lock()

        self.active = False  # whether someone has just talked to me

        self.morning_message_timer = 0  # how long ago we have said a morning message

        self.slashcommands = OrderedDict()  # command:callback where the callback takes two arguments, (self,msg)
        self.callback_query_types = OrderedDict()  # ident:callback for special reply actions from Telegram

        self.commands = []

        for module in modules.modules:
            module.initialise(self)
            module.register_commands(self)

        # PPA = -6722364 #hardcoded label for party pownies
        self.homegroup = -218118195  # Henk's fun palace
        self.admin_ids = [58838022]  # Alex

    def add_slash_command(self, command, callback):
        if command in self.slashcommands:
            raise Exception('Slashcommand %s is already implemented' % command)
        self.slashcommands[command] = callback

    def add_callback_query(self, ident, callback):
        if ident in self.callback_query_types:
            raise Exception('Callback ident %s already used' % ident)
        self.callback_query_types[ident] = callback

    def sendMessage(self, chat_id, s):
        with self.message_lock:
            m = self.telebot.sendMessage(chat_id, s)

        return m

    def pick(self, options):
        return random.sample(options, 1)[0].replace('!name', self.sender_name)

    def on_chat_message(self, message: RawTelegramMessage) -> None:
        parsed_message = Message(message)
        if not parsed_message.is_text:
            logging.info('Chat: %s %s %s', parsed_message.content_type, parsed_message.chat_type, parsed_message.chat_id)
            self.active = False
            return

        self.dataManager.write_message(parsed_message.object)
        self.sender_name = parsed_message.sender_name
        logging.info('Chat: %s %s %s', parsed_message.chat_type, parsed_message.chat_id, parsed_message.normalised.encode('utf-8'))

        if not parsed_message.raw.startswith('/'):
            logging.debug('Message does not start with /; skipping.')
            return

        # TODO: implement support for "/command@user" syntax
        user_command = parsed_message.raw.split()[0][1:]

        if user_command not in self.slashcommands:
            logging.info('User requested command not recognized: %s', parsed_message.raw)
            return

        parsed_message.command = parsed_message.raw[len(user_command) + 2 :].strip()
        if reply := self.slashcommands[user_command](self, parsed_message):
            self.sendMessage(parsed_message.chat_id, reply)

    def on_callback_query(self, message: RawTelegramMessage) -> None:
        query_id, from_id, data = telepot.glance(message, flavor='callback_query')
        logging.debug('Callback query: %s %s %s', query_id, from_id, data)

        for identifier, callback in self.callback_query_types.items():
            if data.startswith(identifier):
                callback(self, message)
                return

        logging.error('Unknown callback query: %s', data)

    def on_inline_query(self, message: RawTelegramMessage) -> None:
        def compute() -> list:
            telepot.glance(message, flavor='inline_query')
            return []

        self.answerer.answer(message, compute)

    @staticmethod
    def on_chosen_inline_result(message: RawTelegramMessage) -> None:
        result_id, from_id, query_string = telepot.glance(message, flavor='chosen_inline_result')
        logging.info('Chosen Inline Result: %s %s %s', result_id, from_id, query_string)


def patch_telepot() -> None:
    """
    Patch telepot's loop._extract_message function. Without the 'update_id'
    field as a valid message type, bots will break in groups chats.
    See also: https://stackoverflow.com/questions/66796130.
    """
    telepot_message_types = [
        'message',
        'edited_message',
        'channel_post',
        'edited_channel_post',
        'callback_query',
        'inline_query',
        'chosen_inline_result',
        'shipping_query',
        'pre_checkout_query',
        'update_id',
    ]

    def extract_message(update: RawTelegramUpdate) -> tuple[Any, Any]:
        # noinspection PyProtectedMember
        key = telepot._find_first_key(update, telepot_message_types)  # noqa: SLF001
        return key, update[key]

    telepot.loop._extract_message = extract_message  # noqa: SLF001


def run() -> None:
    setup_logging()
    logging.info('Booting...')

    patch_telepot()

    with open('apikey.txt') as file:
        token = file.read()

    telebot = telepot.Bot(token)
    henk = Henk(telebot)
    try:
        MessageLoop(
            telebot,
            {
                'chat': henk.on_chat_message,
                'callback_query': henk.on_callback_query,
                'inline_query': henk.on_inline_query,
                'chosen_inline_result': henk.on_chosen_inline_result,
            },
        ).run_as_thread()
        logging.info('Booted. Listening for messages...')

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info('Shutting down by user interrupt...')
    except Exception as e:
        logging.critical('Henk shut down unexpectedly because of the following error: %s', e)

    logging.info('Shut down.')


if __name__ == '__main__':
    while True:
        try:
            run()
        except KeyboardInterrupt:
            break
        except Exception as e:
            logging.exception('An error occurred that triggers a restart')
