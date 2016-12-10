import pika
import json
import uuid


class RPCClient(object):

    def __init__(self, args):

        self.server_name = None

        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=args.host, port=args.port))

        self.channel = self.connection.channel()

        result = self.channel.queue_declare(exclusive=True)
        self.callback_queue = result.method.queue

        self.channel.basic_consume(self._on_response, no_ack=True,
                                   queue=self.callback_queue)

        self.response = None
        self.corr_id = 0

    def _on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body

    def __getattr__(self, method_name):

        if self.server_name is None:
            raise AttributeError

        def remote_method(**data):
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


def setup_servers_listener(args, callback):

    callback(['test'])
    return

    # TODO check if connection available
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=args.host, port=args.port))
    channel = connection.channel()

    channel.exchange_declare(exchange='topic_server',
                             type='topic')

    result = channel.queue_declare(exclusive=True)
    queue_name = result.method.queue

    channel.queue_bind(exchange='topic_server',
                       queue=queue_name,
                       routing_key='*.info')

    channel.basic_consume(callback,
                          queue=queue_name,
                          no_ack=True)


