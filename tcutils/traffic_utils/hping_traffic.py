import re
import string
import logging
from tcutils.util import get_random_name, retry

result_file = '/tmp/hping'

class Hping3:
    ''' Helper to generate hping traffic

        Mandatory args:
        host : Dest IP
        sender_vm_fixture : Sender VMs fixture handle

        hpgin3 Argument names are as in http://linux.die.net/man/8/hping3

        If multiple hping3 traffic sessions needs to be running together,
        user needs to instantiate as many Hping3 objects

        Recommended image - ubuntu-traffic image or any ubuntu
            or any image which supports hping3

        Ex :
            count='10',
            faster=True,
            rand_source='x.y.z.a' => will set rand-source
            icmp_iphlen='5'       => will set icmp-iphlen
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
        rnd_str = get_random_name()
        self.log_file = result_file + '_' + rnd_str + '.log'
        self.result_file = result_file + '_' + rnd_str + '.result'

    def start(self, wait=True):
        cmd = 'hping3 %s %s 1>%s 2>%s' % (self.args_string, self.host,
                                             self.log_file,
                                             self.result_file)
        self.logger.info('Starting hping3  on %s, args: %s' % (
            self.sender_vm_fixture.vm_name, self.args_string))
        self.logger.debug('Hping3 cmd : %s' %(cmd))
        self.sender_vm_fixture.run_cmd_on_vm(cmds=[cmd], as_sudo=True,
            as_daemon=True)
        if wait:
            self.wait_till_hping3_completes()
    # end start

    def stop(self):
        '''
        Stops the running instance of hping3
        Returns a dict of structure :
        { 'sent' :  xyz,
          'received' : xyz,
          'loss'    : xyz in percent,
          'rtt_min' : xyz in ms,
          'rtt_avg' : xyz,
          'rtt_max' : xyz,
        }
        '''
        cmd = 'pkill -9 -f %s' % (self.result_file)
        self.logger.debug('Ensuring hping3 instance with result file %s '
            'on %s is stopped' % (self.result_file,
                                  self.sender_vm_fixture.vm_name))
        self.sender_vm_fixture.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
        (stats, log) = self.parse_result_file(self.result_file)
        return (stats, log)
    # end stop

    def get_stats(self):
        '''
        Returns a dict of structure :
        { 'sent' :  xyz,
          'received' : xyz,
          'loss'    : xyz in percent,
          'rtt_min' : xyz in ms,
          'rtt_avg' : xyz,
          'rtt_max' : xyz,
        }
        '''
        (stats, log) = self.parse_result_file(self.result_file)
        return stats
    # end get_stats

    def parse_result_file(self, result_file):
        ''' parse output similar to below and return a dict

        len=40 ip=169.254.0.3 ttl=64 DF id=0 sport=81 flags=RA seq=14996 win=0 rtt=4.1 ms
        len=40 ip=169.254.0.3 ttl=64 DF id=0 sport=81 flags=RA seq=14997 win=0 rtt=3.0 ms
        len=40 ip=169.254.0.3 ttl=64 DF id=0 sport=81 flags=RA seq=14998 win=0 rtt=2.0 ms
        len=40 ip=169.254.0.3 ttl=64 DF id=0 sport=81 flags=RA seq=14999 win=0 rtt=0.9 ms

        --- 169.254.0.3 hping statistic ---
        15000 packets transmitted, 14997 packets received, 1% packet loss
        round-trip min/avg/max = 0.1/5.8/1012.5 ms

        '''
        reg_result = None
        rtt_result = None
        result_data = {'sent': None, 'received': None, 'loss': None,
                       'rtt_min':None, 'rtt_avg':None, 'rtt_max':None}
        search1 = '''(\S+) packets transmitted, (\S+) packets received, (\S+)% packet loss'''
        search2 = '''round-trip min/avg/max = (\S+)\/(\S+)\/(\S+) '''
#        with open(result_file, 'r') as myfile:
#            result_log = myfile.read()
        cmds = ['cat %s' %(self.result_file),
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
        if rtt_result:
            result_data['rtt_min'] = rtt_result.group(1)
            result_data['rtt_avg'] = rtt_result.group(2)
            result_data['rtt_max'] = rtt_result.group(3)
        if 'None' in  result_data.values():
            self.logger.warn('Parsing of hping3 had problems. Got stats: %s'
                'Please check debug logs'  %(result_data))
            self.logger.debug(result_content)
        else:
            self.logger.debug('Hping3 stats: %s' % (result_data))
        return (result_data, result_log)
    # end parse_result_file

    def get_cmd_args(self, **kwargs):
        ''' convert { 'k1': val, 'k2':val2 } to 
            "--k1 val --k2 val2"
            All keys are of type string
            All values are string or boolean
        '''
        ret_val = ''
        for (k,v) in kwargs.items():
            key = string.replace(k, '_', '-')
            key = '--%s' % (key)
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

    def _get_pid_of_hping3(self):
        cmd = 'pidof hping3'
        # TODO
        # Need to change to use result's succeeded/failed attributes
        # once ssh fowarding is used to run the cmd
        result = self.sender_vm_fixture.run_cmd_on_vm(cmds=[cmd], as_sudo=True,
                 raw=True)
        status = result.values()[0]
        if 'received nonzero return code' in status:
            self.logger.debug('Unable to get pid of hping3 on %s..may not be '
                ' running' % (self.sender_vm_fixture.vm_name))
            return None
        else:
            self.logger.debug('hping3 is active on %s, PID: %s' % (
                              self.sender_vm_fixture,
                              status))
            return status
    # end _get_pid_of_hping3

    @retry(delay=5, tries=100)
    def wait_till_hping3_completes(self):
        if self._get_pid_of_hping3():
            self.logger.debug('Waiting for hping3 to complete...')
            return False
        else:
            self.logger.debug('hping3 has finished running')
            return True
    # end wait_till_hping3_completes
