
import fixtures
import time 
import uuid
from quantumclient.quantum import client
from quantumclient.client import HTTPClient
from quantumclient.common import exceptions
from contrail_fixtures import *

class QuantumFixture(fixtures.Fixture):
    def __init__(self, connections, tid, inputs, vn_count, vms_per_vn):
        self._vn_count = vn_count
        self._vms_per_vn = vms_per_vn
        self._vns = []
        self._vms = []
        self._subs = []
        self.obj = connections.quantum_fixture.obj
        self.logger = inputs.logger
        self.inputs = inputs
        self.tid = tid

    def setUp(self):
        super(QuantumFixture, self).setUp()
        for idx in range(self._vn_count):
            net_req = {'name': 'vnxxx-%s' % idx }

            try:
                vn_obj = self.obj.show_network(network=net_req['name'])
            except:
                net_req["tenant_id"] = self.tid
                vn_obj = self.obj.create_network({'network': net_req})['network']
            self._vns.append(vn_obj)

            snet = {"network_id":vn_obj['id']}
            snet["cidr"] = "10.%d.0.0/16" % idx
            snet["tenant_id"] = self.tid.replace('-', '')
            snet["ip_version"] = 4

            sub_obj = self.obj.create_subnet({'subnet': snet})['subnet']
            self._subs.append(sub_obj)

            self.logger.info ("Created VN %s, id %s" % (net_req['name'], vn_obj['id']))
            for jdx in range(self._vms_per_vn):
                #import pdb; pdb.set_trace()
                port_obj = self.q_create_port( 'vmy-%d-%d' % (idx,jdx), vn_obj['id'])
                self._vms.append(port_obj)
                #import pdb; pdb.set_trace()

            self.logger.info ("VM count %d" % len(self._vms))

    def q_create_port(self,name,netid):
        uuu = str(uuid.uuid4())
        port_req = {"device_id": uuu}
        port_req["name"] = name
        port_req["network_id"] = netid
        port_req["tenant_id"] = self.tid.replace('-', '')
        try:
            port_obj = self.obj.create_port({'port': port_req})['port']
        except:
            port_obj = None
        return port_obj

    def q_delete_port(self,port_obj):
        self.obj.delete_port(port_obj['id'])
        return

    def cleanUp(self):
        super(QuantumFixture, self).cleanUp()
        for idx in self._vms:
            self.q_delete_port(idx)
        for idx in self._subs:
            self.obj.delete_subnet(idx['id'])
        for idx in self._vns:
            self.obj.delete_network(idx['id'])

    def topVN(self):
        return self._vns[0]['id']
        #return self.obj.show_network(self._vns[0]['id'])

