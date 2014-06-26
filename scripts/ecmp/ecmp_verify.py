import os
import fixtures
import testtools
import unittest
import traffic_tests
import time
from connections import ContrailConnections
from contrail_test_init import ContrailTestInit
from vn_test import *
from floating_ip import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from vm_test import *
from tcutils.wrappers import preposttest_wrapper


class ECMPVerify():

    def get_rt_info_tap_intf_list(self, vn_fixture, vm_fixture, svm_ids):
        right_ip = {}
        left_ip = {}
        self.logger.info('Get the Route Entry in the control node')
        active_controller = None
        inspect_h1 = self.agent_inspect[vm_fixture.vm_node_ip]
        agent_xmpp_status = inspect_h1.get_vna_xmpp_connection_status()
        for entry in agent_xmpp_status:
            if entry['cfg_controller'] == 'Yes':
                active_controller = entry['controller_ip']
                new_controller = self.inputs.host_data[
                    active_controller]['host_ip']
                self.logger.info('Active control node is %s' % new_controller)
        svm_route_entry = {}
        for svm_id in svm_ids:
            svc_obj = self.nova_fixture.get_vm_by_id(
                svm_id, self.inputs.project_name)
            left_ip[svm_id] = svc_obj.addresses[self.si_fixtures[0]
                                                .left_vn_name.split(':')[2]][0]['addr']
            right_ip[svm_id] = svc_obj.addresses[self.si_fixtures[0]
                                                 .right_vn_name.split(':')[2]][0]['addr']
            self.logger.info('%s has %s as left_ip and %s as right_ip' %
                             (svc_obj.name, left_ip[svm_id], right_ip[svm_id]))
            svm_route_entry[svm_id] = self.cn_inspect[new_controller].get_cn_route_table_entry(
                ri_name=vn_fixture.ri_name, prefix=left_ip[svm_id] + '/32')
            result = True
            if svm_route_entry[svm_id]:
                self.logger.info(
                    'Route Entry found in the Active Control-Node %s' %
                    (new_controller))
            else:
                result = False
                assert result, 'Route Entry not found in the Active Control-Node %s' % (
                    new_controller)

            # Get the tap interface list
            (domain, project, vn) = vn_fixture.vn_fq_name.split(':')
            tap_intf_list = []
            inspect_h9 = self.agent_inspect[vm_fixture.vm_node_ip]
            agent_vrf_objs = inspect_h9.get_vna_vrf_objs(domain, project, vn)
            agent_vrf_obj = vm_fixture.get_matching_vrf(
                agent_vrf_objs['vrf_list'], vn_fixture.vrf_name)
            vn_vrf_id9 = agent_vrf_obj['ucindex']
            paths = inspect_h9.get_vna_active_route(
                vrf_id=vn_vrf_id9, ip=left_ip[svm_id], prefix='32')['path_list']
            self.logger.info('There are %s nexthops to %s on Agent %s' %
                             (len(paths), left_ip[svm_id], vm_fixture.vm_node_ip))
            next_hops = inspect_h9.get_vna_active_route(
                vrf_id=vn_vrf_id9, ip=left_ip[svm_id], prefix='32')['path_list'][0]['nh']

            if not next_hops:
                result = False
                assert result, 'Route not found in the Agent %s' % vm_fixture.vm_node_ip
            else:
                self.logger.info('Route found in the Agent %s' %
                                 vm_fixture.vm_node_ip)

            if 'mc_list' in next_hops:
                self.logger.info('Composite Next Hops seen')
                multi_next_hops = inspect_h9.get_vna_active_route(
                    vrf_id=vn_vrf_id9, ip=left_ip[svm_id], prefix='32')['path_list'][0]['nh']['mc_list']

                for nh in multi_next_hops:
                    label = nh['label']
                    if nh['type'] == 'Tunnel':
                        destn_agent = nh['dip']
                        new_destn_agent = self.inputs.host_data[
                            destn_agent]['host_ip']
                        inspect_hh = self.agent_inspect[new_destn_agent]
                        agent_vrf_objs = inspect_hh.get_vna_vrf_objs(
                            domain, project, vn)
                        agent_vrf_obj = vm_fixture.get_matching_vrf(
                            agent_vrf_objs['vrf_list'], vn_fixture.vrf_name)
                        fvn_vrf_id5 = agent_vrf_obj['ucindex']
                        next_hops_in_tnl = inspect_hh.get_vna_active_route(
                            vrf_id=fvn_vrf_id5, ip=left_ip[svm_id], prefix='32')['path_list'][0]['nh']['mc_list']
                        for next_hop in next_hops_in_tnl:
                            if next_hop['type'] == 'Interface':
                                tap_intf_from_tnl = next_hop['itf']
                                tap_intf_list.append(tap_intf_from_tnl)
                    elif nh['type'] == 'Interface':
                        tap_intf = nh['itf']
                        tap_intf_list.append(tap_intf)
            else:
                self.logger.info('No mc_list seen')
                if 'unnel' in next_hops['type']:
                    destn_agent = next_hops['dip']
                    new_destn_agent = self.inputs.host_data[
                        destn_agent]['host_ip']
                    inspect_hh = self.agent_inspect[new_destn_agent]
                    agent_vrf_objs = inspect_hh.get_vna_vrf_objs(
                        domain, project, vn)
                    agent_vrf_obj = vm_fixture.get_matching_vrf(
                        agent_vrf_objs['vrf_list'], vn_fixture.vrf_name)
                    fvn_vrf_id5 = agent_vrf_obj['ucindex']
                    next_hops_in_tnl = inspect_hh.get_vna_active_route(
                        vrf_id=fvn_vrf_id5, ip=left_ip[svm_id], prefix='32')['path_list'][0]['nh']
                    if 'face' in next_hops_in_tnl['type']:
                        tap_intf_from_tnl = next_hops_in_tnl['itf']
                        tap_intf_list.append(tap_intf_from_tnl)
                elif 'face' in next_hops['type']:
                    tap_intf = next_hops['itf']
                    tap_intf_list.append(tap_intf)
            self.logger.info(
                'The list of Tap interfaces from the agents are %s' %
                tap_intf_list)

        return True
    # end get_rt_info_tap_intf_list
