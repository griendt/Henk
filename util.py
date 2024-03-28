import datetime
import random
import re
from collections.abc import Sequence

import telepot


def get_current_hour():
    return datetime.datetime.time(datetime.datetime.now()).hour


remove_emoji = re.compile(
    "[" "\U0001f300-\U0001f64f" "\U0001f680-\U0001f6ff" "\u2600-\u26ff\u2700-\u27bf]+",
    re.UNICODE,
)


def normalise(s):  # " Hoi   bla" -> "hoi bla"
    r = s.lower().strip()
    r = remove_emoji.sub("", r)
    r = " ".join(r.split())
    return r


def prepare_query(s):
    r = s.lower().strip().replace(", ", " ").replace("?", "").replace("!", "")
    if r.endswith("."):
        r = r[:-1]
    return r.strip()


def pick(items: Sequence):  # picks random element from list
    return random.sample(items, 1)[0]


def probaccept(p):  # returns True with probability p, otherwise False
    return random.random() < p


class Message(object):
    def __init__(self, msg):
        content_type, chat_type, chat_id = telepot.glance(msg)
        self.content_type = content_type
        self.istext = content_type == "text"
        self.chat_id = chat_id
        self.chat_type = chat_type
        if self.istext:
            self.raw = msg["text"]
            self.normalised = normalise(msg["text"])
            self.command = self.normalised
        else:
            self.raw = ""
            self.normalised = ""
            self.command = ""
        try:
            self.sender = msg["from"]["id"]
            self.sendername = msg["from"]["first_name"]
        except KeyError:
            self.sender = 0
            self.sendername = ""
        self.date = msg["date"]

        self.object = msg
