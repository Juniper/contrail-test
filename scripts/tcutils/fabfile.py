from fabric.operations import sudo, run, get, put, env
import paramiko
import time

env.command_timeout = 120


def sudo_command(cmd):
    sudo(cmd)


def command(cmd):
    run(cmd)


def fput(src, dest):
    put(src, dest)

def retry(tries=5, delay=3):
    '''Retries a function or method until it returns True.
    delay sets the initial delay in seconds.
    '''

    if tries < 0:
        raise ValueError("tries must be 0 or greater")

    if delay < 0:
        raise ValueError("delay must be 0 or greater")

    def deco_retry(f):
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay  # make mutable

            result = f(*args, **kwargs)  # first attempt
            rv = result
            if type(result) is tuple:
                rv = result[0]
            while mtries > 0:
                if rv == "True" :  # Done on success
                    if type(result) is tuple:
                        return ("True", result[1])
                    return "True"
                mtries -= 1      # consume an attempt
                time.sleep(mdelay)  # wait...

                result = f(*args, **kwargs)  # Try again
                rv = result
                if type(result) is tuple:
                    rv = result[0]
            if not "True" in rv:
                if type(result) is tuple:
                    return ("False", result[1])
                return "False"  # Ran out of tries :-(
            else:
                if type(result) is tuple:
                    return ("True", result[1])
                return "True"

        return f_retry  # true decorator -> decorated function
    return deco_retry  # @retry(arg[, ...]) -> true decorator
# end retry

@retry(delay=3, tries=100)
def wait_for_ssh(timeout=5):
    ip = env.host
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip, username=env.user,
                       password=env.password, timeout=timeout)
        client.close()
    except Exception, e:
        client.close()
        return "False"
    return "True"
# end wait_for_ssh
