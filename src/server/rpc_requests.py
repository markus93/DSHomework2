# Handles RPC requests, publishes necessary info etc

# Import

import json
import pika
from gamesession import *

# Variables

connected_users = []
active_users = []
SESSIONS = {}
"""@type: dict[str, GameSession]"""
SERVER_NAME = "unnamed"


def publish(ch, method, props, rsp):
    """
    Publish response to client RPC call

    Args:
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
        body (json.dumps): json data dumps containing arguments needed for given method
    """

    data = json.loads(body)

    try:
        user_name = data['user']

        print("%s requested connection" % user_name)

        sessions = []
        err = ""

        if user_name not in connected_users:
            connected_users.append(user_name)

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

    try:
        user_name = data['user']
        session_name = data['sname']
        player_count = data['player_count']

        print("%s requested session creation" % user_name)

        map_pieces = []

        if user_name in connected_users and session_name not in SESSIONS:
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

    try:
        user_name = data['user']
        session_name = data['sname']
        map_pieces = []

        print("%s joining to session %s" % (user_name, session_name))

        if user_name in connected_users and session_name in SESSIONS:
            err = ""
            sess = SESSIONS[session_name]

            # check whether spot in game session is free
            players = sess.players
            max_count = sess.max_players

            if len(players) >= max_count:
                err = "Game session \"%s\" is full." % session_name
                print(err)
            else:
                if user_name not in players:
                    players.append(user_name)
                    map_pieces = sess.assign_pieces(user_name)
                else:
                    pass  # TODO player already in list, meaning player tries to reconnect to game session.
                    # TODO in this case other players already in game, should put player back to game?
                sess.players = players

                # send info about sessions to sessions lobby and game session lobby
                publish_to_topic(ch, '%s.sessions.info' % SERVER_NAME, sess.info())
                publish_to_topic(ch, '%s.%s.info' % (SERVER_NAME, session_name), {'msg': "%s joined to session"})

                print("User \"%s\" joined successfully to session %s." % (user_name, session_name))

        elif user_name not in connected_users:
            err = "Username \"%s\" is not in connected users list" % user_name
            print(err)
        else:
            err = "Session \"%s\" does not exist anymore" % session_name
            print(err)

    except KeyError as e:
        print("KeyError: %s" % str(e))
        err = str(e)

    publish(ch, method, props, {'err': err, 'map': map_pieces})


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
                sess.clean_player_info(user_name)  # cleans player info from server (ship placement, player status etc)

                if sess.in_game:
                    # TODO if in_game then other players should know where not to shoot
                    pass

                # check if in-game and only one player left (then game is finished)
                if sess.in_game and len(players) == 1:
                    print "Game over, only one player left in game."
                    # TODO send message to winner
                # check if last player left from session lobby
                elif len(players) == 0:
                    print "Game session %s is empty, deleting session" % session_name
                    # TODO special msg for this, or just client checks whether player_count == 0
                    SESSIONS.pop(session_name)
                # check if player was owner of session
                elif sess.owner == user_name:
                    sess.owner = players[0]
                    publish_to_topic(ch, '%s.%s.info' % (SERVER_NAME, session_name),
                                     {'msg': "%s is new owner of game" % sess.owner, 'owner': sess.owner})

                sess.players = players

                # send info about sessions to sessions lobby and game session lobby
                publish_to_topic(ch, '%s.sessions.info' % SERVER_NAME, sess.info())
                publish_to_topic(ch, '%s.%s.info' % (SERVER_NAME, session_name),
                                 {'msg': "%s leaved from session" % user_name, 'owner': sess.owner})

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

    try:
        user_name = data['user']
        session_name = data['sname']
        coordinates = data['coords']

        print("%s assigning ship coordinates" % user_name)

        err = ""

        if user_name in connected_users and session_name in SESSIONS:
            sess = SESSIONS[session_name]

            # check whether spot in game session is free
            players = sess.players
            if user_name in players:

                err = sess.place_ships(user_name, coordinates)
                if err == "":

                    # send info about sessions to sessions lobby and game session lobby
                    publish_to_topic(ch, '%s.%s.info' % (SERVER_NAME, session_name),
                                     {'msg': "%s placed ships" % user_name, 'owner': sess.owner})

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
                             {'msg': msg})
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
            elif sess.check_ready(user_name):  # check whether players ready

                sess.in_game = True

                # send info about sessions to sessions lobby and game session lobby
                publish_to_topic(ch, '%s.sessions.info' % SERVER_NAME, sess.info())
                publish_to_topic(ch, '%s.%s.info' % (SERVER_NAME, session_name),
                                 {'msg': "%s started game" % user_name, 'active': sess.in_game})
                # TODO how to send info to players about game starting - is there better method,
                # TODO this way client should always check whether msg contains key 'active'.

                print("User \"%s\" started game successfully from session %s." % (user_name, session_name))
            else:
                err = "All players are not ready!"
                print err
                publish_to_topic(ch, '%s.%s.info' % (SERVER_NAME, session_name),
                                 {'msg': "%s tried to start game, but all users are not yet ready to start game"
                                         % user_name})

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
    pass
