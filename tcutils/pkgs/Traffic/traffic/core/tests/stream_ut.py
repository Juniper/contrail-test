"""Unittest for stream module."""

import unittest

import tcutils.pkgs.Traffic.traffic.core.stream as stream


class TestStream(unittest.TestCase):

    def test_help(self):
        stream.help()
        stream.help("IPHeader")

if __name__ == '__main__':
    unittest.main()
