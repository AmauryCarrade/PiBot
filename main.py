from pibot import PiBot


bot = PiBot.PiBot("irc.sigpipe.me", "#pi")

bot.debug = True
bot.launch()
