import socket

def is_v4(address):
    try:
        socket.inet_pton(socket.AF_INET, address)
    except socket.error:
        return False
    return True

def is_v6(address):
    try:
        socket.inet_pton(socket.AF_INET6, address)
    except socket.error:
        return False
    return True
