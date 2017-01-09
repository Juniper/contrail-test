import zmq
import time
import json
import Queue

POLL_TIMEOUT = 5000

def exec_remote_kill(commands, result=None, timeout=120):

    context = zmq.Context()

    mcast_socket = context.socket(zmq.PUB)
    mcast_socket.set(zmq.LINGER, 0)

    poll = zmq.Poller()
    sockets = {}

    # Dictionary to group commands by VM IP
    ip_grouped_commands = {}
    for address, command in commands:
        ip_grouped_commands.setdefault(address, []).append(
            [command])

    for address, commands in ip_grouped_commands.items():
        ucast_socket = context.socket(zmq.REQ)
        ucast_socket.set(zmq.LINGER, 0)
        ucast_socket.connect('tcp://%s:93' % address)
        poll.register(ucast_socket, zmq.POLLIN)
        sockets[ucast_socket] = address
        ucast_socket.send_json(commands)

    deadline = time.time() + timeout

    while sockets and (timeout == 0 or time.time() < deadline):
        for socket, event in poll.poll(POLL_TIMEOUT):
            if event & zmq.POLLIN:
                address = sockets.pop(socket, None)
                if address is None:
                    continue
                response = socket.recv_json()
                response['address'] = address
                result.append(response)
    return result


def exec_send_file(commands, result=None, timeout=120):

    context = zmq.Context()

    poll = zmq.Poller()
    sockets = {}

    ip_grouped_commands = {}
    for address, command in commands:
        ip_grouped_commands.setdefault(address, []).append(
            command)

    for address, commands in ip_grouped_commands.items():
        ucast_socket = context.socket(zmq.REQ)
        ucast_socket.set(zmq.LINGER, 0)
        ucast_socket.connect('tcp://%s:92' % address)
        poll.register(ucast_socket, zmq.POLLIN)
        sockets[ucast_socket] = address
        ucast_socket.send_json(commands)

    deadline = time.time() + timeout

    while sockets and (timeout == 0 or time.time() < deadline):
        for socket, event in poll.poll(POLL_TIMEOUT):
            if event & zmq.POLLIN:
                address = sockets.pop(socket, None)
                if address is None:
                    continue


def exec_remote_commands(commands, result=None, timeout=1200, q = Queue.Queue()):
    
    context = zmq.Context()

    mcast_socket = context.socket(zmq.PUB)
    mcast_socket.set(zmq.LINGER, 0)

    poll = zmq.Poller()
    sockets = {}

    ip_grouped_commands = {}
    for address, command in commands:
        ip_grouped_commands.setdefault(address, []).append(
            [command])

    
    for address, commands in ip_grouped_commands.items():
        mcast_socket.connect('tcp://%s:91' % address)
        ucast_socket = context.socket(zmq.REQ)
        ucast_socket.set(zmq.LINGER, 0)
        ucast_socket.connect('tcp://%s:90' % address)
        poll.register(ucast_socket, zmq.POLLIN)
        sockets[ucast_socket] = address
        ucast_socket.send_json(commands)
 
    deadline = time.time() + timeout

    while sockets and (timeout == 0 or time.time() < deadline):
        mcast_socket.send_string('begin')
        #print sockets
        for socket, event in poll.poll(POLL_TIMEOUT):
            if event & zmq.POLLIN:
                address = sockets.pop(socket, None)
                if address is None:
                    continue
                response = socket.recv_json()
                response['address'] = address
                result.append(response)

    q.put(result)    
    return result 
