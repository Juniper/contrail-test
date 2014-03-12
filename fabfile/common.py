from fabric.state import connections
from fabric.api import *
import time
import subprocess
import sys



def reboot(wait=120, host=None):
    # Shorter timeout for a more granular cycle than the default.
    timeout = 5
    # Use 'wait' as max total wait time
    attempts = int(round(wait / float(timeout)))
    # Set host
    if not host:
        host = env.host
    with settings(
        hide('running'),
        timeout=timeout,
        connection_attempts=attempts,
        host=host
    ):
        sudo('reboot') 
        # Try to make sure we don't slip in before pre-reboot lockdown
        time.sleep(30)
        # This is actually an internal-ish API call, but users can simply drop
        # it in real fabfile use -- the next run/sudo/put/get/etc call will
        # automatically trigger a reconnect.
        # We use it here to force the reconnect while this function is still in
        # control and has the above timeout settings enabled.
        connections.connect(env.host_string)


def reconnect(wait=120):
    timeout = 5
    attempts = int(round(wait / float(timeout)))
    with settings(
        hide('running'),
        timeout=timeout,
        connection_attempts=attempts
    ):
        connections.connect(env.host_string)


def wait_until_host_down(wait=120, host=None):
    if not host:
        host = env.host

    timeout = 5
    attempts = int(round(wait / float(timeout)))

    i = 0
    while i < attempts:
        res = subprocess.call(['ping', '-c', '1', host],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        if res is not 0:
            return
        time.sleep(timeout)
        i += 1
    print 'Timeout while waiting for host to shut down.'
    sys.exit(1)

