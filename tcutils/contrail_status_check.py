# Tool to check contrail status on a bunch of nodes.
# The script has 2 functions.
# 1.Using get_status, you can get the 'contrail-status' output for the nodes that you pass.
#   --If no nodes are passed, the list of nodes specified from the testbed.py are taken by default.
#   --If you want status only for a specific bunch of services, include these as a dict as below:
#     includeservice = {'10.204.217.7': 'supervisor-control,contrail-named', '10.204.216.72': 'supervisor-vrouter'}
#     It will return only these service's status.
# --If you wan the script to retry a few times, send it as another argument. It will check those many times and only
#   if the service is not active, report back with failures.
# 2. Using check_status, you can get all the above mentioned features
# along with a boolean mentioning whether the contrail-status is clean
# with no non-active or duplicate actives or not
# Usage 1:
# nodes = ['10.204.217.7', '10.204.216.72']
# retry = 10
# includeservice = {'10.204.217.7': 'supervisor-control,contrail-control', '10.204.216.72': 'supervisor-vrouter,contr# ail-vrouter-agent'}
# (boolval, ret) = self.stat.check_status(nodes, includeservice, retry)
# The return value in boolval will be 0 if error present, 1 otherwise and in ret will be a list of dict specifying no# , de service and error for that node and service if present:
# boolval = 0
# ret = [{'Node': '10.204.216.72', 'Service': 'contrail-svc-monitor', 'Error': 'contrail-svc-monitor          inactiv# e    \r'}, {'Node': '10.204.217.11', 'Service': 'contrail-schema', 'Error': 'contrail-schema               inactive#        \r'}]
# Usage 2:
# nodes = ['10.204.217.7', '10.204.216.72']
# retry = 5
# ret = self.stat.get_status(nodes, retry)
# The return value in ret will be a list of dict specifying node, service and error for that node and service if pres# ent:
# ret = [{'Node': '10.204.216.72', 'Service': 'contrail-svc-monitor',
# 'Error': 'contrail-svc-monitor          inactive #     \r'}, {'Node':
# '10.204.217.11', 'Service': 'contrail-schema', 'Error': 'contrail-schema
# inactive   #        \r'}]

import re
from common.contrail_test_init import *


class Constatuscheck:

    '''Tool to get contrail status

    Mandatory:
    None

    Optional:
    :nodes : nodes to check the status for
    :includeservice  : check services included in includeservice only
    :retry    : retry for these many times before reporting

    '''

    def __init__(self, inputs=None):
        if not inputs:
            sanity_params = '/root/contrail-test/sanity_params.ini'
            self.inputs = ContrailTestInit(sanity_params)
            self.inputs.read_prov_file()

    def get_status(self, nodes=[], includeservice={}, retry=1):
        # Command used is contrail-status -x
        cmd = 'contrail-status -x'
        # initialize variables to be used during run
        global keys
        keys = ['Node', 'Service', 'Error']
        errlist = []
        skip_status = ['initializing', 'inactive', 'failed', 'timeout']
        single_active_services = {'contrail-schema': None,
                                  'contrail-svc-monitor': None, 'contrail-device-manager': None}
        # Get nodes from host_ips if not passed from test script
        if not nodes:
            nodes = self.inputs.__dict__['host_ips']
        for i in range(0, retry):
            for node in nodes:
                self.inputs.logger.debug(
                    'Executing %s command on node %s to check for contrail-status' % (cmd, node))
                # run command on each node for each retry
                output = self.inputs.run_cmd_on_server(node, cmd)
                for line in output.split("\n"):
                    status = None
                    service_status = line.split()
                    try:
                        service = service_status[0]
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
      # now check if in this retry the service we previously marked erroneous
      # has come up or not. If yes, delete it.
                        for err in errlist:
                            indline = json.dumps({'id': err})
                            #presentser = re.findall('\"Service\": \"(\w+)\"', indline)
                            if ((node in indline) and (service in indline)):
                                errlist.remove(err)
                    # Check for the status being one of the 4 "erroneous"
                    # statuses and update the list
                    if (status in skip_status):
                        if (includeservice):
                            self.update_error_if_includeservice_present(
                                node, includeservice, service, errlist, line, output)
                        else:
                            self.update_error_if_includeservice_not_present(
                                node, includeservice, service, errlist, line, output)

      # check if any of the 3 services in single_active_services defined above
      # have more than 1 "active" status nodes
        if single_active_services:
            for individual_service in single_active_services:
                if (single_active_services[individual_service].count('active')) > 1:
                    single_nodes = re.findall(
                        '([0-9.]+)-active', single_active_services[individual_service])
                    individual_service_error = [
                        single_nodes, individual_service,
                        'multiple actives found for this service']
                    errlist.append(dict(zip(keys, individual_service_error)))

        return errlist

    def check_status(self, nodes=[], includeservice={}, retry=1):
        # get status and return with a boolean too
        returndict = self.get_status(
            nodes=nodes, includeservice=includeservice, retry=retry)
        if returndict:
            return (0, returndict)
        else:
            return (1, returndict)

    def add_node_to_all_active_servers(self, includeservice, node, single_active_services, service, status):
        # add to single_active_services list if any active or backup is present. The check for multiple actives in
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
# if (('initializing' in errorline) or ('inactive' in errorline) or
# ('failed' in errorline) or ('timeout' in errorline) or ('active' in
# errorline) or ('backup' in errorline) or ('contrail-' in errorline) or
# ('supervisor-' in errorline) or ('rabbitmq-' in errorline) or ('ifmap'
# in errorline)):
                    if (self.check_if_erroneous_status_present(errorline)):
                        # sometimes the 'line+1' might have the next service,
                        # in which case 'line' is what we want
                        errorline = line
                    sererror = [node, service, errorline]
                    errlist.append(dict(zip(keys, sererror)))

    def update_error_if_includeservice_not_present(self, node, includeservice, service, errlist, line, output):
        # Check for "erroneous" statuses and update the errlist accordingly
        skip_this_variable = 0
        for err in errlist:
            indline = json.dumps({'id': err})
            if ((node in indline) and (service in indline)):
                # tag which node and service to not skip
                skip_this_variable = 1
        if not skip_this_variable:
            errorline = output.split("\n")[output.split("\n").index(line) + 1]
# if (('initializing' in errorline) or ('inactive' in errorline) or
# ('failed' in errorline) or ('timeout' in errorline) or ('active' in
# errorline) or ('backup' in errorline) or ('contrail-' in errorline) or
# ('supervisor-' in errorline) or ('rabbitmq-' in errorline) or ('ifmap'
# in errorline)):
            if (self.check_if_erroneous_status_present(errorline)):
                # sometimes the 'line+1' might have the next service, in which
                # case 'line' is what we want
                errorline = line
            sererror = [node, service, errorline]
            errlist.append(dict(zip(keys, sererror)))

    def check_if_erroneous_status_present(self, errorline):
        # check for the "erroneous" statuses and return True or False
        if (('initializing' in errorline) or ('inactive' in errorline) or ('failed' in errorline) or ('timeout' in errorline) or ('active' in errorline) or ('backup' in errorline) or ('contrail-' in errorline) or ('supervisor-' in errorline) or ('rabbitmq-' in errorline) or ('ifmap' in errorline)):
            return True
        else:
            return False
