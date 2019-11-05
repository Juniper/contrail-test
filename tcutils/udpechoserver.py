from __future__ import print_function
from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import range
from builtins import object
import argparse
import select
import socket
import sys
import queue
import signal
import os
import errno

message = 'Hello'

def get_addr_port(tup):
    return tup[0], tup[1]

class UdpEchoServer(object):
    def __init__(self, start_port, end_port, pid_file, stats_file):
        self.sockets= list()
        self.start_port = start_port
        self.end_port = end_port
        self.pid_file = pid_file
        self.stats_file = stats_file
        self.stats = dict()
        self.connections = 0
        self.write_pid_to_file()

    def write_pid_to_file(self):
        with open(self.pid_file, 'w', 0) as fd:
            fd.write(str(os.getpid()))

    def write_stats_to_file(self):
        with open(self.stats_file, 'w', 0) as fd:
            for dport, connections in self.stats.items():
                for sip, stats in connections.items():
                    fd.write('dport: %s - src ip: %s - sent: %s - recv: %s%s'%(
                        dport, sip, stats['sent'], stats['recv'], os.linesep))

    def create(self):
        for port in range(self.start_port, self.end_port+1):
            for family, socktype, proto, canonname, sockaddr in \
                    socket.getaddrinfo(None, port, 0, socket.SOCK_DGRAM, 0, socket.AI_PASSIVE):
                sock = socket.socket(family, socktype)
                if family == socket.AF_INET6:
                    sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
                sock.setblocking(0)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                # Bind the socket to the port
                sock.bind(sockaddr)
                self.stats[port] = dict()
                # Listen for incoming connections
                self.sockets.append(sock)

    def run(self):
        inputs = [s for s in self.sockets]
        outputs = []
        message_queues = {}
        while inputs:
            try:
                readable, writable, exceptional = select.select(inputs, outputs, inputs)
            except select.error as e:
                err = e.args[0]
                if err == errno.EAGAIN or err == errno.EWOULDBLOCK or err == errno.EINTR:
                    continue
                raise
            for s in readable:
                try:
                    data, sockaddr = s.recvfrom(1024)
                except Exception as e:
                    print(e)
                    continue
                if data:
                    server_address, server_port = get_addr_port(s.getsockname())
                    client_address, client_port = get_addr_port(sockaddr)
                    if s not in message_queues:
                        message_queues[s] = queue.Queue()
                        self.stats[server_port][client_address] = {'sent': 0, 'recv': 0}
                    self.stats[server_port][client_address]['recv'] += data.count(message)
                    message_queues[s].put((data, sockaddr))
                    if s not in outputs:
                        outputs.append(s)
                else:
                    if s in outputs:
                        outputs.remove(s)
                    inputs.remove(s)
                    s.close()
                    del message_queues[s]
            for s in writable:
                try:
                    next_msg, sockaddr = message_queues[s].get_nowait()
                except queue.Empty:
                    outputs.remove(s)
                else:
                    try:
                        server_address, server_port = get_addr_port(s.getsockname())
                        client_address, client_port = get_addr_port(sockaddr)
                        s.sendto(next_msg, sockaddr)
                        self.stats[server_port][client_address]['sent'] += next_msg.count(message)
                    except Exception as e:
                        print(e)
            for s in exceptional:
                inputs.remove(s)
                if s in outputs:
                    outputs.remove(s)
                s.close()
                del message_queues[s]

    def handler(self, signum, frame):
        self.write_stats_to_file()
        if signum == signal.SIGTERM:
            raise SystemExit('Received SIGTERM')

def parse_cli(args):
    '''TCP Echo Server'''
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start_port', action='store', type=int,
                        required=True)
    parser.add_argument('--end_port', action='store', type=int,
                        required=True)
    parser.add_argument('--pid_file', action='store',
                        required=True)
    parser.add_argument('--stats_file', action='store',
                        default='/tmp/tcpechoserver.stats')
    pargs = parser.parse_args(args)
    return pargs

def main():
    pargs = parse_cli(sys.argv[1:])
    server = UdpEchoServer(pargs.start_port, pargs.end_port,
        pargs.pid_file, pargs.stats_file)
    signal.signal(signal.SIGUSR1, server.handler)
    signal.signal(signal.SIGTERM, server.handler)
    server.create()
    try:
        server.run()
    finally:
        server.write_stats_to_file()

if __name__ == '__main__':
    main()
