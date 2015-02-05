import uuid

class User(object):
	"""
	Represents an user connected to the channel.
	"""

	def __init__(self, nick, user, host):
		self.nick = nick
		self.user = user
		self.host = host

		self.uuid = uuid.uuid4()

	def __hash__(self):
		return int(self.uuid)

	def __eq__(self, other):
		if not isinstance(other, self.__class__):
			return False

		return self.nick == other.nick and self.user == other.user and self.host == other.host