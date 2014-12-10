#utils to start and stop traffic on VM
import vm_test
from util import retry
from tcutils.commands import ssh, execute_cmd, execute_cmd_out


def start_traffic_pktgen(
        vm_fix,
        src_min_ip='',
        src_max_ip='',
        dest_ip='',
        dest_min_port='',
        dest_max_port=''):
    """ This routine is for generation of UDP flows using pktgen. Only UDP packets are generated using this routine.
    """
    vm_fix.logger.info("Sending traffic...")
    try:
        cmd = '~/pktgen_new.sh %s %s %s %s %s' % (src_min_ip,
                                                  src_max_ip,
                                                  dest_ip,
                                                  dest_min_port,
                                                  dest_max_port)
        vm_fix.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
    except Exception as e:
        vm_fix.logger.exception("Got exception at start_traffic as %s" % (e))
# end start_traffic


def stop_traffic_pktgen(vm_fix):
    vm_fix.logger.info("Stopping traffic...")
    try:
        cmd = 'killall ~/pktgen_new.sh'
        vm_fix.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
    except Exception as e:
        vm_fix.logger.exception("Got exception at stop_traffic as %s" % (e))


def start_traffic_pktgen_between_vm(
        sr_vm_fix,
        dst_vm_fix,
        dest_min_port=10000,
        dest_max_port=10000):
    """This method starts traffic between VMs using pktgen"""

    start_traffic_pktgen(
        sr_vm_fix,
        src_min_ip=sr_vm_fix.vm_ip,
        src_max_ip=sr_vm_fix.vm_ip,
        dest_ip=dst_vm_fix.vm_ip,
        dest_min_port=dest_min_port,
        dest_max_port=dest_max_port)
