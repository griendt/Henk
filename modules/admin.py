from henk import Henk
from util import Message
from .base import Module


class Admin(Module):
    def register_commands(self, bot):
        bot.add_slash_command("help", self.help)
        bot.add_slash_command("ping", self.ping)

        bot.add_command_category("whatcanyoudo", self.help)

    @staticmethod
    def help(bot: Henk, msg: Message):
        return "Ik ben Ingrid, en ik ben een beetje verlegen. Daarom sta ik standaard in stille modus. Je kan alleen met mij klaverjassen."

    @staticmethod
    def ping(bot: Henk, msg: Message):
        return "pong"


admin = Admin()
