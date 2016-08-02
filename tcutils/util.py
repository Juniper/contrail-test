import math
import subprocess
import os
import re
import time
from collections import defaultdict, MutableMapping
from netaddr import *
import pprint
from fabric.operations import get, put, sudo
from fabric.api import run, env
import logging
import threading
from functools import wraps
import errno
import signal
import uuid
import string
import random
import fcntl
import socket
import struct
from fabric.exceptions import CommandTimeout, NetworkError
from fabric.contrib.files import exists
from fabric.context_managers import settings, hide, cd
from fabric.state import connections as fab_connections
import ConfigParser
from testtools.testcase import TestSkipped
import functools
import testtools
from fabfile import *
from fabutils import *

log = logging.getLogger('log01')
#log.basicConfig(format='%(levelname)s: %(message)s', level=log.DEBUG)

sku_dict = {'2014.1': 'icehouse', '2014.2': 'juno', '2015.1': 'kilo', '12.0': 'liberty', '13.0': 'mitaka'}

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
            final = False
            if type(result) is tuple:
                rv = result[0]
                if 'final' in result:
                    final = True
            if type(result) is dict:
                rv = result['result']
                if 'final' in result.keys() and result['final']:
                    final = True
            while mtries > 0:
                if rv is True:  # Done on success
                    if type(result) is tuple:
                        return (True, result[1])
                    if type(result) is dict:
                        return {'result': True, 'msg': result['msg']}
                    else:
                        return True
                if final:
                    break
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
        log.debug(e)
        return output
    return output
# end web_invoke

# function to get match count of a list of string from a string
# will return a dictionary


def get_string_match_count(string_list, string_where_to_search):

    list_of_string = []
    list_of_string = string_list
    d = defaultdict(int)
    for i in list_of_string:
        d[i] += string_where_to_search.count(i)
    return d


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



def get_via_netconf(ip=env.host, username=env.user, password=env.password, cmd='', timeout=10, device='junos', hostkey_verify="False", format='text'):
    from ncclient import manager
    if hostkey_verify == 'False':
        hostkey_verify = bool(False)
    timeout = int(timeout)
    if device == 'junos':
        device_params = {'name': 'junos'}
    try:
        conn = manager.connect(host=str(ip), username=username, password=password,
                               timeout=timeout, device_params=device_params, hostkey_verify=hostkey_verify)
        get_config = conn.command(command=str(cmd), format=format)
        if format == 'json':
            op = json.loads(get_config._NCElement__root.text)
        else:
            op = get_config.tostring
        return op
    except Exception, e:
        return False
# end get_via_netconf

def config_via_netconf(ip=env.host, username=env.user, password=env.password, cmd_string=[], timeout=10, device='junos', hostkey_verify="False"):
    from ncclient import manager
    if hostkey_verify == 'False':
        hostkey_verify = bool(False)
    timeout = int(timeout)
    if device == 'junos':
        device_params = {'name': 'junos'}
    cmdList = cmd_string.split(';')
    try:
        conn = manager.connect(host=str(ip), username=username, password=password,
                               timeout=timeout, device_params=device_params, hostkey_verify=hostkey_verify)
        conn.lock()
        send_config = conn.load_configuration(action='set', config=cmdList)
        print send_config.tostring
        check_config = conn.validate()
        print check_config.tostring
        compare_config = conn.compare_configuration()
        print compare_config.tostring
        conn.commit()
        if 'family mpls mode packet-based' in cmd_string:
            conn.reboot()
        conn.unlock()
        conn.close_session()
        print compare_config.tostring
        return True
    except Exception, e:
        return False
# end config_via_netconf

def copy_fabfile_to_agent():
    src = 'tcutils/fabfile.py'
    dst = '~/fabfile.py'
    if 'fab_copied_to_hosts' not in env.keys():
        env.fab_copied_to_hosts = list()
    if not env.host_string in env.fab_copied_to_hosts:
        if not exists(dst):
            put(src, dst)
        env.fab_copied_to_hosts.append(env.host_string)

def run_cmd_through_node(host_string, cmd, password=None, gateway=None,
                         gateway_password=None, with_sudo=False, timeout=120,
                         as_daemon=False, raw=False, cd=None, warn_only=True):
    """ Run command on remote node through another node (gateway).
        This is useful to run commands on VMs through compute node
    Args:
        host_string: host_string on which the command to run
        password: Password
        cmd: command
        gateway: host_string of the node through which host_string will connect
        gateway_password: Password of gateway hoststring
        with_sudo: use Sudo
        timeout: timeout
        cd: change directory to provided parameter
        as_daemon: run in background
        raw: If raw is True, will return the fab _AttributeString object itself without removing any unwanted output
    """
    fab_connections.clear()
    kwargs = {}
    if as_daemon:
        cmd = 'nohup ' + cmd + ' &'
        kwargs['pty']=False

    if cd:
        cmd = 'cd %s; %s' % (cd, cmd)

    (username, host_ip) = host_string.split('@')

    if username == 'root':
        with_sudo = False

    shell = '/bin/bash -l -c'

    if username == 'cirros':
        shell = '/bin/sh -l -c'

    _run = sudo if with_sudo else run

    #with hide('everything'), settings(host_string=host_string,
    with settings(host_string=host_string,
                                      gateway=gateway,
                                      warn_only=warn_only,
                                      shell=shell,
                                      disable_known_hosts=True,
                                      abort_on_prompts=False):
        env.forward_agent = True
        gateway_hoststring = gateway if re.match(r'\w+@[\d\.]+:\d+', gateway) else gateway + ':22'
        node_hoststring = host_string if re.match(r'\w+@[\d\.]+:\d+', host_string) else host_string + ':22'
        if password:
            env.passwords.update({node_hoststring: password})
            # If gateway_password is not set, guess same password
            # (if key is used, it will be tried before password)
            if not gateway_password:
                env.passwords.update({gateway_hoststring: password})

        if gateway_password:
            env.passwords.update({gateway_hoststring: gateway_password})
            if not password:
                env.passwords.update({node_hoststring: gateway_password})

        log.debug(cmd)
        tries = 1
        output = None
        while tries > 0:
            try:
                output = _run(cmd, timeout=timeout, **kwargs)
            except CommandTimeout:
                pass
            if (output) and ('Fatal error' in output):
                tries -= 1
                time.sleep(5)
            else:
                break
        # end while

        if not raw:
            real_output = remove_unwanted_output(output)
        else:
            real_output = output
        return real_output


def run_fab_cmd_on_node(host_string, password, cmd, as_sudo=False, timeout=120, as_daemon=False, raw=False,
                        warn_only=True):
    """
    Run fab command on a node. Usecase : as part of script running on cfgm node, can run a cmd on VM from compute node

    If raw is True, will return the fab _AttributeString object itself without removing any unwanted output
    """
    cmd = _escape_some_chars(cmd)
    (username, host_ip) = host_string.split('@')
    copy_fabfile_to_agent()
    cmd_args = '-u %s -p "%s" -H %s -D --hide status,user,running' % (username,
                password, host_ip)
    if warn_only:
        cmd_args+= ' -w '
    cmd_str = 'fab %s ' % (cmd_args)
    if as_daemon:
        cmd_str += '--no-pty '
        cmd = 'nohup ' + cmd + ' &'
    if username == 'root':
        as_sudo = False
    elif username == 'cirros':
        cmd_str += ' -s "/bin/sh -l -c" '
    if as_sudo:
        cmd_str += 'sudo_command:\"%s\"' % (cmd)
    else:
        cmd_str += 'command:\"%s\"' % (cmd)
    # Sometimes, during bootup, there could be some intermittent conn. issue
    log.debug(cmd_str)
    tries = 1
    output = None
    while tries > 0:
        if timeout:
            try:
                output = sudo(cmd_str, timeout=timeout)
                log.debug(output)
            except CommandTimeout:
                return output
        else:
            output = run(cmd_str)
        if ((output) and ('Fatal error' in output)):
            tries -= 1
            time.sleep(5)
        else:
            break
    # end while

    if not raw:
        real_output = remove_unwanted_output(output)
    else:
        real_output = output
    return real_output
# end run_fab_cmd_on_node


def fab_put_file_to_vm(host_string, password, src, dest):
    copy_fabfile_to_agent()
    (username, host_ip) = host_string.split('@')
    cmd_str = 'fab -u %s -p "%s" -H %s -D -w --hide status,user,running fput:\"%s\",\"%s\"' % (
        username, password, host_ip, src, dest)
    log.debug(cmd_str)
    output = run(cmd_str)
    real_output = remove_unwanted_output(output)
# end fab_put_file_to_vm


def sshable(host_string, password=None, gateway=None, gateway_password=None):
    host_string_split = re.split(r"[@:]", host_string)
    host_port = host_string_split[2] if len(host_string_split) > 2 else '22'
    with hide('everything'), settings(host_string=gateway,
                                      password=gateway_password,
                                      warn_only=True):
        try:
            if run('(echo > /dev/tcp/%s/%s)' % (host_string_split[1], host_port)).succeeded:
                time.sleep(5)
                if run('(echo > /dev/tcp/%s/%s)' % (host_string_split[1], host_port)).succeeded:
                    return True
                else:
                    log.error("Error on ssh to %s" % host_string)
                    return False
        except CommandTimeout, e:
            log.debug('Could not ssh to %s ' % (host_string))
            return False


def fab_check_ssh(host_string, password):
    copy_fabfile_to_agent()
    (username, host_ip) = host_string.split('@')
    cmd_str = 'fab -u %s -p "%s" -H %s -D -w --hide status,user,running verify_socket_connection:22' % (
        username, password, host_ip)
    log.debug(cmd_str)
    output = run(cmd_str)
    log.debug(output)
    if 'True' in output:
        return True
    return False
# end fab_check_ssh


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


def get_random_string(size=8, chars=string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def get_random_name(prefix=None, constant_prefix='ctest'):
    if not prefix:
        prefix = 'random'
    return constant_prefix + '-' + prefix + '-' + get_random_string()


def gen_str_with_spl_char(size, char_set=None):
    if char_set:
        special_chars = char_set
    else:
        special_chars = ['<', '>', '&', '%', '.', '_', ',', '"', ' ', '$']
    char_set = ''.join(special_chars) + \
        string.ascii_uppercase[:6] + string.digits[:6]
    return ''.join(random.choice(char_set) for _ in range(size))


def is_v4(address):
    try:
        ip = IPNetwork(address)
        if ip.version == 4:
            return True
    except AddrFormatError:
        pass
    return False


def is_v6(address):
    try:
        ip = IPNetwork(address)
        if ip.version == 6:
            return True
    except AddrFormatError:
        pass
    return False


def is_mac(address):
    try:
        mac = EUI(address)
        if mac.version == 48:
            return True
    except AddrFormatError:
        pass
    return False


def get_af_type(address):
    try:
        if is_v4(address):
            return 'v4'
        if is_v6(address):
            return 'v6'
        if is_mac(address):
            return 'mac'
    except:
        pass
    return None


def get_af_from_cidrs(cidrs):
    af_list = list(map(get_af_type, cidrs))
    if 'v4' in af_list and 'v6' in af_list:
        return 'dual'
    return af_list[0]


def is_valid_af(af):
    valid_address_families = ['v4', 'v6']
    if af in valid_address_families:
        return True
    return False


def update_reserve_cidr(cidr):
    if not cidr:
        return
    current = os.getenv('RESERVED_CIDRS', '').split(',')
    current.extend([cidr])
    env = dict(RESERVED_CIDRS=','.join(current).strip(','))
    os.environ.update(env)

SUBNET_MASK = {'v4': {'min': 8, 'max': 29, 'default': 24},
               'v6': {'min': 64, 'max': 125, 'default': 64}}


def is_valid_subnet_mask(plen, af='v4'):
    '''
    Minimum v4 subnet mask is 8 and max 29
    Minimum v6 subnet mask is 64 and max 125(openstack doesnt support 127)
    '''
    plen = int(plen)
    if plen < SUBNET_MASK[af]['min'] or plen > SUBNET_MASK[af]['max']:
        return False
    return True


def is_reserved_address(address):
    '''
    Check whether a particular address is reserved and should not be allocated.
    RESERVED_CIDRS env variable will take comma separated list of cidrs
    '''
    reserved_cidrs = os.getenv('RESERVED_CIDRS', None)
    if reserved_cidrs:
        cidrs = list(set(reserved_cidrs.split(',')))  # Handling duplicates
        for cidr in cidrs:
            if not cidr.strip():  # taking care of empty commas
                continue
            if not cidr_exclude(address, cidr.strip()):
                return True
    return False


def is_valid_address(address):
    ''' Validate whether the address provided is routable unicast address '''
    addr = IPAddress(address)
    if addr.is_loopback() or addr.is_reserved() or addr.is_private()\
       or addr.is_link_local() or addr.is_multicast():
        return False
    return True


def get_random_cidr(mask=None, af='v4'):
    ''' Generate a random subnet based on netmask and address family '''
    if not is_valid_af(af=af):
        raise ValueError("Address family not supported %s" % af)
    if mask is None:
        mask = SUBNET_MASK[af]['default']
    if type(mask) is int:
        mask = str(mask)
    if not is_valid_subnet_mask(plen=mask, af=af):
        raise ValueError("Invalid subnet mask %s for af %s" % (mask, af))
    while (True):
        if af == 'v6':
            min = 0x2001000000000000
            max = 0x3fffffffffffffff
            address = socket.inet_ntop(socket.AF_INET6,
                                       struct.pack('>2Q',
                                                   random.randint(min, max),
                                                   random.randint(0, 2 ** 64)))
        elif af == 'v4':
            address = socket.inet_ntop(socket.AF_INET,
                                       struct.pack('>I',
                                                   random.randint(2 ** 24, 2 ** 32)))
        if is_reserved_address(address):
            continue
        if is_valid_address(address):
            return '%s/%s' % (str(IPNetwork(address + '/' + mask).network), mask)


def get_random_cidrs(stack):
    subnets = list()
    if 'v4' in stack or 'dual' in stack:
        subnets.append(get_random_cidr(af='v4'))
    if 'v6' in stack or 'dual' in stack:
        subnets.append(get_random_cidr(af='v6'))
    return subnets


def get_an_ip(cidr, offset=2):
    '''
    Fetch an ip from the subnet
    default offset is 2 as 0 points to subnet and 1 is taken by gateway
    This stands good for openstack v6 implementation as of Juno
    '''
    return str(IPNetwork(cidr)[offset])


def get_subnet_broadcast(cidr):
    return str(IPNetwork(cidr).broadcast)


def get_default_cidr(stack='dual'):
    return [str(IPNetwork(x).supernet()[0]) for x in get_random_cidrs(stack=stack)]


# Min support mask is /30 or /126
def get_random_ip(cidr):
    first = IPNetwork(cidr).first
    last = IPNetwork(cidr).last
    if first + 2 >= last:
        return cidr
    return get_an_ip(cidr, offset=random.randint(2, last - first - 1))


def get_random_string_list(max_list_length, prefix='', length=8):
    final_list = []
    list_length = random.randint(0, max_list_length)
    for i in range(0, list_length):
        final_list.append(prefix + '-' + get_random_string(length))
    return final_list


def get_random_mac():
    return ':'.join(map(lambda x: "%02x" % x, [0x00, 0x16, 0x3E,
                                               random.randint(0x00, 0x7F), random.randint(
                                                   0x00, 0xFF),
                                               random.randint(0x00, 0xFF)]))


def search_arp_entry(arp_output, ip_address=None, mac_address=None):
    '''
    arp_output : output of 'arp -an'
    Returns a tuple (ip, mac) if ip_address or mac_address matched
    '''
    if ip_address:
        match_string = ip_address
    elif mac_address:
        match_string = mac_address
    else:
        return (None, None)
    for line in arp_output.splitlines():
        search_obj = None
        if match_string in line:
            search_obj = re.search(
                '\? \((.*)\) at ([0-9:a-f]+)', line, re.M | re.I)
        if search_obj:
            (ip, mac) = (search_obj.group(1), search_obj.group(2))
            return (ip, mac)
    return (None, None)


def get_random_rt(contrail_rt=True):
    '''
    contrail_rt is set to True if the ASN is same as that of the Global ASN of the cluster
    '''
    if contrail_rt:
        return str(random.randint(1, 8000000))
    else:
        return str(random.randint(1, 4294967295))


def get_random_boolean():
    bool_list = [True, False]
    return random.choice(bool_list)


def get_uuid():
    return str(uuid.uuid1())


def compare(val1, val2, operator='subset'):
    if type(val1) is bool:
        val1 = str(val1)
    if type(val2) is bool:
        val2 = str(val2)
    if type(val1) is list and type(val2) is list:
        val1 = sorted(val1)
        val2 = sorted(val2)
    if operator == 'subset':
        return val1 <= val2
    else:
        return val1 == val2


def run_once(f):
    '''A decorator which can be used to call a function only once
    '''
    def wrapper(*args, **kwargs):
        if not wrapper.has_run:
            wrapper.has_run = True
            return f(*args, **kwargs)
    wrapper.has_run = False
    return wrapper

def run_cmd_on_server(issue_cmd, server_ip, username,
                      password, pty=True, as_sudo=False):
    log.debug('[%s]: Running cmd : %s' % (server_ip, issue_cmd))
    with hide('everything'):
        with settings(
            host_string='%s@%s' % (username, server_ip), password=password,
                warn_only=True, abort_on_prompts=False):
            if as_sudo:
                output = sudo('%s' % (issue_cmd), pty=pty) 
            else:
                output = run('%s' % (issue_cmd), pty=pty)
            log.debug('Output : %s' % (output))
            return output
# end run_cmd_on_server

class Lock:

    def __init__(self, filename):
        self.filename = filename
        # This will create it if it does not exist already
        self.handle = open(filename, 'w')

    # Bitwise OR fcntl.LOCK_NB if you need a non-blocking lock
    def acquire(self):
        fcntl.flock(self.handle, fcntl.LOCK_EX)

    def release(self):
        fcntl.flock(self.handle, fcntl.LOCK_UN)

    def __del__(self):
        self.handle.close()


def read_config_option(config, section, option, default_option):
    ''' Read the config file. If the option/section is not present, return the default_option
    '''
    if not config:
        return default_option
    try:
        val = config.get(section, option)
        if val.lower() == 'true':
            val = True
        #elif val.lower() == 'false' or val.lower() == 'none':
        elif val.lower() == 'false':
            val = False
        elif not val:
            val = default_option

        if type(val) is not bool and val is not None and (
            '$__' in val or val.lower() == 'none'):
            # ie. having a template value unpopulated(for $__xyz__)
            # or None
            val = ''
        if val == '' :
            val = default_option
        return val
    except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
        return default_option
# end read_config_option


def copy_file_to_server(host, src, dest, filename, force=False):

    fname = "%s/%s" % (dest, filename)
    with settings(host_string='%s@%s' % (host['username'],
                                         host['ip']), password=host['password'],
                  warn_only=True, abort_on_prompts=False):
        if not exists(fname) or force:
            time.sleep(random.randint(1, 10))
            put(src, dest)
# end copy_file_to_server

def get_host_domain_name(host):
    output = None
    with settings(hide('everything'), host_string='%s@%s' % (host['username'],
        host['ip']), password=host['password'],
        warn_only=True, abort_on_prompts=False):
        output = run('hostname -d')

    return output
# end get_host_domain_name


def get_random_vxlan_id():
    return random.randint(1, 16777215)


def get_random_asn():
    return random.randint(1, 64511)


class v4OnlyTestException(TestSkipped):
    pass


class custom_dict(MutableMapping, dict):

    '''
    custom dict wrapper around dict which could be used in scenarios
    where setitem can be deffered until getitem is requested

    MutableMapping was reqd to inherit clear,get,free etal

    :param callback: callback function which would create value upon keynotfound
    :param env_key : Key under env incase the dict can be shared across testcases
    '''

    def __init__(self, callback, env_key=None):
        self.callback = callback
        self.env_key = env_key
        if self.env_key and self.env_key not in env:
            env[self.env_key] = dict()

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            if self.env_key and key in env[self.env_key]:
                return env[self.env_key][key]
            self[key] = self.callback(key)
            return dict.__getitem__(self, key)

    def __setitem__(self, key, value):
        if self.env_key:
            env[self.env_key][key] = value
        dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        if self.env_key:
            del env[self.env_key][key]
        dict.__delitem__(self, key)

    def __iter__(self):
        return dict.__iter__(self)

    def __len__(self):
        return dict.__len__(self)

    def __keytransform__(self, key):
        return key

    def __contains__(self, key):
        if self.env_key:
            return True if key in env[self.env_key] else False
        else:
            return True if key in self else False


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        try:
            f = '/tmp/%s.lock' % (str(cls.__name__))
            lock = Lock(f)
            lock.acquire()
            if cls not in cls._instances:
                cls._instances[cls] = super(
                    Singleton, cls).__call__(*args, **kwargs)
        finally:
            lock.release()
        return cls._instances[cls]
# end Singleton


def skip_because(*args, **kwargs):
    """A decorator useful to skip tests hitting known bugs or specific orchestrator
    @param bug: optional bug number causing the test to skip
    @param orchestrator: optional orchestrator to be checked to skip test
    @param feature: optional feature to be checked to skip test
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapper(self, *func_args, **func_kwargs):
            skip = False
            if "address_family" in kwargs and "orchestrator" not in kwargs:
                if kwargs["address_family"] in self.inputs.address_family:
                    skip = True
                    msg = "Skipped as %s not supported for this test" % kwargs["address_family"]
                    raise testtools.TestCase.skipException(msg)

            if "orchestrator" in kwargs and 'address_family' in kwargs:
                if ((kwargs["orchestrator"] in self.inputs.orchestrator)
                        and (kwargs['address_family'] in self.inputs.address_family)):
                    skip = True
                    msg = "Skipped as not supported in %s orchestration setup" % self.inputs.orchestrator
                    raise testtools.TestCase.skipException(msg)

            if "orchestrator" in kwargs and 'address_family' not in kwargs:
                if kwargs["orchestrator"] in self.inputs.orchestrator:
                    skip = True
                    msg = "Skipped as not supported in %s orchestration setup" % self.inputs.orchestrator
                    raise testtools.TestCase.skipException(msg)

            if "feature" in kwargs:
                if not self.orch.is_feature_supported(kwargs["feature"]):
                    skip = True
                    msg = "Skipped as feature %s not supported in %s \
				orchestration setup" % (kwargs["feature"], self.inputs.orchestrator)
                    raise testtools.TestCase.skipException(msg)

            if 'ha_setup' in kwargs:
                if ((not self.inputs.ha_setup) and (kwargs["ha_setup"] == False)):
                    skip = True
                    msg = "Skipped as not supported in non-HA setup"
                    raise testtools.TestCase.skipException(msg)

            if "bug" in kwargs:
                skip = True
                if not kwargs['bug'].isdigit():
                    raise ValueError('bug must be a valid bug number')
                msg = "Skipped until Bug: %s is resolved." % kwargs["bug"]
                raise testtools.TestCase.skipException(msg)
            return f(self, *func_args, **func_kwargs)
        return wrapper
    return decorator


def get_build_sku(openstack_node_ip, openstack_node_password='c0ntrail123', user='root'):
    build_sku = get_os_env("SKU")
    if build_sku is not None:
        return str(build_sku).lower()
    else:
        host_str='%s@%s' % (user, openstack_node_ip)
        cmd = 'nova-manage version'
        tries = 10
        while not build_sku and tries:
            try:
                with hide('everything'), settings(host_string=host_str,
                                                  user=user,
                                                  password=openstack_node_password):
                    output = sudo(cmd)
                    build_sku = sku_dict[re.findall("[0-9]+.[0-9]+",output)[0]]
            except NetworkError, e:
                time.sleep(1)
                pass
            tries -= 1
        return build_sku

def is_almost_same(val1, val2, threshold_percent=10, num_type=int):
    ''' returns false if val2 is less than or greater than threshold_percent
        percent of val1
    '''

    val1 = num_type(val1)
    val2 = num_type(val2)
    if val1:
        if (abs(float(val1-val2))/val1)*100 < threshold_percent:
            return True
        else:
            return False
    else:
        if val2:
            return False
        else:
            return True
# end is_almost_same

def compare_dict(dict1, dict2, ignore_keys=[]):
    ''' Compares two dicts.
        Returns a tuple (True/False, set of items which dont match)
    '''
    d1_new = dict((k, v) for k,v in dict1.iteritems() \
        if k not in ignore_keys)
    d2_new = dict((k, v) for k,v in dict2.iteritems() \
        if k not in ignore_keys)
    return (d1_new == d2_new, set(d1_new) ^ set(d2_new))
# end compare_dict
