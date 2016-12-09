# Main client methods

# Import------------------------------------------------------------------------
import pika
import uuid
import json

# Info-------------------------------------------------------------------------

___NAME = 'Battleship Client'
___VER = '0.0.0.1'
___DESC = 'Multiplayer battleship game client using indirect connection and RPC'
___BUILT = '2016-12-14'
___VENDOR = 'Copyright (c) 2016 DSLab'

# Variables


def __info():
    return '%s version %s (%s) %s' % (___NAME, ___VER, ___BUILT, ___VENDOR)


class RpcClient(object):

    def __init__(self, args):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=args.host, port=args.port))

        self.channel = self.connection.channel()

        result = self.channel.queue_declare(exclusive=True)
        self.callback_queue = result.method.queue

        self.channel.basic_consume(self.on_response, no_ack=True,
                                   queue=self.callback_queue)

        self.response = None
        self.corr_id = 0

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body

    def call(self, method_name, **data):
        self.response = None
        message = json.dumps(data)
        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(exchange='',
                                   routing_key=method_name,
                                   properties=pika.BasicProperties(
                                         reply_to=self.callback_queue,
                                         correlation_id=self.corr_id,
                                         ),
                                   body=message)
        while self.response is None:
            self.connection.process_data_events()
        return json.loads(self.response)


def callback(ch, method, properties, body):
    print("Session info: " + body)


def client_main(args):

    connection = pika.BlockingConnection(pika.ConnectionParameters(  # TODO check if connection available
        host=args.host, port=args.port))
    channel = connection.channel()

    channel.exchange_declare(exchange='topic_server',
                             type='topic')

    result = channel.queue_declare(exclusive=True)
    queue_name = result.method.queue

    # channel.queue_bind(exchange='topic_server',
    #                    queue=queue_name,
    #                    routing_key='*.info')
    #
    # channel.basic_consume(callback,
    #                       queue=queue_name,
    #                       no_ack=True)

    # TODO use *.info to get game server names, which is also used in order to use right RPC queues

    server_name = "test"

    channel.queue_bind(exchange='topic_server',
                       queue=queue_name,
                       routing_key='%s.sessions.info' % server_name)  # basic info about all sessions (not in game info)

    channel.basic_consume(callback,
                          queue=queue_name,
                          no_ack=True)

    # RPC METHODS TEST

    # Connect user to server
    rpc = RpcClient(args)
    response = rpc.call('test_rpc_connect', **{'user': "test_user"})
    print "Connect to server: " + str(response)
    # gives back initial list of game sessions on server (sessions)
    # use sessions info to fill list with current info about game sessions and
    # start listening to new changes to sessions

    # create game session
    response = rpc.call('test_rpc_create_session', **{'user': 'test_user', 'sname': 'test_session', 'player_count': 4})
    print "Create game: " + str(response)

    # new connection, join to session
    rpc.call('test_rpc_connect', **{'user': "test_user2"})
    response = rpc.call('test_rpc_join_session', **{'user': "test_user2", 'sname': 'test_session'})
    print "Join session: " + str(response)

    #send ship placement
    response = rpc.call('test_rpc_send_ship_placement', **{'user': "test_user2", 'sname': 'test_session',
                                                           'coords': [[0,0], [0,1], [0,2], [3,3]]})
    response = rpc.call('test_rpc_send_ship_placement', **{'user': "test_user2", 'sname': 'test_session',
                                                           'coords': [[0, 0], [0, 1], [0, 2], [3, 3]]})
    print "Ships placed: " + str(response)

    # toggle ready state of player
    response = rpc.call('test_rpc_ready', **{'user': "test_user2", 'sname': 'test_session'})
    print response
    #response = rpc.call('test_rpc_ready', **{'user': "test_user2", 'sname': 'test_session'})
    #print response

    response = rpc.call('test_rpc_start_game', **{'user': "test_user", 'sname': 'test_session'})
    print response

    # leave from session
    response = rpc.call('test_rpc_leave_session', **{'user': "test_user", 'sname': 'test_session'})
    response = rpc.call('test_rpc_leave_session', **{'user': "test_user2", 'sname': 'test_session'})
    print "Leave from session" + str(response)

    # leave from server
    response = rpc.call('test_rpc_disconnect', **{'user': "test_user"})
    response = rpc.call('test_rpc_disconnect', **{'user': "test_user2"})
    print "Disconnect: " + str(response)

    channel.start_consuming()

