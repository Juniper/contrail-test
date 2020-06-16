from builtins import str
from builtins import range
from common.gw_less_fwd.base import *
from tcutils.wrappers import preposttest_wrapper
from contrailapi import ContrailVncApi
from common.svc_firewall.base import BaseSvc_FwTest
from common.servicechain.firewall.verify import VerifySvcFirewall
from common.servicechain.mirror.verify import VerifySvcMirror
import test
from tcutils.util import *
from time import sleep
from copy import copy

class TestGWLessFWD(GWLessFWDTestBase):

    @classmethod
    def setUpClass(cls):
        super(TestGWLessFWD, cls).setUpClass()
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(TestGWLessFWD, cls).tearDownClass()
    # end tearDownClass

    @test.attr(type=['cb_sanity', 'sanity', 'vcenter'])
    @preposttest_wrapper
    def test_gw_less_fwd_single_vn_ip_fab(self):
        '''
            Test Gateway less forwarding with single VN and IP Fabric provider
            network. IP Fbaric network is configured as provider network
            over vn1. Multiple VMs will be launched across compute nodes
            and ping between VMs should be successful and happen through
            underlay. Ping between vhosts to VMs should be successful and happen
            through underlay. Also, ping between VMs to vhosts also should be
            successful and should go through underlay.
        '''
        if (len(self.inputs.compute_ips) < 2):
             raise self.skipTest(
                "Skipping Test. At least 2 compute node required to run the test")

        if not self.inputs.fabric_gw_info:
             raise self.skipTest(
                "Skipping Test. Fabric gateway is required to run the test")

        # VN parameters. IP Fabric forwarding is enabled on vn1.
        vn = {'count':1,
              'vn1':{'subnet':get_random_cidr(), 'ip_fabric':True},
             }

        # VMI parameters
        vmi = {'count':2,
               'vmi1':{'vn': 'vn1'},
               'vmi2':{'vn': 'vn1'},
              }

        # VM parameters
        vm = {'count':2, 'launch_mode':'distribute',
              'vm1':{'vn':['vn1'], 'vmi':['vmi1']},
              'vm2':{'vn':['vn1'], 'vmi':['vmi2']},
             }

        # Setup VNs, VMs as per user configuration
        ret_dict = self.setup_gw_less_fwd(vn=vn, vmi=vmi, vm=vm)

        vn_fixtures = ret_dict['vn_fixtures']

        # Verify Gateway less forward functionality. As IP Fabric forwarding
        # is enabled on vn1, traffic should go through underlay between VMs
        # As there is no explicit policy to allow traffic between VN and
        # "ip-fbric" network, ping from vhost to VM and VM to vhost should fail

        self.logger.info("-- SCENARIO: 1 Verifying gateway less forward "\
                         "functionality without explicit policy --")
        self.verify_gw_less_fwd(ret_dict)

        # Policy parameters. Configuring a policy between between ip-fabric vn
        # and vn1 to allow communication between compute node and VMs in vn1.
        policy = {'count':1,
                  'p1': {
                      'rules': [
                            {
                            'direction':'<>',
                            'protocol':'any',
                            'source_network': 'default-domain:default-project:ip-fabric',
                            'dest_network':'vn1',
                            'src_ports':'any',
                            'dst_ports':'any'
                            },
                        ]
                    }
                  }

        # Configure policy as per user configuration
        policy_fixtures = self.setup_policy(policy=policy,
                                            vn_fixtures=vn_fixtures)
        ret_dict['policy_fixtures'] = policy_fixtures

        # Verify Gateway less forward functionality. As IP Fabric forwarding
        # is enabled on vn1, traffic should go through underlay. Also, as
        # there is explicit policy to allow traffic between VN and "ip-fabric"
        # network, ping from vhost to VM and VM to vhost should be successful.

        self.logger.info("-- SCENARIO: 2 Verifying gateway less forward "\
                         "functionality with explicit policy --")
        self.verify_gw_less_fwd(ret_dict)

        # Now, remove IP fabric provider network configuration on vn1
        vn1_fixture = vn_fixtures['vn1']
        ip_fab_vn_obj = self.get_ip_fab_vn()
        vn1_fixture.del_ip_fabric_provider_nw(ip_fab_vn_obj)

        time.sleep(2)

        # Verify Gateway less forward functionality. As IP Fabric forwarding
        # is disabled on vn1, traffic should go through overlay

        self.logger.info("-- SCENARIO: 3 Verifying gateway less forward "\
                         "functionality when IP farwarding is disabled--")
        self.verify_gw_less_fwd(ret_dict=ret_dict)

    # end test_gw_less_fwd_single_vn_ip_fab

    @preposttest_wrapper
    def test_gw_less_fwd_multi_vn_ip_fab(self):
        '''
            Test Gateway less forwarding with multiple VNs and IP Fabric provider
            network. IP Fbaric network is configured as provider network
            over vn1 and vn2. Multiple VMs will be launched across compute nodes
            and ping between VMs should be successful and happen through
            underlay. Ping between vhosts to VMs should be successful and happen
            through underlay. Also, ping between VMs to vhosts should be
            successful and should go through underlay. Also, verify when policy
            is disabled between vn1 and vn2, communication should not takes place
        '''

        if (len(self.inputs.compute_ips) < 2):
             raise self.skipTest(
                "Skipping Test. At least 2 compute node required to run the test")

        if not self.inputs.fabric_gw_info:
             raise self.skipTest(
                "Skipping Test. Fabric gateway is required to run the test")


        # VN parameters. IP Fabric forwarding is enabled on both vn1 and vn2.
        vn = {'count':2,
              'vn1':{'subnet':get_random_cidr(), 'ip_fabric':True},
              'vn2':{'subnet':get_random_cidr(), 'ip_fabric':True},
             }

        # VMI parameters. 2 VMIs per VN.
        vmi = {'count':4,
               'vmi1':{'vn': 'vn1'},
               'vmi2':{'vn': 'vn1'},
               'vmi3':{'vn': 'vn2'},
               'vmi4':{'vn': 'vn2'},
              }

        # VM parameters. 2 VMs are launched across compute nodes.
        vm = {'count':4, 'launch_mode':'distribute',
              'vm1':{'vn':['vn1'], 'vmi':['vmi1']},
              'vm2':{'vn':['vn1'], 'vmi':['vmi2']},
              'vm3':{'vn':['vn2'], 'vmi':['vmi3']},
              'vm4':{'vn':['vn2'], 'vmi':['vmi4']},
             }

        # Setup VNs, VMs as per user configuration
        ret_dict = self.setup_gw_less_fwd(vn=vn, vmi=vmi, vm=vm)

        vn_fixtures = ret_dict['vn_fixtures']

        # Verify Gateway less forward functionality with out policy
        # As IP Fabric provider network is configured on vn1 and vn2
        # and policy is disabled Traffic should go through underlay
        # between VMs within same VN and traffic should fail across VNs

        self.logger.info("-- SCENARIO: 1 Verifying gateway less forward "\
                         "functionality without explicit policy --")
        self.verify_gw_less_fwd(ret_dict = ret_dict)

        # Policy parameters. Configuring policy between vn1 and vn2 to allow
        # the traffic. Also, policy between ip-fabric vn and vn1 needs to be
        # configured to allow communication between compute node and VMs in vn1.
        # Similarly for vn2 as well.
        policy = {'count':3,
                  'p1': {
                      'rules': [
                            {
                            'direction':'<>',
                            'protocol':'any',
                            'source_network': 'vn1',
                            'dest_network':'vn2',
                            'src_ports':'any',
                            'dst_ports':'any'
                            },
                        ]
                    },
                  'p2': {
                      'rules': [
                            {
                            'direction':'<>',
                            'protocol':'any',
                            'source_network': 'default-domain:default-project:ip-fabric',
                            'dest_network':'vn1',
                            'src_ports':'any',
                            'dst_ports':'any'
                            },
                        ]
                    },
                  'p3': {
                      'rules': [
                            {
                            'direction':'<>',
                            'protocol':'any',
                            'source_network': 'default-domain:default-project:ip-fabric',
                            'dest_network':'vn2',
                            'src_ports':'any',
                            'dst_ports':'any'
                            },
                        ]
                    }
                  }


        # Configure policy as per user configuration
        policy_fixtures = self.setup_policy(policy=policy,
                                            vn_fixtures=vn_fixtures)
        ret_dict['policy_fixtures'] = policy_fixtures

        # Verify Gateway less forward functionality with policy
        # As IP Fabric provider network is configured on vn1 and vn2
        # Traffic should go through underlay and traffic across VNs should pass.
        # Ping from vhost to VMs and VMs to vhost should also be successful.
        self.verify_gw_less_fwd(ret_dict=ret_dict)

        # Now, remove IP fabric provider network configuration on vn1 and vn2
        vn1_fixture = vn_fixtures['vn1']
        vn2_fixture = vn_fixtures['vn2']
        ip_fab_vn_obj = self.get_ip_fab_vn()

        self.logger.info("Deleting IP Fabric forwarding on VN: vn1")
        vn1_fixture.del_ip_fabric_provider_nw(ip_fab_vn_obj)
        self.logger.info("Deleting IP Fabric forwarding on VN: vn1")
        vn2_fixture.del_ip_fabric_provider_nw(ip_fab_vn_obj)
        time.sleep(2)

        # Since IP fabric provider network configuration on vn1 and vn2
        # is disabled traffic should go through overlay, instead of underlay
        self.verify_gw_less_fwd(ret_dict=ret_dict)

    # end test_gw_less_fwd_multi_vn_ip_fab

    @preposttest_wrapper
    def test_gw_less_fwd_ip_fab_vn_and_cust_vn(self):
        '''
            Test Gateway less forwarding with multiple VNs and IP Fabric provider
            network. IP Fbaric network is configured as provider network
            over vn1. vn2 is not configured with IP fabric provider network.
            Policy is configured between vn1 and vn2 to allow the traffic.
            Multiple VMs will be launched across compute nodes
            and ping between VMs should be successful and happen through
            overlay .
        '''

        if (len(self.inputs.compute_ips) < 2):
             raise self.skipTest(
                "Skipping Test. At least 2 compute node required to run the test")

        if not self.inputs.fabric_gw_info:
             raise self.skipTest(
                "Skipping Test. Fabric gateway is required to run the test")


        # VN parameters. IP Fabric forwarding is enabled on vn1 and not on vn2.
        vn = {'count':2,
              'vn1':{'subnet':get_random_cidr(), 'ip_fabric':True},
              'vn2':{'subnet':get_random_cidr(), 'ip_fabric':False},
             }
        # VMI parameters
        vmi = {'count':4,
               'vmi1':{'vn': 'vn1'},
               'vmi2':{'vn': 'vn1'},
               'vmi3':{'vn': 'vn2'},
               'vmi4':{'vn': 'vn2'},
              }

        # VM parameters
        vm = {'count':4, 'launch_mode':'distribute',
              'vm1':{'vn':['vn1'], 'vmi':['vmi1']},
              'vm2':{'vn':['vn1'], 'vmi':['vmi2']},
              'vm3':{'vn':['vn2'], 'vmi':['vmi3']},
              'vm4':{'vn':['vn2'], 'vmi':['vmi4']},
             }

        # Setup VNs, VMs as per user configuration
        ret_dict = self.setup_gw_less_fwd(vn=vn, vmi=vmi, vm=vm)

        vn_fixtures = ret_dict['vn_fixtures']

        # Policy parameters. Configuring policy between vn1 and vn2 to allow
        # the traffic. Also, policy between ip-fabric vn and vn1 needs to be
        # configured to allow communication between compute node and VMs in vn1.
        # Similarly for vn2 as well.
        policy = {'count':2,
                  'p1': {
                      'rules': [
                            {
                            'direction':'<>',
                            'protocol':'any',
                            'source_network': 'vn1',
                            'dest_network':'vn2',
                            'src_ports':'any',
                            'dst_ports':'any'
                            },
                        ]
                    },
                  'p2': {
                      'rules': [
                            {
                            'direction':'<>',
                            'protocol':'any',
                            'source_network': 'default-domain:default-project:ip-fabric',
                            'dest_network':'vn1',
                            'src_ports':'any',
                            'dst_ports':'any'
                            },
                        ]
                    },
                  }


        # Configure policy between vn1 and vn2
        policy_fixtures = self.setup_policy(policy=policy,
                                            vn_fixtures=vn_fixtures)
        ret_dict['policy_fixtures'] = policy_fixtures

        # As IP Fabric forwarding is enabled on vn1 and not vn2 and policy is
        # configured to allow traffic between vn1 and vn2. Traffic should go
        # through overlay between VNs. Also, ping from vhost to VMs and
        # VMs to vhost should also be successful.
        ret_dict = self.verify_gw_less_fwd(ret_dict=ret_dict)

    # end test_gw_less_fwd_ip_fab_vn_and_cust_vn

    @preposttest_wrapper
    def test_gw_less_fwd_aap(self):
        '''
            Test Gateway less forwarding functionality with allowed address pair.
            Configure a VN and enable IP Fabric forwarding. Launch 3 VMs across
            compute nodes on this VN. Configure AAP active-active mode on 2 VMIs.
            Ping the AAP IP from 3rd VM, ping should be successful and happen
            through underlay. Verify AAP IP is present on default routing
            instance as well.
        '''

        if (len(self.inputs.compute_ips) < 2):
             raise self.skipTest(
                "Skipping Test. At least 2 compute node required to run the test")

        if not self.inputs.fabric_gw_info:
             raise self.skipTest(
                "Skipping Test. Fabric gateway is required to run the test")


        # VN parameters
        vn = {'count':1,
              'vn1':{'subnet':'100.100.100.0/24', 'ip_fabric':True},
             }
        # VMI parameters
        vmi = {'count':3,
               'vmi1':{'vn': 'vn1', 'vip': '100.100.100.100', 'mode': 'active-active'},
               'vmi2':{'vn': 'vn1', 'vip': '100.100.100.100', 'mode': 'active-active'},
               'vmi3':{'vn': 'vn1'},
              }
        # VM parameters
        vm = {'count':3, 'launch_mode':'distribute',
              'vm1':{'vn':['vn1'], 'vmi':['vmi1']},
              'vm2':{'vn':['vn1'], 'vmi':['vmi2']},
              'vm3':{'vn':['vn1'], 'vmi':['vmi3']},
             }

        # Setup VNs, VMs as per user configuration
        ret_dict = self.setup_gw_less_fwd(vn=vn, vmi=vmi, vm=vm)

        vn_fixtures = ret_dict['vn_fixtures']
        vm_fixtures = ret_dict['vm_fixtures']
        vmi_fixtures = ret_dict['vmi_fixtures']

        # Policy parameters. Configuring a policy between between ip-fabric vn
        # and vn1 to allow communication between compute node and VMs in vn1.
        policy = {'count':1,
                  'p1': {
                      'rules': [
                            {
                            'direction':'<>',
                            'protocol':'any',
                            'source_network': 'default-domain:default-project:ip-fabric',
                            'dest_network':'vn1',
                            'src_ports':'any',
                            'dst_ports':'any'
                            },
                        ]
                    }
                  }

        # Configure policy as per user configuration
        policy_fixtures = self.setup_policy(policy=policy,
                                            vn_fixtures=vn_fixtures)
        ret_dict['policy_fixtures'] = policy_fixtures

        vIP = "100.100.100.100"
        # Verify AAP route in default routing instance in agent
        self.verify_route_ip_fabric_vn_in_agent(ret_dict=ret_dict, ip=vIP)

        # Verify AAP route in default routing instance in control node
        self.verify_route_ip_fabric_vn_in_control_node(ret_dict=ret_dict,
                                                       ip=vIP,test_fixture=ret_dict['vm_fixtures']['vm2'])
        # Configuring AAP on 2 VMs
        vm_list = [vm_fixtures['vm1'], vm_fixtures['vm2']]
        for vm in vm_list:
            output = vm.run_cmd_on_vm(
                ['sudo ifconfig eth0:10 ' + vIP + ' netmask 255.255.255.0'])

        # Verify IP Fabric forwarding functionality
        # Ping across VMs, ping from vhosts to VMs and VMs to vhsots
        ret_dict = self.verify_gw_less_fwd(ret_dict=ret_dict)

        # Pinging AAP from 3rd VM
        src_vm_fixture = vm_fixtures['vm3']
        src_vm_ip = src_vm_fixture.vm_ip
        result = src_vm_fixture.ping_with_certainty(vIP, count=2)

        if result:
            self.logger.info('Ping from VM: %s to VIP: %s is successful,'\
                             ' as expected' %(src_vm_ip, vIP))
        else:
            assert result, "Ping from VM: %s to VIP: %s is NOT successful" %(
                src_vm_ip, vIP)


        # Pinging AAP from compute nodes, ping should be successful
        compute_node_ips = set()
        for vm_fixture in list(vm_fixtures.values()):
            compute_node_ips.add(vm_fixture.get_compute_host())

        for compute_ip in compute_node_ips:
            result = self.ping_vm_from_vhost(compute_ip, vIP, count=2)
            if result:
                self.logger.info('Ping from vHost: %s to VIP: %s is successful,'\
                                 ' as expected' %(compute_ip, vIP))
            else:
                assert result, "Ping from VM: %s to VIP: %s is NOT successful" %(
                    compute_ip, vIP)

    # end test_gw_less_fwd_aap

    @preposttest_wrapper
    def test_gw_less_fwd_fip(self):
        '''
            Test Gateway less forwarding functionality with floating-ip.
            4 scenarios will be tested here.
            Scenario 1: IP Fabric is enabled on both the VNs (vn1 and vn2)
            Scenario 2: IP Fabric is enabled on vn1 and disabled on vn2
            Scenario 3: IP Fabric is disabled on vn1 and enabled on vn2
            Scenario 4: IP Fabric is disabled on both the VNs (vn1 and vn2)

            In all above cases, floating ip is created from vn1 and applied it
            on vn2 VM (vm2). Verify FIP is preesnt on default routing instance
            only when IP fabric is enabled on VN (vn1). Ping FIP from vm1 and
            ping should be successful all the cases.

        '''
        if (len(self.inputs.compute_ips) < 2):
             raise self.skipTest(
                "Skipping Test. At least 2 compute node required to run the test")

        if not self.inputs.fabric_gw_info:
             raise self.skipTest(
                "Skipping Test. Fabric gateway is required to run the test")


        # VN parameters. IP Fabric forwarding is enabled on both VNs
        vn = {'count':2,
              'vn1':{'subnet':get_random_cidr(), 'ip_fabric':True},
              'vn2':{'subnet':get_random_cidr(), 'ip_fabric':True},
             }
        # VMI parameters
        vmi = {'count':2,
               'vmi1':{'vn': 'vn1'},
               'vmi2':{'vn': 'vn2'},
              }

        # VM parameters
        vm = {'count':2, 'launch_mode':'distribute',
              'vm1':{'vn':['vn1'], 'vmi':['vmi1']},
              'vm2':{'vn':['vn2'], 'vmi':['vmi2']},
             }

        # Setup VNs, VMs as per user configuration
        ret_dict = self.setup_gw_less_fwd(vn=vn, vmi=vmi, vm=vm)

        vn_fixtures = ret_dict['vn_fixtures']
        vm_fixtures = ret_dict['vm_fixtures']
        vmi_fixtures = ret_dict['vmi_fixtures']

        # Policy parameters. Configuring a policy between between ip-fabric vn
        # and vn1 to allow communication between compute node and VMs in vn1.
        policy = {'count':1,
                  'p1': {
                      'rules': [
                            {
                            'direction':'<>',
                            'protocol':'any',
                            'source_network': 'default-domain:default-project:ip-fabric',
                            'dest_network':'vn1',
                            'src_ports':'any',
                            'dst_ports':'any'
                            },
                        ]
                    }
                  }

        # Configure policy as per user configuration
        policy_fixtures = self.setup_policy(policy=policy,
                                            vn_fixtures=vn_fixtures)
        ret_dict['policy_fixtures'] = policy_fixtures

        # Scenario 1: IP Fabric is enabled on both the VNs (vn1 and vn2)
        # Configuring FIP. FIP pool is created from vn1 and applied on vm2
        self.logger.info("-- SCENARIO: 1 --")
        self.logger.info("IP Fabric is enabled on both the VNs (vn1 and vn2)")
        vn_id = vn_fixtures['vn1'].vn_id
        vmi_id = vmi_fixtures['vmi2'].uuid
        (my_fip, fip_obj) = self.config_fip(ret_dict, vn_id, vmi_id)

        # Verify FIP route in default routing instance in agent
        self.verify_route_ip_fabric_vn_in_agent(ret_dict=ret_dict, ip=my_fip)

        # Verify FIP route in default routing instance in control node
        self.verify_route_ip_fabric_vn_in_control_node(ret_dict=ret_dict,
                                                       ip=my_fip, test_fixture=ret_dict['vm_fixtures']['vm2'])

        # Pinging FIP from VM1
        src_vm_fixture = vm_fixtures['vm1']
        src_vm_ip = src_vm_fixture.vm_ip
        result = src_vm_fixture.ping_with_certainty(my_fip, count=2)

        if result:
            self.logger.info('Ping from VM: %s to FIP: %s is successful, '\
                             'as expected' %(src_vm_ip, my_fip))
        else:
            assert result, "Ping from VM: %s to FIP: %s is NOT successful" %(
                src_vm_ip, my_fip)

        # Scenario 2: IP Fabric is enabled on vn1 and disabled on vn2
        # Now, remove IP fabric provider network configuration on vn2
        # FIP pool is from IP fabric forwarding VN (vn1)
        self.logger.info("-- Scanerio: 2 --")
        self.logger.info("IP Fabric is enabled on vn1 and disabled on vn2")
        vn2_fixture = vn_fixtures['vn2']
        ip_fab_vn_obj = self.get_ip_fab_vn()
        vn2_fixture.del_ip_fabric_provider_nw(ip_fab_vn_obj)

        time.sleep(2)

        # Verify FIP route in default routing instance in agent
        self.verify_route_ip_fabric_vn_in_agent(ret_dict=ret_dict, ip=my_fip)

        # Verify FIP route in default routing instance in control node
        self.verify_route_ip_fabric_vn_in_control_node(ret_dict=ret_dict,
                                                       ip=my_fip, test_fixture=ret_dict['vm_fixtures']['vm2'])

        result = src_vm_fixture.ping_with_certainty(my_fip, count=2)

        if result:
            self.logger.info('Ping from VM: %s to FIP: %s is successful, '\
                             'as expected' %(src_vm_ip, my_fip))
        else:
            assert result, "Ping from VM: %s to FIP: %s is NOT successful" %(
                src_vm_ip, my_fip)

        # Scenario 3: IP Fabric is disabled on vn1 and enabled on vn2
        # Now, remove IP fabric provider network configuration on vn2 and enable
        # on vn1
        self.logger.info("-- Scanerio: 3 --")
        self.logger.info("IP Fabric is disabled on vn1 and enabled on vn2")
        self.logger.info("Disable IP Fabric forwarding on VN: vn1")
        vn1_fixture = vn_fixtures['vn1']
        vn1_fixture.del_ip_fabric_provider_nw(ip_fab_vn_obj)

        self.logger.info("Enable IP Fabric forwarding on VN: vn2")
        vn2_fixture = vn_fixtures['vn2']
        vn2_fixture.set_ip_fabric_provider_nw(ip_fab_vn_obj)
        time.sleep(2)

        # Since FIP pool is from vn1, FIP should NOT be present in default
        # routing instance as IP Fabric is disabled on vn1

        # Verify FIP route is NOT in default routing instance in agent
        self.verify_route_ip_fabric_vn_in_agent(ret_dict=ret_dict, ip=my_fip,
                                                expectation=False)

        # Verify FIP route is NOT in default routing instance in control node
        self.verify_route_ip_fabric_vn_in_control_node(ret_dict=ret_dict,
                                                       ip=my_fip,
                                                       expectation=False,
                                                       test_fixture=ret_dict['vm_fixtures']['vm2'])

        result = src_vm_fixture.ping_with_certainty(my_fip, count=2)

        if result:
            self.logger.info('Ping from VM: %s to FIP: %s is successful, '\
                             'as expected' %(src_vm_ip, my_fip))
        else:
            assert result, "Ping from VM: %s to FIP: %s is NOT successful" %(
                src_vm_ip, my_fip)

        # Scenario 4: IP Fabric is disabled on both the VNs (vn1 and vn2)
        # Now, remove IP fabric provider networ both VNs
        self.logger.info("-- Scanerio: 4 --")
        self.logger.info("IP Fabric is disabled on both the VNs (vn1 and vn2)")
        self.logger.info("Disable IP Fabric forwarding on VN: vn2")
        vn2_fixture = vn_fixtures['vn2']
        vn2_fixture.del_ip_fabric_provider_nw(ip_fab_vn_obj)

        self.logger.info("Disable IP Fabric forwarding on VN: vn1")
        vn1_fixture = vn_fixtures['vn1']
        vn1_fixture.del_ip_fabric_provider_nw(ip_fab_vn_obj)
        time.sleep(2)

        # Since FIP pool is from vn1, FIP should be removed from default routing
        # instance as IP Fabric is deleted from vn1

        # Verify FIP route is NOT in default routing instance in agent
        self.verify_route_ip_fabric_vn_in_agent(ret_dict=ret_dict, ip=my_fip,
                                                expectation=False)

        # Verify FIP route is NOT in default routing instance in control node
        self.verify_route_ip_fabric_vn_in_control_node(ret_dict=ret_dict,
                                                       ip=my_fip,
                                                       expectation=False,
                                                       test_fixture=ret_dict['vm_fixtures']['vm2'])

        result = src_vm_fixture.ping_with_certainty(my_fip, count=2)

        if result:
            self.logger.info('Ping from VM: %s to FIP: %s is successful, '\
                             'as expected' %(src_vm_ip, my_fip))
        else:
            assert result, "Ping from VM: %s to FIP: %s is NOT successful" %(
                src_vm_ip, my_fip)


    # end test_gw_less_fwd_fip


    @preposttest_wrapper
    def test_gw_less_fwd_vhost0_policy(self):
        '''
            Test Gateway less forwarding with single VN and IP Fabric provider
            network when policy is enabled/disabled on vhost0 interface.
            IP Forwarding functionality should work when both policy is enabled
            and disabled on vhost0 VMI interfaces.
            IP Fbaric network is configured as provider network
            over vn1. Multiple VMs will be launched across compute nodes
            and ping between VMs should be successful and happen through
            underlay. Ping between vhosts to VMs should be successful and happen
            through underlay. Also, ping between VMs to vhosts also should be
            successful and should go through underlay.
        '''
        if (len(self.inputs.compute_ips) < 2):
             raise self.skipTest(
                "Skipping Test. At least 2 compute node required to run the test")

        if not self.inputs.fabric_gw_info:
             raise self.skipTest(
                "Skipping Test. Fabric gateway is required to run the test")


        # VN parameters. IP Fabric forwarding is enabled on vn1.
        vn = {'count':1,
              'vn1':{'subnet':get_random_cidr(), 'ip_fabric':True},
             }

        # VMI parameters
        vmi = {'count':2,
               'vmi1':{'vn': 'vn1'},
               'vmi2':{'vn': 'vn1'},
              }

        # VM parameters
        vm = {'count':2, 'launch_mode':'distribute',
              'vm1':{'vn':['vn1'], 'vmi':['vmi1']},
              'vm2':{'vn':['vn1'], 'vmi':['vmi2']},
             }

        # Setup VNs, VMs as per user configuration
        ret_dict = self.setup_gw_less_fwd(vn=vn, vmi=vmi, vm=vm)

        vn_fixtures = ret_dict['vn_fixtures']
        # Policy parameters. Configuring a policy between between ip-fabric vn
        # and vn1 to allow communication between compute node and VMs in vn1.
        policy = {'count':1,
                  'p1': {
                      'rules': [
                            {
                            'direction':'<>',
                            'protocol':'any',
                            'source_network': 'default-domain:default-project:ip-fabric',
                            'dest_network':'vn1',
                            'src_ports':'any',
                            'dst_ports':'any'
                            },
                        ]
                    }
                  }

        # Configure policy as per user configuration
        policy_fixtures = self.setup_policy(policy=policy,
                                            vn_fixtures=vn_fixtures)
        ret_dict['policy_fixtures'] = policy_fixtures

        # Enable policy on vhost0 VMI interfaces
        value = False
        self.disable_policy_on_vhost0(value)

        vn_fixtures = ret_dict['vn_fixtures']

        # Verify Gateway less forward functionality. As IP Fabric forwarding
        # is enabled on vn1, traffic should go through underlay
        self.verify_gw_less_fwd(ret_dict)

        # Now, remove IP fabric provider network configuration on vn1
        vn1_fixture = vn_fixtures['vn1']
        ip_fab_vn_obj = self.get_ip_fab_vn()
        vn1_fixture.del_ip_fabric_provider_nw(ip_fab_vn_obj)

        time.sleep(2)

        # Verify Gateway less forward functionality. As IP Fabric forwarding
        # is disabled on vn1, traffic should go through overlay
        self.verify_gw_less_fwd(ret_dict=ret_dict)

        # Disable back policy on vhost0 VMI interfaces
        value = True
        self.disable_policy_on_vhost0(value)

    # end test_gw_less_fwd_vhost0_policy



    @preposttest_wrapper
    def test_gw_less_fwd_flat_subnet_single_vn(self):
        '''
            Test Gateway less forwarding with flat-subnet Ipam.
            VN is configured to use flat-subnet ipam. IP Fbaric network is
            configured as provider network over vn1.
            Multiple VMs will be launched across compute nodes
            and ping between VMs should be successful and happen through
            underlay.
        '''
        if (len(self.inputs.compute_ips) < 2):
             raise self.skipTest(
                "Skipping Test. At least 2 compute node required to run the test")

        if not self.inputs.fabric_gw_info:
             raise self.skipTest(
                "Skipping Test. Fabric gateway is required to run the test")

        # Ipam parameters
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

        # Setup flat subnet Ipam as per configuration
        ipam_obj = self.setup_ipam(ipam)

        # VN parameters. IP Fabric forwarding is enabled on vn1.
        vn = {'count':1,
              'vn1':{
                    'address_allocation_mode':'flat-subnet-only',
                    'ip_fabric':True, 'ipam_fq_name': ipam_obj.fq_name,
                    },
             }

        # VMI parameters
        vmi = {'count':2,
               'vmi1':{'vn': 'vn1'},
               'vmi2':{'vn': 'vn1'},
              }

        # VM parameters
        vm = {'count':2, 'launch_mode':'distribute',
              'vm1':{'vn':['vn1'], 'vmi':['vmi1']},
              'vm2':{'vn':['vn1'], 'vmi':['vmi2']},
             }

        # Setup VNs, VMs as per user configuration
        ret_dict = self.setup_gw_less_fwd(vn=vn, vmi=vmi, vm=vm)

        vn_fixtures = ret_dict['vn_fixtures']

        # Verify Gateway less forward functionality. As IP Fabric forwarding
        # is enabled on vn1, traffic should go through underlay between VMs
        # As there is no explicit policy to allow traffic between VN and
        # "ip-fbric" network, ping from vhost to VM and VM to vhost should fail

        self.logger.info("-- SCENARIO: 1 Verifying gateway less forward "\
                         "functionality without explicit policy --")
        self.verify_gw_less_fwd(ret_dict)

        # Policy parameters. Configuring a policy between between ip-fabric vn
        # and vn1 to allow communication between compute node and VMs in vn1.
        policy = {'count':1,
                  'p1': {
                      'rules': [
                            {
                            'direction':'<>',
                            'protocol':'any',
                            'source_network': 'default-domain:default-project:ip-fabric',
                            'dest_network':'vn1',
                            'src_ports':'any',
                            'dst_ports':'any'
                            },
                        ]
                    }
                  }

        # Configure policy as per user configuration
        policy_fixtures = self.setup_policy(policy=policy,
                                            vn_fixtures=vn_fixtures)
        ret_dict['policy_fixtures'] = policy_fixtures

        # Verify Gateway less forward functionality. As IP Fabric forwarding
        # is enabled on vn1, traffic should go through underlay. Also, as
        # there is explicit policy to allow traffic between VN and "ip-fabric"
        # network, ping from vhost to VM and VM to vhost should be successful.

        self.logger.info("-- SCENARIO: 2 Verifying gateway less forward "\
                         "functionality with explicit policy --")
        self.verify_gw_less_fwd(ret_dict)

        # Now, remove IP fabric provider network configuration on vn1
        vn1_fixture = vn_fixtures['vn1']
        ip_fab_vn_obj = self.get_ip_fab_vn()
        vn1_fixture.del_ip_fabric_provider_nw(ip_fab_vn_obj)

        time.sleep(2)

        # Verify Gateway less forward functionality. As IP Fabric forwarding
        # is disabled on vn1, traffic should go through overlay

        self.logger.info("-- SCENARIO: 3 Verifying gateway less forward "\
                         "functionality when IP farwarding is disabled--")
        self.verify_gw_less_fwd(ret_dict = ret_dict)

    # end test_gw_less_fwd_flat_subnet_single_vn

    @preposttest_wrapper
    def test_gw_less_fwd_flat_subnet_multi_vn(self):
        '''
            Test Gateway less forwarding with flat-subnet Ipam and with multiple
            VNs. Multiple VNs are configured to use flat-subnet ipam.
            IP Fbaric network is configured as provider network
            over vn1 and vn2. Multiple VMs will be launched across compute nodes
            and policy is enabled between VNs. Ping between VMs should be
            successful and happen through underlay. Ping between vhosts to VMs
            should be successful and happen through underlay. Also, ping between
            VMs to vhosts also should be successful and should go through underlay.
            Also, verify when policy is disabled between vn1 and vn2,
            communication should not takes place.
        '''

        if (len(self.inputs.compute_ips) < 2):
             raise self.skipTest(
                "Skipping Test. At least 2 compute node required to run the test")

        if not self.inputs.fabric_gw_info:
             raise self.skipTest(
                "Skipping Test. Fabric gateway is required to run the test")

        # Ipam parameters
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

        # Setup flat subnet Ipam as per configuration
        ipam_obj = self.setup_ipam(ipam)

        # VN parameters. IP Fabric forwarding is enabled on vn1.
        vn = {'count':2,
              'vn1':{
                    'address_allocation_mode':'flat-subnet-only',
                    'ip_fabric':True, 'ipam_fq_name': ipam_obj.fq_name,
                    },
              'vn2':{
                    'address_allocation_mode':'flat-subnet-only',
                    'ip_fabric':True, 'ipam_fq_name': ipam_obj.fq_name,
                    },
             }

        # VMI parameters. 2 VMIs per VN.
        vmi = {'count':4,
               'vmi1':{'vn': 'vn1'},
               'vmi2':{'vn': 'vn1'},
               'vmi3':{'vn': 'vn2'},
               'vmi4':{'vn': 'vn2'},
              }

        # VM parameters. 2 VMs are launched across compute nodes.
        vm = {'count':4, 'launch_mode':'distribute',
              'vm1':{'vn':['vn1'], 'vmi':['vmi1']},
              'vm2':{'vn':['vn1'], 'vmi':['vmi2']},
              'vm3':{'vn':['vn2'], 'vmi':['vmi3']},
              'vm4':{'vn':['vn2'], 'vmi':['vmi4']},
             }


        # Setup VNs, VMs as per user configuration
        ret_dict = self.setup_gw_less_fwd(vn=vn, vmi=vmi, vm=vm)

        vn_fixtures = ret_dict['vn_fixtures']

        # Verify Gateway less forward functionality with out policy
        # As IP Fabric provider network is configured on vn1 and vn2
        # and policy is disabled Traffic should go through underlay
        # between VMs within same VN and traffic should fail across VNs

        self.logger.info("-- SCENARIO: 1 Verifying gateway less forward "\
                         "functionality without explicit policy --")
        self.verify_gw_less_fwd(ret_dict = ret_dict)

        # Policy parameters. Configuring policy between vn1 and vn2 to allow
        # the traffic. Also, policy between ip-fabric vn and vn1 needs to be
        # configured to allow communication between compute node and VMs in vn1.
        # Similarly for vn2 as well.
        policy = {'count':3,
                  'p1': {
                      'rules': [
                            {
                            'direction':'<>',
                            'protocol':'any',
                            'source_network': 'vn1',
                            'dest_network':'vn2',
                            'src_ports':'any',
                            'dst_ports':'any'
                            },
                        ]
                    },
                  'p2': {
                      'rules': [
                            {
                            'direction':'<>',
                            'protocol':'any',
                            'source_network': 'default-domain:default-project:ip-fabric',
                            'dest_network':'vn1',
                            'src_ports':'any',
                            'dst_ports':'any'
                            },
                        ]
                    },
                  'p3': {
                      'rules': [
                            {
                            'direction':'<>',
                            'protocol':'any',
                            'source_network': 'default-domain:default-project:ip-fabric',
                            'dest_network':'vn2',
                            'src_ports':'any',
                            'dst_ports':'any'
                            },
                        ]
                    }
                }

        # Configure policy as per user configuration
        policy_fixtures = self.setup_policy(policy=policy,
                                            vn_fixtures=vn_fixtures)
        ret_dict['policy_fixtures'] = policy_fixtures

        # Verify Gateway less forward functionality with policy
        # As IP Fabric provider network is configured on vn1 and vn2
        # Traffic should go through underlay and traffic across VNs should pass

        self.logger.info("-- SCENARIO: 2 Verifying gateway less forward "\
                         "functionality with explicit policy --")
        self.verify_gw_less_fwd(ret_dict = ret_dict)

        # Now, remove IP fabric provider network configuration on vn1 and vn2
        vn1_fixture = vn_fixtures['vn1']
        vn2_fixture = vn_fixtures['vn2']
        ip_fab_vn_obj = self.get_ip_fab_vn()

        self.logger.info("Deleting IP Fabric forwarding on VN: vn1")
        vn1_fixture.del_ip_fabric_provider_nw(ip_fab_vn_obj)
        self.logger.info("Deleting IP Fabric forwarding on VN: vn1")
        vn2_fixture.del_ip_fabric_provider_nw(ip_fab_vn_obj)
        time.sleep(2)

        # Since IP fabric provider network configuration on vn1 and vn2
        # is disabled traffic should go through overlay, instead of underlay

        self.logger.info("-- SCENARIO: 3 Verifying gateway less forward "\
                         "functionality when IP farwarding is disabled--")
        self.verify_gw_less_fwd(ret_dict = ret_dict)

    # end test_gw_less_fwd_flat_subnet_multi_vn


    @preposttest_wrapper
    def test_gw_less_fwd_flat_subnet_ipfab_vn_and_cust_vn(self):
        '''
            Test Gateway less forwarding with flat-subnet VN and custom VN.
            vn1 is configured to use flat-subnet ipam. IP Fbaric network is
            configured as provider network on vn1. vn2 is custom VN and not
            configured with IP fabric provider network.

            Policy is configured between vn1 and vn2 to allow the traffic.
            Multiple VMs will be launched across compute nodes
            and ping between VMs should be successful and happen through
            overlay .
        '''

        if (len(self.inputs.compute_ips) < 2):
             raise self.skipTest(
                "Skipping Test. At least 2 compute node required to run the test")

        if not self.inputs.fabric_gw_info:
             raise self.skipTest(
                "Skipping Test. Fabric gateway is required to run the test")

        # Ipam parameters
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

        # Setup flat subnet Ipam as per configuration
        ipam_obj = self.setup_ipam(ipam)

        # VN parameters. IP Fabric forwarding is enabled on vn1 and not on vn2.
        vn = {'count':2,
              'vn1':{
                    'address_allocation_mode':'flat-subnet-only',
                    'ip_fabric':True, 'ipam_fq_name': ipam_obj.fq_name,
                    },
              'vn2':{'subnet':'20.20.20.0/24', 'ip_fabric':False},
             }
        # VMI parameters
        vmi = {'count':4,
               'vmi1':{'vn': 'vn1'},
               'vmi2':{'vn': 'vn1'},
               'vmi3':{'vn': 'vn2'},
               'vmi4':{'vn': 'vn2'},
              }

        # VM parameters
        vm = {'count':4, 'launch_mode':'distribute',
              'vm1':{'vn':['vn1'], 'vmi':['vmi1']},
              'vm2':{'vn':['vn1'], 'vmi':['vmi2']},
              'vm3':{'vn':['vn2'], 'vmi':['vmi3']},
              'vm4':{'vn':['vn2'], 'vmi':['vmi4']},
             }

        # Setup VNs, VMs as per user configuration
        ret_dict = self.setup_gw_less_fwd(vn=vn, vmi=vmi, vm=vm)

        vn_fixtures = ret_dict['vn_fixtures']

        # Policy parameters. Configuring policy between vn1 and vn2 to allow
        # the traffic. Also, policy between ip-fabric vn and vn1 needs to be
        # configured to allow communication between compute node and VMs in vn1.
        policy = {'count':2,
                  'p1': {
                      'rules': [
                            {
                            'direction':'<>',
                            'protocol':'any',
                            'source_network': 'vn1',
                            'dest_network':'vn2',
                            'src_ports':'any',
                            'dst_ports':'any'
                            },
                        ]
                    },
                  'p2': {
                      'rules': [
                            {
                            'direction':'<>',
                            'protocol':'any',
                            'source_network': 'default-domain:default-project:ip-fabric',
                            'dest_network':'vn1',
                            'src_ports':'any',
                            'dst_ports':'any'
                            },
                        ]
                    },
                  }

        # Configure policy between vn1 and vn2
        policy_fixtures = self.setup_policy(policy=policy,
                                            vn_fixtures=vn_fixtures)
        ret_dict['policy_fixtures'] = policy_fixtures

        # As IP Fabric forwarding is enabled on vn1 and not vn2 and policy is
        # configured to allow traffic between vn1 and vn2. Traffic should go
        # through overlay between VNs
        ret_dict = self.verify_gw_less_fwd(ret_dict=ret_dict)

    # end test_gw_less_fwd_flat_subnet_ipfab_vn_and_cust_vn

    @preposttest_wrapper
    def test_gw_less_fwd_flat_subnet_aap(self):
        '''
            Test Gateway less forwarding functionality with flat-subnet VN and
            allowed address pair. VN is configured to use flat-subnet (flat
            ipam) and IP Fabric forwarding is enabled. Launch 3 VMs across
            compute nodes on this VN. Configure AAP active-active mode on 2 VMIs.
            Ping the AAP IP from 3rd VM, ping should be successful and happen
            through underlay. Verify AAP IP is present on default routing
            instance as well.
        '''

        if (len(self.inputs.compute_ips) < 2):
             raise self.skipTest(
                "Skipping Test. At least 2 compute node required to run the test")

        if not self.inputs.fabric_gw_info:
             raise self.skipTest(
                "Skipping Test. Fabric gateway is required to run the test")

        # Ipam parameters
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

        # Setup flat subnet Ipam as per configuration
        ipam_obj = self.setup_ipam(ipam)

        # VN parameters. IP Fabric forwarding is enabled on vn1.
        vn = {'count':1,
              'vn1':{
                    'address_allocation_mode':'flat-subnet-only',
                    'ip_fabric':True, 'ipam_fq_name': ipam_obj.fq_name,
                    },
             }

        # VMI parameters
        vmi = {'count':3,
               'vmi1':{'vn': 'vn1', 'vip': '10.204.218.155', 'mode': 'active-active'},
               'vmi2':{'vn': 'vn1', 'vip': '10.204.218.155', 'mode': 'active-active'},
               'vmi3':{'vn': 'vn1'},
              }

        # VM parameters
        vm = {'count':3, 'launch_mode':'distribute',
              'vm1':{'vn':['vn1'], 'vmi':['vmi1']},
              'vm2':{'vn':['vn1'], 'vmi':['vmi2']},
              'vm3':{'vn':['vn1'], 'vmi':['vmi3']},
             }

        # Setup VNs, VMs as per user configuration
        ret_dict = self.setup_gw_less_fwd(vn=vn, vmi=vmi, vm=vm)

        # Policy parameters. Configuring a policy between between ip-fabric vn
        # and vn1 to allow communication between compute node and VMs in vn1.
        policy = {'count':1,
                  'p1': {
                      'rules': [
                            {
                            'direction':'<>',
                            'protocol':'any',
                            'source_network': 'default-domain:default-project:ip-fabric',
                            'dest_network':'vn1',
                            'src_ports':'any',
                            'dst_ports':'any'
                            },
                        ]
                    }
                  }

        vn_fixtures = ret_dict['vn_fixtures']
        vm_fixtures = ret_dict['vm_fixtures']
        vmi_fixtures = ret_dict['vmi_fixtures']


        # Configure policy as per user configuration
        policy_fixtures = self.setup_policy(policy=policy,
                                            vn_fixtures=vn_fixtures)
        ret_dict['policy_fixtures'] = policy_fixtures

        vIP = "10.204.218.155"
        # Verify AAP route in default routing instance in agent
        self.verify_route_ip_fabric_vn_in_agent(ret_dict=ret_dict, ip=vIP)

        # Verify AAP route in default routing instance in control node
        self.verify_route_ip_fabric_vn_in_control_node(ret_dict=ret_dict,
                                                       ip=vIP, test_fixture=ret_dict['vm_fixtures']['vm2'])

        # Configuring AAP on 2 VMs
        vm_list = [vm_fixtures['vm1'], vm_fixtures['vm2']]
        for vm in vm_list:
            output = vm.run_cmd_on_vm(
                ['sudo ifconfig eth0:10 ' + vIP + ' netmask 255.255.255.0'])

        # Verify IP Fabric forwarding functionality
        # Ping across VMs, ping from vhosts to VMs and VMs to vhsots
        ret_dict = self.verify_gw_less_fwd(ret_dict=ret_dict)

        # Pinging AAP from 3rd VM
        src_vm_fixture = vm_fixtures['vm3']
        src_vm_ip = src_vm_fixture.vm_ip
        result = src_vm_fixture.ping_with_certainty(vIP, count=2)

        if result:
            self.logger.info('Ping from VM: %s to VIP: %s is successful,'\
                             ' as expected' %(src_vm_ip, vIP))
        else:
            assert result, "Ping from VM: %s to VIP: %s is NOT successful" %(
                src_vm_ip, vIP)


        # Pinging AAP from compute nodes, ping should be successful
        compute_node_ips = set()
        for vm_fixture in list(vm_fixtures.values()):
            compute_node_ips.add(vm_fixture.get_compute_host())

        for compute_ip in compute_node_ips:
            result = self.ping_vm_from_vhost(compute_ip, vIP, count=2)
            if result:
                self.logger.info('Ping from vHost: %s to VIP: %s is successful,'\
                                 ' as expected' %(compute_ip, vIP))
            else:
                assert result, "Ping from VM: %s to VIP: %s is NOT successful" %(
                    compute_ip, vIP)

    # end test_gw_less_fwd_flat_subnet_aap
    @preposttest_wrapper
    def test_gw_less_fwd_flat_subnet_fip(self):
        '''
            Test Gateway less forwarding functionality with flat-subnet VN and
            floating-ip. VNs are configured to use flat-subnet (flat ipam).
            4 scenarios will be tested here.
            Scenario 1: IP Fabric is enabled on both the VNs (vn1 and vn2)
            Scenario 2: IP Fabric is enabled on vn1 and disabled on vn2
            Scenario 3: IP Fabric is disabled on vn1 and enabled on vn2
            Scenario 4: IP Fabric is disabled on both the VNs (vn1 and vn2)

            In all above cases, floating ip is created from vn1 and applied it
            on vn2 VM (vm2). Verify FIP is preesnt on default routing instance
            only when IP fabric is enabled on VN (vn1). Ping FIP from vm1 and
            ping should be successful all the cases.

        '''

        if (len(self.inputs.compute_ips) < 2):
             raise self.skipTest(
                "Skipping Test. At least 2 compute node required to run the test")

        if not self.inputs.fabric_gw_info:
             raise self.skipTest(
                "Skipping Test. Fabric gateway is required to run the test")

        # Ipam parameters
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

        # Setup flat subnet Ipam as per configuration
        ipam_obj = self.setup_ipam(ipam)

        # VN parameters. IP Fabric forwarding is enabled on vn1.
        vn = {'count':2,
              'vn1':{
                    'address_allocation_mode':'flat-subnet-only',
                    'ip_fabric':True, 'ipam_fq_name': ipam_obj.fq_name,
                    },
              'vn2':{
                    'address_allocation_mode':'flat-subnet-only',
                    'ip_fabric':True, 'ipam_fq_name': ipam_obj.fq_name,
                    },
             }

        # VMI parameters
        vmi = {'count':2,
               'vmi1':{'vn': 'vn1'},
               'vmi2':{'vn': 'vn2'},
              }

        # VM parameters
        vm = {'count':2, 'launch_mode':'distribute',
              'vm1':{'vn':['vn1'], 'vmi':['vmi1']},
              'vm2':{'vn':['vn2'], 'vmi':['vmi2']},
             }

        # Setup VNs, VMs as per user configuration
        ret_dict = self.setup_gw_less_fwd(vn=vn, vmi=vmi, vm=vm)

        vn_fixtures = ret_dict['vn_fixtures']
        vm_fixtures = ret_dict['vm_fixtures']
        vmi_fixtures = ret_dict['vmi_fixtures']

        # Policy parameters. Configuring a policy between between ip-fabric vn
        # and vn1 to allow communication between compute node and VMs in vn1.
        policy = {'count':1,
                  'p1': {
                      'rules': [
                            {
                            'direction':'<>',
                            'protocol':'any',
                            'source_network': 'default-domain:default-project:ip-fabric',
                            'dest_network':'vn1',
                            'src_ports':'any',
                            'dst_ports':'any'
                            },
                        ]
                    }
                  }

        # Configure policy as per user configuration
        policy_fixtures = self.setup_policy(policy=policy,
                                            vn_fixtures=vn_fixtures)
        ret_dict['policy_fixtures'] = policy_fixtures

        # Scenario 1: IP Fabric is enabled on both the VNs (vn1 and vn2)
        # Configuring FIP. FIP pool is created from vn1 and applied on vm2
        self.logger.info("-- SCENARIO: 1 --")
        self.logger.info("IP Fabric is enabled on both the VNs (vn1 and vn2)")
        vn_id = vn_fixtures['vn1'].vn_id
        vmi_id = vmi_fixtures['vmi2'].uuid
        (my_fip, fip_obj) = self.config_fip(ret_dict, vn_id, vmi_id,
                                            my_fip = "10.204.218.155")

        # Verify FIP route in default routing instance in agent
        self.verify_route_ip_fabric_vn_in_agent(ret_dict=ret_dict, ip=my_fip)

        # Verify FIP route in default routing instance in control node
        self.verify_route_ip_fabric_vn_in_control_node(ret_dict=ret_dict,
                                                       ip=my_fip, test_fixture=ret_dict['vm_fixtures']['vm2'])

        # Pinging FIP from VM1
        src_vm_fixture = vm_fixtures['vm1']
        src_vm_ip = src_vm_fixture.vm_ip
        result = src_vm_fixture.ping_with_certainty(my_fip, count=2)

        if result:
            self.logger.info('Ping from VM: %s to FIP: %s is successful, '\
                             'as expected' %(src_vm_ip, my_fip))
        else:
            assert result, "Ping from VM: %s to FIP: %s is NOT successful" %(
                src_vm_ip, my_fip)

        # Scenario 2: IP Fabric is enabled on vn1 and disabled on vn2
        # Now, remove IP fabric provider network configuration on vn2
        # FIP pool is from IP fabric forwarding VN (vn1)
        self.logger.info("-- Scanerio: 2 --")
        self.logger.info("IP Fabric is enabled on vn1 and disabled on vn2")
        vn2_fixture = vn_fixtures['vn2']
        ip_fab_vn_obj = self.get_ip_fab_vn()
        vn2_fixture.del_ip_fabric_provider_nw(ip_fab_vn_obj)

        time.sleep(2)

        # Verify FIP route in default routing instance in agent
        self.verify_route_ip_fabric_vn_in_agent(ret_dict=ret_dict, ip=my_fip)

        # Verify FIP route in default routing instance in control node
        self.verify_route_ip_fabric_vn_in_control_node(ret_dict=ret_dict,
                                                       ip=my_fip, test_fixture=ret_dict['vm_fixtures']['vm2'])

        result = src_vm_fixture.ping_with_certainty(my_fip, count=2)

        if result:
            self.logger.info('Ping from VM: %s to FIP: %s is successful, '\
                             'as expected' %(src_vm_ip, my_fip))
        else:
            assert result, "Ping from VM: %s to FIP: %s is NOT successful" %(
                src_vm_ip, my_fip)

        # Scenario 3: IP Fabric is disabled on vn1 and enabled on vn2
        # Now, remove IP fabric provider network configuration on vn2 and enable
        # on vn1
        self.logger.info("-- Scanerio: 3 --")
        self.logger.info("IP Fabric is disabled on vn1 and enabled on vn2")
        self.logger.info("Disable IP Fabric forwarding on VN: vn1")
        vn1_fixture = vn_fixtures['vn1']
        vn1_fixture.del_ip_fabric_provider_nw(ip_fab_vn_obj)

        self.logger.info("Enable IP Fabric forwarding on VN: vn2")
        vn2_fixture = vn_fixtures['vn2']
        vn2_fixture.set_ip_fabric_provider_nw(ip_fab_vn_obj)
        time.sleep(2)

        # Since FIP pool is from vn1, FIP should NOT be present in default
        # routing instance as IP Fabric is disabled on vn1

        # Verify FIP route is NOT in default routing instance in agent
        self.verify_route_ip_fabric_vn_in_agent(ret_dict=ret_dict, ip=my_fip,
                                                expectation=False)

        # Verify FIP route is NOT in default routing instance in control node
        self.verify_route_ip_fabric_vn_in_control_node(ret_dict=ret_dict,
                                                       ip=my_fip,
                                                       expectation=False,
                                                       test_fixture=ret_dict['vm_fixtures']['vm2'])
        result = src_vm_fixture.ping_with_certainty(my_fip, count=2)

        if result:
            self.logger.info('Ping from VM: %s to FIP: %s is successful, '\
                             'as expected' %(src_vm_ip, my_fip))
        else:
            assert result, "Ping from VM: %s to FIP: %s is NOT successful" %(
                src_vm_ip, my_fip)

        # Scenario 4: IP Fabric is disabled on both the VNs (vn1 and vn2)
        # Now, remove IP fabric provider networ both VNs
        self.logger.info("-- Scanerio: 4 --")
        self.logger.info("IP Fabric is disabled on both the VNs (vn1 and vn2)")
        self.logger.info("Disable IP Fabric forwarding on VN: vn2")
        vn2_fixture = vn_fixtures['vn2']
        vn2_fixture.del_ip_fabric_provider_nw(ip_fab_vn_obj)

        self.logger.info("Disable IP Fabric forwarding on VN: vn1")
        vn1_fixture = vn_fixtures['vn1']
        vn1_fixture.del_ip_fabric_provider_nw(ip_fab_vn_obj)
        time.sleep(2)

        # Since FIP pool is from vn1, FIP should be removed from default routing
        # instance as IP Fabric is deleted from vn1

        # Verify FIP route is NOT in default routing instance in agent
        self.verify_route_ip_fabric_vn_in_agent(ret_dict=ret_dict, ip=my_fip,
                                                expectation=False)

        # Verify FIP route is NOT in default routing instance in control node
        self.verify_route_ip_fabric_vn_in_control_node(ret_dict=ret_dict,
                                                       ip=my_fip,
                                                       expectation=False,
                                                       test_fixture=ret_dict['vm_fixtures']['vm2'])

        result = src_vm_fixture.ping_with_certainty(my_fip, count=2)

        if result:
            self.logger.info('Ping from VM: %s to FIP: %s is successful, '\
                             'as expected' %(src_vm_ip, my_fip))
        else:
            assert result, "Ping from VM: %s to FIP: %s is NOT successful" %(
                src_vm_ip, my_fip)


    # end test_gw_less_fwd_flat_subnet_fip


    def test_gw_less_fwd_single_vn_ipv6(self):
        '''
        Description:  Validate Ping between 3 VMs in the same VN.
        Test steps:
               1. Create a VN and Enable IP Fabric forwarding
               2. Launch 3 VMs (Ipv6) in it.
               3. Ping between VMs

        Pass criteria: Ping between the VMs should go thru fine.
        '''
        self.inputs.set_af('v6')

        # Provision underlay gateway
        self.provision_underlay_gw()

        vn1_name = get_random_name('vn30')
        vn1_vm1_name = get_random_name('vm1')
        vn1_vm2_name = get_random_name('vm2')
        vn1_vm3_name = get_random_name('vm3')

        # Creating a VN with IP Forwarding enabled
        vn1_fixture = self.create_vn(vn_name=vn1_name,orch=self.orchestrator,
                                     ip_fabric=True)

        # Launching 3 VMs
        vm1_fixture = self.create_vm(vn_fixture=vn1_fixture,
                                     vm_name=vn1_vm1_name,orch=self.orchestrator)
        vm2_fixture = self.create_vm(vn_ids=[vn1_fixture.uuid],
                                     vm_name=vn1_vm2_name)
        vm3_fixture = self.create_vm(vn_ids=[vn1_fixture.uuid],
                                     vm_name=vn1_vm3_name)

        assert vm1_fixture.wait_till_vm_is_up()
        assert vm2_fixture.wait_till_vm_is_up()
        assert vm3_fixture.wait_till_vm_is_up()

        assert vm1_fixture.ping_with_certainty(dst_vm_fixture=vm2_fixture),\
            "Ping from %s to %s failed" % (vn1_vm1_name, vn1_vm2_name)
        assert vm2_fixture.ping_with_certainty(dst_vm_fixture=vm1_fixture),\
            "Ping from %s to %s failed" % (vn1_vm2_name, vn1_vm1_name)
        assert vm1_fixture.ping_with_certainty(dst_vm_fixture=vm3_fixture),\
            "Ping from %s to %s failed" % (vn1_vm1_name, vn1_vm3_name)
        assert vm3_fixture.ping_with_certainty(dst_vm_fixture=vm1_fixture),\
            "Ping from %s to %s failed" % (vn1_vm3_name, vn1_vm1_name)

        return True
    # end test_gw_less_fwd_single_vn_ipv6

    def test_gw_less_fwd_broadcast_multicast(self):
        '''
        Description:  Validate Ping on subnet broadcast,link local multucast,network broadcast.
        Test steps:
                1. Configure a VN with IP Forwarding enabled
                2. Send ICMP traffic stream to subnet broadcast, multicast and all-broadcast address,
                3. Enable response to broadcasts on the destination VMs.
        Pass criteria: There should be no packet loss and all the three destination VMs should see the ICMP traffic.
        '''

        # Provision underlay gateway
        self.provision_underlay_gw()

        result = True
        ping_count = '2'
        vn1_subnets = ['30.1.1.0/24']
        vn1_vm1_name = get_random_name('vn1_vm1')
        vn1_vm2_name = get_random_name('vn1_vm2')
        vn1_vm3_name = get_random_name('vn1_vm3')
        vn1_vm4_name = get_random_name('vn1_vm4')

        # Configuring a VN with IP Forwarding enabled
        vn1_fixture = self.create_vn(vn_subnets=vn1_subnets, ip_fabric=True)

        # Launching 4 VMs
        vm1_fixture = self.create_vm(vn1_fixture, vm_name=vn1_vm1_name)
        vm2_fixture = self.create_vm(vn1_fixture, vm_name=vn1_vm2_name)
        vm3_fixture = self.create_vm(vn1_fixture, vm_name=vn1_vm3_name)
        vm4_fixture = self.create_vm(vn1_fixture, vm_name=vn1_vm4_name)
        assert vm1_fixture.wait_till_vm_is_up()
        assert vm2_fixture.wait_till_vm_is_up()
        assert vm3_fixture.wait_till_vm_is_up()
        assert vm4_fixture.wait_till_vm_is_up()

        # Geting the VM ips
        vm1_ip = vm1_fixture.vm_ip
        vm2_ip = vm2_fixture.vm_ip
        vm3_ip = vm3_fixture.vm_ip
        vm4_ip = vm4_fixture.vm_ip
        ip_list = [vm1_ip, vm2_ip, vm3_ip, vm4_ip]

        # Broadcast IP adress
        bcast_ip = str(IPNetwork(vn1_subnets[0]).broadcast)


        list_of_ip_to_ping = [bcast_ip, '224.0.0.1', '255.255.255.255']

        # Configure VM to respond to ICMP broadcasts
        cmd = ['echo 0 > /proc/sys/net/ipv4/icmp_echo_ignore_broadcasts']

        vm_fixtures = [vm1_fixture, vm2_fixture, vm3_fixture, vm4_fixture]
        for vm in vm_fixtures:
            self.logger.debug('Running cmd for %s' % vm.vm_name)
            for i in range(3):
                try:
                    self.logger.debug("Retry %s" % (i))
                    ret = vm.run_cmd_on_vm(cmds=cmd, as_sudo=True)
                    if not ret:
                        for vn in vm.vn_fq_names:
                            vm.ping_vm_from_host(vn)
                        raise Exception
                except Exception as e:
                    time.sleep(5)
                    self.logger.exception("Got exception as %s" % (e))
                else:
                    break

        # Pinging Broadcast/Multicast adresses
        for dst_ip in list_of_ip_to_ping:
            self.logger.info('pinging from %s to %s' % (vm1_ip, dst_ip))

            # pinging from Vm1 to subnet broadcast
            ping_output = vm1_fixture.ping_to_ip(
                dst_ip, return_output=True, count=ping_count, other_opt='-b')
            self.logger.info("ping output : \n %s" % (ping_output))

            expected_result = ' 0% packet loss'
            if expected_result not in ping_output:
                self.logger.error('Expected 0% packet loss!')
                self.logger.error('Ping result : %s' % (ping_output))
                result = result and False

            # getting count of ping response from each vm
            string_count_dict = {}
            string_count_dict = get_string_match_count(ip_list, ping_output)
            self.logger.info("output %s" % (string_count_dict))
            self.logger.info(
                "There should be atleast 4 echo reply from each ip")
            for k in ip_list:
                if (ping_output.count('DUP') >= 3):
                    self.logger.info('Seen replies from all vms..')
                else:
                    self.logger.info('NOT Seen replies from all vms..')
                    result = result and False

        if not result:
            self.logger.error('There were errors. Verifying VM fixtures')
            assert vm1_fixture.verify_on_setup()
            assert vm2_fixture.verify_on_setup()
            assert vm3_fixture.verify_on_setup()
            assert vm4_fixture.verify_on_setup()
        return True
    # end test_gw_less_fwd_broadcast_multicast

    @skip_because(min_nodes=2)
    @preposttest_wrapper
    def test_gw_less_fwd_fip_4518_with_FIP(self):
        '''
            Test Gateway less forwarding functionality with floating-ip to cover Riot Games CEM-4518 with FIP
            Min Topology  cn1-vm1--+        
                            VN1    |       +--vm4--cn2 
                          cn2-vm2--+ --FIP | VN2 
                            VN1    |       +--------- 
                          cn1-vm3--+

            Scenario 1:IP Fabric is enabled on vn1 and vn2 with fip from Vn1
                     1.ping between the vms with in vn1 should go through underlay
                     2.ping from vm1 to vhost0 should be through underlay
                     3.ping from local host to fip should be through underlay
                     4.ping from remote compute to fip should be through underlay
                     5.ping to fip from vn2 vm should be successful with policy bteween vn1 and vn2
 
            In all above cases, floating ip is created from vn1 and applied it
            on vn1 VMs . Verify FIP is preesnt on default routing instance
            only when IP fabric is enabled on VN (vn1). 
        '''
        # VN parameters. IP Fabric forwarding is enabled on both VNs Initially
        vn = {'count':2,
              'vn1':{'subnet':get_random_cidr(), 'ip_fabric':True},
              'vn2':{'subnet':get_random_cidr(), 'ip_fabric':True},
             }
        # VMI parameters,vmis are distributed among the compute nodes
        vmi = {'count':4, 'launch_mode':'distribute',
               'vmi1':{'vn': 'vn1'},
               'vmi2':{'vn': 'vn1'},
               'vmi3':{'vn': 'vn1'},
               'vmi4':{'vn': 'vn2'},
              }
        # VM parameters
        vm = {'count':4, 'launch_mode':'distribute',
              'vm1':{'vn':['vn1'], 'vmi':['vmi1']},
              'vm2':{'vn':['vn1'], 'vmi':['vmi2']},
              'vm3':{'vn':['vn1'], 'vmi':['vmi3']},
              'vm4':{'vn':['vn2'], 'vmi':['vmi4']},
             }

        # Setup VNs, VMs as per user configuration
        obj_dict = self.setup_gw_less_fwd(vn=vn, vmi=vmi, vm=vm)

        vn_fixtures = obj_dict['vn_fixtures']
        vm_fixtures = obj_dict['vm_fixtures']
        vmi_fixtures = obj_dict['vmi_fixtures']

        # Policy parameters. Configuring a policy between between ip-fabric vn
        # and vn1 to allow communication between compute node and VMs in vn1.
        # policy between vn1 and vn2 
        policy = {'count':2,
                  'p1': {
                      'rules': [
                            {
                            'direction':'<>',
                            'protocol':'any',
                            'source_network': 'vn1',
                            'dest_network':'vn2',
                            'src_ports':'any',
                            'dst_ports':'any'
                            },
                        ]
                    },
                  'p2': {
                      'rules': [
                            {
                            'direction':'<>',
                            'protocol':'any',
                            'source_network': 'default-domain:default-project:ip-fabric',
                            'dest_network':'vn1',
                            'src_ports':'any',
                            'dst_ports':'any'
                            },
                        ]
                    }
                  }

        # Configure policy as per user configuration
        policy_fixtures = self.setup_policy(policy=policy,
                                            vn_fixtures=vn_fixtures)
        obj_dict['policy_fixtures'] = policy_fixtures
        #IP Fabric is enabled on both the VNs (vn1 and vn2)
        # Configuring FIP. FIP pool is created from vn1 and applied on vm1
        # reach from vn2 vm to fip 
        self.logger.info("IP Fabric is enabled on both the VNs (vn1 and vn2)")
        vn_id = vn_fixtures['vn1'].vn_id
        vmi_id = vmi_fixtures['vmi1'].uuid
        (my_fip, fip_obj) = self.config_fip(obj_dict, vn_id, vmi_id)
        # Verify FIP route in default routing instance in agent
        self.verify_route_ip_fabric_vn_in_agent(ret_dict=obj_dict, ip=my_fip)

        # Verify FIP route in default routing instance in control node
        self.verify_route_ip_fabric_vn_in_control_node(ret_dict=obj_dict,
                                                       ip=my_fip, test_fixture=obj_dict['vm_fixtures']['vm4'])
        # Pinging from vm1 to vm4
        src_vm_fixture = vm_fixtures['vm1']
        src_vm_ip = src_vm_fixture.vm_ip
        result = src_vm_fixture.ping_with_certainty(vm_fixtures['vm4'].vm_ip, count=3)
        if result:
            self.logger.info('Ping from VM: %s to VM: %s is successful, '\
                             'as expected' %(src_vm_ip, vm_fixtures['vm4'].vm_ip))
        else:
            assert result, "Ping from VM: %s to VM: %s is NOT successful" %(
                src_vm_ip, vm_fixtures['vm4'].vm_ip)
        #pinging from vm1 to vm2
        result = src_vm_fixture.ping_with_certainty(vm_fixtures['vm2'].vm_ip, count=3)
        if result:
            self.logger.info('Ping from VM: %s to FIP: %s is successful, '\
                             'as expected' %(src_vm_ip, vm_fixtures['vm2'].vm_ip))
        else:
            assert result, "Ping from VM: %s to FIP: %s is NOT successful" %(
                src_vm_ip, vm_fixtures['vm2'].vm_ip)
        #pinging form vm4 to fip
        src_vm_fixture = vm_fixtures['vm4']
        src_vm_ip = src_vm_fixture.vm_ip
        result = src_vm_fixture.ping_with_certainty(my_fip, count=3)
        if result:
            self.logger.info('Ping from VM: %s to FIP: %s is successful, '\
                             'as expected' %(src_vm_ip, my_fip))
        else:
            assert result, "Ping from VM: %s to FIP: %s is NOT successful" %(
                src_vm_ip, my_fip)
        #pinging from  vm4 to vm1
        result = src_vm_fixture.ping_with_certainty( vm_fixtures['vm1'].vm_ip, count=3)
        if result:
            self.logger.info('Ping from VM: %s to VM: %s is successful, '\
                             'as expected' %(src_vm_ip, vm_fixtures['vm1'].vm_ip))
        else:
            assert result, "Ping from VM: %s to VM: %s is NOT successful" %(
                src_vm_ip, vm_fixtures['vm1'].vm_ip) 

        #all the vms should should reach the vhost1 of all the computes
        new_dict = {}
        for k, v in obj_dict.items():
            new_dict[k] = copy(v)
        del new_dict['vm_fixtures']['vm4']
        del new_dict['vmi_fixtures']['vmi4']
        self.verify_ping_from_vms_to_vhosts(ret_dict = new_dict)

        # IP Fabric is enabled on vn1 and disabled on vn2
        # Now, remove IP fabric provider network configuration on vn2
        # FIP pool is from IP fabric forwarding VN (vn1)
        self.logger.info("IP Fabric is enabled on vn1 and disabled on vn2")
        vn2_fixture = vn_fixtures['vn2']
        ip_fab_vn_obj = self.get_ip_fab_vn()
        vn2_fixture.del_ip_fabric_provider_nw(ip_fab_vn_obj)
        time.sleep(2)
        # Verify FIP route in default routing instance in agent
        self.verify_route_ip_fabric_vn_in_agent(ret_dict=obj_dict, ip=my_fip)
        # Verify FIP route in default routing instance in control node
        self.verify_route_ip_fabric_vn_in_control_node(ret_dict=obj_dict,
                                                       ip=my_fip, test_fixture=obj_dict['vm_fixtures']['vm4'])

        #ping vn2 vm to fip
        result = src_vm_fixture.ping_with_certainty(my_fip, count=2)

        if result:
            self.logger.info('Ping from VM: %s to FIP: %s is successful, '\
                             'as expected' %(src_vm_ip, my_fip))
        else:
            assert result, "Ping from VM: %s to FIP: %s is NOT successful" %(
                src_vm_ip, my_fip)

        #vn2 vm to vn1 vm
        result = src_vm_fixture.ping_with_certainty(vm_fixtures['vm1'].vm_ip, count=2)

        if result:
            self.logger.info('Ping from VM: %s to VM: %s is successful, '\
                             'as expected' %(src_vm_ip, vm_fixtures['vm1'].vm_ip))
        else:
            assert result, "Ping from VM: %s to VM: %s is NOT successful" %(
                src_vm_ip, vm_fixtures['vm1'].vm_ip)

        #vn1 vm to vn2 vm    
        src_vm_fixture = vm_fixtures['vm1']
        src_vm_ip = src_vm_fixture.vm_ip
        result = src_vm_fixture.ping_with_certainty(vm_fixtures['vm4'].vm_ip, count=3)

        if result:
            self.logger.info('Ping from VM: %s to VM: %s is successful, '\
                             'as expected' %(src_vm_ip, vm_fixtures['vm4'].vm_ip))
        else:
            assert result, "Ping from VM: %s to VM: %s is NOT successful" %(
                src_vm_ip, vm_fixtures['vm4'].vm_ip)

        #  computes nodes to fip 
        compute_node_ips = set()
        for vm_fixture in list(vm_fixtures.values()):
            compute_node_ips.add(vm_fixture.get_compute_host())

        for compute_ip in compute_node_ips:
            result = self.ping_vm_from_vhost(compute_ip, my_fip, count=3)
            if result:
                self.logger.info('Ping from vHost: %s to FIP: %s is successful,'\
                                 ' as expected' %(compute_ip, my_fip))
            else:
                assert result, "Ping from VM: %s to FIP: %s is NOT successful" %(
                    compute_ip, my_fip)
        #computes to vm4 should fail
        for compute_ip in compute_node_ips:
            result = self.ping_vm_from_vhost(compute_ip, vm_fixtures['vm4'], count=2)
            if result:
                assert result, "Ping from VM: %s to FIP: %s is NOT successful" %(
                                 ' Not as expected' %(compute_ip,  vm_fixtures['vm4'].vm_ip))
            else:
                self.logger.info('Ping from vHost: %s to FIP: %s is NOT successful,'\
                                 ' as expected' %(compute_ip,  vm_fixtures['vm4'].vm_ip))

        self.verify_ping_from_vms_to_vhosts(ret_dict = obj_dict)
    #End  of 4518 scenarios test

class TestGWLessFWDSvcChain(GWLessFWDTestBase, BaseSvc_FwTest, VerifySvcFirewall):

    @classmethod
    def setUpClass(cls):
        super(TestGWLessFWDSvcChain, cls).setUpClass()
    @preposttest_wrapper
    def test_ip_fabric_svc_in_network_datapath(self):
        '''
        Description:  Validate service chain functionality with gateway less
        forward feature

        Test steps:
            1. Configure 3 VNs (mgmt_vn and left_vn, right_vn) with IP Forwarding enabled
            2. Bring up VMs in left_vn and right_vn
            3. Configure a SVC
            3. Verify ping between left_vn and right_vn VMs are fine
        Pass criteria: There should be no packet loss.
        '''
        # Provision underlay gateway
        self.provision_underlay_gw()

        return self.verify_svc_chain(svc_img_name='cirros_in_net',
                                     service_mode='in-network', create_svms=True,
                                     ip_fabric=True)



