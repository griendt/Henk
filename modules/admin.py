from henk import Henk
from util import Message
from .base import Module
import longstrings

class Admin(Module):
    def register_commands(self,bot):
        bot.add_slash_command("help", self.help)
        bot.add_slash_command("learnhelp", self.learnhelp)
        bot.add_slash_command("say ", self.say)
        bot.add_slash_command("reload", self.reload)
        bot.add_slash_command("setsilent", self.setsilent)
        bot.add_slash_command("quit", self.quit)

        bot.add_command_category("whatcanyoudo", self.help)
        bot.add_command_category("howdoyoulearn", self.learnhelp)


    def help(self, bot, msg):
        if msg.chat_id in bot.silentchats:
            return longstrings.helpsilent
        else: return  longstrings.helptext
    
    def learnhelp(self, bot, msg):
        return longstrings.learnhelp
    
    def say(self, bot, msg):
        if msg.sender in bot.admin_ids:
            bot.sendMessage(bot.homegroup, msg.raw[4:])
        return

    def quit(self, bot, msg):
        if msg.sender in bot.admin_ids:
            bot.should_exit = True
            return "Quitting"

    def reload(self, bot, msg):
        if msg.sender in bot.admin_ids:
            bot.load_files()
            return "reloading files"
        else:
            return "I'm afraid I can't let you do that"

    def setsilent(self, bot: Henk, msg: Message) -> str:
        return "Ik ben een lieve, stille bot."


admin = Admin()