import select
import socket
import sys
import Queue

min=int(sys.argv[1]) if len(sys.argv) > 1 else 50000
max=int(sys.argv[2]) if len(sys.argv) > 2 else 50000
sockets= list()
# Create a TCP/IP socket
for port in range(min, max+1):
    socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket.setblocking(0)
    # Bind the socket to the port
    service = ('', port)
    print 'starting up on %s port %s' % service
    socket.bind(service)

    # Listen for incoming connections
    socket.listen(5)
    sockets.append(socket)

# Sockets from which we expect to read
inputs = [s for s in sockets]

# Sockets to which we expect to write
outputs = [ ]

# Outgoing message queues (socket:Queue)
message_queues = {}

while inputs:

    # Wait for at least one of the sockets to be ready for processing
    readable, writable, exceptional = select.select(inputs, outputs, inputs)
    # Handle inputs
    for s in readable:
        if s in sockets:
            # A "readable" server socket is ready to accept a connection
            connection, client_address = s.accept()
            print 'new connection from', client_address
            connection.setblocking(0)
            inputs.append(connection)

            # Give the connection a queue for data we want to send
            message_queues[connection] = Queue.Queue()
        else:
            try:
                data = s.recv(1024)
            except Exception as e:
                print e
                continue
            if data:
                # A readable client socket has data
                message_queues[s].put(data)
                # Add output channel for response
                if s not in outputs:
                    outputs.append(s)
            else:
                # Interpret empty result as closed connection
                print 'closing', s, 'after reading no data'
                # Stop listening for input on the connection
                if s in outputs:
                    outputs.remove(s)
                inputs.remove(s)
                s.close()

                # Remove message queue
                del message_queues[s]

    # Handle outputs
    for s in writable:
        try:
            next_msg = message_queues[s].get_nowait()
        except Queue.Empty:
            # No messages waiting so stop checking for writability.
            outputs.remove(s)
        else:
            try:
                s.send(next_msg)
            except Exception as e:
                print e

    # Handle "exceptional conditions"
    for s in exceptional:
        # Stop listening for input on the connection
        inputs.remove(s)
        if s in outputs:
            outputs.remove(s)
        print 'closing socket', s
        s.close()

        # Remove message queue
        del message_queues[s]

