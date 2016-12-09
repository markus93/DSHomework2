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

    response = json.dumps(rsp)

    ch.basic_publish(exchange='',
                     routing_key=props.reply_to,
                     properties=pika.BasicProperties(correlation_id=props.correlation_id),
                     body=response)
    ch.basic_ack(delivery_tag=method.delivery_tag)


def publish_to_topic(ch, key, rsp):

    response = json.dumps(rsp)

    ch.basic_publish(exchange='topic_server', routing_key=key,
                     body=response)


def on_request_connect(ch, method, props, body):

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
                    pass  # TODO what should happen if player already in list
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

    data = json.loads(body)

    try:
        user_name = data['user']
        session_name = data['sname']

        print("%s leaving from session %s" % (user_name, session_name))

        if user_name in connected_users and session_name in SESSIONS:
            err = ""
            sess = SESSIONS[session_name]

            # check whether spot in game session is free
            players = sess.players
            if user_name in players:
                players.remove(user_name)
                sess.unassign_pieces(user_name)
                # TODO also remove ships, if in game
            else:
                print("User was not in players list!")

            # check if last player
            if len(players) == 0:
                print "Game session %s is empty, deleting session" % session_name
                # TODO special msg for this, or just client checks whether player_count == 0
                SESSIONS.pop(session_name)
            elif sess.owner == user_name:  # check if player was owner of session
                sess.owner = players[0]

            sess.players = players

            # send info about sessions to sessions lobby and game session lobby
            publish_to_topic(ch, '%s.sessions.info' % SERVER_NAME, sess.info())
            publish_to_topic(ch, '%s.%s.info' % (SERVER_NAME, session_name),
                             {'msg': "%s leaved from session" % user_name, 'owner': sess.owner})

            print("User \"%s\" leaved successfully from session %s." % (user_name, session_name))
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

    data = json.loads(body)

    try:
        user_name = data['user']
        session_name = data['sname']

        print("%s is getting ready" % user_name)
        err = ""

        if user_name in connected_users and session_name in SESSIONS:

            sess = SESSIONS[session_name]
            p_ready = sess.players_ready

            # TODO check if user in players list
            # TODO check if user has placed ships

            if user_name in p_ready:
                p_ready.remove(user_name)
                msg = "%s is not ready anymore" % user_name
            else:
                p_ready.append(user_name)
                msg = "%s is ready" % user_name

            sess.players_ready = p_ready

            # send info about sessions to sessions lobby and game session lobby
            publish_to_topic(ch, '%s.%s.info' % (SERVER_NAME, session_name),
                             {'msg': msg})
            # TODO acknowledge client of player ready state

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


def on_request_send_ship_placement(ch, method, props, body):

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
                    # TODO set also "player has assigned ships" to true (needed in order to ready player)

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


def on_request_start_game(ch, method, props, body):

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
