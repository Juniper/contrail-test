import os
import fixtures
import testtools

from vn_test import VNFixture
from vm_test import VMFixture
from connections import ContrailConnections
from tcutils.commands import ssh, execute_cmd
from policy_test import PolicyFixture
from policy.config import AttachPolicyFixture
from tcutils.commands import ssh, execute_cmd


class ConfigPerformance():

    def config_vn(self, vn_name, vn_net):
        vn_fixture = self.useFixture(VNFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_name=vn_name, inputs=self.inputs, subnets=vn_net))
        assert vn_fixture.verify_on_setup()
        return vn_fixture

    def config_vm(self, vn_fix, vm_name, node_name=None, image_name='ubuntu-netperf'):
        vm_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_obj=vn_fix.obj, vm_name=vm_name, node_name=node_name, image_name=image_name, flavor='contrail_flavor_large'))
        return vm_fixture

    def config_policy(self, policy_name, rules):
        """Configures policy."""
        # create policy
        policy_fix = self.useFixture(PolicyFixture(
            policy_name=policy_name, rules_list=rules,
            inputs=self.inputs, connections=self.connections))
        return policy_fix

    def attach_policy_to_vn(self, policy_fix, vn_fix, policy_type=None):
        policy_attach_fix = self.useFixture(AttachPolicyFixture(
            self.inputs, self.connections, vn_fix, policy_fix, policy_type))
        return policy_attach_fix

    def set_cpu_performance(self, hosts):
        sessions = {}
        cmd = 'for f in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor ; do echo performance > $f; cat $f; done'
        for i in range(0, 2):
            session = ssh(hosts[i]['host_ip'], hosts[i]
                          ['username'], hosts[i]['password'])
            execute_cmd(session, cmd, self.logger)
        return
