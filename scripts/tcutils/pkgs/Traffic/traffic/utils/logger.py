import logging
import os
import sys

# logging/format definitions
BANNER_WIDTH = 70
LOG_BASE = "contrail"
LOGGER = "%s.traffic" % LOG_BASE

DEFAULT_LEVEL = logging.DEBUG
DEFAULT_FORMAT = "%(asctime)s %(levelname)-8s| %(message)s"
LOG_HANDLERS = []


def get_logger(name=LOGGER, level=DEFAULT_LEVEL, format=None):
    """Configures a basic logger.
    On the first invocation, the root logger will be configured.
    """

    root_logger = logging.getLogger('')

    # If the root logger already has a handler, don't add a new one.
    if not (LOG_HANDLERS or root_logger.handlers):
        # Configure the root logger

        root_logger.setLevel(logging.WARNING)

        stdout_handler = logging.StreamHandler(sys.stdout)
        LOG_HANDLERS.append(stdout_handler)

    #    stderr_handler = logging.StreamHandler(sys.stderr)
    #    stderr_handler.setLevel(logging.WARNING)
    #    LOG_HANDLERS.append(stderr_handler)

        if format is None:
            format = DEFAULT_FORMAT

        formatter = logging.Formatter(format, datefmt="%H:%M:%S")

        for handler in LOG_HANDLERS:
            root_logger.addHandler(handler)
            handler.setFormatter(formatter)

    ret_log = logging.getLogger(name)
    ret_log.setLevel(level)

    return ret_log
