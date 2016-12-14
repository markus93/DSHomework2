import pika
import json
import uuid
import time
from threading import Thread, Timer

CONNECTION_TIMEOUT = 3


class RPCClient(object):

    def __init__(self, args):
        """
        This class handles the RPC part. Any method called on this is sent to the server and the response is given.
        """

        self.server_name = None

        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=args.host, port=args.port))

        self.channel = self.connection.channel()

        result = self.channel.queue_declare(exclusive=True)
        self.callback_queue = result.method.queue

        self.channel.basic_consume(self.on_response, no_ack=True,
                                   queue=self.callback_queue)

        self.response = None
        self.corr_id = 0

        self.timer = None
        self.keep_connection_open()

    def __getattr__(self, method_name):

        if self.server_name is None:
            raise AttributeError

        def remote_method(**data):
            """
            For client it looks like it calls a local function on the RPC object.

            Args:
                **data (dict[str, object]): Data to send to the server

            Returns:
                dict[str, object]: Response dictionary from the server
            """

            self.response = None
            message = json.dumps(data)
            self.corr_id = str(uuid.uuid4())
            self.channel.basic_publish(exchange='',
                                       routing_key='{0}_rpc_{1}'.format(self.server_name, method_name),
                                       properties=pika.BasicProperties(
                                             reply_to=self.callback_queue,
                                             correlation_id=self.corr_id,
                                             ),
                                       body=message)

            start_time = time.time()
            while self.response is None:
                self.connection.process_data_events()

                if start_time + CONNECTION_TIMEOUT < time.time():
                    return {'err': 'Connection timed out'}

            return json.loads(self.response)

        return remote_method

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body

    def exit(self):
        self.timer.cancel()
        self.connection.close()

    def keep_connection_open(self):
        """
        To avoid connection timeout, we must call connection.process_data_events periodically
        """
        self.connection.process_data_events()
        self.timer = Timer(10, self.keep_connection_open)
        self.timer.start()


class BaseListener(Thread):

    def __init__(self, key, args, callback, **kwargs):
        """
        Baseclass for listeners.

        Args:
            key (str): Name of rabbitmq key that to listen for
            args:
            callback: External callback function to call after reciveing from server(s).
        """
        super(BaseListener, self).__init__(**kwargs)

        # Set up the RabbitMQ stuff
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=args.host, port=args.port))

        channel = self.connection.channel()

        channel.exchange_declare(exchange='topic_server',
                                 type='topic')

        result = channel.queue_declare(exclusive=True)
        queue_name = result.method.queue

        channel.queue_bind(exchange='topic_server',
                           queue=queue_name,
                           routing_key=key)

        channel.basic_consume(self.callback,
                              queue=queue_name,
                              no_ack=True)

        # And now the thread logic
        self.external_callback = callback
        self._is_running = True
        self.start()

    def run(self):
        while self._is_running:
            self.connection.process_data_events()

    def exit(self):
        self._is_running = False
        self.connection.close()

    def callback(self, ch, method, props, body):
        """
        Override this
        """
        pass


class GlobalListener(BaseListener):

    def __init__(self, args, callback):
        """
        Listen for servers announcing themselves.
        Calls callback with list of available server names.
        """
        super(GlobalListener, self).__init__('*.info', args, callback, name='GlobalListener')

        # And now the thread logic
        self.servers = {}
        self.update_servers_list()

    def callback(self, ch, method, props, body):
        self.servers[body] = time.time()

    def update_servers_list(self):
        current_time = time.time()
        self.external_callback(server_name for server_name, last_seen in self.servers.items()
                               if last_seen > current_time - 5)

        if self._is_running:
            Timer(1, self.update_servers_list).start()


class ServerListener(BaseListener):

    def __init__(self, key, args, callback):
        """
        Listen for anouncments about the server.
        """
        super(ServerListener, self).__init__(key, args, callback, name='ServerListener')

    def callback(self, ch, method, props, body):
        self.external_callback([json.loads(body)])


class GameListener(BaseListener):

    def __init__(self, key, args, callback):
        """
        Listen for anouncments about the game.
        """
        super(GameListener, self).__init__(key, args, callback, name='GameListener')

    def callback(self, ch, method, props, body):
        self.external_callback(**json.loads(body))


class PlayerListener(BaseListener):

    def __init__(self, key, args, callback):
        """
        Listen for personal anouncments about the player.
        """
        super(PlayerListener, self).__init__(key, args, callback, name='PlayerListener')

    def callback(self, ch, method, props, body):
        self.external_callback(**json.loads(body))