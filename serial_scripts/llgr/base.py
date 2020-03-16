#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
from common.neutron.base import BaseNeutronTest
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import *
import test_v1
from common import isolated_creds
from common.connections import ContrailConnections
from tcutils.control.cn_introspect_utils import ControlNodeInspect 
from common.device_connection import NetconfConnection
from control_node import CNFixture
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
        if len(cls.host_list) > 1 and len(cls.inputs.bgp_ips) > 1 :
            cls.set_xmpp_peering(compute_ip=cls.inputs.host_data[cls.host_list[0]]['host_control_ip'] , 
                                 ctrl_node=cls.inputs.bgp_ips[0],mode='disable')
            cls.set_xmpp_peering(compute_ip=cls.inputs.host_data[cls.host_list[1]]['host_control_ip'] , 
                                 ctrl_node=cls.inputs.bgp_ips[1],mode='disable')
        if cls.inputs.ext_routers:
            cls.mx1_ip = cls.inputs.ext_routers[0][1]
            # TODO remove the hard coding once we get this parameters populated from testbed
            cls.mx_user = 'root'
            cls.mx_password = 'Embe1mpls'
            cls.mx1_handle = NetconfConnection(host = cls.mx1_ip,username=cls.mx_user,password=cls.mx_password)
            cls.mx1_handle.connect()
        time.sleep(20)
    # end setUp

    @classmethod
    def tearDownClass(cls):
        '''
            It will remove topology where agent is connected to only one of the control node
        '''
        cls.set_bgp_peering(mode='enable')
        cls.set_gr_llgr(mode='disable')
        cls.set_xmpp_peering(compute_ip=cls.inputs.host_data[cls.host_list[0]]['host_control_ip'] , 
                                           mode='enable')
        cls.set_xmpp_peering(compute_ip=cls.inputs.host_data[cls.host_list[1]]['host_control_ip'] , 
                                           mode='enable')
        super(TestLlgrBase, cls).tearDownClass()
    # end cleanUp

    @classmethod
    def set_gr_llgr(self, **kwargs):
        '''
           Enable/Disable GR / LLGR configuration with gr/llgr timeout values as parameters
        '''
        gr_timeout = kwargs['gr']
        llgr_timeout = kwargs['llgr']
        gr_enable = True if kwargs['mode'] == 'enable' else False
        eor_timeout = '60'
        router_asn = '64512' if gr_enable == True else self.inputs.router_asn
        cntrl_fix = self.useFixture(CNFixture(
                                       connections=self.connections,
                                       router_name=self.inputs.ext_routers[0][0],
                                       router_ip=self.mx1_ip,
                                       router_type='mx',
                                       inputs=self.inputs))
        cntrl_fix.set_graceful_restart(gr_restart_time=gr_timeout,
                                     llgr_restart_time = llgr_timeout, 
                                     eor_timeout = eor_timeout, 
                                     gr_enable = gr_enable, 
                                     router_asn = router_asn,
                                     bgp_helper_enable = True, 
                                     xmpp_helper_enable = False)
        return True

    @classmethod
    def set_bgp_peering(self,**kwargs):
        ''' 
           Stop and start of BGP peer communication so that GR/LLGR timers are triggered
        '''
        mode = kwargs['mode']
        if mode == 'disable':
            cmd = 'iptables -A OUTPUT -p tcp --destination-port 179 -j DROP; \
                     iptables -A INPUT -p tcp --destination-port 179 -j DROP'
        else:
            cmd = 'iptables -D OUTPUT -p tcp --destination-port 179 -j DROP; \
                      iptables -D INPUT -p tcp --destination-port 179 -j DROP'
        self.logger.debug('%s bgp peering : %s' %(mode,cmd))
        self.inputs.run_cmd_on_server(self.inputs.bgp_ips[0],cmd)
        return True

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
            self.logger.error("Not able to find route flags for prefix %s:%s"%flags,rtbl['flags'])
            return False
        return True

    @classmethod
    def set_xmpp_peering(self,**kwargs):
        ''' 
            Enabling / Disabling XMPP peer communication 
        '''
        compute_ip = kwargs['compute_ip']
        mode = kwargs['mode']
        control_ips = []
        if mode == 'disable':
            ctrl_host = kwargs['ctrl_node']
            ctrl_ip = self.inputs.host_data[ctrl_host]['host_data_ip']
            ctrl_ip = ctrl_ip + ":"+'5269'
            self.configure_server_list(compute_ip, 'contrail-vrouter-agent',
                             'CONTROL-NODE', 'servers' , [ctrl_ip], container = "agent")
        else : 
            control_ips = [self.inputs.host_data[x]['host_data_ip']+":"+'5269' for x in self.inputs.bgp_ips]
            self.configure_server_list(compute_ip, 'contrail-vrouter-agent',
                           'CONTROL-NODE', 'servers' , control_ips , container = "agent")
        return True
   
    @classmethod
    def set_headless_mode(self,**kwargs):
        ''' 
           Enabling/Disabling headless mode in agent 
        '''
        mode = kwargs['mode']
        if mode == 'enable':
            cmd = '/usr/bin/openstack-config --set /etc/contrail/contrail-vrouter-agent.conf DEFAULT headless_mode true'
        else:
            cmd = '/usr/bin/openstack-config --del /etc/contrail/contrail-vrouter-agent.conf DEFAULT headless_mode'
        for host in self.host_list:
            self.logger.debug('enable headless mode %s : %s' %(host,cmd))
            self.inputs.run_cmd_on_server(host,cmd,container='agent')
        self.inputs.restart_service('contrail-vrouter-agent',self.host_list)
        return True 

    def verify_gr_bgp_flags(self,**kwargs):
        '''
           Check for Notification bit,GR timeout,Forwarding state are sent properly during BGP Open message.
        '''
        pcap_file = kwargs['pcap_file']
        host = kwargs['host']
        control_ip = self.inputs.host_data[host]['control-ip']
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
        cmd = 'tcpdump -r %s -vvv -n | grep Open  -A28 | grep %s -A28 | grep \'Restart Flags\' -A5 | grep 0x0000'%(pcap_file,control_ip)
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
        control_ip = self.inputs.host_data[host]['control-ip']
        # Unknown (71), length: 28
        # no decoder for Capability 71
        # 0x0000:  0001 8080 0000 3c00 1946 8000 003c 0001
        # 8080 forwarding state is set
        # c0 is 65 sec of llgr time
        cmd = 'tcpdump -r %s -vvv -n | grep Open  -A28 | grep %s -A28 | grep \'Unknown (71)\' -A3 | grep 0x0000'%(pcap_file,control_ip)
        res = self.inputs.run_cmd_on_server(host,cmd)
        self.logger.debug('results %s' %(res))
        res = res.split(':')
        flags = res[1].split(' ')
        if not flags:
            self.logger.error("not able to get flags %s"%flags)
            return False
        flags = [x for x in flags if x != '']
        self.logger.info("flags set properly %s"%flags[0])
        if flags[3] != '3c00' and flags[1] != '8080':
            self.logger.error("flags not set properly %s"%flags[0])
            return False
        return True

    @classmethod
    def configure_server_list(self, client_ip, client_process,
                               section, option, server_list, container):
        '''
        This function configures the .conf file with new server_list
        and then send a sighup to the client so that configuration
        change is effective.
        '''
        client_conf_file = client_process + ".conf"
        server_string =  " ".join(server_list)
        cmd_set = "openstack-config --set /etc/contrail/" + client_conf_file
        cmd = cmd_set + " " + section + " " + option + ' "%s"' % server_string
        self.inputs.run_cmd_on_server(client_ip, cmd,
                            self.inputs.host_data[client_ip]['username']\
                            , self.inputs.host_data[client_ip]['password'],
                            container = container)
        if "nodemgr" in client_process:
            nodetype = client_process.rstrip("-nodemgr")
            client_process = "contrail-nodemgr --nodetype=%s" % nodetype
        else:
            client_process = "/usr/bin/" + client_process
        pid_cmd = 'pgrep -f -o "%s"' % client_process
        pid = int(self.inputs.run_cmd_on_server(client_ip, pid_cmd,
                            self.inputs.host_data[client_ip]['username']\
                            , self.inputs.host_data[client_ip]['password'],
                            container = container))
        sighup_cmd = "kill -SIGHUP %d " % pid
        self.inputs.run_cmd_on_server(client_ip, sighup_cmd,
                            self.inputs.host_data[client_ip]['username']\
                            , self.inputs.host_data[client_ip]['password'],
                            container = container)

    def is_test_applicable(self):
        # check for atleast 2 compute nodes
        if len(self.host_list) < 2 :
            return (False ,"compute nodes are not sufficient")
        # check for atleast 2 control nodes
        if len(self.inputs.bgp_ips) < 2 :
            return (False, "compute nodes are not sufficient")
        # check for 1 mx 
        if len(self.inputs.ext_routers) < 1:
            self.logger.error("MX routers are not sufficient : %s"%len(self.inputs.ext_routers))
            return (False ,"MX routers are not sufficient")
        return (True,None)


