import test_v1
from vn_test import MultipleVNFixture
from common.device_connection import NetconfConnection
import physical_device_fixture
from physical_router_fixture import PhysicalRouterFixture
from tcutils.contrail_status_check import *
from fabric.api import run, hide, settings
from vm_test import MultipleVMFixture
from vn_test import VNFixture
from vm_test import VMFixture
from vnc_api.vnc_api import *
from policy_test import PolicyFixture
from tcutils.util import get_random_name
from scripts.securitygroup.verify import VerifySecGroup
from common.policy.config import ConfigPolicy
from common import isolated_creds
import os
import re
from time import sleep

class Md5Base(test_v1.BaseTestCase_v1, VerifySecGroup, ConfigPolicy):

    @classmethod
    def setUpClass(cls):
        super(Md5Base, cls).setUpClass()
        cls.quantum_h = cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib = cls.connections.vnc_lib
        cls.agent_inspect = cls.connections.agent_inspect
        cls.cn_inspect = cls.connections.cn_inspect
        cls.analytics_obj = cls.connections.analytics_obj
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(Md5Base, cls).tearDownClass()
    # end tearDownClass

    def setUp(self):
        super(Md5Base, self).setUp()

    def tearDown(self):
        super(Md5Base, self).tearDown()

    def config_basic(self, is_mx_present):
        #mx config using device manager
        if is_mx_present:   
            if self.inputs.ext_routers:
                if self.inputs.use_devicemanager_for_md5:
                    router_params = self.inputs.physical_routers_data.values()[0]
                    self.phy_router_fixture = self.useFixture(PhysicalRouterFixture(
                        router_params['name'], router_params['mgmt_ip'],
                        model=router_params['model'],
                        vendor=router_params['vendor'],
                        asn=router_params['asn'],
                        ssh_username=router_params['ssh_username'],
                        ssh_password=router_params['ssh_password'],
                        mgmt_ip=router_params['mgmt_ip'],
                        connections=self.connections))
        else:
            if self.inputs.ext_routers:
                router_params = self.inputs.physical_routers_data.values()[0]
                cmd = []
                cmd.append('set groups md5_tests routing-options router-id %s' % router_params['mgmt_ip'])
                cmd.append('set groups md5_tests routing-options route-distinguisher-id %s' % router_params['mgmt_ip'])
                cmd.append('set groups md5_tests routing-options autonomous-system %s' % router_params['asn'])
                cmd.append('set groups md5_tests protocols bgp group md5_tests type internal')
                cmd.append('set groups md5_tests protocols bgp group md5_tests multihop')
                cmd.append('set groups md5_tests protocols bgp group md5_tests local-address %s' % router_params['mgmt_ip'])
                cmd.append('set groups md5_tests protocols bgp group md5_tests hold-time 90')
                cmd.append('set groups md5_tests protocols bgp group md5_tests keep all')
                cmd.append('set groups md5_tests protocols bgp group md5_tests family inet-vpn unicast')
                cmd.append('set groups md5_tests protocols bgp group md5_tests family inet6-vpn unicast')
                cmd.append('set groups md5_tests protocols bgp group md5_tests family evpn signaling')
                cmd.append('set groups md5_tests protocols bgp group md5_tests family route-target')
                cmd.append('set groups md5_tests protocols bgp group md5_tests local-as %s' % router_params['asn'])
                for node in self.inputs.bgp_control_ips:
                    cmd.append('set groups md5_tests protocols bgp group md5_tests neighbor %s peer-as %s' % (node, router_params['asn']))
                cmd.append('set apply-groups md5_tests')
                mx_handle = NetconfConnection(host = router_params['mgmt_ip'])
                mx_handle.connect()
                cli_output = mx_handle.config(stmts = cmd, timeout = 120) 
        vn61_name = "test_vnv6sr"
        vn61_net = ['2001::101:0/120']
        #vn1_fixture = self.config_vn(vn1_name, vn1_net)
        vn61_fixture = self.useFixture(VNFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_name=vn61_name, inputs=self.inputs, subnets=vn61_net))
        vn62_name = "test_vnv6dn"
        vn62_net = ['2001::201:0/120']
        #vn2_fixture = self.config_vn(vn2_name, vn2_net)
        vn62_fixture = self.useFixture(VNFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_name=vn62_name, inputs=self.inputs, subnets=vn62_net))
        vm61_name = 'source_vm'
        vm62_name = 'dest_vm'
        #vm1_fixture = self.config_vm(vn1_fixture, vm1_name)
        #vm2_fixture = self.config_vm(vn2_fixture, vm2_name)
        vm61_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_obj=vn61_fixture.obj, vm_name=vm61_name, node_name=None,
            image_name='cirros-0.3.0-x86_64-uec', flavor='m1.tiny'))

        vm62_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_obj=vn62_fixture.obj, vm_name=vm62_name, node_name=None,
            image_name='cirros-0.3.0-x86_64-uec', flavor='m1.tiny'))
        vm61_fixture.wait_till_vm_is_up()
        vm62_fixture.wait_till_vm_is_up()

        rule = [
            {
                'direction': '<>',
                'protocol': 'any',
                'source_network': vn61_name,
                'src_ports': [0, -1],
                'dest_network': vn62_name,
                'dst_ports': [0, -1],
                'simple_action': 'pass',
            },
        ]
        policy_name = 'allow_all'
        policy_fixture = self.config_policy(policy_name, rule)

        vn61_policy_fix = self.attach_policy_to_vn(
            policy_fixture, vn61_fixture)
        vn62_policy_fix = self.attach_policy_to_vn(
            policy_fixture, vn62_fixture)

        vn1 = "vn1"
        vn2 = "vn2"
        vn_s = {'vn1': '10.1.1.0/24', 'vn2': ['20.1.1.0/24']}
        rules = [
            {
                'direction': '<>',
                'protocol': 'any',
                'source_network': vn1,
                'src_ports': [0, -1],
                'dest_network': vn2,
                'dst_ports': [0, -1],
                'simple_action': 'pass',
            },
        ]

        self.logger.info("Configure the policy with allow any")
        self.multi_vn_fixture = self.useFixture(MultipleVNFixture(
            connections=self.connections, inputs=self.inputs, subnet_count=2,
            vn_name_net=vn_s,  project_name=self.inputs.project_name))
        vns = self.multi_vn_fixture.get_all_fixture_obj()
        (self.vn1_name, self.vn1_fix) = self.multi_vn_fixture._vn_fixtures[0]
        (self.vn2_name, self.vn2_fix) = self.multi_vn_fixture._vn_fixtures[1]
        self.config_policy_and_attach_to_vn(rules)

        self.multi_vm_fixture = self.useFixture(MultipleVMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vm_count_per_vn=1, vn_objs=vns, image_name='cirros-0.3.0-x86_64-uec',
            flavor='m1.tiny'))
        vms = self.multi_vm_fixture.get_all_fixture()
        (self.vm1_name, self.vm1_fix) = vms[0]
        (self.vm2_name, self.vm2_fix) = vms[1]

    def config_policy_and_attach_to_vn(self, rules):
        randomname = get_random_name()
        policy_name = "sec_grp_policy_" + randomname
        policy_fix = self.config_policy(policy_name, rules)
        policy_vn1_attach_fix = self.attach_policy_to_vn(
            policy_fix, self.vn1_fix)
        policy_vn2_attach_fix = self.attach_policy_to_vn(
            policy_fix, self.vn2_fix)

    def config_md5(self, host, auth_data):
        rparam = self.vnc_lib.bgp_router_read(id=host).bgp_router_parameters
        list_uuid = self.vnc_lib.bgp_router_read(id=host)
        rparam.set_auth_data(auth_data)
        list_uuid.set_bgp_router_parameters(rparam)
        self.vnc_lib.bgp_router_update(list_uuid)

    def check_bgp_status(self, is_mx_present=False):
        result = True
        self.cn_inspect = self.connections.cn_inspect
                # Verify the connection between all control nodes and MX(if
                # present)
        host = self.inputs.bgp_ips[0]
        cn_bgp_entry = self.cn_inspect[host].get_cn_bgp_neigh_entry()
        if not is_mx_present:
            if self.inputs.ext_routers:
                for bgpnodes in cn_bgp_entry:
                    bgpnode = str(bgpnodes)
                    if self.inputs.ext_routers[0][0] in bgpnode:
                        cn_bgp_entry.remove(bgpnodes)
                cn_bgp_entry = str(cn_bgp_entry)

        cn_bgp_entry = str(cn_bgp_entry)
        est = re.findall(' \'state\': \'(\w+)\', \'flap_count', cn_bgp_entry)
        for ip in est:
            if not ('Established' in ip):
                result = False
                self.logger.debug("Check the BGP connection on %s", host)
        return result

    def check_tcp_status(self):
        result = True
        #testcases which check tcp status quickly change keys and check for tcp status. 
        #internally, tcp session is restarted when md5 keys are changed,
        #as tcp session may take some time to come up, adding some sleep.
        sleep(10)
        for node in self.inputs.bgp_control_ips:
            cmd = 'netstat -tnp | grep :179 | awk \'{print $6}\''
            tcp_status = self.inputs.run_cmd_on_server(node, cmd)
            tcp_status=tcp_status.split('\n')
            for status in tcp_status:
                if not ('ESTABLISHED' in status):
                    result = False
                    self.logger.debug("Check the TCP connection on %s", node)
        return result

    def config_per_peer(self, auth_data):
        uuid = self.vnc_lib.bgp_routers_list()
        uuid = str(uuid)
        list_uuid = re.findall('u\'uuid\': u\'([a-zA-Z0-9-]+)\'', uuid)
        for node in list_uuid:
           if (self.vnc_lib.bgp_router_read(id=node).get_bgp_router_parameters().get_vendor()) == 'contrail':
               list_uuid1 = self.vnc_lib.bgp_router_read(id=node)
               iterrrefs = list_uuid1.get_bgp_router_refs()
               for str1 in iterrrefs:
                   sess = str1['attr'].get_session()
                   firstsess = sess[0]
                   firstattr = firstsess.get_attributes()
                   firstattr[0].set_auth_data(auth_data)
                   list_uuid1._pending_field_updates.add('bgp_router_refs')
                   self.vnc_lib.bgp_router_update(list_uuid1) 

    @classmethod
    def remove_mx_group_config(cls):
        if cls.inputs.ext_routers:
            router_params = cls.inputs.physical_routers_data.values()[0]
            cmd = []
            cmd.append('delete groups md5_tests')
            cmd.append('delete apply-groups md5_tests')
            mx_handle = NetconfConnection(host = router_params['mgmt_ip'])
            mx_handle.connect()
            cli_output = mx_handle.config(stmts = cmd, timeout = 120)

    def remove_configured_md5(self):
        auth_data=None
        for host in self.list_uuid:
            self.config_per_peer(auth_data=auth_data)
            self.config_md5( host=host, auth_data=auth_data )

    def create_md5_config(self):
        auth_data=None
        for host in self.list_uuid:
            self.config_per_peer(auth_data=auth_data)
            self.config_md5( host=host, auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should be up before md5"
        for host in self.list_uuid:
            auth_data={'key_items': [ { 'key':"juniper","key_id":0 } ], "key_type":"md5"}
            self.config_md5( host=host, auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes after basic md5 config not up"
        return True

    def add_delete_md5_config(self):
        auth_data=None
        for host in self.list_uuid:
            self.config_per_peer(auth_data=auth_data)
            self.config_md5( host=host, auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should be up before md5"
        host=self.list_uuid[1]
        auth_data={'key_items': [ { 'key':"juniper","key_id":0 } ], "key_type":"md5"}
        self.config_md5(host=host, auth_data=auth_data)
        sleep(95)
        assert not (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should not be up as only one side has md5"

        for host in self.list_uuid:
            auth_data={'key_items': [ { 'key':"juniper","key_id":0 } ], "key_type":"md5"}
            self.config_md5( host=host, auth_data=auth_data )

        sleep(95)
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after both sides have md5"
        host=self.list_uuid[1]
        auth_data=None
        self.config_md5(host=host, auth_data=auth_data)
        sleep(95)
        assert not (self.check_bgp_status(self.is_mx_present)), "BGP between nodes 2 should not be up as others have md5"

        for host in self.list_uuid:
            auth_data={'key_items': [ { 'key':"juniper","key_id":0 } ], "key_type":"md5"}
            self.config_md5( host=host, auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after 2 both sides have md5"

        for host in self.list_uuid:
            auth_data=None
            self.config_md5( host=host, auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should be up"
        return True

    def different_keys_md5_config(self):
        auth_data=None
        for host in self.list_uuid:
            self.config_per_peer(auth_data=auth_data)
            self.config_md5( host=host, auth_data=auth_data )
        sleep(95) 
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should be up before md5"
        for host in self.list_uuid:
            auth_data={'key_items': [ { 'key':"juniper","key_id":0 } ], "key_type":"md5"}
            self.config_md5( host=host, auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after md5 config"
        i=1
        for host in self.list_uuid:
            key = "juniper" + i.__str__()
            auth_data={'key_items': [ { 'key':key,"key_id":0 } ], "key_type":"md5"}
            self.config_md5( host=host, auth_data=auth_data )
            i += 1
        sleep(95)
        assert not (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should not be up as keys are different"       
            
        for host in self.list_uuid:
            auth_data={'key_items': [ { 'key':"juniper","key_id":0 } ], "key_type":"md5"}
            self.config_md5( host=host, auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after md5 config on all sides"

        for host in self.list_uuid:
            auth_data=None
            self.config_md5( host=host, auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should be up"
        return True
    
    def check_per_peer_md5_config(self):
        auth_data=None
        for host in self.list_uuid:
            self.config_per_peer(auth_data=auth_data)
            self.config_md5( host=host, auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should be up before md5"

        auth_data={'key_items': [ { 'key':"juniper","key_id":0 } ], "key_type":"md5"}
        host=self.list_uuid[1]
        self.config_per_peer(auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after per peer config"
        return True

    def add_delete_per_peer_md5_config(self):
        auth_data=None
        for host in self.list_uuid:
            self.config_per_peer(auth_data=auth_data)
            self.config_md5( host=host, auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should be up before md5"

        auth_data={'key_items': [ { 'key':"juniper","key_id":0 } ], "key_type":"md5"}
        host=self.list_uuid[1]
        self.config_per_peer(auth_data=auth_data)
        sleep(95)
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after per peer with mx"
        auth_data={'key_items': [ { 'key':"juniper","key_id":0 } ], "key_type":"md5"}
        host=self.list_uuid[1]
        self.config_per_peer(auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after different per peer value" 

        auth_data=None
        host=self.list_uuid[1]
        self.config_per_peer(auth_data=auth_data)
        sleep(95)
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should be up"

        auth_data={'key_items': [ { 'key':"juniper","key_id":0 } ], "key_type":"md5"}
        host=self.list_uuid[1]
        self.config_per_peer(auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after reconfig per peer with mx"
        auth_data=None
        host=self.list_uuid[1]
        self.config_per_peer(auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after removing md5 with control"
        auth_data={'key_items': [ { 'key':"juniper","key_id":0 } ], "key_type":"md5"}
        host=self.list_uuid[1]
        self.config_per_peer(auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after reconfiguring md5 with control"
        return True

    def diff_keys_per_peer_md5_config(self):
        auth_data=None
        for host in self.list_uuid:
            self.config_per_peer(auth_data=auth_data)
            self.config_md5( host=host, auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should be up before md5"

        auth_data={'key_items': [ { 'key':"juniper","key_id":0 } ], "key_type":"md5"}
        host=self.list_uuid[1]
        self.config_per_peer(auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after per peer with mx"

        auth_data={'key_items': [ { 'key':"juniper","key_id":0 } ], "key_type":"md5"}
        host=self.list_uuid[1]
        self.config_per_peer( auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should be up"
        auth_data={'key_items': [ { 'key':"juniper","key_id":0 } ], "key_type":"md5"}
        host=self.list_uuid[1]
        self.config_per_peer(auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after reconfiguring key with mx"
        return True

    def precedence_per_peer_md5_config(self):
        auth_data=None
        host=self.list_uuid[1]
        self.config_per_peer(auth_data=auth_data)
        for host in self.list_uuid:
            self.config_md5( host=host, auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should be up before md5"
        auth_data={'key_items': [ { 'key':"simple","key_id":0 } ], "key_type":"md5"}
        host=self.list_uuid[1]
        self.config_per_peer( auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after per peer with mx"

        auth_data=None
        host=self.list_uuid[1]
        self.config_per_peer(auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after removing md5 with control"

        i=1
        for host in self.list_uuid:
            key = "juniper" + i.__str__()
            auth_data={'key_items': [ { 'key':key,"key_id":0 } ], "key_type":"md5"}
            self.config_md5( host=host, auth_data=auth_data )
            i += 1
        sleep(95)
        assert not (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should not be up after global md5 key mismatch"
        auth_data={'key_items': [ { 'key':"juniper","key_id":0 } ], "key_type":"md5"}
        host=self.list_uuid[1]
        self.config_per_peer( auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after global mismatch, but per peer match"


        auth_data=None
        host=self.list_uuid[1]
        self.config_per_peer( auth_data=auth_data )

        sleep(95)
        assert not (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should not be up as global mismatch still exists"
        for host in self.list_uuid:
            auth_data={'key_items': [ { 'key':"trialbyerror","key_id":0 } ], "key_type":"md5"}
            self.config_md5( host=host, auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after reconfiguring global match"

        for host in self.list_uuid:
            auth_data=None
            self.config_md5( host=host, auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after having no md5 between control"

        return True

    def iter_keys_per_peer_md5_config(self):
        auth_data=None
        for host in self.list_uuid:
            self.config_per_peer(auth_data=auth_data)
            self.config_md5( host=host, auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should be up before md5"
        auth_data={'key_items': [ { 'key':"iter","key_id":0 } ], "key_type":"md5"}
        host=self.list_uuid[1]
        self.config_per_peer(auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after per peer with mx"

        for i in range(1, 11):
            for host in self.list_uuid:
                key = "juniper" + i.__str__()
                auth_data={'key_items': [ { 'key':key,"key_id":0 } ], "key_type":"md5"}
                self.config_md5( host=host, auth_data=auth_data )
            sleep(95)
            assert (self.check_tcp_status()), "TCP connection should be up after key change"
            assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should be up 1 as keys are the same everywhere"
            with settings(
                host_string='%s@%s' % (
                    self.inputs.username, self.inputs.cfgm_ips[0]),
                    password=self.inputs.password, warn_only=True, abort_on_prompts=False, debug=True):
                conrt = run('service contrail-control restart')
            cluster_status, error_nodes = ContrailStatusChecker().wait_till_contrail_cluster_stable()
            assert cluster_status, 'Hash of error nodes and services : %s' % (error_nodes)
            assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should be up 2 as keys are the same everywhere"

        for i in range(1, 11):
            for host in self.list_uuid:
                key = "juniper" + i.__str__()
                auth_data={'key_items': [ { 'key':key,"key_id":0 } ], "key_type":"md5"}
                self.config_md5( host=host, auth_data=auth_data )
        sleep(95)
        assert (self.check_tcp_status()), "TCP connection should be up after key change"
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should be up 3 as keys are the same everywhere"
        with settings(
            host_string='%s@%s' % (
                self.inputs.username, self.inputs.cfgm_ips[0]),
                password=self.inputs.password, warn_only=True, abort_on_prompts=False, debug=True):
            conrt = run('service contrail-control restart')
        cluster_status, error_nodes = ContrailStatusChecker().wait_till_contrail_cluster_stable()
        assert cluster_status, 'Hash of error nodes and services : %s' % (error_nodes)
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should be up 4 as keys are the same everywhere"

        for i in range(1, 11):
            key = "juniper" + i.__str__()
            auth_data={'key_items': [ { 'key':key,"key_id":0 } ], "key_type":"md5"}
            host=self.list_uuid[1]
            self.config_per_peer( auth_data=auth_data )
            sleep(95)
            assert (self.check_tcp_status()), "TCP connection should be up after key change"
            assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after per peer match"

        for i in range(1, 11):
            key = "juniper" + i.__str__()
            auth_data={'key_items': [ { 'key':key,"key_id":0 } ], "key_type":"md5"}
            host=self.list_uuid[1]
            notmx=1
            self.config_per_peer(auth_data=auth_data )
        sleep(95)
        assert (self.check_tcp_status()), "TCP connection should be up after key change"
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after per peer match"

        return True

# end class Md5Base
