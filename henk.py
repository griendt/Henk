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
from util import Message, get_current_hour, probaccept


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

        self.querycounts = {}  # counts how many times I've said a thing lately
        self.lastupdate = 0  # how long it has been since I've updated querycounts
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
        if probaccept(0.7):
            self.active = True
        else:
            self.active = False
        return m

    def pick(self, options):
        return random.sample(options, 1)[0].replace('!name', self.sendername)

    def update_querycounts(self, amount):
        for q in self.querycounts:
            self.querycounts[q] = max([0, self.querycounts[q] - amount])

    def react_to_query(self, q):
        """Determine whether we will react to this specific query based on if we did so previously, to prevent spam"""
        i = self.aliasdict[q]
        if i not in self.querycounts:
            self.querycounts[i] = 0
        if (
            q.find('ingrid') != -1
            or (self.active and probaccept(2 ** -(max([self.querycounts[i] - 3, 0]))))
            or probaccept(2 ** -(max([self.querycounts[i] - 1, 0])))
        ):
            self.querycounts[i] += 1
            self.active = True
            return True
        return False

    def on_chat_message(self, message):
        msg = Message(message)
        if not msg.istext:
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
                    msg.command = msg.raw[len(k) + 2 :].strip()
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

    def on_inline_query(self, msg):
        def compute():
            telepot.glance(msg, flavor='inline_query')
            return []

        answerer.answer(msg, compute)

    def on_chosen_inline_result(self, msg):
        result_id, from_id, query_string = telepot.glance(msg, flavor='chosen_inline_result')
        print('Chosen Inline Result:', result_id, from_id, query_string)


if __name__ == '__main__':
    f = open('apikey.txt')
    TOKEN = f.read()  # token for Henk
    f.close()

    # PPA = -6722364 #hardcoded label for party pownies
    PPA = -218118195  # Henk's fun palace

    ADMIN = 19620232  # John

    telebot = telepot.Bot(TOKEN)
    answerer = telepot.helper.Answerer(telebot)
    henk = None

    try:
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

        silent = False

        h = get_current_hour()
        # if not silent:
        #    if h>6 and h<13:
        #        telebot.sendMessage(PPA,"Goedemorgen")
        #    elif h>12 and h<19:
        #        telebot.sendMessage(PPA,"Goedemiddag")
        #    else:
        #       telebot.sendMessage(PPA,"Goedeavond")

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
    finally:
        if henk and not henk.should_exit:
            telebot.sendMessage(PPA, 'Ik ga even slapen nu. doei doei')
