"""Policy config utilities."""

import random

import fixtures

from policy_test import PolicyFixture

from vnc_api.gen.resource_xsd import TimerType, SequenceType,\
    VirtualNetworkPolicyType
from vnc_api.vnc_api import NetworkPolicy


class AttachPolicyFixture(fixtures.Fixture):

    """Policy attach fixture to attach policy to Virtuak Networks."""

    def __init__(self, inputs, connections, vn_fixture, policy_fixture, policy_type=None):
        self.inputs = inputs
        self.logger = self.inputs.logger
        self.orch = connections.orch
        self.vnc_lib = connections.vnc_lib
        self.vn_fixture = vn_fixture
        self.policy_fixture = policy_fixture
        self.vn_obj = self.vnc_lib.virtual_network_read(
            fq_name_str=self.vn_fixture.vn_fq_name)
        self.policy_obj = self.vnc_lib.network_policy_read(
            fq_name=self.policy_fixture.policy_fq_name)
        seq = random.randint(1, 655535)
        kwargs = {'sequence': SequenceType(seq, 0)}
        if policy_type == 'dynamic':
            kwargs.update({'timer': TimerType()})
        self.policy_type = VirtualNetworkPolicyType(**kwargs)

    def setUp(self):
        self.logger.info("Attaching policy %s to vn %s",
                         self.policy_fixture.policy_name, self.vn_fixture.vn_name)
        super(AttachPolicyFixture, self).setUp()
        self.vn_obj.add_network_policy(self.policy_obj, self.policy_type)
        self.vnc_lib.virtual_network_update(self.vn_obj)
        # Required for verification by VNFixture in vn_test.py
        policy = self.orch.get_policy(self.policy_fixture.policy_fq_name)
        policy_name_objs = dict((policy_obj['policy']['name'], policy_obj)
                                for policy_obj in self.vn_fixture.policy_objs)
        if isinstance(policy, NetworkPolicy):
            policy_name = policy.fq_name[-1]
        else:
            policy_name = policy['policy']['name']
        if policy_name not in policy_name_objs.keys():
            self.vn_fixture.policy_objs.append(policy)

    def cleanUp(self):
        self.logger.info("Dettaching policy %s from vn %s",
                         self.policy_fixture.policy_name, self.vn_fixture.vn_name)
        super(AttachPolicyFixture, self).cleanUp()
        self.vn_obj.del_network_policy(self.policy_obj)
        self.vnc_lib.virtual_network_update(self.vn_obj)
        # Required for verification by VNFixture in vn_test.py
        policy = self.orch.get_policy(self.policy_fixture.policy_fq_name)
        if isinstance(policy, NetworkPolicy):
            policy_name = policy.fq_name[-1]
            policy_name_objs = dict((policy_obj.fq_name[-1], policy_obj)
                                for policy_obj in self.vn_fixture.policy_objs)
        else:
            policy_name = policy['policy']['name']
            policy_name_objs = dict((policy_obj['policy']['name'], policy_obj)
                                for policy_obj in self.vn_fixture.policy_objs)
        if policy_name in policy_name_objs.keys():
            self.vn_fixture.policy_objs.remove(policy_name_objs[policy_name])


class ConfigPolicy():

    def remove_from_cleanups(self, fix):
        for cleanup in self._cleanups:
            if fix.cleanUp in cleanup:
                self._cleanups.remove(cleanup)
                break

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

    def detach_policy(self, vn_policy_fix):
        self.logger.debug("Removing policy from '%s'",
                          vn_policy_fix.vn_fixture.vn_name)
        vn_policy_fix.cleanUp()
        self.remove_from_cleanups(vn_policy_fix)

    def unconfig_policy(self, policy_fix):
        """Un Configures policy."""
        self.logger.debug("Delete policy '%s'", policy_fix.policy_name)
        policy_fix.cleanUp()
        self.remove_from_cleanups(policy_fix)
