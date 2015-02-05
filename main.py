from pibot.PiBot import PiBot, Hook, event_handler

@event_handler(Hook.CHANNEL_MESSAGE_RECEIVED)
def on_message(ev, bot):
	# do something
	pass


dearBot = PiBot("irc.sigpipe.me", "#pi")

dearBot.debug = True
dearBot.launch()
