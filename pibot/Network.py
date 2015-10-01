import socket
import time
import re
from threading import Thread
from queue import Queue


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


requests_queue = Queue()



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

            self.raw = data

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



class PiRequest(object):
    """
    Represents a request made to the IRC client.
    """

    def __init__(self, request: str, expected_answers: set=None, callback=None):
        """
        :param request:
            The raw request to be sent to the IRC server.

        :param expected_answers:
            A set of either regexps or response codes to filter the messages received by the
            client.

            For each item, if it match exactly the command name (number or string like "JOIN"),
            it is transmitted; else, the response is checked against the item, using it as a regexp.
            Only messages matching at least one of the set's items are sent to the callback until the
            request has been marked as closed.

            If this set is empty or (None), all incoming messages are sent to the callback function
            (until closed).

        :param callback:
            The callback called when an incoming message matches an item of the expected_answers set.
            This callback may be called multiple times.

            The arguments received are (ordered):
             - the message received by the client from the IRC server (RawMessage);
             - the instance of the request (use this to call the close method) (instance of this class).

            If this is None, the request will be sent then forgotten.
        """

        if expected_answers is None:
            expected_answers = {}

        self.request = request
        self.expected_answers = expected_answers
        self.callback = callback

        self.opened = False

        self.bot = None

    def open(self, bot):
        """
        Opens the request using the given IRC bot.
        """
        self.bot = bot
        self.bot._requests_handler.register_request(self)

    def _call_callback(self, message: RawMessage):
        """
        Calls the... callback.
        """
        if self.callback is not None:
            self.callback(message, self)

    def close(self):
        """
        Closes this IRC request. The callback will no longer receive any
        matching incoming message from the IRC server.
        """
        if self.bot is not None:
            self.bot._requests_handler.close_request(self)



class PiRequestsHandler:

    def __init__(self):
        self.ongoing_requests = []

    def register_request(self, request: PiRequest):
        # Registers the ongoing request, used by the PiRequestReceiver
        if request.callback is not None:
            self.ongoing_requests.append(request)
        else:
            request.opened = False

        # Register the request to the server, used by the PiRequestsSender
        requests_queue.put(request.request)

    def close_request(self, request: PiRequest):
        request.opened = False
        self.ongoing_requests.remove(request)



# noinspection PyProtectedMember
class PiRequestsReceiver(Thread):
    """
    The lowest-level of connection to the IRC server, receiving the requests.
    """

    BUFFER_SIZE = 512

    def __init__(self, connection: socket, bot):
        """
        IRC client constructor.

        :param connection: The socket opened to the IRC server.
        :param bot: The bot's main class.
        """

        Thread.__init__(self, name="PiIRCBot_RequestsReceiver")

        self._connection = connection
        self._bot = bot

    def interrupt(self):
        """
        Kills the requests receiver thread.
        """
        self._connection = None

    def run(self):

        data = ''
        last_successful_reception = time.time()

        while self._connection is not None:
            try:
                partial_data = _s(self._connection.recv(self.BUFFER_SIZE))
            except socket.timeout:
                if time.time() - last_successful_reception > self._bot.ping_timeout:
                    self._bot.ping_timeout()
                    return

                continue

            if partial_data == '':
                continue

            data += partial_data
            last_successful_reception = time.time()

            if not data.endswith("\r\n"):
                continue

            try:
                raw = RawMessage(data.rstrip())

                self._bot.log_debug("« " + raw.raw)

                for request in self._bot._requests_handler.ongoing_requests:
                    request = request  # type: PiRequest
                    transmit_request = False

                    if request.expected_answers is None or len(request.expected_answers) == 0:
                        transmit_request = True

                    else:
                        for expected_answer in request.expected_answers:
                            if raw.command == expected_answer:
                                transmit_request = True
                            elif re.match(expected_answer, raw.raw):
                                transmit_request = True

                    if transmit_request:
                        request._call_callback(raw)

            finally:
                data = ''


class PiRequestsSender(Thread):
    """
    The lowest-level of connection to the IRC server, sending the requests.
    """

    def __init__(self, connection: socket, bot):
        """
        IRC client constructor.

        :param connection: The socket opened to the IRC server.
        :param bot: The bot's main class.
        """

        Thread.__init__(self, name="PiIRCBot_RequestsSender")

        self._connection = connection  # type: socket
        self._bot = bot

    def interrupt(self):
        """
        Kills the requests receiver thread.
        """
        self._connection = None

    def run(self):
        while self._connection is not None:
            request = requests_queue.get()

            if request is None:
                continue

            # rstriped then line ends added so we are sure the request is valid.
            request = request.rstrip()

            self._bot.log_debug("» " + request + "\n")
            self._connection.send(_b(request + '\r\n'))

            requests_queue.task_done()
