import test
from common.connections import ContrailConnections
from common import isolated_creds
from vm_test import VMFixture
from vn_test import VNFixture
from tcutils.util import retry


class BaseRtFilterTest(test.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(BaseRtFilterTest, cls).setUpClass()
        cls.isolated_creds = isolated_creds.IsolatedCreds(cls.__name__,
                                                          cls.inputs, ini_file=cls.ini_file,
                                                          logger=cls.logger)
        cls.isolated_creds.setUp()
        cls.project = cls.isolated_creds.create_tenant()
        cls.isolated_creds.create_and_attach_user_to_tenant()
        cls.inputs = cls.isolated_creds.get_inputs()
        cls.connections = cls.isolated_creds.get_conections()
        #cls.connections= ContrailConnections(cls.inputs)
        cls.quantum_h = cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib = cls.connections.vnc_lib
#        cls.logger= cls.inputs.logger
        cls.agent_inspect = cls.connections.agent_inspect
        cls.cn_inspect = cls.connections.cn_inspect
        cls.analytics_obj = cls.connections.analytics_obj
        cls.api_s_inspect = cls.connections.api_server_inspect
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        # cls.isolated_creds.delete_user()
        cls.isolated_creds.delete_tenant()
        super(BaseRtFilterTest, cls).tearDownClass()
    # end tearDownClass

    def remove_from_cleanups(self, fix):
        for cleanup in self._cleanups:
            if fix.cleanUp in cleanup:
                self._cleanups.remove(cleanup)
                break
   # end remove_from_cleanups

    def create_vn(self, vn_name, vn_subnets):
        return self.useFixture(
            VNFixture(project_name=self.inputs.project_name,
                      connections=self.connections,
                      inputs=self.inputs,
                      vn_name=vn_name,
                      subnets=vn_subnets))

    def create_vm(self, vn_fixture, vm_name, node_name=None,
                  flavor='contrail_flavor_small',
                  image_name='ubuntu-traffic'):
        return self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=vn_fixture.obj,
                vm_name=vm_name,
                image_name=image_name,
                flavor=flavor,
                node_name=node_name))

    @retry(delay=5, tries=10)
    def verify_rt_group_entry(self, control_node, route_target):
        rt_group_entry = self.cn_inspect[
            control_node].get_cn_rtarget_group(route_target)
        result = False
        if rt_group_entry is None:
            result = False
            self.logger.warn(
                'No entry for RT %s seen in the RTGroup Table of control nodes' % route_target)
        else:
            result = True
            self.logger.info(
                'RT %s seen in the RTGroup Table of control node-%s' % (route_target, control_node))
        return result
    # end verify_rt_group_entry

    @retry(delay=5, tries=10)
    def verify_dep_rt_entry(self, control_node, route_target, ip):
        rt_group_entry = self.cn_inspect[
            control_node].get_cn_rtarget_group(route_target)
        result = False
        if rt_group_entry is not None:
            for y in rt_group_entry['dep_route']:
                if ip in y:
                    result = True
                    self.logger.info('IP %s is seen in the dep_routes of RT %s in the RTGroup Table of ctrl_node %s' % (
                        ip, route_target, control_node))
                    break
                else:
                    result = False
        else:
            self.logger.warn('IP %s is not seen in the dep_routes of RT %s in the RTGroup Table of ctrl_node %s' % (
                ip, route_target, control_node))
        return result
    # end verify_dep_rt_entry

    @retry(delay=5, tries=10)
    def verify_dep_rt_entry_removal(self, control_node, route_target, ip):
        rt_group_entry = self.cn_inspect[
            control_node].get_cn_rtarget_group(route_target)
        result = True
        if rt_group_entry['dep_route'] is not None:
            for y in rt_group_entry['dep_route']:
                if ip in y:
                    result = False
                    self.logger.warn('IP %s is still seen in the dep_routes of RT %s in the RTGroup Table of ctrl_node %s' % (
                        ip, route_target, control_node))
                    break
        if result == True:
            self.logger.info('IP %s not seen in the dep_routes of RT %s in the RTGroup Table of ctrl_node %s' % (
                ip, route_target, control_node))
        return result
    # end verify_dep_rt_entry_removal

    @retry(delay=5, tries=10)
    def verify_rtarget_table_entry(self, control_node, route_target):
        rt_table_entry = self.cn_inspect[control_node].get_cn_rtarget_table()
        result = False
        for rt_entry in rt_table_entry:
            if route_target in rt_entry['prefix']:
                result = True
                self.logger.info(
                    'RT %s seen in the bgp.rtarget.0 table of the control node-%s' % (route_target, control_node))
                break
        if result == False:
            self.logger.warn(
                'RT %s not seen in the bgp.rtarget.0 table of the control nodes' % route_target)
        return result
    # end verify_rtarget_table_entry

    @retry(delay=5, tries=10)
    def verify_rt_entry_removal(self, control_node, route_target):
        rt_group_entry = self.cn_inspect[
            control_node].get_cn_rtarget_group(route_target)
        rt_table_entry = self.cn_inspect[control_node].get_cn_rtarget_table()
        result = True
        sub_result = True
        for rt_entry in rt_table_entry:
            if route_target in rt_entry['prefix']:
                result = False
                break
        if result == True:
            self.logger.info(
                'RT %s removed from the bgp.rtarget.0 table' % route_target)
        else:
            self.logger.warn(
                'RT %s is still seen in the bgp.rtarget.0 table of the control nodes' % route_target)
        if rt_group_entry is None:
            self.logger.info(
                'RT %s removed from the RTGroup Table of the control nodes' % route_target)
        else:
            sub_result = False
            self.logger.warn(
                '%s still seen in the RTGroup Table of the control nodes' % route_target)
        return result and sub_result
    # end verify_rt_entry_removal

    def get_active_control_node(self, vm):
        active_controller = None
        inspect_h1 = self.agent_inspect[vm.vm_node_ip]
        agent_xmpp_status = inspect_h1.get_vna_xmpp_connection_status()
        for entry in agent_xmpp_status:
            if entry['cfg_controller'] == 'Yes':
                active_controller = entry['controller_ip']
                new_controller = self.inputs.host_data[
                    active_controller]['host_ip']
        self.logger.info('Active control node is %s' % new_controller)
        return new_controller
    # end get_active_control_node

    @retry(delay=2, tries=5)
    def remove_rt_filter_family(self):
        mx = self.vnc_lib.bgp_router_read(
            fq_name=[u'default-domain', u'default-project', u'ip-fabric', u'__default__', unicode(self.inputs.ext_routers[0][0])])
        mx.bgp_router_parameters.get_address_families().set_family(
            [u'inet-vpn'])
        mx._pending_field_updates.add('bgp_router_parameters')
        for rt_refs in mx.bgp_router_refs:
            curr_fam = rt_refs['attr'].get_session()[0].get_attributes()[
                0].get_address_families().get_family()
            self.logger.info('With %s, the session has the following capablities : %s' % (
                rt_refs['to'][-1], curr_fam))
            rt_refs['attr'].get_session()[0].get_attributes()[
                0].get_address_families().set_family([u'inet-vpn'])
        mx._pending_field_updates.add('bgp_router_refs')
        self.vnc_lib.bgp_router_update(mx)
        return True
    # end remove_rt_filter_family

    @retry(delay=2, tries=5)
    def add_rt_filter_family(self):
        mx = self.vnc_lib.bgp_router_read(
            fq_name=[u'default-domain', u'default-project', u'ip-fabric', u'__default__', unicode(self.inputs.ext_routers[0][0])])
        mx.bgp_router_parameters.get_address_families().set_family(
            [u'route-target', u'inet-vpn'])
        mx._pending_field_updates.add('bgp_router_parameters')
        for rt_refs in mx.bgp_router_refs:
            curr_fam = rt_refs['attr'].get_session()[0].get_attributes()[
                0].get_address_families().get_family()
            self.logger.info('With %s, the session has the following capablities : %s' % (
                rt_refs['to'][-1], curr_fam))
            rt_refs['attr'].get_session()[0].get_attributes()[
                0].get_address_families().set_family([u'route-target', u'inet-vpn'])
        mx._pending_field_updates.add('bgp_router_refs')
        self.vnc_lib.bgp_router_update(mx)
        return True
    # end add_rt_filter_family
