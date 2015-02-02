from pibot import PiBot


bot = PiBot.PiBot("irc.sigpipe.me", "#zcraft")

bot.debug = True
bot.launch()
