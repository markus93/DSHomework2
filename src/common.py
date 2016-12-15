"""
Common variables

"""
# Imports----------------------------------------------------------------------
import logging
from threading import Thread
import pika

# Logging----------------------------------------------------------------------

FORMAT = '%(asctime)-15s %(levelname)s %(message)s'
logging.basicConfig(level=logging.WARNING, format=FORMAT)  # Log only errors
LOG = logging.getLogger()

# TCP related constants -------------------------------------------------------
#
DEFAULT_MQ_PORT = 5672
DEFAULT_MQ_INET_ADDR = '127.0.0.1'


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
