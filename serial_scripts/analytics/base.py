import test_v1
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

class AnalyticsBaseTest(test_v1.BaseTestCase_v1):

    @classmethod
    def setUpClass(cls):
        super(AnalyticsBaseTest, cls).setUpClass()
        cls.quantum_h= cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib= cls.connections.vnc_lib
        cls.agent_inspect= cls.connections.agent_inspect
        cls.cn_inspect= cls.connections.cn_inspect
        cls.analytics_obj=cls.connections.analytics_obj
        cls.orch = cls.connections.orch 
        resource_class = cls.__name__ + 'Resource'
        cls.res = ResourceFactory.createResource(resource_class)
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        cls.res.cleanUp()
        super(AnalyticsBaseTest, cls).tearDownClass()
    #end tearDownClass

    def remove_from_cleanups(self, fix):
        for cleanup in self._cleanups:
            if fix.cleanUp in cleanup:
                self._cleanups.remove(cleanup)
                break
    #end remove_from_cleanups


    def test_cmd_output(self, cmd_type, cmd_args_list, check_output=False, form_cmd=True, as_sudo=False):
        failed_cmds = []
        passed_cmds = []
        result = True
        for cmd_args in cmd_args_list:
            cmd = cmd_args
            if form_cmd:
                cmd = self._form_cmd(cmd_type, cmd_args)
            self.logger.info("Running the following cmd:%s \n" %cmd)
            if not self.execute_cli_cmd(cmd, check_output, as_sudo=False):
                self.logger.error('%s command failed..' % cmd)
                failed_cmds.append(cmd)
                result = result and False
            else:
                passed_cmds.append(cmd)

        self.logger.info('%s commands passed..\n' % passed_cmds)
        self.logger.info('%s commands failed..\n ' % failed_cmds)
        return result
   # end test_cmd_output

    def _form_cmd(self, cmd_type, cmd_args):
        cmd = cmd_type
        for k, v in cmd_args.iteritems():
            if k == 'no_key':
                for elem in v:
                    cmd = cmd + ' --' +  elem
            else:
                cmd = cmd + ' --' + k + ' ' + v
        return cmd
    # _form_cmd

    def execute_cli_cmd(self, cmd, check_output=False, as_sudo=False):
        result = True
        analytics = self.res.inputs.collector_ips[0]
        output = self.res.inputs.run_cmd_on_server(analytics, cmd,
                                                   container='analytics', as_sudo=False)
        self.logger.info("Output: %s \n" % output)
        if output.failed:
            self.logger.error('%s command failed..' % cmd)
            result = result and False
        if check_output:
            output_str = str(output)
            if not output_str:
                self.logger.error("Output is empty")
                result = result and False
        return result
    # end execute_cli_cmd
    
    def setup_flow_export_rate(self, value):
        ''' Set flow export rate and handle the cleanup
        '''
        vnc_lib_fixture = self.connections.vnc_lib_fixture
        vnc_lib_fixture.set_flow_export_rate(value)
        self.addCleanup(vnc_lib_fixture.set_flow_export_rate,0)
    # end setup_flow_export_rate

    def verify_vna_stats(self,stat_type=None):
        result = True
        for vn in [self.res.vn1_fixture.vn_fq_name,\
                    self.res.vn2_fixture.vn_fq_name]:
            if stat_type == 'bandwidth_usage':
                #Bandwidth usage
                if not (int(self.analytics_obj.get_bandwidth_usage\
                        (self.inputs.collector_ips[0], vn, direction = 'out')) > 0):
                        self.logger.error("Bandwidth not shown  \
                                    in %s vn uve"%(vn))
                        result = result and False

                if not (int(self.analytics_obj.get_bandwidth_usage\
                        (self.inputs.collector_ips[0], vn, direction = 'in')) > 0):
                        self.logger.error("Bandwidth not shown  \
                                    in %s vn uve"%(vn))
                        result = result and False
            else:
                #ACL count
                if not (int(self.analytics_obj.get_acl\
                        (self.inputs.collector_ips[0],vn)) > 0):
                        self.logger.error("Acl counts not received from Agent uve \
                                    in %s vn uve"%(vn))
                        result = result and False

                if not (int(self.analytics_obj.get_acl\
                        (self.inputs.collector_ips[0], vn, tier = 'Config')) > 0):
                        self.logger.error("Acl counts not received from Config uve \
                                    in %s vn uve"%(vn))
                        result = result and False
                #Flow count
                if not (int(self.analytics_obj.get_flow\
                        (self.inputs.collector_ips[0], vn, direction = 'egress')) > 0):
                        self.logger.error("egress flow  not shown  \
                                    in %s vn uve"%(vn))
                        result = result and False

                if not (int(self.analytics_obj.get_flow\
                        (self.inputs.collector_ips[0], vn, direction = 'ingress')) > 0):
                        self.logger.error("ingress flow  not shown  \
                                    in %s vn uve"%(vn))
                        result = result and False

                #VN stats
                vns = [self.res.vn1_fixture.vn_fq_name,\
                        self.res.vn2_fixture.vn_fq_name]
                vns.remove(vn)
                other_vn = vns[0]
                if not (self.analytics_obj.get_vn_stats\
                        (self.inputs.collector_ips[0], vn, other_vn)):
                        self.logger.error("vn_stats   not shown  \
                                    in %s vn uve"%(vn))
                        result = result and False
        return result
    #end verify_vna_stats

class ResourceFactory:
    factories = {}
    def createResource(id):
        if not ResourceFactory.factories.has_key(id):
            ResourceFactory.factories[id] = \
              eval(id + '.Factory()')
        return ResourceFactory.factories[id].create()
    createResource = staticmethod(createResource)

class BaseSanityResource(fixtures.Fixture):
   
    __metaclass__ = Singleton
     
    def setUp(self,inputs,connections):
        super(BaseSanityResource , self).setUp()
        self.inputs = inputs
        self.connections = connections
        self.setup_sanity_common_objects(self.inputs , self.connections)

    def cleanUp(self):
        super(BaseSanityResource, self).cleanUp()

    def setup_sanity_common_objects(self, inputs , connections):
        self.inputs = inputs
        self.connections = connections
        self.orch = self.connections.orch
        self.logger = self.inputs.logger
        self.vn1_name = get_random_name("vn1")
        (self.vn1_vm1_name, self.vn1_vm2_name) = (get_random_name('vn1_vm1'),
                get_random_name('vn1_vm2'))

        self.vn1_fixture=self.useFixture( VNFixture(project_name= self.inputs.project_name,
                            connections= self.connections, inputs= self.inputs,
                            vn_name= self.vn1_name))

        host_list = self.orch.get_hosts()
        compute_1 = host_list[0]
        self.vn1_vm1_fixture=self.useFixture(VMFixture(project_name= self.inputs.project_name,
                                connections= self.connections, vn_obj= self.vn1_fixture.obj,
                                vm_name= self.vn1_vm1_name,image_name='ubuntu-traffic',
				flavor='contrail_flavor_medium', node_name=compute_1))

        self.vn1_vm2_fixture=self.useFixture(VMFixture(project_name= self.inputs.project_name,
                                connections= self.connections, vn_obj= self.vn1_fixture.obj,
                                vm_name= self.vn1_vm2_name , image_name='ubuntu-traffic',
				flavor='contrail_flavor_medium'))

        self.verify_sanity_common_objects()
    #end setup_common_objects

    def verify_sanity_common_objects(self):
        assert self.vn1_fixture.verify_on_setup()
        assert self.vn1_vm1_fixture.wait_till_vm_is_up()
        assert self.vn1_vm2_fixture.wait_till_vm_is_up()
    #end verify_common_objects


class BaseResource(BaseSanityResource):

    __metaclass__ = Singleton

    def setUp(self,inputs,connections):
        super(BaseResource , self).setUp(inputs, connections)
        self.setup_common_objects(self.inputs , self.connections)

    def cleanUp(self):
        super(BaseResource, self).cleanUp()

    def setup_common_objects(self, inputs , connections):
        (self.vn2_name, self.fip_vn_name) = (get_random_name("vn2"), get_random_name("fip_vn"))
        self.vn2_vm2_name = get_random_name('vn2_vm2')
        self.fvn_vm1_name = get_random_name('fvn_vm1')

        self.vn2_fixture = self.useFixture(VNFixture(
            project_name=self.inputs.project_name,
            connections=self.connections,
            inputs=self.inputs,
            vn_name=self.vn2_name))

        self.fvn_fixture = self.useFixture(VNFixture(
            project_name=self.inputs.project_name,
            connections=self.connections,
            inputs=self.inputs,
            vn_name=self.fip_vn_name))

        # Making sure VM falls on diffrent compute host
        self.orch = self.connections.orch 
        host_list = self.orch.get_hosts()
        compute_2 = host_list[0]
        if len(host_list) > 1:
            compute_2 = host_list[1]

        self.vn2_vm2_fixture=self.useFixture(VMFixture(project_name= self.inputs.project_name,
                            connections= self.connections, vn_obj= self.vn2_fixture.obj,
                            vm_name= self.vn2_vm2_name, image_name='ubuntu-traffic',
                            node_name=compute_2))
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
        super(BaseResource , self).verify_sanity_common_objects()
        assert self.vn2_fixture.verify_on_setup()
        assert self.fvn_fixture.verify_on_setup()
        assert self.fvn_vm1_fixture.wait_till_vm_is_up()
        assert self.vn2_vm2_fixture.wait_till_vm_is_up()
        assert self.multi_intf_vm_fixture.wait_till_vm_is_up()
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

class AnalyticsTestSanityWithMinResource(BaseSanityResource):

    def setUp(self,inputs,connections):
        super(AnalyticsTestSanityWithMinResource , self).setUp(inputs,connections)

    def cleanUp(self):
        super(AnalyticsTestSanityWithMinResource , self).cleanUp()

    class Factory:
        def create(self): return AnalyticsTestSanityWithMinResource()

class AnalyticsTestSanityResource(BaseResource): 

    def setUp(self,inputs,connections):
        pass
        #super(AnalyticsTestSanityResource , self).setUp(inputs,connections)

    def cleanUp(self):
        pass
        #super(AnalyticsTestSanityResource, self).cleanUp()

    class Factory:
        def create(self): return AnalyticsTestSanityResource()

class AnalyticsTestSanity1Resource(BaseResource):

    def setUp(self,inputs,connections):
        pass
        #super(AnalyticsTestSanity1Resource , self).setUp(inputs,connections)

    def cleanUp(self):
        pass
        #super(AnalyticsTestSanity1Resource, self).cleanUp()

    class Factory:
        def create(self): return AnalyticsTestSanity1Resource()


class AnalyticsTestSanity2Resource(BaseResource):

    def setUp(self,inputs,connections):
        pass
        #super(AnalyticsTestSanity2Resource , self).setUp(inputs,connections)

    def cleanUp(self):
        pass
        #super(AnalyticsTestSanity2Resource, self).cleanUp()

    class Factory:
        def create(self): return AnalyticsTestSanity2Resource()

class AnalyticsTestSanity3Resource(BaseResource):

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


