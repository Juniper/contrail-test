import math
import subprocess
import os
import time
from collections import defaultdict
from netaddr import *
import pprint
from fabric.operations import get, put
from fabric.api import run
import logging as log
import threading
from functools import wraps
import errno
import signal
import uuid
log.basicConfig(format='%(levelname)s: %(message)s', level=log.DEBUG)

# Code borrowed from http://wiki.python.org/moin/PythonDecoratorLibrary#Retry


def retry(tries=5, delay=3):
    '''Retries a function or method until it returns True.
    delay sets the initial delay in seconds. 
    '''

    # Update test retry count.
    retry_factor = get_os_env("TEST_RETRY_FACTOR") or "1.0"
    tries = math.floor(tries * float(retry_factor))
    if tries < 0:
        raise ValueError("tries must be 0 or greater")

    # Update test delay interval.
    delay_factor = get_os_env("TEST_DELAY_FACTOR") or "1.0"
    delay = math.floor(delay * float(delay_factor))
    if delay < 0:
        raise ValueError("delay must be 0 or greater")

    def deco_retry(f):
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay  # make mutable

            result = f(*args, **kwargs)  # first attempt
            rv = result
            if type(result) is tuple:
                rv = result[0]
            if type(result) is dict:
                rv = result['result']
            while mtries > 0:
                if rv is True:  # Done on success
                    if type(result) is tuple:
                        return (True, result[1])
                    if type(result) is dict:
                        return {'result': True, 'msg': result['msg']}
                    else:
                        return True
                mtries -= 1      # consume an attempt
                time.sleep(mdelay)  # wait...

                result = f(*args, **kwargs)  # Try again
                rv = result
                if type(result) is tuple:
                    rv = result[0]
                if type(result) is dict:
                    rv = result['result']
            if not rv:
                if type(result) is tuple:
                    return (False, result[1])
                if type(result) is dict:
                    return {'result': False, 'msg': result['msg']}
                return False  # Ran out of tries :-(
            else:
                if type(result) is tuple:
                    return (True, result[1])
                if type(result) is dict:
                    return {'result': True, 'msg': result['msg']}
                else:
                    return True

        return f_retry  # true decorator -> decorated function
    return deco_retry  # @retry(arg[, ...]) -> true decorator
# end retry


def web_invoke(httplink):
    output = None
    try:
        cmd = 'curl ' + httplink
        output = subprocess.check_output(cmd, shell=True)
    except Exception, e:
        output = None
        print e
        return output
    return output
# end web_invoke

# function to get match count of a list of string from a string
# will return a dictionary


def get_string_match_count(string_list, string_where_to_search):

    print ('insdie function get_string_match_count')
    list_of_string = []
    list_of_string = string_list
    print string_where_to_search
    d = defaultdict(int)
    for i in list_of_string:
        d[i] += string_where_to_search.count(i)
    return d


def get_subnet_broadcast_from_ip(ip='', subnet=''):

    print 'inside get_subnet_broadcast_from_ip function'

    ipaddr = ''
    ipaddr = str(ip) + '/' + str(subnet)
    print ipaddr
    ipaddr = IPNetwork(ipaddr)
    return str(ipaddr.broadcast)


def get_os_env(var):
    if var in os.environ:
        return os.environ.get(var)
    else:
        return None
# end get_os_env


def _escape_some_chars(text):
    chars = ['"', '=']
    for char in chars:
        text = text.replace(char, '\\\\' + char)
    return text
# end escape_chars


def remove_unwanted_output(text):
    ''' Fab output usually has content like [ x.x.x.x ] out : <content>
    '''
    return_list = text.split('\n')

    return_list1 = []
    for line in return_list:
        line_split = line.split(' out: ')
        if len(line_split) == 2:
            return_list1.append(line_split[1])
        else:
            if ' out:' not in line:
                return_list1.append(line)
    real_output = '\n'.join(return_list1)
    return real_output


def run_fab_cmd_on_node(host_string, password, cmd, as_sudo=False):
    '''
    Run fab command on a node. Usecase : as part of script running on cfgm node, can run a cmd on VM from compute node
    '''
    cmd = _escape_some_chars(cmd)
    # Fetch fabfile
    put('tcutils/fabfile.py', '~/')
    (username, host_ip) = host_string.split('@')
    cmd_str = 'fab -u %s -p "%s" -H %s -D -w --hide status,user,running ' % (
        username, password, host_ip)
    if username == 'root':
        as_sudo = False
    elif username == 'cirros':
        cmd_str += ' -s "/bin/sh -l -c" '
    if as_sudo:
        cmd_str += 'sudo_command:\"%s\"' % (cmd)
    else:
        cmd_str += 'command:\"%s\"' % (cmd)
    output = run(cmd_str)
    real_output = remove_unwanted_output(output)
    return real_output
# end run_fab_cmd_on_node


def fab_put_file_to_vm(host_string, password, src, dest):
    (username, host_ip) = host_string.split('@')
    put('tcutils/fabfile.py', '~/')
    cmd_str = 'fab -u %s -p %s -H %s -D -w --hide status,user,running fput:\"%s\",\"%s\"' % (
        username, password, host_ip, src, dest)
    log.debug(cmd_str)
    output = run(cmd_str)
    real_output = remove_unwanted_output(output)
# end fab_put_file_to_vm


def retry_for_value(tries=5, delay=3):
    '''Retries a function or method until it returns True.
        delay sets the initial delay in seconds. 
    '''
    tries = tries * 1.0
    tries = math.floor(tries)
    if tries < 0:
        raise ValueError("tries must be 0 or greater")

    if delay <= 0:
        raise ValueError("delay must be greater than 0")

    def deco_retry(f):
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay  # make mutable
            result = None
            while (mtries > 0):
                result = f(*args, **kwargs)  # first attempt
                if result:
                    return result
                else:
                    mtries -= 1      # consume an attempt
                    time.sleep(mdelay)
            return result
        return f_retry  # true decorator -> decorated function
    return deco_retry  # @retry(arg[, ...]) -> true decorator

# end retry_for_value


class threadsafe_iterator:

    """Takes an iterator/generator and makes it thread-safe by
    serializing call to the `next` method of given iterator/generator.
    """

    def __init__(self, it):
        self.it = it
        self.lock = threading.Lock()

    def __iter__(self):
        return self

    def next(self):
        with self.lock:
            return self.it.next()
# end threadsafe_iterator


def threadsafe_generator(f):
    """A decorator that takes a generator function and makes it thread-safe.
    """
    def g(*a, **kw):
        return threadsafe_iterator(f(*a, **kw))
    return g
# end thread_safe generator


class TimeoutError(Exception):
    pass


def timeout(seconds=10, error_message=os.strerror(errno.ETIME)):
    '''Takes a I/O function and raises time out exception if function is stuck for specified time'''
    def decorator(func):
        def _handle_timeout(signum, frame):
            raise TimeoutError(error_message)

        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result

        return wraps(func)(wrapper)

    return decorator
# End timeout


def get_dashed_uuid(id):
    ''' Return a UUID with dashes '''
    return(str(uuid.UUID(id)))


def get_plain_uuid(id):
    ''' Remove the dashes in a uuid '''
    return id.replace('-', '')
