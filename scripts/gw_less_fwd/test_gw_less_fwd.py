from tcutils.wrappers import preposttest_wrapper
from common.gw_less_fwd.base import *
from contrailapi import ContrailVncApi
import test

from time import sleep

class TestGWLessFWD(GWLessFWDTestBase):

    @classmethod
    def setUpClass(cls):
        super(TestGWLessFWD, cls).setUpClass()
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(TestGWLessFWD, cls).tearDownClass()
    # end tearDownClass

    @test.attr(type=['cb_sanity', 'sanity'])
    @preposttest_wrapper
    def test_gw_less_fwd_single_vn_ip_fab(self):
        '''
            Test Gateway less forwarding with single VN and IP Fabric provider
            network. IP Fbaric network is configured as provider network
            over vn1. Multiple VMs will be launched across compute nodes
            and ping between VMs should be successful and happen through
            underlay.
        '''
        if (len(self.inputs.compute_ips) < 2):
             raise self.skipTest(
                "Skipping Test. At least 2 compute node required to run the test")
        result = True


        # VN parameters. IP Fabric forwarding is enabled on vn1.
        vn = {'count':1,
              'vn1':{'subnet':'10.10.10.0/24', 'ip_fabric':True},
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

        # Gateway bgp peer configuration
        bgp = {'count': 1,
               'bgp1':{'router_name': 'sw166',
                       'router_ip': '10.204.217.254',
                       'router_asn': 64512,
                       'address_families': ["inet"]
                      },
               }

        # Setup VNs, VMs as per user configuration
        ret_dict = self.setup_gw_less_fwd(vn=vn, vmi=vmi, vm=vm, bgp=bgp)

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
        self.verify_gw_less_fwd(ret_dict = ret_dict)

    # end test_gw_less_fwd_single_vn_ip_fab

    @preposttest_wrapper
    def test_gw_less_fwd_multi_vn_ip_fab(self):
        '''
            Test Gateway less forwarding with multiple VNs and IP Fabric provider
            network. IP Fbaric network is configured as provider network
            over vn1 and vn2. Multiple VMs will be launched across compute nodes
            and ping between VMs should be successful and happen through
            underlay.
        '''

        if (len(self.inputs.compute_ips) < 2):
             raise self.skipTest(
                "Skipping Test. At least 2 compute node required to run the test")
        result = True

        # VN parameters. IP Fabric forwarding is enabled on both vn1 and vn2.
        vn = {'count':2,
              'vn1':{'subnet':'10.10.10.0/24', 'ip_fabric':True},
              'vn2':{'subnet':'20.20.20.0/24', 'ip_fabric':True},
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

        # Gateway bgp peer configuration
        bgp = {'count': 1,
               'bgp1':{'router_name': 'sw166',
                       'router_ip': '10.204.217.254',
                       'router_asn': 64512,
                       'address_families': ["inet"]
                      },
               }


        # Policy parameters. Configuring policy between vn1 and vn2 to allow
        # the traffic.
        policy = {'count':1,
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
                    }
                  }

       # Setup VNs, VMs as per user configuration
        ret_dict = self.setup_gw_less_fwd(vn=vn, vmi=vmi, vm=vm, bgp=bgp)

        vn_fixtures = ret_dict['vn_fixtures']

        # Verify Gateway less forward functionality with out policy
        # As IP Fabric provider network is configured on vn1 and vn2
        # and policy is disabled Traffic should go through underlay
        # between VMs within same VN and traffic should fail across VNs

        #This step is commented out due to bug: 1716837
        #self.verify_gw_less_fwd(ret_dict = ret_dict)

        # Configure policy as per user configuration
        policy_fixtures = self.setup_policy(policy=policy,
                                            vn_fixtures=vn_fixtures)
        ret_dict['policy_fixtures'] = policy_fixtures

        # Verify Gateway less forward functionality with policy
        # As IP Fabric provider network is configured on vn1 and vn2
        # Traffic should go through underlay and traffic across VNs should pass
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
        self.verify_gw_less_fwd(ret_dict = ret_dict)

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
        result = True

        # VN parameters. IP Fabric forwarding is enabled on vn1 and not on vn2.
        vn = {'count':2,
              'vn1':{'subnet':'10.10.10.0/24', 'ip_fabric':True},
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

        # Gateway bgp peer configuration
        bgp = {'count': 1,
               'bgp1':{'router_name': 'sw166',
                       'router_ip': '10.204.217.254',
                       'router_asn': 64512,
                       'address_families': ["inet"]
                      },
               }


        # Policy parameters
        policy = {'count':1,
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
                    }
                  }

        # Setup VNs, VMs as per user configuration
        ret_dict = self.setup_gw_less_fwd(vn=vn, vmi=vmi, vm=vm, bgp=bgp)

        vn_fixtures = ret_dict['vn_fixtures']

        # Configure policy between vn1 and vn2
        policy_fixtures = self.setup_policy(policy=policy,
                                            vn_fixtures=vn_fixtures)
        ret_dict['policy_fixtures'] = policy_fixtures

        # As IP Fabric forwarding is enabled on vn1 and not vn2 and policy is
        # configured to allow traffic between vn1 and vn2. Traffic should go
        # through underlay between VNs
        ret_dict = self.verify_gw_less_fwd(ret_dict=ret_dict)

    # end test_gw_less_fwd_ip_fab_vn_and_cust_vn

    @preposttest_wrapper
    def test_gw_less_fwd_aap(self):
        '''
            Test Gateway less forwarding functionality with allowed address pair
        '''

        if (len(self.inputs.compute_ips) < 2):
             raise self.skipTest(
                "Skipping Test. At least 2 compute node required to run the test")
        result = True

        # VN parameters
        vn = {'count':1,
              'vn1':{'subnet':'10.10.10.0/24', 'ip_fabric':True},
             }
        # VMI parameters
        vmi = {'count':3,
               'vmi1':{'vn': 'vn1', 'vip': '10.10.10.100', 'mode': 'active-active'},
               'vmi2':{'vn': 'vn1', 'vip': '10.10.10.100', 'mode': 'active-active'},
               'vmi3':{'vn': 'vn1'},
              }

        # VM parameters
        vm = {'count':3, 'launch_mode':'distribute',
              'vm1':{'vn':['vn1'], 'vmi':['vmi1']},
              'vm2':{'vn':['vn1'], 'vmi':['vmi2']},
              'vm3':{'vn':['vn1'], 'vmi':['vmi3']},
             }

        # Gateway bgp peer configuration
        bgp = {'count': 1,
               'bgp1':{'router_name': 'sw166',
                       'router_ip': '10.204.217.254',
                       'router_asn': 64512,
                       'address_families': ["inet"]
                      },
               }

        # Setup VNs, VMs as per user configuration
        ret_dict = self.setup_gw_less_fwd(vn=vn, vmi=vmi, vm=vm, bgp=bgp)

        vIP = "10.10.10.100"
        # Verify AAP route in default routing instance in agent
        self.verify_route_ip_fabric_vn_in_agent(ret_dict=ret_dict, ip=vIP)

        # Verify AAP route in default routing instance in control node
        self.verify_route_ip_fabric_vn_in_control_node(ret_dict=ret_dict,
                                                       ip=vIP)

        vn_fixtures = ret_dict['vn_fixtures']
        vm_fixtures = ret_dict['vm_fixtures']
        vmi_fixtures = ret_dict['vmi_fixtures']

        # Configuring AAP on 2 VMs
        vm_list = [vm_fixtures['vm1'], vm_fixtures['vm2']]
        for vm in vm_list:
            output = vm.run_cmd_on_vm(
                ['sudo ifconfig eth0:10 ' + vIP + ' netmask 255.255.255.0'])
            self.check_master_in_agent(vm, vn_fixtures['vn1'], vIP, ecmp=True)

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
        for vm_fixture in vm_fixtures.values():
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
            IP fabric is enabled on both the VNs (vn1 and vn2) and floating ip is
            created from vn1 and applied it on vn2 VM (vm2). Now, pinging FIP
            from vm1 and ping should be successful. Also, FIP should be present
            default routing instance.

            In next scenario, IP fabric forwarding is disabled on vn1 and Pinging
            FIP from vm1 and it should be successful.


        '''

        if (len(self.inputs.compute_ips) < 2):
             raise self.skipTest(
                "Skipping Test. At least 2 compute node required to run the test")
        result = True

        # VN parameters. IP Fabric forwarding is enabled on both VNs
        vn = {'count':2,
              'vn1':{'subnet':'10.10.10.0/24', 'ip_fabric':True},
              'vn2':{'subnet':'20.20.20.0/24', 'ip_fabric':True},
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

        # Gateway bgp peer configuration
        bgp = {'count': 1,
               'bgp1':{'router_name': 'sw166',
                       'router_ip': '10.204.217.254',
                       'router_asn': 64512,
                       'address_families': ["inet"]
                      },
               }

        # Setup VNs, VMs as per user configuration
        ret_dict = self.setup_gw_less_fwd(vn=vn, vmi=vmi, vm=vm, bgp=bgp)

        vn_fixtures = ret_dict['vn_fixtures']
        vm_fixtures = ret_dict['vm_fixtures']
        vmi_fixtures = ret_dict['vmi_fixtures']

        # Configuring FIP. FIP pool is created from vn1 and applied on vm2
        vn_id = vn_fixtures['vn1'].vn_id
        vmi_id = vmi_fixtures['vmi2'].uuid
        (my_fip, fip_obj) = self.config_fip(ret_dict, vn_id, vmi_id)

        # Verify FIP route in default routing instance in agent
        self.verify_route_ip_fabric_vn_in_agent(ret_dict=ret_dict, ip=my_fip)

        # Verify FIP route in default routing instance in control node
        self.verify_route_ip_fabric_vn_in_control_node(ret_dict=ret_dict,
                                                       ip=my_fip)

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

        # Now, remove IP fabric provider network configuration on vn2
        # FIP pool is from IP fabric forwarding VN (vn1)
        vn2_fixture = vn_fixtures['vn2']
        ip_fab_vn_obj = self.get_ip_fab_vn()
        vn2_fixture.del_ip_fabric_provider_nw(ip_fab_vn_obj)

        time.sleep(2)

        # Verify FIP route in default routing instance in agent
        self.verify_route_ip_fabric_vn_in_agent(ret_dict=ret_dict, ip=my_fip)

        # Verify FIP route in default routing instance in control node
        self.verify_route_ip_fabric_vn_in_control_node(ret_dict=ret_dict,
                                                       ip=my_fip)

        result = src_vm_fixture.ping_with_certainty(my_fip, count=2)

        if result:
            self.logger.info('Ping from VM: %s to FIP: %s is successful, '\
                             'as expected' %(src_vm_ip, my_fip))
        else:
            assert result, "Ping from VM: %s to FIP: %s is NOT successful" %(
                src_vm_ip, my_fip)

        # Now, remove IP fabric provider network configuration on vn1
        vn1_fixture = vn_fixtures['vn1']
        ip_fab_vn_obj = self.get_ip_fab_vn()
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
                                                       expectation=False)

        result = src_vm_fixture.ping_with_certainty(my_fip, count=2)

        if result:
            self.logger.info('Ping from VM: %s to FIP: %s is successful, '\
                             'as expected' %(src_vm_ip, my_fip))
        else:
            assert result, "Ping from VM: %s to FIP: %s is NOT successful" %(
                src_vm_ip, my_fip)




    # end test_gw_less_fwd_fip


