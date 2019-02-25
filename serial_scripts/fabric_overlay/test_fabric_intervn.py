# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will
# try to pick params.ini in PWD

from tcutils.wrappers import preposttest_wrapper
from verify import VerifyEVPNType5
from common.contrail_fabric.base import BaseEvpnType5Test
from common.contrail_fabric.base import BaseFabricTest
import test
from tcutils.util import skip_because
from tcutils.util import get_an_ip
from tcutils.util import get_random_cidr
from tcutils.util import get_random_name
import time


class TestEvpnType5VxLANRoutingBasic(BaseEvpnType5Test, VerifyEVPNType5):

    @classmethod
    def setUpClass(cls):
        super(TestEvpnType5VxLANRoutingBasic, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestEvpnType5VxLANRoutingBasic, cls).tearDownClass()

    setup_fixtures = {}

    lrs = {'lr1': {'vn_list': ['vn1', 'vn2'], 'vni': 70001},
           'lr2': {'vn_list': ['vn3', 'vn4'], 'vni': 70002}
           }
    # VN parameters:
    vn = {'count': 4,            # VN count
          'vn1': {'subnet': '21.0.0.0/24'},
          'vn2': {'subnet': '22.0.0.0/24'},
          'vn3': {'subnet': '23.0.0.0/24'},
          'vn4': {'subnet': '24.0.0.0/24'},
          }

    # VMI parameters:
    vmi = {'count': 5,  # VMI Count
           'vmi11': {'vn': 'vn1'},  # VMI details
           'vmi12': {'vn': 'vn1'},  # VMI details
           'vmi21': {'vn': 'vn2'},  # VMI details
           'vmi31': {'vn': 'vn3'},  # VMI details
           'vmi41': {'vn': 'vn4'},  # VMI details
           }

    # VM parameters:
    vm = {'count': 5,  # VM Count
          'launch_mode': 'distribute',
          'vm11': {'vn': ['vn1'], 'vmi': ['vmi11']},  # VM Details
          'vm12': {'vn': ['vn1'], 'vmi': ['vmi12']},  # VM Details
          'vm21': {'vn': ['vn2'], 'vmi': ['vmi21']},  # VM Details
          'vm31': {'vn': ['vn3'], 'vmi': ['vmi31']},  # VM Details
          'vm41': {'vn': ['vn4'], 'vmi': ['vmi41']},  # VM Details
          }


    def is_test_applicable(self):
        result, msg = super(TestEvpnType5VxLANRoutingBasic,
                            self).is_test_applicable()
        if result:
            msg = 'No spines in the provided fabric topology'
            for device in self.inputs.physical_routers_data.iterkeys():
                if self.get_role_from_inputs(device) == 'spine':
                    return (True, None)
        return False, msg

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
        bms_vn_fixture = self.create_vn(
            vn_name='vn100', vn_subnets=['100.0.0.0/24'])
        self.setup_fixtures = self.setup_evpn_type5(
            lrs=self.lrs, vn=self.vn, vmi=self.vmi, vm=self.vm)
        lr1_fix = self.setup_fixtures['lr_fixtures']['lr1']
        lr1_fix.add_interface([bms_vn_fixture.vn_id])
        vn1_fixture = self.setup_fixtures['vn_fixtures']['vn1']
        vn2_fixture = self.setup_fixtures['vn_fixtures']['vn2']

        for spine in self.spines:
            self.setup_fixtures['lr_fixtures']['lr1'].add_physical_router(
                spine.uuid)
        self.logger.debug(
            "Sleeping for 60 secs..after extending LR to Physical Router ...")
        time.sleep(60)

        # find out compute nodes those are part of given logical router
        self.lrs['lr1']['node_ip_list'] = set()
        self.lrs['lr2']['node_ip_list'] = set()
        for each_vm in self.setup_fixtures['vm_fixtures']:
            vm_fix = self.setup_fixtures['vm_fixtures'][each_vm]
            for each_lr in self.lrs:
                for each_vn in self.vm[each_vm]['vn']:
                    if each_vn in self.lrs[each_lr]['vn_list']:
                        self.lrs[each_lr]['node_ip_list'].add(
                            vm_fix.vm_node_ip)
        # verify on setup
        for each_lr in self.setup_fixtures['lr_fixtures']:
            lr_fix = self.setup_fixtures['lr_fixtures'][each_lr]
            lr_fix.verify_on_setup(self.lrs[each_lr]['node_ip_list'])

        self.logger.info(
            "Verify Traffic between VN-1 and VN-2 on Logical Router: lr1")
        send_vm_fixture = self.setup_fixtures['vm_fixtures']['vm11']
        recv_vm_fixture = self.setup_fixtures['vm_fixtures']['vm21']
        traffic_result = self.verify_traffic(sender_vm=send_vm_fixture, receiver_vm=recv_vm_fixture,
                                             proto='udp', sport=10000, dport=20000)
        self.logger.info("Traffic Tx-Pkts: %d  Rx-Pkts: %d" %
                         (traffic_result[0], traffic_result[1]))

        assert traffic_result[0] == traffic_result[1], "Traffic between VN-1 and VN-2 on Logical Router: lr1 Failed"

        self.logger.info(
            "Verify Traffic between VN-3 and VN-4 on Logical Router: lr2")
        send_vm_fixture = self.setup_fixtures['vm_fixtures']['vm31']
        recv_vm_fixture = self.setup_fixtures['vm_fixtures']['vm41']
        traffic_result = self.verify_traffic(sender_vm=send_vm_fixture, receiver_vm=recv_vm_fixture,
                                             proto='udp', sport=10000, dport=20000)
        self.logger.info("Traffic Tx-Pkts: %d  Rx-Pkts: %d" %
                         (traffic_result[0], traffic_result[1]))
        assert traffic_result[0] == traffic_result[1], "Traffic between VN-3 and VN-4 on Logical Router: lr2 Failed"

        bms_fixtures = []
        for bms in self.inputs.bms_data.keys():
            offset = 10 + int(self.inputs.bms_data.keys().index(bms))
            bms_ip = get_an_ip(bms_vn_fixture.get_cidrs()[0], offset=offset)
            bms_fixtures.append(self.create_bms(bms_name=bms,
                                                vn_fixture=bms_vn_fixture,
                                                unit=100,
                                                bms_ip=bms_ip,
                                                bms_mac='00:11:22:33:' +
                                                str(offset) + ':44',
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

        self.logger.info(
            "Verify Traffic between BMS and (vn1, vn2) Logical Router: lr1")
        for bms_fix in bms_fixtures:
            assert bms_fix.ping_with_certainty(
                vm11_ip), "Traffic from BMS to VM-11 Failed"
            assert bms_fix.ping_with_certainty(
                vm21_ip), "Traffic from BMS to VM-21 Failed"

        # end test_evpn_type_5_vxlan_traffic_between_vn

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_evpn_type_5_vm_to_bms(self):
        '''
            Configure Encapsulation order as VxLAN, MPLSoverGRE, MPLSoverUDP
            Enable VxLAN Routing under that project settings
            Create Virtual Networks
            Create a Logical Router and attach above created VNs
            Create a VM in VN1
            Assign an IP from VN2 to a BMS
            Verify traffic between VM to BMS

        '''
        my_lrs = {'lr1': {'vn_list': ['vn1', 'vn2'], 'vni': 70001},
                  }
        my_vn = {'count': 2,
                'vn1': {'subnet': get_random_cidr(af='v4')},
                'vn2': {'subnet': get_random_cidr(af='v4')},
                }
        my_vmi = {'count': 2,  # VMI Count
                  'vmi11': {'vn': 'vn1'},  # VMI details
                  'vmi21': {'vn': 'vn2'},  # VMI details
                  }
        my_vm = {'count': 2,  # VM Count
                 'launch_mode': 'distribute',
                 'vm11': {'vn': ['vn1'], 'vmi': ['vmi11']},  # VM Details
                 'vm21': {'vn': ['vn2'], 'vmi': ['vmi21']},  # VM Details
                 }
        self.setup_fixtures = self.setup_evpn_type5(
            lrs=my_lrs, vn=my_vn, vmi=my_vmi, vm=my_vm)
        vn1_fixture = self.setup_fixtures['vn_fixtures']['vn1']
        vn2_fixture = self.setup_fixtures['vn_fixtures']['vn2']
        lr1_fix = self.setup_fixtures['lr_fixtures']['lr1']
        lr1_fix.add_interface([vn1_fixture.vn_id, vn2_fixture.vn_id])

        for spine in self.spines:
            self.setup_fixtures['lr_fixtures']['lr1'].add_physical_router(
                spine.uuid)
        self.logger.debug(
            "Sleeping for 60 secs..after extending LR to Physical Router ...")
        time.sleep(60)
        bms_fixtures = []
        bms = self.inputs.bms_data.keys()[0]
        bms_ip = get_an_ip(vn2_fixture.get_cidrs()[0], offset=100)
        bms_fixtures.append(self.create_bms(bms_name=bms,
                                            vn_fixture=vn2_fixture,
                                            unit=100,
                                            bms_ip=bms_ip,
                                            bms_mac='00:11:22:33:44:55',
                                            bms_ip_netmask='24',
                                            bms_gw_ip=vn2_fixture.get_subnets()[
                                                0]['gateway_ip'],
                                            static_ip=True,
                                            security_groups=[self.default_sg.uuid]))

        self.logger.info("Modifying SG to allow traffic from BMS to VM...")
        self.allow_default_sg_to_allow_all_on_project(self.inputs.project_name)
        self.logger.info("Modified Default Secutiy Group Rules")

        vm11_fixture = self.setup_fixtures['vm_fixtures']['vm11']
        vm11_ip = vm11_fixture.get_vm_ips()[0]

        self.logger.info("Verify Traffic between BMS and VM")
        for bms_fix in bms_fixtures:
            assert bms_fix.ping_with_certainty(
                vm11_ip), "Traffic from BMS to VM-11 Failed"

        # end test_evpn_type_5_vm_to_bms

    @preposttest_wrapper
    def test_evpn_type_5_vm_to_bms_remove_vn_from_lr(self):
        '''
            Configure Encapsulation order as VxLAN, MPLSoverGRE, MPLSoverUDP
            Enable VxLAN Routing under that project settings
            Create Virtual Networks
            Create a Logical Router and attach above created VNs
            Create a VM in VN1
            Assign an IP from VN2 to a BMS
            Verify traffic between VM to BMS
            Now remove VN2 from the LR
            Traffic across the VNs should fail

        '''
        my_lrs = {'lr1': {'vn_list': ['vn1', 'vn2'], 'vni': 70001},
                  }
        my_vn = {'count': 2,
                 'vn1': {'subnet': get_random_cidr(af='v4')},
                 'vn2': {'subnet': get_random_cidr(af='v4')},
                 }

        my_vmi = {'count': 2,
                  'vmi11': {'vn': 'vn1'},  # VMI details
                  'vmi21': {'vn': 'vn2'},  # VMI details
                  }

        my_vm = {'count': 2,
                 'launch_mode': 'distribute',
                 'vm11': {'vn': ['vn1'], 'vmi': ['vmi11']},  # VM Details
                 'vm21': {'vn': ['vn2'], 'vmi': ['vmi21']},  # VM Details
                 }
        self.setup_fixtures = self.setup_evpn_type5(
            lrs=my_lrs, vn=my_vn, vmi=my_vmi, vm=my_vm)
        vn1_fixture = self.setup_fixtures['vn_fixtures']['vn1']
        vn2_fixture = self.setup_fixtures['vn_fixtures']['vn2']
        lr1_fix = self.setup_fixtures['lr_fixtures']['lr1']
        lr1_fix.add_interface([vn1_fixture.vn_id, vn2_fixture.vn_id])

        for spine in self.spines:
            self.setup_fixtures['lr_fixtures']['lr1'].add_physical_router(
                spine.uuid)
        self.logger.debug(
            "Sleeping for 60 secs..after extending LR to Physical Router ...")
        time.sleep(60)
        bms_fixtures = []
        bms = self.inputs.bms_data.keys()[0]
        bms_ip = get_an_ip(vn2_fixture.get_cidrs()[0], offset=100)
        bms_fixtures.append(self.create_bms(bms_name=bms,
                                            vn_fixture=vn2_fixture,
                                            unit=100,
                                            bms_ip=bms_ip,
                                            bms_mac='00:11:22:33:44:55',
                                            bms_ip_netmask='24',
                                            bms_gw_ip=vn2_fixture.get_subnets()[
                                                0]['gateway_ip'],
                                            static_ip=True,
                                            security_groups=[self.default_sg.uuid]))

        self.logger.info("Modifying SG to allow traffic from BMS to VM...")
        self.allow_default_sg_to_allow_all_on_project(self.inputs.project_name)
        self.logger.info("Modified Default Secutiy Group Rules")

        vm11_fixture = self.setup_fixtures['vm_fixtures']['vm11']
        vm11_ip = vm11_fixture.get_vm_ips()[0]

        self.logger.info("Verify Traffic between BMS and VM")
        for bms_fix in bms_fixtures:
            assert bms_fix.ping_with_certainty(
                vm11_ip), "Traffic from BMS to VM-11 Failed"
        self.logger.info(
            'Will disassociate VN2 from the LR. Traffic between the BMS and VM should fail')
        lr1_fix.remove_interface([vn2_fixture.vn_id])
        self.logger.debug(
            "Sleeping for 30 secs to allow config change to be pushed to the Spine")
        time.sleep(30)
        for bms_fix in bms_fixtures:
            assert bms_fix.ping_with_certainty(
                vm11_ip, expectation=False), "Traffic from BMS to VM-11 Passed. Should have failed"

        # end test_evpn_type_5_vm_to_bms_remove_vn_from_lr

    @preposttest_wrapper
    def test_evpn_type_5_vm_to_bms_remove_vni_from_lr(self):
        '''
            Configure Encapsulation order as VxLAN, MPLSoverGRE, MPLSoverUDP
            Enable VxLAN Routing under that project settings
            Create Virtual Networks
            Create a Logical Router and attach above created VNs
            Create a VM in VN1
            Assign an IP from VN2 to a BMS
            Verify traffic between VM to BMS
            Now remove the VNI from the LR
            Traffic across the VNs should continue to work

        '''
        my_lrs = {'lr1': {'vn_list': ['vn1', 'vn2'], 'vni': 70001},
                  }
        my_vn = {'count': 2,
                 'vn1': {'subnet': get_random_cidr(af='v4')},
                 'vn2': {'subnet': get_random_cidr(af='v4')},
                 }

        my_vmi = {'count': 2,
                  'vmi11': {'vn': 'vn1'},  # VMI details
                  'vmi21': {'vn': 'vn2'},  # VMI details
                  }

        my_vm = {'count': 2,
                 'launch_mode': 'distribute',
                 'vm11': {'vn': ['vn1'], 'vmi': ['vmi11']},  # VM Details
                 'vm21': {'vn': ['vn2'], 'vmi': ['vmi21']},  # VM Details
                 }
        self.setup_fixtures = self.setup_evpn_type5(
            lrs=my_lrs, vn=my_vn, vmi=my_vmi, vm=my_vm)
        vn1_fixture = self.setup_fixtures['vn_fixtures']['vn1']
        vn2_fixture = self.setup_fixtures['vn_fixtures']['vn2']
        lr1_fix = self.setup_fixtures['lr_fixtures']['lr1']
        lr1_fix.add_interface([vn1_fixture.vn_id, vn2_fixture.vn_id])

        for spine in self.spines:
            self.setup_fixtures['lr_fixtures']['lr1'].add_physical_router(
                spine.uuid)
        self.logger.debug(
            "Sleeping for 60 secs..after extending LR to Physical Router ...")
        time.sleep(60)
        bms_fixtures = []
        bms = self.inputs.bms_data.keys()[0]
        bms_ip = get_an_ip(vn2_fixture.get_cidrs()[0], offset=100)
        bms_fixtures.append(self.create_bms(bms_name=bms,
                                            vn_fixture=vn2_fixture,
                                            unit=100,
                                            bms_ip=bms_ip,
                                            bms_mac='00:11:22:33:44:55',
                                            bms_ip_netmask='24',
                                            bms_gw_ip=vn2_fixture.get_subnets()[
                                                0]['gateway_ip'],
                                            static_ip=True,
                                            security_groups=[self.default_sg.uuid]))

        self.logger.info("Modifying SG to allow traffic from BMS to VM...")
        self.allow_default_sg_to_allow_all_on_project(self.inputs.project_name)
        self.logger.info("Modified Default Secutiy Group Rules")

        vm11_fixture = self.setup_fixtures['vm_fixtures']['vm11']
        vm11_ip = vm11_fixture.get_vm_ips()[0]

        self.logger.info("Verify Traffic between BMS and VM")
        for bms_fix in bms_fixtures:
            assert bms_fix.ping_with_certainty(
                vm11_ip), "Traffic from BMS to VM-11 Failed"
        self.logger.info(
            'Will delete the VNI associated with the LR. Traffic between the BMS and VM should pass with the system-generated VNI')
        lr1_fix.delete_vni()
        self.logger.debug(
            "Sleeping for 30 secs to allow config change to be pushed to the Spine")
        time.sleep(30)
        for bms_fix in bms_fixtures:
            assert bms_fix.ping_with_certainty(
                vm11_ip), "Traffic from BMS to VM-11 failed"

        # end test_evpn_type_5_vm_to_bms_remove_vni_from_lr

    @preposttest_wrapper
    def test_evpn_type_5_vm_to_bms_add_rt_to_lr(self):
        '''
            Configure Encapsulation order as VxLAN, MPLSoverGRE, MPLSoverUDP
            Enable VxLAN Routing under that project settings
            Create Virtual Networks
            Create a Logical Router and attach above created VNs
            Create a VM in VN1
            Assign an IP from VN2 to a BMS
            Verify traffic between VM to BMS
            Now add a new RT to the LR
            Traffic across the VNs should continue to work

        '''
        my_lrs = {'lr1': {'vn_list': ['vn1', 'vn2'], 'vni': 70001},
                  }
        my_vn = {'count': 2,
                 'vn1': {'subnet': get_random_cidr(af='v4')},
                 'vn2': {'subnet': get_random_cidr(af='v4')},
                 }

        my_vmi = {'count': 2,
                  'vmi11': {'vn': 'vn1'},  # VMI details
                  'vmi21': {'vn': 'vn2'},  # VMI details
                  }

        my_vm = {'count': 2,
                 'launch_mode': 'distribute',
                 'vm11': {'vn': ['vn1'], 'vmi': ['vmi11']},  # VM Details
                 'vm21': {'vn': ['vn2'], 'vmi': ['vmi21']},  # VM Details
                 }
        self.setup_fixtures = self.setup_evpn_type5(
            lrs=my_lrs, vn=my_vn, vmi=my_vmi, vm=my_vm)
        vn1_fixture = self.setup_fixtures['vn_fixtures']['vn1']
        vn2_fixture = self.setup_fixtures['vn_fixtures']['vn2']
        lr1_fix = self.setup_fixtures['lr_fixtures']['lr1']
        lr1_fix.add_interface([vn1_fixture.vn_id, vn2_fixture.vn_id])

        for spine in self.spines:
            self.setup_fixtures['lr_fixtures']['lr1'].add_physical_router(
                spine.uuid)
        self.logger.debug(
            "Sleeping for 60 secs..after extending LR to Physical Router ...")
        time.sleep(60)
        bms_fixtures = []
        bms = self.inputs.bms_data.keys()[0]
        bms_ip = get_an_ip(vn2_fixture.get_cidrs()[0], offset=100)
        bms_fixtures.append(self.create_bms(bms_name=bms,
                                            vn_fixture=vn2_fixture,
                                            unit=100,
                                            bms_ip=bms_ip,
                                            bms_mac='00:11:22:33:44:55',
                                            bms_ip_netmask='24',
                                            bms_gw_ip=vn2_fixture.get_subnets()[
                                                0]['gateway_ip'],
                                            static_ip=True,
                                            security_groups=[self.default_sg.uuid]))

        self.logger.info("Modifying SG to allow traffic from BMS to VM...")
        self.allow_default_sg_to_allow_all_on_project(self.inputs.project_name)
        self.logger.info("Modified Default Secutiy Group Rules")

        vm11_fixture = self.setup_fixtures['vm_fixtures']['vm11']
        vm11_ip = vm11_fixture.get_vm_ips()[0]

        self.logger.info("Verify Traffic between BMS and VM")
        for bms_fix in bms_fixtures:
            assert bms_fix.ping_with_certainty(
                vm11_ip), "Traffic from BMS to VM-11 Failed"
        self.logger.info(
            'Will add a new Route-Target to the LR. Traffic between the BMS and VM should continue to pass')
        lr1_fix.add_rt('target:64512:12345')
        self.logger.debug(
            "Sleeping for 30 secs to allow config change to be pushed to the Spine")
        time.sleep(30)

        for bms_fix in bms_fixtures:
            assert bms_fix.ping_with_certainty(
                vm11_ip), "Traffic from BMS to VM-11 failed"

        # end test_evpn_type_5_vm_to_bms_add_rt_to_lr
