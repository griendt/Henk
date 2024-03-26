from henk import Henk
from util import Message
from .base import Module


class Admin(Module):
    def register_commands(self, bot):
        bot.add_slash_command("help", self.help)
        bot.add_slash_command("ping", self.ping)

    @staticmethod
    def help(bot: Henk, message: Message) -> str:
        return (
            "Ik ben Ingrid, en ik ben een beetje verlegen. Daarom sta ik standaard in stille modus. Je kan alleen met mij klaverjassen. "
            "Mijn commands zijn: \n/"
            + "\n/".join(bot.slashcommands.keys())
        )

    @staticmethod
    def ping(bot: Henk, message: Message) -> str:
        return "pong"


admin = Admin()
