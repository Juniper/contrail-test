# Python libs
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
from time import sleep
from datetime import datetime, timedelta
import traceback
import logging
from pprint import pformat
from random import randint
from netaddr import *

#
# Contrail libs
#
import argparse
import ConfigParser
import json

#
# Contrail scaling libs
#
from ssh_interactive_commnds import *
from flap_agent_scale_test import *


class Controller (object):

    def __init__(self, args_str=None):
        self._args = None

        self.fl = FlapAgentScaleInit(args_str, pre_scale_setup=1)

        #
        # Time how long test runs
        #
        self.test_start_time = datetime.now()

        #
        # Get fds to test servers
        #
        self._prepare_servers()

        #
        # Get number of cpu_threads
        #
        self._get_num_cpu_threads()

    # end __init__

    def _edit_params(self, num_cpu_threads, ts_index, cn_index):

        self.fl._log_print(
            "INFO: changing number cpu_threads to: %s on control-node: %s" %
            (num_cpu_threads, self.fl.cn_ips[cn_index]))
        ts_fd = self.ts_ssh_fds[ts_index]
        cmd = 'sed -i.bak -re "s/(TBB_THREAD_COUNT=)([0-9]+)/\\1%s/g"  %s/params.ini' % (num_cpu_threads,
                                                                                         self.fl._args.run_dir)
        res = ts_fd.execCmd(cmd)

        return

    # end _edit_params

    def _adjust_contrail_services(self):

        fl = self.fl

        #
        # Stop compute node (vrouter) on api server
        #
        cmd = fl._args.api_server_stop_vrouter
        fl._log_print("INFO: stopping vrouter on api-server: %s cmd: %s" %
                      (fl._args.api_server_ip, cmd))
        result = fl.api_ssh_fd.execCmd(cmd)

        #
        # If we can't reach api server, try again, then abort
        #
        if result == None:
            fl._log_print(
                "WARNING: trying again in %ss - problem stopping vrouter on api-server: %s result: %s" %
                (fl._args.sleeptime_between_polling_process, fl._args.api_server_ip, result))
            time.sleep(int(fl._args.sleeptime_between_polling_process))

            result = fl.api_ssh_fd.execCmd(cmd)
            if result == None:
                fl._log_print(
                    "ERROR: failed to stop vrouter on api-server: %s result: %s move'n on.." %
                    (fl._args.api_server_ip, result))
                #self._cleanup ()
                # sys.exit()

        #
        # Restart control-node - but only if we did not just go through a reboot
        #
        if not int(fl._args.run_reboot_cmd):
            fl._restart_cn()

        return

    # end _adjust_contrail_services

    def _stop_contrail_services_and_reboot(self, test_run=0):

        fl = self.fl

        if not int(fl._args.run_reboot_cmd):
            return

        #
        # Stop contrail services on control-node
        #
        cmd = fl._args.control_node_stop_cmd
        for i in range(len(fl.cn_ips)):
            cnshell_self = fl.cn_ssh_fds[i]
            cn_ip = fl.cn_ips[i]
            fl._log_print(
                "INFO: stopping services in preparation for rebooting control-node: %s testrun: %s" %
                (cn_ip, test_run))
            result = cnshell_self.execCmd(cmd)

        #
        # Stop contrail services on api server
        #
        fl._log_print(
            "INFO: stopping services in preparation for rebooting api-server: %s testrun: %s" %
            (fl._args.api_server_ip, test_run))
        cmd = fl._args.api_server_stop_contrail_services_cmd
        result = fl.api_ssh_fd.execCmd(cmd)

        #
        # Sleep a few sec so that stop commands complete
        #
        fl._log_print(
            "INFO: sleeping %ss after stopping contrail services and before reboot testrun: %s" %
            (fl._args.sleeptime_after_cn_restart, test_run))
        time.sleep(int(fl._args.sleeptime_after_cn_restart))

        #
        # Reboot api server first, let it come back up
        #
        cmd = fl._args.reboot_cmd
        fl._log_print("INFO: rebooting api server: %s testrun: %s" %
                      (fl._args.api_server_ip, test_run))
        result1 = fl.api_ssh_fd.execCmd(cmd)
        sleep_time = int(fl._args.sleeptime_after_reboot_api)
        self._sleep_awhile(
            sleep_time, msg="sleeping %ss after reboot and before starting to poll for api server back up.. testrun: %s" %
                            (sleep_time, test_run))
        self._check_servers_up_after_reboot(api_only=True)

        #
        # Reboot control node servers, skip any that were not reachable initially
        #
        cn_reboot_status = ([(False) for i in range(len(fl.cn_ips))])
        for i in range(len(fl.cn_ips)):
            #
            # Get control node info
            #
            cn_fd = fl.cn_ssh_fds[i]
            cn_ip = fl.cn_ips[i]

            #
            # Issue/log reboot
            #
            fl._log_print("INFO: rebooting control node: %s testrun: %s" %
                          (cn_ip, test_run))
            cn_reboot_status[i] = cn_fd.execCmd(cmd)

        #
        # Reboot test servers, skip any that were not reachable initially
        #
        ts_reboot_status = ([(False) for i in range(self.num_test_servers)])
        for i in range(self.num_test_servers):
            #
            # Get test server info
            #
            ts_ip = self.ts_ips[i]
            ts_fd = self.ts_ssh_fds[i]

            #
            # Issue/log reboot
            #
            fl._log_print("INFO: rebooting test server: %s testrun: %s" %
                          (ts_ip, test_run))
            ts_reboot_status[i] = ts_fd.execCmd(cmd)

            #
            # sleep a random amount of time bf rebooting the next test server
            #
            sleep_time = randint(1, 5)
            self._sleep_awhile(
                sleep_time, msg="sleeping %ss between rebooting testservers.. testrun: %s" %
                                (sleep_time, test_run))

        #
        # Wait for some time before continuing. Make it random.
        #
        #sleep_time = int(fl._args.sleeptime_after_reboot) + randint(1, int(self.fl._args.sleeptime_max_random_val))
        sleep_time = int(fl._args.sleeptime_after_reboot)
        self._sleep_awhile(
            sleep_time, msg="sleeping %ss after reboot and before starting to poll for servers back up.. testrun: %s" %
                            (sleep_time, test_run))
        self._check_servers_up_after_reboot()

        return

    # end _stop_contrail_services_and_reboot

    def _sleep_awhile(self, sleep_time, msg):

        self.fl._log_print("INFO: %s" % msg)
        time.sleep(int(sleep_time))

    # end _sleep_awhile

    def _get_num_cpu_threads(self):

        fl = self.fl

        #
        # Get num threads per control node
        #
        self.num_cpu_threads = []
        self.num_cpu_threads_running = []
        self.affinity_mask = []
        for i in range(len(fl.cn_ips)):
            #
            # Get control node info
            #
            cnshell_self = fl.cn_ssh_fds[i]
            cn_ip = fl.cn_ips[i]

            cmd = 'cat /proc/cpuinfo | grep -i processor | wc -l'
            res = cnshell_self.execCmd(cmd)
            cpu_threads = 0
            if res != None:
                res = res[:-1]
                if res.isdigit():
                    cpu_threads = int(res)
            #
            # Get affinity mask bits
            #
            affinity_mask = fl._get_affinity_mask(cnshell_self)

            fl._log_print(
                "INFO: number of cpu threads available on control node: %s is: %s affinity mask: %s" %
                (cn_ip, cpu_threads, affinity_mask))

            #
            # Store cpu available, cpu running on cotrol node and affinity mask info
            #
            self.num_cpu_threads.append(cpu_threads)
            self.num_cpu_threads_running.append(
                self._get_num_cpu_threads_running(cnshell_self, cn_ip, cpu_threads))
            self.affinity_mask.append(affinity_mask)

        return

    # end _get_num_cpu_threads

    def _get_num_cpu_threads_running(self, fd, ip, cpu_trheads_available):

        fl = self.fl

        cmd = fl._args.get_running_thread_env_var_cmd
        res = fd.execCmd(cmd)

        if res == None:
            fl._log_print(
                "DEBUG: not able to get control-nodeI: %s env var cpu_threads process is not running, returning previous /proc num: %s" %
                (ip, cpu_trheads_available))
            return cpu_trheads_available

        else:
            res = res[:-1]

        #
        # Get any threading env variables
        #
        if re.search('TBB_THREAD_COUNT=', res):
            num_cpu_threads = re.search('TBB_THREAD_COUNT=(\d+)', res).group(1)

            #
            # Grab the num cpu_threads it is set to
            #
            if num_cpu_threads.isdigit():
                return_val = num_cpu_threads
                fl._log_print(
                    "INFO: number of cpu threads set as env variable on control node process is: %s on cn: %s" %
                    (return_val, ip))

        #
        # None set, using default
        #
        else:
            return_val = self.num_cpu_threads
            fl._log_print(
                "INFO: number of cpu threads in use on control node: %s is not set as env variable - default from /proc is: %s" %
                (ip, cpu_trheads_available))

        return return_val

    # end _get_num_cpu_threads_running

    def _check_servers_up_after_reboot(self, api_only=False):

        fl = self.fl

        if api_only:
            status1 = True
            status2 = False
            status3 = True
            ts_up_status = ([(True) for i in range(self.num_test_servers)])
            cn_up_status = ([(True) for i in range(len(fl.cn_ips))])
        else:
            status1 = False
            status2 = False
            status3 = False
            ts_up_status = ([(False) for i in range(self.num_test_servers)])
            cn_up_status = ([(False) for i in range(len(fl.cn_ips))])

        #
        # Poll for server up - timeout and abort if it does not happen
        #
        start_time = datetime.now()
        while True:

            #
            # Check if control-nodes are up
            #
            if not status1:
                status1 = True
                for i in range(len(fl.cn_ips)):
                    #
                    # Skip control nodes known to be down or already deemed pingable
                    #
                    if cn_up_status[i] == True:
                        continue
                    #
                    # Get ping status
                    #
                    cn_up_status[i] = self._check_pingable(fl.cn_ips[i])
                    status1 &= cn_up_status[i]

                    if cn_up_status[i] == False:
                        fl._log_print(
                            "WARNING: control node server: %s not responding.." % fl.cn_ips[i])
                    else:
                        pass

                # end for loop

            if not status2:
                status2 = self._check_pingable(fl._args.api_server_ip)

            #
            # Check test servers
            #
            if not status3:
                status3 = True
                for i in range(self.num_test_servers):
                    #
                    # Skip servers known to be down or already deemed pingable
                    #
                    if self.ts_ip_status[i] == None or ts_up_status[i] == True:
                        continue
                    #
                    # Get ping status
                    #
                    ts_up_status[i] = self._check_pingable(self.ts_ips[i])
                    status3 &= ts_up_status[i]

                    if ts_up_status[i] == False:
                        fl._log_print(
                            "ERROR: test server: %s not responding.." %
                            self.ts_ips[i])
                    else:
                        pass

                # end for loop
            else:
                pass

            # end if not status3

            #
            # See if they are all done..
            #
            if status1 and status2 and status3:
                fl._log_print(
                    "INFO: all servers that were online originally are back up")
                break

            delta_time = fl._get_time_diffs_seconds(
                start_time, datetime.now(), 0)
            time_left_sec = int(
                fl._args.timeout_seconds_server_up_after_reboot) - delta_time
            if delta_time > int(fl._args.timeout_seconds_server_up_after_reboot):
                fl._log_print(
                    "ABORT: timed out waiting for servers to come back up - no time left- waited: %ss" % delta_time)
                self._cleanup()
                sys.exit()
            else:
                time_left_sec = int(
                    fl._args.timeout_seconds_server_up_after_reboot) - delta_time
                time_left_min = int(time_left_sec / 60)
                sleep_time = int(
                    fl._args.sleeptime_between_polling_servers_back_up)
                self._sleep_awhile(
                    sleep_time, msg="sleeping %ss until next poll - timout in: %sm" %
                                    (sleep_time, time_left_min))

        # end while loop

        return True

    # end _check_servers_up_after_reboot

    def _check_pingable(self, dst):

        fl = self.fl
        pattern = ' 0% packet loss'
        cmd = "ping %s -c 2 -W 1" % dst

        status, result = fl._get_subprocess_info(cmd)

        return_val = False
        if status:
            if re.search(pattern, result):
                fl._log_print("INFO: server: %s up after reboot" % dst)
                return_val = True
        else:
            pass

        return return_val

    # end _check_pingable

    def _check_timeout_minutes(self, t1, timeout_min):

        #
        # Get delta time in minutes, rounding ok
        #
        delta_time_minutes = int(((datetime.now() - t1).seconds) / 60)

        #
        # See if max time was
        #
        status = delta_time_minutes > int(timeout_min)

        return (status, delta_time_minutes)

    # end _check_timeout_minutes

    def _check_bgp_up_to_mx(self):

        fl = self.fl

        if not int(fl._args.check_bgp_up):
            return

        peering_cn_index = 0
        cn_ip = fl.cn_ips[peering_cn_index]

        #
        # Poll for peer up - timeout and abort if it does not happen
        #
        cmd = "%s %s | grep %s" % (
            fl._args.rtr_cli_show_bgp_neighbor_cmd, cn_ip, fl._args.rtr_bgp_up_state)
        fl._log_print("INFO: checking if bgp is up on router: %s cmd: %s" %
                      (fl._args.rtr_ip, cmd))
        start_time = datetime.now()
        first_timeout = False
        while True:
            #
            # Check if control-node is in Established state on the MX
            #
            result = fl.ssh_rtr.execCmd(cmd)

            if result != None and re.search(fl._args.rtr_bgp_up_state, result):
                fl._log_print(
                    "INFO: bgp up between control-node: %s and mx: %s" %
                    (cn_ip, fl._args.rtr_ip))
                fl._log_print("INFO: bgp up result: %s" % result[:-1])
                return_val = True
                break

            #
            # Check timeouts
            #
            timed_out, timed_minutes = self._check_timeout_minutes(
                start_time, int(fl._args.timeout_minutes_bgp_to_come_up))
            if timed_out:
                #
                # Try restarting control node process
                #
                if not first_timeout:
                    fl._log_print(
                        "WARNING: starting to time out waiting for bgp up between control-node: %s and mx: %s waited: %smin, restarting cn" %
                        (cn_ip, fl._args.rtr_ip, timed_minutes))
                    fl._restart_cn(
                        why="bc peering with MX not coming up", restart_anyway=1)
                    first_timeout = True
                    continue
                else:
                    fl._log_print(
                        "ABORT: timed out waiting for bgp up between control-node: %s and mx: %s waited: %smin" %
                        (cn_ip, fl._args.rtr_ip, timed_minutes))
                    self._cleanup()
                    sys.exit()
            else:
                pass

        return return_val

    # end _check_bgp_up_to_mx

    def _get_remote_pid(self, remote_fd, remote_ip, parent_name, child_name):

        #
        # Get parent PID on remote server
        #
        fl = self.fl
        cmd = "ps -efww | grep %s | grep -v grep | gawk '\\''{print $2}'\\''" % (parent_name)
        remote_parent_pid = remote_fd.execCmd(cmd)[:-1]

        #
        # Get child of parent PID on remote server
        #
        if remote_parent_pid.isdigit():
            cmd = "ps -efww | grep %s | grep ' %s ' | grep -v %s | grep -v grep |  gawk '\\''{print $2}'\\''" % (
                child_name, remote_parent_pid, parent_name)
            remote_child_pid = remote_fd.execCmd(cmd)[:-1]

            if remote_child_pid.isdigit():
                return_val = remote_child_pid
                fl._log_print(
                    "INFO: found pid: %s for process: %s on node: %s" %
                    (remote_child_pid, child_name, remote_ip))
            else:
                return_val = 0
                pass

            return return_val

    # end _get_remote_pid

    def _wait_until_done(self, process, num_cpu_threads=0):

        start_time = datetime.now()
        fl = self.fl
        done = False
        self.ts_done_status = ([(False) for i in range(self.num_test_servers)])
        timed_out, timed_minutes = self._check_timeout_minutes(
            start_time, int(fl._args.timeout_minutes_wait_process))
        while not done:

            #
            # Check each server
            #
            num_done = 0
            for i in range(self.num_test_servers):

                #
                # Skip servers that are already tagged as done
                #
                if self.ts_done_status[i]:
                    num_done += 1
                    continue

                #
                # Skip servers that were down
                #
                if self.ts_ip_status[i] == None and not self.ts_done_status[i]:
                    fl._log_print(
                        "INFO: skip polling test server: %s for test completion server not up" % remote_ip)
                    self.ts_done_status[i] = True
                    num_done += 1
                    continue

                #
                # Get test server info
                #
                remote_ip = self.ts_ips[i]
                remote_fd = self.ts_ssh_fds[i]
                remote_pid = self.pid_parent_flap[i]

                #
                # Check if the test was ever up..
                #
                if remote_pid == None:
                    num_done += 1
                    fl._log_print(
                        "INFO: skip polling test server: %s process was never found" % remote_ip)
                    self.ts_done_status[i] = True
                    continue

                fl._log_print(
                    "INFO: polling test server: %s for process/pid: %s/%s" %
                    (remote_ip, process, remote_pid))

                #
                # Check status of pid
                #
                cmd = "ps -efww | grep %s | grep %s | grep -v grep" % (process,
                                                                       remote_pid)
                result = remote_fd.execCmd(cmd)

                #
                # Note status if return val does not match process/pid
                #
                if result == None or not re.search(remote_pid, result):

                    #
                    # Record "done" status per test server
                    #
                    self.ts_done_status[i] = True
                    num_done += 1

                    if num_cpu_threads:
                        fl._log_print(
                            "INFO: test server: %s done no process: %s with pid: %s found cpu_threads: %s" %
                            (remote_ip, process, remote_pid, num_cpu_threads))
                    else:
                        fl._log_print(
                            "INFO: test server: %s done no process: %s with pid: %s" %
                            (remote_ip, process, remote_pid))

                #
                # Check test servers for process status
                #
                done = self._get_done_status_all()
                if done:
                    fl._log_print("INFO: all test servers are done")
                    break

                #
                # Check for timeout - will need kill all possible remote processes
                #
                timed_out, timed_minutes = self._check_timeout_minutes(
                    start_time, int(fl._args.timeout_minutes_wait_process))
                if timed_out:
                    fl._log_print(
                        "ERROR: timed out waiting for test server: %s to finish waited: %ss  - killing remote process pid: %s" %
                        (remote_ip, timed_minutes, remote_pid))
                    self._kill_remote_process(remote_fd, remote_pid)
                    self.ts_done_status[i] = True

                    #
                    # Re-check all server status now that this one timed out..
                    #
                    done = self._get_done_status_all()
                    continue
                else:
                    pass

            # end looping thru test servers

            if done or num_done == self.num_test_servers:
                fl._log_print(
                    "INFO: done checking for remote testserver status")
                break

            time_left = int(fl._args.timeout_minutes_wait_process) - \
                timed_minutes
            fl._log_print(
                "INFO: sleeping: %ss until next poll - timeout in: %sm" %
                (fl._args.sleeptime_between_polling_process, time_left))
            time.sleep(int(fl._args.sleeptime_between_polling_process))

        # end wait loop

        return True

    # end _wait_until_done
    def _get_done_status_all(self):

        #
        # Check status on all servers - those that were
        # never # up are considered done as well.. (array
        # entry is "None"
        #
        status = True
        for i in range(self.num_test_servers):

            #
            # Return False if any servers are still running
            #
            status &= self.ts_done_status[i]

        return status

    # end _get_done_status_all

    def _kill_remote_process(self, remote_fd, pid):
            #
            # Kill processes
            #
        cmd = "kill -9 %s" % (pid)
        result = remote_fd.execCmd(cmd)

        return result

    # end _kill_remote_process

    def _execute_test_cmd(self, iteration_index=0, num_cpu_threads=0):

        fl = self.fl

        #
        # Launch test on test servers, record pids
        #
        self.pid_parent_flap = []
        for i in range(self.num_test_servers):
            cmd = "cd %s; %s" % (fl._args.run_dir, fl._args.start_bgp_test_cmd)

            #
            # Skip server if status showed dn at test start
            #
            if self.ts_ip_status[i] == None:
                continue

            #
            # Get testserver info
            #
            ts_ip = self.ts_ips[i]
            ts_fd = self.ts_ssh_fds[i]

            #
            # Check rules
            #  if one-to-one, send knob indicating control node index "i"
            #
            if int(fl._args.rule_ts_cn_one_to_one):
                cmd = "%s %s %s" % (
                    cmd, fl._args.rule_ts_cn_one_to_one_knob, i)

            #
            #  Add optinal knob for nroutes
            #
            if int(fl._args.rule_nroutes_per_all_agents):
                num_routes = self._get_num_routes_per_knobs_and_iteration(
                    iteration_index)
                cmd = "%s %s %s" % (
                    cmd, fl._args.rule_nroutes_per_all_agents_knob, num_routes)

            fl._log_print("INFO: running on testserver: %s command: '%s'" %
                          (ts_ip, cmd))
            ts_fd.execCmd(cmd)

            #
            # Get pid of parent flap process (all logs will have this pid)
            #
            pid = self._get_remote_pid(
                ts_fd, ts_ip, 'SCREEN', fl._args.bgp_test_script)
            self.pid_parent_flap.append(pid)

            #
            # Check for error on pid
            #
            if pid == None:
                fl._log_print(
                    "WARNING: problem getting pid from test server: %s'" % ts_ip)
                self.ts_ip_status[i] = False
                continue

        #
        # Poll until parent processes are done
        #
        self._wait_until_done(fl._args.bgp_test_script)

        return

    # end _execute_test_cmd

    def get_ssh_fd(usr, pw, ip, fd):

        #
        # Get ssh fd
        #
        ssh_fd = remoteCmdExecuter()
        ssh_fd.execConnect(ip, usr, pw)

        return ssh_fd

    # end get_ssh_fd

    def _prepare_servers(self):

        fl = self.fl

        username = fl._args.ssh_username
        password = fl._args.ssh_password

        #
        # Get test server ssh fds
        #
        ts_ips = re.split(",", "".join(fl._args.test_server_ips.split()))
        self.ts_ips = []
        self.ts_ip_status = []
        self.ts_ssh_fds = []

        #
        # Cechk to see if this is an iteration situation
        #
        ts_iterate = int(fl._args.test_server_iterations)
        if ts_iterate:
            self.num_test_servers = ts_iterate
            ip = IPAddress(fl._args.test_server_iterations_start_server)
        else:
            self.num_test_servers = len(ts_ips)

        self.num_up = 0
        for i in range(self.num_test_servers):

            #
            # Get either IP address from iteration or test_server ip address list
            #
            if ts_iterate:
                ts_ip = str(ip)
                ip += 1
            else:
                ts_ip = ts_ips[i]

            self.ts_ips.append(ts_ip)
            self.ts_ssh_fds.append(remoteCmdExecuter())

            self.ts_ssh_fds[i].execConnect(ts_ip, username, password)

            #
            # Record server up status, rtn val is None if it is not responding
            #
            res = self.ts_ssh_fds[i].execCmd("pwd")
            self.ts_ip_status.append(res)

            if res != None:
                self.num_up += 1

        #
        # Exit of no test servers are up
        #
        if self.num_up == 0:
            fl._log_print("ABORT: test servers not up")
            self._cleanup()
            sys.exit()

        #
        # Transfer scripts to test servers
        #
        self._prepare_scripts()

        return

    # end _prepare_servers

    def _prepare_scripts(self, descr='pre-run'):

        fl = self.fl

        #
        # Only run this if a testcase is going to run
        #
        if int(fl._args.run_cpu_test) == 0 and int(fl._args.run_test) == 0:
            return
        #
        # tar files on build server
        #

        #
        # Get testserver info
        #
        for i in range(self.num_test_servers):

            #
            # Skip server if status shows down
            #
            if self.ts_ip_status[i] == None:
                continue

            #
            # scp .tar file to ts
            #

            #
            # Get testserver info
            #
            ts_ip = self.ts_ips[i]
            ts_fd = self.ts_ssh_fds[i]

            #
            # mv current bgp directory if it's present
            #
            self._mv_rundir_log(ts_ip, ts_fd, descr)

            #
            # Untar scripts
            #
            cmd = 'tar xvf %s.tar' % fl._args.version
            fl._log_print(
                "INFO: untar script file on test server: %s - (assume tar'd dirs match run dir) cmd: %s" % (ts_ip, cmd))
            result = ts_fd.execCmd(cmd)

        return

    # end _prepare_scripts

    def _save_rundir_log(self, descr):

        fl = self.fl

        #
        # Only run this if a testcase ran
        #
        if int(fl._args.run_cpu_test) == 0 and int(fl._args.run_test) == 0:
            return

        #
        # Rename/save rundir on all servers
        #
        for i in range(self.num_test_servers):

            #
            # Skip server if status shows down
            #
            if self.ts_ip_status[i] == None:
                continue

            #
            # Get testserver info
            #
            ts_ip = self.ts_ips[i]
            ts_fd = self.ts_ssh_fds[i]

            #
            # mv current bgp rundir to names dir
            #
            self._mv_rundir_log(ts_ip, ts_fd, descr)

        return

    # end _save_rundir_log

    def _mv_rundir_log(self, ip, fd, descr):

        fl = self.fl

        script_dir = re.search('^.*\/(\w+)$', fl._args.run_dir).group(1)
        cmd = "find . -name %s/log" % script_dir
        result = fd.execCmd(cmd)
        if result != None and len(result) > 0:
            cmd = 'mv {0}/log {0}_{1}_{2}_log'.format(fl._args.run_dir,
                                                      descr, datetime.strftime(datetime.now(), '%m_%d_%Y-%H_%M_%S'))
            fl._log_print(
                "INFO: moving run dir log to named run dir on test server: %s cmd: %s" % (ip, cmd))
            result = fd.execCmd(cmd)
        else:
            fl._log_print("INFO: did not find rundir log to move: %s/log" %
                          script_dir)

        return

    # end _mv_rundir_log

    def _run_cpu_test(self):

        fl = self.fl

        if int(fl._args.run_cpu_test) == 0:
            return

        fl._log_print("INFO: starting test '_run_cpu_test' on localhost: %s" %
                      fl.localhost_ip)

        #
        # Get test server and cn index vals
        #
        cn_index = fl.cn_index
        ts_index = cn_index

        #
        # Iterate through <n> cpus at a time
        #
        self.cpu_mulitplier = int(fl._args.cpu_mulitplier)

        #
        # Derive CPU iterations per multiplier
        #
        num_cpu_iterations = int(self.num_cpu_threads / self.cpu_mulitplier)

        cpu_threads = self.cpu_mulitplier
        for i in range(num_cpu_iterations):

            #
            # Edit .params file
            #
            #self._edit_params(cpu_threads, ts_index, cn_index)

            #
            # Stop contrail services and reboot (unless param knob precludes that)
            #
            self._stop_contrail_services_and_reboot()

            #
            # Make sure BGP is up with MX
            #
            self._check_bgp_up_to_mx()

            #
            # Stop vrouter and controller on api server
            #
            self._adjust_contrail_services()

            #
            # Check vns are present
            #
            fl._check_vn_all()

            #
            # Start test
            #
            self._execute_test_cmd(0, cpu_threads)

            #
            # Get next cpu val
            #
            cpu_threads = cpu_threads + self.cpu_mulitplier

        # end test loop

    # end _run_cpu_test

    def _get_results(self):

        fl = self.fl

        #
        # Retrieve all the result logs as tar files
        #
        for i in range(self.num_test_servers):
            #
            # Skip servers known to be down
            #
            if self.ts_ip_status[i] == None:
                continue

            #
            # Get test server info
            #
            ts_ip = self.ts_ips[i]
            ts_fd = self.ts_ssh_fds[i]
            ts_pid = self.pid_parent_flap[i]

            #
            # Get logs
            #
            self._get_result_logs(
                ts_ip, ts_fd, fl._args.logfile_name_flap_agent_scale_test, fl._args.logdir_name, ts_pid)

        return

    # end _get_results

    def _get_result_logs(self, dst, fd, name, logdir, pid):

        fl = self.fl

        #
        # check if remote logdir exists, if so, tar logs
        #
        logdir_nopath = re.search('^.*\/(\w+)$', logdir).group(1)
        cmd = "find . -name %s" % logdir_nopath
        result = fd.execCmd(cmd)
        if result != None and len(result) > 0:
            #
            # tar log files on remote server
            #
            cmd = 'cd {0}; tar cvf {1}_{2}_{3}.tar *{3}*.*'.format(logdir,
                                                                   name, dst, pid)
            fl._log_print("INFO: tar log files on test server: %s cmd: %s" %
                          (dst, cmd))
            #result = fd.execCmd (cmd)
        else:
            fl._log_print(
                "ERROR: problem tarring remote logs - no log dir: %s found on testserver: %s" % (logdir, dst))

        #
        # todo scp files over
        #
        return

    # end _get_result_logs

    def _run_test(self):

        fl = self.fl

        if int(fl._args.run_test) == 0:
            return

        #
        # Open file for results
        #
        fl._open_logfile('summary')
        fl._summary_print("Summary %s" % datetime.now())
        fl._summary_print(
            "num_tests: %s num_testservers: %s num_control_nodes: %s" %
            (fl._args.rule_num_tests, len(fl.ts_ips), len(fl.cn_ips)))
        line = "%s\t%s\t%s\t%s\t" % ("ntest", "ip", "#iter", "#xmpp")
        line += "%s\t\t%s\t\t%s\t\t%s\t\t%s\t" % ("#iter_add",
                                                  "#iter_del", "adds", "dels", "tpeers")
        line += "%s\t%s\t\t%s\t\t%s\t%s\t" % ("tadd", "tdel",
                                              "tpeer_ps", "updt_add_ps", "updt_del_ps")
        line += "%s\t%s\t%s\t%s\t" % ("tpeers_and_adds",
                                      "rts_all_ts", "rts_all_ts_M", "rts_all_per_ts")
        line += "%s\t%s" % ("total_updates", "total_updates_M")
        fl._summary_print(line)

        fl._log_print(
            "INFO: starting test '_run_test' %s times on localhost: %s" %
            (fl._args.rule_num_tests, fl.localhost_ip))

        ntimes = 0
        for i in range(int(fl._args.rule_num_tests)):

            descr = self._get_params_descr(i)

            fl._log_print("INFO: start test_n: %s test params: %s" %
                          (i, descr))

            #
            # Stop contrail services and reboot (per param knob)
            #
            self._stop_contrail_services_and_reboot(i)

            #
            # Make sure BGP is up with MX
            #
            self._check_bgp_up_to_mx()

            #
            # Stop vrouter and control-node on api server
            #
            self._adjust_contrail_services()

            #
            # Check vns are present
            #
            fl._check_vn_all()

            #
            # Start test
            #
            self._execute_test_cmd(i)

            #
            # Get result data
            #
            self._get_result_data(i, descr)

            #
            # Move current rundirs to named rundirs (also untar scripts to general bgp dir)
            #
            self._save_rundir_log(descr)

            #
            # Get result logs
            #
            # self._get_results()
            fl._log_print("INFO: done test_n: %s test params: %s" %
                          (i, descr))

            ntimes += 1

            #
            # sleep a bit
            #
            if (i + 1) != int(fl._args.rule_num_tests):
                sleep_time = int(fl._args.sleeptime_between_top_parent_runs)
                self._sleep_awhile(
                    sleep_time, msg="sleeping %ss between top parent test runs %s" % (sleep_time, i))

        # end test loop
        fl._log_print(
            "INFO: done test '_run_test' on localhost: %s ran: %s tests" %
            (fl.localhost_ip, ntimes))

        return

    # end _run_test

    def _get_total_routes(self, rindex):

        fl = self.fl

        return_val =  fl.num_iterations * \
            fl.ninstances[0] * fl.nagents[0] * \
            self._get_num_routes_per_knobs_and_iteration(rindex)

        return int(return_val)

    # end _get_total_routes

    def _get_remote_cli_output(self, cmd, fd, chop=0):

        result = fd.execCmd(cmd)

        return_val = None

        if result != None:
            return_val = result[:-1]

        #
        # Chop
        #
        if chop == 1:
            return_val = return_val[:-1]

        return return_val

    # end _get_remote_cli_output

    def _get_result_data(self, rindex, descr):

        fl = self.fl

        total_expected_routes = self._get_total_routes(rindex)

        #
        # Gather operative data from the runs
        #
        for i in range(len(fl.ts_ips)):
            #
            # Skip server if status showed dn at test start
            #
            if self.ts_ip_status[i] == None:
                continue

            #
            # Get testserver info
            #
            ts_ip = self.ts_ips[i]
            ts_fd = self.ts_ssh_fds[i]

            remote_pid = self.pid_parent_flap[i]
            remote_filename = "%s/%s_%s.txt" % (fl._args.logdir_name,
                                                fl._args.result_averages_logfilename, remote_pid)

            #
            # Make sure log description matches test iteration descr
            #
            cmd = "grep params %s | gawk '\\''{print $3}'\\'' " % remote_filename
            log_descr = self._get_remote_cli_output(cmd, ts_fd)
            fl._summary_print("test %s.%s param descr: %s" %
                              (rindex, i, log_descr))
            if descr != log_descr:
                fl._print_summary_and_regular_log(
                    "WARNING: descr and log_descr don't match: %s vs %s ip: %s ts: %s.%s" % (descr, log_descr, ts_ip, rindex, i))

            fl._log_print(
                "INFO: getting summary datapoints results from ts: %s params: %s filename: %s total_expected_routes: %s" %
                (ts_ip, log_descr, remote_filename, total_expected_routes))

            #
            # Get xmpp peers
            #
            cmd = "grep XMPP %s | gawk '\\''{print $6}'\\'' " % remote_filename
            xmpp_peers = self._get_remote_cli_output(cmd, ts_fd)

            #
            # Get total iterations found for peers, adds, deletes
            #
            cmd = "grep iterations %s | grep found | grep -v add | grep -v del | gawk '\\''{print $7}'\\'' " % remote_filename
            peer_iterations = self._get_remote_cli_output(cmd, ts_fd)
            cmd = "grep iterations %s | grep found | grep add | gawk '\\''{print $7}'\\'' " % remote_filename
            add_iterations = self._get_remote_cli_output(cmd, ts_fd)
            cmd = "grep iterations %s | grep found | grep del | gawk '\\''{print $7}'\\'' " % remote_filename
            del_iterations = self._get_remote_cli_output(cmd, ts_fd)

            #
            # Get total prefixes found for adds, deletes
            #
            cmd = "grep Total %s | grep prefixes | grep add | gawk '\\''{print $6}'\\'' " % remote_filename
            add_prefixes = self._get_remote_cli_output(cmd, ts_fd)
            cmd = "grep Total %s | grep prefixes | grep del | gawk '\\''{print $6}'\\'' " % remote_filename
            del_prefixes = self._get_remote_cli_output(cmd, ts_fd)

            #
            # Get time for peers up, adds, deletes
            #
            cmd = "grep wall %s | grep peers | gawk '\\''{print $10}'\\'' " % remote_filename
            tpeer = self._get_remote_cli_output(cmd, ts_fd, chop=1)
            cmd = "grep wall %s | grep -v peers | grep add | gawk '\\''{print $10}'\\'' " % remote_filename
            tadd = self._get_remote_cli_output(cmd, ts_fd, chop=1)
            cmd = "grep wall %s | grep -v peers | grep del | gawk '\\''{print $10}'\\'' " % remote_filename
            tdel = self._get_remote_cli_output(cmd, ts_fd, chop=1)

            #
            # Get Updates/sec for peers, adds, deletes
            #
            cmd = "grep Peers %s | grep second | gawk '\\''{print $4}'\\'' " % remote_filename
            peer_per_sec = self._get_remote_cli_output(cmd, ts_fd)
            cmd = "grep Updates %s | grep add | gawk '\\''{print $13}'\\'' " % remote_filename
            add_per_sec = self._get_remote_cli_output(cmd, ts_fd)
            cmd = "grep Updates %s | grep del | gawk '\\''{print $13}'\\'' " % remote_filename
            del_per_sec = self._get_remote_cli_output(cmd, ts_fd)

            #
            # Derive data needed for excel charts..
            #
            total_time_peers_up_and_adds = self._get_digit(
                tpeer) + self._get_digit(tadd)
            total_routes_all_servers = total_expected_routes * \
                self.num_test_servers
            total_routes_all_servers_M = round(
                float(total_expected_routes * self.num_test_servers) / 1000000, 2)

            total_updates = total_expected_routes * fl.nagents[0]
            total_updates_M = round(
                float(total_expected_routes * fl.nagents[0]) / 1000000, 1)

            line = "%s\t%s\t%s\t%s\t%s\t\t" % (
                rindex, ts_ip, fl.num_iterations, xmpp_peers, add_iterations)
            line += "%s\t\t%s\t\t%s\t\t%s\t\t" % (del_iterations,
                                                  add_prefixes, del_prefixes, tpeer)
            line += "%s\t%s\t\t%s\t\t%s\t%s\t" % (tadd,
                                                  tdel, peer_per_sec, add_per_sec, del_per_sec)
            line += "%s\t%s\t\t%s\t%s\t" % (total_time_peers_up_and_adds,
                                            total_routes_all_servers, total_routes_all_servers_M, total_expected_routes)
            line += "%s\t%s" % (total_updates, total_updates_M)
            fl._summary_print(line)

            #
            # Get ERROR/WARNING and memory stats from remote testserver flap_test (parent of bgp_stress) logs
            #
            remote_filename = "%s/%s_%s.log" % (fl._args.logdir_name,
                                                fl._args.logfile_name_flap_agent_scale_test, remote_pid)
            fl._log_print(
                "INFO: getting memory stats from ts: %s filename: %s" %
                (ts_ip, remote_filename))

            #
            # Print headers in summary file - format targetsexcel import
            #
            fl._summary_print(
                "mem_stat_id\tts_ip\t\tcn_ip\t\ttot_mem_kB\t\tcn_mem unit\tnormalized_cn_mem")
            line_prepend = "mem_stat: %s\t%s\t" % (rindex, ts_ip)
            for i in range(len(fl.cn_ips)):
                cn_fd = fl.cn_ssh_fds[i]
                cn_ip = fl.cn_ips[i]

                cmd = "grep %s %s | grep total-free-cached | gawk '\\''{print $6 \"\t\" $11 \"\t\t\" $18 \" \" $19 \"\t\t\" $21}'\\'' " % (
                    cn_ip, remote_filename)
                result = self._get_remote_cli_output(cmd, ts_fd)
                if result:
                    # chop newline at the end of the output
                    lines = result.split('\n')[:-1]
                    for i in range(len(lines)):
                        line = "%s %s " % (line_prepend, lines[i])
                        fl._summary_print(line)

                #
                # Grab any ERROR/WARNING messages, add to this process log
                #
                cmd = 'grep -v egrep %s | grep -v "abrt-watch-log" | egrep --color=auto "WARNING|ERROR"' % remote_filename
                result = self._get_remote_cli_output(cmd, ts_fd)
                fl._log_print(
                    "INFO: begin getting errors and warning from ts: %s \n\tcmd: %s \nbegin --------> result:\n%s\nend <--------" %
                    (ts_ip, cmd, result))
                fl._log_print(
                    "INFO: end getting errors and warning from ts: %s result from cmd: %s" % (ts_ip, cmd))

        # end looping through test servers

        return

    # end _get_result_data

    def _get_digit(self, num):

        if num == None or len(num) == 0:
            return_val = -1
        else:
            try:
                return_val = float(num)
                return_val = round(return_val, 1)

            except subprocess.CalledProcessError, OSError:
                return_val = -1

        return return_val

    # end _get_digit

    def _get_num_routes_per_knobs_and_iteration(self, iteration_index):

        fl = self.fl

        if int(fl._args.rule_nroutes_per_all_agents):
            if int(fl._args.rule_nroutes_start_add_val_per_call) > 0:
                if iteration_index == 0:
                    num_routes = int(
                        fl._args.rule_nroutes_start_add_val_per_call)
                else:
                    num_routes = int(fl._args.rule_nroutes_start_add_val_per_call) + \
                        int(fl._args.rule_nroutes_add_val_per_call) * \
                        iteration_index
            else:
                num_routes = int(fl._args.rule_nroutes_add_val_per_call) * \
                    (iteration_index + 1)
        else:
            num_routes = fl.nroutes[0]

        return int(num_routes)

    # end _get_num_routes_per_knobs_and_iteration

    def _get_params_descr(self, iteration_index):

        fl = self.fl

        nroutes = self._get_num_routes_per_knobs_and_iteration(
            iteration_index)
        return_val = "%s_iterations_at_%sx%sx%s" % (
            fl.num_iterations, fl.ninstances[0], fl.nagents[0], nroutes)
        self.test_param_name = return_val

        return return_val

    # end _get_params_descr

    def _order_summary_lines(self, sum_fname, sorted_sum_fname):

        fl = self.fl

        #
        # Copy fist 5 lines of header portion of the file, then sort the
        # rest based on IP adddr and test_num within that
        #
        cmd = 'head -3 {0} | /bin/egrep -v "Summary|num" > {1}; cat {0} | /bin/egrep -v "Summary|WARNING|param|test|mem_stat" | sort -k2,2d -k1,1d >> {1}; grep -m 1 mem_stat_id {0} >> {1};grep "mem_stat\:" {0} >> {1}'.format(
            sum_fname, sorted_sum_fname)
        status, result = fl._get_subprocess_info(cmd)

        return

    # end _order_summary_lines

    def _cleanup(self):

        fl = self.fl

        #
        # Get delta time
        #
        self.test_end_time = datetime.now()
        self.delta_time_minutes = int(
            ((self.test_end_time - self.test_start_time).seconds) / 60)

        #
        # Sort results based on testserver ip addr
        #
        try:
            if fl.summary_fd:
                sorted_filename = "%s/sorted_%s_%s.txt" % (fl._args.logdir_name,
                                                           fl._args.result_averages_logfilename, fl.pid)
                self._order_summary_lines(fl.summary_fd.name, sorted_filename)
                fl._log_print("INFO: result file: %s" % fl.summary_fd.name)
                fl._log_print("INFO: sorted result file: %s" %
                              sorted_filename)
        except:
            pass

        #
        # Makes for easy cut/paste when manually running..
        #
        fl._log_print("INFO: log file: %s" % fl.fd_name)
        fl._log_print(
            'INFO: grep -v egrep %s/*%s* | grep -v "abrt-watch-log" | egrep --color=auto "WARNING|ERROR"' %
            (fl._args.logdir_name, fl.pid))
        fl._log_print(
            'INFO: grep -v egrep %s/*%s* | grep -v "abrt-watch-log" | egrep --color=auto "done no process"' %
            (fl._args.logdir_name, fl.pid))
        fl._log_print('INFO: Test ran for ~%s min' % self.delta_time_minutes)

        #
        # Close logfiles
        #
        try:
            if fl.summary_fd:
                fl.summary_fd.close()
        except:
            pass

        try:
            if fl.fd:
                fl.fd.close()
        except:
            pass

        return

    # end _cleanup

# end class Controller


def main(args_str=None):

    #
    # Init
    #
    self = Controller(args_str)

    #
    # Execute cases
    #
    self._run_cpu_test()

    #
    # Execute cases
    #
    self._run_test()

    #
    # Transfer scripts to test servers
    #
    # self._gather_logs()

    #
    # Cleanup
    #
    self._cleanup()

    return

# end main

if __name__ == "__main__":
    main()
