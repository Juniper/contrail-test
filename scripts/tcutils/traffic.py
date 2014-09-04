#utils for start and stop traffic on VM
import vm_test
from util import retry
from tcutils.commands import ssh, execute_cmd, execute_cmd_out


def start_traffic_pktgen(obj, vm_fix, src_min_ip='', src_max_ip='', dest_ip='', dest_min_port='', dest_max_port=''):
    """ This routine is for generation of UDP flows using pktgen. Only UDP packets are generated using this routine.
    """
    obj.logger.info("Sending traffic...")
    try:
	cmd = '~/pktgen_new.sh %s %s %s %s %s' % (src_min_ip,
                                                           src_max_ip, dest_ip, dest_min_port, dest_max_port)
        vm_fix.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
    except Exception as e:
        obj.logger.exception("Got exception at start_traffic as %s" % (e))
# end start_traffic

def stop_traffic_pktgen(obj, vm_fix):
    obj.logger.info("Stopping traffic...")
    try:
        cmd = 'killall ~/pktgen_new.sh'
        vm_fix.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
    except Exception as e:
        obj.logger.exception("Got exception at stop_traffic as %s" % (e))

def start_traffic_pktgen_between_vm(obj, sr_vm_fix, dst_vm_fix, dest_min_port=10000, dest_max_port=10000):
    """This method starts traffic between VMs using pktgen"""

    start_traffic_pktgen(obj, sr_vm_fix, src_min_ip = sr_vm_fix.vm_ip, src_max_ip = sr_vm_fix.vm_ip,
				dest_ip=dst_vm_fix.vm_ip, dest_min_port=dest_min_port,
				dest_max_port = dest_max_port)

def start_tcpdump_on_vm(obj, vm_fix, vn_fix, filters='-v'): 
    compute_ip = vm_fix.vm_node_ip
    compute_user = obj.inputs.host_data[compute_ip]['username']
    compute_password = obj.inputs.host_data[compute_ip]['password']
    session = ssh(compute_ip, compute_user, compute_password)
    vm_tapintf = vm_fix.tap_intf[vn_fix.vn_fq_name]['name']
    pcap = '/tmp/%s.pcap' % vm_tapintf 
    cmd = 'tcpdump -ni %s %s -w %s' % (vm_tapintf, filters, pcap)
    execute_cmd(session, cmd, obj.logger)

    return (session, pcap)

@retry(delay=2, tries=2)
def stop_tcpdump_on_vm_verify_cnt(obj, session, pcap, exp_count=None):

    cmd = 'tcpdump -r %s | wc -l' % pcap
    out, err = execute_cmd_out(session, cmd, obj.logger)
    count = int(out.strip('\n'))
    if exp_count and count != exp_count:
	obj.logger.warn("%s packets are found in tcpdump output but expected %s" % (count, exp_count))	
	return False
    elif count == 0:
        obj.logger.warn("No packets are found in tcpdump output but expected something")
        return False

    obj.logger.info("%s packets are found in tcpdump output", count)
    cmd = 'rm -f %s' % pcap
    execute_cmd(session, cmd, obj.logger)
    cmd = 'kill $(pidof tcpdump)'
    execute_cmd(session, cmd, obj.logger)
    return True 

