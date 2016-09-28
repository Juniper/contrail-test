import re
import string
import logging
from tcutils.util import get_random_name, retry, is_v6

result_file = '/tmp/ping'

class Ping:
    ''' Helper to generate ping traffic

        Mandatory args:
        host : Dest IP
        sender_vm_fixture : Sender VMs fixture handle

        Supports ping with IPv4 and IPv6
        If c option is not passed then ping will run continuosly
        If multiple ping traffic sessions needs to be running together,
        user needs to instantiate as many ping objects

        Ex :
            c=10
    '''
    def __init__(self,
        sender_vm_fixture,
        host,
        *args,
        **kwargs
        ):
        self.logger = sender_vm_fixture.logger
        self.sender_vm_fixture = sender_vm_fixture
        self.host = host
        self.args_string = self.get_cmd_args(**kwargs)
        self.rnd_str = get_random_name()
        self.log_file = result_file + '_' + self.rnd_str + '.log'
        self.result_file = result_file + '_' + self.rnd_str + '.result'
        self.ping_cmd = 'ping'
        self.pid_file = '/tmp/ping_%s.pid' %(self.rnd_str)
        if is_v6(self.host):
            self.ping_cmd = 'ping6'

    def start(self, wait=True):
        '''
        if c is not passed as argument to ping, 'wait' must be False
        '''
        cmd = '%s %s %s 2>%s 1>%s' % (self.ping_cmd, self.args_string,
            self.host, self.log_file, self.result_file)
        self.logger.info('Starting %s on %s, args: %s' % (self.ping_cmd,
            self.sender_vm_fixture.vm_name, self.args_string))
        self.logger.debug('%s cmd : %s' % (self.ping_cmd, cmd))
        self.sender_vm_fixture.run_cmd_on_vm(cmds=[cmd], as_sudo=True,
            as_daemon=True, pidfile=self.pid_file)
        if wait:
            self.wait_till_ping_completes()
    # end start

    def stop(self):
        '''
        Stops the running instance of ping
        Returns a dict of structure :
        { 'sent' :  xyz,
          'received' : xyz,
          'loss'    : xyz in percent,
          'time'    : xyz in ms
          'rtt_min' : xyz in ms,
          'rtt_avg' : xyz,
          'rtt_max' : xyz,
          'rtt_mdev' : xyz
        }
        '''
        cmd = 'cat %s | xargs kill -2 ' % (self.pid_file)
        self.logger.debug('Ensuring ping instance with result file %s '
            'on %s is stopped' % (self.result_file,
                                  self.sender_vm_fixture.vm_name))
        self.sender_vm_fixture.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
        (stats, log) = self.parse_result_file()
        self.delete_log_files()
        return (stats, log)
    # end stop

    def get_stats(self):
        '''
        Get the ping stats without killing the ping
        log file output format when SIGQUIT(-3) is used for ping:
            67/67 packets, 0% loss, min/avg/ewma/max = 0.171/0.217/0.208/0.312 ms
            77/77 packets, 0% loss, min/avg/ewma/max = 0.171/0.221/0.232/0.312 ms
        Returns a dict of structure :
        { 'sent' :  xyz,
          'received' : xyz,
          'loss'    : xyz in percent,
        }
        '''
        cmd = 'cat %s | xargs kill -3 ' % (self.pid_file)
        self.sender_vm_fixture.run_cmd_on_vm(cmds=[cmd], as_sudo=True)

        result_data = {'sent': None, 'received': None, 'loss': None}
        search1 = '''(\S+)\/(\S+) packets, (\S+)% loss'''
        cmds = ['cat %s| tail -1' %(self.log_file)]
        result = self.sender_vm_fixture.run_cmd_on_vm(cmds, timeout=300)

        result_content = result[cmds[0]]
        if result_content:
            reg_result = re.search(search1, result_content)
        if reg_result:
            result_data['sent'] = reg_result.group(1)
            result_data['received'] = reg_result.group(2)
            result_data['loss'] = reg_result.group(3)
        if 'None' in  result_data.values():
            self.logger.warn('Parsing of ping had problems. Got stats: %s'
                'Please check debug logs'  %(result_data))
            self.logger.debug(result_content)
        else:
            self.logger.debug('ping stats: %s' % (result_data))
        return result_data
    # end get_stats

    def parse_result_file(self, result_file=None):
        ''' parse output similar to below and return a dict

        64 bytes from netmatters.juniper.net (66.129.230.17): icmp_seq=1 ttl=50 time=231 ms
        64 bytes from netmatters.juniper.net (66.129.230.17): icmp_seq=2 ttl=50 time=213 ms
        64 bytes from netmatters.juniper.net (66.129.230.17): icmp_seq=3 ttl=50 time=213 ms
        ^C
        --- juniper.net ping statistics ---
        4 packets transmitted, 3 received, 25% packet loss, time 3003ms
        rtt min/avg/max/mdev = 213.115/219.307/231.394/8.564 ms
        '''
        result_file = result_file or self.result_file
        reg_result = None
        rtt_result = None
        result_data = {'sent': None, 'received': None, 'loss': None,
            'time':None, 'rtt_min':None, 'rtt_avg':None, 'rtt_max':None,
            'rtt_mdev':None}
        search1 = '''(\S+) packets transmitted, (\S+) received, (\S+)% packet loss, time (\S+)ms'''
        search2 = '''rtt min/avg/max/mdev = (\S+)\/(\S+)\/(\S+)\/(\S+) '''

        cmds = ['cat %s' %(result_file),
                'cat %s' %(self.log_file)]
        result = self.sender_vm_fixture.run_cmd_on_vm(cmds, timeout=300)

        result_content = result[cmds[0]]
        result_log = result[cmds[1]]
        if result_content:
            reg_result = re.search(search1, result_content)
            rtt_result = re.search(search2, result_content)
        if reg_result:
            result_data['sent'] = reg_result.group(1)
            result_data['received'] = reg_result.group(2)
            result_data['loss'] = reg_result.group(3)
            result_data['time'] = reg_result.group(4)
        if rtt_result:
            result_data['rtt_min'] = rtt_result.group(1)
            result_data['rtt_avg'] = rtt_result.group(2)
            result_data['rtt_max'] = rtt_result.group(3)
            result_data['rtt_mdev'] = rtt_result.group(4)
        if 'None' in  result_data.values():
            self.logger.warn('Parsing of ping had problems. Got stats: %s'
                'Please check debug logs'  %(result_data))
            self.logger.debug(result_content)
        else:
            self.logger.debug('ping stats: %s' % (result_data))
        return (result_data, result_log)
    # end parse_result_file

    def get_cmd_args(self, **kwargs):
        ''' convert { 'k1': val, 'k2':val2 } to
            "-k1 val -k2 val2"
            All keys are of type string
            All values are string or boolean
        '''
        ret_val = ''
        for (k,v) in kwargs.items():
            key = '-%s' % (k)
            if type(v) == bool:
                if v:
                    v = ''
                else:
                    # i.e. dont set this arg
                    continue
            ret_val += ' %s %s ' % (key,v)
        # end for
        return ret_val
    # end get_cmd_args

    def _check_if_ping_still_running(self):
        result = self.sender_vm_fixture.run_cmd_on_vm(
            cmds=['kill -2 `cat %s`' %(self.pid_file)],
            raw=True)
        status = result.values()[0]
        if result.succeeded:
            self.logger.debug('ping is active on %s, PID: %s' % (
                              self.sender_vm_fixture,
                              status))
            return True
        else:
            self.logger.debug('PID of ping not found to be running'
                ' on VM %s. It must have completed' % (
                self.sender_vm_fixture.vm_name))
            return False
    # end _check_if_ping_still_running

    @retry(delay=5, tries=50)
    def wait_till_ping_completes(self):
        if self._check_if_ping_still_running():
            self.logger.debug('Waiting for ping to complete...')
            return False
        else:
            self.logger.debug('ping has finished running')
            return True
    # end wait_till_ping_completes

    def delete_log_files(self):
        cmd = 'rm -f %s;rm -f %s' % (self.log_file, self.result_file)
        output = self.sender_vm_fixture.run_cmd_on_vm(cmds=[cmd], as_sudo=True)

        self.logger.debug('Result for removing the log files: %s' % (output))
