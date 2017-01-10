import vnc_api_test
from cfgm_common.exceptions import NoIdError
from tcutils.util import get_random_name, retry

class HealthCheckFixture(vnc_api_test.VncLibFixture):
    '''Fixture to handle ServiceHealthCheck object

    Optional:
    :param name : name of the health check (random name)
    :param uuid : UUID of the health check
    :param enabled  : Health check status default:True
    :param hc_type : Health check type (link-local, end-to-end)
    :param probe_type : Health check probe type (PING,HTTP)
    :param delay : delay in secs between probes
    :param timeout : timeout for each probe, must be < delay
    :param max_retries : max no of retries
    :param http_method : One of GET/PUT/PUSH default:GET
    :param http_url : HTTP URL Path (local-ip or ip-addr or http://ip:port/v1)
    :param http_codes : HTTP reply codes

    Inherited optional parameters:
    :param domain   : default is default-domain
    :param project_name  : default is admin
    :param cfgm_ip  : default is 127.0.0.1
    :param api_port : default is 8082
    :param connections : ContrailConnections object. default is None
    :param username : default is admin
    :param password : default is contrail123
    :param auth_server_ip : default is 127.0.0.1

    '''

    def __init__(self, **kwargs):
        super(HealthCheckFixture, self).__init__(self, **kwargs)
        self.name = kwargs.get('name') or get_random_name('HealthCheck')
        self.uuid = kwargs.get('uuid', None)
        self.hc_type = kwargs.get('hc_type') or 'link-local'
        self.status = kwargs.get('enabled') or True
        self.probe_type = kwargs.get('probe_type') or 'PING'
        self.delay = kwargs.get('delay', None)
        self.timeout = kwargs.get('timeout', None)
        self.max_retries = kwargs.get('max_retries', None)
        self.http_method = kwargs.get('http_method', None)
        self.http_url = kwargs.get('http_url', 'local-ip')
        self.http_codes = kwargs.get('http_codes', None)
        self.created = False

    def setUp(self):
        super(HealthCheckFixture, self).setUp()
        self.fq_name = [self.domain, self.project_name, self.name]
        self.create()

    def cleanUp(self):
        super(HealthCheckFixture, self).cleanUp()
        if (self.created == False or self.inputs.fixture_cleanup == 'no') and\
           self.inputs.fixture_cleanup != 'force':
            self.logger.info('Skipping deletion of Health Check %s :'
                              %(self.fq_name))
        else:
            self.delete()

    def read(self):
        self.logger.debug('Fetching info about Health Check %s'%self.uuid)
        obj = self.vnc_h.get_health_check(id=self.uuid)
        self.name = obj.name
        self.fq_name = obj.get_fq_name()
        prop = obj.get_service_health_check_properties()
        self.status = prop.enabled
        self.hc_type = prop.health_check_type
        self.probe_type = prop.monitor_type
        self.delay = prop.delay
        self.timeout = prop.timeout
        self.max_retries = prop.max_retries
        self.http_method = prop.http_method
        self.http_url = prop.url_path
        self.http_codes = prop.expected_codes

    def create(self):
        if not self.uuid:
            try:
                obj = self.vnc_h.get_health_check(fq_name=self.fq_name)
                self.uuid = obj.uuid
            except NoIdError:
                pass
        if self.uuid:
            self.read()
        else:
            self.logger.info('Creating Health Check %s'%self.name)
            self.uuid = self.vnc_h.create_health_check(self.fq_name,
                                  enabled=self.status,
                                  health_check_type=self.hc_type,
                                  monitor_type=self.probe_type,
                                  delay=self.delay,
                                  timeout=self.timeout,
                                  max_retries=self.max_retries,
                                  http_method=self.http_method,
                                  url_path=self.http_url,
                                  expected_codes=self.http_codes)
            self.created = True
        self.logger.info('Health Check: %s(%s), type %s'
                         %(self.name, self.uuid, self.probe_type))

    def delete(self):
        self.logger.info('Deleting Health Check %s(%s)'%(self.name, self.uuid))
        self.vnc_h.delete_health_check(id=self.uuid)
        if getattr(self, 'verify_is_run', False):
            assert self.verify_on_cleanup()

    def update_properties(self, enabled=None, hc_type=None,
                          probe_type=None, delay=None,
                          timeout=None, max_retries=None, http_method=None,
                          http_url=None, http_codes=None):
        self.status = enabled or self.status
        self.hc_type = hc_type or self.hc_type
        self.probe_type = probe_type or self.probe_type
        self.delay = delay or self.delay
        self.timeout = timeout or self.timeout
        self.max_retries = max_retries or self.max_retries
        self.http_url = http_url or self.http_url
        self.http_method = http_method or self.http_method
        self.http_codes = http_codes or self.http_codes
        self.vnc_h.update_health_check_properties(self.uuid,
                                      enabled=self.status,
                                      health_check_type=self.hc_type,
                                      monitor_type=self.probe_type,
                                      delay=self.delay,
                                      timeout=self.timeout,
                                      max_retries=self.max_retries,
                                      http_method=self.http_method,
                                      url_path=self.http_url,
                                      expected_codes=self.http_codes)

    def verify_on_setup(self):
        self.verify_is_run = True
        ret = self.verify_in_api_server()
        self.logger.info('Health Check(%s): verify_on_setup %s'%(self.uuid,
                         'passed' if ret else 'failed'))
        return ret

    def verify_on_cleanup(self):
        ret = self.verify_not_in_api_server()
        self.logger.info('Health Check(%s): verify_on_cleanup %s'%(self.uuid,
                         'passed' if ret else 'failed'))
        return ret

    @retry(delay=2, tries=5)
    def verify_in_api_server(self):
        api_h = self.connections.api_server_inspect
        api_obj = api_h.get_service_health_check(self.uuid)
        if self.status != api_obj.status:
            self.logger.warn('HC status didnt match. Exp: %s Act: %s'%(
                              self.status, api_obj.status))
            return False
        if self.hc_type != api_obj.health_check_type:
            self.logger.warn('HC type didnt match. Exp: %s Act: %s'%(
                              self.hc_type, api_obj.health_check_type))
            return False
        if self.probe_type != api_obj.probe_type:
            self.logger.warn('HC probe_type didnt match. Exp: %s Act: %s'%(
                              self.probe_type, api_obj.probe_type))
            return False
        if self.delay and self.delay != api_obj.delay:
            self.logger.warn('HC delay didnt match. Exp: %s Act: %s'%(
                              self.delay, api_obj.delay))
            return False
        if self.timeout and self.timeout != api_obj.timeout:
            self.logger.warn('HC timeout didnt match. Exp: %s Act: %s'%(
                              self.timeout, api_obj.timeout))
            return False
        if self.max_retries and self.max_retries != api_obj.max_retries:
            self.logger.warn('HC retries didnt match. Exp: %s Act: %s'%(
                              self.max_retries, api_obj.max_retries))
            return False
        if self.http_url and self.http_url != api_obj.http_url:
            self.logger.warn('HC http_url didnt match. Exp: %s Act: %s'%(
                              self.http_url, api_obj.http_url))
            return False
        if self.http_method and self.http_method != api_obj.http_method:
            self.logger.warn('HC http-method didnt match. Exp: %s Act: %s'%(
                              self.http_method, api_obj.http_method))
            return False
        if self.http_codes and self.http_codes != api_obj.http_codes:
            self.logger.warn('HC http-codes didnt match. Exp: %s Act: %s'%(
                              self.http_codes, api_obj.http_codes))
            return False
        self.logger.info('verify_in_api_server passed for HC obj %s'%self.uuid)
        return True

    @retry(delay=2, tries=5)
    def verify_not_in_api_server(self):
        api_h = self.connections.api_server_inspect
        if api_h.get_service_health_check(self.uuid, refresh=True):
            self.logger.warn('HC: %s is still found in api server'%self.uuid)
            return False
        self.logger.debug('HC: %s deleted from api server'%self.uuid)
        return True

    # Need to be called by service chain utils to check status
    def is_hc_active(self, agent, vmi_id):
        agent_h = self.connections.agent_inspect[agent]
        agent_obj = agent_h.get_health_check(self.uuid)
        return agent_obj.is_hc_active(vmi_id)

    # Need to be called by service chain utils to verify end-to-end
    def get_health_check_ip(self, agent, vmi_id):
        agent_h = self.connections.agent_inspect[agent]
        agent_obj = agent_h.get_health_check(self.uuid)
        return agent_obj.get_hc_ip_of_vmi(vmi_id)

    # Need to be called by service chain utils to verify attributes in agent
    def verify_in_agent(self, agent):
        self.logger.info('Check HC obj %s on agent %s'%(self.uuid, agent))
        agent_h = self.connections.agent_inspect[agent]
        agent_obj = agent_h.get_health_check(self.uuid)
        if self.probe_type != agent_obj.probe_type:
            self.logger.warn('HC probe_type didnt match. Exp: %s Act: %s'%(
                              self.probe_type, agent_obj.probe_type))
            return False
        if self.delay and self.delay != int(agent_obj.delay):
            self.logger.warn('HC delay didnt match. Exp: %s Act: %s'%(
                              self.delay, agent_obj.delay))
            return False
        if self.timeout and self.timeout != int(agent_obj.timeout):
            self.logger.warn('HC timeout didnt match. Exp: %s Act: %s'%(
                              self.timeout, agent_obj.timeout))
            return False
        if self.max_retries and self.max_retries != int(agent_obj.max_retries):
            self.logger.warn('HC retries didnt match. Exp: %s Act: %s'%(
                              self.max_retries, agent_obj.max_retries))
            return False
        if self.http_url and self.http_url != agent_obj.http_url:
            self.logger.warn('HC http_url didnt match. Exp: %s Act: %s'%(
                              self.http_url, agent_obj.http_url))
            return False
        # Uncomment the below section once http_method and expected_codes
        # are implemented
        '''
        if self.http_method and self.http_method != agent_obj.http_method:
            self.logger.warn('HC http-method didnt match. Exp: %s Act: %s'%(
                              self.http_method, agent_obj.http_method))
            return False
        if self.http_codes and self.http_codes != agent_obj.http_codes:
            self.logger.warn('HC http-codes didnt match. Exp: %s Act: %s'%(
                              self.http_codes, agent_obj.http_codes))
            return False
        '''
        self.logger.info('verify_in_agent passed for HC obj %s'%self.uuid)
        return True

    # Need to be called by service chain utils to verify if removed
    def verify_not_in_agent(self, agent):
        agent_h = self.connections.agent_inspect[agent]
        if agent_h.get_health_check(self.uuid):
           self.logger.warn('HC: %s is still found in agent %s'%(
                            self.uuid, agent))
           return False
        return True
