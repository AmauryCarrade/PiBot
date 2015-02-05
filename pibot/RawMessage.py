class RawMessage(object):
	"""
	Represents a request received from the server

	self.hostmask : hostmask
	self.command : command
	self.args : list of arguments
	"""

	def __init__(self, data):
		"""
		data: the raw message received from the server.
			  Format: ":{prefix} {command}[ {parameters}]\r\n"
			  Where parameters is a list of words separated by some spaces; the last
			  parameter can contain spaces but with a ":" before.
		"""

		try:
			request = data.split()

			self.hostmask = request[0].split(":")[1]
			self.command  = request[1]
			self.args = []

			# Used to see if we need to add an argument or to append the arguments to the last one.
			current_last_arg = False
			if len(request) > 2:
				for i in range(2, len(request)):
					if not current_last_arg and not request[i].startswith(":"):
						self.args.append(request[i])

					elif request[i].startswith(":"):
						current_last_arg = True
						self.args.append(request[i][1:])

					else:
						self.args[len(self.args) - 1] += " " + request[i]
		except IndexError:
			# Cannot parse request - invalid format, but sometime used (example, SASL authentication).
			self.hostmask = ""
			self.command = ""
			self.args = []