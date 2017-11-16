from tcutils.wrappers import preposttest_wrapper
import test
from common.gw_less_fwd.base import *

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
        self.verify_gw_less_fwd(ret_dict, mode="underlay")

        # Now, remove IP fabric provider network configuration on vn1
        vn1_fixture = vn_fixtures['vn1']
        ip_fab_vn_obj = self.get_ip_fab_vn()
        vn1_fixture.del_ip_fabric_provider_nw(ip_fab_vn_obj)

        time.sleep(2)

        # Verify Gateway less forward functionality. As IP Fabric forwarding
        # is disabled on vn1, traffic should go through overlay
        self.verify_gw_less_fwd(ret_dict = ret_dict, mode = "overlay")

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
        #self.verify_gw_less_fwd(ret_dict = ret_dict, mode = "underlay")

        # Configure policy as per user configuration
        policy_fixtures = self.setup_policy(policy=policy,
                                            vn_fixtures=vn_fixtures)
        ret_dict['policy_fixtures'] = policy_fixtures

        # Verify Gateway less forward functionality with policy
        # As IP Fabric provider network is configured on vn1 and vn2
        # Traffic should go through underlay and traffic across VNs should pass
        self.verify_gw_less_fwd(ret_dict = ret_dict, mode = "underlay")

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
        self.verify_gw_less_fwd(ret_dict = ret_dict, mode = "overlay")

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
        policy_fixtures = self.setup_policy(policy=policy, vn_fixtures=vn_fixtures)
        ret_dict['policy_fixtures'] = policy_fixtures

        # As IP Fabric forwarding is enabled on vn1 and not vn2 and policy is
        # configured to allow traffic between vn1 and vn2. Traffic should go
        # through underlay between VNs
        ret_dict = self.verify_gw_less_fwd(ret_dict = ret_dict, mode = "overlay")

    # end test_gw_less_fwd_ip_fab_vn_and_cust_vn


