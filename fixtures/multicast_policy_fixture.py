import vnc_api_test
from vnc_api.exceptions import NoIdError
from tcutils.util import get_random_name, retry
from vnc_api.vnc_api import *
import pprint
import logging

class MulticastPolicyFixture(vnc_api_test.VncLibFixture):

    def __init__(self,**kwargs):
        super(MulticastPolicyFixture, self).__init__(**kwargs)
        self.name = kwargs.get('name', get_random_name('mcastpolicy'))
        self.uuid = kwargs.get('uuid',None)
        self.policy = kwargs.get('policy')
        self.api_type = kwargs.get('api_type', 'contrail')
        self.parent_fq_name = [self.domain, self.project_name]
        self.parent_type = 'project'
        self.created = False
        self.fq_name = self.parent_fq_name + [self.name]

    def setUp(self):
        super(MulticastPolicyFixture, self).setUp()
        return self.create()

    
    def create(self):
        if not self.uuid:
            try:
                obj = self.vnc_api_h.multicast_policy_read(fq_name=self.fq_name)
                self.uuid = obj.uuid
            except NoIdError:
                self.logger.info('Creating multicast policy %s'%self.name)
                self.uuid = self.vnc_h.create_multicast_policy(
                             name=self.name,
                             policyList=self.policy)
                self.created = True

        return self.uuid



    def delete(self):
        self.vnc_h.delete_multicast_policy(self.uuid)

    def get_fq_name(self):
        return self.fq_name

    
    def cleanUp(self):
        if (self.created == False or self.inputs.fixture_cleanup == 'no') and\
           self.inputs.fixture_cleanup != 'force':
            self.logger.info('Skipping deletion of Multicast policy %s :'
                              %(self.fq_name))
        else:
            self.delete()

if __name__ == "__main__":
        from tcutils.util import *
        pol1 =[{'action' : 'deny' ,'source' : '0.0.0.0','group' : '225.1.1.1'}, {'action' : 'deny' ,'source' : '0.0.0.0','group' : '225.1.1.2'}]

        from common.contrail_test_init import ContrailTestInit
        from common.connections import ContrailConnections
        from common.log_orig import ContrailLogger
        logger = ContrailLogger('event')
        logger.setUp()
        mylogger = logger.logger
        inputs = ContrailTestInit('./instances.yaml', logger=mylogger)
        connections = ContrailConnections(inputs=inputs, logger=mylogger)

        obj = MulticastPolicyFixture(name='test_policy',policy=pol1,connections=connections)
        obj.setUp()
        obj.cleanUp()
      
