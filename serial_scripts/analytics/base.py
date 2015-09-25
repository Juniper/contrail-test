import test
from common import isolated_creds
from vn_test import *
from vm_test import *
import fixtures
sys.path.append(os.path.realpath('tcutils/pkgs/Traffic'))
from traffic.core.stream import Stream
from traffic.core.profile import create, ContinuousProfile, StandardProfile, BurstProfile, ContinuousSportRange
from traffic.core.helpers import Host
from traffic.core.helpers import Sender, Receiver
from tcutils.util import Singleton

class AnalyticsBaseTest(test.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(AnalyticsBaseTest, cls).setUpClass()
        cls.isolated_creds = isolated_creds.IsolatedCreds(cls.__name__, cls.inputs, ini_file = cls.ini_file, logger = cls.logger)
        cls.isolated_creds.setUp()
        cls.project = cls.isolated_creds.create_tenant() 
        cls.isolated_creds.create_and_attach_user_to_tenant()
        cls.inputs = cls.isolated_creds.get_inputs()
        cls.connections = cls.isolated_creds.get_conections() 
        cls.quantum_h= cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib= cls.connections.vnc_lib
        cls.agent_inspect= cls.connections.agent_inspect
        cls.cn_inspect= cls.connections.cn_inspect
        cls.analytics_obj=cls.connections.analytics_obj
        resource_class = cls.__name__ + 'Resource'
        cls.res = ResourceFactory.createResource(resource_class)
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        cls.res.cleanUp()
        cls.isolated_creds.delete_tenant()
        super(AnalyticsBaseTest, cls).tearDownClass()
    #end tearDownClass

    def remove_from_cleanups(self, fix):
        for cleanup in self._cleanups:
            if fix.cleanUp in cleanup:
                self._cleanups.remove(cleanup)
                break
    #end remove_from_cleanups

class ResourceFactory:
    factories = {}
    def createResource(id):
        if not ResourceFactory.factories.has_key(id):
            ResourceFactory.factories[id] = \
              eval(id + '.Factory()')
        return ResourceFactory.factories[id].create()
    createResource = staticmethod(createResource)


class BaseResource(fixtures.Fixture):
   
    __metaclass__ = Singleton
     
    def setUp(self,inputs,connections):
        super(BaseResource , self).setUp()
        self.inputs = inputs
        self.connections = connections
        self.setup_common_objects(self.inputs , self.connections)

    def cleanUp(self):
        super(BaseResource, self).cleanUp() 

    def setup_common_objects(self, inputs , connections):
  
    	self.inputs = inputs

        #self.inputs.set_af('dual')
        self.connections = connections
        self.logger = self.inputs.logger
        #(self.vn1_name, self.vn1_subnets)= ("vn1", ["192.168.1.0/24"])
        #(self.vn2_name, self.vn2_subnets)= ("vn2", ["192.168.2.0/24"])
        #(self.fip_vn_name, self.fip_vn_subnets)= ("fip_vn", ['100.1.1.0/24'])
        (self.vn1_name, self.vn2_name, self.fip_vn_name)= (get_random_name("vn1"), \
						get_random_name("vn2"),get_random_name("fip_vn"))
        (self.vn1_vm1_name, self.vn1_vm2_name)=( get_random_name('vn1_vm1'), get_random_name('vn1_vm2'))
        self.vn2_vm1_name= get_random_name('vn2_vm1')
        self.vn2_vm2_name= get_random_name('vn2_vm2')
        self.fvn_vm1_name= get_random_name('fvn_vm1')

        # Configure 3 VNs, one of them being Floating-VN
        self.vn1_fixture=self.useFixture( VNFixture(project_name= self.inputs.project_name,
                            connections= self.connections, inputs= self.inputs,
                            vn_name= self.vn1_name))

        self.vn2_fixture=self.useFixture( VNFixture(project_name= self.inputs.project_name,
                            connections= self.connections, inputs= self.inputs,
                            vn_name= self.vn2_name))

        self.fvn_fixture=self.useFixture( VNFixture(project_name= self.inputs.project_name,
                            connections= self.connections, inputs= self.inputs,
                            vn_name= self.fip_vn_name))

        # Making sure VM falls on diffrent compute host
        host_list = self.connections.nova_h.get_hosts()
        compute_1 = host_list[0]
        compute_2 = host_list[0]
        if len(host_list) > 1:
            compute_1 = host_list[0]
            compute_2 = host_list[1]
        # Configure 6 VMs in VN1, 1 VM in VN2, and 1 VM in FVN
        self.vn1_vm1_fixture=self.useFixture(VMFixture(project_name= self.inputs.project_name,
                                connections= self.connections, vn_obj= self.vn1_fixture.obj,
                                vm_name= self.vn1_vm1_name,image_name='ubuntu-traffic',
				flavor='contrail_flavor_medium', node_name=compute_1))

        self.vn1_vm2_fixture=self.useFixture(VMFixture(project_name= self.inputs.project_name,
                                connections= self.connections, vn_obj= self.vn1_fixture.obj,
                                vm_name= self.vn1_vm2_name , image_name='ubuntu-traffic',
				flavor='contrail_flavor_medium'))

        self.vn2_vm2_fixture=self.useFixture(VMFixture(project_name= self.inputs.project_name,
                            connections= self.connections, vn_obj= self.vn2_fixture.obj,
                            vm_name= self.vn2_vm2_name, image_name='ubuntu-traffic', flavor='contrail_flavor_medium',
                            node_name=compute_2))
#
        self.fvn_vm1_fixture=self.useFixture(VMFixture(project_name= self.inputs.project_name,
                                connections= self.connections, vn_obj= self.fvn_fixture.obj,
                                vm_name= self.fvn_vm1_name))

        self.multi_intf_vm_fixture = self.useFixture(VMFixture(connections=self.connections,
                                     vn_objs=[self.vn1_fixture.obj , self.vn2_fixture.obj],
                                     vm_name='mltf_vm',
                                     project_name=self.inputs.project_name))
    
        self.verify_common_objects()
    #end setup_common_objects

    def verify_common_objects(self):
        assert self.vn1_fixture.verify_on_setup()
        assert self.vn2_fixture.verify_on_setup()
        assert self.fvn_fixture.verify_on_setup()
        assert self.vn1_vm1_fixture.verify_on_setup()
        assert self.vn1_vm2_fixture.verify_on_setup()
        assert self.fvn_vm1_fixture.verify_on_setup()
        assert self.vn2_vm2_fixture.verify_on_setup()
        assert self.multi_intf_vm_fixture.verify_on_setup()
    #end verify_common_objects

    def start_traffic(self):
        # installing traffic package in vm
        self.vn1_vm1_fixture.install_pkg("Traffic")
        self.vn2_vm2_fixture.install_pkg("Traffic")
        self.fvn_vm1_fixture.install_pkg("Traffic")

        self.tx_vm_node_ip = self.vn1_vm1_fixture.vm_node_ip
        self.rx_vm_node_ip = self.vn2_vm2_fixture.vm_node_ip
        self.tx_local_host = Host(
                            self.tx_vm_node_ip, self.inputs.host_data[
                            self.tx_vm_node_ip]['username'], self.inputs.host_data[
                            self.tx_vm_node_ip]['password'])
        self.rx_local_host = Host(
                            self.rx_vm_node_ip, self.inputs.host_data[
                            self.rx_vm_node_ip]['username'], self.inputs.host_data[
                            self.rx_vm_node_ip]['password'])
        self.send_host = Host(self.vn1_vm1_fixture.local_ip,
                            self.vn1_vm1_fixture.vm_username,
                            self.vn1_vm1_fixture.vm_password)
        self.recv_host = Host(self.vn2_vm2_fixture.local_ip,
                            self.vn2_vm2_fixture.vm_username,
                            self.vn2_vm2_fixture.vm_password)
        # Create traffic stream
        self.logger.info("Creating streams...")
        stream = Stream(
            protocol="ip",
            proto="udp",
            src=self.vn1_vm1_fixture.vm_ip,
            dst=self.vn2_vm2_fixture.vm_ip,
            dport=9000)

        profile = StandardProfile(
            stream=stream,
            size=100,
            count=10,
            listener=self.vn2_vm2_fixture.vm_ip)
        self.sender = Sender(
            "sendudp",
            profile,
            self.tx_local_host,
            self.send_host,
            self.inputs.logger)
        self.receiver = Receiver(
            "recvudp",
            profile,
            self.rx_local_host,
            self.recv_host,
            self.inputs.logger)
        self.receiver.start()
        self.sender.start()
        time.sleep(10)

    def stop_traffic(self):
        self.sender.stop()
        self.receiver.stop()
        self.logger.info("Sent traffic: %s"%(self.sender.sent))
        self.logger.info("Received traffic: %s"%(self.receiver.recv))


class AnalyticsTestSanityResource (BaseResource): 

    def setUp(self,inputs,connections):
        pass
        #super(AnalyticsTestSanityResource , self).setUp(inputs,connections)

    def cleanUp(self):
        pass
        #super(AnalyticsTestSanityResource, self).cleanUp()

    class Factory:
        def create(self): return AnalyticsTestSanityResource()

class AnalyticsTestSanity1Resource (BaseResource):

    def setUp(self,inputs,connections):
        pass
        #super(AnalyticsTestSanity1Resource , self).setUp(inputs,connections)

    def cleanUp(self):
        pass
        #super(AnalyticsTestSanity1Resource, self).cleanUp()

    class Factory:
        def create(self): return AnalyticsTestSanity1Resource()


class AnalyticsTestSanity2Resource (BaseResource):

    def setUp(self,inputs,connections):
        pass
        #super(AnalyticsTestSanity2Resource , self).setUp(inputs,connections)

    def cleanUp(self):
        pass
        #super(AnalyticsTestSanity2Resource, self).cleanUp()

    class Factory:
        def create(self): return AnalyticsTestSanity2Resource()

class AnalyticsTestSanity3Resource (BaseResource):

    def setUp(self,inputs,connections):
        pass
        #super(AnalyticsTestSanity3Resource , self).setUp(inputs,connections)

    def cleanUp(self):
        pass
        #super(AnalyticsTestSanity3Resource, self).cleanUp()

    class Factory:
        def create(self): return AnalyticsTestSanity3Resource()

class AnalyticsTestSanityWithResourceResource(BaseResource):

    def setUp(self,inputs,connections):
        super(AnalyticsTestSanityWithResourceResource , self).setUp(inputs,connections)

    def cleanUp(self):
        super(AnalyticsTestSanityWithResourceResource, self).cleanUp()

    class Factory:
        def create(self): return AnalyticsTestSanityWithResourceResource()
#End resource


