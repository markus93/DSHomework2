# Parses arguments (IP, port and other stuff)
# Runs main method of server


# Imports----------------------------------------------------------------------
from argparse import ArgumentParser  # Parsing command line arguments
from os.path import abspath, sep
from sys import path, argv

from server.main import __info, ___VER, server_main
from common import DEFAULT_MQ_INET_ADDR,\
    DEFAULT_MQ_PORT

# Main method -----------------------------------------------------------------
if __name__ == '__main__':
    # Find the script absolute path, cut the working directory
    a_path = sep.join(abspath(argv[0]).split(sep)[:-1])
    # Append script working directory into PYTHONPATH
    path.append(a_path)

    # Parsing arguments
    parser = ArgumentParser(description=__info(),
                            version=___VER)
    parser.add_argument('-H', '--host',\
                        help='INET address of RabbitMQ '\
                        'defaults to %s' % DEFAULT_MQ_INET_ADDR, \
                        default=DEFAULT_MQ_INET_ADDR)
    parser.add_argument('-p', '--port', type=int,\
                        help='Port of RabbitMQ, '\
                        'defaults to %d' % DEFAULT_MQ_PORT, \
                        default=DEFAULT_MQ_PORT)
    parser.add_argument('-n', '--name', type=str, \
                        help='Name of Game Server')
    # TODO Add server name as argument
    args = parser.parse_args()

    # Run Server main method
    server_main(args)
