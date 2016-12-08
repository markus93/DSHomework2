# Handles RPC requests, publishes necessary info etc

# Import

import json
import pika

# Variables

connected_users = []
active_users = []
# Variables
SESSIONS = {}
"""@type: dict[str, GameSession]"""


def on_request_connect(ch, method, props, body):

    data = json.loads(body)

    try:
        user_name = data['user']

        print("%s requested connection" % user_name)

        sessions = []

        if user_name not in connected_users:
            err = ""
            # TODO send also back game sessions info
            connected_users.append(user_name)

            # Get sessions info
            for key in SESSIONS.keys():
                sessions.append(SESSIONS[key].info())

            print("User \"%s\" connected successfully." % user_name)
        # elif check if user is not active - didn't shot at his/her turn
        else:
            print("Username \"%s\" already taken" % user_name)
            err = "Username already taken."

    except KeyError as e:
        print("KeyError: %s" % str(e))
        err = str(e)

    response = json.dumps({'err': err, 'sessions': sessions})

    ch.basic_publish(exchange='',
                     routing_key=props.reply_to,
                     properties=pika.BasicProperties(correlation_id=props.correlation_id),
                     body=response)
    ch.basic_ack(delivery_tag=method.delivery_tag)


def on_request_disconnect(ch, method, props, body):

    data = json.loads(body)

    try:
        user_name = data['user']

        print("%s requested disconnecting" % user_name)

        if user_name in connected_users:
            err = ""
            connected_users.remove(user_name)

            print("User \"%s\" disconnected successfully." % user_name)
        else:
            err = "Username \"%s\" is not in connected users list" % user_name
            print(err)

    except KeyError as e:
        print("KeyError: %s" % str(e))
        err = str(e)

    response = json.dumps({'err': err})

    ch.basic_publish(exchange='',
                     routing_key=props.reply_to,
                     properties=pika.BasicProperties(correlation_id=props.correlation_id),
                     body=response)
    ch.basic_ack(delivery_tag=method.delivery_tag)
