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



class PiBot(object):
	"""
	The Pi IRC bot.
	"""
	
	BOT_VERSION = "0.1-dev"
	
	BUFFER_SIZE = 2048
	CTCP_CHAR = '';
	
	def __init__(self, network, channel, port=6667, nick="PiBot"):
		
		self.network = network
		self.port    = port
		self.channel = channel
		self.nick    = nick
		
		self.debug = False
		
		self._irc = None
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
		
		self._irc.send(_b(raw + '\r\n'))
	
	
	def send_message(self, message, user = None):
		"""
		Sends a message to the user given, or to the channel if user is None.
		"""
		
		if(user == None): user = self.channel
		
		if(self.debug): print("M-> " + message + " (to " + user + ")")
		
		self.raw('PRIVMSG ' + user + ' :' + message)
	
	
	def send_notice(self, message, user = None):
		"""
		Sends a notice to the user given, or to the channel if user is None.
		"""
		
		if(user == None): user = self.channel
		
		if(self.debug): print("N-> " + message + " (to " + user + ")")
		
		self.raw('NOTICE ' + user + ' :' + message)
	
	
	def send_ctcp_answer(self,requestType,  message, user):
		"""
		Sends an answer to a CTCP request.
		"""
		
		self.send_notice(self.CTCP_CHAR + requestType + " " + message + self.CTCP_CHAR, user);
	
	
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
		requestType = request[0].strip().upper()
		
		# Version of the client
		if requestType == "VERSION":
			self.send_ctcp_answer(requestType, "PiBot version " + self.BOT_VERSION + " by AmauryPi", user)
		
		# Current time (timestamp)
		elif requestType == "TIME":
			self.send_ctcp_answer(requestType, str(time.time()), user)
		
		else:
			self.send_ctcp_answer("ERRMSG", "CTCP request '" + requestType + "' not supported.", user)
	
	
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
		
		while self._irc != None:
			
			partial_data = _s(self._irc.recv(self.BUFFER_SIZE))
			
			if(partial_data == ''):
				continue
			
			data += partial_data
			
			if data.endswith("\r\n"):
				transmission_finished = True
			else:
				transmission_finished = False
				continue
			
			try:
				if(self.debug): print("<-- " + data + "\n")
				
				
				# If the pseudonym is already used
				if not self._logged and data.find(self.nick + " :Nickname is already in use") != -1:
					self.nick += "_";
					self.raw('NICK ' + self.nick)
				
					print("Nick in use, trying with " + self.nick + "...")
					continue
			
			
				# Registration
				if not self._logged:
					results = re.search('/quote PONG ([\S]*)', data)
					if results != None and len(results.group(1)) != 0:
						self.raw('PONG ' + results.group(1))
						self._logged = True
				
					continue
			
			
				# Here, we're registered.
			
				# Answer to the PING
				if data.find('PING') != -1:
					self.raw('PONG ' + data.split()[1])
			
				# Join
				if data.find("JOIN :" + self.channel) != -1:
					# We check if the join message is our join message
					user = self._get_user_from_hostmask(data.split(':')[1].split()[0])
					if(user.nick == self.nick and not self._joined):
						self._joined = True
						print("Connected to " + self.channel + ".\n")
				
					#else:
					#	print(user.nick + " joined " + self.channel)
					#	self._users[user.nick] = user
			
				# Our own join
				if not self._joined:
					self.raw('JOIN ' + self.channel)
			
				# Left
				#if data.find('PART ' + self.channel) != -1:
				#	user = self._get_user_from_hostmask(data.split(':')[1].split()[0])
				#	if user.nick in self._users:
				#		print(user.nick + " left " + self.channel)
				#		del self._users[user.nick]
			
				# Messages
				if data.find('PRIVMSG') != -1:
					# Format: ":User!UserHost PRIVMSG receiver :message\r\n"
					# where receiver is the nick of the bot, or the name of the channel the bot is in
					privmsg = data.split(':')
					privmsg_meta = privmsg[1].strip().split()
					user = privmsg_meta[0].split('!')
					message = privmsg[2].strip()
				
					if privmsg_meta[2] == self.channel:
						self.handle_room_message(message, user[0], user[1])
					else:
						self.handle_private_message(message, user[0], user[1])
				
					continue
			
			except Exception as e:
				print("[ERROR] An error occured.");
				print(str(e));
			
			finally:
				# In all cases we need to clear this
				data = ''
			


