from .Hook import *

# Stores the addons.
_addons = dict()

for the_hook in Hook:
	_addons[the_hook] = set()


def event_handler(hook):
	"""
	Registers a function as an event handler for the Pi IRC Bot.
	The function needs to accept a single argument, an Event class containing attributes with some data
	about the event received.
	See the Hook enum for a list of these arguments per hook.

	:param hook: The hook this function will watch for.
	"""
	def decorator(handler):
		"""
		:param handler: function
		"""

		# The event handler is registered
		_addons[hook].add(handler)

		def wrapper(ev, bot):
			"""
			:param ev: An Event object.
			:param bot: The bot (PiBot object) who called this function.
			:return:
			"""
			return handler(ev, bot)

		return wrapper

	return decorator

def call_event(hook, event, bot):
	"""
	Calls all the functions registered for the given hook, passing the same event object to all these functions.

	:param hook: The hook.
	:param event: The Event object.
	:param bot: The bot.
	:return:
	"""
	for function in _addons[hook]:
		function(event, bot)
