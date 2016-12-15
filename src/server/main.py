# Main client - set up connection and MQ-s and start sending information about server activity to "topic_server"

# Import------------------------------------------------------------------------
import pika
import time
from threading import Thread, Timer
import rpc_requests
from common import BaseListener


# Info-------------------------------------------------------------------------

___NAME = 'Battleship Server'
___VER = '0.0.0.1'
___DESC = 'Multiplayer battleship game server using indirect connection and RPC'
___BUILT = '2016-12-14'
___VENDOR = 'Copyright (c) 2016 DSLab'


def __info():
    return '%s version %s (%s) %s' % (___NAME, ___VER, ___BUILT, ___VENDOR)


def server_main(args):
    """
    Call this method to set up and start server
    """

    global_listener = None
    server_announcements_thread = None
    connection = None

    # Initialize connection with mq, TODO save server info upon closing
    try:
        channel, connection = init_connection_to_mq(args)

        # Start announcing server name to topic_server (so client could check whether server is online)
        server_announcements_thread = ServerAnnouncements(args.name, channel)
        server_announcements_thread.start()

        #global_listener = GlobalListener(args, rpc_requests.check_player_activity)

        print "Server %s is up and running" % args.name

        # Start consuming client RPC-s
        channel.start_consuming()
    except (KeyboardInterrupt, SystemExit):
        # On Windows we don't make it to here :(
        print('Shutting down...')
    finally:
        if server_announcements_thread is not None:
            server_announcements_thread.exit()
        if global_listener is not None:
            global_listener.exit()
        if connection is not None:
            connection.close()


def init_connection_to_mq(args):
    """
    Create new connection with MQ and declare queues for RPC and topic exchange
    """

    server_name = args.name  # TODO server name should be unique
    rpc_requests.SERVER_NAME = server_name  # add server name also to rpc_request variables

    connection = pika.BlockingConnection(pika.ConnectionParameters(
        host=args.host, port=args.port))

    channel = connection.channel()

    # Create queues for RPC
    channel.queue_declare(queue='%s_rpc_connect' % server_name)
    channel.queue_declare(queue='%s_rpc_disconnect' % server_name)
    channel.queue_declare(queue='%s_rpc_create_session' % server_name)
    channel.queue_declare(queue='%s_rpc_join_session' % server_name)
    channel.queue_declare(queue='%s_rpc_leave_session' % server_name)
    channel.queue_declare(queue='%s_rpc_ready' % server_name)
    channel.queue_declare(queue='%s_rpc_send_ship_placement' % server_name)
    channel.queue_declare(queue='%s_rpc_start_game' % server_name)
    channel.queue_declare(queue='%s_rpc_shoot' % server_name)

    channel.basic_qos(prefetch_count=1)

    # Assign consumption method for rcp queues
    channel.basic_consume(rpc_requests.on_request_connect, queue='%s_rpc_connect' % server_name)
    channel.basic_consume(rpc_requests.on_request_disconnect, queue='%s_rpc_disconnect' % server_name)
    channel.basic_consume(rpc_requests.on_request_create_session, queue='%s_rpc_create_session' % server_name)
    channel.basic_consume(rpc_requests.on_request_join_session, queue='%s_rpc_join_session' % server_name)
    channel.basic_consume(rpc_requests.on_request_leave_session, queue='%s_rpc_leave_session' % server_name)
    channel.basic_consume(rpc_requests.on_request_ready, queue='%s_rpc_ready' % server_name)
    channel.basic_consume(rpc_requests.on_request_send_ship_placement, queue='%s_rpc_send_ship_placement' % server_name)
    channel.basic_consume(rpc_requests.on_request_start_game, queue='%s_rpc_start_game' % server_name)
    channel.basic_consume(rpc_requests.on_request_shoot, queue='%s_rpc_shoot' % server_name)

    # using exchange topic_server to send information about server and game sessions of server
    channel.exchange_declare(exchange='topic_server', type='topic')

    return channel, connection


class ServerAnnouncements(Thread):
    """
    Thread for sending server name to *.info queue, needed in order to check whether server is online or not
    """
    def __init__(self, server_name, channel):
        """
        Publish server's name after every second in order to show that server is active.
        @param server_name:
        @type server_name: str
        @param channel:
        @type channel: BlockingConnection.channel
        """
        super(ServerAnnouncements, self).__init__()
        self.server_name = server_name
        self.channel = channel
        self._is_running = True

    def run(self):
        while self._is_running:
            self.channel.basic_publish(exchange='topic_server', routing_key='%s.info' % self.server_name,
                                       body=self.server_name)
            time.sleep(1)

    def exit(self):
        self._is_running = False


class GlobalListener(BaseListener):

    def __init__(self, args, callback):
        """
        Listen for players announcing themselves.
        Calls callback with list of active player names.
        """
        super(GlobalListener, self).__init__('players.info', args, callback, name='GlobalListener')

        # And now the thread logic
        self.players = {}
        self.update_players_activity()

    def callback(self, ch, method, props, body):
        self.players[body] = time.time()

    def update_players_activity(self):
        current_time = time.time()
        self.external_callback(player_name for player_name, last_seen in self.players.items()
                               if last_seen > current_time - 5)

        if self._is_running:
            Timer(1, self.update_players_activity).start()
