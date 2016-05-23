import test_v1
from common.connections import ContrailConnections
from common import isolated_creds

class BaseECMPTest(test_v1.BaseTestCase_v1):

    @classmethod
    def setUpClass(cls):
        super(BaseECMPTest, cls).setUpClass()
        cls.quantum_h= cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib= cls.connections.vnc_lib
        cls.agent_inspect= cls.connections.agent_inspect
        cls.cn_inspect= cls.connections.cn_inspect
        cls.analytics_obj=cls.connections.analytics_obj
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BaseECMPTest, cls).tearDownClass()
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
        import pdb;pdb.set_trace()
        key, vm_uuid = vm_fixture.vmi_ids.popitem()
        vm_config = self.vnc_lib.virtual_machine_interface_read(id = str(vm_uuid))
        vm_config.set_ecmp_hashing_include_fields(ecmp_hash)
        self.vnc_lib.virtual_machine_interface_update(vm_config)

    def config_all_hash(self, ecmp_hashing_include_fields):

        global_vrouter_id = self.vnc_lib.get_default_global_vrouter_config_id()
        global_config = self.vnc_lib.global_vrouter_config_read(id = global_vrouter_id)
        global_config.set_ecmp_hashing_include_fields(ecmp_hashing_include_fields)
        self.vnc_lib.global_vrouter_config_update(global_config)

    def verify_if_hash_changed(self, ecmp_hashing_include_fields):
        paths = inspect_h9.get_vna_active_route(
                vrf_id=fvn_vrf_id9, ip=self.res.my_fip, prefix='32')['path_list']  
