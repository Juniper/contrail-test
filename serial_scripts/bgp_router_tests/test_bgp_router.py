from tcutils.commands import *
from tcutils.util import retry
from tcutils.wrappers import preposttest_wrapper
import base
import re
from time import sleep
from control_node import CNFixture

class BgpRouterTest(base.BaseBgpRouterTest):
    
    @classmethod
    def setUpClass(cls):
        super(BgpRouterTest, cls).setUpClass()
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BgpRouterTest, cls).tearDownClass()
    #end tearDownClass
    
    @preposttest_wrapper
    def test_control_node_bgp_peer(self):
        '''Control node should not be Active if it doesn't have bgp-router for self 
        1)delete bgp_router of control node
        2)check contrail-status for control-service  
        3)Test passed if control service is inactive with message No BGP configuration for self
        '''
        cn_fixture = self.get_cn_fixture()
        cn_status = 'contrail-status'
        check_str ='No BGP configuration for self'
        self.logger.info('Deleting control node bgp peer %s' %self.control_ip)
        cn_fixture.del_cn_node(self.control_ip)
        output=self.inputs.run_cmd_on_server(self.control_ip,cn_status)
        if check_str not in output:
            self.logger.info('Control node should not be Active if it does not have bgp-router for self.Test failed')
            cn_fixture.create_cn_node(self.control_ip,self.router_type)
            return False
        cn_fixture.create_cn_node(self.control_ip,self.router_type)
        result=self.inputs.verify_service_state(self.control_ip,'contrail-control',self.cn_user,self.cn_password)
        assert result,'Contrail-Control service is inactive'
        self.logger.info('Control service is inactive and has message No BGP configuration for self.Test Passed')  
    #end test_control_node_bgp_peer
    
    @preposttest_wrapper
    def test_bgp_peer_passive(self):
        '''Test passive knob of bgp_router
           1)check  bgp_peers present or not
           2)if present set bgp_peer as passive for any bgp_router 
           3)verify state of bgp_peer in introspect.
           4)If passive is True and state is Active,Test passed'''
        cn_fixture = self.get_cn_fixture()
        assert cn_fixture.verify_peer_in_control_nodes()
        bgp_list = self.vnc_lib.bgp_routers_list()
        bgp_list = str(bgp_list)
        list_uuids = re.findall('u\'uuid\': u\'([a-zA-Z0-9-]+)\'', bgp_list)
        bgp_obj = self.vnc_lib.bgp_router_read(id=list_uuids[0])
        bgp_control_ip = bgp_obj.get_bgp_router_parameters().get_address()
        bgp_refs = bgp_obj.get_bgp_router_refs()
        bgp_session = bgp_refs[0]['attr'].get_session()
        bgp_attr = bgp_session[0].get_attributes()
        bgp_attr[0].set_passive(True)
        bgp_obj._pending_field_updates.add('bgp_router_refs')
        self.vnc_lib.bgp_router_update(bgp_obj)
        self.logger.info('Bgp peer is set to passive,verifying in introspect')
        peer_uuid = bgp_refs[0]['uuid']
        peer_obj = self.vnc_lib.bgp_router_read(id=peer_uuid)
        peer_name = peer_obj.name
        sleep(20)
        host_ip = self.inputs.host_data[bgp_control_ip]['host_ip']
        cn_bgp_entry = self.cn_inspect[
            host_ip].get_cn_bgp_neigh_entry(encoding='BGP')
        for entry in cn_bgp_entry:
            if entry['peer'] == peer_name:
                if (entry['encoding'] == 'BGP') and (entry['passive'] == 'true') and (entry['state'] == 'Active'):
                    self.logger.info('Verification in introspect passed')
                    bgp_attr[0].set_passive(False)
                    bgp_obj._pending_field_updates.add('bgp_router_refs')
                    self.vnc_lib.bgp_router_update(bgp_obj)
                    sleep(20)
                    assert cn_fixture.verify_peer_in_control_nodes(),'Failed to Reset the passive knob'
                    self.logger.info('Succesfully tested bgp_peer passive knob.Test_passed')
                    return       
        assert False,'Failed to set and verify bgp_peer passive knob.Test Failed'
        #assert False,'Test Failed'
    #end test_bgp_peer_passive

        
    @preposttest_wrapper
    def test_bgp_peer_admin_down(self):
        '''Test admin_down knob of bgp_router
           1)check  bgp_peers present or not
           2)if present set admin down to one of bgp_router 
           3)verify state of bgp_peer in introspect.
           4)If admin_down is True and state is Idle,Test passed'''
        cn_fixture = self.get_cn_fixture()
        assert cn_fixture.verify_peer_in_control_nodes()
        bgp_list = self.vnc_lib.bgp_routers_list()
        bgp_list = str(bgp_list)
        list_uuids = re.findall('u\'uuid\': u\'([a-zA-Z0-9-]+)\'', bgp_list)
        bgp_obj = self.vnc_lib.bgp_router_read(id=list_uuids[0])
        bgp_params = bgp_obj.get_bgp_router_parameters()
        bgp_params.set_admin_down(True)
        bgp_control_ip = bgp_params.get_address()
        bgp_obj._pending_field_updates.add('bgp_router_parameters')
        self.vnc_lib.bgp_router_update(bgp_obj)
        self.logger.info('Bgp peer is set to admin down ,verifying in introspect')
        sleep(20)
        host_ip = self.inputs.host_data[bgp_control_ip]['host_ip']
        cn_bgp_entry = self.cn_inspect[
            host_ip].get_cn_bgp_neigh_entry(encoding='BGP')
        for entry in cn_bgp_entry:
            if (entry['encoding'] == 'BGP') and (entry['admin_down'] == 'true') and (
                                entry['state'] == 'Idle') and (entry['send_state'] == 'not advertising'):
                continue
            else:
                assert False,'Failed to set and verify bgp_router admin_down knob.Test Failed'
        self.logger.info('Verification in introspect passed')
        bgp_params.set_admin_down(False)
        bgp_obj._pending_field_updates.add('bgp_router_parameters')
        self.vnc_lib.bgp_router_update(bgp_obj)
        sleep(20)
        assert cn_fixture.verify_peer_in_control_nodes(),'Failed to Reset the admin_down knob'
        self.logger.info('Succesfully tested bgp_router admin_down knob.Test_passed')
    #end test_bgp_peer_admin_down


    @preposttest_wrapper
    def test_bgp_router_local_AS(self):
        pass
    
