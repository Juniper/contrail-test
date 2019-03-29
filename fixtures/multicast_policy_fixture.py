import vnc_api_test
from cfgm_common.exceptions import NoIdError
from tcutils.util import get_random_name, retry
from vnc_api.vnc_api import *
import pprint
import logging

class MulticastPolicyFixture(vnc_api_test.VncLibFixture):

    def __init__(self,name,parent_obj,connections, *args, **kwargs):
        super(MulticastPolicyFixture, self).__init__(*args, **kwargs)
        self.name = name
        self.uuid = kwargs.get('uuid')
        self.action = kwargs.get('action') or 'pass'
        self.source = kwargs.get('source')
        self.group = kwargs.get('group')
        self.parent_obj = parent_obj
        self.connections = connections
        self.vnc_h = connections.orch.vnc_h

    def setUp(self):
        super(MulticastPolicyFixture, self).setUp()
        return self.create()

    def create(self):

        self.fq_name = self.parent_obj.fq_name + [self.name] 
        self.uuid = self.vnc_h.create_multicast_policy(
                             name=self.name,
                             parent_obj=self.parent_obj,
                             action=self.action,
                             source=self.source,
                             group=self.group)
        self.created = True
        return self.uuid

    def delete(self):
        self.vnc_h.delete_multicast_policy(self.uuid)

    def get_fq_name(self):
        return self.fq_name

    def cleanUp(self):
        self.delete()
        super(MulticastPolicyFixture, self).cleanUp()
