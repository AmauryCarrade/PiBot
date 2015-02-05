from enum import Enum

class Hook(Enum):
	"""
	Represents the hooks a plugin can listen.
	"""

	# Fired when a raw message is received.
	RAW_MESSAGE_RECEIVED = "hook.received.raw_message"

	# Fired when a message is sent into the channel watched by this bot.
	CHANNEL_MESSAGE_RECEIVED = "hook.received.channel_message"

	# Fired when a private message is sent to the bot.
	PRIVATE_MESSAGE_RECEIVED = "hook.received.private_message"

	# Fired when the bot receive a message either from the channel or a specific user (private message).
	# Do not fires for CTCP requests.
	MESSAGE_RECEIVED = "hook.received.message"

	# Fired when a CTCP request is received.
	CTCP_REQUEST_RECEIVED = "hook.received.ctcp_request"
