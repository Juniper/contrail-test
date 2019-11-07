from base import BaseDockerTest
from tcutils.util import get_random_name
from tcutils.wrappers import preposttest_wrapper

class TestBasicDocker(BaseDockerTest):

    @classmethod
    def setUpClass(cls):
        super(TestBasicDocker, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestBasicDocker, cls).tearDownClass()

    @preposttest_wrapper
    def test_ping_within_vn(self):
        '''
        Description:  Validate Ping between 2 docker's in the same VN.
        Test steps:
               1. Create a VN and launch 2 docker's in it.
        Pass criteria: Ping between the docker's should go thru fine.
        Maintainer : ijohnson@juniper.net
        '''
        vn1_name = get_random_name('docker_vn')
        vn1_docker1_name = get_random_name('docker1')
        vn1_docker2_name = get_random_name('docker2')
        vn1_fixture = self.create_vn(vn_name=vn1_name)
        assert vn1_fixture.verify_on_setup()
        docker1_fixture = self.create_docker(vn_fixture=vn1_fixture, vm_name=vn1_docker1_name)
        docker2_fixture = self.create_docker(vn_fixture=vn1_fixture, vm_name=vn1_docker2_name)
        assert docker1_fixture.verify_on_setup()
        assert docker2_fixture.verify_on_setup()
        docker1_fixture.wait_till_vm_is_up()
        docker2_fixture.wait_till_vm_is_up()
        assert docker1_fixture.ping_with_certainty(dst_vm_fixture=docker2_fixture),\
            "Ping from %s to %s failed" % (vn1_docker1_name, vn1_docker2_name)
        assert docker2_fixture.ping_with_certainty(dst_vm_fixture=docker1_fixture),\
            "Ping from %s to %s failed" % (vn1_docker2_name, vn1_docker1_name)
        return True
