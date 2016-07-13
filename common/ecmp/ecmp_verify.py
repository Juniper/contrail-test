import os
import fixtures
import testtools
import unittest
import time
from common.connections import ContrailConnections
from common.contrail_test_init import ContrailTestInit
from vn_test import *
from floating_ip import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from vm_test import *
from tcutils.wrappers import preposttest_wrapper


class ECMPVerify():

    def get_rt_info_tap_intf_list(self, src_vn, src_vm, dst_vm, svm_ids):
        shared_ip= self.find_rt_in_ctrl_node(src_vn, src_vm, dst_vm, svm_ids)
        self.find_rt_in_agent(src_vn, src_vm, dst_vm)
        return self.get_tap_intf_list(src_vn, src_vm, dst_vm, shared_ip)
    #end get_rt_info_tap_intf_list

    def find_rt_in_ctrl_node(self, src_vn, src_vm, dst_vm, svm_ids):
        right_ip = {}
        left_ip = {}
        count= 0
        self.logger.info('%%%Get the Route Entry in the control node%%%')
        active_controller = None
        inspect_h1 = self.agent_inspect[src_vm.vm_node_ip]
        agent_xmpp_status = inspect_h1.get_vna_xmpp_connection_status()
        for entry in agent_xmpp_status:
            if entry['cfg_controller'] == 'Yes':
                count += 1
                active_controller = entry['controller_ip']
                new_controller = self.inputs.host_data[
                    active_controller]['host_ip']
                self.logger.info('Active control node is %s' % new_controller)
        assert count > 0, 'Some Problem with the setup. Pls chk XMPP connection'
        svm_route_entry = {}
        for svm_id in svm_ids:
            svc_obj = self.nova_h.get_vm_by_id(svm_id)
            left_ip[svm_id] = svc_obj.addresses[self.si_fixtures[0]
                                                .left_vn_name.split(':')[2]][0]['addr']
            right_ip[svm_id] = svc_obj.addresses[self.si_fixtures[0]
                                                 .right_vn_name.split(':')[2]][0]['addr']
            self.logger.info('%s has %s as left_ip and %s as right_ip' %
                             (svc_obj.name, left_ip[svm_id], right_ip[svm_id]))
            shared_ip= left_ip[svm_id]
        net = '/32'
        if self.inputs.get_af() == 'v6':
            net = '/128'
        dst_vm_ip = self.cn_inspect[new_controller].get_cn_route_table_entry(
                ri_name=src_vn.ri_name, prefix=dst_vm.vm_ip + net)
        result = True
        if dst_vm_ip:
            self.logger.info(
                'Route to %s found in the Active Control-Node %s' %
                (dst_vm.vm_ip, new_controller))
        else:
            result = False
            assert result, 'Route to %s not found in the Active Control-Node %s' %(dst_vm.vm_ip, new_controller)

        return shared_ip
    #end find_rt_in_ctrl_node

    def find_rt_in_agent(self, src_vn, src_vm, dst_vm):
        self.logger.info('%%%Get the Route Entry in the agent%%%')
        vn_vrf_id= self.get_vrf_id(src_vn, src_vm)
        inspect_h1 = self.agent_inspect[src_vm.vm_node_ip]
        net = '32'
        if self.inputs.get_af() == 'v6':
            net = '128'
        paths = inspect_h1.get_vna_active_route(
            vrf_id=vn_vrf_id, ip=dst_vm.vm_ip, prefix=net)['path_list']
        self.logger.info('There are %s nexthops to %s on Agent %s' %
                         (len(paths), dst_vm.vm_ip, src_vm.vm_node_ip))
        next_hops = paths[0]['nh']
        if not paths:
            result = False
            assert result, 'Route to %s not found in the Agent %s' %(dst_vm.vm_ip, src_vm.vm_node_ip)
        return True
    #end find_rt_in_agent

    def get_tap_intf_list(self, src_vn, src_vm, dst_vm, shared_ip):
        self.logger.info('%%%Get the Tap Interface List%%%')
        vn_vrf_id= self.get_vrf_id(src_vn, src_vm)
        inspect_h1 = self.agent_inspect[src_vm.vm_node_ip]
        net = '32'
        if self.inputs.get_af() == 'v6':
            net = '128'
        paths = inspect_h1.get_vna_active_route(
            vrf_id=vn_vrf_id, ip=shared_ip, prefix=net)['path_list']
        next_hops = paths[0]['nh']       
        (domain, project, vn) = src_vn.vn_fq_name.split(':')
        tap_intf_list= []
        if 'mc_list' in next_hops:
            self.logger.info('Composite Next Hops seen')
            inspect_h1 = self.agent_inspect[src_vm.vm_node_ip]
            vn_vrf_id= self.get_vrf_id(src_vn, src_vm)
            multi_next_hops = inspect_h1.get_vna_active_route(
                vrf_id=vn_vrf_id, ip=shared_ip, prefix=net)['path_list'][0]['nh']['mc_list']

            for nh in multi_next_hops:
                if nh['type'] == 'Tunnel':
                    destn_agent = nh['dip']
                    new_destn_agent = self.inputs.host_data[
                        destn_agent]['host_ip']
                    inspect_hh = self.agent_inspect[new_destn_agent]
                    vn_vrf_id= self.get_vrf_id(src_vn, src_vm, new_destn_agent)
                    next_hops_in_tnl = inspect_hh.get_vna_active_route(
                        vrf_id=vn_vrf_id, ip=shared_ip, prefix=net)['path_list'][0]['nh']['mc_list']
                    for next_hop in next_hops_in_tnl:
                        if next_hop['type'] == 'Interface':
                            tap_intf_from_tnl = next_hop['itf']
                            agent_tap_intf_tuple= (new_destn_agent, tap_intf_from_tnl)
                            tap_intf_list.append(agent_tap_intf_tuple)
                elif nh['type'] == 'Interface':
                    tap_intf = nh['itf']
                    agent_tap_intf_tuple= (src_vm.vm_node_ip, tap_intf)
                    tap_intf_list.append(agent_tap_intf_tuple)
        else:
            self.logger.debug('No mc_list seen')
            if 'unnel' in next_hops['type']:
                destn_agent = next_hops['dip']
                new_destn_agent = self.inputs.host_data[
                    destn_agent]['host_ip']
                inspect_hh = self.agent_inspect[new_destn_agent]
                vn_vrf_id= self.get_vrf_id(src_vn, src_vm, new_destn_agent)
                next_hops_in_tnl = inspect_hh.get_vna_active_route(
                    vrf_id=vn_vrf_id, ip=shared_ip, prefix=net)['path_list'][0]['nh']
                if 'mc_list' in next_hops_in_tnl:
                    next_hops_in_tnl= next_hops_in_tnl['mc_list']
                    for next_hop in next_hops_in_tnl:
                        if next_hop['type'] == 'Interface':
                            tap_intf_from_tnl = next_hop['itf']
                            agent_tap_intf_tuple= (new_destn_agent, tap_intf_from_tnl)
                            tap_intf_list.append(agent_tap_intf_tuple)
                elif 'face' in next_hops_in_tnl['type']:
                    tap_intf_from_tnl = next_hops_in_tnl['itf']
                    agent_tap_intf_tuple= (new_destn_agent, tap_intf_from_tnl)
                    tap_intf_list.append(agent_tap_intf_tuple)
            elif 'face' in next_hops['type']:
                tap_intf = next_hops['itf']
                agent_tap_intf_tuple= (src_vm.vm_node_ip, tap_intf)
                tap_intf_list.append(agent_tap_intf_tuple)
        self.logger.info(
                'The Tap interface list :%s' %
            tap_intf_list)
        return tap_intf_list
    # end get_tap_intf_list
 
    def get_vrf_id(self, src_vn, src_vm, destn_agent= None):
        if destn_agent is None:
            destn_agent= src_vm.vm_node_ip
            destn_agent= self.inputs.host_data[destn_agent]['host_ip']
        (domain, project, vn) = src_vn.vn_fq_name.split(':')
        inspect_h1 = self.agent_inspect[destn_agent]
        agent_vrf_objs = inspect_h1.get_vna_vrf_objs(domain, project, vn)
        agent_vrf_obj = src_vm.get_matching_vrf(
            agent_vrf_objs['vrf_list'], src_vn.vrf_name)
        vn_vrf_id = agent_vrf_obj['ucindex']
        return vn_vrf_id
    #end get_vrf_id
 
    def get_svms_in_si(self, si, proj_name):
        svm_ids= si.svm_ids                                                                                                                                                                
        svm_list= []
        for svm_id in svm_ids:
            svm_list.append(self.nova_h.get_vm_by_id(svm_id))
        return svm_list
    #end get_svms_in_si
