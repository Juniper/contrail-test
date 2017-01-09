import test
import fixtures
from common import isolated_creds

class BaseEvpnTest(test.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(BaseEvpnTest, cls).setUpClass()
        cls.isolated_creds = isolated_creds.IsolatedCreds(cls.__name__, \
				cls.inputs, ini_file = cls.ini_file, \
				logger = cls.logger)
        cls.isolated_creds.setUp()
        cls.project = cls.isolated_creds.create_tenant() 
        cls.isolated_creds.create_and_attach_user_to_tenant()
        cls.inputs = cls.isolated_creds.get_inputs()
        cls.connections = cls.isolated_creds.get_conections() 
        #cls.connections= ContrailConnections(cls.inputs)
        cls.quantum_h= cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib= cls.connections.vnc_lib
#        cls.logger= cls.inputs.logger
        cls.agent_inspect= cls.connections.agent_inspect
        cls.cn_inspect= cls.connections.cn_inspect
        cls.analytics_obj=cls.connections.analytics_obj
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        #cls.isolated_creds.delete_user()
        cls.isolated_creds.delete_tenant()
        super(BaseEvpnTest, cls).tearDownClass()
    #end tearDownClass 

    def remove_from_cleanups(self, fix):
        for cleanup in self._cleanups:
        #    if fix.cleanUp in cleanup:
            self._cleanups.remove(cleanup)
            #break
    #end remove_from_cleanups

    def update_encap_priority(self, encap):
        self.logger.info("Read the existing encap priority")
        existing_encap = self.connections.read_vrouter_config_encap()
        if (encap == 'gre'):
            config_id = self.connections.update_vrouter_config_encap(
                'MPLSoGRE', 'MPLSoUDP', 'VXLAN')
            self.logger.info(
                'Created.UUID is %s. MPLSoGRE is the highest priority encap' %
                (config_id))
            configured_encap_list = [
                unicode('MPLSoGRE'), unicode('MPLSoUDP'), unicode('VXLAN')]
            if existing_encap != configured_encap_list :
                self.addCleanup(self.connections.update_vrouter_config_encap, existing_encap[0], existing_encap[1], existing_encap[2])
        elif (encap == 'udp'):
            config_id = self.connections.update_vrouter_config_encap(
                'MPLSoUDP', 'MPLSoGRE', 'VXLAN')
            self.logger.info(
                'Created.UUID is %s. MPLSoUDP is the highest priority encap' %
                (config_id))
            configured_encap_list = [
                unicode('MPLSoUDP'), unicode('MPLSoGRE'), unicode('VXLAN')]
            if existing_encap != configured_encap_list :
                self.addCleanup(self.connections.update_vrouter_config_encap, existing_encap[0], existing_encap[1], existing_encap[2])
        elif (encap == 'vxlan'):
            config_id = self.connections.update_vrouter_config_encap(
                'VXLAN', 'MPLSoUDP', 'MPLSoGRE')
            self.logger.info(
                'Created.UUID is %s. VXLAN is the highest priority encap' %
                (config_id))
            configured_encap_list = [
                unicode('VXLAN'), unicode('MPLSoUDP'), unicode('MPLSoGRE')]
            if existing_encap != configured_encap_list :
                self.addCleanup(self.connections.update_vrouter_config_encap, existing_encap[0], existing_encap[1], existing_encap[2])

    # end update_encap_priority
