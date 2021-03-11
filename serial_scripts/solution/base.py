import test_v1
import os
import re
from common import isolated_creds


class BaseSolutionsTest(test_v1.BaseTestCase_v1):

    @classmethod
    def setUpClass(cls):
        super(BaseSolutionsTest, cls).setUpClass()
        cls.quantum_h= cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib= cls.connections.vnc_lib
        cls.agent_inspect= cls.connections.agent_inspect
        cls.cn_inspect= cls.connections.cn_inspect
        cls.api_s_inspect = cls.connections.api_server_inspect
        cls.ops_inspect = cls.connections.ops_inspect
        cls.analytics_obj=cls.connections.analytics_obj
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BaseSolutionsTest, cls).tearDownClass()
    # end tearDownClass

    def verify_ospf_session_state(self):
        ''' Verification routine to validate OSPF session state.
        '''
        ret = True
        vsfo_fix = self.vsfo_fix
        vrp_31 = self.vrp_31
        vrp_32 = self.vrp_32

        # Validate OSPF session

        self.logger.info("Validate OSPF session.")

        cmd = "sshpass -p contrail123 ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -J \"%s@%s\"  -o GlobalKnownHostsFile=/dev/null root@%s  \"cli\" \"show ospf neighbor\" | grep -c Full" %(self.inputs.host_data[vrp_31.vm_node_ip]['username'] ,vrp_31.vm_node_ip,vrp_31.local_ip)
        op = os.popen(cmd).read()
        vrp_31_ospf = int(re.match(r'\d',op).group())
        EXP_SESS=((self.NB_VSFO_CP_NODES + self.NB_VSFO_UP_NODES + 1))
        if EXP_SESS == vrp_31_ospf:
            self.logger.info("All ospf sessions are UP")
        else:
            self.logger.error("All ospf sessions are not UP")
            ret = False

        return ret

    def verify_bgp_session_state(self):
        ''' Test routine to validate BGP/BFD session state.
        '''
        ret = True

        self.logger.info("Validate BGP/BFD session.")

        vsfo_fix = self.vsfo_fix
        vrp_31 = self.vrp_31
        vrp_32 = self.vrp_32

        # Validate BGP & BFD sessions on vsfo CP nodes

        for i in range(1,self.NB_VSFO_CP_NODES+1):

            self.logger.info("BGP and BFD sessions for %s :-" %vsfo_fix[i].vm_name)
            cmd = "sshpass -p contrail123 ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -J \"%s@%s\"  -o GlobalKnownHostsFile=/dev/null root@%s  \"cli\" \"show bgp summary\" | grep -c Establ" %(self.inputs.host_data[vsfo_fix[i].vm_node_ip]['username'] ,vsfo_fix[i].vm_node_ip,vsfo_fix[i].local_ip)
            op = os.popen(cmd).read()
            vsfo_cp_session = int(re.match(r'\d+',op).group())

            cmd = "sshpass -p contrail123 ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -J \"%s@%s\"  -o GlobalKnownHostsFile=/dev/null root@%s  \"cli\" \"show bfd session\" | grep ge-0/0 | grep -c Up" %(self.inputs.host_data[vsfo_fix[i].vm_node_ip]['username'] ,vsfo_fix[i].vm_node_ip,vsfo_fix[i].local_ip)
            op = os.popen(cmd).read()
            vsfo_cp_bfd_session = int(re.match(r'\d+',op).group())


            EXP_SESS=((2 * (self.NB_VSFO_CP_SIGIF + self.NB_APN_RADIUS + 1) * self.NB_VSFO_CP_EXT_NIC ))

            if EXP_SESS == vsfo_cp_session:
                self.logger.info("All bgp sessions are UP")
            else:
                self.logger.error("All bgp sessions are not UP")
                ret = False

            if EXP_SESS/2 == vsfo_cp_bfd_session:
                self.logger.info("All bfd sessions are UP")
            else:
                self.logger.error("All bfd sessions are not UP")
                ret = False
            i = i + 1
            self.logger.info("*******************************************")

        # Validate BGP & BFD sessions on vsfo UP nodes

        for i in range(self.NB_VSFO_CP_NODES+1 ,self.NB_VSFO_CP_NODES + self.NB_VSFO_UP_NODES+1):

            self.logger.info("BGP and BFD sessions for %s :-" %vsfo_fix[i].vm_name)
            cmd = "sshpass -p contrail123 ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -J \"%s@%s\"  -o GlobalKnownHostsFile=/dev/null root@%s  \"cli\" \"show bgp summary\" | grep -c Establ" %(self.inputs.host_data[vsfo_fix[i].vm_node_ip]['username'] ,vsfo_fix[i].vm_node_ip,vsfo_fix[i].local_ip)
            op = os.popen(cmd).read()
            vsfo_up_session = int(re.match(r'\d+',op).group())

            cmd = "sshpass -p contrail123 ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -J \"%s@%s\"  -o GlobalKnownHostsFile=/dev/null root@%s  \"cli\" \"show bfd session\" | grep ge-0/0 | grep -c Up" %(self.inputs.host_data[vsfo_fix[i].vm_node_ip]['username'] ,vsfo_fix[i].vm_node_ip,vsfo_fix[i].local_ip)
            op = os.popen(cmd).read()
            vsfo_up_bfd_session = int(re.match(r'\d+',op).group())

            EXP_SESS=(( 2*((self.NB_VSFO_UP_CNNIC * self.NB_VSFO_UP_CNIF) + (self.NB_VSFO_UP_EXT_NIC - self.NB_VSFO_UP_CNNIC) * self.NB_APN) ))

            if EXP_SESS == vsfo_up_session:
                self.logger.info("All bgp sessions are UP")
            else:
                self.logger.error("All bgp sessions are not UP")
                ret = False

            if EXP_SESS/2 == vsfo_up_bfd_session:
                self.logger.info("All bfd sessions are UP")
            else:
                self.logger.error("All bfd sessions are not UP")
                ret = False
            i = i+1
            self.logger.info("*******************************************")

        return ret

    def get_route_count(self,output,vsfo_fix,EXP_ADV,EXP_RCV):

        ''' Return no of sessions which have properly advertised/received routes.
        '''

        output = output.split('\n')
        count = 0

        for ele in output:
            mo = re.search(r'\d+\.\d+\.\d+\.\d+',ele)
            if mo:
                ele = ele.split(";")
                peer = ele[0]
                vpn = ele[1]

                cmd = "sshpass -p contrail123 ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -J \"%s@%s\"  -o GlobalKnownHostsFile=/dev/null root@%s  \"cli\" \"show route advertising-protocol bgp %s\" | grep -c \"/\" " %(self.inputs.host_data[vsfo_fix.vm_node_ip]['username'] ,vsfo_fix.vm_node_ip,vsfo_fix.local_ip,peer)
                op = os.popen(cmd).read()
                routes_adv = int(re.match(r'\d+',op).group())

                cmd = "sshpass -p contrail123 ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -J \"%s@%s\"  -o GlobalKnownHostsFile=/dev/null root@%s  \"cli\" \"show route receive-protocol bgp %s table %s.inet.0\" | grep -c \"/\" " %(self.inputs.host_data[vsfo_fix.vm_node_ip]['username'] ,vsfo_fix.vm_node_ip,vsfo_fix.local_ip,peer,vpn)
                op = os.popen(cmd).read()

                routes_rec = int(re.match(r'\d+',op).group())

                self.logger.info("EXP_RCV %s routes_rec %s."%(EXP_RCV ,routes_rec))
                self.logger.info("EXP_ADV %s routes_adv %s."%(EXP_ADV,routes_adv))
                if ((EXP_RCV <= routes_rec) & (EXP_ADV <= routes_adv)):
                    count = count + 1
                    self.logger.info("Routes received and send are OK for %s."%(peer))
                else:
                    self.logger.info("Routes received and send are less than expected for %s."%(peer))
        return count

    def verify_route_count(self):
        ''' Verify routes advertised/received per BGP session.
        '''
        ret = True

        vsfo_fix = self.vsfo_fix

        # Validate routes on VSFO- CP nodes.

        for i in range(1,self.NB_VSFO_CP_NODES+1):

            # cp - radius session
            EXP_ADV = 1
            EXP_RCV = 1

            self.logger.info("Validate routes for RADIUS session.")

            cmd = "sshpass -p contrail123 ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -J \"%s@%s\"  -o GlobalKnownHostsFile=/dev/null root@%s  \"cli\" \"show bgp summary\" | grep \"Establ\|radius_\|sig_\"| awk '{ print $1 }'| sed 'N;s/\\n/ /' |  sed 's/.inet.0://g' | sed 's/ /;/g' | grep radius_" %(self.inputs.host_data[vsfo_fix[i].vm_node_ip]['username'] ,vsfo_fix[i].vm_node_ip,vsfo_fix[i].local_ip)

            output = os.popen(cmd).read()
            good = self.get_route_count(output,vsfo_fix[i],EXP_ADV,EXP_RCV)

            EXP_GOOD_SESSIONS=(( 2 * self.NB_VSFO_CP_EXT_NIC * (self.NB_APN_RADIUS + 1) ))
            if EXP_GOOD_SESSIONS == good:
                self.logger.info("Routes received and send are OK for RADIUS sessions.")
            else:
                ret = False
                self.logger.error("Routes received and send are not proper for RADIUS sessions.Expected: %s Actual: %s."%(EXP_GOOD_SESSIONS,good))


            self.logger.info("Validate routes for Sig session.")

            cmd = "sshpass -p contrail123 ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -J \"%s@%s\"  -o GlobalKnownHostsFile=/dev/null root@%s  \"cli\" \"show bgp summary\" | grep \"Establ\|radius_\|sig_\"| awk '{ print $1 }'| sed 'N;s/\\n/ /' |  sed 's/.inet.0://g' | sed 's/ /;/g' | grep sig_" %(self.inputs.host_data[vsfo_fix[i].vm_node_ip]['username'] ,vsfo_fix[i].vm_node_ip,vsfo_fix[i].local_ip)

            output = os.popen(cmd).read()
            good = self.get_route_count(output,vsfo_fix[i],EXP_ADV,EXP_RCV)

            EXP_GOOD_SESSIONS=(( 2 * self.NB_VSFO_CP_EXT_NIC * self.NB_VSFO_CP_SIGIF ))

            if EXP_GOOD_SESSIONS == good:
                self.logger.info("Routes received and send are OK for Sig sessions.")
            else:
                ret = False
                self.logger.error("Routes received and send are not proper for Sig sessions.Expected: %s Actual: %s."%(EXP_GOOD_SESSIONS,good))
            i = i + 1

        for i in range(self.NB_VSFO_CP_NODES+1 ,self.NB_VSFO_CP_NODES + self.NB_VSFO_UP_NODES+1):


            EXP_ADV=((1 + self.NB_BGP_PREFIXES_PER_APN))
            EXP_RCV = 1

            self.logger.info("Validate routes for APN session.")

            cmd = "sshpass -p contrail123 ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -J \"%s@%s\"  -o GlobalKnownHostsFile=/dev/null root@%s  \"cli\" \"show bgp summary\" | grep \"Establ\|cn_.*_vpn\|apn_.*_vpn\"| awk '{ print $1 }'| sed 'N;s/\\n/ /' |  sed 's/.inet.0://g' | sed 's/ /;/g' | grep apn_" %(self.inputs.host_data[vsfo_fix[i].vm_node_ip]['username'] ,vsfo_fix[i].vm_node_ip,vsfo_fix[i].local_ip)

            output = os.popen(cmd).read()
            good = self.get_route_count(output,vsfo_fix[i],EXP_ADV,EXP_RCV)
            EXP_GOOD_SESSIONS=(( 2 * (self.NB_VSFO_UP_EXT_NIC - self.NB_VSFO_UP_CNNIC) * self.NB_APN ))
            if EXP_GOOD_SESSIONS == good:
                self.logger.info("Routes received and send are OK for APN sessions.")
            else:
                ret = False
                self.logger.error("Routes received and send are not proper for APN sessions.Expected: %s Actual: %s."%(EXP_GOOD_SESSIONS,good))

            EXP_ADV=1
            EXP_RCV = 1

            self.logger.info("Validate routes for CN session.")

            cmd = "sshpass -p contrail123 ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -J \"%s@%s\"  -o GlobalKnownHostsFile=/dev/null root@%s  \"cli\" \"show bgp summary\" | grep \"Establ\|cn_.*_vpn\|apn_.*_vpn\"| awk '{ print $1 }'| sed 'N;s/\\n/ /' |  sed 's/.inet.0://g' | sed 's/ /;/g' | grep cn_" %(self.inputs.host_data[vsfo_fix[i].vm_node_ip]['username'] ,vsfo_fix[i].vm_node_ip,vsfo_fix[i].local_ip)

            output = os.popen(cmd).read()
            good = self.get_route_count(output,vsfo_fix[i],EXP_ADV,EXP_RCV)

            EXP_GOOD_SESSIONS=(( 2 * self.NB_VSFO_UP_CNNIC * self.NB_VSFO_UP_CNIF ))
            if EXP_GOOD_SESSIONS == good:
                self.logger.info("Routes received and send are OK for CN sessions.")
            else:
                ret = False
                self.logger.error("Routes received and send are not proper for CN sessions.Expected: %s Actual: %s."%(EXP_GOOD_SESSIONS,good))


            i = i + 1

        return ret

    def verify_bgpaas_session_ctrlnode(self):
        ''' Verify bgpaas session state on control node.
        '''
        ret = True

        vsfo_fix = self.vsfo_fix
        self.logger.info("Validate bgpas sessions on control node.")

        EXP_S = (self.NB_VSFO_UP_NODES * ((((self.NB_VSFO_CP_SIGIF + \
                 self.NB_APN_RADIUS + 1) * self.NB_VSFO_CP_EXT_NIC )
          )  + (( ((self.NB_VSFO_UP_CNNIC * self.NB_VSFO_UP_CNIF) + (
          self.NB_VSFO_UP_EXT_NIC - self.NB_VSFO_UP_CNNIC) * self.NB_APN) ))))

        bgpasUpSession=0
        for user_planes in range(self.NB_VSFO_CP_NODES+1,\
                self.NB_VSFO_CP_NODES+self.NB_VSFO_UP_NODES+1):
            ctrl_node = vsfo_fix[user_planes].get_control_nodes()[0]
            cn_bgp_entry = self.connections.get_control_node_inspect_handle(
                ctrl_node).get_cn_bgp_neigh_entry(encoding='BGP')
            bgpasUpSessiontemp = 0
            for entry in cn_bgp_entry:
                if entry['router_type'] == 'bgpaas-client' and entry['state'] \
                                               == 'Established':
                    bgpasUpSessiontemp = bgpasUpSessiontemp + 1
            bgpasUpSession = max(bgpasUpSession, bgpasUpSessiontemp)

        if EXP_S <= bgpasUpSession:
            self.logger.info("BGPaaS sessions are UP as expected. \
                Expected  %s Actual %s."%(EXP_S,bgpasUpSession))
        else:
            self.logger.error("BGPaaS sessions are not UP as expected. \
                Expected  %s Actual %s."%(EXP_S,bgpasUpSession))
            ret = False
        return ret
 
    def verify_bgpaas_routes_ctrlnode(self):
        ''' Verify bgpaas session state on control node.
        '''
        self.logger.info("Validate bgpas routes on control node.")

        ret = True
        vsfo_fix = self.vsfo_fix
        vsfoupid = int(self.NB_VSFO_CP_NODES+1)

        ctrl_node = vsfo_fix[vsfoupid].get_control_nodes()[0]
        EXP_R = self.NB_BGP_PREFIXES_PER_APN + 2
        if self.NB_VSFO_UP_EXT_NIC == 2:
            ext_nic_range_s=2
            ext_nic_range_e=3
        else:
            ext_nic_range_s=3
            ext_nic_range_e=5
        for i in range(self.NB_VSFO_CP_NODES+1 ,self.NB_VSFO_CP_NODES + self.NB_VSFO_UP_NODES+1):
            vlan = 3000
            for nic in range(ext_nic_range_s, ext_nic_range_e):
                for each_vlan in range(vlan, vlan + self.NB_APN):
                    vrf = "EPG-B2B-VSFO-%s_EXT-%s_TAGGED-%s" %(i,nic,each_vlan)
                    proj =  self.project.project_fq_name
                    rt = "%s:%s:%s:%s.inet.0" %(proj[0],proj[1],vrf,vrf)
                    op = self.connections.get_control_node_inspect_handle(ctrl_node).get_cn_route_table(rt_name=rt)
                    routes=[]
                    if op:
                        routes = op['routes']
                    count = 0
                    for ele in routes:
                        count = count +1

                    if EXP_R <= count:
                        self.logger.info("Routes are present as expected in %s. \
                            Expected  %s Actual %s."%(rt,EXP_R,count))
                    else:
                        self.logger.error("Routes are not present as expected in %s. \
                            Expected  %s Actual %s."%(rt,EXP_R,count))
                        ret = False
        return ret
 
#end BaseSolutionsTest class

