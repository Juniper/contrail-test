import time


def start_all_control_services(self):
    """ Start all the control services running in the topology.
    """
    for ip in self.inputs.bgp_ips:
        self.inputs.start_service('contrail-control', [ip],
                              container='control')
        time.sleep(60)
# end stop_all_control_services


def stop_all_control_services(self):
    """ Stop all the control services running in the topology.
    """
    for ip in self.inputs.bgp_ips:
        self.inputs.stop_service('contrail-control', [ip],
                             container='control')
        time.sleep(60)
# end stop_all_control_services


def check_through_tcpdump(self, dest_vm, src_vm):
    """ Check that the traffic is alive through tcpdump.
    """
    try:
        cmd = "tcpdump -i eth0 -c 3 -n src host %s | grep '%s'" % (
            src_vm.vm_ip, dest_vm.vm_ip)
        response = dest_vm.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
        if '3 packets received by filter' in response[cmd]:
            self.logger.info("Ping traffic is stable and continued.")
    except Exception as e:
        self.logger.exception(
            "Got exception at check_through_tcpdump as %s" %
            (e))
# end check_through_tcpdump


def get_flow_index_list(self, src_vm, dest_vm):
    """ Get all the flow index numbers of the flows created.
    """
    try:
        cmd = "flow --match %s,%s | awk '{print $1}' | grep '<=>'  |  head -n 1" % (
                 src_vm.vm_ip,dest_vm.vm_ip)
        result = self.inputs.run_cmd_on_server(
            src_vm.vm_node_ip, cmd, self.inputs.host_data[
                src_vm.vm_node_ip]['username'], self.inputs.host_data[
                src_vm.vm_node_ip]['password'],container='agent')
        result.split('\r\n')
        output = result.replace('<=>',' ').split(' ')
        output = [_f for _f in output if _f] 
    except Exception as e:
        self.logger.exception(
            "Got exception at get_flow_index_list as %s" %
            (e))
    return output
# end get_flow_index_list

