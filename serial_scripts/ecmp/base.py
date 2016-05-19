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

    def update_hash_on_network(ecmp_hash, vn_fixture):

        vn_config = self.vnc_lib.virtual_network_read(id = vn_fixture.uuid)
        vn_config.set_ecmp_hashing_include_fields(ecmp_hash)
        self.vnc_lib.virtual_network_update(vn_config)

    def update_hash_on_port(ecmp_hash, vm_fixture):

        vm_config = self.vnc_lib.virtual_machine_interface_read(id = vm_fixture.uuid)
        vm_config.set_ecmp_hashing_include_fields(ecmp_hash)
        self.vnc_lib.virtual_machine_interface_update(vm_config)

    def config_all_hash(self):

        ecmp_hashing_include_fields = {"destination_ip": True, "destination_port": True, "hashing_configured": True, "ip_protocol": True, "source_ip": True, "source_port": True}
        global_vrouter_id = self.vnc_lib.get_default_global_vrouter_config_id()
        global_config = self.vnc_lib.global_vrouter_config_read(id = global_vrouter_id)
        global_config.set_ecmp_hashing_include_fields(ecmp_hashing_include_fields)
        self.vnc_lib.global_vrouter_config_update(global_config)

