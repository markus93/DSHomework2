import pika
import json
import uuid
import time
from threading import Thread


class RPCClient(object):

    def __init__(self, args):

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

            while self.response is None:
                self.connection.process_data_events()

            return json.loads(self.response)

        return remote_method

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body

    def exit(self):
        self.connection.close()


class ServersListener(Thread):

    def __init__(self, args, callback):
        """
        Listen for servers announcing themselves.
        Calls callback with list of available server names.
        """
        super(ServersListener, self).__init__()

        # Set up the RabbitMQ stuff
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=args.host, port=args.port))
        channel = self.connection.channel()

        channel.exchange_declare(exchange='topic_server',
                                 type='topic')

        result = channel.queue_declare(exclusive=True)
        queue_name = result.method.queue

        channel.queue_bind(exchange='topic_server',
                           queue=queue_name,
                           routing_key='*.info')

        channel.basic_consume(self.on_anouncment,
                              queue=queue_name,
                              no_ack=True)

        # And now the thread logic
        self.servers = {}
        self.callback = callback

        self._is_running = True
        self.start()

    def run(self):
        while self._is_running:
            self.connection.process_data_events(1)

    def exit(self):
        self._is_running = False

    def on_anouncment(self, ch, method, props, body):

        current_time = time.time()

        self.servers[body] = current_time

        self.callback(server_name for server_name, last_seen in self.servers.items() if last_seen > current_time - 5)