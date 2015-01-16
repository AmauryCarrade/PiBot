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

class PiBot(object):
	"""
	The Pi IRC bot.
	"""
	
	BOT_VERSION = "0.1-dev"
	
	BUFFER_SIZE = 2048
	
	def __init__(self, network, channel, port=6667, nick="PiBot"):
		
		self.network = network
		self.port    = port
		self.channel = channel
		self.nick    = nick
		
		self.debug = True
		
		self._irc = None
		self._logged = False
		self._joined = False
		
		self._users = []
	
	
	def send_message(self, message, user = None):
		"""
		Sends a message to the user given, or to the channel if user is None.
		"""
		
		if(user == None):
			self._irc.send(_b('PRIVMSG ' + self.channel + ' :' + message + '\r\n'))
		else:
			self._irc.send_(b('PRIVMSG ' + user + ' :' + message + '\r\n'))
	
	
	def handle_private_message(self, message, user, user_host):
		"""
		Handles a private message received by the bot. Includes CTCP requests.
		
		message: the message.
		user: the user who sent this message.
		user_host: the host of the user.
		"""
		
		pass
	
	
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
		
		self._irc.send(_b('NICK ' + self.nick + '\r\n'))
		self._irc.send(_b('USER ' + self.nick + ' ' + self.nick + ' ' + self.nick + ' ' + ':A Pi-powered IRC bot\r\n'))
		
		
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
			
			
			if(self.debug): print(data + "\n")
			
			
			# Authentification
			if not self._logged:
				results = re.search('/quote PONG ([\S]*)', data)
				if results != None and len(results.group(1)) != 0:
					self._irc.send(_b('PONG ' + results.group(1) + '\r\n'))
					self._logged = True
				
				continue
			
			
			# Here, we're registered.
			
			# Answer to the PING
			if data.find('PING') != -1:
				self._irc.send(_b('PONG ' + data.split()[1] + '\r\n'))
			
			# Join
			if not self._joined:
				if data.find("JOIN :" + self.channel) != -1:
					self._joined = True
					print("Connected to " + self.channel + ".\n")
				else:
					self._irc.send(_b('JOIN ' + self.channel + '\r\n'))
			
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
				
			
			if transmission_finished:
				data = ''
			


