from enum import Enum

class Hook(Enum):
	"""
	Represents the hooks a plugin can listen to.
	"""

	# Fired when a raw message is received.
	RAW_MESSAGE_RECEIVED = "hook.received.raw"

	# Fired when a message is sent into the channel watched by this bot.
	CHANNEL_MESSAGE_RECEIVED = "hook.received.channel"

	# Fired when a private message is sent to the bot.
	PRIVATE_MESSAGE_RECEIVED = "hook.received.private"

	# Fired when the bot receive a message either from the channel or a specific user (private message).
	# Do not fires for CTCP requests.
	MESSAGE_RECEIVED = "hook.received.message"

	# Fired when a CTCP request is received.
	CTCP_REQUEST_RECEIVED = "hook.received.ctcp_request"

	# Fired when a raw message is sent to the IRC server.
	RAW_MESSAGE_SENT = "hook.sent.raw"

	# Fired when a message is sent to the channel.
	CHANNEL_MESSAGE_SENT = "hook.sent.channel"

	# Fired when a private message is sent.
	PRIVATE_MESSAGE_SENT = "hook.sent.private"

	# Fired when the boot fires a message either to the channel or a specific user (private message).
	MESSAGE_SENT = "hook.sent.message"

	# Fired when a notice is sent.
	NOTICE_SENT = "hook.sent.notice"
