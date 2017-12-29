# utils to start and stop tcpdump on VM
from time import sleep
from common import log_orig as contrail_logging

from util import retry
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
from tcutils.util import get_random_name

def start_tcpdump_for_intf(ip, username, password, interface, filters='-v', logger=None):
    if not logger:
        logger = contrail_logging.getLogger(__name__)
    session = ssh(ip, username, password)
    pcap = '/tmp/%s_%s.pcap' % (interface, get_random_name())
    cmd = 'sudo tcpdump -nni %s -U %s -w %s' % (interface, filters, pcap)
    execute_cmd(session, cmd, logger)
    return (session, pcap)

def stop_tcpdump_for_intf(session, pcap, logger=None):
    if not logger:
        logger = contrail_logging.getLogger(__name__)
    cmd = 'sudo kill $(ps -ef|grep tcpdump | grep pcap| awk \'{print $2}\')'
    execute_cmd(session, cmd, logger)
    sleep(2)
    return True

def start_tcpdump_for_vm_intf(obj, vm_fix, vn_fq_name, filters='-v', pcap_on_vm=False, vm_intf='eth0', svm=False):
    if not pcap_on_vm:
        compute_ip = vm_fix.vm_node_ip
        compute_user = obj.inputs.host_data[compute_ip]['username']
        compute_password = obj.inputs.host_data[compute_ip]['password']
        vm_tapintf = obj.orch.get_vm_tap_interface(vm_fix.tap_intf[vn_fq_name])
        return start_tcpdump_for_intf(compute_ip, compute_user,
            compute_password, vm_tapintf, filters, logger=obj.logger)
    else:
        pcap = '/tmp/%s.pcap' % (get_random_name())
        tcpdump_cmd = 'tcpdump -ni %s -U %s -w %s 1>/dev/null 2>/dev/null'
        if svm:
            tcpdump_cmd = '/usr/local/sbin/' + tcpdump_cmd
        cmd_to_tcpdump = [ 'sudo ' + tcpdump_cmd % (vm_intf, filters, pcap) ]
        pidfile = pcap + '.pid'
        vm_fix_pcap_pid_files =[]
        for vm_fixture in vm_fix:
            vm_fixture.run_cmd_on_vm(cmds=cmd_to_tcpdump, as_daemon=True, pidfile=pidfile, as_sudo=True)
            vm_fix_pcap_pid_files.append((vm_fixture, pcap, pidfile))
        return vm_fix_pcap_pid_files
# end start_tcpdump_for_vm_intf

def stop_tcpdump_for_vm_intf(obj, session, pcap, vm_fix_pcap_pid_files=[], filters='', verify_on_all=False, svm=False):
    if not vm_fix_pcap_pid_files:
        return stop_tcpdump_for_intf(session, pcap, logger=obj.logger)
    else:
        output = []
        pkt_count = []
        for vm_fix, pcap, pidfile in vm_fix_pcap_pid_files:
            tcpdump_cmd = 'tcpdump -nr %s %s'
            if svm:
                tcpdump_cmd = '/usr/local/sbin/' + tcpdump_cmd
            cmd_to_output  = 'sudo ' + tcpdump_cmd % (pcap, filters)
            cmd_to_kill = 'sudo cat %s | xargs kill ' % (pidfile)
            count = cmd_to_output + '| wc -l'
            if svm:
                cmd_to_kill = 'sudo kill -9 $(sudo cat ' + pidfile + ')'
            vm_fix.run_cmd_on_vm(cmds=[cmd_to_kill], as_sudo=True)
            vm_fix.run_cmd_on_vm(cmds=[cmd_to_output], as_sudo=True)
            output.append(vm_fix.return_output_cmd_dict[cmd_to_output])
            if not svm:
                vm_fix.run_cmd_on_vm(cmds=[count], as_sudo=True)
            else:
                count = 'sudo ' + count
                vm_fix.run_cmd_on_vm(cmds=[count])
            pkt_list = vm_fix.return_output_cmd_dict[count].split('\n')
            pkts = int(pkt_list[len(pkt_list)-1])
            pkt_count.append(pkts)
            total_pkts = sum(pkt_count)
        if not verify_on_all:
            return output, total_pkts
        else:
            return output, pkt_count

# end stop_tcpdump_for_vm_intf

def pcap_on_all_vms_and_verify_mirrored_traffic(
    self, src_vm_fix, dst_vm_fix, svm_fixtures, count=1, filt='', tap='eth0', expectation=True, verify_on_all=False):
        vm_fix_pcap_pid_files = self.start_tcpdump(None, tap_intf=tap, vm_fixtures= svm_fixtures, pcap_on_vm=True)
        assert src_vm_fix.ping_with_certainty(
            dst_vm_fix.vm_ip, expectation=expectation)
        output, total_pkts = self.stop_tcpdump(
            None, pcap=tap, filt=filt, vm_fix_pcap_pid_files=vm_fix_pcap_pid_files, pcap_on_vm=True, verify_on_all=verify_on_all)
        if not verify_on_all:
            if count > total_pkts:
                errmsg = "%s ICMP Packets mirrored to the analyzer VM,"\
                    "Expected %s packets, tcpdump on VM" % (
                    total_pkts, count)
                self.logger.error(errmsg)
                assert False, errmsg
            else:
                self.logger.info("Mirroring verified using tcpdump on the VM, Expected = Mirrored = %s " % (total_pkts))
        else:
            for pkts in total_pkts:
                if not pkts > 0:
                    errmsg = "%s ICMP Packets not mirrored to the analyzer VM,"\
                    "Expected not zero packets, tcpdump on VM"
                    self.logger.error(errmsg)
                    assert False, errmsg
            self.logger.info(
                "Mirroring verified using tcpdump on the VM, Total pkts mirrored = %s on all the VMs" % (total_pkts))
        return True
# end pcap_on_all_vms_and_verify_mirrored_traffic

def read_tcpdump(obj, session, pcap):
    cmd = 'sudo tcpdump -n -r %s' % pcap
    out, err = execute_cmd_out(session, cmd, obj.logger)
    return out

@retry(delay=2, tries=6)
def verify_tcpdump_count(obj, session, pcap, exp_count=None, mac=None,
        exact_match=True, vm_fix_pcap_pid_files=[], svm=False, grep_string=None):

    grep_string = grep_string or 'length'
    if mac:
        cmd = 'sudo tcpdump -nnr %s ether host %s | grep -c %s' % (pcap, mac, grep_string)
    else:
        cmd = 'sudo tcpdump -nnr %s | grep -c %s' % (pcap, grep_string)
    if not vm_fix_pcap_pid_files:
        out, err = execute_cmd_out(session, cmd, obj.logger)
        count = int(out.strip('\n'))
    else:
        output, count = stop_tcpdump_for_vm_intf(
            None, None, pcap, vm_fix_pcap_pid_files=vm_fix_pcap_pid_files, svm=svm)
    result = True
    if exp_count is not None:
        if count != exp_count and exact_match:
            obj.logger.warn("%s packets are found in tcpdump output file %s but \
                                        expected %s" % (count, pcap, exp_count))
            result = False
        elif count > exp_count and not exact_match:
            obj.logger.debug("%s packets are found in tcpdump output file %s but \
                             expected %s, which is fine" % (count, pcap, exp_count))
        elif count < exp_count and not exact_match:
            obj.logger.warn("%s packets are found in tcpdump output file %s but \
                             expected atleast %s" % (count, pcap, exp_count))
            result = False
    else:
        if count == 0:
            obj.logger.warn("No packets are found in tcpdump output file %s but \
                                        expected some packets" % (pcap))
            result = False

    if result:
        obj.logger.info(
            "%s packets are found in tcpdump output as expected",
            count)
        stop_tcpdump_for_vm_intf(obj, session, pcap)
    return result

def search_in_pcap(session, pcap, search_string):
    cmd = 'sudo tcpdump -v -r %s | grep "%s"' % (pcap, search_string)
    out, err = execute_cmd_out(session, cmd)
    if search_string in out:
        return True
    else:
        return False
# end search_in_pcap

def delete_pcap(session, pcap):
    execute_cmd_out(session, 'rm -f %s' % (pcap))

@retry(delay=2, tries=15)
def check_pcap_file_exists(session, pcap, expect=True):
    cmd = 'ls -d /tmp/* | grep -w %s ' % (pcap)
    out, err = execute_cmd_out(session, cmd)
    out = bool(out)
    if expect and out or not expect and not out:
        return True
    return False


