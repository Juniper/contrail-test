# utils to start and stop tcpdump on VM
import vm_test
from util import retry
from tcutils.commands import ssh, execute_cmd, execute_cmd_out


def start_tcpdump_on_vm(obj, vm_fix, vn_fix, filters='-v'):
    compute_ip = vm_fix.vm_node_ip
    compute_user = obj.inputs.host_data[compute_ip]['username']
    compute_password = obj.inputs.host_data[compute_ip]['password']
    session = ssh(compute_ip, compute_user, compute_password)
    vm_tapintf = vm_fix.tap_intf[vn_fix.vn_fq_name]['name']
    pcap = '/tmp/%s.pcap' % vm_tapintf
    cmd = 'tcpdump -ni %s -U %s -w %s' % (vm_tapintf, filters, pcap)
    execute_cmd(session, cmd, obj.logger)

    return (session, pcap)


@retry(delay=2, tries=6)
def stop_tcpdump_on_vm_verify_cnt(obj, session, pcap, exp_count=None):

    cmd = 'tcpdump -r %s | wc -l' % pcap
    out, err = execute_cmd_out(session, cmd, obj.logger)
    count = int(out.strip('\n'))
    if exp_count is not None:
        if count != exp_count:
            obj.logger.warn("%s packets are found in tcpdump output file %s but \
                                        expected %s" % (count, pcap, exp_count))
            return False
    else:
        if count == 0:
            obj.logger.warn("No packets are found in tcpdump output file %s but \
                                        expected some packets" % (pcap))
            return False

    obj.logger.info(
        "%s packets are found in tcpdump output as expected",
        count)
    cmd = 'rm -f %s' % pcap
    execute_cmd(session, cmd, obj.logger)
    cmd = 'kill $(pidof tcpdump)'
    execute_cmd(session, cmd, obj.logger)
    return True
