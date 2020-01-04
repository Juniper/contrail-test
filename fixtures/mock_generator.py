import fixtures
from tcutils.util import *
from contrail_fixtures import *
from fabric.context_managers import settings, hide


class MockGeneratorFixture(fixtures.Fixture):

    '''
    Fixture to handle creation, verification and deletion of mock generator. 
    '''

    def __init__(self, connections, inputs, num_generators,
                 num_instances_per_generator, num_networks,
                 num_flows_per_instance):
        self.connections = connections
        self.inputs = inputs
        self.logger = inputs.logger
        self.num_generators = num_generators
        self.MAX_GENERATORS_PER_PROCESS = 300
        self.num_instances_per_generator = num_instances_per_generator
        self.num_networks = num_networks
        self.num_flows_per_instance = num_flows_per_instance
    # end __init__

    def setUp(self):
        super(MockGeneratorFixture, self).setUp()
        ncomputes = len(self.inputs.compute_ips)
        ngens_per_host = self.num_generators / ncomputes
        nprocess_per_host = ngens_per_host / self.MAX_GENERATORS_PER_PROCESS
        if ngens_per_host % self.MAX_GENERATORS_PER_PROCESS:
            nprocess_per_host = nprocess_per_host + 1
        for host_ip in self.inputs.compute_ips:
            index = self.inputs.compute_ips.index(host_ip)
            ncollectors = len(self.inputs.collector_ips)
            collector_ip = self.inputs.collector_ips[index % ncollectors]
            collector = collector_ip + ':8086'
            cmd = "/opt/contrail/vrouter-venv/bin/run_mock_generator --collectors " + \
                collector
            username = self.inputs.host_data[host_ip]['username']
            password = self.inputs.host_data[host_ip]['password']
            for num in range(nprocess_per_host):
                if num == nprocess_per_host - 1 and ngens_per_host % self.MAX_GENERATORS_PER_PROCESS:
                    ngens = ngens_per_host % self.MAX_GENERATORS_PER_PROCESS
                else:
                    ngens = self.MAX_GENERATORS_PER_PROCESS
                cmd_ngen = " --num_generators " + str(ngens)
                cmd_instances = " --num_instances_per_generator " + \
                    str(self.num_instances_per_generator)
                cmd_networks = " --num_networks " + str(self.num_networks)
                cmd_flows = " --num_flows_per_instance " + \
                    str(self.num_flows_per_instance)
                issue_cmd = cmd + cmd_ngen + \
                    cmd_instances + cmd_networks + cmd_flows
                self.logger.info('Starting %s in %s' %
                                 (issue_cmd, self.get_node_name(host_ip)))
                output = self.inputs.run_cmd_on_server(host_ip, issue_cmd,
                                                       username, password, False)
    # end setUp

    def get_node_name(self, ip):
        return self.inputs.host_data[ip]['name']
    # end get_node_name

    def cleanUp(self):
        super(MockGeneratorFixture, self).cleanUp()
    # end cleanUp

# end class MockGeneratorFixture
