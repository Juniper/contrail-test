# utils to start and stop tcpdump on VM
import vm_test
from util import retry
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
from tcutils.util import get_random_name


def start_tcpdump_for_vm_intf(obj, vm_fix, vn_fq_name, filters='-v'):
    compute_ip = vm_fix.vm_node_ip
    compute_user = obj.inputs.host_data[compute_ip]['username']
    compute_password = obj.inputs.host_data[compute_ip]['password']
    session = ssh(compute_ip, compute_user, compute_password)
    vm_tapintf = vm_fix.tap_intf[vn_fq_name]['name']
    pcap = '/tmp/%s_%s.pcap' % (vm_tapintf, get_random_name())
    cmd = 'tcpdump -ni %s -U %s -w %s' % (vm_tapintf, filters, pcap)
    execute_cmd(session, cmd, obj.logger)

    return (session, pcap)

def stop_tcpdump_for_vm_intf(obj, session, pcap):
    cmd = 'rm -f %s' % pcap
    execute_cmd(session, cmd, obj.logger)
    cmd = 'kill $(ps -ef|grep tcpdump | grep pcap| awk \'{print $2}\')'
    execute_cmd(session, cmd, obj.logger)
    return True
    

@retry(delay=2, tries=6)
def verify_tcpdump_count(obj, session, pcap, exp_count=None):

    cmd = 'tcpdump -r %s | wc -l' % pcap
    out, err = execute_cmd_out(session, cmd, obj.logger)
    count = int(out.strip('\n'))
    result = True 
    if exp_count is not None:
        if count != exp_count:
            obj.logger.warn("%s packets are found in tcpdump output file %s but \
                                        expected %s" % (count, pcap, exp_count))
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
