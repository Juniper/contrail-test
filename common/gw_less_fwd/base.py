import vnc_api_test
from vnc_api.vnc_api import *
import random
import socket
import time
from netaddr import *
from tcutils.util import retry, get_random_mac
from tcutils.tcpdump_utils import *
from fabric.api import run

from floating_ip import *
from contrailapi import ContrailVncApi
from common.base import GenericTestBase
from common.vrouter.base import BaseVrouterTest
from common.servicechain.config import ConfigSvcChain
from fabric.context_managers import settings, hide
from tcutils.util import safe_run, safe_sudo
from tcutils.commands import ssh, execute_cmd, execute_cmd_out

class GWLessFWDTestBase(BaseVrouterTest, ConfigSvcChain):

    @classmethod
    def setUpClass(cls):
        super(GWLessFWDTestBase, cls).setUpClass()
        cls.vnc_lib_fixture = cls.connections.vnc_lib_fixture
        cls.vnc_h = cls.vnc_lib_fixture.vnc_h

    def get_ip_fab_vn(self):
        '''Get IP fabric provider network
        '''
        ip_fab_vn_fq_name_str = "default-domain:default-project:ip-fabric"
        ip_fab_vn_obj = self.vnc_h.virtual_network_read(fq_name_str=
                                                        ip_fab_vn_fq_name_str)
        return ip_fab_vn_obj

    def disable_policy_on_vhost0(self, value=True):
        '''Enable/Disable policy on vhost0 interfaces
        '''
        for compute_name in self.inputs.compute_names:
            vhost0_fq_name_str = "default-global-system-config:"+compute_name+":vhost0"
            if value:
                self.logger.info('Disabling Policy on vhost0 VMI: %s' %
                                 vhost0_fq_name_str)
            else:
                self.logger.info('Enabling Policy on vhost0: %s' %
                                 vhost0_fq_name_str)

            vhost_vmi_obj = self.vnc_h.virtual_machine_interface_read(fq_name_str=
                                                        vhost0_fq_name_str)
            vhost_vmi_obj.set_virtual_machine_interface_disable_policy(bool(value))
            self.vnc_h.virtual_machine_interface_update(vhost_vmi_obj)
        return True


    def setup_ipam(self, ipam=None):
        '''Configures flat-subnet ipam with subnet and allocation pools
            Input ipam looks like:
            ipam = {'count': 1,
                   'ipam1':{'ipam_type': 'dhcp',
                           'subnet_method': 'flat-subnet',
                           'subnet': {
                                'ip_prefix': '10.204.218.0',
                                'len': 24
                            },
                           'allocation_pool': {
                                    'start': '10.204.218.150',
                                    'end': '10.204.218.160',
                            },
                           },
                    }
        '''

        ipam_count = ipam.get('count', 0)
        for i in range(0,ipam_count):
            ipam_id = 'ipam'+str(i+1)
            ipam = ipam.get(ipam_id, None)
            self.logger.info('Configuring Ipam: %s' % ipam)

            ipam_type = ipam.get('ipam_type', 'dhcp')
            ipam_sn_method = ipam.get('subnet_method', 'flat-subnet')
            ipam_sn = ipam.get('subnet', None)
            ipam_sn_ip = ipam_sn.get('ip_prefix', None)
            ipam_sn_len= ipam_sn.get('len', None)

            ipam_alloc_pool = ipam.get('allocation_pool', None)
            ipam_alloc_pool_start = ipam_alloc_pool.get('start',None)
            ipam_alloc_pool_end = ipam_alloc_pool.get('end',None)

            # declare ipam
            ipam = NetworkIpam(ipam_id, self.project.project_obj, IpamType(ipam_type),
                                        ipam_subnet_method=ipam_sn_method)
            # create ipams
            self.vnc_h.network_ipam_create(ipam)
            ipam_obj = self.vnc_h.network_ipam_read(id=ipam.uuid)
            sn_pool_list = []
            sn_pool_list.append(AllocationPoolType(start=ipam_alloc_pool_start,
                                                    end=ipam_alloc_pool_end))
            ipam_sn = IpamSubnetType(subnet=SubnetType(ipam_sn_ip, ipam_sn_len),
                                    allocation_pools=sn_pool_list,
                                    alloc_unit=1)

            # add subnet to ipam
            ipam.set_ipam_subnets(IpamSubnets([ipam_sn]))
            self.vnc_h.network_ipam_update(ipam)
            ipam_obj = self.vnc_h.network_ipam_read(id=ipam.uuid)
            self.addCleanup(self.delete_ipam, ipam_obj)

            return ipam_obj

    def delete_ipam(self, ipam_obj):
        '''Cleanup Ipam
        '''
        self.logger.info('Deleting Ipam %s' % (ipam_obj.fq_name))
        self.vnc_h.network_ipam_delete(ipam_obj.fq_name)
        self.vnc_h.network_ipam_update(ipam_obj)

    def detach_policy_ip_fabric_vn(self, ip_fab_vn_obj, policy_obj):
        '''Cleanup Ipam
        '''
        self.logger.info('Detaching policy %s on VN: %s' % (
            policy_obj.get_fq_name_str(), ip_fab_vn_obj.get_fq_name_str()))
        ip_fab_vn_obj.del_network_policy(policy_obj)
        self.vnc_h.virtual_network_update(ip_fab_vn_obj)

    def setup_vns(self, vn=None):
        '''Setup VN
           Input vn format:
                vn = {'count':1,
                    'vn1':{'subnet':'10.10.10.0/24', 'ip_fabric':True,},
                    }

                vn = {'count':1,
                       'vn1':{
                            'address_allocation_mode':'flat-subnet-only',
                            'ip_fabric':True,
                            'ipam_fq_name': 'default-domain:default-project:ipam0'
                          },
                    }
        '''
        vn_count = vn['count'] if vn else 0
        vn_fixtures = {} # Hash to store VN fixtures
        for i in range(0,vn_count):
            vn_id = 'vn'+str(i+1)
            if vn_id in vn:
                address_allocation_mode = vn[vn_id].get(
                    'address_allocation_mode', 'user-defined-subnet-only')
                if address_allocation_mode == "flat-subnet-only":
                    ipam_fq_name = vn[vn_id].get('ipam_fq_name', None)
                    vn_fixture = self.create_vn(
                        vn_name=vn_id,
                        address_allocation_mode = address_allocation_mode,
                        forwarding_mode ="l3",
                       ipam_fq_name = ipam_fq_name, option='contrail')

                else:
                    vn_subnet = vn[vn_id].get('subnet',None)
                    vn_fixture = self.create_vn(vn_name=vn_id,
                                                vn_subnets=[vn_subnet])

                ip_fabric = vn[vn_id].get('ip_fabric',False)
                if ip_fabric:
                    ip_fab_vn_obj = self.get_ip_fab_vn()
                    assert vn_fixture.set_ip_fabric_provider_nw(ip_fab_vn_obj)
            else:
                vn_fixture = self.create_vn(vn_name=vn_id)
            vn_fixtures[vn_id] = vn_fixture

        return vn_fixtures

    def setup_vmis(self, vn_fixtures, vmi=None):
        '''Setup VMIs
        Input vmi format:
            vmi = {'count':2,
                   'vmi1':{'vn': 'vn1'},
                   'vmi2':{'vn': 'vn1'},
                  }
        '''
        vmi_count = vmi['count'] if vmi else 0
        vmi_fixtures = {} # Hash to store VMI fixtures
        for i in range(0,vmi_count):
            vmi_id = 'vmi'+str(i+1)
            if vmi_id in vmi:
                vmi_vn = vmi[vmi_id]['vn']
                vn_fixture = vn_fixtures[vmi_vn]
                vmi_fixture = self.setup_vmi(vn_fixture.uuid)
            else:
                vmi_vn = 'vn'+str(i+1)
                vn_fixture = vn_fixtures[vmi_vn]
                vmi_fixture = self.setup_vmi(vn_fixture.uuid)

            if vmi[vmi_id].get('vip'):
                vIP = vmi[vmi_id]['vip']
                mode = vmi[vmi_id].get('mode', 'active-standby')
                self.config_aap(vmi_fixture, vIP, mac=vmi_fixture.mac_address,
                                aap_mode='active-active', contrail_api=True)

            vmi_fixtures[vmi_id] = vmi_fixture

        return vmi_fixtures

    def setup_vms(self, vn_fixtures, vmi_fixtures, vm=None):
        '''Setup VMs
        Input vm format:
            vm = {'count':2, 'launch_mode':'distribute',
                  'vm1':{'vn':['vn1'], 'vmi':['vmi1'], 'userdata':{
                    'vlan': str(vmi['vmi3']['vlan'])} },
                  'vm2':{'vn':['vn1'], 'vmi':['vmi2'], 'userdata':{
                    'vlan': str(vmi['vmi4']['vlan'])} }
                }
            launch_mode can be distribute or non-distribute
        '''
        vm_count = vm['count'] if vm else 0
        launch_mode = vm.get('launch_mode','default')
        vm_fixtures = {} # Hash to store VM fixtures

        compute_nodes = self.orch.get_hosts()
        compute_nodes_len = len(compute_nodes)
        index = random.randint(0,compute_nodes_len-1)
        for i in range(0,vm_count):
            vm_id = 'vm'+str(i+1)
            vn_list = vm[vm_id]['vn']
            vmi_list = vm[vm_id]['vmi']

            vn_fix_obj_list =[]
            vmi_fix_uuid_list =[]

            # Build the VN fixtures objects
            for vn in vn_list:
                vn_fix_obj_list.append(vn_fixtures[vn].obj)

           # Build the VMI UUIDs
            for vmi in vmi_list:
                vmi_fix_uuid_list.append(vmi_fixtures[vmi].uuid)

            # VM launch mode handling
            # Distribute mode, generate the new random index
            # Non Distribute mode, use previously generated index
            # Default mode, Nova takes care of launching
            if launch_mode == 'distribute':
                index = i%compute_nodes_len
                node_name = self.inputs.compute_names[index]
            elif launch_mode == 'non-distribute':
                node_name = self.inputs.compute_names[index]
            elif launch_mode == 'default':
                node_name=None

            vm_fixture = self.create_vm(vn_objs=vn_fix_obj_list,
                                        port_ids=vmi_fix_uuid_list,
                                        node_name=node_name, image_name='cirros')
            vm_fixtures[vm_id] = vm_fixture

        for vm_fixture in vm_fixtures.values():
            assert vm_fixture.wait_till_vm_is_up()

        return vm_fixtures


    def provision_underlay_gw(self):
        '''Setup Fabric Gateway

            Sets up underlay fabric gateway
        '''

        # Provision Fabric Gateway
        name = self.inputs.fabric_gw_info[0][0]
        ip = self.inputs.fabric_gw_info[0][1]
        self.vnc_h.provision_fabric_gw(name, ip, self.inputs.router_asn)
        self.addCleanup(self.vnc_h.delete_fabric_gw, name)

        # Default security group to allow all traffic
        self.allow_default_sg_to_allow_all_on_project(self.inputs.project_name)



    def setup_gw_less_fwd(self, vn=None, vmi=None, vm=None, verify=True):
        '''Setup Gateway Less Forwarding .

            Sets up gateway less forwarding

            Input parameters looks like:
                #VN parameters:
                vn = {'count':1,            # VN count
                     # VN Details
                    'vn1':{'subnet':'10.10.10.0/24', 'ip_fabric':True},
                    'vn2':{'subnet':'20.20.20.0/24'},
                    }

                #VMI parameters:
                vmi = {'count':2, # VMI Count
                    'vmi1':{'vn': 'vn1'}, # VMI details
                    'vmi2':{'vn': 'vn1'}, # VMI details
                    }

                #VM parameters:
                vm = {'count':2, # VM Count
                    # VM Launch mode i.e distribute non-distribute, default
                    'launch_mode':'distribute',
                    'vm1':{'vn':['vn1'], 'vmi':['vmi1']}, # VM Details
                    'vm2':{'vn':['vn1'], 'vmi':['vmi2']}, # VM Details
                    }

        '''

        # Provision underlay gateway
        self.provision_underlay_gw()

        # VNs creation
        vn_fixtures = self.setup_vns(vn)

        # VMIs creation
        vmi_fixtures = self.setup_vmis(vn_fixtures, vmi)

        # VMs creation
        vm_fixtures = self.setup_vms(vn_fixtures, vmi_fixtures, vm)

        # Extra sleep for BGP route updates between controller and fabric gw
        time = 30
        self.logger.info('Sleeping for %s secs for BGP convergence' %(time))
        self.sleep(time)

        ret_dict = {
            'vmi_fixtures':vmi_fixtures,
            'vn_fixtures':vn_fixtures,
            'vm_fixtures':vm_fixtures,
        }
        return ret_dict

    @retry(delay=5, tries=3)
    def verify_routes_ip_fabric_vn_in_cn(self, ret_dict=None):
        '''
            Verify whether VM routes are present in control node
            default routing instance
        '''

        vn_fixtures = ret_dict['vn_fixtures']
        vm_fixtures = ret_dict['vm_fixtures']
        vmi_fixtures = ret_dict['vmi_fixtures']

        # Verify VM routes are present in default routing instance
        for src_vm_fixture in vm_fixtures.values():
            vn_fq_name = src_vm_fixture.vn_fq_name
            vn_name = src_vm_fixture.vn_name
            for cn in src_vm_fixture.get_control_nodes():
                ri_name = "default-domain:default-project:ip-fabric:__default__"

                # Check for VM route in each control-node
                for vm_ip in src_vm_fixture.get_vm_ip_dict()[vn_fq_name]:
                    cn_routes = self.cn_inspect[cn].get_cn_route_table_entry(
                        ri_name=ri_name, prefix=vm_ip)

                    # Check if IP Fabric forwarding is enabled
                    # If IP Fabric is enabled, VM route should be present
                    # in default routing instance
                    if vn_fixtures[vn_name].is_ip_fabric_provider_nw_present():
                        if cn_routes:
                            self.logger.info("Route: %s is found in default"\
                                             "routing instance as expected in"\
                                             "control node: %s" % (vm_ip, cn))
                        else:
                            result = False
                            assert result, "Route: %s is NOT found in default"\
                            "routing instance as expected in control node: %s"\
                            %(vm_ip, cn)
                    else:
                        if not cn_routes:
                            self.logger.info("Route: %s is NOT found in default"\
                                             "routing instance as expected in"\
                                             "control node: %s" % (vm_ip, cn))
                        else:
                            result = False
                            assert result, "Route: %s found in Control-node %s,"\
                                "not expected in control node" % (vm_ip, cn)

        return True
    # end verify_routes_ip_fabric_in_control_node

    @retry(delay=5, tries=3)
    def verify_route_ip_fabric_vn_in_control_node(self, ret_dict = None,
                                                  ip = None, expectation = True):
        '''
            Verify whether AAP/FIP route is present in agent
            default routing instance
        '''

        ri_name = "default-domain:default-project:ip-fabric:__default__"
        #Verify VM routes are present in default routing instance
        cn_ips = self.inputs.bgp_control_ips

        for cn in cn_ips:
            cn_routes = self.cn_inspect[cn].get_cn_route_table_entry(
                ri_name=ri_name, prefix=ip)

            # Check if IP Fabric forwarding is enabled
            # If IP Fabric is enabled, VM route should be present
            # in default routing instance
            if expectation:
                if cn_routes:
                    self.logger.info("Route: %s is found in default routing "\
                                    "instance as expected in control node: %s"
                                    % (ip,cn))
                else:
                    result = False
                    assert result, "Route: %s is NOT found in default routing "\
                        "instance as expected in control node: %s" % (ip, cn)
            else:
                if cn_routes:
                    result = False
                    assert result, "Route: %s is found in default routing "\
                        "instance, NOT expected in control node: %s" % (ip, cn)
                else:
                    self.logger.info("Route: %s is NOT found in default routing"\
                                    " instance as expected in control node: %s"
                                    % (ip,cn))

            return True



    @retry(delay=5, tries=3)
    def verify_route_ip_fabric_vn_in_agent(self, ret_dict = None, ip = None,
                                           expectation = True):
        '''
            Verify whether AAP/FIP route is present in agent
            default routing instance
        '''

        vm_fixtures = ret_dict['vm_fixtures']
        # Get the unique compute nodes
        compute_node_ips = set()
        for vm_fixture in vm_fixtures.values():
            compute_node_ips.add(vm_fixture.get_compute_host())

        # Verify VM routes are present in default routing instance
        for compute_ip in compute_node_ips:
            agent_inspect_h = self.agent_inspect[compute_ip]
            vrf_id = 0
            route = agent_inspect_h.get_vna_route(vrf_id= vrf_id, ip=ip)
            self.logger.debug("Route value : %s" % ip)

            if expectation:
                if route:
                    self.logger.info("Route: %s is found in default routing "\
                                    "instance as expected in agent on "\
                                    "compute node: %s" % (ip, compute_ip))
                else:
                    result = False
                    assert result, "Route: %s is NOT present in fabric routing "\
                        "instance, not expected in agent" % (ip, compute_ip)
            else:
                if route:
                    result = False
                    assert result, "Route: %s is present in fabric routing "\
                        "instance, NOT expected in agent" % (ip, compute_ip)
                else:
                    self.logger.info("Route: %s is NOT found in default routing"\
                                    " instance as expected in agent on "\
                                    "compute node: %s" % (ip, compute_ip))

        return True



    @retry(delay=5, tries=3)
    def verify_routes_ip_fabric_vn_in_agent(self, ret_dict = None):
        '''
            Verify whether VM routes are present in agent
            default routing instance
        '''

        vn_fixtures = ret_dict['vn_fixtures']
        vm_fixtures = ret_dict['vm_fixtures']
        vmi_fixtures = ret_dict['vmi_fixtures']

        # Verify VM routes are present in default routing instance
        for src_vm_fixture in vm_fixtures.values():
            compute_ip = src_vm_fixture.vm_node_ip
            agent_inspect_h = self.agent_inspect[compute_ip]
            vrf_id = 0
            route = agent_inspect_h.get_vna_route(vrf_id= vrf_id,
                                                  ip=src_vm_fixture.vm_ip)
            self.logger.debug("Route value : %s" % route)

            vn_name = src_vm_fixture.vn_name
            port_ids = src_vm_fixture.port_ids

            # Check if IP Fabric forwarding is enabled
            # If IP Fabric is enabled, VM route should be present
            # in default routing instance
            if vn_fixtures[vn_name].is_ip_fabric_provider_nw_present():
                if route:
                    self.logger.info("Route: %s is found in default routing "\
                                     "instance as expected in agent on compute"\
                                     " node: %s" % (src_vm_fixture.vm_ip,
                                                   compute_ip))
                else:
                    result = False
                    assert result, "Route: %s is NOT present in fabric routing"\
                        " instance, not expected in agent on compute node: %s" \
                        % (src_vm_fixture.vm_ip, compute_ip)
            else:
                if not route:
                    self.logger.info("Route: %s is NOT found in default "\
                                     "routing  instance as expected in agent "\
                                     "on compute node: %s" % (
                                         src_vm_fixture.vm_ip, compute_ip))
                else:
                    result = False
                    assert result, "Route: %s is present in fabric routing "\
                        "instance, not expected in agent on compute node: %s" \
                        % (src_vm_fixture.vm_ip, compute_ip)
        return True


    def verify_ping_from_vhosts_to_vms(self, ret_dict = None):
        '''
            Verify whether ping from each vhost to another VMs is fine or not
            Also verify whether ping is going trough underlay
        '''

        vn_fixtures = ret_dict['vn_fixtures']
        vm_fixtures = ret_dict['vm_fixtures']
        vmi_fixtures = ret_dict['vmi_fixtures']

        # Get the unique compute nodes
        compute_node_ips = set()
        for vm_fixture in vm_fixtures.values():
            compute_node_ips.add(vm_fixture.get_compute_host())

        # Pinging all VMIs from vhost
        for compute_ip in compute_node_ips:
            for src_vm_fixture in vm_fixtures.values():

                vn_name = src_vm_fixture.vn_name

                # IP Fabric forwarding is enabled on the VN, ping from vhost to
                # VM should be successful and should go through underlay
                if vn_fixtures[vn_name].is_ip_fabric_provider_nw_present():

                    # Source VM is local VM
                    if src_vm_fixture.get_compute_host() == compute_ip:
                        result = self.ping_vm_from_vhost(compute_ip,
                                                         src_vm_fixture.vm_ip,
                                                         count=2)
                        if result:
                            self.logger.info('Ping from compute node: %s to '\
                                             'local VM: %s is successful as '\
                                             'expected' %(compute_ip,
                                                          src_vm_fixture.vm_ip))
                        else:
                            assert result, 'Ping from compute node: %s to VM: '\
                                '%s is NOT successful, not expected' %(
                                    compute_ip, src_vm_fixture.vm_ip)
                    # Source VM is remote VM
                    else:
                        #Start tcpdump on compute node.
                        #Traffic should go through underlay
                        compute_user = self.inputs.host_data[compute_ip]['username']
                        compute_password = self.inputs.host_data[compute_ip]['password']
                        inspect_h = self.agent_inspect[compute_ip]
                        compute_intf = inspect_h.get_vna_interface_by_type('eth')

                        if len(compute_intf) == 1:
                            compute_intf = compute_intf[0]
                        self.logger.debug('Compute interface name: %s' %
                                          compute_intf)

                        # Filters as per underlay traffic
                        filters = '\'(src host %s and dst host %s)\'' % (
                            compute_ip, src_vm_fixture.vm_ip)
                        session, pcap = start_tcpdump_for_intf(compute_ip,
                                                               compute_user,
                                                               compute_password,
                                                               compute_intf,
                                                               filters = filters)
                        self.sleep(1)

                        # Pinging remote VM from compute
                        result = self.ping_vm_from_vhost(compute_ip,
                                                         src_vm_fixture.vm_ip,
                                                         count=2)
                        if result:
                            self.logger.info('Ping from compute node: %s to '\
                                             'remote VM: %s is successful'
                                             %(compute_ip, src_vm_fixture.vm_ip))
                        else:
                            assert result, 'Ping from compute node: %s to '\
                                'remote VM: %s is NOT successful' %(
                                compute_ip, src_vm_fixture.vm_ip)

                        self.sleep(1)

                        stop_tcpdump_for_intf(session, pcap)

                        result = verify_tcpdump_count(self, session, pcap,
                                exp_count=2, grep_string=src_vm_fixture.vm_ip)
                        # Verify tcpdump
                        if result:
                            self.logger.info('Packets are going through '\
                                             'underlay properly between compute'\
                                             'node: %s and VM: %s'
                                             %(compute_ip, src_vm_fixture.vm_ip))
                        else:
                            assert result, "Packets are going NOT through "\
                                "underlay properly between compute node: "\
                                "%s and VM: %s" %(compute_ip,
                                                  src_vm_fixture.vm_ip)

                # IP Fabric forwarding is disabled, ping from compute node to VM
                # should not be successful.
                else:
                    result = self.ping_vm_from_vhost(compute_ip,
                                                     src_vm_fixture.vm_ip,
                                                     count=2, expectation=False)
                    if result:
                        self.logger.info('Ping from compute node: %s to VM: %s'\
                                         ' is NOT successful as expected' %(
                                             compute_ip, src_vm_fixture.vm_ip))
                    else:
                        assert result, 'Ping from compute node: %s to VM: %s '\
                            'is successful, not expected' %(compute_ip,
                                                            src_vm_fixture.vm_ip)

        return True


    def verify_ping_from_vms_to_vhosts(self, ret_dict = None):
        '''
            Verify whether ping from each VM to vhosts is fine or not
            Also verify whether ping is going trough underlay
        '''

        vn_fixtures = ret_dict['vn_fixtures']
        vm_fixtures = ret_dict['vm_fixtures']
        vmi_fixtures = ret_dict['vmi_fixtures']

        # Get the compute nodes
        compute_node_ips = set()
        for vm_fixture in vm_fixtures.values():
            compute_node_ips.add(vm_fixture.get_compute_host())


        # Pinging all vhosts from the VMs
        for src_vm_fixture in vm_fixtures.values():
            for compute_ip in compute_node_ips:

                vn_name = src_vm_fixture.vn_name

                # IP Fabric forwarding is enabled on the VN, ping from VM to
                # vhost should be successful and should go through underlay
                if vn_fixtures[vn_name].is_ip_fabric_provider_nw_present():

                    # Local compute node
                    if src_vm_fixture.get_compute_host() == compute_ip:
                        result = src_vm_fixture.ping_with_certainty(compute_ip,
                                                                    count=2)
                        if result:
                            self.logger.info('Ping from VM:%s to local compute '\
                                             'node: %s is successful as expected'
                                             %(src_vm_fixture.vm_ip, compute_ip))
                        else:
                            assert result, 'Ping from VM: %s to local compute'\
                                'node: %s is NOT successful, which is not '\
                                'expected' %(src_vm_fixture.vm_ip, compute_ip)

                    # pinging remote compute from VM in underlay mode.
                    # Verify whether traffic goes through underlay or not
                    else:
                        # Start tcpdump on compute node. Traffic should go
                        # through underlay
                        compute_user = self.inputs.host_data[compute_ip]['username']
                        compute_password = self.inputs.host_data[compute_ip]['password']
                        inspect_h = self.agent_inspect[compute_ip]
                        compute_intf = inspect_h.get_vna_interface_by_type('eth')

                        if len(compute_intf) == 1:
                            compute_intf = compute_intf[0]
                        self.logger.debug('Compute interface name: %s' %
                                          compute_intf)

                        # Filters as per underlay traffic
                        filters = '\'(src host %s and dst host %s)\'' % (
                            src_vm_fixture.vm_ip,compute_ip)
                        session, pcap = start_tcpdump_for_intf(compute_ip,
                                                               compute_user,
                                                               compute_password,
                                                               compute_intf,
                                                               filters = filters)
                        self.sleep(1)

                        # Pinging remote compute from VM
                        result = src_vm_fixture.ping_with_certainty(compute_ip,
                                                                    count=2)
                        if result:
                            self.logger.info('Ping from VM: %s to remote '\
                                             'compute node: %s is successful '\
                                             'as expected' %(src_vm_fixture.vm_ip,
                                                             compute_ip))
                        else:
                            assert result, 'Ping from VM: %s to remote compute'\
                                ' node: %s is NOT successful, not expected' %(
                                src_vm_fixture.vm_ip, compute_ip)

                        self.sleep(1)

                        stop_tcpdump_for_intf(session, pcap)

                        result = verify_tcpdump_count(self, session, pcap,
                                  exp_count=2, grep_string=src_vm_fixture.vm_ip)

                        # Verify tcpdump
                        if result:
                            self.logger.info('Packets are going through underlay'\
                                             ' properly between VM: %s and '\
                                             'Compute Node: %s' %(
                                             src_vm_fixture.vm_ip, compute_ip))
                        else:
                            assert result, 'Packets are NOT going through '\
                                'underlay properly between VM: %s and Compute '\
                                'Node: %s' %(src_vm_fixture.vm_ip, compute_ip)

                # IP Fabric forwarding is disabled, ping from VM to compute node
                # should not be successful.
                else:
                    result = src_vm_fixture.ping_with_certainty(compute_ip,
                                                                count=2,
                                                                expectation=False)
                    if result:
                        self.logger.info('Ping from VM: %s to compute node: %s'\
                                         ' is NOT successful as expected'
                                         %(src_vm_fixture.vm_ip, compute_ip))
                    else:
                        assert result, 'Ping from VM: %s to compute node: %s '\
                            'is successful, which is not expected' %(
                            src_vm_fixture.vm_ip, compute_ip)


        return True


    def verify_ping_across_vms(self, ret_dict = None):
        '''
            Verify whether ping from each VM to another VMs is fine or not
            Also verify whether ping is going trough underlay or overlay
            as per IP Fabric configuration on VN
        '''

        vn_fixtures = ret_dict['vn_fixtures']
        vm_fixtures = ret_dict['vm_fixtures']
        vmi_fixtures = ret_dict['vmi_fixtures']
        policy_fixtures = ret_dict.get('policy_fixtures', None)
        if policy_fixtures:
            expectation = True
        else:
            expectation = False

        # Pinging all the VMIs
        for src_vm_fixture in vm_fixtures.values():
            for dst_vm_fixture in vm_fixtures.values():
                src_vm_ip = src_vm_fixture.vm_ip
                dst_vm_ip = dst_vm_fixture.vm_ip
                src_vn_name = src_vm_fixture.vn_name
                dst_vn_name = dst_vm_fixture.vn_name

                src_vn_is_ip_fab = vn_fixtures[src_vn_name].is_ip_fabric_provider_nw_present()
                dst_vn_is_ip_fab = vn_fixtures[dst_vn_name].is_ip_fabric_provider_nw_present()

                # Same VM
                if src_vm_ip == dst_vm_ip:
                    continue

                # IP Fabric forwarding is enabled on both source and destination
                # VM VNs. Ping should go through underlay
                if src_vn_is_ip_fab and dst_vn_is_ip_fab:

                    # Both source and destination VMs are in same compute
                    if src_vm_fixture.get_compute_host() == dst_vm_fixture.get_compute_host():
                        result = src_vm_fixture.ping_with_certainty(dst_vm_ip,
                                        count=2, expectation=expectation)
                        if expectation:
                            if result:
                                self.logger.info('Ping from VM: %s to VM: %s '\
                                                 'is successful, as expected'
                                                 %(src_vm_ip, dst_vm_ip))
                            else:
                                assert result, "Ping from VM: %s to VM: %s is"\
                                    "not successful" %(src_vm_ip, dst_vm_ip)
                        else:
                            # Ping between VMs across VNs should fail.
                            if src_vn_name != dst_vn_name:
                                if result:
                                    assert not result, "Ping from VM: %s to VM:"\
                                        "%s should not be successful" %(
                                        src_vm_ip, dst_vm_ip)
                                else:
                                    self.logger.info('Ping from VM: %s to VM:'\
                                                     '%s is NOT successful as '\
                                                     'expected' %(src_vm_ip,
                                                                  dst_vm_ip))

                    else:
                        #Start tcpdump on compute node. Traffic should go through as per mode configured
                        compute_ip = src_vm_fixture.vm_node_ip
                        compute_user = self.inputs.host_data[compute_ip]['username']
                        compute_password = self.inputs.host_data[compute_ip]['password']
                        inspect_h = self.agent_inspect[compute_ip]
                        compute_intf = inspect_h.get_vna_interface_by_type('eth')
                        if len(compute_intf) == 1:
                            compute_intf = compute_intf[0]
                        self.logger.debug('Compute interface name: %s'
                                          % compute_intf)

                        filters = '\'(src host %s and dst host %s)\'' %(src_vm_ip,
                                                                        dst_vm_ip)

                        session, pcap = start_tcpdump_for_intf(compute_ip,
                                                               compute_user,
                                                               compute_password,
                                                               compute_intf,
                                                               filters = filters)
                        self.sleep(1)

                        result = src_vm_fixture.ping_with_certainty(dst_vm_ip,
                                                                    count=2)
                        self.sleep(1)

                        if expectation:
                            if result:
                                self.logger.info('Ping from VM: %s to VM: %s '\
                                                 'is successful' %(src_vm_ip,
                                                                   dst_vm_ip))
                            else:
                                assert result, "Ping from VM: %s to VM:%s is"\
                                "NOT successful" %(src_vm_ip, dst_vm_ip)
                        else:
                            # Ping between VMs across VNs should fail.
                            if src_vn_name != dst_vn_name:
                                if result:
                                    assert not result, "Ping from VM: %s to "\
                                    "VM:%s should not be successful" %(src_vm_ip,
                                                                       dst_vm_ip)
                                else:
                                    self.logger.info('Ping from VM: %s to VM:'\
                                                     '%s is NOT successful as'\
                                                     'expected' %(src_vm_ip,
                                                                  dst_vm_ip))

                        stop_tcpdump_for_intf(session, pcap)

                        result = verify_tcpdump_count(self, session, pcap,
                                                      exp_count=2,
                                                      grep_string=dst_vm_ip)

                        # Verify tcpdump
                        if result:
                            self.logger.info('Packets are going through '\
                                             'underlay properly between SRC VM:'\
                                             '%s and DST VM: %s' %(src_vm_ip,
                                                                   dst_vm_ip))
                        else:
                            assert result, 'Packets are NOT going through '\
                            'underlay between SRC VM: %s and DST VM: %s' %(
                            src_vm_ip, dst_vm_ip)

                else:
                    # Ping between VMs within a VN should be successful
                    if src_vn_name == dst_vn_name:
                        expectation = True

                    result = src_vm_fixture.ping_with_certainty(dst_vm_ip,
                                                count=2, expectation=expectation)
                    if expectation:
                        if result:
                            self.logger.info('Ping from VM: %s to VM: %s is'\
                                             'successful, as expected'
                                             %(src_vm_ip, dst_vm_ip))
                        else:
                            assert result, "Ping from VM: %s to VM: %s is not"\
                            "successful" %(src_vm_ip, dst_vm_ip)
                    else:
                        # Ping between VMs across VNs should fail.
                        if src_vn_name != dst_vn_name:
                            if result:
                                assert not result, "Ping from VM: %s to VM: %s"\
                                "should not be successful" %(src_vm_ip,
                                                             dst_vm_ip)
                            else:
                                self.logger.info('Ping from VM: %s to VM: %s '\
                                                 'is NOT successful as expected'
                                                 %(src_vm_ip, dst_vm_ip))


        return True

    def verify_gw_less_fwd(self, ret_dict = None):
        '''
            Verify if gateway less forwarding works fine or not
            1. Ping from each VM to remaining VMs should be successful
            2. Packet should be going through underlay
            3. Verify routes in VRF:0
            4. Verify encapsulation type, it should be Underlay
            5. Verify ping from vhost to VM also successful
        '''

        vn_fixtures = ret_dict['vn_fixtures']
        vm_fixtures = ret_dict['vm_fixtures']
        vmi_fixtures = ret_dict['vmi_fixtures']
        policy_fixtures = ret_dict.get('policy_fixtures', None)

        # Verify VM routes are present in default routing instance or not
        # at agent and control
        self.verify_routes_ip_fabric_vn_in_agent(ret_dict=ret_dict)
        self.verify_routes_ip_fabric_vn_in_cn(ret_dict=ret_dict)

        # Ping between VMs. Traffic should go through as per config
        self.verify_ping_across_vms(ret_dict=ret_dict)

        # Pinging all VMIs from vhost. Traffic should go through as per config
        self.verify_ping_from_vhosts_to_vms(ret_dict=ret_dict)

        # Pinging all vhosts from VMIs. Traffic should go through as per config
        self.verify_ping_from_vms_to_vhosts(ret_dict=ret_dict)

        return True


    def ping_vm_from_vhost(self, vm_node_ip, vm_ip, count=2, expectation=True,
                           timeout=2):
        '''
            Ping the VM metadata IP from the host
        '''

        cmd = 'ping %s -c 2 -W %s' % (vm_ip, timeout)
        output = self.inputs.run_cmd_on_server(vm_node_ip, cmd)

        failure = ' 100% packet loss'
        if failure in output:
            self.logger.debug(
                "Ping to IP %s is failed from vhost: %s!"
                %(vm_ip, vm_node_ip))
            result = False
        else:
            self.logger.debug(
                'Ping to IP %s is passed from vhost:%s'
                %(vm_ip, vm_node_ip))
            result = True

        return (result == expectation)
    # end ping_vm_from_host

    def setup_policy(self, policy=None, vn_fixtures=None , verify=True):
        '''
            Setup Policy

            Input parameters looks like:

            policy = {  'count':1,
                        'p1': {
                            rules': [
                                {
                                    'direction':'<>',
                                    'protocol':'any',
                                    'source_network': 'vn1',
                                    'dest_network':'vn2',
                                    'src_ports':'any',
                                    'dst_ports':'any'
                                },
                            ]
                        }
                    }
        '''
        policy_count = policy['count'] if policy else 1
        policy_fixtures = {} # Hash to store Policy fixtures
        for i in range(0,policy_count):
            policy_id = 'p'+str(i+1)
            if policy_id in policy:
                rules = policy[policy_id].get('rules',None)
                source_network = rules[0].get('source_network',None)
                dest_network = rules[0].get('dest_network',None)
                policy_fixture = self.config_policy(policy_id, rules)

                if source_network == 'default-domain:default-project:ip-fabric':
                    ip_fab_vn_obj = self.get_ip_fab_vn()
                    policy_obj = self.vnc_h.network_policy_read(
                        fq_name=policy_fixture.policy_fq_name)
                    self.logger.info('Attaching policy %s on VN: %s' % (
                        policy_obj.name, ip_fab_vn_obj.get_fq_name_str()))
                    ip_fab_vn_obj.add_network_policy(
                        policy_obj,
                        VirtualNetworkPolicyType(sequence=SequenceType(major=0,
                                                                       minor=0)))
                    self.vnc_h.virtual_network_update(ip_fab_vn_obj)
                    self.addCleanup(self.detach_policy_ip_fabric_vn, ip_fab_vn_obj, policy_obj)
                else:
                    src_vn_fix = vn_fixtures[source_network]
                    self.attach_policy_to_vn(policy_fixture, src_vn_fix)
                if dest_network == 'default-domain:default-project:ip-fabric':
                    ip_fab_vn_obj = self.get_ip_fab_vn()
                    policy_obj = self.vnc_h.network_policy_read(
                        fq_name=policy_fixture.policy_fq_name)
                    self.logger.info('Attaching policy %s on VN: %s' % (
                        policy_obj.name, ip_fab_vn_obj.get_fq_name_str()))
                    ip_fab_vn_obj.add_network_policy(
                        policy_obj,
                        VirtualNetworkPolicyType(sequence=SequenceType(major=0,
                                                                       minor=0)))
                    self.vnc_h.virtual_network_update(ip_fab_vn_obj)
                    self.addCleanup(self.detach_policy_ip_fabric_vn, ip_fab_vn_obj, policy_obj)
                else:
                    dst_vn_fix = vn_fixtures[dest_network]
                    self.attach_policy_to_vn(policy_fixture, dst_vn_fix)

                policy_fixtures[policy_id] = policy_fixture
        return policy_fixtures

    def config_aap(self, vmi, prefix, prefix_len=32, mac='',
                   aap_mode='active-standby', contrail_api=False):
        '''
            Setup allowed address pair as per user configuration
        '''
        self.logger.info('Configuring AAP on port %s' % vmi.uuid)
        if contrail_api:
            self.vnc_h.add_allowed_address_pair(
                vmi.uuid, prefix, prefix_len, mac, aap_mode)
        else:
            port_dict = {'allowed_address_pairs': [
                {"ip_address": prefix + '/' + str(prefix_len),
                 "mac_address": mac}]}
            port_rsp = self.update_port(vmi.uuid, port_dict)
        return True
    # end config_aap

    def config_fip(self, ret_dict, vn_id, vmi_id, my_fip=None):
        '''
            Create a FIP on VN (vn_id) and apply this on VMI (vmi_id)
        '''

        self.logger.info('Configuring FIP on port %s' % vmi_id)

        vn_fixtures = ret_dict['vn_fixtures']
        vm_fixtures = ret_dict['vm_fixtures']
        vmi_fixtures = ret_dict['vmi_fixtures']

        if my_fip is None:
            my_fip = self.get_random_fip(vn_fixtures['vn1'])

        fip_fixture = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name, inputs=self.inputs,
                connections=self.connections, pool_name='some-pool1',
                vn_id=vn_id))
        assert fip_fixture.verify_on_setup()

        fvn_obj = self.vnc_h.virtual_network_read(id=vn_id)
        fip_pool_obj = FloatingIpPool('some-pool1', fvn_obj)
        fip_obj = FloatingIp('fip', fip_pool_obj, my_fip, True)

        fip_obj.set_project(self.project_fixture.project_obj)

        # Apply FIP on the VMI
        vm_intf = self.vnc_h.virtual_machine_interface_read(id=vmi_id)
        fip_obj.add_virtual_machine_interface(vm_intf)
        self.vnc_h.floating_ip_create(fip_obj)
        self.addCleanup(self.vnc_h.floating_ip_delete, fip_obj.fq_name)
        fip_obj = self.vnc_h.floating_ip_read(fq_name=fip_obj.fq_name)
        fip = fip_obj.get_floating_ip_address()

        return (fip, fip_obj)

    # end config_fip


    def get_random_fip(self, vn):
        return get_random_ip(vn.vn_subnets[0]['cidr'])
    #end get_random_fip

    @classmethod
    def tearDownClass(cls):
        super(GWLessFWDTestBase, cls).tearDownClass()
    # end tearDownClass
