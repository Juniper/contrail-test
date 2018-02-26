"""Unittest for commands module."""

import unittest
from time import sleep

from tcutils.commands import Command


class TestCommand(unittest.TestCase):

    def test_command(self):
        ping = Command("ping localhost")
        ping.start()
        sleep(2)
        r, o, e = ping.stop()
        assert 'PING' in o

if __name__ == '__main__':
    unittest.main()
