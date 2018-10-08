# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD

from tcutils.wrappers import preposttest_wrapper
from verify import VerifyEVPNType5
from common.contrail_fabric.base import BaseEvpnType5Test
from common.contrail_fabric.base import BaseFabricTest
import test
from tcutils.util import skip_because
import time

class TestEvpnType5VxLANRoutingBasic(BaseEvpnType5Test, VerifyEVPNType5):
   
    setup_fixtures = {}

    lrs = { 'lr1':{'vn_list': ['vn1','vn2'], 'vni': 70001},
            'lr2':{'vn_list': ['vn3','vn4'], 'vni': 70002}
            }
                    #VN parameters:
    vn = {'count':4,            # VN count
            'vn1':{'subnet':'21.0.0.0/24'},
            'vn2':{'subnet':'22.0.0.0/24'},
            'vn3':{'subnet':'23.0.0.0/24'},
            'vn4':{'subnet':'24.0.0.0/24'},
            }

                    #VMI parameters:
    vmi = {'count':5, # VMI Count
            'vmi11':{'vn': 'vn1'}, # VMI details
            'vmi12':{'vn': 'vn1'}, # VMI details
            'vmi21':{'vn': 'vn2'}, # VMI details
            'vmi31':{'vn': 'vn3'}, # VMI details
            'vmi41':{'vn': 'vn4'}, # VMI details
            }

                #VM parameters:
    vm = {'count':5, # VM Count
                'launch_mode':'distribute',
                'vm11':{'vn':['vn1'], 'vmi':['vmi11']}, # VM Details
                'vm12':{'vn':['vn1'], 'vmi':['vmi12']}, # VM Details
                'vm21':{'vn':['vn2'], 'vmi':['vmi21']}, # VM Details
                'vm31':{'vn':['vn3'], 'vmi':['vmi31']}, # VM Details
                'vm41':{'vn':['vn4'], 'vmi':['vmi41']}, # VM Details
             }
    
    @preposttest_wrapper
    def not_test_evpn_type_5_vxlan_traffic_within_vn(self):

        ''' 
            Change Encapsulation order as VxLAN, MPLSoverGRE, MPLSoverUDP
            Enable VxLAN Routing under that project settings
            Create Virtual Networks 
            Create logical Routers and attach above created VNs
            Create VMs on Virtual Networks and verify communications accross those VMs

        '''
        ''' 
        lrs = { 'lr1':{'vn_list': ['vn1','vn2'], 'vni': 7001},
               'lr2':{'vn_list': ['vn3','vn4'], 'vni': 7002}
             }
                    #VN parameters:
        vn = {'count':4,            # VN count
              'vn1':{'subnet':'21.0.0.0/24'},
              'vn2':{'subnet':'22.0.0.0/24'},
              'vn3':{'subnet':'23.0.0.0/24'},
              'vn4':{'subnet':'24.0.0.0/24'}
             }
    
                    #VMI parameters:
        vmi = {'count':5, # VMI Count
                'vmi11':{'vn': 'vn1'}, # VMI details
                'vmi12':{'vn': 'vn1'}, # VMI details
                'vmi21':{'vn': 'vn2'}, # VMI details
                'vmi31':{'vn': 'vn3'}, # VMI details
                'vmi41':{'vn': 'vn4'}, # VMI details
              }
    
                #VM parameters:
        vm = {'count':5, # VM Count
                        'launch_mode':'distribute',
                        'vm11':{'vn':['vn1'], 'vmi':['vmi11']}, # VM Details
                        'vm12':{'vn':['vn1'], 'vmi':['vmi12']}, # VM Details
                        'vm21':{'vn':['vn2'], 'vmi':['vmi21']}, # VM Details
                        'vm31':{'vn':['vn3'], 'vmi':['vmi31']}, # VM Details
                        'vm41':{'vn':['vn4'], 'vmi':['vmi41']}, # VM Details
             }
        '''
        if self.setup_fixtures == {}:
           self.setup_fixtures = self.setup_evpn_type5(lrs=self.lrs,vn=self.vn,vmi=self.vmi,vm=self.vm)

        send_vm_fixture = self.setup_fixtures['vm_fixtures']['vm11']
        recv_vm_fixture = self.setup_fixtures['vm_fixtures']['vm12']
        traffic_result = self.verify_traffic(sender_vm=send_vm_fixture, receiver_vm=recv_vm_fixture, 
                                        proto='udp', sport=10000, dport=20000)
        self.logger.info("Traffic Tx-Pkts: %d  Rx-Pkts: %d" % (traffic_result[0],traffic_result[1]))
        assert traffic_result[0] == traffic_result[1]



    @preposttest_wrapper
    def test_evpn_type_5_vxlan_traffic_between_vn(self):

        '''
            Configure Encapsulation order as VxLAN, MPLSoverGRE, MPLSoverUDP
            Enable VxLAN Routing under that project settings
            Create Virtual Networks
            Create logical Routers and attach above created VNs
            Create VMs on Virtual Networks
            Verify traffic between accross Virtual Networks

        '''
        # Fabric onboarding...
        spine_router_uuids = list()
        self.default_sg = self.get_default_sg()
        fabric_dict = self.inputs.fabrics[0]
        fabric, devices, interfaces = self.onboard_existing_fabric(fabric_dict, name='evpn_type5_fabric')
        assert interfaces, 'Failed to onboard existing fabric %s'%fabric_dict

        self.assign_roles(fabric, devices)

        self.logger.info("Deleting Auto LR ...")
        fabric_name = fabric.get_name()
        self.delete_auto_lr(fabric_name=fabric_name)

        self.logger.info("Sleeping for 60 secs..after auto LR deletion...")
        time.sleep(60)
        bms_vn_fixture = self.create_vn(vn_name='vn100', vn_subnets=['100.0.0.0/24'])
        self.setup_fixtures = self.setup_evpn_type5(lrs=self.lrs,vn=self.vn,vmi=self.vmi,vm=self.vm)
        lr1_fix = self.setup_fixtures['lr_fixtures']['lr1']
        lr1_fix.add_interface(bms_vn_fixture.vn_id)
        vn1_fixture = self.setup_fixtures['vn_fixtures']['vn1']
        vn2_fixture = self.setup_fixtures['vn_fixtures']['vn2']
        for device in devices:
            self.logger.info("Device Roles: %s" % device.get_role())
            if self.get_role_from_inputs(device.name) == 'spine':
                spine_router_uuids.append(device.get_uuid())

        assert spine_router_uuids, "NOT Able to find Spine Router UUID..Please check fabric phy device fixtures"
        for spine_router_uuid in spine_router_uuids:
            self.setup_fixtures['lr_fixtures']['lr1'].add_physical_router(spine_router_uuid) 
        self.logger.debug("Sleeping for 60 secs..after extending LR to Physical Router ...")
        time.sleep(60)

        # find out compute nodes those are part of given logical router 
        self.lrs['lr1']['node_ip_list'] = set()
        self.lrs['lr2']['node_ip_list'] = set()
        for each_vm in self.setup_fixtures['vm_fixtures']:
            vm_fix = self.setup_fixtures['vm_fixtures'][each_vm] 
            for each_lr in self.lrs:
                for each_vn in self.vm[each_vm]['vn']:
                    if each_vn in self.lrs[each_lr]['vn_list']:
                        self.lrs[each_lr]['node_ip_list'].add(vm_fix.vm_node_ip)
        
        #import pdb; pdb.set_trace()
        # verify on setup
        for each_lr in self.setup_fixtures['lr_fixtures']:
            lr_fix = self.setup_fixtures['lr_fixtures'][each_lr] 
            lr_fix.verify_on_setup(self.lrs[each_lr]['node_ip_list'])

        self.logger.info("Verify Traffic between VN-1 and VN-2 on Logical Router: lr1")
        send_vm_fixture = self.setup_fixtures['vm_fixtures']['vm11']
        recv_vm_fixture = self.setup_fixtures['vm_fixtures']['vm21']
        traffic_result = self.verify_traffic(sender_vm=send_vm_fixture, receiver_vm=recv_vm_fixture,
                                        proto='udp', sport=10000, dport=20000)
        self.logger.info("Traffic Tx-Pkts: %d  Rx-Pkts: %d" % (traffic_result[0],traffic_result[1]))

        assert traffic_result[0] == traffic_result[1], "Traffic between VN-1 and VN-2 on Logical Router: lr1 Failed"

        self.logger.info("Verify Traffic between VN-3 and VN-4 on Logical Router: lr2")
        send_vm_fixture = self.setup_fixtures['vm_fixtures']['vm31']
        recv_vm_fixture = self.setup_fixtures['vm_fixtures']['vm41']
        traffic_result = self.verify_traffic(sender_vm=send_vm_fixture, receiver_vm=recv_vm_fixture,
                                        proto='udp', sport=10000, dport=20000)
        self.logger.info("Traffic Tx-Pkts: %d  Rx-Pkts: %d" % (traffic_result[0],traffic_result[1]))
        assert traffic_result[0] == traffic_result[1], "Traffic between VN-3 and VN-4 on Logical Router: lr2 Failed"

        #bms_mac=self.inputs.bms_data[bms]['interfaces'][0]['host_mac'],
        bms_fixtures = []

        for bms in self.inputs.bms_data.keys():
            bms_fixtures.append(self.create_existing_bms(bms_name=bms,
                                 vn_fixture=bms_vn_fixture, 
                                 unit=100,
                                 bms_ip='100.0.0.10',
                                 bms_mac='00:11:22:33:44:55',
                                 bms_ip_netmask='24',
                                 bms_gw_ip='100.0.0.1',
                                 static_ip=True,
                                 security_groups=[self.default_sg.uuid]))

        self.logger.info("Modifying SG to allow traffic from BMS to VM...")
        self.allow_default_sg_to_allow_all_on_project(self.inputs.project_name)
        self.logger.info("Modified Default Secutiy Group Rules")

        vm11_fixture = self.setup_fixtures['vm_fixtures']['vm11']
        vm21_fixture = self.setup_fixtures['vm_fixtures']['vm21']
        vm11_ip = vm11_fixture.get_vm_ips()[0]
        vm21_ip = vm21_fixture.get_vm_ips()[0]

        self.logger.info("Verify Traffic between BMS and (vn1, vn2) Logical Router: lr1")
        for bms_fix in bms_fixtures:
            assert bms_fix.ping_with_certainty(vm11_ip), "Traffic from BMS to VM-11 Failed"
            assert bms_fix.ping_with_certainty(vm21_ip), "Traffic from BMS to VM-21 Failed"


