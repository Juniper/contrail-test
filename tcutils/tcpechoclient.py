import socket
import sys
import time
import argparse

def parse_cli(args):
    '''Define and Parse arguments for the script'''
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--servers', action='store', required=True, nargs='+',
                        help='List of servers')
    parser.add_argument('--dports', action='store', nargs='+',
                        default=[50000], type=int, help='List of dst ports')
    parser.add_argument('--flows', action='store', default='1', type=int,
                        help='No of flows per dst port[1]')
    parser.add_argument('--slow', action='store_true',
                        help='Enable slow mode where in there is a pause between each send')
    parser.add_argument('--retry', action='store_true',
                        help='Retry connecting to service indefinitely, if down')
    parser.add_argument('--count', action='store', default='0', type=int,
                        help='No of echo pkts to send, <=0 means indefinite')
    pargs = parser.parse_args(args)
    return pargs

def run(args):
    socks = list()
    connects = 0
    servers = args.servers
    dports = args.dports
    sport_start = 20000
    n_tranx = 1 if args.slow else 10

    for server in servers:
        for port in dports:
            for sport in range(sport_start, sport_start+args.flows):
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                #s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                s.bind(('', sport))
                service = (server, port)
                while True:
                    try:
                        s.connect(service)
                        connects += 1
                        break
                    except socket.error as e:
                        print 'service', service, 'seems to be down.', e
                        if args.retry:
                            time.sleep(5)
                            continue
                        raise
                    socks.append(s)

    print 'Able to successfully create ', connects, 'connections'
    message = 'Hello'

    iter = 1
    while True:
        for s in socks:
            for i in range(0, n_tranx):
                s.send(message)
        for s in socks:
            data = s.recv(1024)
            print data
            if not data:
                print 'closing socket', s.getsockname()
                s.close()
        iter = iter + 1
        if args.count > 0 and iter > args.count:
            for s in socks:
                s.close()
            print 'sent and received', args.count, 'echos'
            break
        if args.slow:
            time.sleep(1)

def main():
    args = parse_cli(sys.argv[1:])
    run(args)

if __name__ == '__main__':
    main()

