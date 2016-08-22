#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from rally import consts
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.neutron import utils as neutron_utils
from rally.plugins.openstack.scenarios.nova import utils as nova_utils
from rally.task import validation
from rally.task import types
from rally.task import atomic
from rally.common import log as logging
from rally import exceptions
from rally.task import scenario
import random
import os
import re

LOG = logging.getLogger(__name__)

class RandomScenarios(neutron_utils.NeutronScenario, nova_utils.NovaScenario):
    """
    Set of complex scenarios


    Note: methods in this scenarios add some objects which will be prepended
    with a string 'rs_'. This is to avoid any conflict of any existing objects.
    """
    @validation.required_services(consts.Service.NOVA, consts.Service.NEUTRON)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["neutron"]})
    def random_scenarios(self, scenario_config=None):
        if not scenario_config:
            raise exceptions.InvalidConfigException(
                "scenario_config must be configured"
            )

        for task in random.choice(scenario_config):
            if isinstance(task, dict):
                func = next(task.iterkeys())
                param_string=''
                for param, value in task[func]['params'].iteritems():
                    if isinstance(value,str) and re.match('^__macro__',value):
                        task[func]['params'][param] = getattr(self, re.sub('^__macro__','',value))

                getattr(self,func)(**task[func]['params'])
            else:
                getattr(self,task)()

    def rs_create_network(self, network_create_args=None):
        """Create neutron network.

        :param network_create_args: dict, POST /v2.0/networks request options
        :returns: neutron network dict
        """
        self.rs_network = self._create_network(network_create_args or {})
        self.rs_network_id = self.rs_network['network']['id']
        return self.rs_network


    def _create_ports(self, network,
                      security_groups=None,
                      ports_per_network=-1,
                      min_ports_per_network=5,
                      max_ports_per_network=15,
                      port_create_args=None):
        if not port_create_args:
            port_create_args = {}

        if security_groups:
            port_create_args['security_groups'] = security_groups

        if ports_per_network == -1:
            num_ports = random.randint(min_ports_per_network, max_ports_per_network)
        else:
            num_ports = ports_per_network

        for i in range(num_ports):
            self._create_port(network, port_create_args)

    def _create_security_groups(self, num_security_groups=1,
                                num_rules_per_security_group=-1,
                                max_rules_per_security_group=10,
                                min_rules_per_security_group=1,
                                min_security_groups=1,
                                max_security_groups=5,
                                security_group_create_args=None):
        """
        Create security groups with rules in it.
        :param num_security_groups: Number of security groups to be created.
        Value -1 will make it to pick random number between min and max
        :param min_security_groups: Minimum number of security groups
        :param max_security_groups: Maximum number of security groups
        :param rules_per_security_group: Number of rules per security group,
        The value -1 will make to pick random number between min and max
        :param  max_rules_per_security_group: maximum number of rules per
        secgroup
        :param min_rules_per_security_group: Minimum number of rules per secgroup
        :param security_group_create_args: arguments to pass to secgroup create
        :return array of security group ids
        """
        security_groups = []
        security_group_ids = []
        security_group_create_args = security_group_create_args or {}

        if num_security_groups == -1:
            num_sgs = random.randint(min_security_groups, max_security_groups)
        else:
            num_sgs  = num_security_groups

        for i in range(num_sgs):
            sg = self._create_security_group(**security_group_create_args)
            if num_rules_per_security_group == -1:
                num_rules = random.randint(min_rules_per_security_group, max_rules_per_security_group)
            else:
                num_rules = num_rules_per_security_group

            self.create_security_group_rules(
                security_group=sg,
                rules_per_security_group=num_rules
            )
            security_group_ids.append(sg['security_group']['id'])
            security_groups.append(sg)
        self.rs_security_groups = security_groups
        self.rs_security_group_ids = security_group_ids
        return (self.rs_security_group_ids, self.rs_security_groups)


    def create_security_group_rules(self,
                                    security_group_create_args=None,
                                    security_group=None,
                                    rules_per_security_group=None):
        """Create security group policies"""
        security_group_create_args = security_group_create_args or {}

        if not security_group:
            security_group = self._create_security_group(**security_group_create_args)

        for i in range(rules_per_security_group):
            remote = random.choice(['sg','ip','none'])
            if remote == 'sg':
                remote_sg = self._create_security_group()
                remote_ip = None
            elif remote == 'ip':
                remote_ip = ".".join(map(str, (random.randint(0, 255)
                                             for _ in range(4))))
                remote_sg = None
            else:
                remote_ip = None
                remote_sg = None

            security_group_rule_create_args = {
                "direction": "egress",
                "protocol": random.choice(['tcp','udp','icmp'])
            }

            if remote_sg:
                security_group_rule_create_args["remote_group_id"] = remote_sg["security_group"]["id"]
            elif remote_ip:
                security_group_rule_create_args["remote_ip_prefix"] = remote_ip

            if security_group_rule_create_args['protocol'] == 'icmp':
                min_port = 0
                max_port = 255
            else:
                min_port = 0
                max_port = 65535

            security_group_rule_create_args["port_range_min"] = random.randint(min_port,max_port)
            security_group_rule_create_args["port_range_max"] = random.randint(security_group_rule_create_args["port_range_min"],max_port)
            LOG.debug("Using random generated sg rule arguments: %s" % security_group_rule_create_args)
            self._create_security_group_rule(security_group, security_group_rule_create_args)

    @atomic.action_timer("neutron.create_security_group_rule")
    def _create_security_group_rule(self, security_group,
                                    security_group_rule_create_args=None):
        """Create neutron security group rules.
        """
        security_group_rule_create_args['security_group_id'] = security_group["security_group"]["id"]
        security_group_rule_create_args.setdefault('direction', 'egress')
        self.rs_security_group_rule = self.clients("neutron").create_security_group_rule(
            {"security_group_rule": security_group_rule_create_args}
        )
        return self.rs_security_group_rule

    def rs_boot_server(self, image_id, flavor_id, nic_net_id, auto_assign_nic=False, **kwargs):
        """ Boot server
        :param image_id: Image id
        :param flavor_id: Flavor id
        """
        #if not kwargs.get("nics", False):
        kwargs["nics"] = [{'net-id': nic_net_id}]

        self._boot_server(image_id, flavor_id, auto_assign_nic, **kwargs)