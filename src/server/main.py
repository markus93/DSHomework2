# Main client methods

# Import------------------------------------------------------------------------
import pika
import time
import json
from common import *
from threading import Thread
from gamesession import *
import rpc_requests


# Info-------------------------------------------------------------------------

___NAME = 'Battleship Server'
___VER = '0.0.0.1'
___DESC = 'Multiplayer battleship game server using indirect connection and RPC'
___BUILT = '2016-12-14'
___VENDOR = 'Copyright (c) 2016 DSLab'


def __info():
    return '%s version %s (%s) %s' % (___NAME, ___VER, ___BUILT, ___VENDOR)


def server_main(args):

    server_name = args.name  # TODO server name should be unique
    rpc_requests.SERVER_NAME = server_name  # add server name also to this variable

    connection = pika.BlockingConnection(pika.ConnectionParameters(  # TODO check if connection available
        host=args.host, port=args.port))

    channel = connection.channel()

    # Create queues for rpc
    channel.queue_declare(queue='%s_rpc_connect' % server_name)
    channel.queue_declare(queue='%s_rpc_disconnect' % server_name)
    channel.queue_declare(queue='%s_rpc_create_session' % server_name)
    channel.queue_declare(queue='%s_rpc_join_session' % server_name)
    channel.queue_declare(queue='%s_rpc_leave_session' % server_name)
    channel.queue_declare(queue='%s_rpc_ready' % server_name)
    channel.queue_declare(queue='%s_rpc_send_ship_placement' % server_name)
    channel.queue_declare(queue='%s_rpc_start_game' % server_name)

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

    # using exchange topic_server to send information about server and game sessions of server
    channel.exchange_declare(exchange='topic_server', type='topic')

    server_announcements_thread = ServerAnnouncements(server_name, channel)
    server_announcements_thread.start()

    print "Server %s is up and running" % server_name

    channel.start_consuming()


class ServerAnnouncements(Thread):
    def __init__(self, server_name, channel):
        """
        Publish server's name after every second in order to show that server is active.
        @param server_name:
        @type server_name: str
        @param channel:
        @type channel: pika.BlockingConnection.channel
        """
        super(ServerAnnouncements, self).__init__()
        self.server_name = server_name
        self.channel = channel
        self._is_running = True

    def run(self):
        while self._is_running:
            while True:
                self.channel.basic_publish(exchange='topic_server', routing_key='%s.info' % self.server_name,
                                           body=self.server_name)  # TODO add this to json data dumps?
                time.sleep(1)
