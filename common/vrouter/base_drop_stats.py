from tcutils.util import *
import fixtures
import re
from common.base import *
import time

class BaseDropStats(GenericTestBase) :


    @classmethod
    def setUpClass(cls):
        super(BaseDropStats, cls).setUpClass()
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BaseDropStats, cls).tearDownClass()
    # end tearDownClass

    # end get_drop_stats_dict

    def print_drop_stats_dict(self, d):
        self.logger.info("%s \n"  % ('-'*100))
        for k, v in d.iteritems():
            self.logger.info("%s : %s"  % (k, v))
    # end print_drop_stats_dict

    def get_drop_stats_dict(self, compute, fq_name=None, module='vif'):
        if module == 'vrouter':
            drop_stats_list = self.agent_inspect_h[compute].get_agent_vrouter_drop_stats()
        else:
            drop_stats_list = self.agent_inspect_h[compute].get_agent_vm_interface_drop_stats(fq_name)
        return drop_stats_list

    def verify_flow_action_drop_stats(self, drop_type='ds_flow_action_drop'):
        result = True
        ping_count = 5
        image_name = 'cirros'

        compute_ips = self.inputs.compute_ips
        compute0 = compute_ips[0]
        compute1 = compute0
        compute0_name =  hostname = self.inputs.host_data[compute0]['name']
        compute1 = compute_ips[1]
        compute1_name =  hostname = self.inputs.host_data[compute1]['name']

        vm1_fixture, vm1_ip, vm2_fixture, vm2_ip = self.create_verify_vn_vm(compute0_name, compute1_name, image_name)

        tap = vm1_fixture.get_tap_intf_of_vm()[0]['name']
        intf_details = self.agent_inspect[compute0].get_vna_intf_details(tap)
        vif_index = intf_details[0]['index']
        ip_addr = intf_details[0]['ip_addr']
        fq_name = intf_details[0]['config_name']

        vif_dict_before = self.get_drop_stats_dict(compute0, fq_name)
        self.print_drop_stats_dict(vif_dict_before)

        vrouter_dict_before = self.get_drop_stats_dict(compute0, module='vrouter')
        self.print_drop_stats_dict(vrouter_dict_before)

        assert not vm1_fixture.ping_to_ip(vm2_ip, count=ping_count)

        count = 0
        while True:
            vif_dict_after = self.get_drop_stats_dict(compute0, fq_name)
            vrouter_dict_after = self.get_drop_stats_dict(compute0, module='vrouter')
            vif_stats = self.verify_dropstats_of_type(drop_type, vif_dict_before,
                vif_dict_after, ping_count)
            vrouter_stats = self.verify_dropstats_of_type(drop_type, vrouter_dict_before,
                vrouter_dict_after, ping_count)
            if not vif_stats or not vrouter_stats:
                count = count + 1
                time.sleep(2)
                if count > 60:
                    result = result and False
                    mod = 'Vif'
                    if not vrouter_stats:
                        mod = 'Vrouter'
                    self.logger.error("%s dropstats of type %s failed" % (mod, drop_type))
                    break
            else:
                self.logger.info("Vif and vrouter dropstats of type %s verifed" % drop_type)
                break
        self.print_drop_stats_dict(vif_dict_after)
        self.print_drop_stats_dict(vrouter_dict_after)

        return result
    # end verify_flow_action_drop_stats

    def create_verify_vn_vm(self, compute0_name, compute1_name, image_name):

        vn1_fixture = self.create_vn()
        vn2_fixture = self.create_vn()

        vn1_fq_name = vn1_fixture.vn_fq_name
        vn2_fq_name = vn2_fixture.vn_fq_name

        vn1_name = vn1_fq_name.split(':')[2]
        vn2_name = vn2_fq_name.split(':')[2]

        policy_name_vn1_vn2 = get_random_name("vn1_vn2_deny")

        rules_vn1_vn2 = [{'direction': '<>',
                       'protocol': 'icmp',
                       'source_network': vn1_name,
                       'src_ports': [0, 65535],
                       'dest_network': vn2_name,
                       'dst_ports': [0, 65535],
                       'simple_action': 'deny',
                       'action_list': {'simple_action': 'deny'}
                       },
                       {'direction': '<>',
                       'protocol': 'icmp6',
                       'source_network': vn1_name,
                       'src_ports': [0, 65535],
                       'dest_network': vn2_name,
                       'dst_ports': [0, 65535],
                       'simple_action': 'deny',
                       'action_list': {'simple_action': 'deny'}
                       }]

        vm1_name = get_random_name("vm1")
        vm2_name = get_random_name("vm2")

        vm1_fixture = self.create_vm(
            vn_fixture=vn1_fixture, vm_name=vm1_name, node_name=compute0_name, image_name=image_name)
        vm2_fixture = self.create_vm(
            vn_fixture=vn2_fixture, vm_name=vm2_name, node_name=compute1_name, image_name=image_name)

        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        vm1_ip = vm1_fixture.get_vm_ips(vn1_fq_name)[0]
        vm2_ip = vm2_fixture.get_vm_ips(vn2_fq_name)[0]

        return vm1_fixture, vm1_ip, vm2_fixture, vm2_ip

   # end create_verify_vn_vm

    def verify_dropstats_of_type(self, drop_type, dict_before, dict_after, ping_count):
        result = True


        drop_before = int(dict_before[drop_type])
        drop_after = int(dict_after[drop_type])

        diff = drop_after - drop_before
        if diff != ping_count:
            result = result and False
        return result
    # end verify_dropstats_of_type
