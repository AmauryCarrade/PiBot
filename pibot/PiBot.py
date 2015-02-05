import base64
import socket
import time

from .Event import *
from .User import *
from .RawMessage import *
from .Commands import *
from .EventsManager import *

__all__ = ['PiBot', 'Commands', 'RawMessage', 'User', 'event_handler', 'Event', 'Hook']


def _b(data):
	"""
	Converts data to something that can be used by a buffer (some bytes).
	"""
	return bytes(data, 'UTF-8')

def _s(data):
	"""
	Converts bytes to a string
	"""
	return str(data, 'UTF-8')



class AuthMethod(Enum):
	"""
	Represents the authentication method used to login to IRC services.
	"""
	Nothing = 0
	NickServ = 1
	SASL = 2


class PiBot(object):
	"""
	The Pi IRC bot.
	"""
	
	BOT_VERSION = "0.1-dev"
	
	BUFFER_SIZE = 512
	
	# Standard codes and commands
	CTCP_CHAR = ''

	def __init__(self, network, channel, port=6667, nick="PiBot", channel_password=""):
		
		self.network = network
		self.port    = port
		self.channel = channel
		self.nick    = nick

		self.channel_password = channel_password

		self.debug = False

		self._irc      = None
		self._logged   = False
		self._joined   = False

		self.auth_method = AuthMethod.Nothing
		self.auth_username = ""
		self.auth_password = ""
		self.nickserv_username = "NickServ"

		self._sasl_auth_type_exposed  = False
		self._sasl_auth_type_accepted = False

		# Set to true when the MOTD has been received (first notice).
		# Before, trying to send JOIN or other AUTHENTICATE commands is useless.
		self._can_send_commands = False

		self._users = set()


	### Log methods

	def _fatal(self, error):
		"""
		A call to this terminates the bot.
		"""
		print("[FATAL] " + error + " Aborting." + "\n")
		self._irc = None

	def _warn(self, warn):
		"""
		A warning message.
		"""
		print("[WARNING] " + warn + "\n")

	def _info(self, notice):
		"""
		A simple information.
		"""
		print("[INFO] " + notice + "\n")

	def _debug(self, debug):
		"""
		A debug message, printed only if self.debug is set to True.
		"""
		if self.debug: print("[DEBUG] " + debug + "\n")



	def _get_user_from_hostmask(self, hostmask):
		"""
		Returns an User object from the given hostmask.
		
		Returns the User stored in self._users if this user is in the
		channel watched by this bot, or a new User object if not.
		"""
		
		# Hostmask format: nick!user@host
		nick, hostname = hostmask.split('!')
		user, host = hostname.split('@')

		for channel_user in self._users:
			if channel_user.nick == nick and channel_user.user == user and channel_user.host == host:
				return channel_user

		return User(nick, user, host)
	
	
	def raw(self, raw):
		"""
		Sends a raw message to the IRC server.
		raw: string.
		"""
		
		self._debug("--> " + raw + "\n")
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

		# Normal private messages
		else:
			event = Event()
			event.message = message
			event.user = user

			call_event(Hook.PRIVATE_MESSAGE_RECEIVED, event, self)
			call_event(Hook.MESSAGE_RECEIVED, event, self)
	
	
	def handle_ctcp_request(self, request, user, user_host):
		"""
		Handles a Client-To-Client-Protocol request.

		message: the message.
		user: the user who sent this message.
		user_host: the host of the user.
		"""
		self._info("CTCP request received from " + user + ": " + request)

		request = request.split()
		request_type = request[0].strip().upper()

		answer = ""
		answer_type = request_type
		
		# Version of the client
		if request_type == "VERSION":
			answer = "PiBot version " + self.BOT_VERSION + " by AmauryPi. " \
			         "Source code available on GitHub: https://github.com/AmauryCarrade/PiBot"
		
		# Current time (timestamp)
		elif request_type == "TIME" or request_type == "PING":
			answer = str(int(time.time() * 1000))
		
		else:
			answer = "CTCP request '" + request_type + "' not supported."
			answer_type = "ERRMSG"

		event = Event()
		event.request_type = request_type
		event.answer = answer
		event.answer_type = answer_type

		call_event(Hook.CTCP_REQUEST_RECEIVED, event, self)

		if answer is not None:
			self.send_ctcp_answer(event.answer_type, event.answer, user)
	
	def handle_room_message(self, message, user, user_host):
		"""
		Handles a channel message received by the bot.
		
		message: the message.
		channel_user: the channel_user who sent this message.
		user_host: the host of the channel_user.
		"""
		event = Event()
		event.message = message
		event.user = user

		call_event(Hook.CHANNEL_MESSAGE_RECEIVED, event, self)
		call_event(Hook.MESSAGE_RECEIVED, event, self)
	
	
	def launch(self):
		"""
		Starts the bot.
		Connects it to the server, and starts the main loop.
		"""

		if self.auth_username == "":
			self.auth_username = self.nick

		self._irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self._irc.connect((self.network, self.port))
		
		self._info("Connecting to the IRC server...\n")

		if self.auth_method == AuthMethod.SASL:
			self.raw("CAP LS")

		self.raw(Commands.NICK_COMMAND + ' ' + self.nick)
		self.raw(Commands.USER_COMMAND + ' ' + self.nick + ' ' + self.nick + ' ' + self.nick + ' ' + ':A Pi-powered IRC bot')
		
		
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
				self._debug("<-- " + data)

					
				# Ping pong (special format)
				if data.startswith("PING "):
					self.raw('PONG ' + data.split()[1])
					continue
				
				
				raw = RawMessage(data)

				event = Event()
				event.raw = raw
				call_event(Hook.RAW_MESSAGE_RECEIVED, event, self)


				#self._debug("[RAW] [COMMAND " + raw.command + "] [PARAMS " + str(raw.args) + "]")


				if raw.command == Commands.AUTH_ERR_ALREADYREGISTRED:
					self._fatal("User already registered!")
					continue


				### Authentication with SASL

				if self.auth_method == AuthMethod.SASL and not self._logged:
					if raw.command == "CAP":
						if raw.args[1] == "LS":
							self.raw("CAP REQ :sasl")
						elif raw.args[2] == "sasl":
							self.raw("AUTHENTICATE PLAIN")

					elif data.startswith("AUTHENTICATE +"):
						auth_string = base64.b64encode(_b(self.nick + '\0' + self.nick + '\0' + self.auth_password))
						self.raw("AUTHENTICATE " + _s(auth_string))

					elif raw.command == Commands.SASL_RPL_SASLSUCCESS:
						self._info("SASL authentication successful - the bot is now logged in.")

					elif raw.command == Commands.SASL_ERR_SASLFAIL:
						self._fatal("SASL authentication failed - cannot authenticate.")

					elif raw.command == Commands.SASL_ERR_SASLTOOLONG:
						self._fatal("SASL authentication failed (too long) - cannot authenticate.")

					elif raw.command == Commands.SASL_ERR_SASLABORTED:
						self._warn("SASL authentication aborted.")

					elif raw.command == Commands.SASL_ERR_SASLALREADY:
						self._warn("SASL authentication failed - you are already logged in.")

				### Nick-related checks

				# If the pseudonym is already used
				if raw.command == Commands.NICK_ERR_NICKNAMEINUSE:
					self.nick += "_"
					self.raw(Commands.NICK_COMMAND + ' ' + self.nick)

					self._warn("Nick already used, trying with " + self.nick + "...")
					continue

				# If the pseudonym is invalid
				elif raw.command == Commands.NICK_ERR_ERRONEUSNICKNAME:
					self._fatal(self.nick + ": invalid nickname!")
					continue

				# If the server considers the pseudonym as empty
				elif raw.command == Commands.NICK_ERR_NONICKNAMEGIVEN:
					self._fatal("No nickname given!")
					continue

				# If the server refused the connexion due to a nick conflict
				elif raw.command == Commands.NICK_ERR_NICKCOLLISION:
					self._fatal("The server answered with a NICKCOLLISION error.")
					continue


				# Join
				if not self._joined:

					if raw.command == Commands.JOIN_ERR_NOSUCHCHANNEL:
						self._fatal("Unable to join " + self.channel + ": the channel doesn't exists.")
						continue

					elif raw.command == Commands.JOIN_ERR_CHANNELISFULL:
						self._fatal("Unable to join " + self.channel + ": this channel is full.")
						continue

					elif raw.command == Commands.JOIN_ERR_INVITEONLYCHAN:
						self._fatal("Unable to join " + self.channel + ": you are not invited to this channel.")
						continue

					elif raw.command == Commands.JOIN_ERR_BANNEDFROMCHAN:
						self._fatal("Unable to join " + self.channel + ": you are banned from this channel!")
						continue

					elif raw.command == Commands.JOIN_ERR_BADCHANNELKEY:
						self._fatal("Unable to join " + self.channel + ": a password is required; the password given is empty or invalid.")
						continue

					elif raw.command == Commands.JOIN_COMMAND and raw.args[0] == self.channel:
						# We check if the join message is our join message
						user = self._get_user_from_hostmask(raw.hostmask)
						if user.nick == self.nick and not self._joined:
							self._joined = True
							self._info("Connected to " + self.channel + ".")

							# We want to list the users connected to our channel
							self.raw(Commands.WHO_COMMAND + ' ' + self.channel)

							# We authenticate, if needed. Here, we are sure we can do it.
							if self.auth_method == AuthMethod.NickServ:
								self.send_message(Commands.NICKSERV_IDENTIFY_COMMAND + ' ' + self.auth_password, self.nickserv_username)

							continue


					if not self._joined:
						self.raw(Commands.JOIN_COMMAND + ' ' + self.channel + " " + self.channel_password)


				# The results of the "WHO channel" command
				if raw.command == Commands.WHO_RPL_WHOREPLY:
					raw_args = ""
					for arg in raw.args:
						raw_args += arg + " "

					args_words = raw_args.split()

					# The informations needed for each user are just after the channel in the WHO reply
					# format.
					for i in range(len(args_words)):
						if args_words[i] == self.channel and args_words[i - 2] != Commands.WHO_RPL_ENDOFWHO:
							user = args_words[i + 1]
							host = args_words[i + 2]
							nick = args_words[i + 4]

							user = self._get_user_from_hostmask(nick + "!" + user + "@" + host)
							self._users.add(user)

							i += 4
						else:
							continue


				# The result of the authentication process through NickServ
				if self.auth_method == AuthMethod.NickServ:
					if raw.command == Commands.NICKSERV_ERR_NICKLOCKED:
						self._warn("The nick " + self.nick + " is currently locked - cannot authenticate.")
					elif raw.command == Commands.NICKSERV_RPL_LOGGEDIN:
						self._info("The bot is now logged in.")
					elif raw.command == Commands.NICKSERV_RPL_LOGGEDOUT:
						self._info("The bot is now logged out.")




				# Join/leave messages (from other users)
				if raw.command == Commands.JOIN_COMMAND and raw.args[0] == self.channel:
					user = self._get_user_from_hostmask(raw.hostmask)

					if user.nick != self.nick:
						self._users.add(user)

						self._info(user.nick + " joined the channel.")

				if (raw.command == Commands.PART_COMMAND and raw.args[0] == self.channel) or raw.command == Commands.QUIT_COMMAND:
					user = self._get_user_from_hostmask(raw.hostmask)

					if user.nick != self.nick and user in self._users:
						self._users.remove(user)

						self._info(user.nick + " left the channel.")


			
				# Messages
				if raw.command == Commands.PRIVMSG_COMMAND:
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
