from tcutils.topo.sdn_topo_setup import *
from tcutils.test_lib.test_utils import assertEqual, get_ip_list_from_prefix
from common.policy.get_version import get_OS_Release_BuildVersion


# get source min, max ip's and destination max port.
def src_min_max_ip_and_dst_max_port(
        ips,
        no_of_ip,
        dst_min_port,
        flows):
    """ Called by test_flow_single_project or test_system_flow_multi_project to
        get the min source ip, max source ip and Max port number of the
        destination. This helps to create certain no of flows as expected by
        test_flow_single_project or test_system_flow_multi_project routines,
        from where it is called.
    """
    ip_list = list()
    for index in range(no_of_ip):
        ip_list.append(ips[index])
    src_min_ip = ip_list[0]
    src_max_ip = ip_list[-1]
    dst_max_port = dst_min_port + (flows / no_of_ip)
    result_dict = {'src_min_ip': src_min_ip, 'src_max_ip':
                   src_max_ip, 'dst_max_port': dst_max_port}
    return result_dict
# end src_min_max_ip_and_dst_max_port


def create_traffic_profiles(topo_obj, config_topo):

    # Create traffic based on traffic profile defined in topology.
    traffic_profiles = {}
    count = 0
    num_ports_per_ip = 50000.00
    # forward flows = (total no. of flows / 2), so fwd_flow_factor = 2
    fwd_flow_factor = 2
    for profile, data in topo_obj.traffic_profile.items():
        src_min_ip = 0
        src_max_ip = 0
        dst_ip = 0
        pkt_cnt = 0
        dst_min_port = 5000
        dst_max_port = 55000
        count += 1
        #profile = 'profile' + str(count)
        src_vm = data['src_vm']
        src_vm_obj = None
        dst_vm_obj = None
        pkt_cnt = data['num_pkts']
        for proj in config_topo:
            for vm in config_topo[proj]:
                for vm_name in config_topo[proj][vm]:
                    if data['dst_vm'] == vm_name:
                        dst_ip = config_topo[proj][vm][vm_name].vm_ip
                        dst_vm_obj = config_topo[proj][vm][vm_name]
                    if src_vm == vm_name:
                        src_vm_obj = config_topo[proj][vm][vm_name]

        prefix = topo_obj.vm_static_route_master[src_vm]
        ip_list = get_ip_list_from_prefix(prefix)
        no_of_ip = int(
            math.ceil(
                (data['num_flows'] /
                 fwd_flow_factor) /
                num_ports_per_ip))
        forward_flows = data['num_flows'] / fwd_flow_factor
        result_dict = src_min_max_ip_and_dst_max_port(
            ip_list, no_of_ip, dst_min_port, forward_flows)
        if int(no_of_ip) == 1:
            # Use the src VM IP to create the flows no need of static IP's
            # that have been provisioned to the VM route table.
            traffic_profiles[profile] = [src_vm_obj,
                                         src_vm_obj.vm_ip,  # src_ip_min
                                         src_vm_obj.vm_ip,  # src_ip_max
                                         dst_ip,  # dest_vm_ip
                                         dst_min_port,  # dest_port_min
                                         # dest_port_max
                                         result_dict['dst_max_port'],
                                         data['num_pkts'], dst_vm_obj]
        else:
            # Use thestatic IP's that have been provisioned to the VM route
            # table as src IP range.
            traffic_profiles[profile] = [src_vm_obj,
                                         # src_ip_min
                                         result_dict['src_min_ip'],
                                         # src_ip_max
                                         result_dict['src_max_ip'],
                                         dst_ip,  # dest_vm_ip
                                         dst_min_port,  # dest_port_min
                                         # dest_port_max
                                         result_dict['dst_max_port'],
                                         data['num_pkts'], dst_vm_obj]
    return traffic_profiles

# end create_traffic_profiles


def config_topo_single_proj(class_instance,
                            topology_class_name,
                            create_traffic_profile=True):
    """Initialize and Setup configurations for single project related flow
       system tests.
    """
    #self.agent_objs = {}
    # self.set_flow_tear_time()
    #
    # Check if there are enough nodes i.e. atleast 2 compute nodes to run this
    # test.
    # else report that minimum 2 compute nodes are needed for this test and
    # exit.
    # if len(self.inputs.compute_ips) < 2:
    if len(class_instance.inputs.compute_ips) < 2:
        class_instance.logger.warn(
            "Minimum 2 compute nodes are needed for this test to run")
        class_instance.logger.warn(
            "Exiting since this test can't be run on single compute node")
        return True
    #
    # Get config for test from topology
    #topology_class_name = system_test_topo.SystestTopoSingleProject
    # For testing script, use mini topology
    # topology_class_name =
    # mini_system_test_topo.SystestTopoSingleProject
    class_instance.logger.info(
        "Scenario for the test used is: %s" %
        (str(topology_class_name)))

    topo = topology_class_name(
        compute_node_list=class_instance.inputs.compute_ips)
    #
    # Test setup: Configure policy, VN, & VM
    # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
    # Returned topo is of following format:
    # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm':
    # vm_fixture}
    setup_obj = class_instance.useFixture(
        class_instance(),
        sdnTopoSetupFixture(
            class_instance.connections,
            topo))
    out = setup_obj.sdn_topo_setup()
    assertEqual(out['result'], True, out['msg'])
    if out['result']:
        topo, config_topo = out['data'][0], out['data'][1]
    proj = list(topo.keys())[0]

    # Get the vrouter build version for logging purposes.
    class_instance.BuildTag = get_OS_Release_BuildVersion(class_instance)

    # Create traffic profile with all details like IP addresses, port
    # numbers and no of flows, from the profile defined in the topology.
    if create_traffic_profile:
        class_instance.traffic_profiles = create_traffic_profiles(
            topo[proj],
            config_topo)

    class_instance.topo, class_instance.config_topo = topo, config_topo
    class_instance.config_setup_obj = setup_obj

# end config_topo_single_proj
