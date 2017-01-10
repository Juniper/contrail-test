import re
import string
import logging
from collections import OrderedDict
from tcutils.util import get_random_name, retry

result_file = '/tmp/iper3'

class Iperf3:
    ''' Helper to generate iperf3 traffic

        Mandatory args:
        host : Dest IP
        client_vm_fixture : Sender VMs fixture handle
        server_vm_fixture : Receiver VMs fixture handle

        iperf3 Argument names are as in https://iperf.fr/iperf-doc.php

        If multiple iperf3 traffic sessions needs to be running together,
        user needs to instantiate as many Iperf3 objects

        Recommended image - ubuntu-traffic image or any ubuntu
            or any image which supports iperf3

        Ex :
            port = 4203,
            bandwidth = '1G',
            udp = True
            length = 65507
            icmp_iphlen='5'
            tos = '0x24'

    '''
    def __init__(self,
        client_vm_fixture,
        server_vm_fixture,
        *args,
        **kwargs
        ):
        self.logger = client_vm_fixture.logger
        self.client_vm_fixture = client_vm_fixture
        self.server_vm_fixture = server_vm_fixture
        self.args_string = self.get_cmd_args(**kwargs)
        self.rnd_str = get_random_name()
        self.log_file = result_file + '_' + self.rnd_str + '.log'
        self.result_file = result_file + '_' + self.rnd_str + '.result'
        self.iperf_cmd = None
        self.client_pid_file = '/tmp/iperf_client_%s.pid' %(self.rnd_str)
        self.server_pid_file = '/tmp/iperf_server_%s.pid' %(self.rnd_str)

    def start(self, wait=True):
        if "--port" in self.args_string:
            args_list = self.args_string.split(" ")
            port_index = args_list.index("--port") + 1
            port_value = args_list[port_index]
            server_cmd = 'iperf3 -s --port %s 1>%s 2>%s' % (port_value,
                                                            self.log_file,
                                                            self.result_file)
        else:
            server_cmd = 'iperf3 -s 1>%s 2>%s' % (self.log_file,
                                                  self.result_file)
        client_cmd = 'iperf3 -c %s %s 1>%s 2>%s' % (
                                            self.server_vm_fixture.vm_ip, 
                                            self.args_string,
                                            self.log_file,
                                            self.result_file)
        self.logger.info('Starting Iperf3  on %s, args: %s' % (
            self.client_vm_fixture.vm_name, self.args_string))
        self.logger.debug('Iperf3 cmd : %s' %(client_cmd))
        self.server_vm_fixture.run_cmd_on_vm(cmds=[server_cmd], timeout = 15,
            as_sudo=True, as_daemon=True, pidfile=self.server_pid_file)
        self.client_vm_fixture.run_cmd_on_vm(cmds=[client_cmd], timeout = 15,
            as_sudo=True, as_daemon=True, pidfile=self.client_pid_file)
        if wait:
            self.wait_till_iperf3_completes()
    # end start

    def stop(self):
        '''
        Stops the running instance of iperf3
        '''
        servercmd = 'cat %s | xargs kill ' % (self.server_pid_file)
        clientcmd = 'cat %s | xargs kill ' % (self.client_pid_file)
        self.logger.debug('Ensuring iperf3 instance with result file %s '
            'on %s is stopped' % (self.result_file,
                                  self.client_vm_fixture.vm_name))
        self.client_vm_fixture.run_cmd_on_vm(cmds=[clientcmd], as_sudo=True)
        self.server_vm_fixture.run_cmd_on_vm(cmds=[servercmd], as_sudo=True)
    # end stop

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

    def _check_if_iperf_still_running(self):
        result = self.client_vm_fixture.run_cmd_on_vm(
            cmds=['kill `cat %s`' %(self.client_pid_file)],
            raw=True)
        status = result.values()[0]
        if status.succeeded:
            self.logger.debug('iperf3 is active on %s, PID: %s' % (
                              self.client_vm_fixture,
                              status))
            return True
        else:
            self.logger.debug('PID of iperf not found to be running'
                ' on VM %s. It must have completed' % (
                self.client_vm_fixture.vm_name))
            return False
    # end _check_if_iperf_still_running

    @retry(delay=5, tries=50)
    def wait_till_iperf3_completes(self):
        if self._check_if_iperf_still_running():
            self.logger.debug('Waiting for iperf3 to complete...')
            return False
        else:
            self.logger.debug('iperf3 has finished running')
            return True
    # end wait_till_iperf3_completes
