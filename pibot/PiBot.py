import socket
import time
from pibot.Network import PiRequestsHandler, PiRequestsReceiver, PiRequestsSender

__author__ = 'amaury'


class PiBot:
    """
    The Pi IRC bot.
    """

    BOT_VERSION = "0.1-dev"

    BUFFER_SIZE = 512

    # Standard codes and commands
    CTCP_CHAR = ''

    def __init__(self, network, port=6667):
        self.network = network
        self.port    = port

        self.debug = False

        self.ping_timeout = 240  # seconds
        self.delay_before_reconnection = 10  # seconds

        self._irc_connection = None     # type: socket
        self._requests_handler = None   # type: PiRequestsHandler
        self._requests_sender = None    # type: PiRequestsSender
        self._requests_receiver = None  # type: PiRequestsReceiver


    # ##  Runner

    def run(self):
        self.log_info("Connecting to the IRC server...")

        self._irc_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._irc_connection.settimeout(15)  # Used to force the loop to loop at least every 15 seconds.
        self._irc_connection.connect((self.network, self.port))

        self._requests_handler = PiRequestsHandler()

        self._requests_receiver = PiRequestsReceiver(connection=self._irc_connection, bot=self)
        self._requests_sender = PiRequestsSender(connection=self._irc_connection, bot=self)

        self._requests_receiver.setDaemon(False)
        self._requests_sender.setDaemon(False)

        self._requests_receiver.start()
        self._requests_sender.start()


    def kill(self):
        self._requests_receiver.interrupt()
        self._requests_sender.interrupt()

    def relaunch(self, delay=0):
        """
        Kill the connection and then reconnects the bot using a new fresh connection,
        after `delay` seconds.

        :param delay: The waiting time between the stop and the restart, in seconds.
        """
        self.kill()

        if delay > 0:
            time.sleep(delay)

        self.run()


    def ping_timeout(self):
        self.log_fatal("Ping timeout! Nothing received from the server since " + str(self.ping_timeout) + " seconds.")
        self.log_info("Retrying in " + str(self.delay_before_reconnection) + " seconds...")

        self.relaunch(delay=self.delay_before_reconnection)



    # ##  Log methods

    def log_fatal(self, error):
        """
        A call to this terminates the bot.
        :param error: The error message to display.
        """
        print("[FATAL] " + error + " Aborting." + "\n")
        self._irc.close()
        self._irc = None

    @staticmethod
    def log_warn(warn):
        """
        A warning message.
        :param warn: The warning message to display.
        """
        print("[WARNING] " + warn + "\n")

    @staticmethod
    def log_info(notice):
        """
        A simple information.
        :param notice: The notice to display.
        """
        print("[INFO] " + notice + "\n")

    def log_debug(self, debug):
        """
        A debug message, printed only if self.debug is set to True.
        :param debug: The debug message to display.
        """
        if self.debug: print("[DEBUG] " + debug + "\n")
