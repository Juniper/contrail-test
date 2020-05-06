#!/usr/bin/python
#  {'Error': 'contrail-schema inactive          \r',
#   'Node': '10.204.217.11',
#   'Service': 'contrail-schema'}]

from __future__ import absolute_import
from builtins import range
from builtins import object
import re
import time
import sys
from .contrail_status import contrail_status
from collections import defaultdict

class ContrailStatusChecker(object):

    '''Tool to get contrail status

    Mandatory:
    None

    Optional:
    :inputs : ContrailTestInit object
    :nodes : nodes to check the status for
    :includeservice  : check services included in includeservice only
    '''

    def __init__(self, inputs=None):
        self.inputs = inputs

    def _get_failed_services(self, status_dict):
        failed_services = defaultdict(dict)
        for host in status_dict:
            for service in status_dict[host]:
                if status_dict[host][service]['status'] != 'active' and \
                   status_dict[host][service]['status'] != 'backup':
                    failed_services[host][service] = dict(status_dict[host][service])
        return failed_services

    def _confirm_service_status(self, status_dict, expected_status):
        for host in status_dict:
            for service in status_dict[host]:
                if status_dict[host][service]['status'] != expected_status:
                    return False
        return True

    def wait_till_service_down(self, *args, **kwargs):
        return self.wait_till_contrail_cluster_stable(*args, expectation=False, **kwargs)

    def get_service_status(self, svc, state, nodes=None, roles=None,
            services=None, delay=10, tries=30, expectation=True,
            expected_state=None, keyfile=None, certfile=None, cacert=None,
            refresh=False):
        svchosts = list()
        status_dict = contrail_status(self.inputs, nodes, roles, services,
                keyfile=keyfile, certfile=certfile, cacert=cacert, refresh=refresh)
        for host in status_dict:
            if svc in status_dict[host]:
                 if status_dict[host][svc]['status'] == state:
                    svchosts.append(host)
        return svchosts

    def wait_till_contrail_cluster_stable(self, nodes=None, roles=None,
            services=None, delay=10, tries=30, expectation=True,
            expected_state=None, keyfile=None, certfile=None, cacert=None,
            refresh=False):
        exp = 'up' if expectation else 'down'
        for i in range(0, tries):
            status_dict = contrail_status(self.inputs, nodes, roles, services,
                keyfile=keyfile, certfile=certfile, cacert=cacert, refresh=refresh)
            failed_services = self._get_failed_services(status_dict)
            if (failed_services and expectation) or (not expectation and not failed_services):
                self.inputs.logger.debug('%s'%failed_services)
                if i+1 < tries:
                    self.inputs.logger.debug('Not all services up. '
                        'Sleeping for %s seconds. iteration: %s' %(delay, i))
                    time.sleep(delay)
                continue
            elif (expected_state is not None) and (
                not self._confirm_service_status(status_dict, expected_state)):
                if i+1 < tries:
                    self.inputs.logger.debug('All Services are not in expected'
                        'state %s. Sleeping for %s seconds. iteration: %s' %(
                         expected_state, delay, i))
                    time.sleep(delay)
                continue
            else:
                if roles or services:
                    msg = 'Contrail services %s are %s' %(services or roles, exp)
                else:
                    msg = 'All the contrail services are %s'%(exp)
                if nodes:
                    msg = msg+' on nodes %s'%nodes
                else:
                    msg = msg+' on all nodes'
                try:
                    self.inputs.logger.info(msg)
                except Exception as e:
                    pass
                return (True, status_dict)
        self.inputs.logger.error(
            'Not all services up , Gave up!')
        return (False, failed_services)
