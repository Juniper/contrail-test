import math
import subprocess
import os
import time
from collections import defaultdict
from netaddr import *
import pprint

# Code borrowed from http://wiki.python.org/moin/PythonDecoratorLibrary#Retry
def retry(tries=5, delay=3):
    '''Retries a function or method until it returns True.
    delay sets the initial delay in seconds. 
    '''
    tries=tries*1.0
    tries = math.floor(tries)
    if tries < 0:
        raise ValueError("tries must be 0 or greater")

    if delay <= 0:
        raise ValueError("delay must be greater than 0")

    def deco_retry(f):
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay # make mutable

            result = f(*args, **kwargs) # first attempt
            rv = result
            if type(result) is tuple: rv = result[0]
            while mtries > 0:
                if rv is True: # Done on success
                    if type(result) is tuple: return (True, result[1])
                    return True
                mtries -= 1      # consume an attempt
                time.sleep(mdelay) # wait...

                result = f(*args, **kwargs) # Try again
                rv = result
                if type(result) is tuple: rv = result[0]
            if not rv: 
                if type(result) is tuple: return (False, result[1])
                return False # Ran out of tries :-(

        return f_retry # true decorator -> decorated function
    return deco_retry  # @retry(arg[, ...]) -> true decorator
#end retry 

def web_invoke(httplink):
    output=None
    try:
        cmd='curl '+httplink
        output=subprocess.check_output(cmd, shell=True)
    except Exception,e : 
        output=None
        print e
        return output
    return output
#end web_invoke

#function to get match count of a list of string from a string
#will return a dictionary
def get_string_match_count(string_list,string_where_to_search):
    
    print ('insdie function get_string_match_count')
    list_of_string=[]
    list_of_string=string_list
    print string_where_to_search
    d=defaultdict(int)
    for i in list_of_string:
        d[i]+=string_where_to_search.count(i)
    return d
    
def get_subnet_broadcast_from_ip(ip='',subnet=''):

    print 'inside get_subnet_broadcast_from_ip function'
   
    ipaddr=''
    ipaddr=str(ip)+'/'+str(subnet)
    print ipaddr 
    ipaddr=IPNetwork(ipaddr)
    return str(ipaddr.broadcast)        
        
def get_os_env(var):
    if var in os.environ:
        return os.environ.get(var)
    else:
        return None
#end get_os_env
