import fixtures
from ipam_test import *
from vn_test import *
from tcutils.util import *
import time
import traceback
from fabric.api import env
from fabric.api import run
from fabric.state import output
from fabric.operations import get, put
from fabric.context_managers import settings, hide
import socket
from contrail_fixtures import *
env.disable_known_hosts = True
import json
import copy
from netaddr import IPNetwork


class CNFixture(fixtures.Fixture):

    '''
    Fixture to handle creation, verification and deletion of control node BGP peering.
    '''

    def __init__(self, connections, inputs, router_name, router_ip, router_type='contrail', router_asn='64512'):
        self.connections = connections
        self.inputs = inputs
        self.quantum_h = self.connections.quantum_h
        self.vnc_lib_h = self.connections.vnc_lib
        self.api_s_inspect = self.connections.api_server_inspect
        self.agent_inspect = self.connections.agent_inspect
        self.cn_inspect = self.connections.cn_inspect
        self.logger = inputs.logger
        self.already_present = False
        self.verify_is_run = False
        self.router_asn = router_asn
        self.router_name = router_name
        self.router_ip = router_ip
        self.router_type = router_type
    # end __init__

    def setUp(self):
        super(CNFixture, self).setUp()
        if not self.is_cn_present(self.router_ip):
            self.create_cn_node(self.router_ip, self.router_type)
            self.logger.info('Creating Peering in control node with ip %s' %
                             (self.router_ip))
        else:
            self.logger.info(
                'Control nodel %s already present, not creating it' %
                (self.router_ip))
            self.already_present = True

    # end setUp

    def create_cn_node(self, router_ip, router_type):
        '''
        Procedure to create control node
        '''
        bgp_addr_fams = AddressFamilies(['inet-vpn'])
        bgp_sess_attrs = [
            BgpSessionAttributes(address_families=bgp_addr_fams)]
        bgp_sessions = [BgpSession(attributes=bgp_sess_attrs)]
        bgp_peering_attrs = BgpPeeringAttributes(session=bgp_sessions)
        #rt_inst_obj = self._get_rt_inst_obj()
        vnc_lib = self.vnc_lib_h
        router_type = self.router_type
        rt_inst_obj = vnc_lib.routing_instance_read(
            fq_name=['default-domain', 'default-project',
                     'ip-fabric', '__default__'])

        router_params = BgpRouterParams(
            vendor=router_type, autonomous_system=int(self.router_asn),
            identifier=str(
                IPNetwork(router_ip).ip),
            address=str(
                IPNetwork(router_ip).ip),
            port=179, address_families=bgp_addr_fams)

        bgp_router_obj = BgpRouter(self.router_name, rt_inst_obj,
                                   bgp_router_parameters=router_params)

        cur_id = vnc_lib.bgp_router_create(bgp_router_obj)
        cur_obj = vnc_lib.bgp_router_read(id=cur_id)
        # full-mesh with existing bgp routers
        fq_name = rt_inst_obj.get_fq_name()
        bgp_router_list = vnc_lib.bgp_routers_list(parent_fq_name=fq_name)
        bgp_router_ids = [bgp_dict['uuid']
                          for bgp_dict in bgp_router_list['bgp-routers']]
        bgp_router_objs = []
        for id in bgp_router_ids:
            bgp_router_objs.append(vnc_lib.bgp_router_read(id=id))

            for other_obj in bgp_router_objs:
                if other_obj.uuid == cur_id:
                    continue

                cur_obj.add_bgp_router(other_obj, bgp_peering_attrs)

            vnc_lib.bgp_router_update(cur_obj)
    # end create_cn_node

    def del_cn_node(self, router_ip):
        '''
        Delete control node
        '''
        vnc_lib = self.vnc_lib_h
        #rt_inst_obj = self._get_rt_inst_obj()
        rt_inst_obj = vnc_lib.routing_instance_read(
            fq_name=['default-domain', 'default-project',
                     'ip-fabric', '__default__'])

        fq_name = rt_inst_obj.get_fq_name() + [self.router_name]
        cur_obj = vnc_lib.bgp_router_read(fq_name=fq_name)

        # remove full-mesh with existing bgp routers
        fq_name = rt_inst_obj.get_fq_name()
        bgp_router_list = vnc_lib.bgp_routers_list(parent_fq_name=fq_name)
        bgp_router_ids = [bgp_dict['uuid']
                          for bgp_dict in bgp_router_list['bgp-routers']]
        bgp_router_objs = []
        for id in bgp_router_ids:
            bgp_router_objs.append(vnc_lib.bgp_router_read(id=id))

        for other_obj in bgp_router_objs:
            if other_obj.uuid == cur_obj.uuid:
                # our refs will be dropped on delete further down
                continue

            other_obj.del_bgp_router(cur_obj)

        vnc_lib.bgp_router_delete(id=cur_obj.uuid)
     # end del_cn_node

    def verify_on_setup(self):
        result = True
        if not self.verify_peer_in_control_nodes():
            result = result and False
            self.logger.error(
                "Either Control node %s does not have any BGP peer or is not in Established state" % (self.router_ip))
        self.verify_is_run = True
        # TODO Verify in APi Server
        # TODO Verify in Agent
        return result
    # end verify

    def is_cn_present(self, router_ip):
        """
        Check if control node is already present
        """
        result = False
        present_router_list = []
        rt_inst_obj = self.vnc_lib_h.routing_instance_read(
            fq_name=['default-domain', 'default-project',
                     'ip-fabric', '__default__'])
        fq_name = rt_inst_obj.get_fq_name()
        bgp_router_list = self.vnc_lib_h.bgp_routers_list(
            parent_fq_name=fq_name)
        bgp_router_ids = [bgp_dict['uuid']
                          for bgp_dict in bgp_router_list['bgp-routers']]
        for id in bgp_router_ids:
            present_router_list.append(
                self.vnc_lib_h.bgp_router_read(id=id).bgp_router_parameters.address)
            if router_ip in present_router_list:
                result = True

        return result
    # end is_cn_present

    @retry(delay=5, tries=6)
    def verify_peer_in_control_nodes(self):
        """
        Check the configured control node has any peer and if so the state is Established.
        """
        result = True
        for entry1 in self.inputs.bgp_ips:
            cn_bgp_entry = self.cn_inspect[
                entry1].get_cn_bgp_neigh_entry(encoding='BGP')
            if not cn_bgp_entry:
                result = False
                self.logger.error(
                    'Control Node %s does not have any BGP Peer' %
                    (self.router_ip))
            else:
                for entry in cn_bgp_entry:
                    if entry['state'] != 'Established':
                        result = result and False
                        self.logger.error('With Peer %s peering is not Established. Current State %s ' % (
                            entry['peer'], entry['state']))
                    else:
                        self.logger.info(
                            'With Peer %s peering is Current State is %s ' %
                            (entry['peer'], entry['state']))
        return result
    # end verify_vn_in_control_node

    def restart_control_node(self, host_ips=[]):
        '''
        Restart the control node service
        '''
        result = True
        service_name = 'contrail-control'
        if len(host_ips) == 0:
            host_ips = [self.router_ip]
        for host in host_ips:
            username = self.inputs.host_data[host]['username']
            password = self.inputs.host_data[host]['password']
            self.logger.info('Restarting %s.service in %s' %
                             (service_name, self.inputs.host_data[host]['name']))
            issue_cmd = 'service %s restart' % (service_name)
            self.inputs.run_cmd_on_server(host, issue_cmd, username, password)
    # end restart_service

    def stop_control_node(self, host_ips=[]):
        '''
        Stop the control node service
        '''
        result = True
        service_name = 'contrail-control'
        if len(host_ips) == 0:
            host_ips = [self.router_ip]
        for host in host_ips:
            username = self.inputs.host_data[host]['username']
            password = self.inputs.host_data[host]['password']
            self.logger.info('Stoping %s.service in %s' %
                             (service_name, self.inputs.host_data[host]['name']))
            issue_cmd = 'service %s stop' % (service_name)
            self.inputs.run_cmd_on_server(host, issue_cmd, username, password)
    # end stop_service

    def start_control_node(self, host_ips=[]):
        '''
        Start the control node service
        '''
        result = True
        service_name = 'contrail-control'
        if len(host_ips) == 0:
            host_ips = [self.router_ip]
        for host in host_ips:
            username = self.inputs.host_data[host]['username']
            password = self.inputs.host_data[host]['password']
            self.logger.info('Starting %s.service in %s' %
                             (service_name, self.inputs.host_data[host]['name']))
            issue_cmd = 'service %s start' % (service_name)
            self.inputs.run_cmd_on_server(host, issue_cmd, username, password)
    # end start_service

    def cleanUp(self):
        super(CNFixture, self).cleanUp()
        do_cleanup = True
        if self.inputs.fixture_cleanup == 'no':
            do_cleanup = False
        if self.already_present:
            do_cleanup = False
        if self.inputs.fixture_cleanup == 'force':
            do_cleanup = True
        if do_cleanup:
            self.del_cn_node(self.router_ip)
            self.logger.info("Deleting the Control Node %s " %
                             (self.router_ip))
            # TODO Add verification after cleanup here
        else:
            self.logger.info('Skipping the deletion of the Control Node %s ' %
                             (self.router_ip))
    # end cleanUp
