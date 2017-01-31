import fixtures
from kubernetes.client.rest import ApiException

from common import log_orig as contrail_logging
from tcutils.util import get_random_name, retry

class PodFixture(fixtures.Fixture):
    '''
    '''
    def __init__(self, connections, name=None):
        self.logger = connections.logger or contrail_logging.getLogger(__name__)
        self.name = name or get_random_name('pod')
        self.k8s_client = connections.k8s_client

        self.already_exists = False

    def setUp(self):
        super(PodFixture, self).setUp()    
        self.create()

    def verify_on_setup()
        if not self.verify_pod_is_running():
            self.logger.error('POD %s verification failed', %(
                               self.name))
            return False
        if not self.verify_pod_in_contrail_api():
            self.logger.error('POD %s not seen in Contrail API' %(
                               self.name))
            return False
        if not self.verify_pod_in_contrail_control():
            self.logger.error('POD %s not seen in Contrail control' %(
                               self.name))
            return False
        if not self.verify_pod_in_contrail_agent():
            self.logger.error('POD %s not seen in Contrail agent' %(
                               self.name))
            return False
        self.logger.info('Namespace %s verification passed' % (self.name))
        return True
    # end verify_on_setup 


    @retry(delay=1, tries=10)
    def verify_pod_is_running(self):
        if self.status != 'Running':
            self.logger.warn('POD %s is not running yet, It is %s' %(
                             self.name, self.status))
            return False
        return True
    # end verify_namespace_is_active


    def cleanUp(self):
        super(PodFixture, self).cleanUp()
        self.delete()

    def _populate_attr(self):
        self.uuid = self.obj.metadata.uid
        self.status = self.obj.status.phase

    def read(self):
        try:
            self.obj = self.k8s_client.read_pod(self.name,self.namespace='default')
            self._populate_attr()
            self.already_exists = True
        except ApiException as e:
            self.logger.debug('POD %s not present' % (self.name))
            return None 
    # end read

    def create(self):
        #ns_exists = self.read()
        ns_exits=False ;#  Will if necessary 
        if ns_exists:
            return ns_exists
        self.obj = self.k8s_client.create_pod(self.namespace='default',self.name, self.image='nginx')
        self._populate_attr() 
    # end create

    def delete(self):
        if not self.already_exists:
            return self.k8s_client.delete_pod(self.namespace='default', self.name)
    # end delete

    @retry(delay=1, tries=10)
    def verify_pod_in_contrail_api(self):
        # TODO 
        return True  
    # end verify_pod_in_contrail_api   
  
    @retry(delay=1, tries=10)
    def verify_pod_is_running (self):
        # TODO 
        return True  
    # verify_pod_is_running 

    @retry(delay=1, tries=10)
    def verify_pod_in_contrail_control (self):
        # TODO 
        return True  
    # verify_pod_in_contrail_control
 
    @retry(delay=1, tries=10)
    def verify_pod_in_contrail_agent (self):
        # TODO 
        return True  
    # verify_pod_in_contrail_agent 
