from __future__ import print_function
import time
import sys
import os
import re
import signal
from netaddr import *
from datetime import datetime, timedelta
from pytz import timezone
import pytz
import subprocess
import traceback
import ast
import os
import socket
#
# Contrail libs
#
from commands import Command
from cn_introspect_bgp import ControlNodeInspect
from ssh_interactive_commnds import *

#
# Used to kill any residual bgp_stress_test processes including zombies
#
BGP_STRESS = None


def log_print(line, fd=''):

    #
    # Get id val from logfilename
    #
    run_id = 0
    if re.search('\d+$', fd.name):
        run_id = re.search('\d+$', fd.name).group()

    msg = "{0} scale{1} {2}".format(datetime.now(), run_id, line)
    print (msg)
    print (msg, file=fd)
    fd.flush()

# end log_print


def open_logfile(fname):

    #
    # Create logdir if needed
    #
    if not os.path.exists('log'):
        os.mkdir('log')

    #
    # Open file
    #
    try:
        fd = open(fname, 'w')
    except (SystemExit, KeyboardInterrupt):
        raise
    except Exception, e:
        print (
            'ABORT: Failed to open file:%s, since this is a scaling script, check that the number of file descriptors (max files) has not been exceeded:[lsof -n, and ulimit -n]', fname)
        sys.exit()

    return fd

# end open_logfile


def get_ssh_fd(usr, pw, ip, fd):

    #
    # Check for 0 IP address, return None if so
    #
    if ip == 0:
        return None

    #
    # Get ssh fd
    #
    ssh_fd = remoteCmdExecuter()
    ssh_fd.execConnect(ip, usr, pw)

    return ssh_fd

# end get_ssh_fd


def get_cn_ispec(ip):

    cn_ispec = ControlNodeInspect(ip)

    return cn_ispec

# end get_cn_ispec


def check_if_swapping(result, who, fd):
    '''Check if system is swapping
    '''
    return_val = False
    try:
        result
        if not re.search(' 0 kB', result):
            log_print(
                "WARNING: system swapping:{0} -> reboot device".format(who), fd)
            return_val = True
    except:
        pass

    return return_val

# end check_if_swapping


def check_for_crash(result, who, fd):
    '''Check if system crashed
    '''
    return_val = False
    if re.search('core', result):
        log_print(
            "WARNING: crash found on: {0} crash files:\n{1}".format(who, result), fd)
        return_val = True

    return return_val

# end check_for_crash


def get_instance_name(ninstances, ri_name, index, ri_domain):

    # stress code uses "instance1" for one instance
    # if ninstances == 1:
    #    name = "%s%s" % (ri_name, index)

    # stress code uses "instance" for iterating, just return full name with index
    # else:
    #    name = ri_name

    name = ri_name

    full_name = "{0}:{1}{2}:{1}{2}".format(ri_domain, ri_name, index)

    return (name, full_name)

# end get_instance_name


def get_total_prefix_expectations(ninstances, import_targets_per_instance, nagents, nroutes, overlapped_prefixes):

    #
    # Agents/intances may be grouped into vrfs, *unless only on instance)
    #
    ntargets = 1
    if ninstances > 1:
        if import_targets_per_instance > 1:
            ntargets = int(ninstances / import_targets_per_instance)

    #
    # Compute num prefixes per instance per agent. Note that if the
    # "overlapped_prefixes" flag is set, then all agents are getting
    # the same set of prefiexes (xmpp_prefix used in the call).
    #
    if not overlapped_prefixes:
        prefixes_per_instance = nagents * nroutes * ntargets
    else:
        prefixes_per_instance = nroutes * ntargets

    #
    # Total vpn prefixes - as seen in route bgp.l3vpn table
    #
    vpn_prefixes = ninstances * nagents * nroutes

    return (prefixes_per_instance, vpn_prefixes)

# end get_total_prefix_expectations


def bgp_scale_mock_agent(cn_usr, cn_pw, rt_usr, rt_pw, cn_ip, cn_ip_alternate, rt_ip, rt_ip2, xmpp_src, ri_domain, ri_name, ninstances, import_targets_per_instance, family, nh, test_id, nagents, nroutes, oper, sleep_time, logfile_name_bgp_stress, logfile_name_results, timeout_minutes_poll_prefixes, background, xmpp_prefix, xmpp_prefix_large_option, skip_krt_check, report_stats_during_bgp_scale, report_cpu_only_at_peak_bgp_scale, skip_rtr_check, bgp_env, no_verify_routes, logging, local_ip):
    '''Performs bgp stress test
    '''

    #
    # For exception handler since it runs as a separate process
    #
    global BGP_STRESS

    #
    # Open logfile for this function/results
    #
    fd = open_logfile(logfile_name_results)

    #
    # Get fd/handles
    #
    if skip_rtr_check != 0:
        rt_self = None
        rt_self2 = None
    else:
        rt_self = get_ssh_fd(rt_usr, rt_pw, rt_ip, fd)
        rt_self2 = get_ssh_fd(rt_usr, rt_pw, rt_ip2, fd)

    cn_self = get_cn_ispec(cn_ip)

    #
    # Get control node ssh fd only if not running in the background - bug w ssh blocking on multiprocessing
    #
    # cnshell_self = 0
    # if not background:
    cnshell_self = get_ssh_fd(cn_usr, cn_pw, cn_ip, fd)

    #
    # xmpp_prefix is optional, if it is 0, do not use it
    #
    overlapped_prefixes = 0
    if not xmpp_prefix:
        xmpp_start_prefix = ''
        omsg = ''
    else:
        xmpp_start_prefix = "--xmpp-prefix=%s" % (xmpp_prefix)

        #
        # If there is an xmpp_start_prefix, then all agents will get the same set of
        # prefixes. And in this case, the number of expected prefixes changes..
        #
        overlapped_prefixes = 1
        omsg = "Overlapping prefixes/agent (xmpp_prefix provided)"

    #
    #
    # xmpp-prefix-large option is an optinal paramter
    #
    if xmpp_prefix_large_option == 0:
        xmpp_prefix_large = ''
    else:
        xmpp_prefix_large = "--xmpp-prefix-format-large"

    #
    # Derive total prefixes expected for each agent vs total
    #
    prefixes_per_instance, vpn_prefixes = get_total_prefix_expectations(
        ninstances, import_targets_per_instance, nagents, nroutes, overlapped_prefixes)

    #
    # Normalize the name
    #
    op = (oper.rsplit()[0][:3]).lower()

    #
    # Get localhost IP
    #
    localhost_ip = get_localhost_ip()

    #
    # process ID
    #
    pid = os.getpid()

    #
    # Record test title
    #
    msg = get_msg_ninst_x_agents_x_nroutes(ninstances, nagents, nroutes)
    log_print("INFO: BGP Stress Test PID:%s" % pid, fd)
    log_print(
        "INFO: BGP Stress Test - CN:{0}  family:{1}  Operation:{2}  ninst X nagent X nroutes = {5}x{3}x{4} NumImportTargetsPerRinstance:{6}".format(cn_ip,
                                                                                                                                                    family, oper, nagents, nroutes, ninstances, import_targets_per_instance), fd)

    #
    # Logfile name is passed to the bgp_stress call
    #
    logfile_name = "--log-file=%s" % (logfile_name_bgp_stress)

    #
    # Derive instance name if only one instance, otherwise use base name (polling and bgp_stress iterates over the names)
    #
    instance_name, full_instance_name = get_instance_name(
        ninstances, ri_name, 1, ri_domain)

    #
    # Check if "--routes-send-trigger" paramter is set. Retrieve the associated
    # file name if so.
    #
    try:
        trigger_file = re.search(
            'send-trigger(\s+|=)(.*)$', logging, re.IGNORECASE)
        if trigger_file != None:
            trigger_file = trigger_file.group(2)
            new_trigger_file = trigger_file + str(pid)
            logging = re.sub(trigger_file, new_trigger_file, logging)
            log_print("DEBUG: found trigger file: %s new_trigger_file:%s" %
                      (trigger_file, new_trigger_file), fd)
    except:
        trigger_file = 0

    #
    # Command to instantiate bgp_stress_test
    #
    bgp_stress_test_command = './bgp_stress_test --no-multicast --xmpp-port=5269 --xmpp-server=%s --xmpp-source=%s --ninstances=%s --instance-name=%s --test-id=%s --nagents=%s --nroutes=%s --xmpp-nexthop=%s %s %s %s %s' % (
        cn_ip_alternate, xmpp_src, ninstances, instance_name, test_id, nagents, nroutes, nh, xmpp_start_prefix, xmpp_prefix_large, logging, logfile_name)

    #
    # Get stats before test run
    #
    if report_stats_during_bgp_scale:
        report_stats(cn_self, rt_self, cnshell_self, cn_ip, rt_ip,
                     "Stats Before Test Run {0}".format(oper), report_cpu_only_at_peak_bgp_scale, fd)

    #
    # Log expected values and bgp_stress_test command
    #
    msg = "ninst X nagent X nroutes = {0}x{1}x{2}".format(
        ninstances, nagents, nroutes)
    log_print(
        "INFO: BGP Stress Test - {0} Total Prefixes Expected/all-instances-cn:{1} Expected/instance-cn:{2} VPN Prefixes-rtr:{3}".format(omsg,
                                                                                                                                        prefixes_per_instance * ninstances, prefixes_per_instance, vpn_prefixes), fd)
    log_print("INFO: %s" % bgp_stress_test_command, fd)

    #
    # Delete prefixes if operation requested is a delete
    #
    (rc, out, err) = (0, 0, 0)
    if re.search('del', oper, re.IGNORECASE):

        #
        # Poll prefix delete time
        #
        del_start_time = datetime.now()
        get_prefix_install_or_delete_time(
            cn_self, rt_self, cn_ip, rt_ip, ri_domain, instance_name, ninstances,  prefixes_per_instance, vpn_prefixes,
            op, family, nagents, nroutes, timeout_minutes_poll_prefixes, skip_krt_check, skip_rtr_check, no_verify_routes, xmpp_src, del_start_time, fd)

    #
    # Install prefixes
    #
    elif re.search('add', oper, re.IGNORECASE):

        #
        # Start bgp_stress_test in the background
        #
        log_print("INFO: Starting bgp_stress on localhost %s" %
                  (localhost_ip), fd)
        BGP_STRESS = Command(bgp_stress_test_command, bgp_env)
        BGP_STRESS.start()
        bgp_start_time = datetime.now()
        log_print("INFO: notable_event started bgp_stress at timestamp: %s" %
                  str(bgp_start_time), fd)
        #
        # Time how long it takes for peers to come up - abort gracefully if timed out
        #
        tdelta, timestamp_all_peers_up, timestamp_at_least_one_peer_up = get_agent_bringup_time(
            cn_self, xmpp_src, full_instance_name, nagents, "xmpp", op, False, bgp_start_time, fd)

        #
        # If a trigger file is indicated, routes will not start until the file
        # is touched. Start "route_add" timer if so.
        #
        if trigger_file and len(trigger_file):
            log_print(
                "INFO: trigger file found: %s sleeping for %s seconds before starting prefix announcements" %
                (new_trigger_file, sleep_time), fd)
            time.sleep(sleep_time)
            cmd = 'touch %s' % new_trigger_file
            try:
                return_val = subprocess.check_output(
                    cmd, stderr=subprocess.STDOUT, shell=True)
                log_print("DEBUG: executed cmd:%s" % cmd, fd)
            except:
                log_print("ERROR: problem executing cmd:%s" % cmd, fd)

            timestamp_trigger_prefix_announcements = datetime.now()
            log_print(
                "INFO: notable_event prefix adds triggered at timestamp: %s" %
                str(timestamp_trigger_prefix_announcements), fd)
            timestamp_start_prefix_announcement = timestamp_trigger_prefix_announcements
        else:
            timestamp_start_prefix_announcement = timestamp_at_least_one_peer_up

        #
        # Hold if this is an agent only test with no prefixes
        #
        if re.search('agents_only', oper, re.IGNORECASE):
            #
            # Get stats after test run
            #
            if not background:
                report_stats(cn_self, rt_self, cnshell_self, cn_ip, rt_ip,
                             "Stats After Install - Peak period {0}".format(oper), report_cpu_only_at_peak_bgp_scale, fd)

            log_print(
                "INFO: sleeping a long time %s seconds or until ctrl-c..." %
                sleep_time, fd)
            time.sleep(sleep_time)

            #
            # Gracefully terminate BGP session with control node,
            # then kill bgp_tress_test
            #
            kill_bgp_stress_python_call('bgp_stress_test', 'python', fd)
            rc, out, err = BGP_STRESS.stop()
            BGP_STRESS = False
            return 0

        #
        # Get prefix install time (polls introspect)
        #
        get_prefix_install_or_delete_time(
            cn_self, rt_self, cn_ip, rt_ip, rt_usr, rt_pw, ri_domain, instance_name, ninstances, prefixes_per_instance, vpn_prefixes, op, family,
            nagents, nroutes, timeout_minutes_poll_prefixes, skip_krt_check, skip_rtr_check, no_verify_routes, xmpp_src, timestamp_start_prefix_announcement, fd)

        #
        # Perform post-install tasks such as stats reporting and sleeping
        #
        post_install_tasks(
            cnshell_self, cn_self, rt_self, cn_ip, rt_ip, oper, sleep_time,
            msg, background, report_stats_during_bgp_scale, report_cpu_only_at_peak_bgp_scale, fd)

        #
        # Terminate BGP session with control node by t stopping bgp_stress python
        # child first, grab timestamp (routes stop at that point), then stop bgp_stress
        #
        log_print(
            "DEBUG: stopping route announcements/agents.. stopping python first", fd)
        kill_bgp_stress_python_call('bgp_stress_test', 'python', fd)
        del_start_time = datetime.now()
        log_print(
            "INFO: notable_event stopping prefix announcements at timestamp: %s" %
            (str(del_start_time)), fd)

        #
        # Stop bgp_stress
        #
        rc, out, err = BGP_STRESS.stop()
        log_print("DEBUG: after stop attempt for bgp_stress..", fd)
        BGP_STRESS = False

        #
        # Get prefix delete time (polls introspect)
        #
        get_prefix_install_or_delete_time(
            cn_self, rt_self, cn_ip, rt_ip, rt_usr, rt_pw, ri_domain, instance_name, ninstances,  prefixes_per_instance, vpn_prefixes,
            "del", family, nagents, nroutes, timeout_minutes_poll_prefixes, skip_krt_check, skip_rtr_check, no_verify_routes, xmpp_src, del_start_time, fd)

    #
    # Get stats after test run
    #
    if report_stats_during_bgp_scale:
        report_stats(cn_self, rt_self, cnshell_self, cn_ip, rt_ip,
                     "Stats After Test Run {0}".format(oper), report_cpu_only_at_peak_bgp_scale, fd)

    #
    # Print logfile info
    #
    log_print("INFO: Log file: %s" % fd.name, fd)

    return

# end bgp_scale_mock_agent


def kill_bgp_stress_python_call(child_name, child_of_child_name, fd, retry=2, delay=5):

    #
    # Parent is this process
    #
    parent_pid = os.getpid()

    #
    # Get correspnding child process (bgp_stress_test) pid (noting that many may be running from other parents)
    #
    child_ps_line = subprocess.check_output(
        'ps -efww | \grep %s | grep " %s " | grep -v grep' %
        (child_name, parent_pid), stderr=subprocess.STDOUT, shell=True)
    log_print(
        "DEBUG: bgp_stress ps line:%s that matched this child:%s and parent pid:%s" %
        (child_ps_line, child_name, parent_pid), fd)
    bgp_stress_test_pid = 0
    try:
        re.search('\d+', child_ps_line)
        bgp_stress_test_pid = int(re.search('\d+', child_ps_line).group())
        log_print("DEBUG: bgp_stress_test pid found:%s" %
                  bgp_stress_test_pid, fd)
    except:
        pass

    while True and bgp_stress_test_pid:
        cmd = 'ps -efww |  grep %s | grep " %s " | grep -v %s | grep -v grep' % (
            child_of_child_name, bgp_stress_test_pid, child_name)
        #log_print ("DEBUG: cmd: %s" % cmd, fd)

        #
        # Search for the child_of_the_child (python), where the pid matches it's parent,
        # bgp_stress_test pid, but precludes the child itself (bgp_stress_test name)
        #
        try:
            child_of_child_ps_line = subprocess.check_output(
                cmd, stderr=subprocess.STDOUT, shell=True)
            python_pid = int(re.search('\d+', child_of_child_ps_line).group())
            log_print(
                "DEBUG: found python pid:%s ps of bgp_stress_test child python:%s" %
                (python_pid, child_of_child_ps_line), fd)

            #
            # Send SIGKILL to python shild of bgp_stress_test
            #
            try:
                os.kill(python_pid, signal.SIGKILL)
                log_print("DEBUG: SIGKILL %s pid:%s" %
                          (child_of_child_name, python_pid), fd)
                break
            except OSError:
                pass

        except subprocess.CalledProcessError, error:
            retry -= 1
            log_print("WARNING: command %s failed: %s" %
                      (cmd, error.output), fd)

            #
            #  Retry
            #
            if retry > 0:
                log_print("WARNING: command %s failed: %s" %
                          (cmd, error.output), fd)

                #
                # Check if bgp_stress is defunct (possibly due to assert on hold-time expire), if so send SIGKILL
                #
                if re.search('defunct', child_ps_line, re.IGNORECASE):
                    log_print(
                        "ERROR: bgp_stress_test pid:%s state is defunct (check if it crashed), no child python process, sending it SIGKILL line:%s" %
                        (bgp_stress_test_pid, child_ps_line), fd)
                    if type(bgp_stress_test_pid) == int:
                        try:
                            os.kill(bgp_stress_test_pid, signal.SIGKILL)
                            log_print("INFO: sending SIGKILL %s pid:%s" %
                                      (child_name, bgp_stress_test_pid), fd)
                        except OSError:
                            pass

                    break

                log_print(
                    "WARNING: retry:%d Command %s after sleeping  %d seconds" %
                    (retry, cmd, delay), fd)
                time.sleep(delay)
                continue
            else:
                log_print(
                    "ERROR: problem bringing down python (called by bgp_stress_test pid:%s) move'n on.." %
                    bgp_stress_test_pid, fd)
        break

# end kill_bgp_stress_python_call


def _cleanup_fds(rt_self, cn_self, fd):

    if rt_self.close:
        rt_self.close()
    if cn_self.close:
        cn_self.close()
    if fd:
        fd.close()

# end _cleanup_fds


def post_install_tasks(cnshell_self, cn_self, rt_self, cn_ip, rt_ip, oper, sleep_time, test_info, background, report_stats_during_bgp_scale, report_cpu_only_at_peak_bgp_scale, fd):

    #
    # Get stats after test run
    #
    # if not background and report_stats_during_bgp_scale != 0:
    if report_stats_during_bgp_scale:
        report_stats(cn_self, rt_self, cnshell_self, cn_ip, rt_ip,
                     "Stats After Install - Peak period {0}".format(oper), report_cpu_only_at_peak_bgp_scale, fd)

    #
    # Get sleep messages (sleep_time determined by calling script)
    #
    if re.search('hold', oper, re.IGNORECASE):
        msg = "CTL-C to get out, or wait a really long time..."
    else:
        msg = "%s %s test" % (test_info, oper)

    log_print(
        "INFO: sleeping for %s seconds after prefix installation of: %s" %
        (sleep_time, msg), fd)
    time.sleep(sleep_time)

    return

# end post_install_tasks


def get_agent_bringup_time(self, ip, full_instance_name, num_peers, encoding, oper, log_details, start_time, fd):

    log_print(
        "INFO: polling for %s agent peers to come up instance:%s oper:%s at:%s" %
        (num_peers, full_instance_name, oper, str(start_time)), fd)

    #
    # Note that only one instance name is used
    #
    tdelta, timestamp_done, timestamp_at_least_one_peer_up = get_time_bringup_or_teardown_peers(
        self, ip, full_instance_name, num_peers, encoding, oper, log_details, start_time, fd)

    #
    # Abort this instance of bgp_stress if agent peers bring-up times out
    #
    if tdelta == 'TimeoutWaitingPeersToComeUp':
        log_print(
            "ERROR: agent peers not coming up, aborting this bgp_stress_test result:%s " %
            tdelta, fd)
        kill_bgp_stress_python_call('bgp_stress_test', 'python', fd)
        rc, out, err = BGP_STRESS.stop()
        fd.close()
        sys.exit()

    return (tdelta, timestamp_done, timestamp_at_least_one_peer_up)

# end get_agent_bringup_time


def get_agent_teardown_time(self, ip, instance_full_name, num_peers, encoding, oper, log_details, start_time, fd):

    log_print("INFO: Waiting for {0} agent peers to go dn.. instance:{1}".format(
        num_peers, full_instance_name), fd)
    tdelta, timestamp_done = get_time_bringup_or_teardown_peers(
        self, ip, instance_full_name, num_peers, encoding, oper, log_details, start_time, fd)

    return (tdelta, timestamp_done)

# end get_agent_teardown_time


def get_time_bringup_or_teardown_peers(self, ip, instance_full_name, num_peers, encoding, oper, log_details, start_time, fd):

    sleeptime_between_introspect_polls = 1
    at_least_one_peer_up_noted = 0
    time_chk = 0
    if re.search('del', oper, re.IGNORECASE):
        peers_up = num_peers
        max_time = 15  # min
        while peers_up > 0:
            peers_up = self.get_cn_bgp_neighbor_stats_element(
                'count', 'xmpp', 'up', instance_full_name)
            if (peers_up == 0):
                delta_time, timestamp_done = get_delta_time(start_time)
                log_print("INFO: notable_event peers down at timestamp: %s",
                          str(timestamp_done), fd)
                continue

            #log_print ("DEBUG: in del oper: %s peers_up:%s (out of: %s)" % (oper, peers_up, num_peers), fd)

            #
            # Check timeout val
            #
            time_chk, time_now = get_delta_time(start_time, 'minutes')
            if time_chk >= max_time:
                log_print(
                    "ERROR: timeout waiting for peers to go down... waited:%s minutes" %
                    time_chk, fd)
                return ('TimeoutWaitingPeersToComeUp', time_chk)

            #log_print ("DEBUG: sleeping for %s seconds inbetween introspect polling for peers oper:%s" % (sleep_time, oper), fd)
            time.sleep(sleeptime_between_introspect_polls)

    elif re.search('add', oper, re.IGNORECASE):
        peers_up = 0
        max_time = 15  # min
        waited = 1
        while peers_up < num_peers:
            peers_up = int(self.get_cn_bgp_neighbor_stats_element(
                'count', 'xmpp', 'up', instance_full_name))

            #
            # Record at least one or more peers up - prefix adds have started
            #
            if peers_up > 0 and at_least_one_peer_up_noted == 0:
                at_least_one_peer_up_noted = 1
                t1, timestamp_at_least_one_peer_up = get_delta_time(
                    start_time)
                log_print(
                    "INFO: notable_event at least one peer up at timestamp: %s" %
                    str(timestamp_at_least_one_peer_up), fd)

            #
            # Grab the add timestamp as soon as peers are up
            #
            if (peers_up == num_peers):
                delta_time, timestamp_done = get_delta_time(start_time)
                log_print("INFO: notable_event peers up at timestamp: %s" %
                          str(timestamp_done), fd)
                continue

            #
            # Sleep longer if already waited 2 min.. Just to avoid hammering the DUT
            #
            if waited > 120:
                log_print(
                    "DEBUG: sleeping %s sec in get_time_bringup_or_teardown_peers oper: %s peers_up:%s (out of: %s) timeout_in:%sm" %
                    (sleeptime_between_introspect_polls * 4, oper, peers_up, num_peers, max_time - time_chk), fd)
                time.sleep(sleeptime_between_introspect_polls * 4)

            #
            # Check timeout val
            #
            time_chk, time_now = get_delta_time(start_time, "minutes")
            if time_chk >= max_time:
                log_print(
                    "ERROR: timeout waiting for peers to come up... inst:%s waited:%s minutes tnow:%s" %
                    (instance_full_name, str(time_chk), str(time_now)), fd)
                return ('TimeoutWaitingPeersToComeUp', 0, 0)

            #log_print ("INFO: sleeping for %s seconds inbetween introspect polling for peers oper:%s" % (sleeptime_between_introspect_polls, oper), fd)
            time.sleep(sleeptime_between_introspect_polls)
            waited += 1
    else:
        log_print(
            "ERROR: invalid operation in timing peer bringup/teardown:%s" %
            oper, fd)
        return None

    #
    # Log the time it took for peers to come up (or go down)
    #
    delta_time_str = timedelta_to_string(delta_time)
    log_print(
        "INFO:    Elapsed time to %s %s peers:%ss (total peers found:%s)" %
        (oper, num_peers, delta_time_str, peers_up), fd)

    return (delta_time, timestamp_done, timestamp_at_least_one_peer_up)

# end get_time_bringup_or_teardown_peers


def get_time_diffs_seconds(t1, t2, decimal_places):

    return_val = 0
    if type(t1) == datetime and type(t2) == datetime:
        #
        # Check date is not in the past
        #
        delta_time = (t2 - t1)
        if delta_time.days < 0:
            log_print("ERROR: time diff results in a past date t1:%s t2:%s" %
                      (t1, t2))
            return 0

        return_val = float("%s.%s" % (str(abs(delta_time).seconds),
                                      str(abs((delta_time)).microseconds)[:decimal_places]))

    else:
        log_print(
            "ERROR: time1 or time2 not type datatime: t1 type:%s t2 type:%s" %
            (type(t1), type(t2)))

    return return_val

# end get_time_diffs_seconds


def timedelta_to_string(delta_time):

    return_val = 0

    if type(delta_time) == timedelta:
        return_val = float("%s.%s" %
                           (str(abs(delta_time).seconds), str(abs((delta_time)).microseconds)[:3]))
        #seconds = (delta_time).seconds
        #microseconds = (delta_time).microseconds
        #return_val = float("%s.%s" % (seconds, str(microseconds)[:3]))
    else:
        log_print(
            "ERROR: delta_time wrong type, expecting timedelta type(%s) is:%s" %
            (delta_time, type(delta_time)))

    return return_val

# end timedelta_to_string


def get_time_units(num_bgp_peers, oper):

    if re.search('del', oper, re.IGNORECASE):
        return_val = 'seconds'

    elif num_bgp_peers < 2500:
        return_val = 'microseconds'

    else:
        #
        # default to seconds
        #
        return_val = 'seconds'

    return return_val

# end get_time_units


def get_kernel_routes_light(self):
    '''Use this commad for scale tests on juniper routers to get kernel routes
       It is much lighter weight than "show route forwarding-table summary.
       Must be run as root.
    '''

    #
    # Extract route field after executing command
    #
    routes = re.search('\d+', self.execCmd('ifsmon -Id | grep ROUTE'))

    #
    # Return kernel routes
    #
    return routes.group()

# end get_kernel_routes_light


def get_localhost_ip():
    local_host = socket.gethostname()
    from test_flap_agent_scale import *
    return TestBGPScale.inputs.host_data[local_host]['host_control_ip']
#    cmd = 'resolveip -s `hostname`'
#    cmd = "ip addr show | \grep 192.168.200 | awk '{print $2}' | cut -d '/' -f 1"
#    ip = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
#    return ip[:-1]  # chop newline

# end get_localhost_ip


def check_krt_queue_empty(self, oper, rt_prefixes, expected_prefixes, fd):
    '''This is a cli show command on the router. Only use this periodically
       during the test, it is cpu intense and slow.. Only issue when near
       the end of rib install. Otherwise return "False"
    '''
    #
    # Check if we are even close yet for an add
    #
    if re.search('add', oper, re.IGNORECASE):
        if (rt_prefixes < (expected_prefixes - 500)):
            return "WaitChk"

    elif re.search('del', oper, re.IGNORECASE):
        if (rt_prefixes > (expected_prefixes + 500)):
            return "WaitChk"

    #
    # Get krt info
    #
    cmd = 'cli -c "show krt queue | match %s | match gf"' % oper
    result = self.execCmd(cmd)

    return_val = False
    if result == None or re.search('gf', result):
        return_val = False
    else:
        return_val = True

    return return_val

# end check_krt_queue_empty


def get_peer_states(self, xmpp_src, nagents, instance, pending_updates, fd):
    '''Get peer state
    '''
    #
    # Iterate through a list of peers checking if they are up or not
    #
    number_peers_up = 0
    ip = IPAddress(xmpp_src)
    for i in range(nagents):
        status, peer_state = self.get_cn_bgp_neighbor_element(
            str(ip), "state")
        log_print(
            "INFO: instance:%s xmpp_peer:%s pending_updates:%s STATE:%s" %
            (instance, str(ip), pending_updates, peer_state), fd)
        ip += 1

    return

# end get_peer_states


def check_peers_up(self, ip_start, num_peers, encoding, oper, print_peer_status, fd):
    '''Check that all the peers are up
    '''
    #
    # Iterate through a list of peers checking if they are up or not
    #
    number_peers_up = 0
    ip = IPAddress(ip_start)
    for i in range(num_peers):

        t1 = datetime.now()
        status, peer_state = self.get_cn_bgp_neighbor_element(
            str(ip), "state")
        status, peer_encoding = self.get_cn_bgp_neighbor_element(
            str(ip), "encoding")
        t2 = datetime.now()

        #
        # Check if the peer is up with matchinng encoding
        #
        if status is True and re.match('Established', peer_state, re.IGNORECASE):
            if re.match(encoding, peer_encoding, re.IGNORECASE):
                number_peers_up += 1

        #
        # Optionally log peers not up yet
        #
        elif oper == 'add':
            if print_peer_status:
                log_print("INFO: Peer:{0} status:{1} state:{2} encoding_param:{3} encoding_found:{4}".format(
                    ip, status, peer_state, encoding, peer_encoding), fd)

        t3 = datetime.now()
        ip += 1

    log_print("INFO: Total peers established: {0} (out ot {1})".format(
        number_peers_up, num_peers), fd)

    return number_peers_up

# end check_peers_up


def check_peer_error(self, ip, fd):

    status, last_error = self.get_cn_bgp_neighbor_element(
        str(ip), 'last_error')

    #
    # Log if there is an error
    #
    if status is True and last_error:
        status, peer_encoding = self.get_cn_bgp_neighbor_element(
            str(ip), 'encoding')
        log_print("WARNING: {0} peer:{1} error notification:{2} peer found?:{3}".format(
            peer_encoding, ip, last_error, status), fd)

    return last_error

# end check_peer_error


def check_peers_for_errors(self, ip_start, num_peers, print_logs, fd):
    '''See if a peer has an error
    '''

    #
    # Iterate through a list of peers checking if they are up or not
    #
    number_peers_with_errs = 0
    ip = IPAddress(ip_start)
    for i in range(num_peers):

        #
        # Success if the last_state_at matches previous time for last_state_at
        #
        err = check_peer_error(self, ip, fd)
        if err is not None:
            number_peers_with_errs += 1

        if print_logs:
            log_print("INFO: Peer:{0} err:{1}".format(ip, err), fd)

        ip += 1

    #
    # Log it if needed
    #
    if number_peers_with_errs:
        log_print("INFO: Total peers with errors logged:{0} (out of {1} checked)".format(
            number_peers_with_errs, num_peers), fd)

    return number_peers_with_errs

# end check_peers_for_errors


def get_shell_cmd_output(self, cmd, fd):
    '''This is a cli show command on the router to get dram memory usage info
    '''
    #
    # Execute command at the shell
    #
    return self.execCmd(cmd)

# end get_shell_cmd_output


def get_rtr_dram_pct_utlization(self, fd):
    '''This is a cli show command on the router to get dram memory usage info
    '''
    #
    # Get chassis routing-engine memory total and % utilized
    #
    mem1 = self.execCmd(
        'cli -c "show chassis routing-engine | display xml | match memory-dram-size"')
    memory_dram_size = int(re.search('\d+', mem1).group())

    mem2 = self.execCmd(
        'cli -c "show chassis routing-engine | display xml | match memory-buffer-utilization"')
    memory_re_utlization = int(re.search('\d+', mem2).group())

    return (memory_dram_size, memory_re_utlization)

# end get_rtr_dram_pct_utlization


def get_rt_l3vpn_prefixes(self, rtr_ip, rtr_usn, rtr_pwd, instance_name, ninstances, nbr_ip, fd):
    '''This is a cli show command on the router
    '''
    if not nbr_ip:
        log_print("ERROR: Missing bgp neighbor IP address parameter", fd)
        return (0, 0)
    local_ip = get_localhost_ip()
    #
    # Get xml output of show bgp neighbor
    #
    active_prefixes_resp = {}
    active_prefixes_resp = self.execCmd(
        'show bgp neighbor {0}'.format(nbr_ip), rtr_usn, rtr_pwd, rtr_ip, local_ip)
#        'show bgp neighbor {0} | display xml | grep received-prefix-count'.format(nbr_ip), rtr_usn, rtr_pwd, rtr_ip, local_ip)
#        'show route table bgp.l3vpn.0 receive-protocol bgp {0} active-path '.format(nbr_ip), rtr_usn, rtr_pwd, rtr_ip, local_ip)
    #
    # Get out if no bgp neigbor present yet
    #
    if not active_prefixes_resp:
        return (0, 0)

    #
    # The first count is from the bgp.l3vpn.inet.0 table
    #
    #log_print("INFO: %s" %active_prefixes_resp, fd)
    #var = active_prefixes_resp.splitlines()
    #log_print("INFO: %s" %json1_data, fd)
    #l3vpn_prefix_count = int(re.search('\d+', var[0]).group())
    #l3vpn_prefix_count = int(active_prefixes_resp['route-information'][0]['route-table'][0]['destination-count'][0]['data'])
    active_prefixes_resp_dict = ast.literal_eval(active_prefixes_resp)
#    log_print("INFO: %s" %active_prefixes_resp_dict, fd)
# l3vpn_prefix_count =
# int(active_prefixes_resp_dict["bgp-information"][0][][0]['destination-count'][0]['data'])
    l3vpn_prefix_count = int(active_prefixes_resp_dict[
                             'bgp-information'][0]['bgp-peer'][0]['bgp-rib'][0]['received-prefix-count'][0]['data'])
    log_print("INFO: Active Prefixes : %s" % l3vpn_prefix_count, fd)

    #
    # TODO: this is a hack so that just the bgp.l3vpn table is counted
    #
    return (l3vpn_prefix_count, l3vpn_prefix_count)

    #
    # Get xml output of instance names, note that this does not include the bgp.l3vpn table name
    #
    #cmd = 'cli -c "show bgp neighbor {0} | display xml | grep name | grep {1}"'.format(nbr_ip, instance_name)
    cmd = 'show bgp neighbor {0} | display xml | grep name'.format(nbr_ip)
    names_resp = self.execCmd(cmd)

    #
    # Get out if no instance info present yet
    #
    if not names_resp:
        log_print("WARNING: no bgp neighbor:{0} on router".format(nbr_ip), fd)
        return (0, 0)

    #
    # Iterate over the bgp neighbor instance names, skipping non-instance names
    #
    var_names = names_resp.splitlines()
    instance_prefix_count = 0
    index_prefixes = 1  # Skip first element, it is the bgp.l3vpn count
    for i in range(len(var_names)):

        #
        # "shouldn't" get here..
        #
        if index_prefixes >= len(var):
            break

        #
        # Extract element value
        #("DEBUG: i:%s, instance_prefix_count:%s, index_prefix:%s, var[index_prefix]:%s, var_names[i]:%s" %(i, instance_prefix_count, index_prefix, var[index_prefix],  var_names[i]), fd)
        #
        element_val = re.search('\d+', var[index_prefixes])
        index_prefixes += 1

        #
        # Check for non-existant match before adding to tally
        #
        if element_val:

            #
            # Check instance name matches before tallying - TODO, not sure we care..
            #
            instance_prefix_count += int(element_val.group())

        #log_print ("DEBUG: time how long this call takes..".format(instance_prefix_count, fd))

    return (l3vpn_prefix_count, instance_prefix_count)

# end get_rt_l3vpn_prefixes


def get_cn_introspect_elements(self, ninstances, ri_domain, ri_name, family, xmpp_src, oper, nagents, time_chk, fd):

    cn_prefixes = 0
    cn_pending_updates = 0
    cn_markers = 0
    cn_paths = 0
    cn_primary_paths = 0
    cn_secondary_paths = 0
    cn_infeasible_paths = 0

    status = 0
    peer_state = 0
    for i in range(ninstances):

        #
        # Get full instance name
        #
        instance_name, full_instance_name = get_instance_name(
            ninstances, ri_name, i + 1, ri_domain)

        #
        # Get control node active prefiexes for this instance
        #
        #nprefixes = self.get_cn_routing_instance_bgp_active_paths (full_instance_name, family)
        status, nprefixes = self.get_cn_routing_instance_table_element(
            full_instance_name, family, 'prefixes')

        #
        # Get control node pending_updates for this instance
        #
        # paths, primary_paths, secondary_paths and infeasible_paths
        #
        status, pending_updates = self.get_cn_routing_instance_table_element(
            full_instance_name, family, 'pending_updates')
        status, markers = self.get_cn_routing_instance_table_element(
            full_instance_name, family, 'markers')
        status, paths = self.get_cn_routing_instance_table_element(
            full_instance_name, family, 'paths')
        status, primary_paths = self.get_cn_routing_instance_table_element(
            full_instance_name, family, 'primary_paths')
        status, secondary_paths = self.get_cn_routing_instance_table_element(
            full_instance_name, family, 'secondary_paths')
        status, infeasible_paths = self.get_cn_routing_instance_table_element(
            full_instance_name, family, 'infeasible_paths')

        #
        # Get xmpp status if there are pending updates for a long period of time - note that time_chk is in minutes
        #
        if oper == "add" and type(pending_updates) == int and pending_updates > 0 and time_chk > 1:
            get_peer_states(self, xmpp_src, nagents,
                            full_instance_name, pending_updates, fd)

        #
        # Get integer return values, or 0 (log errors)
        #
        cn_prefixes += check_introspect_return_values(nprefixes,
                                                      'prefixes', full_instance_name, fd)
        cn_pending_updates += check_introspect_return_values(pending_updates,
                                                             'pending_updates', full_instance_name, fd)
        cn_markers += check_introspect_return_values(markers,
                                                     'markers', full_instance_name, fd)
        # New:paths, primary_paths, secondary_paths and infeasible_paths
        cn_paths += check_introspect_return_values(paths,
                                                   'paths', full_instance_name, fd)
        cn_primary_paths += check_introspect_return_values(primary_paths,
                                                           'primary_paths', full_instance_name, fd)
        cn_secondary_paths += check_introspect_return_values(secondary_paths,
                                                             'secondary_paths', full_instance_name, fd)
        cn_infeasible_paths += check_introspect_return_values(
            infeasible_paths,
            'infeasible_paths', full_instance_name, fd)

    return (cn_prefixes, cn_pending_updates, cn_markers, cn_paths, cn_primary_paths, cn_secondary_paths, cn_infeasible_paths)

# end get_cn_introspect_elements


def check_introspect_return_values(val, element_name, instance, fd):

    #
    # Check if error codes, if so, log and return 0
    #
    return_val = 0
    if type(val) == str:
        #log_print ("WARNING: rtn_val:{0} val_ype:{1} while retrieving {2} from instance: {3} chk if cn crashed..".format(val, type(val), element_name, instance), fd)
        return_val = 0
    elif type(val) == None:
        #log_print ("WARNING: rtn_val:{0} val_ype:{1} while retrieving {2} from instance: {3} chk if cn crashed..".format(val, type(val), element_name, instance), fd)
        return_val = 0
    elif type(val) == int:
        return_val = val

    return return_val

# end check_introspect_return_values


def check_done_flags(cn_done, rt_done, skip_rtr_check, skip_krt_check, krt_clear, oper, timestamp_done_cn, timestamp_done_rt, fd):

    #
    # See if all operations are finished
    #
    return_val = False
    if (cn_done == True and rt_done == True and (skip_krt_check != 0 or krt_clear == True)):

        #
        # Get the later of the two timestamps, that is, the entire test is only
        # done when both are done.
        #
        timestamp_done = timestamp_done_cn
        if skip_rtr_check != 1 and timestamp_done_rt > timestamp_done_cn:
            timestamp_done = timestamp_done_rt

        log_print("INFO: notable_event finished prefix %s timestamp: %s" %
                  (oper, str(timestamp_done)), fd)

        return_val = True

    return return_val

# end check_done_flags


def get_prefix_install_or_delete_time(cn_self, rt_self, cn_ip, rt_ip, rt_usr, rt_pw, ri_domain, ri_name, ninstances, prefixes_per_instance, vpn_prefixes, oper, family, nagents, nroutes, timeout_minutes_poll_prefixes, skip_krt_check, skip_rtr_check, no_verify_routes, xmpp_src, start_time, fd):

    #
    # Return if no_verify is set
    #
    if no_verify_routes:
        return 0

    #
    # Sometimes there are no prefixes, if so, just end it now..
    #
    if prefixes_per_instance == 0:
        return 0

    #
    # Each instances has the same number of expected prefixes
    #
    total_expected_prefixes = prefixes_per_instance * ninstances

    #
    # Loop until it the number of routes has been reached, or timeout if count does not change for <n> times
    #
    time_chk = 0
    cn_prefixes = 0
    cn_pending_updates = 0
    cn_markers = 0
    rt_prefixes = 0
    rt_vpn_prefixes = 0
    cn_delta_seconds = 0
    rt_delta_seconds = 0
    return_val = 0
    timestamp_done_cn = ''
    timestamp_done_rt = ''
    sleeptime_between_introspect_polls = 5

    #
    # Set expected prefixe count and timeout according to add or delete
    #
    if re.search('add', oper, re.IGNORECASE):
        expected_prefix_count = total_expected_prefixes
        max_time = timeout_minutes_poll_prefixes
    if re.search('del', oper, re.IGNORECASE):
        expected_prefix_count = 0
        max_time = timeout_minutes_poll_prefixes

    #
    # Check routes until either all are installed or all are deleted, depending on the oper
    #
    cn_done = False
    if skip_rtr_check != 0:
        rt_done = True
        krt_clear = True
    else:
        rt_done = False
        krt_clear = False
    while True:

        #
        # Iterate throuh the control node instance tables
        #
        if not cn_done:
            cn_prefixes, cn_pending_updates, cn_markers, cn_paths, cn_primary_paths, cn_secondary_paths, cn_infeasible_paths = get_cn_introspect_elements(
                cn_self, ninstances, ri_domain, ri_name, family, xmpp_src, oper, nagents, time_chk, fd)

        #
        # Iterate through the router instance tables
        #
        if not rt_done:
            if rt_self != None:
                rt_vpn_prefixes, rt_prefixes = get_rt_l3vpn_prefixes(
                    rt_self, rt_ip, rt_usr, rt_pw, ri_name, ninstances, cn_ip, fd)

        #
        # Check if control node is done, but only if not already done in previous loop iteration
        #
        if not cn_done:
            cn_done = check_if_done_polling_for_prefixes(
                oper, cn_prefixes, expected_prefix_count, "cn", cn_pending_updates, fd)

            #
            # Get delta times if done - only call this once per test
            #
            if cn_done:
                timestamp_done_cn = datetime.now()
                cn_delta_seconds = get_time_diffs_seconds(
                    start_time, timestamp_done_cn, decimal_places=2)

        #
        # Check if rotuer is done, note it's total is based on the bgp.l3vpn table.
        #
        if (rt_done == False or krt_clear == False):
            rt_done = check_if_done_polling_for_prefixes(
                oper, rt_vpn_prefixes, expected_prefix_count, "rt", cn_pending_updates, fd)
            krt_clear = skip_krt_check != 0 or check_krt_queue_empty(
                rt_self, oper, rt_vpn_prefixes, expected_prefix_count, fd)
            #log_print("DEBUG: prefixes: %s vpn_prefixes %s, expected: %s" %(rt_vpn_prefixes, vpn_prefixes, expected_prefix_count), fd)

            #
            # Get delta times if done - only call this once per test
            #
            if (rt_done == True and krt_clear == True):
                rt_delta_seconds, timestamp_done_rt = get_delta_time(
                    start_time, 'seconds')

        #
        # Timeout if we're spinning..
        #
        time_chk, time_now = get_delta_time(start_time, 'minutes')
        if time_chk >= max_time:
            log_print("ERROR: timeout waiting for route install, total expected prefixes:{0} cn had:{1} cn_pending_updates:{2} rtr had:{3} waited {4} min, expected_prefix_count {5}, rt_done {6}, cn_done {7}, krt_clear {8}".format(
                total_expected_prefixes, cn_prefixes, cn_pending_updates, rt_prefixes, max_time, expected_prefix_count, rt_done, cn_done, krt_clear), fd)
            return_val = 'GetRouteTimeout'
            break

        #
        # Control-node stats for log
        #
        msg1 = "INFO: pfxes:%s pending:%s marker:%s paths:%s primry:%s secondry:%s infeasbl:%s" % (
            cn_prefixes, cn_pending_updates, cn_markers, cn_paths, cn_primary_paths, cn_secondary_paths, cn_infeasible_paths)
        msg_last = "ri:%s op:%s cdone:%s timeout-in:%sm pfx_expected:%s" % (
            ri_name, oper, cn_done, max_time - time_chk, expected_prefix_count)

        #
        # Optionally append router stats for log
        #
        if skip_rtr_check == 0:
            msg1 = "%s rt_vpn:%s rt:%s rdone:%s" % (
                msg1, rt_vpn_prefixes, rt_prefixes, rt_done)

        #
        # Optionally append router krt stats for log
        #
        if skip_krt_check == 0:
            msg1 = "%s krt:%s" % (msg1, krt_clear)

        #
        # Log stats
        #
        log_print("%s %s" % (msg1, msg_last), fd)

        #
        # Check if we reached expected prefix values - use the greater timestamp for
        # overall completion time.
        #
        # Note:
        # - timetamps were already recorded for cn_done (and rt_done if applicable)
        # - this is called after either cn or rt is checked for done status (to keep timings accurate)
        #
        if check_done_flags(cn_done, rt_done, skip_rtr_check, skip_krt_check, krt_clear, oper, timestamp_done_cn, timestamp_done_rt, fd):
            break

        #
        # Wait a bit before continuing
        #
        #log_print ("DEBUG: sleeping for %s seconds inbetween introspect polling for prefix add :%s" % (sleeptime_between_introspect_polls, oper), fd)
        time.sleep(sleeptime_between_introspect_polls)

    # end while loop

    #
    # Unless it's a timeout, report delta time
    #
    if not re.search('timeout', str(return_val), re.IGNORECASE):
        report_delta_times(oper, total_expected_prefixes, cn_delta_seconds,
                           rt_delta_seconds, ninstances, nagents, nroutes, skip_rtr_check, fd)

    return return_val

# end get_prefix_install_or_delete_time


def report_stats(cn_self, rt_self, cnshell_self, cn_ip, rt_ip, msg, report_cpu_only_at_peak_bgp_scale, fd):

    local_ip = get_localhost_ip()
    pid = os.getpid()

    #
    # Beginning stats info
    #
    log_print(" ", fd)
    log_print(
        "============================ <Begin> {0} ===============================".format(msg), fd)
    #
    # Control Node cpu
    #
    result1 = get_shell_cmd_output(
        cnshell_self, 'cat /proc/stat | grep -i cpu', fd)
    result2 = get_shell_cmd_output(cnshell_self, 'top -b | head -15', fd)
    result3 = get_shell_cmd_output(cnshell_self, 'mpstat -P ALL', fd)
    log_print("ip:{0} Control Node CPU info (brief):".format(cn_ip), fd)
    log_print(
        "ip:{0} cat /proc/stat | grep -i cpu\n{1}".format(cn_ip, result1), fd)
    log_print("ip:{0} top -b | head -15\n{1}".format(cn_ip, result2), fd)
    log_print("ip:{0} mpstat -P ALL\n{1}".format(cn_ip, result3), fd)
    log_print(
        "============================ <End> {0} ===============================".format(msg), fd)

    # TODO - reorganize cpu call
    if report_cpu_only_at_peak_bgp_scale:
        return

    #
    # Localhost ulimit settings
    #
    result1 = subprocess.check_output(
        'ulimit -a',  stderr=subprocess.STDOUT, shell=True)
    log_print("ip:{0} Localhost Ulimit Settings:".format(local_ip), fd)
    log_print("ip:{0} ulimit -a \n{1}".format(local_ip, result1), fd)

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
        'pmap {0} | grep -i total'.format(pid), stderr=subprocess.STDOUT, shell=True)
    log_print("ip:{0} Localhost Memory:".format(local_ip), fd)
    log_print(
        'ip:{0} egrep "Mem|Cache|Swap" /proc/meminfo\n{1}'.format(local_ip, mem_result1), fd)
    log_print(
        'ip:{0} ps -e -orss=,args= | sort -b -k1,1n \n{1}'.format(local_ip, mem_result2), fd)
    log_print(
        'ip:{0} ps -e -ovsz=,args= | sort -b -k1,1n \n{1}'.format(local_ip, mem_result3), fd)
    log_print('ip:{0} vmstat\n{1}'.format(local_ip, mem_result4), fd)
    log_print(
        'ip:{0} pmap {1} | grep -i total\n{2}'.format(local_ip, pid, mem_result5), fd)

    #
    # Localhost file descriptprs
    #
    result1 = subprocess.check_output(
        'lsof -n | wc -l', stderr=subprocess.STDOUT, shell=True)
    result2 = subprocess.check_output(
        'lsof -n | grep -i tcp | wc -l', stderr=subprocess.STDOUT, shell=True)
    log_print(
        "ip:{0} Localhost File Descriptors (lsof -n):".format(local_ip), fd)
    log_print("ip:{0} Total fds: {1}".format(local_ip, result1), fd)
    log_print("ip:{0} TCP   fds: {1}".format(local_ip, result2), fd)

    #
    # Localhost cpu
    #
    result1 = subprocess.check_output(
        'cat /proc/stat | grep -i cpu', stderr=subprocess.STDOUT, shell=True)
    result2 = subprocess.check_output(
        'top -b | head -15', stderr=subprocess.STDOUT, shell=True)
    log_print("ip:{0} Localhost CPU info (brief):".format(local_ip), fd)
    log_print("ip:{0} top -b | head -15".format(local_ip), fd)
    log_print(result1, fd)
    log_print("ip:{0} cat /proc/stat | grep -i cpu".format(local_ip), fd)
    log_print(result2, fd)

    if re.search('Before', msg, re.IGNORECASE):
        defs = "Field definitions for /proc/stat, in case you remembered to forget: \n- user: normal processes executing in user mode \n- nice: niced processes executing in user mode \n- system: processes executing in kernel mode \n- idle: twiddling thumbs \n- iowait: waiting for I/O to complete \n- irq: servicing interrupts \n- softirq: servicing softirqs \n- steal: involuntary wait \n- guest: running a normal guest \n- guest_nice: running a niced guest\n"
        log_print(defs, fd)

    #
    # Localhost crash info
    #
    #localhost_crash_info = subprocess.check_output('ls -lt /var/crashes; ls -lt /var/crash', stderr=subprocess.STDOUT, shell=True)
    #log_print ("ip:{0} Localhost Crash info:".format(local_ip), fd)
    #log_print ("ip:{0} ls -lt /var/crashes; ls -lt /var/crash\n{1}".format(cn_ip, localhost_crash_info), fd)

    #
    # Get router RE memory usage info
    #
    if rt_self != None:
        total, used = get_rtr_dram_pct_utlization(rt_self, fd)
        log_print('ip:{0} Router Memory:'.format(rt_ip), fd)
        log_print("ip:{0} DRAM: {1}".format(rt_ip, total), fd)
        log_print(
            "ip:{0} Memory utilization {1} percent".format(rt_ip, used), fd)

    #
    # Control node run command, including env variables
    #
    #result1 = cnshell_self.execCmd ('ps e `pidof control-node.optimized`')
    result1 = cnshell_self.execCmd('ps e `pidof control-node`')
    log_print(
        "ip:{0} Control Node ps info with env variables:".format(cn_ip), fd)
    log_print(
        "ip:{0} ps e `pidof control-node`\n{1}".format(cn_ip, result1), fd)

    #
    # Control node  ulimit settings
    #
    result1 = get_shell_cmd_output(
        cnshell_self, 'cat /proc/`pidof control-node`/limits', fd)
    log_print("ip:{0} Control Node Ulimit Settings:".format(cn_ip), fd)
    log_print(
        "ip:{0} cat /proc/`pidof control-node`/limits\n{1}".format(cn_ip, result1), fd)

    #
    # Control Node memory info
    #
    mem_result1 = get_shell_cmd_output(
        cnshell_self, 'egrep "Mem|Cache|Swap" /proc/meminfo', fd)
    mem_result2 = get_shell_cmd_output(
        cnshell_self, 'ps -e -orss=,args= | sort -b -k1,1n | pr -TW195 | sort -rn | head -n 20', fd)
    mem_result3 = get_shell_cmd_output(
        cnshell_self, 'ps -e -ovsz=,args= | sort -b -k1,1n | pr -TW195 | sort -rn | head -n 20', fd)
    mem_result4 = get_shell_cmd_output(cnshell_self, 'vmstat', fd)
    mem_result5 = get_shell_cmd_output(
        cnshell_self, 'pmap `pidof control-node` | grep -i total', fd)
    log_print('ip:{0} Control Node Memory:'.format(cn_ip), fd)
    log_print(
        'ip:{0} egrep "Mem|Cache|Swap" /proc/meminfo\n{1}'.format(cn_ip, mem_result1), fd)
    log_print(
        'ip:{0} ps -e -orss=,args= | sort -b -k1,1n \n{1}'.format(cn_ip, mem_result2), fd)
    log_print(
        'ip:{0} ps -e -ovsz=,args= | sort -b -k1,1n \n{1}'.format(cn_ip, mem_result3), fd)
    log_print('ip:{0} vmstat\n{1}'.format(cn_ip, mem_result4), fd)
    log_print(
        'ip:{0} pmap `pidof control-node` | grep -i total\n{1}'.format(cn_ip, mem_result5), fd)

    #
    # Control Node file descriptprs
    #
    result1 = get_shell_cmd_output(cnshell_self, 'lsof -n | wc -l', fd)
    result2 = get_shell_cmd_output(
        cnshell_self, 'lsof -n | grep -i tcp | wc -l', fd)
    # result3 = get_shell_cmd_output (cnshell_self, 'lsof -i | wc -l', fd) #
    # can hang system...
    log_print(
        "ip:{0} Control Node File Descriptors (lsof -n):".format(cn_ip), fd)
    log_print("ip:{0} Total fds: {1}".format(cn_ip, result1), fd)
    log_print("ip:{0} TCP   fds: {1}".format(cn_ip, result2), fd)

    result1 = get_shell_cmd_output(cnshell_self, 'netstat -vatn | wc -l', fd)
    log_print(
        'ip:{0} Control Node Open Ports and Established TCP Sessions "netstat -vatn | wc -l"\n{1}'.format(cn_ip, result1), fd)

    #
    # Control Node cpu
    #
    result1 = get_shell_cmd_output(
        cnshell_self, 'cat /proc/stat | grep -i cpu', fd)
    result2 = get_shell_cmd_output(cnshell_self, 'top -b | head -15', fd)
    result3 = get_shell_cmd_output(cnshell_self, 'mpstat -P ALL', fd)
    log_print("ip:{0} Control Node CPU info (brief):".format(cn_ip), fd)
    log_print(
        "ip:{0} cat /proc/stat | grep -i cpu\n{1}".format(cn_ip, result1), fd)
    log_print("ip:{0} top -b | head -15\n{1}".format(cn_ip, result2), fd)
    log_print("ip:{0} mpstat -P ALL\n{1}".format(cn_ip, result3), fd)

    #
    # Control node Crash info
    #
    #cn_crash_info = get_shell_cmd_output (cnshell_self, 'ls -lt /var/crashes; ls -lt /var/crash', fd)
    #log_print ("ip:{0} Localhost Crash info:".format(cn_ip), fd)
    #log_print ("ip:{0} ls -lt /var/crashes; ls -lt /var/crash\n{1}".format(cn_ip, cn_crash_info), fd)

    log_print(
        "============================ {0} <End> =======================".format(msg), fd)
    log_print(" ", fd)

    #
    # Get control node swap info
    #
    result = get_shell_cmd_output(
        cnshell_self, 'egrep "SwapCached" /proc/meminfo', fd)
    swap1 = check_if_swapping(result, "Control node:%s" % cn_ip, fd)

    #
    # Get localhost swap info
    #
    result = subprocess.check_output(
        'egrep "SwapCached" /proc/meminfo', stderr=subprocess.STDOUT, shell=True)
    swap2 = check_if_swapping(
        result, "Localhost:%s running bgp_stress_test code" % local_ip, fd)

    if swap1 or swap2:
        log_print(
            "WARNING: control node swap status:{0}, localhost swap status:{1}".format(swap1, swap2), fd)

    #
    # Check if crashing
    #
    #check_for_crash (localhost_crash_info, "Localhost:%s running bgp_stress_test code" %local_ip, fd)
    #check_for_crash (cn_crash_info, "Control node:%s" %cn_ip, fd)

    return (swap1, swap2)

# end report_stats


def check_if_done_polling_for_prefixes(oper, current_prefixes, expected_prefixes, who, pending_updates, fd):

    return_val = False

    #
    # Check if prefix install is done
    #
    if re.search('add', oper, re.IGNORECASE):
        log_print("INFO: current:%s expected:%s" %
                  (current_prefixes, expected_prefixes), fd)
        if current_prefixes >= expected_prefixes:
            return_val = True
        else:
            return_val = False

    #
    # Check if prefix delete is done
    #
    elif re.search('del', oper, re.IGNORECASE):
        if current_prefixes <= expected_prefixes:
            return_val = True
        else:
            return_val = False

    #
    # Check if pending updates are clear
    #
    if who == 'cn':
        if pending_updates:
            return_val = False
            #log_print ("DEBUG: pending_updates present:%s returning:%s oper:%s who:%s current:%s expected:%s" %(pending_updates, return_val, oper, who, current_prefixes, expected_prefixes), fd)

    #log_print ("DEBUG: check_if_done_polling_for_prefixes: returning:%s oper:%s who:%s current:%s expected:%s pending_updates:%s" %(return_val, oper, who, current_prefixes, expected_prefixes, pending_updates), fd)
    return return_val

# end check_if_done_polling_for_prefixes


def report_delta_times(oper, expected_prefixes, cn_delta_seconds, rt_delta_seconds, ninstances, nagents, nroutes, skip_rtr_check, fd):

    #
    # Compute the number of add/delete per second
    #
    cn_ips = get_ops_per_second(int(cn_delta_seconds), expected_prefixes)
    rt_ips = get_ops_per_second(int(rt_delta_seconds), expected_prefixes)
    tunit = 'seconds'

    msg = get_msg_ninst_x_agents_x_nroutes(ninstances, nagents, nroutes)
    if skip_rtr_check != 0:
        log_print(
            "INFO:    Elapsed time to {0} {1} prefixes on_control_node:{2}{6} prefixes/{6}:{4} {7}".format(oper,
                                                                                                           expected_prefixes, cn_delta_seconds, rt_delta_seconds, cn_ips, rt_ips, tunit[:1], msg), fd)
    else:
        log_print(
            "INFO:    Elapsed time to {0} {1} prefixes on_control_node:{2}{6}, and on_router:{3}{6} prefixes/{6}: ({4} and {5}) {7}".format(oper,
                                                                                                                                            expected_prefixes, cn_delta_seconds, rt_delta_seconds, cn_ips, rt_ips, tunit[:1], msg), fd)

    return

# end report_delta_times


def get_msg_ninst_x_agents_x_nroutes(ninstances, nagents, nroutes):

    return "ninst X nagent X nroutes = {0}x{1}x{2}".format(ninstances, nagents, nroutes)

# end get_msg_ninst_x_agents_x_nroutes


def get_ops_per_second(delta_seconds, expected_prefixes):

    #
    # Compute prefix install (or delete) per second
    #
    if delta_seconds > 0:
        return_val = expected_prefixes / delta_seconds
        return return_val
    else:
        return expected_prefixes

# end get_ops_per_second


def get_delta_time(t1, units=''):

    t2 = datetime.now()

    #
    # Use direct time diff
    #
    if not units:
        return_val = (t2 - t1)

    #
    # The has GOT to be a better way..
    #
    if units == 'minutes':
        return_val = int(((t2 - t1).seconds) / 60)

    elif units == 'seconds':
        return_val = (t2 - t1).seconds

    elif units == 'microseconds':
        return_val = "%s.%s" % (
            int(((t2 - t1).seconds) / 60), ((t2 - t1).microseconds))

    return (return_val, t2)

# end get_delta_time


def utc_to_tz(ut, time_zone=''):

    #
    # Check if we have a valid timestamp..
    #
    try:
        new_utc = datetime.strptime(ut, '%Y-%b-%d %H:%M:%S.%f')
    except ValueError:
        return 'InvalidDateFormat'

    #
    # Default to PST (if no timezone param)
    #
    if not time_zone:
        time_zone = 'US/Pacific'

    #
    # Convert string to datetime format (introspect returns string format..)
    #
    if type(ut) is str:
        # Using the format introspect returns
        new_utc = datetime.strptime(ut, '%Y-%b-%d %H:%M:%S.%f')

    #
    # Attach utc timezone
    #
    new_utc = new_utc.replace(tzinfo=pytz.utc)

    #
    # Convert timezone, use format: %Y-%m-%d %H:%M:%S.%f ex: 2013-06-01 18:53:30.308432
    #
    new_tz = timezone(time_zone)
    new_time = new_tz.normalize(
        d.astimezone(new_tz)).strftime('%Y-%b-%d %H:%M:%S.%f')

    #
    # Convert back to type "datetime"
    #
    new_time = datetime.strptime(new_time, '%Y-%b-%d %H:%M:%S.%f')

    return new_time

# end utc_to_tz


def set_tcp_keepalives(who, fd, self=''):
    ''' NOT USEED
       Set tcp values low so that if bgp_stress gets killed, the xmpp session go down
       sysctl -w net.ipv4.tcp_keepalive_time=30 net.ipv4.tcp_keepalive_probes=3 net.ipv4.tcp_keepalive_intvl=3
       old defail vales:
       net.ipv4.tcp_keepalive_intvl = 75
       net.ipv4.tcp_keepalive_probes = 9
       net.ipv4.tcp_keepalive_time = 7200
    '''

    #
    # Command to set tcp session timeout lower
    #
    cmd = "sysctl -w net.ipv4.tcp_keepalive_intvl=75 net.ipv4.tcp_keepalive_probes=9 net.ipv4.tcp_keepalive_time=7200"
    cmd = "sysctl -w net.ipv4.tcp_keepalive_intvl=3 net.ipv4.tcp_keepalive_probes=3 net.ipv4.tcp_keepalive_time=30"

    if (who == 'localhost'):
        #
        # Instantiate command on localhost
        #
        result = subprocess.check_output(
            cmd, stderr=subprocess.STDOUT, shell=True)
    else:
        #
        # Instantiate command on remote node
        #
        result = get_shell_cmd_output(self, cmd, fd)

    log_print("INFO: Executing command on:%s cmd:%s" % (who, cmd), fd)

    return result

# end set_tcp_keepalives


def main():
    local_server = get_localhost_ip()

if __name__ == '__bgp_scale_mock_agent__':
    try:
        bgp_scale_mock_agent()
    except Exception, msg:
        # print traceback.format_exc()
        log_print("WARNING: Hit exception in bgp.py after main..", fd)
    finally:
        if BGP_STRESS:
            kill_bgp_stress_python_call('bgp_stress_test', 'python', fd)
            BGP_STRESS.stop()
