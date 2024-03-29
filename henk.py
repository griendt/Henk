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
from util import Message, RawTelegramMessage, setup_logging


class Henk:
    MAX_MESSAGE_LENGTH = 4096  # as specified in https://limits.tginfo.me/en

    telebot: telepot.Bot
    answerer: telepot.helper.Answerer

    commands: list
    responses: list
    sendername: Any
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

        self.active = False
        return m

    def pick(self, options):
        return random.sample(options, 1)[0].replace('!name', self.sendername)

    def on_chat_message(self, message):
        msg = Message(message)
        if not msg.is_text:
            logging.info('Chat: %s %s %d', msg.content_type, msg.chat_type, msg.chat_id)
            self.active = False
            return

        self.dataManager.write_message(msg.object)
        self.sendername = msg.sendername
        logging.info('Chat: %s %d %s', msg.chat_type, msg.chat_id, msg.normalised.encode('utf-8'))

        # slash commands first
        if msg.raw.startswith('/'):
            for k in self.slashcommands.keys():
                cmd = msg.raw.split()[0]
                if cmd[1:] == k:
                    msg.command = msg.raw[len(k) + 2:].strip()
                    v = self.slashcommands[k](self, msg)
                    if v:
                        self.sendMessage(msg.chat_id, v)
                    return

        self.active = False
        return

    def on_callback_query(self, message: RawTelegramMessage) -> None:
        query_id, from_id, data = telepot.glance(message, flavor='callback_query')
        logging.debug('Callback query: %d %d %s', query_id, from_id, data)

        for identifier, callback in self.callback_query_types.items():
            if data.startswith(identifier):
                callback(self, message)
                return

        logging.error('Unknown callback query: %s', data)

    def on_inline_query(self, msg: RawTelegramMessage) -> None:
        def compute() -> list:
            telepot.glance(msg, flavor='inline_query')
            return []

        self.answerer.answer(msg, compute)

    @staticmethod
    def on_chosen_inline_result(msg: RawTelegramMessage) -> None:
        result_id, from_id, query_string = telepot.glance(msg, flavor='chosen_inline_result')
        logging.info('Chosen Inline Result: %d %d %s', result_id, from_id, query_string)


def patch_telepot() -> None:
    """
    Patch telepot's loop._extract_message function. Without the 'update_id'
    field as a valid message type, bots will break in groups chats.
    See also: https://stackoverflow.com/questions/66796130.
    """
    telepot_message_types = ['message',
                             'edited_message',
                             'channel_post',
                             'edited_channel_post',
                             'callback_query',
                             'inline_query',
                             'chosen_inline_result',
                             'shipping_query',
                             'pre_checkout_query',
                             'update_id']

    def extract_message(update) -> tuple[Any, Any]:  # noqa: ANN001
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
    run()
