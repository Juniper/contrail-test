from builtins import str
from builtins import object
import argparse
import socket
import sys
import time
import argparse
import signal
import os
import errno

message = 'Hello'.zfill(9000)
server = '255.255.255.255'

def daemonize(pidfile, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError as e:
        sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
        sys.exit(1)
    os.chdir("/")
    os.setsid()
    os.umask(0)
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError as e:
        sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
        sys.exit(1)
    si = file(stdin, 'r')
    os.dup2(si.fileno(), sys.stdin.fileno())
    with open(pidfile, 'w', 0) as fd:
        fd.write("%s" % os.getpid())

def get_addr_port(tup):
    return tup[0], tup[1]

class UdpEchoClient(object):
    def __init__(self, dports, slow, count, pid_file, stats_file):
        self.sockets = dict()
        self.dports = dports
        self.slow = slow
        self.count = count
        self.pid_file = pid_file
        self.stats_file = stats_file
        self.stats = dict()
        self.sent = 0
        self.write_pid_to_file()

    def write_pid_to_file(self):
        with open(self.pid_file, 'w', 0) as fd:
            fd.write(str(os.getpid()))

    def write_stats_to_file(self):
        with open(self.stats_file, 'w', 0) as fd:
            for dport, connections in self.stats.items():
                for dip, stats in connections.items():
                    fd.write('dport: %s - sent: %s%s'%(
                        dport, stats['sent'], os.linesep))

    def create(self):
        for port in self.dports:
            self.stats[port] = dict()
            family, socktype, proto, canonname, sockaddr = \
                socket.getaddrinfo(server, port, 0, socket.SOCK_DGRAM, 0, 0)[0]
            s = socket.socket(family, socktype)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.stats[port][server] = {'sent': 0}
            self.sockets[s] = sockaddr

    def run(self):
        count = 1
        while True:
            for s, sockaddr in self.sockets.items():
                try:
                    s.sendto(message, sockaddr)
                except socket.error as e:
                    if e.args[0] == errno.EAGAIN or e.args[0] == errno.EINTR:
                        continue
                    raise
                self.stats[sockaddr[1]][sockaddr[0]]['sent'] += 1
            count = count + 1
            if self.count > 0 and count > self.count:
                for s in self.sockets:
                    s.close()
                break
            if self.slow:
                time.sleep(0.5)

    def handler(self, signum, frame):
        self.write_stats_to_file()
        if signum == signal.SIGTERM:
            raise SystemExit('Received SIGTERM')

def parse_cli(args):
    '''Define and Parse arguments for the script'''
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dports', action='store', required=True, nargs='+',
                        type=int, help='List of dst ports')
    parser.add_argument('--slow', action='store_true',
                        help='Enable slow mode, with pause between each send')
    parser.add_argument('--count', action='store', default='0', type=int,
                        help='No of echo pkts to send, <=0 means indefinite')
    parser.add_argument('--pid_file', action='store',
                        required=True)
    parser.add_argument('--stats_file', action='store',
                        default='/tmp/tcpechoclient.stats')
    pargs = parser.parse_args(args)
    return pargs

def main():
    pargs = parse_cli(sys.argv[1:])
    daemonize(pargs.pid_file)
    client = UdpEchoClient(pargs.dports, pargs.slow,
        pargs.count, pargs.pid_file, pargs.stats_file)
    signal.signal(signal.SIGUSR1, client.handler)
    signal.signal(signal.SIGTERM, client.handler)
    client.create()
    try:
        client.run()
    finally:
        client.write_stats_to_file()

if __name__ == '__main__':
    main()
