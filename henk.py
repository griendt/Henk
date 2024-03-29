#!/usr/bin/python3
# coding=latin-1
"""
Henkbot 2017
Should be run in at least Python 3.5 (3.4 maybe works as well)
Dependencies: telepot, simpleeval, dataset, textblob, unidecode
Install these with "pip install libname" and for textblob additionally call python -m textblob.download_corpora

"""

import random
import threading
import time
from collections import OrderedDict
from typing import Any

import telepot
import urllib3
from telepot.loop import MessageLoop

import modules
from managedata import ManageData
from util import Message


class Henk:
    MAX_MESSAGE_LENGTH = 4096  # as specified in https://limits.tginfo.me/en

    commands: list
    responses: list
    sendername: Any
    slashcommands: OrderedDict
    callback_query_types: OrderedDict

    def __init__(self, bot: telepot.Bot, is_dummy=False):
        self.telebot = bot  # the bot interface for Telegram
        self.dataManager = ManageData()  # interface to the database
        self.dataManager.dummy = is_dummy
        self.should_exit = False
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
            print('Chat:', msg.content_type, msg.chat_type, msg.chat_id)
            self.active = False
            return

        self.dataManager.write_message(msg.object)
        self.sendername = msg.sendername
        try:
            print('Chat:', msg.chat_type, msg.chat_id, msg.normalised)
        except UnicodeDecodeError:
            print('Chat:', msg.chat_type, msg.chat_id, msg.normalised.encode('utf-8'))

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

    def on_callback_query(self, msg):
        query_id, from_id, data = telepot.glance(msg, flavor='callback_query')
        print('Callback query:', query_id, from_id, data)
        for ident, callback in self.callback_query_types.items():
            if data.startswith(ident):
                callback(self, msg)
                return
        print('Unkown callback query: %s' % data)

    def on_inline_query(self, msg) -> None:
        def compute():
            telepot.glance(msg, flavor='inline_query')
            return []

        answerer.answer(msg, compute)

    def on_chosen_inline_result(self, msg):
        result_id, from_id, query_string = telepot.glance(msg, flavor='chosen_inline_result')
        print('Chosen Inline Result:', result_id, from_id, query_string)


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


if __name__ == '__main__':
    f = open('apikey.txt')
    TOKEN = f.read()  # token for Henk
    f.close()

    PPA = -218118195  # Henk's fun palace
    ADMIN = 19620232  # John

    telebot = telepot.Bot(TOKEN)
    answerer = telepot.helper.Answerer(telebot)
    henk = None

    try:
        patch_telepot()
        henk = Henk(telebot)
        MessageLoop(
            telebot,
            {
                'chat': henk.on_chat_message,
                'callback_query': henk.on_callback_query,
                'inline_query': henk.on_inline_query,
                'chosen_inline_result': henk.on_chosen_inline_result,
            },
        ).run_as_thread()
        print('Listening ...')

        # Keep the program running.
        while True:
            try:
                if henk.should_exit:
                    break
                time.sleep(1)
            except ConnectionResetError:
                print('ConnectionResetError')
            except urllib3.exceptions.ProtocolError:
                print('ProtocolError')
    except KeyboardInterrupt:
        pass
