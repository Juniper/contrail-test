import test_v1
from common.connections import ContrailConnections
from common import isolated_creds

class BaseECMPRestartTest(test_v1.BaseTestCase_v1):

    @classmethod
    def setUpClass(cls):
        super(BaseECMPRestartTest, cls).setUpClass()
        cls.quantum_h= cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib= cls.connections.vnc_lib
        cls.agent_inspect= cls.connections.agent_inspect
        cls.cn_inspect= cls.connections.cn_inspect
        cls.analytics_obj=cls.connections.analytics_obj
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BaseECMPRestartTest, cls).tearDownClass()
    #end tearDownClass 

    def remove_from_cleanups(self, fix):
        for cleanup in self._cleanups:
        #    if fix.cleanUp in cleanup:
            self._cleanups.remove(cleanup)
            #break
   #end remove_from_cleanups

    def update_hash_on_network(self, ecmp_hash, vn_fixture):

        vn_config = self.vnc_lib.virtual_network_read(id = vn_fixture.uuid)
        vn_config.set_ecmp_hashing_include_fields(ecmp_hash)
        self.vnc_lib.virtual_network_update(vn_config)

    def update_hash_on_port(self, ecmp_hash, vm_fixture):
        key, vm_uuid = vm_fixture.get_vmi_ids().popitem()
        vm_config = self.vnc_lib.virtual_machine_interface_read(id = str(vm_uuid))
        vm_config.set_ecmp_hashing_include_fields(ecmp_hash)
        self.vnc_lib.virtual_machine_interface_update(vm_config)

    def config_all_hash(self, ecmp_hashing_include_fields):

        global_vrouter_id = self.vnc_lib.get_default_global_vrouter_config_id()
        global_config = self.vnc_lib.global_vrouter_config_read(id = global_vrouter_id)
        global_config.set_ecmp_hashing_include_fields(ecmp_hashing_include_fields)
        self.vnc_lib.global_vrouter_config_update(global_config)

    def verify_if_hash_changed(self, vn1_fixture, vm1_fixture, vm2_fixture, ecmp_hashing_include_fields):
        (domain, project, vn) = vn1_fixture.vn_fq_name.split(':')
        inspect_h = self.agent_inspect[vm1_fixture.vm_node_ip]
        agent_vrf_objs = inspect_h.get_vna_vrf_objs(domain, project, vn)
        agent_vrf_obj = vm1_fixture.get_matching_vrf(
                agent_vrf_objs['vrf_list'], vn1_fixture.vrf_name)
        vn_vrf_id = agent_vrf_obj['ucindex']
        next_hops = inspect_h.get_vna_active_route(
                     vrf_id=vn_vrf_id, ip=vm2_fixture.vm_ip, prefix='32')['path_list'][0]['nh']['mc_list'] 

        if not next_hops:
            result = False
            assert result, 'Route not found in the Agent %s' % vm2_fixture.vm_node_ip
        else:
            self.logger.info('Route found in the Agent %s' % vm2_fixture.vm_node_ip)
        next_hop_values = []
        for each_nh in next_hops:
            next_hop_values.append(each_nh['dip'])
        
        ecmp_field = inspect_h.get_vna_active_route(
                     vrf_id=vn_vrf_id, ip=vm2_fixture.vm_ip, prefix='32')['path_list'][0]['ecmp_hashing_fields']
        if not(ecmp_field == ecmp_hashing_include_fields):
            return False
        ecmp_keys = ecmp_hashing_include_fields.split(',')
        ri_fq_name = [self.inputs.domain_name, self.inputs.project_name, vn1_fixture.vn_name, vn1_fixture.vn_name]
        ri_obj = self.vnc_lib.routing_instance_read(fq_name=ri_fq_name)
        for node in self.inputs.bgp_ips:
            route_entry = self.cn_inspect[node].get_cn_route_table_entry(
                ri_name=ri_fq_name, prefix=vm2_fixture.vm_ip)
            if route_entry:
                for each_route_entry in route_entry:
                    if each_route_entry['protocol'] == 'ServiceChain':
                        if not(each_route_entry['next_hop'] in next_hop_values):
                            return False
                    for ecmp_key in ecmp_keys:
                        if ecmp_key:
                            if not('field-hash' in each_route_entry['load_balance'].values()[0]['decision_type'] and ecmp_key in each_route_entry['load_balance'].values()[0]['fields']):
                                return False 
