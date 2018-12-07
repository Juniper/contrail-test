#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import *
import test_v1
from common import isolated_creds
from common.connections import ContrailConnections
from common.neutron.base import BaseNeutronTest
from tcutils.control.cn_introspect_utils import ControlNodeInspect 
from common.device_connection import NetconfConnection
from physical_router_fixture import PhysicalRouterFixture
#from control_node import CNFixture
from control_node import *
import time

class TestLlgrBase(BaseNeutronTest):
 
    @classmethod
    def setUpClass(cls):
        '''
            It will set up a topology where agent is connected to only one of the control node
            This way we make sure that the route is learned from a different agent via bgp
        '''
        super(TestLlgrBase, cls).setUpClass()
        cls.cn_introspect = ControlNodeInspect(cls.inputs.bgp_ips[0])
        cls.host_list = cls.connections.orch.get_hosts()
        cls.vnc_lib_fixture=cls.connections.vnc_lib_fixture
        cls.mx_loopback_ip = cls.inputs.public_host 
        cls.mx_loopback_ip6 = cls.inputs.public_host_v6
        device = cls.inputs.physical_routers_data
        if not device:
            self.logger.error("Not able to get device info from inputs")  
            return False
        cls.device_name = device.items()[0][0]
        cls.router_params = device[cls.device_name]
        cls.mx1_ip = cls.router_params['mgmt_ip']
        cls.mx_user = cls.router_params['ssh_username']
        cls.mx_password = cls.router_params['ssh_password'] 
        cls.mx_peer_ip = cls.router_params['tunnel_ip']
        cls.mx1_handle = NetconfConnection(host = cls.mx1_ip,username=cls.mx_user,password=cls.mx_password)
        cls.mx1_handle.connect()
        cls.phy_router_fixture = None
        time.sleep(20)
    # end setUp

    @classmethod
    def tearDownClass(cls):
        super(TestLlgrBase, cls).tearDownClass()
    # end cleanUp

    def setUp(self):
        super(TestLlgrBase, self).setUp()
        if len(self.host_list) > 1 and len(self.inputs.bgp_ips) > 1 :
            self.set_xmpp_peering(compute_ip=self.inputs.host_data[self.host_list[0]]['host_control_ip'] , 
                                 ctrl_node=self.inputs.bgp_ips[0],mode='disable')
            self.set_xmpp_peering(compute_ip=self.inputs.host_data[self.host_list[1]]['host_control_ip'] , 
                                 ctrl_node=self.inputs.bgp_ips[1],mode='disable')
        if self.create_bgp_router() is None:
            self.logger.error("Not able to create BGP router")
            return False

    def tearDown(self):
        self.set_bgp_peering(mode='enable')
        self.set_gr_llgr(mode='disable')
        self.set_xmpp_peering(compute_ip=self.inputs.host_data[self.host_list[0]]['host_control_ip'] , 
                                           mode='enable')
        self.set_xmpp_peering(compute_ip=self.inputs.host_data[self.host_list[1]]['host_control_ip'] , 
                                           mode='enable')
        super(TestLlgrBase,self).tearDown()

    def set_gr_llgr(self, **kwargs):
        '''
           Enable/Disable GR / LLGR configuration with gr/llgr timeout values as parameters
        '''
        gr_timeout = kwargs['gr'] if 'gr' in kwargs else 0
        llgr_timeout = kwargs['llgr'] if 'llgr' in kwargs else 0
        gr_enable = True if kwargs['mode'] == 'enable' else False
        eor_timeout = '60'
        router_asn = '64512' if gr_enable == True else self.inputs.router_asn
        bgp_hlp = False if kwargs.has_key('bgp_hlp') and kwargs['bgp_hlp'] == 'disable' else True
        xmpp_hlp = True if kwargs.has_key('xmpp_hlp') and kwargs['xmpp_hlp'] == 'enable' else False
        self.vnc_lib_fixture.set_graceful_restart(gr_restart_time=gr_timeout,
                                     llgr_restart_time = llgr_timeout, 
                                     eor_timeout = eor_timeout, 
                                     gr_enable = gr_enable, 
                                     router_asn = router_asn,
                                     bgp_helper_enable = bgp_hlp, 
                                     xmpp_helper_enable = xmpp_hlp)
        return True

    def set_bgp_peering(self,**kwargs):
        ''' 
           Stop and start of BGP peer communication so that GR/LLGR timers are triggered
        '''
        mode = kwargs['mode']
        port = 179 if not kwargs.has_key('port') else kwargs['port']
        if mode == 'disable':
            cmd = 'iptables -A OUTPUT -p tcp --destination-port %s -j DROP; \
                     iptables -A INPUT -p tcp --destination-port %s -j DROP;\
                     iptables -A OUTPUT -p tcp --source-port %s -j DROP;\
                     iptables -A INPUT -p tcp --source-port %s -j DROP' %(port,port,port,port)
        else:
            cmd = 'iptables -D OUTPUT -p tcp --destination-port %s -j DROP; \
                  iptables -D INPUT -p tcp --destination-port %s -j DROP; \
                  iptables -D OUTPUT -p tcp --source-port %s -j DROP; \
                  iptables -D INPUT -p tcp --source-port %s -j DROP'%(port,port,port,port)
        self.logger.debug('%s bgp peering : %s' %(mode,cmd))
        for host in self.inputs.bgp_ips:
            self.inputs.run_cmd_on_server(host,cmd)
        return True

    def create_bgp_router(self):
        if self.phy_router_fixture is None:
            self.phy_router_fixture = self.useFixture(PhysicalRouterFixture(
                                         self.router_params['name'], self.router_params['mgmt_ip'],
                                         model=self.router_params['mode'],
                                         vendor=self.router_params['vendor'],
                                         asn=self.router_params['asn'],
                                         ssh_username=self.router_params['ssh_username'],
                                         ssh_password=self.router_params['ssh_password'],
                                         mgmt_ip=self.router_params['mgmt_ip'],
                                         tunnel_ip=self.router_params['tunnel_ip'],
                                         connections=self.connections,
                                         logger=self.logger))
        return self.phy_router_fixture

    def verify_traffic_loss(self,**kwargs):
        vm1_fixture = kwargs['vm_fixture'] 
        result_file = kwargs['result_file']
        pkts_trans = '0'
        pkts_recv = '0'
        ret = False
 
        cmd = 'cat %s | grep loss'% result_file
        res = vm1_fixture.run_cmd_on_vm(cmds=[cmd]) 
        self.logger.debug('results %s' %(res))
        if not res[cmd]:
            self.logger.error("Not able to get the log file %s"%res)
            return (ret,pkts_trans,pkts_recv)

        pattern = '''(\S+) packets transmitted, (\S+) received, (\S+)% packet loss'''
        res = re.search(pattern,res[cmd]) 
        if res:
            pkts_trans = res.group(1)
            pkts_recv = res.group(2) 
            loss = res.group(3)
            ret = True
        return (ret,pkts_trans,pkts_recv)

    @retry(tries=20, delay=6)
    def verify_gr_llgr_flags(self,**kwargs):
        '''
           Validate Stale / LLgrStale flags after GR/LLGR timer is triggered
        '''
        flags = kwargs['flags']
        vn_fix = kwargs['vn_fix']
        prefix = kwargs['prefix']
        ri = vn_fix.vn_fq_name+":"+vn_fix.vn_name
        rtbl_entry = self.cn_introspect.get_cn_route_table_entry(prefix,ri)
        if not rtbl_entry:
            self.logger.error("Not able to find route table entry %s"%prefix)
            return False
        rtbl = self.cn_introspect.get_cn_route_table_entry(prefix,ri)[0]
        if not rtbl :
            self.logger.error("Not able to find route table for prefix %s"%prefix)
            return False
        self.logger.debug('prefix flags %s' %(rtbl['flags']))
        if flags != rtbl['flags'] :
            self.logger.error("Not able to find route flags for prefix %s:%s"%(flags,rtbl['flags']))
            return False
        return True

    def set_xmpp_peering(self,**kwargs):
        ''' 
            Enabling / Disabling XMPP peer communication 
        '''
        compute_ip = kwargs['compute_ip']
        mode = kwargs['mode']
        control_ips = [] 
        if mode == 'disable':
            ctrl_host = kwargs['ctrl_node']
            ctrl_ip = self.inputs.host_data[ctrl_host]['host_data_ip'] or self.inputs.host_data[ctrl_host]['host_ip']
            self.configure_server_list(compute_ip, 'contrail-vrouter-agent',
                             'CONTROL-NODE', 'servers' , [ctrl_ip], container = "agent")
        else : 
            for ip in self.inputs.bgp_ips:
                control_ip = self.inputs.host_data[ip]['host_data_ip'] or self.inputs.host_data[ip]['host_ip']
                control_ips.append(control_ip)
            self.configure_server_list(compute_ip, 'contrail-vrouter-agent',
                           'CONTROL-NODE', 'servers' , control_ips , container = "agent")
        time.sleep(10)
        return True
   
    def set_headless_mode(self,**kwargs):
        ''' 
           Enabling/Disabling headless mode in agent 
        '''
        mode = kwargs['mode']
        if mode == 'enable':
            cmds = ['/usr/bin/openstack-config --set /etc/contrail/contrail-vrouter-agent.conf RESTART restore_enable true',
                   '/usr/bin/openstack-config --set /etc/contrail/contrail-vrouter-agent.conf RESTART backup_enable true']
        else:
            cmds = ['/usr/bin/openstack-config --set /etc/contrail/contrail-vrouter-agent.conf RESTART restore_enable False',
                  '/usr/bin/openstack-config --set /etc/contrail/contrail-vrouter-agent.conf RESTART backup_enable False']

        for host in self.host_list:
            self.logger.debug('enable headless mode %s : %s' %(host,cmds))
            for cmd in cmds:
                self.inputs.run_cmd_on_server(host,cmd,container='agent')
        self.inputs.restart_service('contrail-vrouter-agent',self.host_list)
        return True 

    def verify_gr_bgp_flags(self,**kwargs):
        '''
           Check for Notification bit,GR timeout,Forwarding state are sent properly during BGP Open message.
        '''
        pcap_file = kwargs['pcap_file']
        host = kwargs['host']
        control_ip = self.inputs.host_data[host]['host_control_ip'] or self.inputs.host_data[host]['host_ip']
        # Graceful Restart (64), length: 18
        #        Restart Flags: [none], Restart Time 35s
        #          AFI IPv4 (1), SAFI labeled VPN Unicast (128), Forwarding state preserved: yes
        #          AFI VPLS (25), SAFI Unknown (70), Forwarding state preserved: yes
        #          AFI IPv4 (1), SAFI Route Target Routing Information (132), Forwarding state preserved: yes
        #          AFI IPv6 (2), SAFI labeled VPN Unicast (128), Forwarding state preserved: yes
        # 0x0000:  4023 0001 8080 0019 4680 0001 8480 0002 (Check for 4023) , where 4 is notification bit
        # 4023  notification bit is set
        # 8080 forwarding state is set
        # 23 is 35 sec of gr time
        cmd = 'tcpdump -r %s -vvv -n | grep Open  -A28 | grep %s -A28 | grep \'Restart Flags\' -A8 | grep 0x0000'%(pcap_file,control_ip)
        res = self.inputs.run_cmd_on_server(host,cmd)
        self.logger.debug('results %s' %(res))
        res = res.split(':')
        flags = res[1].split(' ')
        if not flags:
            self.logger.error("not able to get flags %s"%flags)
            return False
        flags = [x for x in flags if x != '']
        self.logger.info("flags set properly %s"%flags[0])
        if flags[0] != '4023' and flags[2] != 8080:
            self.logger.error("flags not set properly %s"%flags[0])
            return False
        return True

    def verify_llgr_bgp_flags(self,**kwargs):
        '''
           Check for Notification bit, LLGR timeout,Forwarding state are sent properly during BGP Open message.
        '''
        pcap_file = kwargs['pcap_file']
        host = kwargs['host']
        control_ip = self.inputs.host_data[host]['host_control_ip'] or self.inputs.host_data[host]['host_ip']
        # Unknown (71), length: 28
        # no decoder for Capability 71
        # 0x0000:  0001 8080 0000 3c00 1946 8000 003c 0001
        # 8080 forwarding state is set
        # c0 is 65 sec of llgr time
        cmd = 'tcpdump -r %s -vvv -n | grep Open  -A32 | grep %s -A32 | grep \'Unknown (71)\' -A8 | grep 0x0000'%(pcap_file,control_ip)
        res = self.inputs.run_cmd_on_server(host,cmd)
        self.logger.debug('results %s' %(res))
        res = res.split(':')
        flags = res[1].split(' ')
        if not flags:
            self.logger.error("not able to get flags %s"%flags)
            return False
        flags = [x for x in flags if x != '']
        self.logger.info("flags set properly %s"%flags)
        if flags[3] != '3c00' and flags[1] != '8080':
            self.logger.error("flags not set properly %s"%flags[0])
            return False
        return True

    def configure_server_list(self, client_ip, client_process,
                               section, option, server_list, container):
        '''
        This function configures the .conf file with new server_list
        and then send a sighup to the client so that configuration
        change is effective.
        '''
        client_conf_file = client_process + ".conf"
        server_string =  ",".join(server_list)
        cmd_set = "openstack-config --set /etc/contrail/" + client_conf_file
        cmd = cmd_set + " " + section + " " + option + ' "%s"' % server_string
        cmd = "sed -i 's/CONTROLLER_NODES.*$/CONTROLLER_NODES=%s/g' /etc/contrail/common.env" % server_string 
        self.inputs.run_cmd_on_server(client_ip, cmd,
                            self.inputs.host_data[client_ip]['username']\
                            , self.inputs.host_data[client_ip]['password'],
                            )
        cmd = "sed -i 's/CONTROL_NODES.*$/CONTROL_NODES=%s/g' /etc/contrail/common.env" % server_string 
        self.inputs.run_cmd_on_server(client_ip, cmd,
                            self.inputs.host_data[client_ip]['username']\
                            , self.inputs.host_data[client_ip]['password'],
                            )

        cmd = "sed -i 's/CONTROLLER_NODES.*$/CONTROLLER_NODES=%s/g' /etc/contrail/common_vrouter.env" % server_string 
        self.inputs.run_cmd_on_server(client_ip, cmd,
                            self.inputs.host_data[client_ip]['username']\
                            , self.inputs.host_data[client_ip]['password'],
                            )

        cmd = "sed -i 's/CONTROL_NODES.*$/CONTROL_NODES=%s/g' /etc/contrail/common_vrouter.env" % server_string 
        self.inputs.run_cmd_on_server(client_ip, cmd,
                            self.inputs.host_data[client_ip]['username']\
                            , self.inputs.host_data[client_ip]['password'],
                            )

        cmd = 'cd /etc/contrail/vrouter/ ; docker-compose down ; docker-compose up -d'
        self.inputs.run_cmd_on_server(client_ip, cmd,
                            self.inputs.host_data[client_ip]['username']\
                            , self.inputs.host_data[client_ip]['password'],
                            )
        return True

    def is_test_applicable(self):
        # check for atleast 2 compute nodes
        if len(self.host_list) < 2 :
            return (False ,"compute nodes are not sufficient")
        # check for atleast 2 control nodes
        if len(self.inputs.bgp_ips) < 2 :
            return (False, "compute nodes are not sufficient")
        # check for 1 mx 
        if len(self.inputs.physical_routers_data) < 1:
            self.logger.error("MX routers are not sufficient : %s"%len(self.inputs.physical_routers_data))
            return (False ,"MX routers are not sufficient")
        return (True,None)


    def get_interface(self,ip):
        cmd = "ip -o -4 addr show | grep %s | awk \'{print $2}\'" % ip
        return self.inputs.run_cmd_on_server(ip,cmd)
