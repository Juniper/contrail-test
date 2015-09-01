try:
    from common.openstack_libs import neutron_exception
    BadCall = neutron_exception.BadRequest
except Exception,e:
    # In Icehouse, python-neutronclient does not have BadRequest yet
    from common.openstack_libs import neutron_client_exception as BadCall

from common.tor.base import *
from tcutils.wrappers import preposttest_wrapper


class TestBMSNegative(BaseTorTest):

    @classmethod
    def setUpClass(cls):
        super(TestBMSNegative, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestBMSNegative, cls).tearDownClass()

    def setUp(self):
        super(TestBMSNegative, self).setUp()
        [self.tor1_fixture, self.tor2_fixture] = self.setup_tors(count=2)

    def is_test_applicable(self):
        if len(self.get_available_devices('tor')) < 2 :
            return (False, 'Skipping Test. Atleast 2 ToRs required in the Test cluster')
        if len(self.inputs.tor_hosts_data.keys()) == 0 :
            return (False, 'Skipping Test. No BMS details seen in the Test cluster')
        return (True, None)

    @preposttest_wrapper
    def test_vmi_delete_when_lif_bound(self):
        result = True
        vn1_fixture = self.create_vn()
        port_fixture = self.setup_vmi(vn1_fixture.uuid)
        (pif_fixture, lif_fixture) = self.setup_tor_port(self.tor1_fixture,
            port_index=0, vmi_objs=[port_fixture])
        try:
            port_fixture.neutron_handle.delete_port(port_fixture.uuid)
            self.logger.error('Port with lif attached was allowed to be '
                'deleted!!')
            result = result and True
        except BadCall, e:
            self.logger.info('Port with lif attached was not allowed to be '
                'deleted...OK')

        assert result, 'Port with lif attached was allowed to be deleted'
    # end test_vmi_delete_when_lif_bound
        


