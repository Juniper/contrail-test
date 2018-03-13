#!/usr/bin/python
# Tool to check contrail status on a bunch of nodes.
# The script has 2 functions.
# 1.Using get_status, you can get the 'contrail-status' output
#   for the nodes that you pass.
#   --If no nodes are passed, the list of nodes specified from
#     the testbed.py are taken by default.
#   --If you want status only for a specific bunch of services,
#     include these as a dict as below:
#     includeservice =
#     {'10.204.216.72': 'supervisor-vrouter',
#      '10.204.217.7': 'supervisor-control,contrail-named'}
#     It will return only these service's status.
# 2. Using check_status, you can get all the above mentioned features
# along with a boolean mentioning whether the contrail-status is
# clean with no non-active or duplicate actives or not
# Usage 1:
# nodes = ['10.204.217.7', '10.204.216.72']
# includeservice =
# {'10.204.216.72': 'supervisor-vrouter,contrail-vrouter-agent',
#  '10.204.217.7': 'supervisor-control,contrail-control'}
# (boolval, ret) = self.stat.check_status(nodes, includeservice)
# The return value in boolval will be False if error present, True
# otherwise and in ret will be a list of dict
# specifying node, service and error for that node and service
# if present:
# boolval = False
# ret =
# [{'Error': 'contrail-svc-monitor          inactive      \r',
#   'Node': '10.204.216.72',
#   'Service': 'contrail-svc-monitor'},
#  {'Error': 'contrail-schema               inactive           \r',
#   'Node': '10.204.217.11',
#   'Service': 'contrail-schema'}]
# Usage 2:
# nodes = ['10.204.217.7', '10.204.216.72']
# ret = self.stat.get_status(nodes)
# The return value in ret will be a list of dict specifying node,
# service and error for that node and service if present:
# ret =
# [{'Error': 'contrail-svc-monitor          inactive      \r',
#   'Node': '10.204.216.72',
#   'Service': 'contrail-svc-monitor'},
#  {'Error': 'contrail-schema inactive          \r',
#   'Node': '10.204.217.11',
#   'Service': 'contrail-schema'}]
# 3. Using wait_till_contrail_cluster_stable, you can get all
#    the above mentioned features
#    along with a boolean mentioning whether the contrail-status
#    is clean with no non-active or duplicate actives or not
#    and along with a delay(default = 300sec)
# Usage 1:
# nodes = ['10.204.217.7', '10.204.216.72']
# delay = 20(default value = 10)
# tries = 50(default value = 30)
# (so delay in this case will be = 20*50 seconds)
# includeservice =
# {'10.204.216.72': 'supervisor-vrouter,contrail-vrouter-agent',
#  '10.204.217.7': 'supervisor-control,contrail-control'}
# (boolval, ret) = self.stat.wait_till_contrail_cluster_stable(nodes, includeservice, delay, tries)
# The return value in boolval will be False if error present, True
# otherwise and in ret will be a list of dict
# specifying node, service and error for that node and service
# if present:
# boolval = False
# ret =
# [{'Error': 'contrail-svc-monitor          inactive      \r',
#   'Node': '10.204.216.72',
#   'Service': 'contrail-svc-monitor'},
#  {'Error': 'contrail-schema               inactive           \r',
#   'Node': '10.204.217.11',
#   'Service': 'contrail-schema'}]
# Usage 2:
# nodes = ['10.204.217.7', '10.204.216.72']
# delay = 50
# (so delay in this case will be = 50*30 seconds)
# ret = self.stat.wait_till_contrail_cluster_stable(nodes, delay)
# The return value in ret will be a list of dict specifying node,
# service and error for that node and service if present:
# ret =
# [{'Error': 'contrail-svc-monitor          inactive      \r',
#   'Node': '10.204.216.72',
#   'Service': 'contrail-svc-monitor'},
#  {'Error': 'contrail-schema inactive          \r',
#   'Node': '10.204.217.11',
#   'Service': 'contrail-schema'}]

import re
import time
from common.contrail_test_init import *
import sys

class ContrailStatusChecker():

    '''Tool to get contrail status

    Mandatory:
    None

    Optional:
    :nodes : nodes to check the status for
    :includeservice  : check services included in includeservice only

    '''

    def __init__(self, inputs=None):
        self.inputs = inputs
        if not inputs:
            sanity_params = os.environ.get(
                'TEST_CONFIG_FILE') or 'sanity_params.ini'
            self.inputs = ContrailTestInit(sanity_params)
            self.inputs.read_prov_file()

    def get_status(self, nodes=[], includeservice={}):
        #ToDo: msenthil - revisit it once contrail-status is supported in microservices model
        raise Exception('contrail-status not supported')
        # Command used is contrail-status -x
        cmd = 'contrail-status -x'
        # initialize variables to be used during run
        self.keys = ['Node', 'Service', 'Error']
        errlist = []
        skip_status = ['initializing', 'inactive', 'failed', 'timeout']
        single_active_services = {'contrail-schema': None,
                                  'contrail-svc-monitor': None,
                                  'contrail-device-manager': None,
                                  'contrail-kube-manager' : None}
        # Get nodes from host_ips if not passed from test script
        if not nodes:
            nodes = self.inputs.host_ips
        if includeservice:
            nodes = includeservice.keys() # Ignoring the value of variable nodes if user include this variable
        for node in nodes:
            self.inputs.logger.debug(
                'Executing %s command on node %s to check for contrail-status' % (cmd, node))
            # run command on each node
            node_roles = []
            if includeservice.get(node):
                services_included = includeservice[node].split(",")
                for service in services_included:
                    role = self.get_service_role(service)
                    if role not in node_roles:
                        node_roles.append(role)
            else:
                if node in self.inputs.bgp_ips:
                    role = "controller"
                    node_roles.append(role)
                if node in self.inputs.collector_ips:
                    role = "analytics"
                    node_roles.append(role)
                if node in self.inputs.database_ips:
                    role = "analyticsdb"
                    node_roles.append(role)
                if node in self.inputs.compute_ips:
                    role = "agent"
                    node_roles.append(role)
                if node in self.inputs.kube_manager_ips:
                    role = "contrail-kube-manager"
                    node_roles.append(role)

            for role in node_roles:
                output = self.inputs.run_cmd_on_server(node, cmd, container = role)
                for line in output.split("\n"):
                    status = None
                    service_status = line.split()
                    try:
                        service = service_status[0]
                        #service name can either have ":" or not.
                        #check if ":" present and remove it
                        if service[-1] == ":":
                            service = service[:-1]
                    except IndexError:
                        service = None
                    if len(service_status) == 2:
                        status = service_status[1].strip()
                    # Variable "status" has the status for corresponding
                    # service
                    if not status:
                        continue
                    if ((status == "active") or (status == "backup")):
                        if service in single_active_services.keys():
                            self.add_node_to_all_active_servers(
                            includeservice, node, single_active_services, service, status)
                    # Check for the status being one of the 4 "erroneous"
                    #statuses and update the list
                    if (status in skip_status):
                        if (includeservice):
                            self.update_error_if_includeservice_present(
                            node, includeservice, service, errlist, line, output)
                        else:
                            self.update_error_if_includeservice_not_present(
                            node, includeservice, service, errlist, line, output)

      # check if any of the 3 services in
      # single_active_services defined above
      # have more than 1 "active" status nodes
      # or no active status nodes
        if single_active_services:
            for individual_service in single_active_services:
                # Services like contrail-device-manager may not be enabled on
                # the node at all
                if not single_active_services[individual_service]:
                    continue
                if (single_active_services[individual_service].count('active')) > 1:
                    single_nodes = re.findall(
                        '([0-9.]+)-active', single_active_services[individual_service])
                    individual_service_error = [
                        single_nodes, individual_service,
                        'multiple actives found for this service']
                    errlist.append(
                        dict(zip(self.keys, individual_service_error)))

                if (single_active_services[individual_service].count('active')) == 0:
                    single_nodes = re.findall(
                        '([0-9.]+)-backup', single_active_services[individual_service])
                    individual_service_error = [
                        single_nodes, individual_service,
                        'no actives found for this service']
                    errlist.append(
                        dict(zip(self.keys, individual_service_error)))

        return errlist

    def check_status(self, nodes=[], includeservice={}):
        # get status and return with a boolean too
        returndict = self.get_status(
            nodes=nodes, includeservice=includeservice)
        if returndict:
            return (False, returndict)
        else:
            return (True, returndict)

    def wait_till_contrail_cluster_stable(self, nodes=[], includeservice={}, delay=10, tries=30):
        # Wait until the contrail-status shows stability across
        # all the  nodes
        for i in range(0, tries):
            returndict = self.get_status(
                nodes=nodes, includeservice=includeservice)
            if returndict:
                self.inputs.logger.debug(
                    'Not all services up. Sleeping for %s seconds. Present iteration number : %s' % (delay, i))
                time.sleep(delay)
                continue
            else:
                if nodes:
                    if includeservice:
                        self.inputs.logger.info(
                            'Services %s are up on %s' % (includeservice, nodes))
                    else:
                        self.inputs.logger.info(
                            'All services are up on %s' % nodes)
                else: 
                    if includeservice:
                        self.inputs.logger.info(
                            'Services %s are up on all nodes in testbed.py' % includeservice)
                    else:
                        self.inputs.logger.info(
                            'Entire Contrail cluster seems stable')
                return (True, returndict)

        self.inputs.logger.error(
            'Not all services up , Gave up!')
        if returndict:
            return (False, returndict)
        else:
            return (True, returndict)

    def add_node_to_all_active_servers(self, includeservice, node, single_active_services, service, status):
        # add to single_active_services list if any
        # active or backup is present. The check for multiple actives in
        # cluster is taken care later
        if (includeservice):
            if node in includeservice.keys():
                if service in includeservice[node]:
                    if single_active_services[service]:
                        if not(node in single_active_services[service]):
                            # if its the correct node and service, add
                            single_active_services[
                                service] = '-'.join([x for x in (single_active_services[service], node, status) if x])
                    else:
                        single_active_services[
                            service] = '-'.join([x for x in (single_active_services[service], node, status) if x])
        # if includeservice not present
        else:
            if single_active_services[service]:
                if not(node in single_active_services[service]):
                    single_active_services[
                        service] = '-'.join([x for x in (single_active_services[service], node, status) if x])
            else:
                single_active_services[
                    service] = '-'.join([x for x in (single_active_services[service], node, status) if x])

    def update_error_if_includeservice_present(self, node, includeservice, service, errlist, line, output):
        # Check for "erroneous" statuses and update the errlist accordingly
        if node in includeservice:
            if service in includeservice[node]:
                skip_this_variable = 0
                for err in errlist:
                    indline = json.dumps({'id': err})
                    if ((node in indline) and (service in indline)):
                        # tag which node and service to not skip
                        skip_this_variable = 1
                if not skip_this_variable:
                    errorline = output.split(
                        "\n")[output.split("\n").index(line) + 1]
                    if (self.check_if_erroneous_status_present(errorline)):
                        # sometimes the 'line+1' might have the next service,
                        # in which case 'line' is what we want
                        errorline = line
                    sererror = [node, service, errorline]
                    errlist.append(dict(zip(self.keys, sererror)))

    def update_error_if_includeservice_not_present(self, node, includeservice, service, errlist, line, output):
        # Check for "erroneous" statuses and update the errlist accordingly
        skip_this_variable = 0
        for err in errlist:
            indline = json.dumps({'id': err})
            if ((node in indline) and (service in indline)):
                # tag which node and service to not skip
                skip_this_variable = 1
        if not skip_this_variable:
            try:
                errorline = output.split("\n")[output.split("\n").index(line) + 1]
                if (self.check_if_erroneous_status_present(errorline)):
                    # sometimes the 'line+1' might have the next service, in which
                    # case 'line' is what we want
                    errorline = line
            except IndexError:
                errorline = line
            sererror = [node, service, errorline]
            errlist.append(dict(zip(self.keys, sererror)))

    def check_if_erroneous_status_present(self, errorline):
        # check for the "erroneous" statuses and return True or False
        if (('initializing' in errorline) or ('inactive' in errorline) or ('failed' in errorline) or ('timeout' in errorline) or ('active' in errorline) or ('backup' in errorline) or ('contrail-' in errorline) or ('supervisor-' in errorline) or ('rabbitmq-' in errorline) or ('ifmap' in errorline)):
            return True
        else:
            return False
    
    def get_service_role(self, service):
        '''
        In case user mention "includeservice" to get status of particular 
        service, this function help get the role for that service
        eg, for service "contrail-collector", this function will return the
        role as "analytics" so that, analytics container can be used to 
        get the status in get_status.
        '''
        service_dict = {"controller" : ["contrail-control", 
                                        "contrail-control-nodemgr",
                                        "contrail-dns",
                                        "contrail-named",
                                        "contrail-api",
                                        "contrail-config-nodemgr",
                                        "contrail-device-manager",
                                        "contrail-schema",
                                        "contrail-svc-monitor",
                                        "contrail-webui",
                                        "contrail-webui-middleware"],
                        "analytics" : ["contrail-alarm-gen",
                                       "contrail-analytics-api",
                                       "contrail-analytics-nodemgr",
                                       "contrail-collector",
                                       "contrail-query-engine",
                                       "contrail-snmp-collector",
                                       "contrail-topology"],
                        "analyticsdb" : ["contrail-database",
                                         "contrail-database-nodemgr",
                                         "kafka"],
                        "contrail-kube-manager" : ["contrail-kube-manager"],
                        "compute" : ["contrail-vrouter-agent",
                                     "contrail-vrouter-nodemgr"]}
        for role in service_dict.keys():
            if service in service_dict[role]:
                return role

    def main(self):
        (boolval, ret) = self.wait_till_contrail_cluster_stable(delay=10, tries=9) 
        sys.exit(boolval)
    # end main

if __name__ == "__main__":
    ContrailStatusChecker().main()
