# Fixture to check contrail status on a bunch of nodes.
# The script has 2 functions.
# 1.Using get_status, you can get the 'contrail-status' output for the nodes that you pass.
#   --If no nodes are passed, the list of nodes specified from the testbed.py are taken by default.
#   --If you want status only for a specific bunch of services, include these as a dict as below:
#     includeservice = {'10.204.217.7': 'supervisor-control,contrail-named', '10.204.216.72': 'supervisor-vrouter'}
#     It will return only these service's status.
# --If you wan the script to retry a few times, send it as another argument. It will check those many times and onl#     y if the service is not active, report back with failures.
# 2. Using check_status, you can get all the above mentioned features
# along with a boolean mentioning whether the cont#   rail-status is clean
# with no non-active or duplicate actives or not
import os
import signal
import re
import json
import struct
import socket
import random
from fabric.state import connections as fab_connections
import test
import traffic_tests
from common.contrail_test_init import *
from common import isolated_creds
from vn_test import *
from vm_test import *
from floating_ip import *
from tcutils.commands import *
sys.path.append(os.path.realpath('tcutils/pkgs/Traffic'))
from traffic.core.stream import Stream
from traffic.core.profile import create, ContinuousProfile
from traffic.core.helpers import Host
from traffic.core.helpers import Sender, Receiver


class Constatuscheck(test.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(Constatuscheck, cls).setUpClass()
        cls.isolated_creds = isolated_creds.IsolatedCreds(cls.__name__,
                                                          cls.inputs, ini_file=cls.ini_file,
                                                          logger=cls.logger)
        cls.isolated_creds.setUp()
        cls.project = cls.isolated_creds.create_tenant()
        cls.isolated_creds.create_and_attach_user_to_tenant()
        cls.inputs = cls.isolated_creds.get_inputs()
        cls.connections = cls.isolated_creds.get_conections()
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib = cls.connections.vnc_lib
        cls.agent_inspect = cls.connections.agent_inspect
        cls.cn_inspect = cls.connections.cn_inspect
        cls.analytics_obj = cls.connections.analytics_obj
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        cls.isolated_creds.delete_tenant()
        super(Constatuscheck, cls).tearDownClass()
    # end tearDownClass

    def get_status(self, nodes=None, includeservice=None, retry=1):
        cmd = 'contrail-status -x'
        keys = ['Node', 'Service', 'Error']
        errlist = []
        oneactonly = {}
        oneactonly['contrail-schema'] = None
        oneactonly['contrail-svc-monitor'] = None
        oneactonly['contrail-device-manager'] = None
        if not nodes:
            nodes = self.inputs.compute_ips
        import pdb
        pdb.set_trace()
        for i in range(0, retry):
            import pdb
            pdb.set_trace()
            for node in nodes:
                self.logger.info("cmd: %s @ %s" % (cmd, node))
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
                    if(status):
                        if ((status == "active") or (status == "backup")):
                            if ((service == "contrail-schema") or (service == "contrail-svc-monitor") or (service == "contrail-device-manager")):
                                if (includeservice):
                                    if node in includeservice:
                                        if service in includeservice[node]:
                                            if oneactonly[service]:
                                                if not(node in oneactonly[service]):
                                                    oneactonly[
                                                        service] = '-'.join([x for x in (oneactonly[service], node, status) if x])
                                            else:
                                                oneactonly[
                                                    service] = '-'.join([x for x in (oneactonly[service], node, status) if x])
                                else:
                                    if oneactonly[service]:
                                        if not(node in oneactonly[service]):
                                            oneactonly[
                                                service] = '-'.join([x for x in (oneactonly[service], node, status) if x])
                                    else:
                                        oneactonly[
                                            service] = '-'.join([x for x in (oneactonly[service], node, status) if x])
                            for err in errlist:
                                indline = json.dumps({'id': err})
                                #presentser = re.findall('\"Service\": \"(\w+)\"', indline)
                                if ((node in indline) and (service in indline)):
                                    errlist.remove(err)

                        if ((status == "initializing") or (status == "inactive") or (status == "failed") or (status == "timeout")):
                            if (includeservice):
                                if node in includeservice:
                                    if service in includeservice[node]:
                                        alpresent = 0
                                        for err in errlist:
                                            indline = json.dumps({'id': err})
                                            if ((node in indline) and (service in indline)):
                                                alpresent = 1
                                        if not alpresent:
                                            errorline = output.split(
                                                "\n")[output.split("\n").index(line) + 1]
                                            if (('initializing' in errorline) or ('inactive' in errorline) or ('failed' in errorline) or ('timeout' in errorline) or ('active' in errorline) or ('backup' in errorline)):
                                                errorline = line
                                            sererror = [node,
                                                        service, errorline]
                                            errlist.append(
                                                dict(zip(keys, sererror)))
                            else:
                                alpresent = 0
                                for err in errlist:
                                    indline = json.dumps({'id': err})
                                    if ((node in indline) and (service in indline)):
                                        alpresent = 1
                                if not alpresent:
                                    errorline = output.split(
                                        "\n")[output.split("\n").index(line) + 1]
                                    if (('initializing' in errorline) or ('inactive' in errorline) or ('failed' in errorline) or ('timeout' in errorline) or ('active' in errorline) or ('backup' in errorline)):
                                        errorline = line
                                    sererror = [node, service, errorline]
                                    errlist.append(dict(zip(keys, sererror)))

        if oneactonly:
            for ser in oneactonly:
                if (oneactonly[ser].count('active')) > 1:
                    snodes = re.findall('([0-9.]+)-active', oneactonly[ser])
                    sererror = [snodes, ser,
                                'multiple actives found for this service']
                    errlist.append(dict(zip(keys, sererror)))

        return errlist

    def check_status(self, nodes=None, includeservice=None, retry=1):
        retdict = self.get_status(
            nodes=nodes, includeservice=includeservice, retry=retry)
        if retdict:
            return (0, retdict)
        else:
            return (1, retdict)
