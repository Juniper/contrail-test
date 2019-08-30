import uuid
import re
import sys
from base import ASN4Base
from tcutils.control.cn_introspect_utils import *
from tcutils.wrappers import preposttest_wrapper
from physical_router_fixture import PhysicalRouterFixture
from physical_device_fixture import PhysicalDeviceFixture
from vn_test import VNFixture
from vm_test import VMFixture
import control_node
from common.bgpaas.base import BaseBGPaaS
from serial_scripts.bgpaas.base import LocalASBase
from tcutils.util import skip_because

cluster_use_local_asn = False

class TestAsn4(ASN4Base,BaseBGPaaS,LocalASBase):

    def setUp(self):
        super(TestAsn4, self).setUp()

    def get_neighbor_info(self):
        bgp_neigh_info = {}
        for control_ip in self.inputs.bgp_ips:
            cn_bgp_entry = self.cn_inspect[control_ip].get_cn_bgp_neigh_entry()
            for entry in range(len(cn_bgp_entry)):
                peer = cn_bgp_entry[entry]
                peer_info = {'peer_ip': peer['peer_address'], 'flap_count': peer['flap_count']}
                bgp_neigh_info[peer['peer']] = peer_info
        return bgp_neigh_info

    def get_4byte_enable(self):
        gsc_obj = self.connections.vnc_lib.global_system_config_read(
                  fq_name=['default-global-system-config'])
        return gsc_obj.get_enable_4byte_as()

    def set_4byte_enable(self,state):
        gsc_obj = self.connections.vnc_lib.global_system_config_read(
                  fq_name=['default-global-system-config'])
        gsc_obj.set_enable_4byte_as(state)
        self.connections.vnc_lib.global_system_config_update(gsc_obj)
        
    def get_global_asn(self ):
        existing_asn = self.connections.vnc_lib_fixture.get_global_asn()
        return existing_asn

    def set_global_asn(self, asn):
        self.connections.vnc_lib_fixture.set_global_asn(asn)


    def set_bgp_router_asn(self,bgp_router_id,asn,local_asn):
        phy_router_obj = self.connections.vnc_lib.bgp_router_read(id=bgp_router_id)
        params = phy_router_obj.get_bgp_router_parameters()
        existing_asn = params.get_autonomous_system()
        params.set_autonomous_system(asn)
        params.set_local_autonomous_system(local_asn)
        phy_router_obj.set_bgp_router_parameters(params)
        self.connections.vnc_lib.bgp_router_update(phy_router_obj)


    def create_physical_device(self,router_params):

        phy_device_fixture=PhysicalDeviceFixture(
                            router_params['name'],router_params['control_ip'],
                            role=None,peer_ip=router_params['control_ip'],
                            tunnel_ip=router_params['control_ip'],
                            ssh_username=router_params['ssh_username'],
                            ssh_password=router_params['ssh_password'],
                            connections=self.connections)
       
        phy_device_fixture.setUp()
        return phy_device_fixture

    def get_bgp_router_flap_count(self,bgp_router_name):

        flap_info = {}

        for entry1 in self.inputs.bgp_ips:
            self.cn_ispec = ControlNodeInspect(entry1)
            cn_bgp_entry = self.cn_ispec.get_cn_bgp_neigh_entry(encoding='BGP')

            if not cn_bgp_entry:
                result = False
                self.logger.error(
                    'Control Node %s does not have any BGP Peer' %
                    (entry1))
            else:
                for entry in cn_bgp_entry:

                    if entry['peer'] == bgp_router_name:

                        flap_info[entry1] = entry['flap_count']
                        self.logger.info(
                                'Node %s peering info:With Peer %s : %s peering is Current State is %s ' %
                                (entry['local_address'],bgp_router_name, entry['peer'], entry['state']))

        return flap_info

    def create_bgp_router(self,router_params,phy_device_fixture):

        phy_router_fixture = PhysicalRouterFixture(
                            router_params['name'], router_params['control_ip'],
                            model="mx",
                            vendor=router_params['vendor'],
                            asn=router_params['asn'],
                            ssh_username=router_params['ssh_username'],
                            ssh_password=router_params['ssh_password'],
                            mgmt_ip=router_params['control_ip'],
                            do_cleanup=False,
                            connections=self.connections)
        phy_router_fixture.phy_device = phy_device_fixture
        phy_router_fixture.setUp()

        if phy_router_fixture.bgp_router_already_present :
           params = phy_router_fixture.bgp_router.get_bgp_router_parameters()
           existing_asn = params.get_autonomous_system()
           params.set_autonomous_system(router_params['asn'])
           params.set_router_type("router")
           phy_router_fixture.bgp_router.set_bgp_router_parameters(params)
           self.connections.vnc_lib.bgp_router_update(phy_router_fixture.bgp_router)
           self.addCleanup(self.set_bgp_router_asn,phy_router_fixture.bgp_router.uuid,existing_asn,None)

        return phy_router_fixture

    def update_bgpaas_configuration(self,control_node_config,vm_config,bgpaas_fixt):
        bgpaas_obj = self.connections.vnc_lib.bgp_as_a_service_read(id=bgpaas_fixt.uuid)
        four_byte_asn_enabled = self.get_4byte_enable()
        if vm_config['asn'] > 65535 and not four_byte_asn_enabled:  
           bgpaas_obj.set_autonomous_system(23456)
        else:
           bgpaas_obj.set_autonomous_system(vm_config['asn'])
        session_attr = bgpaas_obj.get_bgpaas_session_attributes()
        session_attr.local_autonomous_system=control_node_config['control_node_asn'][0]
        bgpaas_obj.set_bgpaas_session_attributes(session_attr)
        self.connections.vnc_lib.bgp_as_a_service_update(bgpaas_obj)

    def reconfigure_bgpaas_vms(self,control_node_config,vm_fixt_list,vm_config_list):

        test_vm = vm_fixt_list[0]
        cmdList = []
        for i,bgp_vm in enumerate(vm_config_list):
            if i == 0:
               continue
            bgpaas_vm = vm_fixt_list[i]

            autonomous_system  = bgp_vm['asn']
            vsrx_4b_capability = bgp_vm['4b_capability']
            local_autonomous_system = control_node_config['control_node_asn'][0]

            if not vsrx_4b_capability and local_autonomous_system > 65535 :
               cmdList.append('set protocols bgp group bgpaas peer-as 23456')
            else:
               if local_autonomous_system:
                  cmdList.append( 'set protocols bgp group bgpaas peer-as ' + str(local_autonomous_system))
               else:
                  cmdList.append( 'set protocols bgp group bgpaas peer-as ' + str(self.inputs.router_asn)) # self.inputs.router_asn is 64512
            self.configure_vsrx(srv_vm=test_vm,dst_vm=bgpaas_vm,cmds=cmdList)

    def configure_bgpaas_vms(self,control_node_config,vn_fixture,vm_fixt_list,vm_config_list=[]):

        cluster_4b_capability = control_node_config['cluster_4b_capability']

        test_vm = vm_fixt_list[0]
        bgpaas_fixture_list = []
        for i,bgp_vm in enumerate(vm_config_list):
            if i == 0:
               bgpaas_fixture_list.append(None)
               continue

            static_routes      = bgp_vm['static_routes']
            static_routes_aggr = bgp_vm['static_routes_aggr']
            aggr_route         = bgp_vm['aggr_route']
            autonomous_system  = bgp_vm['asn']
            vsrx_4b_capability = bgp_vm['4b_capability']
            local_autonomous_system = control_node_config['control_node_asn'][0]

            bgpaas_vm = vm_fixt_list[i]

            if not cluster_4b_capability and autonomous_system > 65535:
               autonomous_system_ui = 23456
            else:
               autonomous_system_ui = autonomous_system

            bgpaas_fixture = self.create_bgpaas(
                bgpaas_shared=True,
                autonomous_system=autonomous_system_ui,
                bgpaas_ip_address=bgpaas_vm.get_vm_ips()[0],
                local_autonomous_system=local_autonomous_system)

            bgpaas_fixture_list.append(bgpaas_fixture)
            self.attach_port_to_bgpaas_obj(bgpaas_vm, bgpaas_fixture)
            address_families = ['inet', 'inet6']
            gw_ip = vn_fixture.get_subnets()[0]['gateway_ip']
            dns_ip = vn_fixture.get_subnets()[0]['dns_server_address']
            neighbors = [gw_ip, dns_ip]
            self.logger.info('We will configure BGP on the vSRX')

            local_ip = bgp_ip = bgpaas_vm.vm_ip
            src_vm=test_vm
            dst_vm=bgpaas_vm
  
            cmdList = []
            cmdList.extend(
                ('set routing-options router-id ' +
                 str(local_ip),
                    'set routing-options autonomous-system ' +
                    str(autonomous_system),
                    'set protocols bgp group bgpaas local-address ' +
                    str(bgp_ip)))
            for family in address_families:
                cmdList.append(
                    'set protocols bgp group bgpaas family ' +
                    str(family) +
                    ' unicast')
            for neighbor in neighbors:
                cmdList.append(
                    'set protocols bgp group bgpaas neighbor ' + str(neighbor))

            if not vsrx_4b_capability and local_autonomous_system > 65535 :
               cmdList.append('set protocols bgp group bgpaas peer-as 23456')
            else:
               if local_autonomous_system:
                  cmdList.append( 'set protocols bgp group bgpaas peer-as ' + str(local_autonomous_system))
               else:
                  cmdList.append( 'set protocols bgp group bgpaas peer-as ' + str(self.inputs.router_asn)) # self.inputs.router_asn is 64512

            cmdList.extend(('set protocols bgp group bgpaas type external',
                            'set protocols bgp group bgpaas multihop', 
                            'set protocols bgp group bgpaas export export-to-bgp',
                            'set protocols bgp group bgpaas export export_aggr',
                            'set protocols bgp group bgpaas hold-time 30', 
                            'set protocols bgp group bgpaas traceoptions file bgp_log',
                            'set protocols bgp group bgpaas traceoptions file size 4294967295',
                            'set protocols bgp group bgpaas traceoptions file world-readable',
                            'set policy-options policy-statement export-to-bgp term allow_local from protocol static', 
                            'set policy-options policy-statement export-to-bgp term allow_local then next-hop ' + str(bgp_ip),
                            'set policy-options policy-statement export-to-bgp term allow_local then accept'))

            for static_route in static_routes:
                cmdList.append("set routing-options static route %s discard"%static_route)

            cmdList.append("set policy-options policy-statement export_aggr from protocol aggregate")
            cmdList.append("set policy-options policy-statement export_aggr then accept")
            cmdList.append("set routing-options aggregate route %s policy export_static_aggr"%aggr_route)
            cmdList.append("set policy-options policy-statement export_static_aggr from protocol static")

            for static_route in static_routes_aggr:
                cmdList.append("set routing-options static route %s discard"%static_route)
                cmdList.append("set policy-options policy-statement export_static_aggr from route-filter %s exact"%static_route)
            cmdList.append("set policy-options policy-statement export_static_aggr then accept")

            if not vsrx_4b_capability :
               cmdList.append("set protocols bgp group bgpaas disable-4byte-as")

            self.configure_vsrx(srv_vm=test_vm,dst_vm=bgpaas_vm,cmds=cmdList)

            bgpaas_vm.wait_for_ssh_on_vm()

            agent = bgpaas_vm.vm_node_ip
            
            ret = bgpaas_fixture.verify_in_control_node(
                bgpaas_vm), 'BGPaaS Session not seen in the control-node'
            if not ret:
               assert False,'BGPaaS Session not seen in the control-node'
        return bgpaas_fixture_list

    def configure_physical_devices(self,control_node_config,mx_config):

        self.logger.info("Configure MX")
        mx_control_ip_address = mx_config['mx_control_ip_address']
        cluster_4b_capability = control_node_config['cluster_4b_capability']
        mx_4b_capability = mx_config['mx_4b_capability']
        mx_asn = mx_config['mx_asn']
        mx_vrf_interfaces   = mx_config['mx_vrf_interfaces']
        cluster_group = None
        control_node_asn     = control_node_config['control_node_asn']

        for device in self.inputs.physical_routers_data.iteritems():
          router_name   = device[0]

          if router_name != mx_config['mx_name']:
             continue

          flap_count_init1 = self.get_bgp_router_flap_count(router_name)
          router_params = device[1]

          single_mx_bgp_router = True if len(mx_control_ip_address) == 1 else False

          for i,mx_ip in enumerate(mx_control_ip_address):

              router_params['asn'] = 23456 if ( not cluster_4b_capability and mx_asn[i] > 65535 ) else mx_asn[i] 
              router_params['vrf_interface'] = mx_vrf_interfaces[i] + ".0"
              router_params['rd']            = mx_control_ip_address[i].split("/")[0] + ":1"
              router_params['tunnel_ip']     = mx_control_ip_address[i].split("/")[0]
              router_params['control_ip']    = router_params['tunnel_ip']

              router_params["ri_name"]       = mx_config['ri_name']
          
              router_params['mx_4b_capability'] = mx_4b_capability
              router_params['name']             = mx_config['mx_name']
              phy_device_fixture = self.create_physical_device(router_params)

              self.phy_router_fixture = self.create_bgp_router(router_params,phy_device_fixture)

              if single_mx_bgp_router:
                 for cn_bgp_name in self.inputs.bgp_names:
                     fq_name = [u'default-domain', u'default-project', u'ip-fabric', u'__default__', u'%s'%cn_bgp_name]
                     cn_node_obj = self.connections.vnc_lib.bgp_router_read(fq_name=fq_name)
                     cn_node_obj.add_bgp_router(self.phy_router_fixture.bgp_router)
                 self.connections.vnc_lib.bgp_router_update(cn_node_obj)
              else:
                 cn_name = self.inputs.host_data[self.inputs.bgp_names[i]]['name']
                 fq_name = [u'default-domain', u'default-project', u'ip-fabric', u'__default__', u'%s'%cn_name]
                 cn_node_obj = self.connections.vnc_lib.bgp_router_read(fq_name=fq_name)
                 cn_node_obj.add_bgp_router(self.phy_router_fixture.bgp_router)
                 self.connections.vnc_lib.bgp_router_update(cn_node_obj)


              peer_config = {}
              peer_config['peer_ips'] = self.inputs.bgp_control_ips
              if cluster_use_local_asn:
                 peer_config['peer_asn'] = cluster_local_asn
              else:
                 peer_config['peer_asn'] = control_node_asn[i]
              router_params['asn'] = mx_asn[i]

              router_params['group']      = None
              router_params['cluster_group'] = None
              router_params['test_group_name'] = mx_config['test_group_name']
              router_params['test_bgp_proto_group_name'] = mx_config['test_bgp_proto_group_name']

              if single_mx_bgp_router and i == 0 :
                 configure_mx_basic = True
              elif not single_mx_bgp_router:
                 configure_mx_basic = True
              else:
                 configure_mx_basic = False

              if configure_mx_basic:
                 self.mx_basic_bgp_test_configuration(router_params,peer_config,skip_cleanup=True)

    def configure_control_nodes(self,control_node_config,mx_config):
        self.logger.info("Configure CONTROL_NODES")

        existing_4b_capability = self.get_4byte_enable()

        new_cluster_4b_capability = control_node_config['cluster_4b_capability']
        new_cluster_global_asn    = control_node_config['cluster_global_asn']
        control_node_asn     = control_node_config['control_node_asn']

        if existing_4b_capability != new_cluster_4b_capability:
           self.set_4byte_enable(new_cluster_4b_capability)
           self.addCleanup(self.set_4byte_enable,existing_4b_capability)

        existing_global_asn = self.get_global_asn()

        if existing_global_asn != new_cluster_global_asn:
           self.set_global_asn(new_cluster_global_asn)

        for i,ctrl_node_name in enumerate(self.inputs.bgp_names):
             ctrl_node_ip = self.inputs.host_data[ctrl_node_name]['control-ip']
             ctrl_node_host_ip = self.inputs.host_data[ctrl_node_name]['host_ip']
             ctrl_fixture = self.useFixture(
                       control_node.CNFixture(
                                 connections=self.connections,
                                 inputs=self.inputs,
                                 router_name=ctrl_node_name,
                                 router_ip=ctrl_node_ip
                                 ))
             if ctrl_fixture.already_present:
                fq_name = [u'default-domain', u'default-project', u'ip-fabric', u'__default__', u'%s'%ctrl_node_name]
                bgp_obj = self.connections.vnc_lib.bgp_router_read(fq_name=fq_name)
                router_params = bgp_obj.get_bgp_router_parameters()
                existing_asn  = router_params.get_autonomous_system()
                existing_local_asn  = router_params.get_local_autonomous_system()
                router_params.set_autonomous_system(control_node_asn[i])
                if cluster_use_local_asn:
                   router_params.set_local_autonomous_system(cluster_local_asn)
                else:
                   router_params.set_local_autonomous_system(None)
                prev_local_asn = None
                bgp_obj.set_bgp_router_parameters(router_params)
                self.connections.vnc_lib.bgp_router_update(bgp_obj)
                self.addCleanup(self.set_bgp_router_asn,bgp_obj.uuid,existing_asn,prev_local_asn)

    def create_vn(self,control_node_config):

        vn_fixture = self.useFixture(VNFixture(connections=self.connections))
        vn_fixture.verify_vn_in_api_server()
        return vn_fixture

        for device in self.inputs.physical_routers_data.iteritems():
          router_name   = device[0]
          router_params = device[1]
        
          if router_name != "blr-mx1":
             continue

          router_params['asn'] = control_node_config['control_node_asn'][0]
    
          phy_router_fixture = self.useFixture(PhysicalRouterFixture(
                router_params['name'], router_params['mgmt_ip'],
                model=router_params['model'],
                vendor=router_params['vendor'],
                asn=router_params['asn'],
                ssh_username=router_params['ssh_username'],
                ssh_password=router_params['ssh_password'],
                mgmt_ip=router_params['mgmt_ip'],
                tunnel_ip=router_params['tunnel_ip'],
                ports=router_params['ports'],
                connections=self.connections,
                logger=self.logger))
          self.extend_vn_to_physical_router(vn_fixture, phy_router_fixture)

        return vn_fixture

    def create_vms(self,vn_fixture,vm_config_list=[]):
        vm_fixt_list = []
        for vm in vm_config_list:
            vm_fixture = self.useFixture(
                          VMFixture(
                              project_name=self.inputs.project_name,
                              connections=self.connections,
                              vn_objs=[
                                  vn_fixture.obj],
                              image_name=vm['image_name'],
                              vm_name=vm['vm_name']))
            vm_fixt_list.append(vm_fixture)
        for vm_fixture in vm_fixt_list:
            vm_fixture.verify_on_setup()
        return vm_fixt_list
 
    def verify_bgpaas_bgp_routes(self,control_node_config,vn_fixture,src_vm,bgpaas_vm,vm_config,expected_routes):
        bgp_summary = self.get_config_via_netconf(src_vm,bgpaas_vm,'show bgp summary')
        control_node_asn = control_node_config['control_node_asn'][0]
        gw_ip            = vn_fixture.get_subnets()[0]['gateway_ip']
        dns_ip           = vn_fixture.get_subnets()[0]['dns_server_address'] 
        if control_node_asn > 65535 and not vm_config['4b_capability']:
           peer_asn = 23456
        else:
           peer_asn = control_node_asn
        gw_ip_state = re.search("%s\s+%d\s+.*Establ"%(gw_ip,peer_asn),bgp_summary)
        dns_ip_state = re.search("%s\s+%d\s+.*Establ"%(dns_ip,peer_asn),bgp_summary)
        
        if not (gw_ip_state and dns_ip_state ):
           assert False,'BGPaaS Session is not in Established State'

        routes_output = self.get_config_via_netconf(src_vm,bgpaas_vm,'show route receive-protocol bgp %s'%gw_ip)
        for exp_route in expected_routes:
            ret = re.search(exp_route,routes_output)
            if ret:
               self.logger.info("Route seen in BGPaaS: %s"%exp_route)
            else:
               assert False,"Route: %s not seen in BGPaaS"%exp_route


    def generate_expected_routes(self,control_node_config,vn_fixture,mx_config,vm_fixt_list,vm_config_list):

        control_node_asn = control_node_config['control_node_asn']
        mx_asn           = mx_config['mx_asn']
        mx_static_routes = self.get_mx_configured_addnl_static_routes()
        mx_aggr_route,mx_aggr_static_routes = self.get_mx_configured_aggr_routes()
        bgp_type = control_node_config['control,mx,bgp_type']
       
        ### START: Routes to be seen at vSRX1: ######
        vsrx1_routes = vsrx2_routes = mx_routes = []

        peer_bgpaas_asn = vm_config_list[2]['asn']
        vn_gw_ip        = vn_fixture.get_subnets()[0]['gateway_ip']

        # route from other vSRX
        for static_route in vm_config_list[2]['static_routes']:
            vsrx1_routes.append('%s\s+%s\s+%d %d'%(static_route,vn_gw_ip,control_node_asn[0],peer_bgpaas_asn))
        for static_route in vm_config_list[2]['static_routes_aggr']:
            vsrx1_routes.append('%s\s+%s\s+%d %d'%(static_route,vn_gw_ip,control_node_asn[0],peer_bgpaas_asn))
        vsrx1_routes.append('%s\s+%s\s+%d %d'%(vm_config_list[2]['aggr_route'],vn_gw_ip,control_node_asn[0],peer_bgpaas_asn))

        # Routes from MX
        if bgp_type == "internal":
           for static_route in mx_static_routes:
               vsrx1_routes.append('%s\s+%s\s+%d (I|\?)'%(static_route,vn_gw_ip,control_node_asn[0]))
           vsrx1_routes.append('%s\s+%s\s+%d (I|\?)'%(mx_aggr_route,vn_gw_ip,control_node_asn[0]))
        else:
           for static_route in mx_static_routes:
               vsrx1_routes.append('%s\s+%s\s+%d %d'%(static_route,vn_gw_ip,control_node_asn[0],mx_asn[0]))
           vsrx1_routes.append('%s\s+%s\s+%d %d'%(mx_aggr_route,vn_gw_ip,control_node_asn[0],mx_asn[0]))

        ### START: Routes to be seen at vSRX2: ######
 
        vsrx2_routes = []
        peer_bgpaas_asn = vm_config_list[1]['asn']
        vn_gw_ip        = vn_fixture.get_subnets()[0]['gateway_ip']
        for static_route in vm_config_list[1]['static_routes']:
            vsrx2_routes.append('%s\s+%s\s+%d %d'%(static_route,vn_gw_ip,control_node_asn[0],peer_bgpaas_asn))
        for static_route in vm_config_list[1]['static_routes_aggr']:
            vsrx2_routes.append('%s\s+%s\s+%d %d'%(static_route,vn_gw_ip,control_node_asn[0],peer_bgpaas_asn))
        vsrx2_routes.append('%s\s+%s\s+%d %d'%(vm_config_list[1]['aggr_route'],vn_gw_ip,control_node_asn[0],peer_bgpaas_asn))
        # Routes from MX
        if bgp_type == "internal":
           for static_route in mx_static_routes:
               vsrx2_routes.append('%s\s+%s\s+%d (I|\?)'%(static_route,vn_gw_ip,control_node_asn[0]))
           vsrx2_routes.append('%s\s+%s\s+%d (I|\?)'%(mx_aggr_route,vn_gw_ip,control_node_asn[0]))
        else:
           for static_route in mx_static_routes:
               vsrx2_routes.append('%s\s+%s\s+%d %d'%(static_route,vn_gw_ip,control_node_asn[0],mx_asn[0]))
           vsrx2_routes.append('%s\s+%s\s+%d %d'%(mx_aggr_route,vn_gw_ip,control_node_asn[0],mx_asn[0]))

        ### START: Routes to be seen at MX ######

        mx_routes = []
        for i,vm_config in enumerate(vm_config_list):
            vm_ip = vm_fixt_list[i].vm_ips[0]
            compute_data_ip = vm_fixt_list[i].vm_node_data_ip
            if bgp_type == "internal":
               mx_routes.append('%s/32\s+%s\s+100\s+200\s+\?'%(vm_ip,compute_data_ip))
            else:
               mx_routes.append('%s/32\s+%s\s+100\s+%d \?'%(vm_ip,compute_data_ip,control_node_asn[0]))
            if i == 0:
               continue
            if bgp_type == "internal":
               for static_route in vm_config['static_routes']:
                   mx_routes.append('%s\s+%s\s+100\s+%d I'%(static_route,compute_data_ip,vm_config['asn']))
               for static_route in vm_config['static_routes_aggr']:
                   mx_routes.append('%s\s+%s\s+100\s+%d I'%(static_route,compute_data_ip,vm_config['asn']))
               mx_routes.append('%s\s+%s\s+100\s+%d I'%(vm_config['aggr_route'],compute_data_ip,vm_config['asn']))
            else:
               for static_route in vm_config['static_routes']:
                   mx_routes.append('%s\s+%s\s+%d %d I'%(static_route,compute_data_ip,control_node_asn[0],vm_config['asn']))
               for static_route in vm_config['static_routes_aggr']:
                   mx_routes.append('%s\s+%s\s+%d %d I'%(static_route,compute_data_ip,control_node_asn[0],vm_config['asn']))
               mx_routes.append('%s\s+%s\s+%d %d I'%(vm_config['aggr_route'],compute_data_ip,control_node_asn[0],vm_config['asn']))
  
        return mx_routes,vsrx1_routes,vsrx2_routes

    def verify_received_routes_in_mx(self,mx_config,peer_ips,expected_routes,bgp_type):
        conn = self.phy_router_fixture.get_connection_obj('juniper',mx_config['control_ip'],'root','c0ntrail123')
        output_dict = {}
        for control_ip in peer_ips:
            cmd = 'show route receive-protocol bgp %s table %s'%(control_ip,mx_config['ri_name'])
            output_dict[control_ip] = conn.handle.cli(cmd)
        route_seen_dict = {}
        for route in expected_routes:
            route_seen_dict[route] = []
        for control_ip in peer_ips:
           for route in expected_routes:
               ret = re.search(route,output_dict[control_ip])
               if ret:
                  route_seen_dict[route].append(control_ip)

        for route in expected_routes:
            if len(route_seen_dict[route]) == 0 :
               assert False,"Route: %s not seen in receive-protocol in MX"%route
            elif bgp_type == "internal" and len(route_seen_dict[route]) != 2:
              self.logger.info("iBGP Update not seen from 2 CN for Route: %s , count: %d"%(route,len(route_seen_dict[route])))
            elif bgp_type == "external" and len(route_seen_dict[route]) != 3:
              self.logger.info("eBGP Update not seen from 3 CN for Route: %s , count: %d"%(route,len(route_seen_dict[route])))
            else:
              self.logger.info("BGP Update Seen correctly for Route: %s , count: %d"%(route,len(route_seen_dict[route])))
 
    def verify_cn_instrospect(self,vn_fixture,prefix_info):
        ri_display_name = vn_fixture.api_s_routing_instance['routing_instances'][0]['routing-instance']['display_name']
        ri_name ="%s:%s:%s"%(self.connections.project_name,ri_display_name,ri_display_name)
        prefix = prefix_info['prefix']
        as_path = prefix_info['as_path']
        as4_path = prefix_info['as4_path']

        for cn in self.inputs.bgp_control_ips:
            cn_entry = self.cn_inspect[cn].get_cn_route_table_entry(prefix=prefix,table="inet.0",ri_name=ri_name)
    
    @test.attr(type=['sanity'])
    @preposttest_wrapper
    #@skip_because(mx_gw=False,msg='Need to set MX_GW=True and atleast one Physical Router')
    def test_basic_as4_ibgp(self):

        if len(self.inputs.ext_routers) != 1:
           raise self.skipTest(
                "Skipping Test. At least 1 external router required to run the test")

        mx_name = self.inputs.ext_routers[0][0]
        mx_info = self.inputs.physical_routers_data[mx_name]
         
        topology_info = {}
        topology_info['mx_control_ip_address'] = [mx_info['control_ip']]
        topology_info['mx_tunnel_ip']        = mx_info['tunnel_ip']
        topology_info['mx_vrf_interfaces']   = [mx_info['vrf_interface']]
        topology_info['mx_bgp_protocol_group']  = mx_info.get('bgp_protocol_group',None)
        topology_info['test_group_name']        = "testbed_%s_4byte" %mx_name
        topology_info['test_bgp_proto_group_name'] = "testbed_%s_4byte_bgp" %mx_name
        topology_info['test_ri_name']           = "ri_4byte_test"
        topology_info['mx_cluster_group']       = mx_info.get('cluster_group',None)
        topology_info['mx_name']                = mx_name

        test_info = {}
        test_info['step1,cluster_global_asn'] = 8901
        test_info['step1,control_node_asn']   = [8901,8901,8901]
        test_info['step1,mx_asn']             = [8901,8901,8901]
        test_info['step1,cluster_4b_capability'] = False
        test_info['step1,mx_4b_capability']      = False

        test_info['step2,cluster_global_asn'] = 89000
        test_info['step2,control_node_asn']   = [89000,89000,89000]
        test_info['step2,mx_asn']             = [89000,89000,89000]
        test_info['step2,cluster_4b_capability'] = True
        test_info['step2,mx_4b_capability']      = True

        self.basic_as4(topology_info,test_info)

    @preposttest_wrapper
    #@skip_because(mx_gw=False,msg='Need to set MX_GW=True and atleast one Physical Router')
    def test_basic_as4_ebgp(self):

        if len(self.inputs.ext_routers) != 1:
           raise self.skipTest(
                "Skipping Test. At least 1 external router required to run the test")

        mx_name = self.inputs.ext_routers[0][0]
        mx_info = self.inputs.physical_routers_data[mx_name]
         
        topology_info = {}
        topology_info['mx_control_ip_address'] = [mx_info['control_ip']]
        topology_info['mx_tunnel_ip']        = mx_info['tunnel_ip']
        topology_info['mx_vrf_interfaces']   = [mx_info['vrf_interface']]
        topology_info['mx_bgp_protocol_group']  = mx_info.get('bgp_protocol_group',None)
        topology_info['test_group_name']        = "testbed_%s_4byte" %mx_name
        topology_info['test_bgp_proto_group_name'] = "testbed_%s_4byte_bgp" %mx_name
        topology_info['test_ri_name']           = "ri_4byte_test"
        topology_info['mx_cluster_group']       = mx_info.get('cluster_group',None)
        topology_info['mx_name']                = mx_name

        test_info = {}
        test_info['step1,cluster_global_asn'] = 8902
        test_info['step1,control_node_asn']   = [8902,8902,8902]
        test_info['step1,mx_asn']             = [8903,8903,8903]
        test_info['step1,cluster_4b_capability'] = False
        test_info['step1,mx_4b_capability']      = False

        test_info['step2,cluster_global_asn'] = 89002
        test_info['step2,control_node_asn']   = [89002,89002,89002]
        test_info['step2,mx_asn']             = [89003,89003,89003]
        test_info['step2,cluster_4b_capability'] = True
        test_info['step2,mx_4b_capability']      = True

        self.basic_as4(topology_info,test_info)


    def basic_as4(self,topology_info,test_info):

        initial_neigh_info = self.get_neighbor_info()
        cluster_global_asn = test_info['step1,cluster_global_asn']
        control_node_asn   = test_info['step1,control_node_asn']
        mx_asn             = test_info['step1,mx_asn']
        cluster_4b_capability = test_info['step1,cluster_4b_capability']
        mx_4b_capability      = test_info['step1,mx_4b_capability']
        mx_control_ip_address = topology_info['mx_control_ip_address']
        mx_tunnel_ip        = topology_info['mx_tunnel_ip']
        if test_info['step1,control_node_asn'] == test_info['step1,mx_asn'] :
           bgp_type = "internal"
        else:
           bgp_type = "external"
        mx_config = {}
        mx_config['mx_4b_capability']  = test_info['step1,mx_4b_capability']
        mx_config['mx_asn']            = test_info['step1,mx_asn']
        mx_config['mx_vrf_interfaces'] = topology_info['mx_vrf_interfaces']
        mx_config['bgp_protocol_group'] = topology_info['mx_bgp_protocol_group']
        mx_config['cluster_group']      = topology_info['mx_cluster_group']
        mx_config['test_group_name']  = topology_info['test_group_name']
        mx_config['test_bgp_proto_group_name']  = topology_info['test_bgp_proto_group_name']
        mx_config['ri_name']           = topology_info['test_ri_name']
        mx_config["vrf_interface"]     = mx_config['mx_vrf_interfaces'][0] + ".0"
        mx_config["rd"]                = mx_control_ip_address[0].split("/")[0] + ":0"
        mx_config['control_ip']    = mx_tunnel_ip
        mx_config['mx_control_ip_address'] = topology_info['mx_control_ip_address']
        mx_config['mx_name']             = topology_info['mx_name']

        control_node_config = {}
        control_node_config['cluster_4b_capability'] = cluster_4b_capability
        control_node_config['cluster_global_asn']    = cluster_global_asn
        control_node_config['control_node_asn']      = control_node_asn
        control_node_config['mx_config']             = mx_config
        control_node_config['control,mx,bgp_type']   = bgp_type
        
        self.logger.info("STEP:1    a. Disable '4 Byte Enabled' in Global System Configuration")
        self.logger.info("          b. Configure 2 Byte AS in Global System Configuration")
        self.logger.info("          c. Configure iBGP with MX")
        self.logger.info("          d. Create 1st BGPaaS with 2 Byte AS and 4Byte Capability Disabled")
        self.logger.info("          e. Create 2nd BGPaaS with 4 Byte AS and 4Byte Capability Enabled")
        self.logger.info("          f. Configure static routes and aggregate routes to be advertised by MX.Update routing-instance with VN rt and add community")
        self.logger.info("Verification: a. Verify Routes from MX are received and seen in Both BGPaaS.Verify AS_PATH")
        self.logger.info("              b. Verify Routes from both BGPaaS are seen in MX")
        self.logger.info("STEP:2        a. Enable '4 Byte Enabled' in Global System Configuration")
        self.logger.info("Verification: a. Verify Routes from MX are received and seen in Both BGPaaS.Verify AS_PATH")
        self.logger.info("              b. Verify Routes from both BGPaaS are seen in MX")
        self.logger.info("STEP:3 \n a. Update 4 Byte AS in Global System Configuration")
        self.logger.info("          b. Update Cluster 4 Byte AS,RT in MX and AS in BGPaaS")
        self.logger.info("Verification: a. Verify Routes from MX are received and seen in Both BGPaaS.Verify AS_PATH")
        self.logger.info("              b. Verify Routes from both BGPaaS are seen in MX")
        existing_global_asn = self.get_global_asn()
        self.addCleanup(self.connections.vnc_lib_fixture.set_global_asn, existing_global_asn)

        self.configure_control_nodes(control_node_config,mx_config)
        self.deactivate_mx_cluster_configuration(mx_config)
        self.configure_physical_devices(control_node_config,mx_config)
        self.addCleanup(self.activate_mx_cluster_configuration,mx_config)

        vm_config_list = [] 
        vm_config = {}
        vm_config['image_name'] = 'ubuntu-traffic'
        vm_config['vm_name']    = 'test-vm'
        vm_config_list.append(vm_config)

        vm_config = {}
        vm_config['image_name'] = 'vsrx'
        vm_config['vm_name']    = 'bgpaas-vm1'
        vm_config['asn']        = 9000
        vm_config['static_routes']      = self.vsrx1_addnl_static_routes()
        vm_config['aggr_route'],vm_config['static_routes_aggr'] = self.vsrx1_aggr_routes()
        vm_config['peer_asn']           = control_node_asn[0]
        vm_config['4b_capability'] = False
        vm_config_list.append(vm_config)

        vm_config = {}
        vm_config['image_name'] = 'vsrx'
        vm_config['vm_name']    = 'bgpaas-vm2'
        vm_config['asn']        = 90000
        vm_config['4b_capability'] = True
        vm_config['peer_asn']      = control_node_asn[0]
        vm_config['static_routes'] = self.vsrx2_addnl_static_routes()
        vm_config['aggr_route'],vm_config['static_routes_aggr'] = self.vsrx2_aggr_routes()
        vm_config['4b_capability'] = True
        vm_config_list.append(vm_config)

        ##### START OF STEP1: ####################
        vn_fixture = self.create_vn(control_node_config=control_node_config)
        vm_fixt_list = self.create_vms(vn_fixture=vn_fixture,vm_config_list=vm_config_list)

        bgpaas_fixture_list = self.configure_bgpaas_vms(control_node_config=control_node_config,vn_fixture=vn_fixture,vm_fixt_list=vm_fixt_list,vm_config_list=vm_config_list)
        self.update_sg_group()

        self.mx_create_vrf(control_node_config=control_node_config,mx_config=mx_config,vn_fixture=vn_fixture)
        self.mx_aggregated_routes_configuration(control_node_config,mx_config,vn_fixture)
        self.mx_static_routes_configuration(control_node_config,mx_config,vn_fixture)

        mx_routes,vsrx1_routes,vsrx2_routes = self.generate_expected_routes(control_node_config,vn_fixture,mx_config,vm_fixt_list,vm_config_list)

        self.verify_bgpaas_bgp_routes(control_node_config=control_node_config,vn_fixture=vn_fixture,src_vm=vm_fixt_list[0],bgpaas_vm=vm_fixt_list[1],vm_config=vm_config_list[1],expected_routes=vsrx1_routes)
        self.verify_bgpaas_bgp_routes(control_node_config=control_node_config,vn_fixture=vn_fixture,src_vm=vm_fixt_list[0],bgpaas_vm=vm_fixt_list[2],vm_config=vm_config_list[1],expected_routes=vsrx2_routes)
        self.verify_received_routes_in_mx(mx_config,peer_ips=self.inputs.bgp_control_ips,expected_routes=mx_routes,bgp_type=bgp_type)

        ###### END OF STEP1: ####################
        ###### START OF STEP2: ####################

        #self.logger.info("START of STEP2")

        cluster_4b_capability = True
        self.set_4byte_enable(cluster_4b_capability)
        self.update_bgpaas_configuration(control_node_config=control_node_config,vm_config=vm_config_list[1],bgpaas_fixt=bgpaas_fixture_list[1])
        self.update_bgpaas_configuration(control_node_config=control_node_config,vm_config=vm_config_list[2],bgpaas_fixt=bgpaas_fixture_list[2])
        time.sleep(60)
        self.verify_bgpaas_bgp_routes(control_node_config=control_node_config,vn_fixture=vn_fixture,src_vm=vm_fixt_list[0],bgpaas_vm=vm_fixt_list[1],vm_config=vm_config_list[1],expected_routes=vsrx1_routes)
        self.verify_bgpaas_bgp_routes(control_node_config=control_node_config,vn_fixture=vn_fixture,src_vm=vm_fixt_list[0],bgpaas_vm=vm_fixt_list[2],vm_config=vm_config_list[1],expected_routes=vsrx2_routes)
        self.verify_received_routes_in_mx(mx_config,peer_ips=self.inputs.bgp_control_ips,expected_routes=mx_routes,bgp_type=bgp_type)

        ###### END OF STEP2: ####################
        self.logger.info("END of STEP2")
        self.logger.info("START of STEP3")

        cluster_global_asn = test_info['step2,cluster_global_asn']
        self.set_global_asn(cluster_global_asn)
        control_node_asn = test_info['step2,control_node_asn']
        mx_asn           = test_info['step2,mx_asn']
        mx_config['mx_4b_capability']  = test_info['step2,mx_4b_capability']
        control_node_config['cluster_4b_capability'] = test_info['step2,cluster_4b_capability']

        control_node_config['control_node_asn'] = control_node_asn
        control_node_config['cluster_global_asn'] = cluster_global_asn
        mx_config['mx_asn']                     = mx_asn
        self.configure_physical_devices(control_node_config,mx_config)
        self.reconfigure_bgpaas_vms(control_node_config=control_node_config,vm_fixt_list=vm_fixt_list,vm_config_list=vm_config_list)

        self.mx_create_vrf(control_node_config=control_node_config,mx_config=mx_config,vn_fixture=vn_fixture)

        self.mx_aggregated_routes_configuration(control_node_config,mx_config,vn_fixture)
        self.mx_static_routes_configuration(control_node_config,mx_config,vn_fixture)

        self.update_bgpaas_configuration(control_node_config=control_node_config,vm_config=vm_config_list[1],bgpaas_fixt=bgpaas_fixture_list[1])
        self.update_bgpaas_configuration(control_node_config=control_node_config,vm_config=vm_config_list[2],bgpaas_fixt=bgpaas_fixture_list[2])
        time.sleep(60)

        mx_routes,vsrx1_routes,vsrx2_routes = self.generate_expected_routes(control_node_config,vn_fixture,mx_config,vm_fixt_list,vm_config_list)
        self.verify_bgpaas_bgp_routes(control_node_config=control_node_config,vn_fixture=vn_fixture,src_vm=vm_fixt_list[0],bgpaas_vm=vm_fixt_list[1],vm_config=vm_config_list[1],expected_routes=vsrx1_routes)
        self.verify_bgpaas_bgp_routes(control_node_config=control_node_config,vn_fixture=vn_fixture,src_vm=vm_fixt_list[0],bgpaas_vm=vm_fixt_list[2],vm_config=vm_config_list[2],expected_routes=vsrx2_routes)
        self.verify_received_routes_in_mx(mx_config,peer_ips=self.inputs.bgp_control_ips,expected_routes=mx_routes,bgp_type=bgp_type)
        ##### END OF STEP3: ####################
        self.logger.info("END of STEP3")
        final_neigh_info = self.get_neighbor_info()
        self.logger.info("Initial_flap_count",initial_neigh_info)
        self.logger.info("Final_flap_count",initial_neigh_info)

    def update_sg_group(self):
        sg_obj = self.connections.vnc_lib.security_group_read(fq_name=[u'default-domain', u'%s'%self.connections.project_name, u'default'])
        self.connections.orch.delete_security_group_rules(sg_id=sg_obj.uuid,project_id=self.connections.project_id)
        uuid_1 = uuid.uuid1().urn.split(':')[2]
        uuid_2 = uuid.uuid1().urn.split(':')[2]
        secgrp_rules =  [
              {'direction': '>',
                  'protocol': 'any',
                  'dst_addresses': [{'security_group': 'local', 'subnet': None}],
                  'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_ports': [{'start_port': 0, 'end_port': 65535}],
                  'src_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                  'rule_uuid': uuid_1
               }, {'direction': '<',
                   'protocol': 'any',
                   'src_addresses': [{'security_group': 'local', 'subnet': None}],
                   'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                   'src_ports': [{'start_port': 0, 'end_port': 65535}],
                   'dst_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}], 'rule_uuid': uuid_2}, ]
        self.connections.orch.set_security_group_rules(sg_id=sg_obj.uuid, sg_entries=secgrp_rules)

