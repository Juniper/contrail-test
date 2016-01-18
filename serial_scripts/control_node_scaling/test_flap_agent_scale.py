# Pytho libs
from __future__ import print_function
import eventlet
import os
import sys
import platform
import re
import uuid
import time
import errno
import socket
import subprocess
import time
from tcutils.wrappers import preposttest_wrapper
from time import sleep
from netaddr import *
from datetime import datetime, timedelta
import multiprocessing
import traceback
import logging
import fixtures
#
# Contrail libs
#
import argparse
import ConfigParser
from vnc_api.vnc_api import *
import json
from pprint import pformat
from common.contrail_test_init import *
#
# Contrail scaling libs
#
from ssh_interactive_commnds import *
from cn_introspect_bgp import ControlNodeInspect
from vn_oper import VnCfg
from bgp_scale import *
#from policy import PolicyCmd
import test
from base import BaseBGPScaleTest


class FlapAgentScaleInit (object):

    def __init__(self, inputs=None, args_str=None, pre_scale_setup=0, params_ini_file=None):
        self._args = None
        self._model = "/sys/block/sda/device/model"
        self._model = "/sys/block/vda/device/modalias"
        #
        # Time how long test runs
        #
        self.test_start_time = datetime.now()

        #
        # Get args
        #
        # if not args_str:
        #    args_str = ' '.join(sys.argv[1:])
        self._parse_args(args_str)
        self.pre_scale_setup = self._args.run_vn
        if not inputs:
            if 'TEST_CONFIG_FILE' in os.environ:
                self.ini_file = os.environ.get('TEST_CONFIG_FILE')
            else:
                self.ini_file = 'sanity_params.ini'
            self.inputs = ContrailTestInit(
                self.ini_file, stack_user=self._args.username,
                stack_password=self._args.password, project_fq_name=['default-domain', 'default-project'])
        else:
            self.inputs = inputs
            self.logger = self.inputs.logger

        #
        # Use for logging where each iteration can be logged
        #
        self.current_run_count = 0

        #
        # Get os info (version,
        #
        self.pid = os.getpid()

        #
        # Create logfile (logdir if needed), append timestamp to arg name
        #
        self._open_logfile("init")

        #
        # Print version
        #
        self._log_print(
            "INFO: bgp scale test flap_agent_scale_test version: %s" %
            self._args.version)

        #
        # Get ssh fd for Control Node
        #
        self._get_prog_fds()

        #
        # Get localhost info
        #
        self._get_localhost_info()

        #
        # Get params values
        #
        self._get_bgp_start_vals()

        #
        # Install sshpass on test-server if it is not present..
        #
#        self._install_sshpass_if_missing()

        #
        # Get linux distribution for all nodes
        #
        # self._get_linux_distribution()

        #
        # Install any packages needed
        #
#        self._add_packages()

        #
        # Run setup (add VNs, secondaries, etc)
        #
        self._setup()

        #
        # Post-process a possible previous run
        #
        self.report_result_averages(
            "init", int(self._args.run_get_result_prior_run))

    # end __init__

    def _log_print(self, line=''):
        '''Log info
        '''
        if self.pre_scale_setup:
            who = self._args.top_parent
            msg = "%s %s %s" % (datetime.now(), who, line)
        else:
            who = self._args.second_parent
            msg = "%s %s%s %s" % (
                datetime.now(), who, self.current_run_count, line)

        print (msg)
        print (msg, file=self.fd)
        self.fd.flush()

        #self.fd.write (msg, "\n")

    # end _log_print

    def _summary_print(self, msg):

        print (msg, file=self.summary_fd)
        self.summary_fd.flush()

    # end _summary_print

    def _get_linux_distribution(self):

        #
        # Get distro for api server
        #
        result = self.api_ssh_fd.execCmd(
            self._args.get_sys_release_cmd, self.inputs.auth_ip, username, password)
        if result != None:
            result = result[:-1]

        self.api_linux_distribution = result
        self._log_print(
            "INFO: linux distribution on api-server: %s release: %s" %
            (self.inputs.auth_ip, self.api_linux_distribution))

        #
        # Get linux distribuition for control nodes
        #
        self.cn_linux_distribution = []
        for i in range(len(self.cn_ips)):
            cn_ssh_fd = self.cn_ssh_fds[i]
            cn_ip = self.cn_ips[i]

            result = cn_ssh_fd.execCmd(
                self._args.get_sys_release_cmd, cn_ip, username, password)
            if result != None:
                result = result[:-1]

            self.cn_linux_distribution.append(result)
            self._log_print(
                "INFO: linux distribution on contrail-control: %s release: %s" %
                (cn_ip, self.cn_linux_distribution[i]))

        #
        # Get linux distribuition for test servers
        #
        self.ts_linux_distribution = []
        for i in range(len(self.ts_ips)):
            ts_ssh_fd = self.ts_ssh_fds[i]
            ts_ip = self.ts_ips[i]

            result = ts_ssh_fd.execCmd(
                self._args.get_sys_release_cmd, ts_ip, username, password)
            if result != None:
                result = result[:-1]

            self.ts_linux_distribution.append(result)
            self._log_print(
                "INFO: linux distribution on testserver: %s release: %s" %
                (ts_ip, self.ts_linux_distribution[i]))

        #
        # Print linux distribuition for localhost
        #
        self._log_print(
            "INFO: linux distribution on localhost testserver: %s release: %s" %
            (self.localhost_ip, self.linux_distribution))

        return

    # end _get_linux_distribution

#    def _install_sshpass_if_missing(self):
#
#        self._log_print("INFO: checking for sshpass on localhost: %s" %
#                        self.localhost_ip)
#
#        #
# Check if sshpass is present
#        #
#        status, result = self._get_subprocess_info("which sshpass")
#
#        #
# Install sshpass if not found..
#        #
# if re.search("no sshpass in", result, re.IGNORECASE):
#        if status == None:
#            self._log_print(
#                "INFO: sshpass not found - installing on localhost: %s" %
#                self.localhost_ip)
#
#            #
# mount something if fedora and not main parent in order to get cobbler-config.repo
#            #
#            if self.linux_distribution == self._args.linux_fedora and not self.pre_scale_setup:
#                status, result = self._get_subprocess_info(
#                    self._args.mnt_shared_dir_cmd)
#                status, result = self._get_subprocess_info(
#                    self._args.cp_cobbler_cmd)
#                status, result = self._get_subprocess_info(
#                    self._args.install_sshpass_rpm_cmd)
#            else:
#                status, result = self._get_subprocess_info(
#                    self._args.install_sshpass_yum_cmd)
#            self._log_print("INFO: sshpass installed on localhost: %s" %
#                            self.localhost_ip)
#
#        else:
#            self._log_print(
#                "INFO: sshpass found on localhost: %s result: %s" %
#                (self.localhost_ip, result[:-1]))
#
# end  _install_sshpass_if_missing
#    def _add_packages(self):
#
#        if not int(self._args.add_packages):
#            return
#
#        try:
#            self._args.install_w_yum_cmd
#        except:
#            self._log_print("INFO: no packages to install..")
#            return
#
#        #
# Add to local host
#        #
#        self._add_package_call('local-host', self.localhost_ip,
#                               0, self.linux_distribution, self._args.install_w_yum_cmd)
#
#        #
# Add packages to control nodes
#        #
#        for i in range(len(self.cn_ips)):
#            cn_ssh_fd = self.cn_ssh_fds[i]
#            cn_ip = self.cn_ips[i]
#            self._add_package_call(
#                'contrail-control', self.cn_ips[i], cn_ssh_fd, self.cn_linux_distribution[i], self._args.install_w_yum_cmd)
#
#        #
# Add packages to test servers
#        #
#        for i in range(len(self.ts_ips)):
#            ts_ssh_fd = self.ts_ssh_fds[i]
#            ts_ip = self.ts_ips[i]
#            self._add_package_call(
#                'test-server', self.ts_ips[i], ts_ssh_fd, self.ts_linux_distribution[i], self._args.install_w_yum_cmd)
#
#        #
# Add packages to api server
#        #
#        self._add_package_call('api-server', self.inputs.auth_ip,
#                               self.api_ssh_fd, self.api_linux_distribution, self._args.install_w_yum_cmd)
#
#        return
#
# end _add_packages
#
#    def _add_package_call(self, who, ip, fd, distro, cmd):
#
#        #
# Get names of each package in the cmd. cmd is in the format:
# yum -y install <package_name_1> ... <package_name_n>, where n >= 0
#        #
# Therefore, remove the first 3 strings
#        #
#        packages = re.split(" ", "".join(cmd))[3:]
#
#        if len(packages) == 1:
#            self._log_print(
#                "INFO: verifying package: %s exists on %s server: %s" %
#                (packages, who, ip))
#        elif len(packages) > 1:
#            self._log_print(
#                "INFO: verifying packages: %s exist on %s server: %s" %
#                (packages, who, ip))
#        else:
#            self._log_print("WARNING: no package list in command: '%s'" % cmd)
#            return
#
#        #
# Check if package exits already, remove from list if so
#        #
#        new_packages_list = []
#        for i in range(len(packages)):
#
#            which_cmd = "which %s" % packages[i]
#            #
# See if it already exists
#            #
#            if who == 'local-host':
#                status, result = self._get_subprocess_info(
#                    which_cmd, print_err_msg_if_encountered=0)
#                if status == None:
#                    new_packages_list.append(packages[i])
#                else:
#                    pass
#            else:
#                status = fd.execCmd(which_cmd, ip, username, password)
#                if status == None:
#                    new_packages_list.append(packages[i])
#                else:
#                    result = status
#
#            if status != None:
# self._log_print ("DEBUG: found package: %s exists on %s server: %s" % (packages, who, ip))
#                pass
#            else:
#                self._log_print(
#                    "INFO: package not found - installing: %s on %s server: %s" % (packages, who, ip))
#
# end check packages
#
#        #
# If packages not already installed, execute the install with the new list
#        #
#        return_val = None
#        if len(new_packages_list):
#
#            #
# Execute cobbler commands for fedora
#            #
#            if distro == self._args.linux_fedora and not self.pre_scale_setup:
#                if who == 'local-host':
#                    status, result = self._get_subprocess_info(
#                        self._args.mnt_shared_dir_cmd)
#                    status, result = self._get_subprocess_info(
#                        self._args.cp_cobbler_cmd)
#                else:
#                    result = fd.execCmd(self._args.mnt_shared_dir_cmd, ip, username, password)
#                    result = fd.execCmd(self._args.cp_cobbler_cmd, ip, username, password)
#
#            #
# Execute command
#            #
#            new_cmd = " ".join(re.split(" ", "".join(cmd))
#                               [0:3]) + " " + " ".join(new_packages_list)
#            if who == 'local-host':
#                status, result = self._get_subprocess_info(new_cmd)
#            else:
#                status = fd.execCmd(new_cmd, ip, username, password)
#
# if status == None:
# self._log_print ("WARNING: package not found on %s server: %s - problem accessing server or installing with cmd: '%s'" % (who, ip, new_cmd))
# else:
# self._log_print ("INFO: package not found on %s server: %s - installing with cmd: '%s'" % (who, ip, new_cmd))
#
#        return
#
# end _add_package_call

    def _setup(self):
        if not int(self._args.run_setup):
            return

        #self._log_print("INFO: in _setup")

        #
        # Add secondary addresses to the test-server running bgp_stress_test
        #
        if self.pre_scale_setup:
            self.add_secondaries()

        #
        # Create VNs.
        # Note: - the delete is there to preclude previous run overlap.,
        #         try and avoid the delete when numbers get over 1K
        #
        if self.pre_scale_setup:
            if int(self._args.del_vn_before_create):
                self.add_or_delete_vns("del")
            else:
                pass
            self.add_or_delete_vns()

        #
        # Create import/export policy between VN instances
        # Note: - if the params bit is set to not run, call returns immediately
        #
        self.policy_config()

        #
        # Append env variables to control node params file and to supervisor-control
        #
        if self.pre_scale_setup:
            self._add_cn_env_vars()

        #
        # Restart Control node, if needed
        #
        self._restart_cn()

        #
        # Check all vns are present
        #
        # if (self.pre_scale_setup and
        # self.set_general_vn_name_across_testservers) or (not
        # self.pre_scale_setup and not
        # self.set_general_vn_name_across_testservers):
        if self.pre_scale_setup and int(self._args.run_at_setup_check_vn_all):
            self._check_vn_all()

        #
        # Set affinity mask
        #
        self._taskset_affinity_mask()

    # end _setup

    def _get_thread_cpu_from_params(self):

        cmd = 'grep THREAD params.ini | grep -v "#"'
        #result = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
        status, result = self._get_subprocess_info(cmd)

        return_val = 0

        if status:
            if re.search('TBB_THREAD_COUNT=', result):
                return_val = re.search(
                    'TBB_THREAD_COUNT=(\d+)', result).group(1)

        return int(return_val)

    # end _get_thread_cpu_from_params

    def _taskset_affinity_mask(self, ip=0, fd=0, cpu_threads=0):

        if self.set_affinity_mask == 0:
            return

        if ip == 0:
            ip = self.cn_ips[self.cn_index]
        if fd == 0:
            fd = self.cn_ssh_fds[self.cn_index]
        if cpu_threads == 0:
            cpu_threads = self._get_thread_cpu_from_params()
            self.cpu_threads = cpu_threads

        #
        # TODO derive it based on num cores/system
        # For now, prefer CPU1
        #

        if cpu_threads == 0:
            mask = "0xffffff"
        elif cpu_threads == 1:
            mask = "0x000040"
        elif cpu_threads == 8:
            mask = "0x0c0fc0"
        elif cpu_threads == 16:
            mask = "0xfc0fc3"
        elif cpu_threads == 24:
            mask = "0xffffff"

        self.affinity_mask = mask

        #
        # Set affinity mask
        #
        cmd = "taskset -p %s `pidof contrail-control`" % mask
        self._log_print(
            "INFO: setting affinity mask on: %s number cpu_threads: %s cmd: %s" %
            (ip, cpu_threads, cmd))
        result = fd.execCmd(cmd)

        return

    # end _taskset_affinity_mask

    def _get_affinity_mask(self, fd):

        #
        # Get affinity mask
        #
        cmd = self._args.get_affinity_mask_cmd
        result = fd.execCmd(cmd, ip, username, password)
        if result != None:
            result = result[:-1]

        return result

    # end _get_affinity_mask

    def _restart_cn(self, why=0, restart_anyway=0):
        '''Stop then start control node
        '''
        #
        # Let stressfactr control any restarts
        #
        if self._args.multiple_testservers_running:
            return

        #
        # Skip if no overriding knob to params - used for delete vn bug, will remove soon
        #
        if not restart_anyway and not int(self._args.restart_cn):
            return

        #
        # Restart all control nodes
        #
        for i in range(len(self.cn_ips)):

            #
            # Get contrail-control fd and ip address
            #
            cn_ssh_fd = self.cn_ssh_fds[i]
            cn_ip = self.cn_ips[i]
            cn_distro = self.cn_linux_distribution[i]

            #
            # Get command to restart the control node - note that fedora uses systemctl at the moment
            #
            cmd = self._args.control_node_restart_cmd
            if cn_distro == self._args.linux_fedora:
                cmd = self._args.control_node_restart_fedora_cmd

            #
            # Issue restart
            #
            if type(why) == str:
                msg = "INFO: restarting control node: %s %s with cmd: %s" % (
                    cn_ip, why, cmd)
            else:
                msg = "INFO: restarting control node: %s with cmd: %s" % (
                    cn_ip, cmd)
            self._log_print("INFO: restarting control node: %s with cmd: %s" %
                            (cn_ip, cmd))
            return_val = cn_ssh_fd.execCmd(cmd, cn_ip, username, password)

        #
        # Sleep a bit
        #
        sleep_time = int(self._args.sleeptime_after_cn_restart)
        self._log_print(
            "INFO: sleeping: %ss after restartng all control nodes result: %s" %
            (sleep_time, return_val))
        time.sleep(sleep_time)

        return

    # end _restart_cn

    def _get_env_variables(self):

        try:
            self._args.bgp_env
            self.bgp_env = self._args.bgp_env
        except:
            self.bgp_env = ''

    # end _get_env_variables

    def _get_env_string(self, string1, string2):

        return_val = string1

        try:
            #
            # Check if param exits
            #
            self._args.string1

            #
            # Concatenate env variable
            #
            return_val = "%s %s=%s" % (string2, string1, self._args.srting1)

        except:
            return_val = ''

        return

    # end _get_env_string

    def check_if_swapping(self, result, who):
        '''Check if system is swapping
        '''
        return_val = False
        if not re.search(' 0 kB', result):
            self._log_print(
                "WARNING: system swapping:{0} -> reboot device".format(who))
            return_val = True

        return return_val

    # end check_if_swapping

    def _get_localhost_info(self):
        '''Machine and distribution on which the test-script is running
        '''

        #
        # Get localhost IP
        #
#	if 'TEST_CONFIG_FILE' in os.environ :
#            self.ini_file= os.environ.get('TEST_CONFIG_FILE')
#        else:
#            self.ini_file= 'sanity_params.ini'
#        self.inputs= ContrailTestInit(
#                self.ini_file, stack_user=self._args.username,
#                stack_password=self._args.password, project_fq_name=['default-domain', 'default-project'])
#	self.inputs.setUp()
#	cmd = 'resolveip -s `hostname`'
#        cmd = "ip addr show | \grep '192\.168\.200' | awk '{print $2}' | cut -d '/' -f 1"
#        status, ip = self._get_subprocess_info(cmd)
#
#        if status:
#            self.localhost_ip = ip[:-1]
#        else:
#            self._log_print("ERROR: Cannot resolve hostname")
#            sys.exit()

        #
        # Get linux distribution for test server
        #
        #self.linux_distribution = platform.linux_distribution()[0]
        local_host = socket.gethostname()
        self.localhost_ip = self.inputs.host_data[
            local_host]['host_control_ip']
        self._log_print("INFO: localhost testserver ip: %s" %
                        self.localhost_ip)

    # end _get_localhost_info
    def _get_prog_fds(self):

        #
        # Login info for servers
        #
        username = self._args.ssh_username
        password = self._args.ssh_password

        #
        # Get API ssh fd
        #
        self.api_ssh_fd = remoteCmdExecuter()
        self.api_ssh_fd.execConnect(
            self.inputs.auth_ip, username, password)

        #
        # Get Control Nodes(s) ssh fd, ips, and introspect self
        #
        #cn_ips = re.split(",", "".join(self._args.control_node_ips.split()))
        cn_ips = self.inputs.bgp_control_ips
        self.cn_ssh_fds = []
        self.cn_introspect = []

        for i in range(len(cn_ips)):
            self.cn_ssh_fds.append(remoteCmdExecuter())
            self.cn_ssh_fds[i].execConnect(cn_ips[i], username, password)
            self.cn_introspect.append(ControlNodeInspect(cn_ips[i]))

        #
        # Get test server fds and ips
        #
        #ts_ips = re.split(",", "".join(self._args.test_server_ips.split()))
        ts_ips = self.inputs.cfgm_control_ips
        self.ts_ssh_fds = []
        self.ts_ips = []

        for i in range(len(ts_ips)):
            self.ts_ssh_fds.append(remoteCmdExecuter())
            self.ts_ssh_fds[i].execConnect(ts_ips[i], username, password)
            self.ts_ips.append(re.search('\d+.*\d+', ts_ips[i]).group())

        #
        # Get router fds and ips
        #
        rtr_username = self._args.rtr_username
        rtr_password = self._args.rtr_password

        #rtr_ips = re.split(",", "".join(self._args.rtr_ips.split()))
        rtr_ips = [self.inputs.ext_routers[0][1]]
        self.rt_ssh_fds = []
        self.rtr_ips = []

        for i in range(len(rtr_ips)):
            self.rt_ssh_fds.append(remoteCmdExecuter())
            self.rt_ssh_fds[i].execConnect(rtr_ips[i], username, password)
            self.rtr_ips = rtr_ips
            #self.rtr_ips.append(re.search('\d+.*\d+', rtr_ips[i]).group())
        return

    # end _get_prog_fds

    def _get_cn_ispec(self, ip, index):

        cn_ispec = ControlNodeInspect(ip)

        return cn_ispec

    # end _get_cn_ispec

    def _open_logfile(self, who):

        #
        # Create logdir if needed
        #
        logdir = self._args.logdir_name
        if not os.path.exists(logdir):
            try:
                os.mkdir(logdir)
            except (SystemExit, KeyboardInterrupt):
                raise
            except Exception, e:
                print (
                    'ABORT: Failed to create logdir directory, since this is a scaling script, check that the number of file descriptors (max files) has not been exceeded:[lsof -n, and ulimit -n] or (2) check for directory name err for log in params (should be "<logdir>/<name>" found: %s aborting script..' % logdir)
                self.cleanup()
                sys.exit()

        if who == 'init':
            if self.pre_scale_setup:
                self.fd_name = "%s/%s_%s.log" % (self._args.logdir_name,
                                                 self._args.logfile_name_parent, self.pid)
            else:
                self.fd_name = "%s/%s_%s.log" % (self._args.logdir_name,
                                                 self._args.logfile_name_flap_agent_scale_test, self.pid)

            self.fd = self._open_file_for_write(self.fd_name)

        elif who == 'summary':
            for file in os.listdir(logdir):
                if file.startswith(self._args.result_averages_logfilename):
                    try:
                        file_fq_name = os.getcwd() + '/' + logdir + '/' + file
                        os.remove(file_fq_name)
                    except OSError:
                        pass
            try:
                pid = int(self._args.run_get_result_prior_run)
                if pid == 0:
                    pid = self.pid
            except:
                pid = self.pid

            self.summary_fd_name = "%s/%s_%s.txt" % (self._args.logdir_name,
                                                     self._args.result_averages_logfilename, pid)
            self.summary_fd = self._open_file_for_write(self.summary_fd_name)

        return

    # end _open_logfile

    def _open_file_for_write(self, filename):

        #
        # Open new file, check for sys errs
        #
        try:
            fd = open(filename, 'w')
        except (SystemExit, KeyboardInterrupt):
            raise
        except Exception, e:
            print (
                'ABORT: Failed to open file: %s, since this is a scaling script, check that the number of file descriptors (max files) has not been exceeded:[lsof -n, and ulimit -n]' % filename)
            self.cleanup()
            sys.exit()

        return fd

    # end _open_file_for_write

    def check_and_fix_connectivity(self, cn_self, src, dst, xmpp_src_net, test_server_ip, nagents, dev, index):
        '''Make sure control node can ping xmpp_src IP addresses
           If not, "route add" it and try again. Otherwise abort script
        '''

        #
        # Return if the skip_check bit is set..
        #
        if int(self._args.skip_check_and_fix_connectivity):
            return

        #
        # Add a static route from the control node back to the xmpp_src
        #
        if not self.standalone_mode:
            net = "%s/%s" % (IPNetwork(xmpp_src_net).network,
                             IPNetwork(xmpp_src_net).prefixlen)
            route_add_cmd = "route add -net {0} gw {1}".format(net,
                                                               test_server_ip)
            try:
                result = cn_self.execCmd(
                    route_add_cmd, self._args.ssh_username, self._args.ssh_password, src, test_server_ip)
            except:
                pass

        #
        # Check secondaries, configure them if needed
        #
        self.check_and_fix_secondaries(
            dev, dst, nagents, xmpp_src_net, test_server_ip)

        #
        # Return if the skip_ping bit is set..
        #
        if int(self._args.skip_check_and_fix_connectivity_ping):
            return

        #
        # Get last ip address as well - used to estimate all addresses pingable
        #
        last_dst = str((IPAddress(dst)) + nagents)

        #
        # Fron the control node ping first and last xmpp_src in advance in case there is no arp entry.
        #
        ping_cmd = "ping {0} -I {1} -c 2 -W 1 ".format(dst, src)
        ping_cmd2 = "ping {0} -I {1} -c 2 -W 1 ".format(last_dst, src)
        result = cn_self.execCmd(ping_cmd)
        result2 = cn_self.execCmd(ping_cmd2)

        #
        # Fron the control node ping first and last xmpp_src, check for 0 drops
        #
        pattern = ' 0% packet loss'
        ping_cmd = 'ping {0} -I {1} -c 1 -W 1 | grep -i "{2}"'.format(dst,
                                                                      src, pattern)
        ping_cmd2 = 'ping {0} -I {1} -c 1 -W 1 | grep -i "{2}"'.format(last_dst,
                                                                       src, pattern)
        result = cn_self.execCmd(ping_cmd)
        result2 = cn_self.execCmd(ping_cmd2)

        #
        # Check first xmpp_src address for ping failure.. Abort if still not working
        #
        if result == None or (not re.search(pattern, result, re.IGNORECASE)):
            self._log_print(
                "WARNING: Pings not working to first xmpp_src address, check local secondaries are configured and up. Aborting script due to failure if this cmd: ping_cmd:{0}  result:{1}".format(ping_cmd, result))
            sys.exit()

        #
        # Check last xmpp_src address for ping failure..
        #
        if result2 == None or (not re.search(pattern, result2, re.IGNORECASE)):
            self._log_print(
                "ERROR: Pings not working to last xmpp_src address, check local secondaries are configured and up. Aborting script due to failure if this cmd: ping_cmd:{0}  result:{1}".format(ping_cmd, result2))
            sys.exit()

        self._log_print(
            "INFO: Connectivity [ok] between cn:{0} and xmpp_server:{1}, result:{2}".format(src, dst, result))

        return result

    # end check_and_fix_connectivity

    def check_and_fix_secondaries(self, dev, dst, nagents, xmpp_src_net, test_server):

        if int(self._args.skip_check_and_fix_secondaries):
            return

        #
        # Convert the ip address string into type IPAddress so easy ip math will work
        #
        ip = IPAddress(dst)

        #
        # Use the same prefix mask length for all the addresses
        #
        prefix_len = IPNetwork(xmpp_src_net).prefixlen

        #
        # Check if secondary is present on localhost, if not configure it.
        # Add a few more than needed to avoid one-off issues
        #
        devnull = open('/dev/null', 'w')
        for i in range(1, nagents + 2):
            #
            # Configure secondary address
            #
            cmd = 'ip addr add {0}/{1} dev {2}'.format(ip, prefix_len, dev)
            #self._log_print ("DEBUG: adding secondary prefix: %s" %cmd)
            status, result = self._get_subprocess_info(
                cmd, print_err_msg_if_encountered=0)

            ip += 1

        devnull.close()
        return

    # end check_and_fix_secondaries

    def _get_cn_range(self):

        #
        # Get control node(s) based on rules
        #
        if self._args.ts_cn_one_to_one:
            cn_start_index = self.cn_index
            num_control_nodes = self.cn_index + 1
        else:
            cn_start_index = 0
            num_control_nodes = len(self.cn_ips)

        return cn_start_index, num_control_nodes

    # end _get_cn_range

    def add_secondaries(self):

        #
        # Return if the skip_check_and_fix_connectivity bit is set..
        #
        if int(self._args.skip_check_and_fix_connectivity):
            return

        self._log_print("INFO: adding secondaries")

        #
        # Configure device up on local test server
        #
        cmd = "ifconfig %s up" % self.dev
        status, result = self._get_subprocess_info(cmd)
        if status == None:
            self._log_print(
                "ABORT: problem configuring device: %s up on test server: %s" %
                (self.localhost_ip, cmd))
            self.cleanup()
            sys.exit()
        self._log_print("INFO: configured device: %s up on test server: %s" %
                        (self.dev, self.localhost_ip))

        #
        # Get control node(s) forloop index vals based on rules
        #
        cn_start_index, num_control_nodes = self._get_cn_range()

        #
        # Handle all control nodes  - each one has a route add back towards the test server
        #
        for i in range(cn_start_index, num_control_nodes):

            #
            # Get contrail-control fd and ip address
            #
            cn_ssh_fd = self.cn_ssh_fds[i]
            cn_ip = self.cn_ips[i]

            #
            # Handle all blocks
            #
            kindex = 0
            for j in range(self.nblocks_of_vns):
                for k in range(self.num_iterations):

                    #
                    # Add secondaries to test server running bgp_stress_test and route from contrail-control back to it
                    #
                    self.check_and_fix_connectivity(cn_ssh_fd, cn_ip, self.xmpp_src[kindex], self.xmpp_src_net[
                        kindex], self.localhost_ip, self.nagents[k], self.dev, kindex)

                    #
                    # Increment the next xmpp_src index
                    #
                    kindex += 1

                # end iteration loop
            # end block loop
        # end control_node loop

    # end add_secondaries

    def start_bgp_scale(self, oper=''):

        if not int(self._args.run_bgp_scale):
            return

        self._log_print("INFO: preparing BGP scale test...")
        self._log_print("INFO: expected_prefixes: %s based on params: %s" %
                        (self.total_expected_prefixes, self.test_param_name))

        #
        # Check if bgp_stress_test is there, abort with an error if not
        #
        status, result = self._get_subprocess_info(
            'ls -lt bgp_stress_test', print_err_msg_if_encountered=0)
        if status == None:
            self._log_print(
                "ABORT: no bgp_stress_test binary found on test server")
            self.cleanup()
            sys.exit()
        else:
            self._log_print("INFO: bgp_stress binary is present")
            self._log_print("INFO: bgp_stress file info: %s" % result[:-1])

        #
        # Get operation, function call param overrides params file
        #
        if not oper:
            oper = self._args.bgp_oper

        #
        # Get program control values
        #
        num_iterations = self.num_iterations
        test_id = int(self._args.test_id)
        start_block_num = int(self._args.start_block_num)
        nblocks_of_vns = int(self._args.nblocks_of_vns)
        background = self.run_bgp_scale_in_background

        self.current_run_count = 0
        bg_run_count = 0

        #
        # Get stats before BGP scale tests start
        #
        self._report_stats("Stats Before BGP Scale {0}".format(
            oper), self.report_stats_before_and_after_tests)
        self._report_stat_during_test(self.report_stat_item_during_test,
                                      msg='stat before starting test', server_type='all', item='memory')

        #
        # Use the block index so that each iteration run uses
        # a unique starting VN name to iterate over
        #
        block_index = 1
        for i in range(num_iterations):

            #
            # Derive timeout val if this is a flap test, want it to vary
            #
            sleeptime = self.get_sleeptime_seconds(
                i + 1, num_iterations, oper)

            #
            # Keep track of the total number of bgp_stress_test calls
            #
            self.current_run_count += 1

            #
            # call to start the bgp_stress test
            #
            self.run_bgp_scale(self.cn_index, block_index,
                               i, test_id, oper, sleeptime)

            #
            # Get the next agent id
            #
            test_id += 1

            if (not background) and ((i + 1) != num_iterations):
                self._log_print("INFO: Sleeping %s seconds in between runs" %
                                self._args.sleeptime_between_runs)
                time.sleep(int(self._args.sleeptime_between_runs))

            block_index += 1

        #
        # If running in background mode, wait until all the processes are done, or timeout
        #
        if background:
            self._wait_until_processes_finish()

        #
        # Get stats after BGP scale tests are over
        #
        self._report_stats("Stats After BGP Scale {0}".format(
            oper), self.report_stats_before_and_after_tests)

    # end start_bgp_scale

    def _get_ifdev(self):

        #
        # Get interface device name that is suitable for adding secondaries
        #

        #
        # Get all ifconfig output, barring bridges etc
        #
        #cmd = self._args.get_ifs_ifconfig_cmd
        local_ip = self.inputs.get_host_ip(self.localhost_ip)
        cmd = "ip addr show | grep %s | sed 's/^.*global //'" % local_ip
        status, result = self._get_subprocess_info(
            cmd, print_err_msg_if_encountered=0)
        if status == None:
            self._log_print(
                "ABORT: error getting ifconfig info on test server: %s cmd: %s" %
                (self.localhost_ip, cmd))
            self.cleanup()
            sys.exit()

        #
        # Get high order two bytes from local net
        #
        local_net = re.search('^\d+\.\d+', self.localhost_ip).group()

        #
        # Find an interface that does not have the localhost network
        # or anything close on it
        #
        return_val = 0
        ifs = result[:-1].split("\n")

        for i in range(len(ifs)):

            #
            # Get output of specific interface
            #
            cmd = "%s %s" % (self._args.get_dev_ifconfig_cmd, ifs[i])
            #result = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
            status, result = self._get_subprocess_info(cmd)

            if status:

                #
                # Serach for localhost, don't use if so..
                #
                if re.search(local_net, result, re.IGNORECASE):
                    continue

                #
                # Use this one
                #
                return_val = ifs[i]
                break
        return return_val

    # end _get_ifdev

    def _wait_until_processes_finish(self):

        #
        # Use start_time for timeout eval
        #
        start_time = datetime.now()
        self.time_after_all_processes_launched = start_time

        #
        # Get stats
        #
        self._report_stats("Stats During BGP Scale {0}".format(
            self._args.bgp_oper), self.report_stats_during_bgp_scale)
        self._report_stat_during_test(
            self.report_stat_item_during_test, msg='stat during test', server_type='all', item='memory')

        #
        # Start polling a bit later
        #
        self._log_print(
            "INFO: flap_parent sleeping %s seconds before checking if child processes are done yet" %
            int(self._args.sleeptime_before_polling_processes))
        time.sleep(int(self._args.sleeptime_before_polling_processes))

        #
        # Once every minute or so, check if processes are still allive
        #
        num_terminated = 0
        timeout_status, timed_minutes = self._check_timout_status(start_time)
        while 1:

            #
            # Loop through the list of exiting processes
            #
            still_kicking = False
            for i in range(self.current_run_count):

                #
                # If we're timed out, end the process, otherwise mark at least one as still_kicking
                #
                if self.process[i].is_alive():
                    still_kicking |= True
                    if timeout_status:
                        self.process[i].terminate()
                        num_terminated += 1
                        self._log_print(
                            "DEBUG: killing bgp_scale_mock_agent processes %s num terminated: %s" % (i + 1, num_terminated))
                else:
                    still_kicking |= False
                    self._log_print(
                        "DEBUG: bgp_scale_mock_agent processes %s ended naturally, num terminated: %s still_kicking: %s" %
                        (i + 1, num_terminated, still_kicking))

            # end for loop

            #
            # Check if we timed out, if so processes will be terminated outside of this loop
            #
            timed_out, timed_minutes = self._check_timout_status(start_time)
            if timed_out:
                self._log_print(
                    "WARNING: timeout waiting for child bgp_scale_mock_agent processes to complete, waited: %smin" %
                    int(self._args.timeout_minutes_wait_process))
                break

            #
            # End parent script if all the children are done
            #
            if not still_kicking:
                self._log_print(
                    "INFO: all bgp_scale_mock_agent processes done")
                break

            #
            # Sleep before polling again
            #
            time_left = int(self._args.timeout_minutes_wait_process) - \
                timed_minutes
            self._log_print(
                "INFO: flap_parent sleeping %s seconds before next child bgp_scale_mock_agent process status check, timeout in: %smin" %
                (self._args.sleeptime_between_polling_process, time_left))
            time.sleep(int(self._args.sleeptime_between_polling_process))

            #
            # Check stats if needed
            #
            self._report_stat_during_test(
                self.report_stat_item_during_test, msg='stat during test', server_type='all', item='memory')

        # end while loop

        #
        # Try and kill lingering processes anyway..
        #
        self._log_print(
            "INFO: as an over-kill, kill all child bgp_scale_mock_agent processes")
        for i in range(self.current_run_count):
            self.process[i].terminate()

        self._log_print(
            "INFO: all child bgp_scale_mock_agent processes done, waited for ~%s min after launching all" %
            (timed_minutes))
        self._report_stat_during_test(
            self.report_stat_item_during_test, msg='stat after test', server_type='all', item='memory')

        return

    # end _wait_until_processes_finish

    def _check_timout_status(self, t1):

        #
        # Get delta time in minutes, rounding ok
        #
        delta_time_minutes = int(((datetime.now() - t1).seconds) / 60)

        #
        # See if max time was
        #
        status = delta_time_minutes > int(
            self._args.timeout_minutes_wait_process)

        return (status, delta_time_minutes)

    # end _check_timout_status

    def get_sleeptime_seconds(self, iteration_index, num_iterations, oper):

        #
        # Derive sleeptime based on the operation
        #
        if re.search('flap', oper, re.IGNORECASE):
            sleeptime_seconds = int(self._args.sleeptime_flap)
            sleeptime_seconds *= iteration_index
        elif re.search('hold', oper, re.IGNORECASE):
            sleeptime_seconds = int(self._args.sleeptime_hold)
        else:
            sleeptime_seconds = int(
                self._args.sleeptime_between_adding_and_deleting_routes)

        return_val = sleeptime_seconds

        return return_val

    # end get_sleeptime_seconds

    def run_bgp_scale(self, cn_index, block_index, iteration_index, test_id, oper, sleeptime):

        #
        # Misc
        #
        run_id = self.current_run_count

        #
        # Control node
        #
        cn_ssh_fd = self.cn_ssh_fds[cn_index]
        cn_ip = self.cn_ips[cn_index]
        cn_ip_alternate = self.cn_ips_alternate[cn_index]

        #
        # Login info
        #
        cn_usr = self._args.ssh_username
        cn_pw = self._args.ssh_password
        rt_usr = self._args.rtr_username
        rt_pw = self._args.rtr_password

        #
        # Bgp stress call control
        #
        background = self.run_bgp_scale_in_background
        skip_krt_check = self.skip_krt_check
        skip_rtr_check = self.skip_rtr_check
        no_verify_routes = self.no_verify_routes

        #
        # Get one or two Router IP addresses, any more than that are not supported
        #
        rtr_ip = self.rtr_ips[0]
        if len(self.rtr_ips) > 1:
            rtr_ip2 = self.rtr_ips[1]
        else:
            rtr_ip2 = 0

        #
        # Bgp Stress call parameters
        #
        family = self._args.family
        nh = self._args.nh
        ninstances = self.ninstances[iteration_index]
        nagents = self.nagents[iteration_index]
        nroutes = self.nroutes[iteration_index]
        import_targets_per_instance = self.import_targets_per_instance[
            iteration_index]

        #
        # get xmpp_src addresses
        #
        xmpp_source = self.xmpp_src[run_id - 1]
        xmpp_source_net = self.xmpp_src_net[run_id - 1]
        xmpp_start_prefix = self.xmpp_start_prefix[run_id - 1]

        #
        # Set the xmpp_start_prefix to 0 if the "use" flag is not set
        #
        if not int(self._args.use_xmpp_start_prefix):
            xmpp_start_prefix = 0

        #
        # Get optional xmpp_large_prefix knob
        #
        xmpp_start_prefix_large = int(self._args.use_xmpp_start_prefix_large)

        #
        # Get testserver IP address
        #
        test_server = self.localhost_ip

        #
        # Get derived vn name
        #
        self.ri_name = self._get_vn_name(
            block_index, cn_ip, ts_ip=self.localhost_ip)

        #
        # Get the rinstance names
        #
        ri_name = self.ri_name
        ri_domain_and_proj_name = "%s:%s" % (
            self._args.ri_domain_name, self._args.ri_proj_name)

        #
        # Misc
        #
        timeout_minutes_poll_prefixes = int(
            self._args.timeout_minutes_poll_prefixes)

        #
        # Get logfile name for bgp_stress_test and results log
        #
        logfile_name_bgp_stress = "%s/%s_%s.log.%s" % (self._args.logdir_name,
                                                       self._args.logfile_name_bgp_stress, self.pid, run_id)
        logfile_name_results = "%s/%s_%s.log.%s" % (self._args.logdir_name,
                                                    self._args.logfile_name_results, self.pid, run_id)

        #
        # Run call in the background
        # passing the test_server_ips - Ganesha
        if background:
            process = multiprocessing.Process(
                target=bgp_scale_mock_agent, args=(
                    cn_usr, cn_pw, rt_usr, rt_pw, cn_ip, cn_ip_alternate, rtr_ip, rtr_ip2, xmpp_source, ri_domain_and_proj_name, ri_name, ninstances, import_targets_per_instance, family, nh, test_id, nagents, nroutes, oper, sleeptime, logfile_name_bgp_stress,
                    logfile_name_results, timeout_minutes_poll_prefixes, background, xmpp_start_prefix, xmpp_start_prefix_large, skip_krt_check, self.report_stats_during_bgp_scale, self.report_cpu_only_at_peak_bgp_scale, skip_rtr_check, self.bgp_env, no_verify_routes, self._args.logging_etc, self.localhost_ip))
            process.start()
            self.process.append(process)
            self._log_print(
                "INFO: started background bgp_stress_test.%s, pid %d" %
                (run_id, process.pid))
            # time.sleep(1)

        #
        # Run call in synch
        #
        else:
            bgp_scale_mock_agent(
                cn_usr, cn_pw, rt_usr, rt_pw, cn_ip, cn_ip_alternate, rtr_ip, rtr_ip2, xmpp_source, ri_domain_and_proj_name, ri_name, ninstances, import_targets_per_instance, family, nh, test_id, nagents, nroutes, oper, sleeptime, logfile_name_bgp_stress, logfile_name_results,
                timeout_minutes_poll_prefixes, background, xmpp_start_prefix, xmpp_start_prefix_large, skip_krt_check, self.report_stats_during_bgp_scale, self.report_cpu_only_at_peak_bgp_scale, skip_rtr_check, self.bgp_env, no_verify_routes, self._args.logging_etc, self.localhost_ip)
            self._log_print("INFO: started bgp_stress_test.%s" % run_id)

    # end run_bgp_scale
    def _derive_net(self, xmpp_src, block_index, index, num_iterations, addr_type):

        #
        # Derive xmpp_src addresses unless they are provided
        # Use the block id and localhost low-order byte to make them unique
        #
        if len(xmpp_src) >= (num_iterations + 1):
            net = re.search('\d+.*\d+', xmpp_src[index]).group()

            #
            # If the low order byte is a 0. change it to a 1
            # Needed for ping later.
            #
            if re.search('\d+$', net).group() == '0':
                net = IPAddress(net) + 1

        else:
            #
            # Get integer val of the low order byte of localhost IP address
            #
            if addr_type == 'xmpp_prefix':
                local_ip_int = 0
            else:
                #
                # For xmpp_src address, use a common address - this works
                # bc each control node has a separate route add pointing
                # to different testservers.
                #
                if self._args.ts_cn_one_to_one:
                    local_ip_int = 0
                else:
                    local_ip_int = int(
                        re.search('\d+$', self.localhost_ip).group())

            #
            # Get high order byte from params
            #
            byte = re.search('^\d+', xmpp_src[0]).group()
            hiByte = int(byte) + int(block_index) + local_ip_int
            net = IPNetwork("%s/%s" % (hiByte, self._args.xmpp_src_prefix_len))
            net += index

            #
            # Change low order byte to a "1", needed for ping later
            #
            net = IPAddress(net.network) + 1
            #self._log_print ("DEBUG: NET: %s" %net)

        #
        # Get any optional mask
        #
        if re.search('\/\d+$', xmpp_src[0]):
            mask = re.search('\/\d+$', xmpp_src[0]).group()
            net = "%s%s" % (str(net), mask)

        return str(net)

    # end _derive_net

    def _report_stat_during_test(self, report_stats, msg, server_type, item):

        if not report_stats:
            return

        self._log_print("INFO: %s server_type: %s item: %s" %
                        (msg, server_type, item))
        self._log_print(
            "INFO: --start-stat-get---------------------------------------------")

        #
        # Check Control nodes
        #
        if server_type == "cn" or server_type == "all":

            for i in range(len(self.cn_ips)):

                #
                # Get control node info
                #
                fd = self.cn_ssh_fds[i]
                ip = self.cn_ips[i]

                #
                # Get stat item
                #
                process = "contrail-control"
                self._report_stat_item(item, process, ip, fd)

        #
        # Check API servers
        #
        if server_type == "api" or server_type == "all":

            ip = self.inputs.auth_ip
            fd = self.api_ssh_fd

            #
            # Get stat item
            #
            process = "contrail-collector"
            self._report_stat_item(item, process, ip, fd)

        self._log_print(
            "INFO: --end-stat-get---------------------------------------------")
        return

    # end _report_stat_during_test

    def _derive_total_mem_used(self, result):

        #
        # Getmemory vals from /proc/meminfo output
        #
        memory_vals = re.search(
            'MemTotal:\s+(\d+) kB\s+MemFree:\s+(\d+) kB\s+Cached:\s+(\d+) kB', result)

        #
        # Derive total memory used: total - free - cached
        #
        if memory_vals != None:
            total = int(memory_vals.group(1))
            free = int(memory_vals.group(2))
            cached = int(memory_vals.group(3))
            return_val = total - free - cached
        else:
            return_val = None

        return return_val

    # end _derive_total_mem_used

    def _report_stat_item(self, item, process, ip, fd):

        #
        # Check for memory type
        #
        if item == "memory":
            cmd = 'egrep "Mem|Cache|Swap" /proc/meminfo; echo " "; egrep "Active|MemTotal" /proc/meminfo'
            res = fd.execCmd(cmd)
            total_memory_used = self._derive_total_mem_used(res)
            self._log_print("INFO: ip: %s cmd: %s \nresult:\n%s" %
                            (ip, cmd, res))

            cmd = "top -b -n 1 | grep `pidof %s` | gawk '\\''{print $6}'\\''" % process
            res = fd.execCmd(cmd)
            self._log_print("INFO: ip: %s cmd: %s \nresult:\n%s" %
                            (ip, cmd, res))

            #
            # Split val from units
            #
            mem = re.search('^(\d?\d?\d?\d?\d?\.?\d?\d?)(.*)', res)
            if mem != None:
                process_mem = float(mem.group(1))
                unit = mem.group(2)
                normalized_process_mem = process_mem
                if unit == "k":
                    normalized_process_mem *= 1000
                elif unit == "m":
                    normalized_process_mem *= 1000000
                elif unit == "g":
                    normalized_process_mem *= 1000000000
                self._log_print(
                    "INFO: ip: %s total memory used (total-free-cached): %s kB - and total for %s: %s %s normalized: %s" %
                    (ip, total_memory_used, process, process_mem, unit, normalized_process_mem))
            else:
                self._log_print(
                    "INFO: ip: %s total memory used (total-free-cached): %s kB - and total for %s: %s %s" %
                    (ip, total_memory_used, process, res))

            cmd = 'pmap `pidof %s` | grep -i total' % process
            res = fd.execCmd(cmd)
            self._log_print("INFO: ip: %s cmd: %s \nresult:\n%s" %
                            (ip, cmd, res))

            cmd = 'ps -e -orss=,args= | sort -b -k1,1n | pr -TW195 | sort -rn | head -n 20'
            res = fd.execCmd(cmd)
            self._log_print("INFO: ip: %s cmd: %s \nresult:\n%s" %
                            (ip, cmd, res))

            cmd = 'ps -e -ovsz=,args= | sort -b -k1,1n | pr -TW195 | sort -rn | head -n 20'
            res = fd.execCmd(cmd)
            self._log_print("INFO: ip: %s cmd: %s \nresult:\n%s" %
                            (ip, cmd, res))

            cmd = 'vmstat'
            res = fd.execCmd(cmd)
            self._log_print("INFO: ip: %s cmd: %s \nresult:\n%s" %
                            (ip, cmd, res))

    # end _report_stat_item

    def _report_stats(self, msg, report_stats):

        if not report_stats:
            return

        #
        # Get server info
        #
        fd = self.fd
        local_ip = self.localhost_ip
        #cn_ips = re.split (",", "".join(self._args.control_node_ips.split()))
        cn_ips = self.cn_ips

        #
        # if remote servers, get ip addresses
        #
        if not self.standalone_mode:
            api_ip = self.inputs.auth_ip
            api_fd = self.api_ssh_fd

        #
        # Beginning stats info
        #
        self._log_print(
            "INFO: ============================ <Begin Gather> {0} \t==============================".format(msg))

        #
        # Localhost running bgp_stress env variables
        #
        #result1 = cnshell_self.execCmd ('ps e `pidof bgp_stress_test`')
        #self._log_print ("INFO: ip:{0} Localhost ps info with env variables:".format(local_ip))
        #self._log_print ("INFO: ip:{0} 'ps e `pidof bgp_stress_test`\n{1}".format(local_ip, result1))
        #
        # Localhost details
        #
        result1 = subprocess.check_output(
            'ulimit -a',  stderr=subprocess.STDOUT, shell=True)
        result2 = subprocess.check_output(
            'uname -a',  stderr=subprocess.STDOUT, shell=True)
        result3 = subprocess.check_output(
            "cat " + self._model,  stderr=subprocess.STDOUT, shell=True)
        self._log_print(
            "INFO: ip:{0} Localhost uname and ulimit Settings:".format(local_ip))
        self._log_print(
            "INFO: ip:{0} uname -a \n{1}".format(local_ip, result1))
        self._log_print(
            "INFO: ip:{0} ulimit -a \n{1}".format(local_ip, result2))
        self._log_print(
            "INFO: ip:{0} cat " + self._model + "\n{1}".format(local_ip, result3))

        if re.search('Before', msg, re.IGNORECASE):
            result3 = subprocess.check_output(
                'cat params.ini',  stderr=subprocess.STDOUT, shell=True)
            self._log_print(
                "INFO: cat params.ini\n{1}".format(local_ip, result3))

        #
        # Localhost memory info
        #
        mem_result1 = subprocess.check_output(
            'egrep "Mem|Cache|Swap" /proc/meminfo', stderr=subprocess.STDOUT, shell=True)
        mem_result2 = subprocess.check_output(
            'ps -e -orss=,args= | sort -b -k1,1n | pr -TW195 | sort -rn | head -n 20', stderr=subprocess.STDOUT, shell=True)
        mem_result3 = subprocess.check_output(
            'ps -e -ovsz=,args= | sort -b -k1,1n | pr -TW195 | sort -rn | head -n 20', stderr=subprocess.STDOUT, shell=True)
        mem_result4 = subprocess.check_output(
            'vmstat',  stderr=subprocess.STDOUT, shell=True)
        mem_result5 = subprocess.check_output(
            'pmap {0} | grep -i total'.format(self.pid),  stderr=subprocess.STDOUT, shell=True)
        self._log_print("INFO: ip:{0} Localhost Memory:".format(local_ip))
        self._log_print(
            'INFO: ip:{0} egrep "Mem|Cache|Swap" /proc/meminfo\n{1}'.format(local_ip, mem_result1))
        self._log_print(
            'INFO: ip:{0} ps -e -orss=,args= | sort -b -k1,1n | pr -TW195 | sort -rn | head -n 20\n{1}'.format(local_ip, mem_result2))
        self._log_print(
            'INFO: ip:{0} ps -e -ovsz=,args= | sort -b -k1,1n | pr -TW195 | sort -rn | head -n 20\n{1}'.format(local_ip, mem_result3))
        self._log_print(
            'INFO: ip:{0} vmstat\n{1}'.format(local_ip, mem_result4))
        self._log_print(
            'INFO: ip:{0} pmap {1} | grep -i total\n{2}'.format(local_ip, self.pid, mem_result5))

        #
        # Localhost file descriptprs
        #
        result1 = subprocess.check_output(
            'lsof -n | wc -l', stderr=subprocess.STDOUT, shell=True)
        result2 = subprocess.check_output(
            'lsof -n | grep -i tcp | wc -l', stderr=subprocess.STDOUT, shell=True)
        result3 = subprocess.check_output(
            "lsof -p %s | wc -l" % self.pid, stderr=subprocess.STDOUT, shell=True)
        self._log_print(
            "INFO: ip:{0} Localhost File Descriptors (lsof -n, lsof -n | grep -i tcp, lsof -p {1} | wc -l):".format(local_ip, self.pid))
        self._log_print(
            "INFO: ip:{0} Total        fds: {1}".format(local_ip, result1))
        self._log_print(
            "INFO: ip:{0} TCP          fds: {1}".format(local_ip, result2))
        self._log_print(
            "INFO: ip:{0} This script  fds: {1}".format(local_ip, result3))

        #
        # Localhost cpu
        #
        result1 = subprocess.check_output(
            'cat /proc/stat | grep -i cpu', stderr=subprocess.STDOUT, shell=True)
        result2 = subprocess.check_output(
            'top -b | head -15', stderr=subprocess.STDOUT, shell=True)
        self._log_print(
            "INFO: ip:{0} Localhost CPU info (brief):".format(local_ip))
        self._log_print(
            "INFO: ip:{0} cat /proc/stat | grep -i cpu\n{1}".format(local_ip, result1))
        self._log_print(
            "INFO: ip:{0} top -b | head -15\n{1}".format(local_ip, result2))

        if re.search('Before', msg, re.IGNORECASE):
            defs = "Field definitions for /proc/stat, in case you remembered to forget: \n- user: normal processes executing in user mode \n- nice: niced processes executing in user mode \n- system: processes executing in kernel mode \n- idle: twiddling thumbs \n- iowait: waiting for I/O to complete \n- irq: servicing interrupts \n- softirq: servicing softirqs \n- steal: involuntary wait \n- guest: running a normal guest \n- guest_nice: running a niced guest\n"
            self._log_print("INFO: %s" % defs)

        #
        # Localhost crash info
        #
        status, localhost_crash_info = self._get_subprocess_info(
            'ls -lt /var/crashes; ls -lt /var/crash', print_err_msg_if_encountered=0)
        self._log_print("INFO: ip:{0} Localhost Crash info:".format(local_ip))
        self._log_print(
            "INFO: ip:{0} ls -lt /var/crashes; ls -lt /var/crash\n{1}".format(local_ip, localhost_crash_info))
        self._check_for_crash(
            localhost_crash_info, "Localhost: %s running bgp_stress_test code" % local_ip)

        #
        # Loop through control nodes
        # Get control node(s) for loop index vals based on rules
        #
        cn_start_index, num_control_nodes = self._get_cn_range()
        for i in range(cn_start_index, num_control_nodes):

            cnshell_self = self.cn_ssh_fds[i]
            cn_ip = cn_ips[i]

            #
            # Control node env variables, contrail-status, contrail-versions, and ls of /usr/bin/contrail-control
            #
            result1 = cnshell_self.execCmd('ps e `pidof contrail-control`')
            result2 = cnshell_self.execCmd(
                'contrail-status; contrail-version')
            result3 = cnshell_self.execCmd(
                'ls -lt %s' % self._args.control_node_binary_location)
            result4 = cnshell_self.execCmd("cat " + self._model)
            self._log_print(
                "INFO: ip:{0} Control Node ps info (with env vars) and version:".format(cn_ip))
            self._log_print(
                "INFO: ip:{0} ps e `pidof contrail-control`\n{1}".format(cn_ip, result1))
            self._log_print(
                "INFO: ip:{0} contrail-status; contrail-version\n{1}".format(cn_ip, result2))
            self._log_print(
                "INFO: ip:{0} ls -lt {1}\n{2}".format(cn_ip, self._args.control_node_binary_location, result3))
            self._log_print(
                "INFO: ip:{0} cat " + self._model + "\n{1}".format(cn_ip, result4))

            #
            # Control node ulimit settings
            #
            result1 = cnshell_self.execCmd(
                'cat /proc/`pidof contrail-control`/limits')
            result2 = cnshell_self.execCmd('uname -a')
            self._log_print(
                "INFO: ip:{0} Control Node uname and ulimit Settings:".format(cn_ip))
            self._log_print(
                "INFO: ip:{0} cat /proc/`pidof contrail-control`/limits\n{1}".format(cn_ip, result1))
            self._log_print(
                "INFO: ip:{0} ulimit -a\n{1}".format(cn_ip, result2))

            #
            # Control Node memory info
            #
            mem_result1 = cnshell_self.execCmd(
                'egrep "Mem|Cache|Swap" /proc/meminfo; echo " "; egrep "Active|MemTotal" /proc/meminfo')
            mem_result2 = cnshell_self.execCmd(
                'ps -e -orss=,args= | sort -b -k1,1n | pr -TW195 | sort -rn | head -n 20')
            mem_result3 = cnshell_self.execCmd(
                'ps -e -ovsz=,args= | sort -b -k1,1n | pr -TW195 | sort -rn | head -n 20')
            mem_result4 = cnshell_self.execCmd('vmstat')
            mem_result5 = cnshell_self.execCmd(
                "pmap `pidof contrail-control` | grep -i total")
            self._log_print('INFO: ip:{0} Control Node Memory:'.format(cn_ip))
            self._log_print(
                'INFO: ip:{0} egrep "Mem|Cache|Swap" /proc/meminfo; echo " "; egrep "Active" /proc/meminfo\n{1}'.format(cn_ip, mem_result1))
            self._log_print(
                'INFO: ip:{0} ps -e -orss=,args= | sort -b -k1,1n | pr -TW195 | sort -rn | head -n 20\n{1}'.format(cn_ip, mem_result2))
            self._log_print(
                'INFO: ip:{0} ps -e -ovsz=,args= | sort -b -k1,1n | pr -TW195 | sort -rn | head -n 20\n{1}'.format(cn_ip, mem_result3))
            self._log_print(
                'INFO: ip:{0} vmstat\n{1}'.format(cn_ip, mem_result4))
            self._log_print(
                'INFO: ip:{0} pmap `pidof contrail-control` | grep -i total\n{1}'.format(cn_ip, mem_result5))

            #
            # Check control node swap info
            #
            result = cnshell_self.execCmd('egrep "SwapCached" /proc/meminfo')
            self.check_if_swapping(
                result, "control node: %s - %s" % (cn_ip, msg))

            #
            # Control Node file descriptprs
            #
            result1 = cnshell_self.execCmd('lsof -n | wc -l')
            result2 = cnshell_self.execCmd('lsof -n | grep -i tcp | wc -l')
            result3 = cnshell_self.execCmd(
                'lsof -p `pidof contrail-control` | wc -l')
            # result3 = cnshell_self.execCmd ('lsof -i | wc -l') # can hang
            # system...
            self._log_print(
                "INFO: ip:{0} Control Node File Descriptors (lsof -n, lsof -p `pidof contrail-control`, lsof -n | grep -i tcp | wc -l):".format(cn_ip))
            self._log_print(
                "INFO: ip:{0} Total        fds: {1}".format(cn_ip, result1))
            self._log_print(
                "INFO: ip:{0} TCP          fds: {1}".format(cn_ip, result2))
            self._log_print(
                "INFO: ip:{0} Control Node fds: {1}".format(cn_ip, result3))

            result1 = cnshell_self.execCmd('netstat -vatn | wc -l')
            self._log_print(
                'INFO: ip:{0} Control Node Open Ports and Established TCP Sessions "netstat -vatn | wc -l"\n'.format(cn_ip, result1))

            #
            # Control Node cpu
            #
            result1 = cnshell_self.execCmd('cat /proc/stat | grep -i cpu')
            result2 = cnshell_self.execCmd('top -b | head -15')
            self._log_print(
                "INFO: ip:{0} Control Node CPU info (brief):".format(cn_ip))
            self._log_print(
                "INFO: ip:{0} cat /proc/stat | grep -i cpu\n{1}".format(cn_ip, result1))
            self._log_print(
                "INFO: ip:{0} top -b | head -15\n{1}".format(cn_ip, result2))

            #
            # Control node crash info
            #
            if not self.standalone_mode:
                cn_crash_info = cnshell_self.execCmd(
                    'ls -lt /var/crashes; ls -lt /var/crash')
                self._log_print(
                    "INFO: ip:{0} Control Node Crash info:".format(cn_ip))
                self._log_print(
                    "INFO: ip:{0} ls -lt /var/crashes; ls -lt /var/crash\n{1}".format(cn_ip, cn_crash_info))
                self._check_for_crash(
                    cn_crash_info, "Control node: %s" % cn_ip)

        # end cn_ips

        #
        # Get api server info
        #
        if not self.standalone_mode:
            #
            # api server memory info
            #
            self._log_print('INFO: ip:{0} Api Server Memory:'.format(api_ip))
            mem_result1 = api_fd.execCmd(
                'egrep "Mem|Cache|Swap" /proc/meminfo; echo " "; egrep "Active|MemTotal" /proc/meminfo')
            self._log_print(
                'INFO: ip:{0} egrep "Mem|Cache|Swap" /proc/meminfo; echo " "; egrep "Active" /proc/meminfo\n{1}'.format(api_ip, mem_result1))
            mem_result2 = api_fd.execCmd(
                'ps -e -orss=,args= | sort -b -k1,1n | pr -TW195 | sort -rn | head -n 20')
            self._log_print(
                'INFO: ip:{0} ps -e -orss=,args= | sort -b -k1,1n | pr -TW195 | sort -rn | head -n 20\n{1}'.format(api_ip, mem_result2))
            mem_result3 = api_fd.execCmd(
                'ps -e -ovsz=,args= | sort -b -k1,1n | pr -TW195 | sort -rn | head -n 20')
            self._log_print(
                'INFO: ip:{0} ps -e -ovsz=,args= | sort -b -k1,1n | pr -TW195 | sort -rn | head -n 20\n{1}'.format(api_ip, mem_result3))
            mem_result4 = api_fd.execCmd('vmstat')
            self._log_print(
                'INFO: ip:{0} vmstat\n{1}'.format(api_ip, mem_result4))
            mem_result5 = api_fd.execCmd("du -skh /home/cassandra")
            self._log_print(
                'INFO: ip:{0} du -skh /home/cassandra\n{1}'.format(api_ip, mem_result5))
            mem_result6 = api_fd.execCmd(
                "find / -name cassandra | gawk '\\''{print \"du -skh \" $1}'\\'' > /tmp/t.sh;sh /tmp/t.sh")
            self._log_print(
                'INFO: ip:{0} find and du all cassandra\n{1}'.format(api_ip, mem_result6))
            mem_result7 = api_fd.execCmd("cat " + self._model)
            self._log_print(
                "INFO: ip:{0}" + self._model + "\n{1}".format(api_ip, mem_result7))
            mem_result8 = api_fd.execCmd(
                'cat /proc/`pidof contrail-collector`/io')
            self._log_print(
                "INFO: ip:{0} cat /proc/`pidof contrail-collector`/io\n{1}".format(api_ip, mem_result8))

            #
            # api server crash info
            #
            api_crash_info = api_fd.execCmd(
                'ls -lt /var/crashes; ls -lt /var/crash')
            self._log_print(
                "INFO: ip:{0} API Server Crash info:".format(api_ip))
            self._log_print(
                "INFO: ip:{0} ls -lt /var/crashes; ls -lt /var/crash\n{1}".format(api_ip, api_crash_info))
            self._check_for_crash(api_crash_info, "API server: %s" % api_ip)

            #
            # api server cpu info
            #
            result1 = api_fd.execCmd('cat /proc/stat | grep -i cpu')
            result2 = api_fd.execCmd('top -b | head -15')
            self._log_print(
                "INFO: ip:{0} API Server CPU info (brief):".format(api_ip))
            self._log_print(
                "INFO: ip:{0} cat /proc/stat | grep -i cpu\n{1}".format(api_ip, result1))
            self._log_print(
                "INFO: ip:{0} top -b | head -15\n{1}".format(api_ip, result2))

        self._log_print(
            "INFO: ============================ <End Gather> {0} \t==============================".format(msg))

        #
        # Get localhost swap info
        #
        result = subprocess.check_output(
            'egrep "SwapCached" /proc/meminfo', stderr=subprocess.STDOUT, shell=True)
        self.check_if_swapping(result, "localhost: %s - %s" % (local_ip, msg))

        #
        # Get api server memory info
        #
        if not self.standalone_mode:
            result = api_fd.execCmd('egrep "SwapCached" /proc/meminfo')
            self.check_if_swapping(result, "api server: %s - %s" %
                                   (api_ip, msg))
        else:
            pass

        return

    # end _report_stats

    def _check_for_crash(self, result, who):
        '''Check if system crashed
        '''
        return_val = False
        if re.search('core', result):
            self._log_print(
                "WARNING: crash found on: {0} crash files:\n{1}".format(who, result))
            return_val = True

        return return_val

    # end _check_for_crash

    def _get_nroutes(self, nroutes_via_params):

        #
        # Get either the value from the params file or command line - the latter overrides
        #
        if self._args.nroutes_per_all_agents:
            return_val = self._args.nroutes_per_all_agents
        else:
            return_val = nroutes_via_params

        return int(return_val)

    # end _get_nroutes

    def _get_ulimit(self, line, option="n"):

        #
        # Grab the ulimit setting from the params file
        #
        result = re.search('.*ulimit \-%s (\d+)' % option, line)
        if result:
            return_val = result.group(1)
        else:
            return_val = None

        return return_val

    # end _get_ulimit

    def _get_bgp_start_vals(self):

        #
        # Get ulimit settings for contrail-control and bgp_stress_test
        #
        self.cn_ulimit_n = self._get_ulimit(
            self._args.control_node_restart_cmd)
        self.bgp_ulimit_n = self._get_ulimit(self._args.start_bgp_test_cmd)

        #
        # Get cpu info
        #
        self.run_cpu_test = int(self._args.run_cpu_test)
        self.set_affinity_mask = int(self._args.set_affinity_mask)

        #
        # Get device where secondary addresses are set
        #
        self.dev = self._get_ifdev()

        #
        # Get list of xmpp_src info
        #
        xmpp_src = re.split(",", "".join(self._args.xmpp_src.split()))
        xmpp_src_prefix_len = self._args.xmpp_src_prefix_len
        xmpp_start_prefix = re.split(
            ",", "".join(self._args.xmpp_start_prefix.split()))

        #
        # Each block runs over the set of "n" interations
        #
        num_blocks = int(self._args.nblocks_of_vns)
        self.nblocks_of_vns = num_blocks

        #
        # Misc
        #
        self.set_general_vn_name_across_testservers = int(
            self._args.set_general_vn_name_across_testservers)
        self.run_bgp_scale_in_background = int(
            self._args.run_bgp_scale_in_background)
        self.skip_krt_check = int(self._args.skip_krt_check)
        self.report_stats_before_and_after_tests = int(
            self._args.report_stats_before_and_after_tests)
        self.report_stats_during_bgp_scale = int(
            self._args.report_stats_during_bgp_scale)
        self.report_cpu_only_at_peak_bgp_scale = int(
            self._args.report_cpu_only_at_peak_bgp_scale)
        self.report_stat_item_during_test = int(
            self._args.report_stat_item_during_test)

        try:
            self._args.kill_all_python_on_cleanup
            self.kill_all_python_on_cleanup = int(
                self._args.kill_all_python_on_cleanup)
        except:
            self.kill_all_python_on_cleanup = 0

        try:
            self._args.skip_rtr_check
            self.skip_rtr_check = int(self._args.skip_rtr_check)
        except:
            self.skip_rtr_check = 0

        try:
            self._args.no_verify_routes
            self.no_verify_routes = int(self._args.no_verify_routes)
        except:
            self.no_verify_routes = 0

        #
        # Get number of iterations. For each iteration, use values as defined
        # in the following params file arrays:
        #
        #    ninstances=n1,n2,n3,...n<n>
        #    nagents=n1,n2,n3,...n<n>
        #    nroutes=n1,n2,n3,...n<n>
        #    import_targets_per_instance=n1,n2,n3,...n<n>
        #
        # The num_iterations value must match the array elements 1-1. Array
        # elemnts can be lengthier but not shorter.
        #
        num_iterations = int(self._args.num_iterations)
        self.num_iterations = num_iterations
        self.run_bgp_scale_in_background = int(
            self._args.run_bgp_scale_in_background)
        ninstances_list = self._args.ninstances.split(",")
        nagents_list = self._args.nagents.split(",")
        nroutes_list = self._args.nroutes.split(",")
        import_targets_per_instance_list = self._args.import_targets_per_instance.split(
            ",")

        #
        # Get env variables for call to bgp_stress_test
        #
        self._get_env_variables()

        #
        # Check that the params item has enough elemnts for the number of iterations - script
        # will abort if there are not enough elements
        #
        self.check_param_has_enough_elements(
            'ninstances', ninstances_list, num_iterations)
        self.check_param_has_enough_elements(
            'nagents', nagents_list, num_iterations)
        self.check_param_has_enough_elements(
            'nroutes', nroutes_list, num_iterations)
        self.check_param_has_enough_elements(
            'import_targets_per_instance', import_targets_per_instance_list, num_iterations)

        #
        # Preload control node info prior to tests.
        # Change upper byte for each start prefix for each contrail-control and get #cpus
        #
#        cn_ips = re.split(",", "".join(self._args.control_node_ips.split()))

        cn_ips = self.inputs.bgp_control_ips
        self.cn_ips = self.inputs.bgp_control_ips
        self.cn_ips_alternate = self.inputs.bgp_control_ips
#        for index in range(len(cn_ips)):
#
#            #
# Get Control Node IP.
#            #
#            self.cn_ips.append(re.search('\d+.*\d+', cn_ips[index]).group())
#            self.cn_ips_alternate.append("192.168.200." + re.search('\d+$', cn_ips[index]).group())
#
#        #
# Check for test server to control node rules - note that the arg is passed in
# and not in the params file
#        #
        if self._args.ts_cn_one_to_one:
            self.cn_index = int(self._args.ts_cn_one_to_one)
        else:
            self.cn_index = 0
#
#        #
# Preload control node env info
#        #
#        try:
#            self._args.cn_env
#            cn_envs = self._args.cn_env.split(",")
#            self.cn_envs = []
#            for index in range(len(cn_envs)):
#                #
# Get Control Node IP, just for readability
#                #
#                self.cn_envs.append(cn_envs[index].strip())
#        except:
#            pass
#
        #
        # Create empty arrays to be filled in next for loop
        #
        self.xmpp_src = []
        self.xmpp_src_net = []
        self.xmpp_start_prefix = []
        self.ninstances = []
        self.nagents = []
        self.nroutes = []
        self.import_targets_per_instance = []

        #
        # Used to stop background processes - fill in during test run
        #
        self.process = []

        #
        # Fill array values of derived xmpp addresses nblocks*ninterations per item
        #
        kindex = 0
        for block_index in range(num_blocks):
            for index in range(num_iterations):

                #
                # Derive start prefix etc, remove whie space
                #
                self.xmpp_src.append(self._derive_net(
                    xmpp_src, block_index, kindex, num_iterations, addr_type='src_addr'))
                self.xmpp_src_net.append("%s/%s" %
                                         (self.xmpp_src[kindex], xmpp_src_prefix_len))
                self.xmpp_start_prefix.append(self._derive_net(
                    xmpp_start_prefix, block_index, kindex, num_iterations, addr_type='xmpp_prefix'))
                kindex += 1

        #
        # Fill array values per iteration,  ninterations per item
        #
        for index in range(num_iterations):
            #
            # Get list of ninstances, nagents, nroutes
            #
            self.ninstances.append(int(ninstances_list[index]))
            self.nagents.append(int(nagents_list[index]))
            #self.nroutes.append (int (nroutes_list[index]))
            self.nroutes.append(self._get_nroutes(nroutes_list[index]))
            self.import_targets_per_instance.append(
                int(import_targets_per_instance_list[index]))

        #
        # Derive run mode:
        #   standalone - test-server, contrail-control, and api-services all run on one node
        #   contrail-control-remote  - test-server and contrail-control run on separate machines
        #
        self.standalone_mode = len(cn_ips) == 1 and (self.localhost_ip == self.inputs.auth_ip) and (
            self.localhost_ip == self.cn_ips[self.cn_index])

        #
        # Use first val as for label
        #
        self.total_expected_prefixes = self.num_iterations * \
            self.ninstances[0] * self.nagents[0] * self.nroutes[0]
        self.test_param_name = "%s_iterations_at_%sx%sx%s" % (
            self.num_iterations, self.ninstances[0], self.nagents[0], self.nroutes[0])

        #
        # Debug for vn add/delete poll timings
        #
        self.num_delete_polls_add = 0
        self.num_delete_polls_del = 0
        self.num_add_polls = 0

    # end _get_bgp_start_vals

    def _get_num_vns(self):

        #
        # If there is a param entry for num_vns, let it overide
        #
        try:
            self._args.num_vns
            return_val = int(self._args.num_vns)
        except:

            #
            # Find the max number of instances in the list of iterations
            # Use that to configure number of VNs per block.
            #
            max_vns = 0
            for i in range(self.num_iterations):
                if int(self.ninstances[i]) > max_vns:
                    max_vns = int(self.ninstances[i])

            return_val = max_vns

        return return_val

    # end _get_num_vns

    def check_param_has_enough_elements(self, item_name, param_item, num_iterations):

        if len(param_item) < num_iterations:
            self._log_print(
                "ERROR: Stop and edit params file, number of elements in '%s' is %s (not enough for the num_iterations==%s)" %
                (item_name, len(param_item), num_iterations))
            self._log_print("ERROR: Exiting..")
            sys.exit()

    # end check_param_has_enough_elements

    def _parse_args(self, args_str):
        '''
        Eg. python flaPagent_scal_test.py
                               --config_file params.ini
        '''

        #
        # Source any specified config/ini file
        # Turn off help, so we print all options in response to -h
        #
        conf_parser = argparse.ArgumentParser(add_help=False)

        conf_parser.add_argument(
            "-c", "--conf_file", help="Specify config file, e.g., prams.ini", metavar="FILE")
#
        args, remaining_argv = conf_parser.parse_known_args(args_str.split())

        defaults = {
            'multiple_testservers_running': 0,
            'nprefixes': 0,
            'ts_cn_one_to_one': 0,
        }

        ksopts = {
            'admin_user': 'root',
            'admin_password': 'contrail123',
            'admin_tenant_name': 'default-domain',
            'vn_name          ': 'demo'
        }
        cwd = os.getcwd()
        args.conf_file = '%s/serial_scripts/control_node_scaling/bgp_scale_params.ini' % cwd
        if args.conf_file:
            config = ConfigParser.SafeConfigParser()
            config.read([args.conf_file])
            defaults.update(dict(config.items("DEFAULTS")))
            if 'BGP_Scale' in config.sections():
                ksopts.update(dict(config.items("Linux")))
                ksopts.update(dict(config.items("Basic")))
                ksopts.update(dict(config.items("Stressfactr")))
                ksopts.update(dict(config.items("Control_node")))
                ksopts.update(dict(config.items("Servers")))
                ksopts.update(dict(config.items("Router")))
                ksopts.update(dict(config.items("Setup")))
                ksopts.update(dict(config.items("VN_Scale")))
                ksopts.update(dict(config.items("Policy_Scale")))
                ksopts.update(dict(config.items("Knobs")))
                ksopts.update(dict(config.items("BGP_Scale")))

        #
        # Override with CLI options
        # Don't surpress add_help here so it will handle -h
        #
        parser = argparse.ArgumentParser(
            #
            # Inherit options from config_parser
            #
            parents=[conf_parser],

            #
            # print script description with -h/--help
            #
            description=__doc__,

            #
            # Don't mess with format of description
            #
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        defaults.update(ksopts)
        parser.set_defaults(**defaults)

        #
        # Use params.ini - it's  hopelessly long lins here...
        #
        #parser.add_argument("--proj_name",              help = "Domain and project name of vn/instance, defaults to 'demo'")
        parser.add_argument("-mu", "--multiple_testservers_running",
                            help="override params to restart control nodes, use when stressfactr runs multiple test servers")
        parser.add_argument("-ts", "--ts_cn_one_to_one",
                            help="each testserver maps to one control node")
        parser.add_argument("-nr", "--nroutes_per_all_agents",
                            help="number prefixes for each case - overrides params file")

        self._args = parser.parse_args(remaining_argv)

        #
        # End a bit more gracefully if no params file indicated
        #
        if not args.conf_file:
            print (
                "ABORTing script no params file specified use: flap_agent_scale_test.py -c param_filename")
            self.cleanup()
            sys.exit()

        return

    # end _parse_args

    # def kill_bgp_stress_python_call (child_name, child_of_child_name, fd,
    # retry = 2, delay = 5):
    def _overkill_lingering_processes(self):

        #
        # Spawned processes (bgp_scale_mock_agent) were cleaned up in a previous
        # call to _wait_until_processes_finish.
        #
        # However, if something went wrong with one of the parent processes
        # (i.e., crashed), we need a way to clean up the spawned processes.
        # As such, clean up (in this order):
        #     python (bgp_stress_test)
        #     bgp_stress_test (spawned by bgp_scale_mock_agent)
        #

        #
        # Get a list of any remaining bgp_stress_test processes
        #
        cmd = 'ps -efww | grep bgp_stress_test | grep -v grep'
        status, bgp_result = self._get_subprocess_info(
            cmd, print_err_msg_if_encountered=0)

        #
        # Get list of any remaining python processes, while precluding this
        # python process
        #
        cmd = 'ps -efww | grep python | grep -v grep | grep -v %s' % self.pid
        status, python_result = self._get_subprocess_info(
            cmd, print_err_msg_if_encountered=0)
        if status:
            # chop newline at the end of the output
            python_lines = python_result.split('\n')[:-1]

        num_bgp_killed = 0
        num_python_killed = 0

        #
        # Loop through all lingering bgp_stress_test processes, use its PID as the
        # associated parent to (over)kill python
        #
        if type(bgp_result) == str:
            # chop newline at the end of the output
            bgp_lines = bgp_result.split('\n')[:-1]

            for i in range(len(bgp_lines)):

                re.search('\d+', bgp_lines[i])
                ppid = int(re.search('\d+', bgp_lines[i]).group())

                try:
                    os.kill(ppid, signal.SIGKILL)
                    num_bgp_killed += 1
                    self._log_print(
                        "DEBUG: sending SIGILL to bgp_stress pid: %s" % ppid)
                except OSError:
                    pass

                #
                # Loop thru python ps output for a match
                #
                if type(python_result) == str:
                    for j in range(len(python_lines)):

                        #
                        # See if the line matches parent bgp_stress_test ppid
                        #
                        if re.search(str(ppid), python_lines[j]):

                            re.search('\d+', python_lines[j])
                            python_pid = int(
                                re.search('\d+', python_lines[j]).group())

                            try:
                                os.kill(python_pid, signal.SIGKILL)
                                num_python_killed += 1
                                self._log_print(
                                    "DEBUG: SIGKILL python pid: %s" % python_pid)
                            except OSError:
                                pass

                    # end looping thru python ps output

            # end looping thru bgp_stress ps output

        #
        # Brute force method in case bgp_stress_test alreday crashed
        # Note this could be a problem if running on a shared system,
        # therefore added a param to control it (kill_all_python_on_cleanup)
        #
        if not self.standalone_mode and self.kill_all_python_on_cleanup:
            if type(python_result) == str:

                for j in range(len(python_lines)):
                    re.search('\d+', python_lines[j])
                    python_pid = int(re.search('\d+', python_lines[j]).group())

                    try:
                        os.kill(python_pid, signal.SIGKILL)
                        num_python_killed += 1
                        #self._log_print ("DEBUG: SIG(over)KILL %s python processes: %s" % python_pid)
                    except OSError:
                        pass

        if num_bgp_killed > 0 or num_python_killed > 0:
            self._log_print(
                "WARNING: SIGKILL lingering processes bgp_stress: %s python: %s" %
                (num_bgp_killed, num_python_killed))

        return

    # end _overkill_lingering_processes

    def cleanup(self, oper=''):

        #
        # Only execute this section if bgp test ran
        #
        if int(self._args.run_bgp_scale):

            #
            # Post process logs, cleanup fds etc
            #
            self.report_result_averages()

            #
            # Post process logs, cleanup fds etc
            #
            self._overkill_lingering_processes()

            #
            # Makes for easy cut/paste when manually running..
            #
            self._log_print("INFO: result file: %s" % self.summary_fd.name)
            self._log_print("INFO: log file: %s" % self.fd.name)
            self._log_print(
                'INFO: grep -v egrep %s/*%s* | grep -v "abrt-watch-log" | egrep --color=auto "WARNING|ERROR"' %
                (self._args.logdir_name, self.pid))
            self._log_print(
                'INFO: grep -v egrep %s/*%s* | egrep --color=auto "Expected|Elapsed"' %
                (self._args.logdir_name, self.pid))
            self._log_print(
                'INFO: grep -v egrep %s/*%s* | egrep --color=auto "BGP Stress Test - CN|Expected|Elapsed"' %
                (self._args.logdir_name, self.pid))

        elif int(self._args.run_get_result_prior_run):
            self._log_print("INFO: result file: %s" % self.summary_fd.name)
            self._log_print("INFO: log file: %s" % self.fd.name)

        #
        # Only close summary fd if bgp_scale ran -or- ran post-process on prior runs
        #
        if int(self._args.run_get_result_prior_run) or int(self._args.run_bgp_scale):
            if self.summary_fd:
                self.summary_fd.close()

        # if self.fd != None:
        if self.fd:
            self.fd.close()

        return

    # end cleanup

    def _get_vn_subnet_addr(self, ip):

        #
        # Get the ip address' lowest byte
        #
        lowbyte = int(re.search('\d+$', ip).group())
        nextbyte = int(self._args.test_id)

        #
        # Use the ip low byte as the network highest byte, just a random way to keep it unique per CN
        #
        new_net = "%s.%s/%s" % (lowbyte, nextbyte,
                                self._args.vn_net_prefix_len)

        #
        # Get new network
        #
        return_val = IPNetwork(new_net)

        return return_val

    # end _get_vn_subnet_addr

    def add_or_delete_vns(self, oper=''):

        if not int(self._args.run_vn):
            return

        #
        # Get operation, function call param overrides params file
        #
        if not oper:
            oper = self._args.vn_oper

        #
        # Get IP addresses of 1 or more control nodes
        #
        cn_ips = self.cn_ips

        #
        # Get IP addresses localhost - use to derive xmpp_src
        #
        local_ip = self.localhost_ip

        #
        # Note 1) each iteration needs a unique block id so that running
        # parallel bgp_stress_tests do not overlap instance names
        #
        # Note 2) if the number of blocks indicated in the params file is
        # in so that a larger set of rinstances may be created
        #
        nblocks_of_vns = int(self._args.nblocks_of_vns)

        #
        # Get the the number of iterations
        #
        num_iterations = self.num_iterations

        #
        # Get the max value of rinstances in iteration list (ninstances)
        #
        num_vns = self._get_num_vns()

        #
        # Reporting stats during test run is optional
        #
        report_stats_vn = int(self._args.report_stats_vn)

        #
        # Count is used to report stats periodically during creating
        #
        nvns = 0

        #
        # Loop thru contrail-control IPs
        #
        # for index in range (len(cn_ips)):
        cn_start_index, num_control_nodes = self._get_cn_range()
        if self.set_general_vn_name_across_testservers:
            self._log_print(
                "INFO: %s vns - num iterations: %s num blocks: %s num vns per block: %s total= %s cn_start_id: %s num_cns: %s" %
                (oper, num_iterations, nblocks_of_vns, num_vns, num_iterations * nblocks_of_vns * num_vns, cn_start_index, num_control_nodes))
        else:
            self._log_print(
                "INFO: %s vns - For each testserver: num iterations: %s num blocks: %s num vns per block: %s total= %s cn_start_id: %s num_cns: %s" %
                (oper, num_iterations, nblocks_of_vns, num_vns, num_iterations * nblocks_of_vns * num_vns, cn_start_index, num_control_nodes))

        for cn_index in range(cn_start_index, num_control_nodes):

            #
            # Get stats prior to run
            #
            self._report_stats(
                "Stats Before VN {0}".format(oper), report_stats_vn)

            #
            # Get control node info
            #
            cn_ip = cn_ips[cn_index]
            cn_ispec = self.cn_introspect[cn_index]

            #
            # Get base network for this control node
            #
            if int(self._args.rule_ts_cn_one_to_one) or int(self._args.rule_ts_cn_many_to_one):
                ts_ip = self.ts_ips[cn_index]
                net = self._get_vn_subnet_addr(ts_ip)
            else:
                ts_ip = local_ip
                net = self._get_vn_subnet_addr(local_ip)

            #
            # Get block number ID to start iteration, not always starting with 1
            #
            start_block_num = int(self._args.start_block_num)
            vn_cfg = VnCfg()

            #
            # Each block of VNs is used in a test iteration, example
            #     s42_vnet_block1_n<vnid>,  s42_vnet_block2_n<vnid>, ...
            for j in range(start_block_num, num_iterations + 1):

                #blck = self._get_vn_name (j, cn_ip, ts_ip)
                #self._log_print ("DEBUG: %s vns on api_server: %s for control node: %s block: %s" % (oper, self.inputs.auth_ip, cn_ip, blck))

                #
                # Each block has 1 or num_vns of VNs, example:
                #    c42_t41_block1_n<vnid>,  c42_t41_block1_n<vnid>, ...
                #
                for i in range(1, num_vns + 1):

                    #
                    # Get derived VN name
                    #
                    vn_name = self._get_vn_name(j, cn_ip, ts_ip, i)

                    #
                    # Check that instnace is deleted before adding
                    #
                    if oper == "add":
                        self.num_delete_polls_add += self._check_vn_deleted(
                            vn_name,
                            cn_ispec, cn_ip)

                    #
                    # Add or delete VN
                    #
                    cmd = '--api_server_ip {0} --api_server_port 8082 --public_subnet {1} --vn_name {2} --oper {3}'.format(
                        self.inputs.auth_ip, str(net), vn_name, oper)
                    self._log_print("INFO: %s" % cmd)
                    vn_cfg._run(cmd)

                    #
                    # Check that vn is deleted before deleting next
                    #
                    if oper == "del":
                        self.num_delete_polls_del += self._check_vn_deleted(
                            vn_name,
                            cn_ispec, cn_ip)

                    net += 1
                    nvns += 1

                # end creating vns per block

            # end blocks of vns

            #
            # Get stats after adding VNs to this control node
            #
            self._report_stats(
                "Stats After with VN {0}".format(oper), report_stats_vn)

            #
            # If using a common inter-controlnode block name, only iterate once..
            #
            if self.set_general_vn_name_across_testservers:
                break
            else:
                pass

        # end control_nodes

        #
        # If add, check all vns are present
        #
        if oper == "add":
            self._log_print("INFO: number delete polls during vn add: %s" %
                            self.num_delete_polls_add)
        else:
            self._log_print("INFO: number delete polls during vn delete: %s" %
                            self.num_delete_polls_del)

        return

    # end add_or_delete_vns

    def _check_vn_deleted(self, instance_name, cn, ip):
        return 0

        #
        # Set start time, in case we need to time out
        #
        start_time = datetime.now()

        polls = 0
        while True:
            res = cn.get_cn_routing_instance(instance_name)
            if len(res) == 0:
                polls += 1
                break
            #
            # Check for timeout - abort if so..
            #
            self._abort_if_timeout(
                start_time, self._args.timeout_seconds_vn_del,
                "cn to verify on server: %s deleted instance: %s num_polls: %s" % (ip, instance_name, polls))

        #self._log_print ("DEBUG: verified on server: %s that vn: %s is not present before adding num_polls: %s" % (ip, instance_name, polls))
        return polls

    # end _check_vn_deleted

    def _check_vn_added(self, instance_name, cn):

        #
        # Set start time, in case we need to time out
        #
        start_time = datetime.now()

        polls = 0
        while True:
            res = cn.get_cn_routing_instance(instance_name)
            if len(res) > 0:
                polls += 1
                break
            #
            # Check for timeout - abort if so..
            #
            self._abort_if_timeout(
                start_time, self._args.timeout_seconds_vn_add,
                "cn to verify added instance: %s num_polls: %s" % (instance_name, polls))

        return polls

    # end _check_vn_added

    def _abort_if_timeout(self, t1, timeout_seconds, msg=0):

        #
        # Check for timeout
        #
        delta_time = self._get_time_diffs_seconds(
            t1, datetime.now(), decimal_places=0)
        if delta_time > float(timeout_seconds):
            if msg == 0:
                self._log_print("ABORT: timed out - waited: %ss" % delta_time)
            else:
                self._log_print(
                    "ABORT: timed out waiting for %s - waited: %ss" %
                    (msg, delta_time))
            self.cleanup()
            sys.exit()
        else:
            pass

        return delta_time

    # end _abort_if_timeout

    def _action_if_timeout(self, t1, timeout_seconds, action, msg=0):

        #
        # Check for timeout
        #
        status = False
        delta_time = self._get_time_diffs_seconds(
            t1, datetime.now(), decimal_places=0)
        if delta_time > float(timeout_seconds):
            if msg == 0:
                self._log_print("%s: timed out - waited: %ss" %
                                (action, delta_time))
            else:
                self._log_print("%s: timed out waiting for %s - waited: %ss" %
                                (action, msg, delta_time))
            if action == "ABORT":
                self.cleanup()
                sys.exit()
            else:
                status = True
        else:
            pass

        return status, delta_time

    # end _action_if_timeout

    def _check_vn_all(self):

        #
        # Skip if only deleting vns
        #
        if self._args.vn_oper == "del":
            return

        return_val = 0

        #
        # Check control nodes, get index vals first
        #
        self._log_print("INFO: checking vns are present on control nodes")
        cn_start_index, num_control_nodes = self._get_cn_range()
        ts_ip = self.ts_ips[0]
        for i in range(cn_start_index, num_control_nodes):

            #
            # Get introspect cn info
            #
            cn_ip = self.cn_ips[i]
            cn_ispec = self.cn_introspect[i]

            #
            # Set start time for each control node iteration, in case we need to time out
            #
            start_time = datetime.now()

            #
            # Get number of and name instances should start with..
            #
            total_expected_routing_instances = self._get_num_vns(
            ) * self.num_iterations
            if int(self._args.rule_ts_cn_one_to_one) or int(self._args.rule_ts_cn_many_to_one):
                ts_ip = self.ts_ips[i]

            vn_beginning_name = self._get_vn_beginning_name(
                cn_ip, ts_ip, self._args.vn_basename)

            self._log_print(
                "INFO: checking control node: %s for: %s vns present with names beginning with: '%s'" %
                (cn_ip, total_expected_routing_instances, vn_beginning_name))

            num_polls = 0
            while True:

                #
                # Get routing-instance list
                #
                ri_list = cn_ispec.get_cn_routing_instance_list()
                num_polls += 1

                #
                # Count elements - start at 7 to skip default fabric instance
                #
                num_rinstances = 0
                if len(ri_list) > 6:
                    for j in range(0, len(ri_list)):
                        if re.search(':%s' % vn_beginning_name, ri_list[j]['name']):
                            num_rinstances += 1
                        else:
                            pass
                else:
                    pass

                #
                # Check number of vns present
                #
                if num_rinstances >= total_expected_routing_instances:
                    self._log_print(
                        "INFO: found a total of %s vns on control node: %s" %
                        (num_rinstances, cn_ip))
                    delta_time = self._get_time_diffs_seconds(
                        start_time, datetime.now(), decimal_places=0)
                    break

                #
                # Check for timeout - abort if on the last control node
                #
                action = "ERROR"
                if i == (num_control_nodes - 1):
                    action = "ABORT"
                timeout_sec = int(self._args.timeout_seconds_all_vns_present)
                status, delta_time = self._action_if_timeout(
                    start_time, timeout_sec, action, "control node: %s to verify all vns created - found: %s num_polls: %s" % (cn_ip, num_rinstances, num_polls))
                if status:
                    delta_time = 0
                    break
                #self._log_print ("DEBUG: num_instances cn_introspect poll: %s timeout in: %ss" % (num_rinstances, timeout_sec - delta_time))

                #
                # Sleep a bit
                #
                sleep_time = int(self._args.sleeptime_between_check_vn_present)
                self._log_print(
                    "INFO: sleeping: %ss between vn present check on control node: %s - timeout in: %ss found: %s vns" %
                    (sleep_time, cn_ip, timeout_sec - delta_time, num_rinstances))
                time.sleep(sleep_time)

            # end while loop

            if (i + 1) < num_control_nodes:
                self._log_print("DEBUG: checking next control node: %s" %
                                self.cn_ips[i + 1])
                pass

        # end for loop through control nodes

        return num_polls

    # end _check_vn_all

    def _get_vn_beginning_name(self, cn_ip, ts_ip, vn_basename):

        if self.set_general_vn_name_across_testservers:
            return_val = self._args.vn_basename
        else:
            return_val = "c%s_t%s_%s" % (
                (re.search('\d+$', cn_ip).group()), (re.search('\d+$', ts_ip).group()), vn_basename)

        return return_val

    # end _get_vn_beginning_name

    def _get_vn_name(self, block_index, cn_ip, ts_ip, n_index=0):

        #
        # Oeverride derived vn mames if param set.
        # Often uses for multiple contrail-control per agent trick
        #
        if self.set_general_vn_name_across_testservers:
            vn_basename = self._args.vn_basename
        else:
            #
            # Use control node and localhost low order bytes to derive
            # vn names
            vn_basename = "c%s_t%s_%s" % (
                (re.search('\d+$', cn_ip).group()), (re.search('\d+$', ts_ip).group()), self._args.vn_basename)

        #
        # Vn name may or may not have last index subscript
        #
        if not n_index:
            vn_name = "{0}{1}_n".format(vn_basename, block_index)
        else:
            vn_name = "{0}{1}_n{2}".format(vn_basename, block_index, n_index)

        return vn_name

    # end _get_vn_name

    def policy_config(self, oper=''):

        if not int(self._args.run_policy):
            return

        #
        # Get operation, function call param overrides params file
        #
        if not oper:
            oper = self._args.policy_oper

        #
        # Use first item in ninstances list
        #
        number_instances = self.ninstances[0]

        #
        # Either use a canned number of policies from params file or derive it
        # based on the number of routing instances
        #
        try:
            self._args.num_bidir_policies
            num_bidir_policies = int(self._args.num_bidir_policies)
        except:
            num_bidir_policies = int(number_instances) / 2

        if num_bidir_policies == 0:
            self._log_print(
                "INFO: Only one instance, skipping instance-to-instance policy config")
            return

        #
        # Create multiple policies per block
        #
        self._log_print("INFO: oper: %s %s bidr policies on: %s" %
                        (oper, self.num_iterations * num_bidir_policies, self.inputs.auth_ip))
        for block_index in range(1, self.num_iterations + 1):
            for policy_index in range(1, num_bidir_policies + 1):

                #
                # Add policy, use the "oper" flag for add or add_bidr_one_import
                # add=>import target applied to both instances towards each other
                # add_bidr_one_import=>import target in one direction, and not in the other even
                # tho a policy is attached.
                #
                if oper == "add":
                    self._config_policy(
                        block_index, policy_index, num_bidir_policies, oper)
                elif oper == "del":
                    self._delete_policy(
                        block_index, policy_index, num_bidir_policies)

    # end policy_config

    def _config_policy(self, block_index, policy_index, num_policies, oper=''):
        ''' Configure policies in both directions
        '''

        #
        # Policy names are sa follows, say there are 100 rinstances, the
        # n1_51, n2_52, ... n50_n100
        #
        second_ri_index = policy_index + num_policies

        #
        # Get policy names for each direction
        #
        policy1 = self._get_policy_name(
            'up', block_index, policy_index, second_ri_index)
        policy2 = self._get_policy_name(
            'dn', block_index, policy_index, second_ri_index)

        #
        # Get vn names
        #
        vn1 = self._get_vn_name(block_index, policy_index)
        vn2 = self._get_vn_name(block_index, second_ri_index)

        #
        # Create policy calls
        # Example call add --vn_list s42_vnet_blk1_n2 s42_vnet_blk1_n1 n2_to_n
        #
        cmd1 = 'cd test/scripts/scale/control-node; python policy.py add --vn_list {0} {1} {2}'.format(
            vn1, vn2, policy1)
        cmd2 = 'cd test/scripts/scale/control-node; python policy.py add --vn_list {0} {1} {2}'.format(
            vn2, vn1, policy2)
        #self._log_print ("INFO: cmd1: %s " % (cmd1))
        #self._log_print ("INFO: cmd2: %s " % (cmd2))
        # return

        #
        # Get the config server
        #
        api_ssh_fd = self.api_ssh_fd

        #
        # Add the policies
        #
        result1 = api_ssh_fd.execCmd(cmd1)
        result2 = api_ssh_fd.execCmd(cmd2)
        self._log_print("INFO: cmd1: %s %s" % (cmd1, result1))
        self._log_print("INFO: cmd2: %s %s" % (cmd2, result2))

        # THis does not work due to ssh issue
        #PolicyCmd (cmd1)
        #PolicyCmd (cmd2)

    # end _config_policy

    def _get_policy_name(self, order, block_index, index, second_ri_index):

        #
        # Get optional policy prepend name, otherwise use instance name
        #
        try:
            self._args.policy_name_prepend_pattern
            pattern = "%sblock%s_" % (
                self._args.policy_name_prepend_pattern, block_index)
        except:
            pattern = "policy_b%s_" % self._get_vn_name(block_index)

        #
        # Create policy per direction
        #
        if order == 'up':
            new_policyname = "{0}n{1}_n{2}".format(
                pattern, index, second_ri_index)
        else:
            new_policyname = "{0}n{2}_n{1}".format(
                pattern, index, second_ri_index)

        return new_policyname

    # end _get_policy_name

    def _get_datetime_from_logline(self, line):

        #
        # Get earliest, latest dates - used for wallclock time for parallel runs
        # Note that the filename may (with multiple iterations) or may not (when
        # one iteration) pre-pend the line.
        #
        time_str = re.search("^(.*log\.\d+:)?(.*) scale\d+", line)
        if time_str != None:
            time_str = time_str.group(2)
            time = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S.%f')
        else:
            time = 0

        return time

    # end _get_datetime_from_logline

    def _get_event_per_second(self, number_of_events, seconds, decimal_places):

        if seconds == 0:
            return_val = 0
        else:
            return_val = round(
                (float(number_of_events) / seconds), decimal_places)

            if decimal_places == 0:
                return_val = int(return_val)

        return return_val

    # end _get_event_per_second

    def _get_event_per_usec(self, number_of_events, seconds, decimal_places):

        if seconds == 0:
            return_val = 0
        else:
            return_val = round(
                (float(number_of_events / seconds) * 1000000), decimal_places)

            if decimal_places == 0:
                return_val = int(return_val)

        return return_val

    # end _get_event_per_usec

    def report_result_averages(self, called_by='', log_pid=''):
        ''' At this point all the process are finished, average the peer-bringup/adds/deletes
        '''

        if log_pid and log_pid != 0:
            log_pid
            pid = log_pid
        else:
            pid = self.pid
            if int(self._args.run_get_result_prior_run) != 0 or called_by == "init":
                return

        #
        # Open summary logfilename
        #
        self._open_logfile('summary')

        #
        # Get delta time
        #
        self.test_end_time = datetime.now()
        self.delta_time_minutes = int(
            ((self.test_end_time - self.test_start_time).seconds) / 60)

        #
        # Print headings
        #
        if self.run_bgp_scale_in_background:
            seq_or_parallel = "parallel"
        else:
            seq_or_parallel = "sequential order"

        self._print_summary_and_regular_log("Summary %s:" % datetime.now())
        self._print_summary_and_regular_log(" ")
        self._print_summary_and_regular_log(
            "    Test start time: %s" % self.test_start_time)
        self._print_summary_and_regular_log(
            "    Test end time:   %s" % self.test_end_time)
        self._print_summary_and_regular_log(
            "    Number of iterations (running in %s): %s" % (seq_or_parallel, self.num_iterations))
        if self.run_cpu_test:
            self._print_summary_and_regular_log(
                "    Number of cpu_threads: %s affinity mask: %s" % (self.cpu_threads, self.affinity_mask))
        self._print_summary_and_regular_log(
            "    Test params: %s" % self.test_param_name)
        self._print_summary_and_regular_log(
            "    Test ran for ~%s min" % self.delta_time_minutes)
        self._print_summary_and_regular_log(
            "    Results file: %s" % self.summary_fd.name)
        self._print_summary_and_regular_log("    Run pid: %s" % pid)

        #
        # Indicate if there is a delay for prefix announcements until after peers are up
        #
        trigger_state = "no"
        try:
            result = re.search(
                'trigger', self._args.logging_etc, re.IGNORECASE)
            if result != None and result:
                trigger_state = "yes"
        except:
            pass

        self._print_summary_and_regular_log(
            "    Prefixes triggered after peers up: %s" % trigger_state)

        #
        # Get averages
        #
        self._get_average_time_peer_bringup(pid)
        self._get_average_time_prefix_add(pid, trigger_state)
        self._get_average_time_prefix_del(pid)

    # end report_result_averages

    def _get_average_time_peer_bringup(self, pid):
        #
        # Post-process log files..
        #

        #
        # Initialize vars
        #
        self.total_num_peers = 0
        self.num_peer_results = 0
        self.total_time_seconds_peer_bringup = 0
        self.total_agg_time_seconds_peer_bringup = 0
        self.timestamp_last_peer_up = 0
        self.timestamp_bgp_stress_started = 0
        self.average_time_peer_bringup = 0
        self.average_time_peer_bringup_per_iteration = 0
        total_time = 0
        total_num_peers = 0
        num_peer = 0
        max_num_peers = 0
        num_peer_results = 0

        #
        # Get the recorded timestamp for peers up
        #
        self.timestamp_bgp_stress_started = self._get_log_event_timestamp(
            pid, self._args.logdir_name, self._args.logfile_name_results, 'notable_event', 'started bgp_stress')
        self.timestamp_last_peer_up = self._get_log_event_timestamp(
            pid, self._args.logdir_name, self._args.logfile_name_results, 'notable_event', 'peers up', 'most_recent')

        #
        # Gather other totals from log file
        #
        cmd = 'grep Elapsed %s/%s_%s.log* | grep peer' % (self._args.logdir_name,
                                                          self._args.logfile_name_results, pid)
        result = self._get_line_with_pattern_match(cmd)
        if result:

            # chop newline at the end of the output
            lines = result.split('\n')[:-1]

            #
            # Get peer bringup times from each lin found
            #
            for i in range(len(lines)):
                result = re.search(
                    '.* time to add (\d+) peers:(\d+\.\d+)', lines[i])
                if result != None:
                    num_peers = int(result.group(1))

                total_num_peers += num_peers
                total_time += float(
                    re.search('.* time to add (\d+) peers:(\d+\.\d+)s',
                              lines[i]).group(2))

                num_peer_results += 1
                if num_peers > max_num_peers:
                    max_num_peers = num_peers

            self.total_agg_time_seconds_peer_bringup = round(total_time, 1)

            #
            # If we are running in parallel, record printed timestamp diffs.
            # Otherwise, for sequential, add up each recorded time.
            #
            if self.run_bgp_scale_in_background:
                self.total_time_seconds_peer_bringup = self._get_time_diffs_seconds(
                    self.timestamp_bgp_stress_started, self.timestamp_last_peer_up,  decimal_places=1)
                self.peer_bringup_per_second = self._get_event_per_second(
                    total_num_peers, self.total_time_seconds_peer_bringup, decimal_places=2)
            else:
                self.peer_bringup_per_second = self._get_event_per_second(
                    total_num_peers, self.total_agg_time_seconds_peer_bringup, decimal_places=2)

            #
            # Get totals and averages..
            #
            self.total_num_peers = total_num_peers
            self.num_peer_results = num_peer_results
            self.average_time_peer_bringup = self._get_event_per_second(
                self.total_time_seconds_peer_bringup, total_num_peers, decimal_places=1)
            self.average_time_peer_bringup_per_iteration = self._get_event_per_second(
                self.total_time_seconds_peer_bringup, num_peer_results, decimal_places=1)

        # enf if result found

        #
        # The payoff
        #
        self._print_summary_and_regular_log(" ")
        self._print_summary_and_regular_log(
            "        Number of peer bringup iterations found: %s" % self.num_peer_results)
        if int(self.num_peer_results) == 0:
            self._print_summary_and_regular_log(
                "        No data found for peer bringup")

        else:
            self._print_summary_and_regular_log(
                "        Total number of XMPP peers: %s" % self.total_num_peers)
            if self.run_bgp_scale_in_background:
                self._print_summary_and_regular_log(
                    "        Total wallclock time for peers brought up in parallel: %ss" % str(self.total_time_seconds_peer_bringup))

            self._print_summary_and_regular_log(
                "        Number of iterations found: %s" % self.num_peer_results)
            self._print_summary_and_regular_log(
                "        Total aggregate time to bringup peers (relevant for sequential runs): %ss" % self.total_agg_time_seconds_peer_bringup)
            self._print_summary_and_regular_log(
                "        Max number of peers per any one iterations: %s" % max_num_peers)
            self._print_summary_and_regular_log(
                "        Average time per iteration: %ss" % self.average_time_peer_bringup_per_iteration)
            self._print_summary_and_regular_log(
                "        Average time per peer bringup: %ss" % self.average_time_peer_bringup)
            self._print_summary_and_regular_log(
                "        Peers-up per second: %s" % self.peer_bringup_per_second)

        return

    # end _get_average_time_peer_bringup

    def _get_log_event_timestamp(self, pid, logdir, logname, pattern1, pattern2, order=''):

        cmd = 'grep %s %s/%s_%s.log* | grep "%s" | sort -n -k 2' % (pattern1,
                                                                    logdir, logname, pid, pattern2)

        #
        # Issue command
        #
        status, result = self._get_subprocess_info(
            cmd, print_err_msg_if_encountered=0)

        #
        # Get logged timestamp (timestamp on the timestamp'd log entry)
        #
        return_val = 0
        timestamp = 0
        t1 = 0
        tbest = 0
        if status:
            lines = ''
            # chop newline at the end of the output
            lines = result.split('\n')[:-1]

            #
            # Loop thru all the lines to get the proper entry
            #
            for i in range(len(lines)):
                timestamp = re.search('.*timestamp: (.*)$', lines[i])
                if timestamp:
                    t1 = datetime.strptime(
                        timestamp.group(1), '%Y-%m-%d %H:%M:%S.%f')
                    if i == 0:
                        tbest = t1
                    if order == 'most_recent':
                        if t1 > tbest:
                            tbest = t1
                    elif order != 'most_recent':
                        if t1 < tbest:
                            tbest = t1
                #self._log_print ("DEBUG: i:%s t1: %s tbest: %s line[%s]: %s" %(i, str(t1), str(tbest), i, lines[i]))

        if tbest == 0:
            self._log_print(
                "WARNING: no patterns pat1: %s, pat2: %s, pat:timestamp  matched for cmd: %s" %
                (pattern1, pattern2, cmd))

        return tbest

    # end _get_log_event_timestamp

    def _get_line_with_pattern_match(self, cmd):

        status, return_val = self._get_subprocess_info(cmd)
        return return_val

    # end _get_line_with_pattern_match

    def _get_average_time_prefix_add(self, pid, trigger_state):

        #
        # Init in case there are no stats available..
        #
        total_time = 0
        total_num_prefixes = 0
        num_prefix_results = 0
        self.total_num_prefixes_add = 0
        self.total_agg_time_seconds_add = 0
        self.num_prefix_results_add = 0
        self.total_time_seconds_prefix_adds = 0
        self.timestamp_last_prefix_add = 0
        self.timestamp_start_announcing_prefixes = 0
        self.average_time_prefix_add_per_iteration = 0
        self.average_time_prefix_add = 0
        self.average_time_update_add = 0

        #
        # Get the recorded timestamp for prefix add start. Note that
        # unless there is a trigger file, it starts when the peers start
        # coming up
        #
        if trigger_state == "yes":
            self.timestamp_start_announcing_prefixes = self._get_log_event_timestamp(
                pid, self._args.logdir_name, self._args.logfile_name_results, 'notable_event', 'prefix adds triggered')
        else:
            self.timestamp_start_announcing_prefixes = self._get_log_event_timestamp(
                pid, self._args.logdir_name, self._args.logfile_name_results, 'notable_event', 'one peer up')

        #
        # Get the recorded timestamp for prefix add completion
        # Note that it's another notable event.
        #
        self.timestamp_last_prefix_add = self._get_log_event_timestamp(
            pid, self._args.logdir_name, self._args.logfile_name_results, 'notable_event', 'finished prefix add', 'most_recent')

        #
        # Derive average timings for prefix adds
        #
        cmd = 'grep Elapsed %s/%s_%s.log* | grep -v peer | grep add' % (
            self._args.logdir_name, self._args.logfile_name_results, pid)
        result = self._get_line_with_pattern_match(cmd)
        if result:

            # chop newline at the end of the output
            lines = result.split('\n')[:-1]

            #
            # Loop through logs for successful add summary lines
            #
            for i in range(len(lines)):
                result = re.search(
                    '.* time to add (\d+) prefixes on_control_node:(\d+\.\d+)s', lines[i])
                if result != None:
                    total_num_prefixes += int(result.group(1))
                    total_time += float(result.group(2))
                    num_prefix_results += 1

            #
            # If we are running in parallel, record printed timestamp diffs.
            # Otherwise, for sequential, add up each recorded time.
            #
            if self.run_bgp_scale_in_background:
                self.total_time_seconds_prefix_adds = self._get_time_diffs_seconds(
                    self.timestamp_start_announcing_prefixes, self.timestamp_last_prefix_add, decimal_places=2)
                self.prefix_adds_per_second = self._get_event_per_second(
                    total_num_prefixes, self.total_time_seconds_prefix_adds, decimal_places=0)
                self.updates_adds_per_second = self._get_event_per_second(
                    total_num_prefixes * self.nagents[0], self.total_time_seconds_prefix_adds, decimal_places=0)
            else:
                self.prefix_adds_per_second = self._get_event_per_second(
                    total_num_prefixes, total_time, decimal_places=0)
                self.updates_adds_per_second = self._get_event_per_second(
                    total_num_prefixes * self.nagents[0], total_time, decimal_places=0)

            #
            # Tally results
            #
            self.total_num_prefixes_add = total_num_prefixes
            self.num_prefix_results_add = num_prefix_results

            #
            # Get aggregate, only relevant for sequential runs
            #
            self.total_agg_time_seconds_add = total_time

            #
            # Derive averages
            #
            self.average_time_prefix_add_per_iteration = self._get_event_per_second(
                self.total_time_seconds_prefix_adds, num_prefix_results, decimal_places=2)
            self.average_time_prefix_add = self._get_event_per_usec(
                self.total_time_seconds_prefix_adds, total_num_prefixes, decimal_places=0)
            self.average_time_update_add = self._get_event_per_usec(
                self.total_time_seconds_prefix_adds, total_num_prefixes * self.nagents[0], decimal_places=0)

        # enf if result found

        #
        # The payoff
        #
        self._print_summary_and_regular_log(" ")
        self._print_summary_and_regular_log(
            "        Number of iterations found for adds: %s" % self.num_prefix_results_add)

        if int(self.num_prefix_results_add) == 0:
            self._print_summary_and_regular_log(
                "        No data found for adds")

        else:
            self._print_summary_and_regular_log(
                "        Total prefixes added (all iterations): %s" % self.total_num_prefixes_add)
            if self.run_bgp_scale_in_background:
                self._print_summary_and_regular_log(
                    "        Total wallclock time running in parallel for prefix adds: %ss" % str(self.total_time_seconds_prefix_adds))

            self._print_summary_and_regular_log(
                "        Total aggregate time (relevant for sequential runs) add: %ss" % self.total_agg_time_seconds_add)
            self._print_summary_and_regular_log(
                "        Average time per iteration for adds: %ss" % self.average_time_prefix_add_per_iteration)
            self._print_summary_and_regular_log(
                "        Average time per prefix add: %sus" % self.average_time_prefix_add)
            self._print_summary_and_regular_log(
                "        Average time per update add: %sus" % self.average_time_update_add)
            self._print_summary_and_regular_log(
                "        Prefix per second for adds: %s" % self.prefix_adds_per_second)
            self._print_summary_and_regular_log(
                "        Updates per second add (valid only if num agents same per iteration): %s" % self.updates_adds_per_second)

        return

    # end _get_average_time_prefix_add

    def _print_summary_and_regular_log(self, msg1, msg2='', msg3='', msg4='', msg5='', msg6='', msg7='', msg8='', msg9=''):

        #
        # Print all the messages to both log and summary log
        #
        i = 1
        while True:
            try:
                msg = vars()['msg' + str(i)]
                if msg == '':
                    break
                self._log_print("INFO: %s" % msg)
                self._summary_print(msg)
                i += 1
            except:
                break

    # end _print_summary_and_regular_log

    def _get_subprocess_info(self, cmd=0, print_err_msg_if_encountered=1):

        #
        # Return if improper command provided
        #
        if cmd == 0 or type(cmd) != str:
            if print_err_msg_if_encountered:
                self._log_print(
                    "ERROR: improper cmd: %s string provided to function _get_subprocess_info, returning 0" % cmd)
            return None

        try:
            result = subprocess.check_output(
                cmd, stderr=subprocess.STDOUT, shell=True)
            status = True
        except subprocess.CalledProcessError, OSError:
            if print_err_msg_if_encountered:
                self._log_print(
                    "WARNING: error executing subprocess shell cmd: '%s'" % cmd)
            status = None
            result = None

        return status, result

    # end _get_subprocess_info

    def _get_time_diffs(self, t1, t2):

        if type(t1) == datetime and type(t2) == datetime:
            return_val = (t2 - t1)
        else:
            return_val = 0
            self._log_print(
                "ERROR: time1 or time2 not type datatime: t1 type: %s t2 type: %s" %
                (type(t1), type(t2)))

        return return_val

    # end _get_time_diffs

    def _get_time_diffs_seconds(self, t1, t2, decimal_places):

        if type(t1) == datetime and type(t2) == datetime:

            #
            # Check date is not in the past
            #
            delta_time = (t2 - t1)
            if delta_time.days < 0:
                self._log_print(
                    "ERROR: time diff results in a past date t1: %s t2: %s" % (str(t1), str(t2)))
                return 0

            return_val = float("%s.%s" % (str(abs(delta_time).seconds),
                                          str(abs((delta_time)).microseconds)[:decimal_places]))
            if decimal_places == 0:
                return_val = int(return_val)

        else:
            return_val = 0
            self._log_print(
                "ERROR: time1 or time2 not type datatime: t1 type: %s t2 type: %s" %
                (type(t1), type(t2)))

        return return_val

    # end _get_time_diffs_seconds

    def _get_average_time_prefix_del(self, pid):

        #
        # Init in case there are no stats available..
        #
        total_time = 0
        total_num_prefixes = 0
        num_prefix_results = 0
        self.total_time_seconds_prefix_deletes = 0
        self.total_num_prefixes_del = 0
        self.total_agg_time_seconds_del = 0
        self.num_prefix_results_del = 0
        self.timestamp_last_agent_del_done = 0
        self.average_time_prefix_del_per_iteration = 0
        self.average_time_prefix_del = 0
        self.average_time_update_del = 0

        #
        # Get timestamp of last bgp_stress child python SIGKIL'd
        #
        self.timestamp_first_agent_del_done = self._get_log_event_timestamp(
            pid, self._args.logdir_name, self._args.logfile_name_results, 'notable_event', 'stopping prefix')
        self.timestamp_last_agent_del_done = self._get_log_event_timestamp(
            pid, self._args.logdir_name, self._args.logfile_name_results, 'notable_event', 'finished prefix del', 'most_recent')

        #
        # Get all lines with successful deletion completion
        #
        cmd = 'grep Elapsed %s/%s_%s.log* | grep -v peer | grep del' % (
            self._args.logdir_name, self._args.logfile_name_results, pid)
        result = self._get_line_with_pattern_match(cmd)
        if result:

            # chop newline at the end of the output
            lines = result.split('\n')[:-1]

            #
            # Loop through all successful deletion completion lines
            #
            for i in range(len(lines)):
                result = re.search(
                    '.* time to del (\d+) prefixes on_control_node:(\d+\.\d+)s', lines[i])
                if result != None:
                    total_num_prefixes += int(result.group(1))
                    total_time += float(result.group(2))
                    num_prefix_results += 1

            #
            # If we are running in parallel, record printed timestamp diffs.
            # Otherwise, for sequential, add up each recorded time.
            #
            if self.run_bgp_scale_in_background:
                self.total_time_seconds_prefix_deletes = self._get_time_diffs_seconds(
                    self.timestamp_first_agent_del_done, self.timestamp_last_agent_del_done, decimal_places=2)
                self.prefix_deletes_per_per_second = self._get_event_per_second(
                    total_num_prefixes, self.total_time_seconds_prefix_deletes, decimal_places=0)
                self.updates_deletes_per_second = self._get_event_per_second(
                    total_num_prefixes * self.nagents[0], self.total_time_seconds_prefix_deletes, decimal_places=0)
            else:
                self.prefix_deletes_per_per_second = self._get_event_per_second(
                    total_num_prefixes, total_time, decimal_places=0)
                self.updates_deletes_per_second = self._get_event_per_second(
                    total_num_prefixes * self.nagents[0], total_time, decimal_places=0)

            #
            # Tally results
            #
            self.total_num_prefixes_del = total_num_prefixes
            self.num_prefix_results_del = num_prefix_results

            #
            # Get aggregate, only relevant for sequential runs
            #
            self.total_agg_time_seconds_del = total_time

            #
            # Derive averages.
            #
            self.average_time_prefix_del_per_iteration = self._get_event_per_second(
                self.total_time_seconds_prefix_deletes, num_prefix_results, decimal_places=2)
            self.average_time_prefix_del = self._get_event_per_usec(
                self.total_time_seconds_prefix_deletes, total_num_prefixes, decimal_places=0)
            self.average_time_update_del = self._get_event_per_usec(
                self.total_time_seconds_prefix_deletes, total_num_prefixes * self.nagents[0], decimal_places=0)

        # enf if result found
        #
        # The payoff
        #
        self._print_summary_and_regular_log(" ")
        self._print_summary_and_regular_log(
            "        Number of iterations found for deletes: %s" % self.num_prefix_results_del)

        if int(self.num_prefix_results_del) == 0:
            self._print_summary_and_regular_log(
                "        No data found for deletes")

        else:
            self._print_summary_and_regular_log(
                "        Total prefixes deleted (all iterations): %s" % self.total_num_prefixes_del)
            if self.run_bgp_scale_in_background:
                self._print_summary_and_regular_log(
                    "        Total wallclock time running in parallel for prefix deletes: %ss" % str(self.total_time_seconds_prefix_deletes))

            self._print_summary_and_regular_log(
                "        Total aggregate time (relevant for sequential runs) delete: %ss" % self.total_agg_time_seconds_del)
            self._print_summary_and_regular_log(
                "        Average time per iteration for deletes: %ss" % self.average_time_prefix_del_per_iteration)
            self._print_summary_and_regular_log(
                "        Average time per prefix delete: %sus" % self.average_time_prefix_del)
            self._print_summary_and_regular_log(
                "        Average time per update delete: %sus" % self.average_time_update_del)
            self._print_summary_and_regular_log(
                "        Prefix per second for deletes: %s" % self.prefix_deletes_per_per_second)
            self._print_summary_and_regular_log(
                "        Updates per second delete (valid only if num agents same per iteration): %s" % self.updates_deletes_per_second)
            self._print_summary_and_regular_log(" ")

        return

    # end _get_average_time_prefix_del

    def _adjust_cn_ulimit(self):

        if self.cn_ulimit_n == None:
            self._log_print(
                "WARNING: no ulimit -n in command line of params file, skipping ulimit setting on file: %s" %
                self._args.control_node_supervisor_param_file)

        #
        # Adjust each control node
        #
        for i in range(len(self.cn_ips)):
            #
            # Get control node info
            #
            cn_ssh_fd = self.cn_ssh_fds[i]
            cn_ip = self.cn_ips[i]

            cmd = 'sed -i.bak -re "s/(ulimit \-n )([0-9]+)/\\1%s/g" %s' % (self.cn_ulimit_n,
                                                                           self._args.control_node_supervisor_param_file)
            self._log_print("INFO: setting ulimit -n to: %s in file: %s" %
                            (self.cn_ulimit_n, self._args.control_node_supervisor_param_file))
            self._log_print("DEBUG: ulimit sed cmd: %s" % cmd)
            result = cn_ssh_fd.execCmd(cmd)

        return

    # end _adjust_cn_ulimit

    def _add_cn_env_vars(self):
        ''' Add contrail-control env variables to /etc/contrail/control_param and ulimit to /etc/init.d/supervisor-control
        '''
        #
        # Return if no flag is set to confgure env vars or if
        # there are multiple testservers running (the latter
        # so that they are not all competing to change/restart the
        # control node, leave it up to stressfactr to handle.
        #
        if not int(self._args.add_cn_env_vars) or self._args.multiple_testservers_running:
            return

        #
        # Adjust ulimits
        #
        self._adjust_cn_ulimit()

        #
        # Return if there are no env variables
        #
        try:
            self._args.cn_env
        except:
            return

        #
        # Add env vars to contrail-control params file /etc/contrail/control_param
        #
        for i in range(len(self.cn_ips)):

            #
            # Get control node info
            #
            cn_ssh_fd = self.cn_ssh_fds[i]
            cn_ip = self.cn_ips[i]

            self._log_print(
                "INFO: adding env variables to control node: %s" % cn_ip)

            #
            # Get params file contents
            #
            cmd = "cat %s" % (self._args.control_node_param_file)
            result = cn_ssh_fd.execCmd(cmd)
            lines = result.split("\n")

            #
            # Copy contents to new file
            #
            cmd = "echo %s > %s_new" % (
                " ", self._args.control_node_param_file)
            cn_ssh_fd.execCmd(cmd)
            for i in range(len(lines)):
                line = lines[i]

                if len(line) == 0:
                    continue

                #
                # Check for ExecStart line possibly append to it
                #
                if re.search('ExecStart', line):
                    self._append_logfile_params(line, self.cn_envs)

                #
                # Copy line to new file
                #
                cmd = "echo %s >> %s_new" % (
                    line, self._args.control_node_param_file)
                cn_ssh_fd.execCmd(cmd)

                #
                # Check for last line
                #
                if re.search('LOGFILE', line):
                    break

            # Append new env variables to new file
            #
            for i in range(len(self.cn_envs)):
                cmd = "echo \%s >> %s_new" % (
                    self.cn_envs[i], self._args.control_node_param_file)
                cn_ssh_fd.execCmd(cmd)

            #
            # Overwrite new file into control_node_param_file, actually save the orig
            #
            cmd = "cp {0} {0}-bak".format(self._args.control_node_param_file)
            cn_ssh_fd.execCmd(cmd)
            cmd = "mv {0}_new {0}".format(self._args.control_node_param_file)
            cn_ssh_fd.execCmd(cmd)

        return

    # end _add_cn_env_vars

    def _append_logfile_params(self, line, cn_envs):

        line = self._append_logfile_params(line, self.cn_envs)
        #
        # Loop thru new env vars - if there is a logfile entry, change the line
        #
        for i in range(len(cn_envs)):

            if re.search('LOGFILE', line):
                line = "%s ${%s}" % (line, cn_envs[i])

        return line

    # end _append_logfile_params

    def _delete_policy(self, block_index, policy_index, num_policies):
        ''' Configure policies in both directions
        '''

        self._log_print("INFO: deleting: %s policies on: %s" %
                        (num_policies, self.inputs.cfgm_control_ips[0]))

        #
        # Policy names are sa follows, say there are 100 rinstances, the
        # n1_51, n2_52, ... n50_n100
        #
        second_ri_index = policy_index + num_policies

        #
        # Get policy names for each direction
        #
        policy1 = self._get_policy_name(
            'up', block_index, policy_index, second_ri_index)
        policy2 = self._get_policy_name(
            'dn', block_index, policy_index, second_ri_index)

        #
        # Get the config server
        #
        api_ssh_fd = self.api_ssh_fd

        #
        # Create policy calls
        # Example call add --vn_list s42_vnet_blk1_n2 s42_vnet_blk1_n1 n2_to_n
        #
        cmd1 = 'cd test/scripts/scale/control-node; python policy.py del {0}'.format(
            policy1)
        cmd2 = 'cd test/scripts/scale/control-node; python policy.py del {0}'.format(
            policy2)

        #self._log_print ("INFO: cmd1: %s " % (cmd1))
        #self._log_print ("INFO: cmd2: %s " % (cmd2))
        # return
        result1 = api_ssh_fd.execCmd(cmd1)
        result2 = api_ssh_fd.execCmd(cmd2)
        self._log_print("INFO: cmd1: %s %s" % (cmd1, result1))
        self._log_print("INFO: cmd2: %s %s" % (cmd2, result2))

        # Add the policies
        #PolicyCmd (cmd1)
        #PolicyCmd (cmd2)

    # end _delete_policy

    def _get_rule_inst_to_inst(inst1, inst2):

        rule = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': '1',
                'source_network': inst1,
                'dest_network': inst2,
            },
        ]

        return rule

    # end _get_rule_inst_to_inst

# end class FlapAgentScaleInit


class TestBGPScale(BaseBGPScaleTest):

    @classmethod
    def setUpClass(cls):
        super(TestBGPScale, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestBGPScale, cls).tearDownClass()

    @preposttest_wrapper
    def test_bgp_scale(self):
        #
        # Init
        #
        # self._log_print("INFO:******ABC*********")
        self.obj = FlapAgentScaleInit(args_str='', inputs=self.inputs)

        #
        # Start agents and routes
        #
        self.obj.start_bgp_scale()

        #
        # Cleanup
        #
        self.obj.cleanup()
        return True

# end main

# def main(args_str=None):
#
#    #
# Init
#    #
#    self = FlapAgentScaleInit(args_str)
#
#    #
# Start agents and routes
#    #
#    self.start_bgp_scale()
#
#    #
# Cleanup
#    #
#    self.cleanup()

# end main

if __name__ == "__main__":
    main()
