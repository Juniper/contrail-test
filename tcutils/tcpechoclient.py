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

message = 'Hello'

def get_addr_port(tup):
    return tup[0], tup[1]

class TcpEchoClient(object):
    def __init__(self, servers, dports, slow, retry, count, pid_file, stats_file, sport=None):
        self.sockets = list()
        self.servers = servers
        self.dports = dports
        self.slow = slow
        self.count = count
        self.retry = retry
        self.pid_file = pid_file
        self.stats_file = stats_file
        self.stats = dict()
        self.sent = 0
        self.recv = 0
        self.sport = sport
        self.write_pid_to_file()

    def write_pid_to_file(self):
        with open(self.pid_file, 'w', 0) as fd:
            fd.write(str(os.getpid()))

    def write_stats_to_file(self):
        with open(self.stats_file, 'w', 0) as fd:
            for dport, connections in self.stats.items():
                for dip, stats in connections.items():
                    fd.write('dport: %s - dst ip: %s - sent: %s - recv: %s%s'%(
                        dport, dip, stats['sent'], stats['recv'], os.linesep))

    def create(self):
        for port in self.dports:
            self.stats[port] = dict()
            for server in self.servers:
                family, socktype, proto, canonname, sockaddr = \
                    socket.getaddrinfo(server, port, 0, socket.SOCK_STREAM, 0, 0)[0]
                s = socket.socket(family, socktype)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                if self.sport:
                    s.bind(('', self.sport))
                while True:
                    try:
                        s.connect(sockaddr)
                        self.stats[port][server] = {'sent': 0, 'recv': 0}
                        self.sockets.append(s)
                        break
                    except socket.error as e:
                        if self.retry:
                            time.sleep(5)
                            continue
                        raise

    def run(self):
        count = 1
        while True:
            for s in self.sockets:
                try:
                    s.send(message)
                except socket.error as e:
                    if e.args[0] == errno.EAGAIN or e.args[0] == errno.EINTR:
                        continue
                    raise
                server_address, server_port = get_addr_port(s.getpeername())
                self.stats[server_port][server_address]['sent'] += 1
            for s in self.sockets[:]:
                try:
                    s.settimeout(4)
                    data = s.recv(1024)
                    s.settimeout(None)
                except socket.timeout:
                    continue
                except socket.error as e:
                    if e.args[0] == errno.EAGAIN or e.args[0] == errno.EINTR:
                        continue
                    raise
                if not data:
                    s.close()
                    self.sockets.remove(s)
                else:
                    server_address, server_port = get_addr_port(s.getpeername())
                    self.stats[server_port][server_address]['recv'] += data.count(message)
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
    parser.add_argument('--servers', action='store', required=True, nargs='+',
                        help='List of servers')
    parser.add_argument('--dports', action='store', required=True, nargs='+',
                        type=int, help='List of dst ports')
    parser.add_argument('--sport', type=int,
                        help='Optional: Source port')
    parser.add_argument('--slow', action='store_true',
                        help='Enable slow mode where in there is a pause between each send')
    parser.add_argument('--retry', action='store_true',
                        help='Retry connecting to service indefinitely, if down')
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
    client = TcpEchoClient(pargs.servers, pargs.dports, pargs.slow,
        pargs.retry, pargs.count, pargs.pid_file, pargs.stats_file, pargs.sport)
    signal.signal(signal.SIGUSR1, client.handler)
    signal.signal(signal.SIGTERM, client.handler)
    client.create()
    try:
        client.run()
    finally:
        client.write_stats_to_file()

if __name__ == '__main__':
    main()
