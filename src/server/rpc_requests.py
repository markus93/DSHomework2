# Handles RPC requests, publishes necessary info to MQ-s based on requests, times out player turn

# Import

import json
import pika
from gamesession import *
from threading import Thread, Lock
from time import time, sleep

# Variables

connected_users = []
active_users = []
SESSIONS = {}
"""@type: dict[str, GameSession]"""
SERVER_NAME = "unnamed"
TIMER_THREADS = {}
"""@type: dict[str, CheckTurnTime]"""
TIMER_LOCK = Lock()


def publish(ch, method, props, rsp):
    """
    Publish response to client RPC call

    Args:
        ch (channel): channel used to publish messages to RabbitMQ
        method (method_frame): used to get delivery tag for acknowledging
        props (header_frame): used to get reply_to routing key and correlation id
        rsp (dict): dictionary containing response to client
    """

    response = json.dumps(rsp)

    ch.basic_publish(exchange='',
                     routing_key=props.reply_to,
                     properties=pika.BasicProperties(correlation_id=props.correlation_id),
                     body=response)
    ch.basic_ack(delivery_tag=method.delivery_tag)


def publish_to_topic(ch, key, rsp):
    """
    Publish message to topic_server topic exchange MQ
    Messages about in-game, game session lobby activities

    Args:
        ch (channel): channel used to publish messages to RabbitMQ
        key (str): routing key of published message
        rsp (dict): dictionary containing response to client
    """

    response = json.dumps(rsp)

    ch.basic_publish(exchange='topic_server', routing_key=key,
                     body=response)


def on_request_connect(ch, method, props, body):
    """
    Client RPC request for connecting to game server
    Publishes response to request to MQ sent by client

    Args:
        ch (channel): channel used to publish messages to RabbitMQ
        method (method_frame): used to get delivery tag for acknowledging
        props (header_frame): used to get reply_to routing key and correlation id
        body (json.dumps): json data dumps containing arguments needed for given method
    """

    data = json.loads(body)

    sessions = []
    err = ""

    try:
        user_name = data['user']

        print("%s requested connection" % user_name)

        if user_name == "info":  # username info is not allowed, because it is used as topic name.
            err = "Username \"info\" already taken."  # sending this as error to arise minimum number of questions
            print("Player tried to take info as username - not allowed")
        elif user_name == "":
            err = "User cannot have empty name"
            print(err)
        elif user_name not in connected_users:
            connected_users.append(user_name)

            # TODO start listening for user activity, if user not active and in game then send info to session.
            # TODO kick player from server if inactive (but should be left in game, in order to reconnect to game)
            # TODO inactive users should be kicked out of lobby if not in game else changed to inactive

            # Get sessions info
            for key in SESSIONS.keys():
                sessions.append(SESSIONS[key].info())

            print("User \"%s\" connected successfully." % user_name)
        else:
            print("Username \"%s\" already taken" % user_name)
            err = "Username already taken."

    except KeyError as e:
        print("KeyError: %s" % str(e))
        err = str(e)

    publish(ch, method, props, {'err': err, 'sessions': sessions})


def on_request_disconnect(ch, method, props, body):
    """
    Client RPC request for disconnecting from game server
    """

    data = json.loads(body)

    try:
        user_name = data['user']

        print("%s requested disconnecting" % user_name)
        err = ""

        if user_name in connected_users:
            connected_users.remove(user_name)

            # TODO stop listening for user activity

            print("User \"%s\" disconnected successfully." % user_name)
        else:
            err = "Username \"%s\" is not in connected users list" % user_name
            print(err)

    except KeyError as e:
        print("KeyError: %s" % str(e))
        err = str(e)

    publish(ch, method, props, {'err': err})


def on_request_create_session(ch, method, props, body):
    """
    Client RPC request for creating new game session
    """
    data = json.loads(body)
    map_pieces = []

    try:
        user_name = data['user']
        session_name = data['sname']
        player_count = data['player_count']

        print("%s requested session creation" % user_name)

        if session_name == "sessions":
            err = "Session name \"sessions\" is not allowed"
            print(err)
        elif user_name in connected_users and session_name not in SESSIONS:
            err = ""
            sess = GameSession(session_name, player_count, user_name)
            SESSIONS[session_name] = sess
            map_pieces = sess.map_pieces[0]  # on creation owner gets automatically map pieces

            ch.basic_publish(exchange='topic_server', routing_key='%s.sessions.info' % SERVER_NAME,
                             body=json.dumps(sess.info()))

            print("Session \"%s\" created successfully." % session_name)
        elif user_name not in connected_users:
            err = "User \"%s\" is not connected to the server" % user_name
            print(err)
        else:
            err = "Session name \"%s\" is already taken" % session_name
            print(err)

    except KeyError as e:
        print("KeyError: %s" % str(e))
        err = str(e)

    publish(ch, method, props, {'err': err, 'map': map_pieces})


def on_request_join_session(ch, method, props, body):
    """
    Client RPC request for joining available game session
    """

    data = json.loads(body)
    map_pieces = []

    try:
        user_name = data['user']
        session_name = data['sname']
        sess = SESSIONS[session_name]
        battlefield = []

        print("%s joining to session %s" % (user_name, session_name))

        if user_name in connected_users and session_name in SESSIONS:
            err = ""

            # check whether spot in game session is free
            players = sess.players
            max_count = sess.max_players

            if sess.in_game:
                # check whether reconnecting user
                if user_name in players:
                    print("Player %s reconnects to session" % user_name)
                    # set player back to active, so he could shoot, send back battlefield showing only his ships
                    battlefield = sess.get_player_battlefield(user_name)
                    if user_name not in sess.players_active:
                        sess.players_active.append(user_name)

                    publish_to_topic(ch, '%s.%s.info' % (SERVER_NAME, session_name),
                                     {'msg': "%s reconnected to session" % user_name, 'joined': user_name})
                else:
                    err = "Can't join to already started game."
                    print(err)

            else:  # in session lobby
                if len(players) >= max_count:
                    err = "Game session \"%s\" is full." % session_name
                    print(err)
                else:
                    if user_name not in players:
                        players.append(user_name)
                        map_pieces = sess.assign_pieces(user_name)
                        sess.players = players
                        # send info about sessions to sessions lobby and game session lobby
                        publish_to_topic(ch, '%s.sessions.info' % SERVER_NAME, sess.info())
                        publish_to_topic(ch, '%s.%s.info' % (SERVER_NAME, session_name),
                                         {'msg': "%s joined to session" % user_name, 'joined': user_name})

                        print("User \"%s\" joined successfully to session %s." % (user_name, session_name))
                    else:
                        err = "User with given name already in lobby"
                        print(err)

        elif user_name not in connected_users:
            err = "Username \"%s\" is not in connected users list" % user_name
            print(err)
        else:
            err = "Session \"%s\" does not exist anymore" % session_name
            print(err)

    except KeyError as e:
        print("KeyError: %s" % str(e))
        err = str(e)

    # response to player
    if err == "" and sess.in_game:  # reconnecting user
        publish(ch, method, props, {'err': err, 'map': map_pieces, 'battlefield': battlefield,
                                    'next': sess.next_shot_by})

    elif err == "" and user_name in sess.players:  # means player joined successfully
        other_players = sess.players[:]
        other_players.remove(user_name)
        other_players.remove(sess.owner)
        publish(ch, method, props, {'err': err, 'map': map_pieces, 'owner': sess.owner,
                                    'players': other_players, 'ready': sess.players_ready})
    else:
        publish(ch, method, props, {'err': err})


def on_request_leave_session(ch, method, props, body):
    """
    Client RPC request for leaving from current game session
    """

    data = json.loads(body)

    try:
        user_name = data['user']
        session_name = data['sname']

        print("%s leaving from session %s" % (user_name, session_name))

        if user_name in connected_users and session_name in SESSIONS:
            err = ""
            sess = SESSIONS[session_name]

            # remove player and ships
            players = sess.players
            if user_name in players:
                # check if player was owner of session
                if sess.owner == user_name:
                    # len(players) must be >= 2 because leaving player removed after if needed
                    if len(players) >= 2:
                        for player in players:
                            if player != sess.owner:
                                sess.owner = player  # add new owner
                        publish_to_topic(ch, '%s.%s.info' % (SERVER_NAME, session_name),
                                         {'msg': "%s is new owner of game (last owner left)" % sess.owner,
                                          'owner': sess.owner})

                # clean player info
                sess.clean_player_info(user_name)

                if sess.in_game:  # check if in-game and only one player left (then game is finished)
                    if len(sess.players)-1 == 1:  # have not yet removed the player
                        print "Game over, only one player left in game."
                        publish_to_topic(ch, '%s.%s.%s' % (SERVER_NAME, session_name, players[0]),  # message to winner
                                         {'msg': 'You won! (other players left)'})
                        publish_to_topic(ch, '%s.%s.info' % (SERVER_NAME, session_name),
                                         {'msg': "%s won the game" % players[0],
                                          'gameover': players[0],
                                         'active': False})  # msg to session, back to lobby

                        sess.reset_session()
                    else:  # otherwise send other players map where is no ships
                        map_empty = sess.get_map_pieces(user_name)
                        print "%s ships removed, sending data to client." % user_name
                        publish_to_topic(ch, '%s.%s.info' % (SERVER_NAME, session_name),
                                         {'msg': "%s ships removed" % user_name, 'empty_map': map_empty})
                else:  # in lobby
                    if len(players)-1 == 0:  # no players left in session - delete session
                        msg = "Game session %s is empty, session deleted" % session_name
                        print(msg)
                        del SESSIONS[session_name]  # only dict key deleted
                    else:  # send message about leaving lobby
                        publish_to_topic(ch, '%s.%s.info' % (SERVER_NAME, session_name),
                                         {'msg': "%s left from session" % user_name, 'left': user_name})
                    # refresh sessions list
                    publish_to_topic(ch, '%s.sessions.info' % SERVER_NAME, sess.info())

                    # delete empty session
                    if len(sess.players) == 0:
                        del sess

                print("User \"%s\" left successfully from session %s." % (user_name, session_name))
            else:
                print("User was not in players list!")
        elif user_name not in connected_users:
            err = "Username \"%s\" is not in connected users list" % user_name
            print(err)
        else:
            err = "Session \"%s\" does not exist anymore" % session_name
            print(err)

    except KeyError as e:
        print("KeyError: %s" % str(e))
        err = str(e)

    publish(ch, method, props, {'err': err})


def on_request_send_ship_placement(ch, method, props, body):
    """
    Client RPC request for sending ship placement to server. Containing coordinates of ships
    """
    data = json.loads(body)
    err = ""

    try:
        user_name = data['user']
        session_name = data['sname']
        coordinates = data['coords']

        print("%s assigning ship coordinates" % user_name)

        if user_name in connected_users and session_name in SESSIONS:
            sess = SESSIONS[session_name]

            # check whether spot in game session is free
            players = sess.players
            if user_name in players:

                err = sess.place_ships(user_name, coordinates)
                if err == "":

                    # send info about sessions to sessions lobby and game session lobby
                    publish_to_topic(ch, '%s.%s.info' % (SERVER_NAME, session_name),
                                     {'msg': "%s placed ships" % user_name})

                    print("User \"%s\" ships successfully placed." % user_name)
                else:
                    print(err)
            else:
                err = "User was not in players list!"
                print(err)

        elif user_name not in connected_users:
            err = "Username \"%s\" is not in connected users list" % user_name
            print(err)
        else:
            err = "Session \"%s\" does not exist anymore" % session_name
            print(err)

    except KeyError as e:
        print("KeyError: %s" % str(e))
        err = str(e)

    publish(ch, method, props, {'err': err})


def on_request_ready(ch, method, props, body):
    """
    Client RPC request for toggling ready state (player is ready to start or not)
    """

    data = json.loads(body)

    try:
        user_name = data['user']
        session_name = data['sname']

        print("%s is getting ready" % user_name)
        err = ""

        if user_name in connected_users and session_name in SESSIONS:

            sess = SESSIONS[session_name]
            p_ready = sess.players_ready

            if user_name not in sess.ships_placed:
                msg = "Place ships before pressing ready."
                print(msg)
            elif user_name in p_ready:
                p_ready.remove(user_name)
                msg = "%s is not ready anymore" % user_name
            else:
                p_ready.append(user_name)
                msg = "%s is ready" % user_name

            sess.players_ready = p_ready

            # send info about sessions to sessions lobby and game session lobby
            publish_to_topic(ch, '%s.%s.info' % (SERVER_NAME, session_name),
                             {'msg': msg, 'ready': user_name})
            # acknowledge client of player ready state

            print("User \"%s\" set successfully ready state" % user_name)
        elif user_name not in connected_users:
            err = "Username \"%s\" is not in connected users list" % user_name
            print(err)
        else:
            err = "Session \"%s\" does not exist anymore" % session_name
            print(err)

    except KeyError as e:
        print("KeyError: %s" % str(e))
        err = str(e)

    publish(ch, method, props, {'err': err})


def on_request_start_game(ch, method, props, body):
    """
    Client RPC request for starting game, checking if all players are ready to start game
    Publishes to topic_server about game starting
    """

    data = json.loads(body)

    try:
        user_name = data['user']
        session_name = data['sname']

        print("%s starting game on %s" % (user_name, session_name))

        if user_name in connected_users and session_name in SESSIONS:
            err = ""
            sess = SESSIONS[session_name]

            # check whether user is sess owner
            if user_name != sess.owner:
                err = "User is not session owner"
                print(err)
            elif sess.check_ready(user_name) and len(sess.players) > 1:  # check whether players ready and more than 1
                # START GAME
                sess.start_game()
                # send info about sessions to sessions lobby and game session lobby
                publish_to_topic(ch, '%s.sessions.info' % SERVER_NAME, sess.info())
                publish_to_topic(ch, '%s.%s.info' % (SERVER_NAME, session_name),
                                 {'msg': "%s started game and has first shot" % user_name,
                                  'active': sess.in_game, 'next': user_name})  # atm owner gets the first shot

                # start timing out player turns if haven't got response from them in 10 seconds
                thread_timer = CheckTurnTime(SERVER_NAME, ch, sess)
                # thread_timer.start()  # TODO test timer thread
                TIMER_THREADS[session_name] = thread_timer

                print("User \"%s\" started game successfully from session %s." % (user_name, session_name))
            else:
                if len(sess.players) > 1:
                    err = "All players are not ready!"
                else:
                    err = "Only one player in game."
                print err
                publish_to_topic(ch, '%s.%s.info' % (SERVER_NAME, session_name),
                                 {'msg': ("%s tried to start game - " % user_name) + err})

        elif user_name not in connected_users:
            err = "Username \"%s\" is not in connected users list" % user_name
            print(err)
        else:
            err = "Session \"%s\" does not exist anymore" % session_name
            print(err)

    except KeyError as e:
        print("KeyError: %s" % str(e))
        err = str(e)

    publish(ch, method, props, {'err': err})


def on_request_shoot(ch, method, props, body):
    """
    Client RPC request for shooting, check if game session in game, player in list, then call shoot method
    """

    data = json.loads(body)

    msg = ""

    # Lock thread for assigning next player. Timer is reset by shooting.
    TIMER_LOCK.acquire()

    try:
        user_name = data['user']
        session_name = data['sname']
        coords = data['coords']

        print("%s taking shot at %s on %s" % (user_name, str(coords), session_name))

        if user_name in connected_users and session_name in SESSIONS:
            err = ""
            sess = SESSIONS[session_name]

            if sess.next_shot_by == user_name:

                TIMER_THREADS[session_name].turn_start_time = time()  # restart timer

                res = sess.check_shot(coords)  # 0-miss, 1-hit, 2-sunk (refactor to enum)

                if res == 0:
                    # shot missed
                    msg = "You missed."
                    print("Shot missed")
                elif res == 1:
                    # shot hit
                    msg = "You hit a ship."
                    print("Shot hit!")
                    hit_name = sess.get_ship_owner(coords)
                    msg2 = "Your ship was hit by %s" % user_name
                    # message to player who was hit
                    publish_to_topic(ch, '%s.%s.%s' % (SERVER_NAME, session_name, hit_name),
                                     {'msg': msg2, 'coords': coords})  # meant only for hit player

                else:
                    # ship sunk
                    msg = "You hit and sunk a ship."
                    ship_coords = sess.get_ship_coordinates(coords)

                    publish_to_topic(ch, '%s.%s.info' % (SERVER_NAME, session_name),
                                     {'msg': "%s sunk a ship" % user_name, 'coords': ship_coords})

                    # check whether any player lost a game and if only one player left
                    player_lost = sess.check_end_game()
                    if player_lost is not None:
                        publish_to_topic(ch, '%s.%s.info' % (SERVER_NAME, session_name),
                                         {'msg': "%s lost game" % player_lost, 'gameover': player_lost})
                        publish_to_topic(ch, '%s.%s.%s' % (SERVER_NAME, session_name, player_lost),  # spectator info
                                         {'msg': 'You lost! Spectator mode.', 'spec_field': sess.battlefield})

                        if len(sess.players_alive) == 1:  # if only one player alive
                            print("Game over")
                            publish_to_topic(ch, '%s.%s.info' % (SERVER_NAME, session_name),
                                             {'msg': "%s won the game" % user_name, 'gameover': user_name,
                                              'active': False})  # Back to lobby
                            # Reset session info
                            sess.reset_session()

                if sess.in_game:  # if still in game, select next player

                    next_player = sess.get_next_player()

                    publish_to_topic(ch, '%s.%s.info' % (SERVER_NAME, session_name),
                                     {'msg': "%s's turn." % next_player, 'next': next_player, 'coords': coords})
            else:
                # it not given players turn to shoot
                err = "It is not your turn to shoot"
                print(err + " " + user_name)

        elif user_name not in connected_users:
            err = "Username \"%s\" is not in connected users list" % user_name
            print(err)
        else:
            err = "Session \"%s\" does not exist anymore" % session_name
            print(err)

    except KeyError as e:
        print("KeyError: %s" % str(e))
        err = str(e)
    finally:
        TIMER_LOCK.release()

    publish(ch, method, props, {'err': err, 'msg': msg})


class CheckTurnTime(Thread):
    """
    Thread for checking whether server have received response from player in time.
    """
    def __init__(self, server_name, channel, session):
        """
        Publish server's name after every second in order to show that server is active.
        @param server_name:
        @type server_name: str
        @param channel:
        @type channel: BlockingConnection.channel
        @param session:
        @type session: GameSession
        """
        super(CheckTurnTime, self).__init__()
        self.server_name = server_name
        self.channel = channel
        self.sess = session
        self.turn_time = 10
        self._is_running = True
        self.turn_start_time = time()

    def run(self):
        while self._is_running:
            TIMER_LOCK.acquire()  # lock while assigning next player
            if self.sess.in_game:
                if time() - self.turn_start_time >= self.turn_time:
                    print("Player didn't send response in time (10 seconds)")
                    next_player = self.sess.get_next_player()
                    publish_to_topic(self.channel, '%s.%s.info' % (SERVER_NAME, self.sess.session_name),
                                     {'msg': "%s's turn." % next_player, 'next': next_player})  # 'coords' not sent
                    self.turn_start_time = time()
            else:
                self._is_running = False
                # remove also from dictionary
                # remove dict key here, otherwise should check when game ended
                del TIMER_THREADS[self.sess.session_name]
            TIMER_LOCK.release()
            sleep(1)  # no need to check very often
