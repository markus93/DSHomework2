"""
Common variables

"""
# Imports----------------------------------------------------------------------
import logging

# Logging----------------------------------------------------------------------

FORMAT = '%(asctime)-15s %(levelname)s %(message)s'
logging.basicConfig(level=logging.WARNING, format=FORMAT)  # Log only errors
LOG = logging.getLogger()

# TCP related constants -------------------------------------------------------
#
DEFAULT_MQ_PORT = 5672
DEFAULT_MQ_INET_ADDR = '127.0.0.1'