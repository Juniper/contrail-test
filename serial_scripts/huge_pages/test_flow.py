from __future__ import absolute_import, unicode_literals
from builtins import str
from builtins import range
import traffic_tests
from vn_test import *
from vm_test import *
from floating_ip import *
from policy_test import *
from user_test import UserFixture
from multiple_vn_vm_test import *
from tcutils.wrappers import preposttest_wrapper
import inspect
import time
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
from tcutils.util import get_subnet_broadcast
from tcutils.util import skip_because
import test
from common.vrouter.base import BaseVrouterTest

class TestFlow(BaseVrouterTest):

    @classmethod
    def setUpClass(cls):
        super(TestFlow, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestFlow, cls).tearDownClass()

    def service_agent_container(self, compute_ip, action):
        compute_fix = self.compute_fixtures_dict[compute_ip]
        container_name = compute_fix.inputs.get_container_name(compute_fix.ip, 'agent')
        cmd = "docker %s %s" %(action, container_name)
        self.logger.info("Executing cmd %s" %(cmd))
        compute_fix.execute_cmd(cmd, None)

    def service_kernel_vrouter(self, compute_ip, action):
        compute_fix = self.compute_fixtures_dict[compute_ip]
        if (action == "start"):
            cmd = "ifup vhost0"
        else:
            cmd = "ifdown vhost0"
        self.logger.info("Executing cmd %s" %(cmd))
        compute_fix.execute_cmd(cmd, None)

    def service_vrouter(self, compute_ip, action):
        if (action == "start"):
            self.service_kernel_vrouter(compute_ip, "start")
            self.service_agent_container(compute_ip, "start")
        else:
            self.service_agent_container(compute_ip, "stop")
            self.service_kernel_vrouter(compute_ip, "stop")

    def is_dpdk_compute(self, compute_ip):
        cmd = "docker ps -a | grep dpdk"
        compute_fix = self.compute_fixtures_dict[compute_ip]
        ret = compute_fix.execute_cmd(cmd, None)
        if (ret != ""):
            return True
        else:
            return False

    def is_1GB_hugepage_configured(self, compute_ip):
        path = "/sys/kernel/mm/hugepages/hugepages-1048576kB/nr_hugepages"
        cmd = "cat " + path
        compute_fix = self.compute_fixtures_dict[compute_ip]
        ret = compute_fix.execute_cmd(cmd, None)
        print "Ret " + ret
        if (re.search("No such", ret)):
            self.logger.info("1GB hugepages is not configured")
            return False
        else:
            if (re.search("0", ret)):
                self.logger.info("1GB hugepages is not configured")
                return False
        self.logger.info("1GB hugepages is configured")
        return True

    def is_2MB_hugepage_configured(self, compute_ip):
        path = "/sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages"
        cmd = "cat " + path
        compute_fix = self.compute_fixtures_dict[compute_ip]
        ret = compute_fix.execute_cmd(cmd, None)
        print "Ret " + ret
        if (re.search("No such", ret)):
            self.logger.info("2MB hugepages is not configured")
            return False
        else:
            if (re.search("0", ret)):
                self.logger.info("2MB hugepages is not configured")
                return False
        self.logger.info("2MB hugepages is configured")
        return True

    def get_hugepage_fs_path(self, compute_ip):
        cmd = "cat /proc/mounts | grep hugetlbfs | cut -d \" \" -f 2"
        compute_fix = self.compute_fixtures_dict[compute_ip]
        return compute_fix.execute_cmd(cmd, None)

    def verify_vrouter_hugepage_files(self, compute_ip):
        path = self.get_hugepage_fs_path(compute_ip)
        flow_path = path + "/flow"
        bridge_path = path + "/bridge"
        compute_fix = self.compute_fixtures_dict[compute_ip]
        cmd = "ls -s " + flow_path
        ret = compute_fix.execute_cmd(cmd, None)
        self.logger.info("Hugepage file for flow:")
        self.logger.info(ret)
        if (re.search("No such", ret)):
            return False
        else:
            cmd = "ls -s " + bridge_path
            ret = compute_fix.execute_cmd(cmd, None)
            self.logger.info("Hugepage file for bridge:")
            self.logger.info(ret)
            if (re.search("No such", ret)):
                return False
        self.logger.info("Hugepage files verified")
        return True

    def config_2MB_hugepage_agent(self, compute_ip, enable):
        compute_fix = self.compute_fixtures_dict[compute_ip]
        container_name = compute_fix.inputs.get_container_name(compute_fix.ip, 'agent')
        huge_page_path = self.get_hugepage_fs_path(compute_ip)
        if (enable == True):
            huge_page_knob_str = "huge_page_2M=" + huge_page_path + "/bridge " + huge_page_path + "/flow"
        else:
            huge_page_knob_str = "huge_page_2M="
        compute_fix.inputs.add_knob_to_container(compute_ip, container_name,
                                        "RESTART", huge_page_knob_str)

    def config_1GB_hugepage_agent(self, compute_ip, enable):
        compute_fix = self.compute_fixtures_dict[compute_ip]
        container_name = compute_fix.inputs.get_container_name(compute_fix.ip, 'agent')
        huge_page_path = self.get_hugepage_fs_path(compute_ip)
        if (enable == True):
            huge_page_knob_str = "huge_page_1G=" + huge_page_path + "/bridge " + huge_page_path+ "/flow"
        else:
            huge_page_knob_str = "huge_page_1G="
        compute_fix.inputs.add_knob_to_container(compute_ip, container_name,
                                        "RESTART", huge_page_knob_str)

    def is_hugepage_configured(self, compute_ip, hugepage_size):
        if (hugepage_size == "2MB"):
            return self.is_2MB_hugepage_configured(compute_ip)
        else:
            return self.is_1GB_hugepage_configured(compute_ip)

    def config_agent_hugepage(self, compute_ip, hugepage_size):
        # restart agent with hugepage_size config
        if (hugepage_size == "2MB"):
            self.config_2MB_hugepage_agent(compute_ip, True)
        else:
            self.config_1GB_hugepage_agent(compute_ip, True)

    def skip_test_case(self, Testname, compute_ip):
        self.logger.warn("Hugepage not configured or not a kernel compute")
        self.logger.warn("Skipping test case " + Testname + " on compute " + compute_ip)

    def test_traffic(self, compute_ip):
        compute_fix = self.compute_fixtures_dict[compute_ip]
        # create a vn
        vn_fixture = self.create_vns()
        self.verify_vns(vn_fixture)
        # create 2 vms
        vm_fixture = self.create_vms(vn_fixture[0], 2, "ubuntu-traffic")
        self.verify_vms(vm_fixture)
        # start traffic type
        # Use 1st vm as src vm and 2nd one as dst vm
        src_vm_ip = vm_fixture[0].get_vm_ip_from_vm()
        if (src_vm_ip == None):
            self.logger.error("Unable to get src vm ip")
            return False
        dst_vm_ip = vm_fixture[1].get_vm_ip_from_vm()
        if (dst_vm_ip == None):
            self.logger.error("Unable to get dst vm ip")
            return False
        # send udp traffic
        udp_sport = 45000
        udp_dport = 45001
        self.send_traffic_verify_flow_dst_compute(vm_fixture[0],
                                  vm_fixture[1], "udp", udp_sport, udp_dport, 1, 1)
        # send tcp traffic
        tcp_sport = 50000
        tcp_dport = 50001
        self.send_traffic_verify_flow_dst_compute(vm_fixture[0],
                                  vm_fixture[1], "tcp", tcp_sport, tcp_dport, 1, 0)
        # send icmp traffic
        vm_fixture[0].ping_with_certainty(dst_vm_ip)
        # let flows age out
        time.sleep(180)
        # check the flow count
        dst_vrf = compute_fix.get_vrf_id(vm_fixture[1].vn_fq_names[0])
        src_vrf = compute_fix.get_vrf_id(vm_fixture[0].vn_fq_names[0]) or dst_vrf
        # udp flow count should be 0
        self.verify_flow_on_compute(compute_fix, src_vm_ip, dst_vm_ip,
                                    src_vrf, dst_vrf, udp_sport, udp_dport, "udp",
                                    0, 0)
        # tcp flow count should be 0
        #self.verify_flow_on_compute(compute_fix, src_vm_ip, dst_vm_ip,
        #                            src_vrf, dst_vrf, tcp_sport, tcp_dport, "tcp",
        #                            0, 0)
        # icmp flow count should be 0
        self.verify_flow_on_compute(compute_fix, src_vm_ip, dst_vm_ip,
                                    src_vrf, dst_vrf, None, 0, "icmp",
                                    0, 0)
        # delete vms
        self.delete_vms(vm_fixture)

    def test_flow_traffic(self, hugepage_size):
        compute_ip = self.compute_ips[0]
        # check if required hugepage_size is configured on compute
        if (self.is_dpdk_compute(compute_ip) or
            (self.is_hugepage_configured(compute_ip, hugepage_size) == False)):
            self.skip_test_case("test_flow_traffic", compute_ip)
            return True
        # config agent huge page
        self.config_agent_hugepage(compute_ip, hugepage_size)
        # verify hugepage files are really created
        assert self.verify_vrouter_hugepage_files(compute_ip)
        self.test_traffic(compute_ip)
        return True

    def test_flow_traffic_vrouter_restart(self, hugepage_size):
        compute_ip = self.compute_ips[0]
        # check if required hugepage_size is configured on compute
        if (self.is_dpdk_compute(compute_ip) or
            (self.is_hugepage_configured(compute_ip, hugepage_size) == False)):
            self.skip_test_case("test_flow_traffic_vrouter_restart", compute_ip)
            return True
        # config agent huge page
        self.config_agent_hugepage(compute_ip, hugepage_size)
        # verify hugepage files are really created
        assert self.verify_vrouter_hugepage_files(compute_ip)
        restart_count = 10
        i = 1
        while (restart_count > 0):
            self.service_vrouter(compute_ip, "stop")
            self.service_vrouter(compute_ip, "start")
            restart_count = restart_count - 1
            self.logger.info("Restarted vrouter " + str(i) + " time");
            i = i + 1
        time.sleep(10)
        self.test_traffic(compute_ip)

    def test_flow_traffic_vrouter_agent_restart(self, hugepage_size):
        compute_ip = self.compute_ips[0]
        # check if required hugepage_size is configured on compute
        if (self.is_dpdk_compute(compute_ip) or
            (self.is_hugepage_configured(compute_ip, hugepage_size) == False)):
            self.skip_test_case("test_flow_traffic_vrouter_restart", compute_ip)
            return True
        # config agent huge page
        self.config_agent_hugepage(compute_ip, hugepage_size)
        # verify hugepage files are really created
        assert self.verify_vrouter_hugepage_files(compute_ip)
        # restart agent container alone
        self.service_agent_container(compute_ip, "stop")
        self.service_agent_container(compute_ip, "start")
        self.logger.info("Restarted agent")
        self.test_traffic(compute_ip)

    @preposttest_wrapper
    def test_flow_traffic_2MB(self):
        return self.test_flow_traffic("2MB")

    @preposttest_wrapper
    def test_flow_traffic_vrouter_restart_2MB(self):
        return self.test_flow_traffic_vrouter_restart("2MB")

    @preposttest_wrapper
    def test_flow_traffic_vrouter_agent_restart_2MB(self):
        return self.test_flow_traffic_vrouter_agent_restart("2MB")

    @preposttest_wrapper
    def test_flow_traffic_1GB(self):
        return self.test_flow_traffic("1GB")

    @preposttest_wrapper
    def test_flow_traffic_vrouter_restart_1GB(self):
        return self.test_flow_traffic_vrouter_restart("1GB")

    @preposttest_wrapper
    def test_flow_traffic_vrouter_agent_restart_1GB(self):
        return self.test_flow_traffic_vrouter_agent_restart("1GB")

    @preposttest_wrapper
    def test_flow_traffic_sanity_no_hugepages(self):
        compute_ip = self.compute_ips[0]
        if (self.is_dpdk_compute(compute_ip)):
            self.logger.info("Compute ip " + compute_ip + " is dpdk compute")
        else:
            self.logger.info("Compute ip " + compute_ip + " is kernel compute")
        #unset any hugepage config from agent
        self.config_2MB_hugepage_agent(compute_ip, False)
        self.config_1GB_hugepage_agent(compute_ip, False)
        self.service_vrouter(compute_ip, "stop")
        self.service_vrouter(compute_ip, "start")
        # wait of xmpp to come up
        time.sleep(10)
        self.test_traffic(compute_ip)

