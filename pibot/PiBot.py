import socket
import time
import re


def _b(data):
	"""
	Converts data to something that can be used by a buffer (some bytes).
	"""
	return bytes(data, 'UTF-8');

def _s(data):
	"""
	Converts bytes to a string
	"""
	return str(data, 'UTF-8');



class User(object):
	"""
	Represents an user connected to the channel.
	"""
	
	def __init__(self, nick, user, host):
		self.nick = nick
		self.user = user
		self.host = host


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
			  Where parameters is a list of words separated by some spaces; the last parameter can be composed by spaces but with
			  a ":" before.
		"""
		
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
		

class PiBot(object):
	"""
	The Pi IRC bot.
	"""
	
	BOT_VERSION = "0.1-dev"
	
	BUFFER_SIZE = 512
	
	# Standard codes and commands
	CTCP_CHAR = ''

	COMMAND_ERR_NONICKNAMEGIVEN = "431"
	COMMAND_ERR_ERRONEUSNICKNAME = "432"
	COMMAND_ERR_NICKNAMEINUSE = "433"
	COMMAND_ERR_NICKCOLLISION = "436"

	COMMAND_ERR_ALREADYREGISTRED = "462"

	def __init__(self, network, channel, port=6667, nick="PiBot"):
		
		self.network = network
		self.port    = port
		self.channel = channel
		self.nick    = nick
		
		self.debug = False
		
		self._irc = None
		self._nick_set = False
		self._logged = False
		self._joined = False
		
		self._users = {}
	
	
	def _get_user_from_hostmask(self, hostmask):
		"""
		Returns an User object from the given hostmask.
		
		Returns the User stored in self._users if this user is in the
		channel watched by this bot, or a new User object if not.
		"""
		
		# Hostmask format: nick!user@host
		nick, hostname = hostmask.split('!')
		user, host = hostname.split('@')
		
		if nick in self._users:
			return self._users[nick]
		else:
			return User(nick, user, host)
	
	
	def raw(self, raw):
		"""
		Sends a raw message to the IRC server.
		raw: string.
		"""
		
		if self.debug : print("--> " + raw + "\n")
		self._irc.send(_b(raw + '\r\n'))
	
	
	def send_message(self, message, user = None):
		"""
		Sends a message to the user given, or to the channel if user is None.
		"""
		
		if user is None : user = self.channel
		
		self.raw('PRIVMSG ' + user + ' :' + message)
	
	
	def send_notice(self, message, user = None):
		"""
		Sends a notice to the user given, or to the channel if user is None.
		"""
		
		if user is None : user = self.channel
		
		self.raw('NOTICE ' + user + ' :' + message)
	
	
	def send_ctcp_answer(self, request_type,  message, user):
		"""
		Sends an answer to a CTCP request.
		"""
		
		self.send_notice(self.CTCP_CHAR + request_type + " " + message + self.CTCP_CHAR, user)
	
	
	def handle_private_message(self, message, user, user_host):
		"""
		Handles a private message received by the bot.
		CTCP requests are redirected from here to the self.handle_ctcp_request method.
		
		message: the message.
		user: the user who sent this message.
		user_host: the host of the user.
		"""
		
		# CTCP requests
		if message.startswith(self.CTCP_CHAR) and message.endswith(self.CTCP_CHAR):
			self.handle_ctcp_request(message.strip(self.CTCP_CHAR), user, user_host)
	
	
	def handle_ctcp_request(self, request, user, user_host):
		"""
		Handles a Client-To-Client-Protocol request.
		
		message: the message.
		user: the user who sent this message.
		user_host: the host of the user.
		"""
		print("[Notice] CTCP request received from " + user + ": " + request + "\n")
		
		request = request.split()
		request_type = request[0].strip().upper()
		
		# Version of the client
		if request_type == "VERSION":
			self.send_ctcp_answer(request_type, "PiBot version " + self.BOT_VERSION + " by AmauryPi", user)
		
		# Current time (timestamp)
		elif request_type == "TIME" or request_type == "PING":
			self.send_ctcp_answer(request_type, str(int(time.time() * 1000)), user)
		
		else:
			self.send_ctcp_answer("ERRMSG", "CTCP request '" + request_type + "' not supported.", user)
	
	
	def handle_room_message(self, message, user, user_host):
		"""
		Handles a channel message received by the bot.
		
		message: the message.
		user: the user who sent this message.
		user_host: the host of the user.
		"""

		pass
	
	
	def launch(self):
		"""
		Starts the bot.
		Connects it to the server, and starts the main loop.
		"""
		
		self._irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self._irc.connect((self.network, self.port))
		
		print("Connecting to the IRC server...\n")
		
		self.raw('NICK ' + self.nick)
		self.raw('USER ' + self.nick + ' ' + self.nick + ' ' + self.nick + ' ' + ':A Pi-powered IRC bot')
		
		
		# A sequence of data may be sent in more than one time. This is used to store the current line.
		# A line ends with "\r\n".
		data = ''
		transmission_finished = False
		
		while self._irc is not None:
			
			partial_data = _s(self._irc.recv(self.BUFFER_SIZE))
			
			if partial_data == '':
				continue
			
			data += partial_data
			
			if data.endswith("\r\n"):
				transmission_finished = True
			else:
				transmission_finished = False
				continue
			
			try:
				if self.debug: print("<-- " + data)

					
				# Ping pong (special format)
				if data.startswith("PING "):
					self.raw('PONG ' + data.split()[1])
					continue
				
				
				raw = RawMessage(data)
				
				print("[RAW] [COMMAND " + raw.command + "] [PARAMS " + str(raw.args) + "]")


				if raw.command == self.COMMAND_ERR_ALREADYREGISTRED:
					print("[FATAL] User already registered! Aborting.")

					self._irc = None
					continue

				
				if not self._nick_set:
					# If the pseudonym is already used
					if raw.command == self.COMMAND_ERR_NICKNAMEINUSE:
						self.nick += "_"
						self.raw('NICK ' + self.nick)

						print("Nick in use, trying with " + self.nick + "...")
						continue

					# If the pseudonym is invalid
					elif raw.command == self.COMMAND_ERR_ERRONEUSNICKNAME:
						print("[FATAL] " + self.nick + ": invalid nickname! Aborting.")

						self._irc = None
						continue

					# If the server considers the pseudonym as empty
					elif raw.command == self.COMMAND_ERR_NONICKNAMEGIVEN:
						print("[FATAL] No nickname given! Aborting.")

						self._irc = None
						continue

					# If the server refused the connexion due to a nick conflict
					elif raw.command == self.COMMAND_ERR_NICKCOLLISION:
						print("[FATAL] The server answered with a NICKCOLLISION error. Aborting.")

						self._irc = None
						continue

				# If we are here, the nick was correctly set.
				self._nick_set = True

				# Join
				if raw.command == "JOIN" and raw.args[0] == self.channel:
					# We check if the join message is our join message
					user = self._get_user_from_hostmask(raw.hostmask)
					if user.nick == self.nick and not self._joined:
						self._joined = True
						print("Connected to " + self.channel + ".\n")

					#else:
					#	print(user.nick + " joined " + self.channel)
					#	self._users[user.nick] = user


				if not self._joined:
					self.raw('JOIN ' + self.channel)

				# Left
				#if data.find('PART ' + self.channel) != -1:
				#	user = self._get_user_from_hostmask(data.split(':')[1].split()[0])
				#	if user.nick in self._users:
				#		print(user.nick + " left " + self.channel)
				#		del self._users[user.nick]
			
				# Messages
				if raw.command == "PRIVMSG":
					user     = raw.hostmask.split('!')
					receiver = raw.args[0]
					message  = raw.args[1]

					if receiver == self.channel:
						self.handle_room_message(message, user[0], user[1])
					else:
						self.handle_private_message(message, user[0], user[1])

					continue
			
			except Exception as e:
				print("[ERROR] An error occurred.")
				print(repr(e))
			
			finally:
				# In all cases, if the transmission is finished, we need to clear this
				if transmission_finished:
					data = ''
			


