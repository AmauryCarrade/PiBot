from pibot import PiBot

@PiBot.event_handler(PiBot.Hook.MESSAGE_RECEIVED)
def test(ev, bot):
	bot.send_message("HONK " + ev.message)


dearBot = PiBot.PiBot("irc.sigpipe.me", "#pi")

dearBot.debug = True
dearBot.launch()
