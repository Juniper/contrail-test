import time


def start_all_control_services(self):
    """ Start all the control services running in the topology.
    """
    self.inputs.start_service('supervisor-control', self.inputs.bgp_ips)
    time.sleep(5)
# end stop_all_control_services


def stop_all_control_services(self):
    """ Stop all the control services running in the topology.
    """
    self.inputs.stop_service('supervisor-control', self.inputs.bgp_ips)
    time.sleep(5)
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
        cmd = "flow -l | grep '%s' | grep '%s' | grep '^ [0-9]\|^[0-9]' | awk '{print $1}'" % (
            src_vm.vm_ip, dest_vm.vm_ip)
        output = self.inputs.run_cmd_on_server(
            src_vm.vm_node_ip, cmd, self.inputs.host_data[
                src_vm.vm_node_ip]['username'], self.inputs.host_data[
                src_vm.vm_node_ip]['password'])

    except Exception as e:
        self.logger.exception(
            "Got exception at get_flow_index_list as %s" %
            (e))
    output = output.split('\r\n')
    return output
# end get_flow_index_list

