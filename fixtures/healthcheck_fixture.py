import vnc_api_test
from tcutils.util import get_random_name, retry

class HealthCheckFixture(vnc_api_test.VncLibFixture):

    '''Fixture to handle ServiceHealthCheck object
    
    Optional:
    :param name : name of the health check (random name)
    :param uuid : UUID of the health check
    :param enabled  : Health check status default:True
    :param probe_type : Health check probe type (PING,HTTP)
    :param delay : delay in secs between probes
    :param timeout : timeout for each probe, must be < delay
    :param max_retries : max no of retries
    :param http_method : One of GET/PUT/PUSH default:GET
    :param http_url : HTTP URL Path
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
        self.name = kwargs.get('name', get_random_name('HealthCheck'))
        self.uuid = kwargs.get('uuid', None)
        self.status = kwargs.get('enabled', True)
        self.probe_type = kwargs.get('probe_type', 'PING')
        self.delay = kwargs.get('delay', None)
        self.timeout = kwargs.get('timeout', None)
        self.max_retries = kwargs.get('max_retries', None)
        self.http_method = kwargs.get('http_method', None)
        self.http_url = kwargs.get('http_url', None)
        self.http_codes = kwargs.get('http_codes', None)
        self.already_present = False

        super(HealthCheckFixture, self).setUp()
        self.parent_fq_name = [self.domain, self.project_name]
        self.fq_name = self.parent_fq_name + [self.name]
        self.parent_type = 'project'

    def setUp(self):
        super(HealthCheckFixture, self).setUp()
        self.create()

    def cleanUp(self):
        super(HealthCheckFixture, self).cleanUp()
        if (self.already_present or self.inputs.fixture_cleanup == 'no') and\
           self.inputs.fixture_cleanup != 'force':
            self.logger.info('Skipping deletion of Health Check %s :'
                              %(self.fq_name))
        else:
            self.delete()

    def read(self):
        self.logger.debug('Fetching info about Health Check %s'%self.uuid)
        self.obj= self.orch.get_health_check(id=self.uuid)
        if not self.obj:
            raise Exception('health check with id %s not found'%uuid)
        self.already_present = True
        self.name = self.obj.name
        self.fq_name = self.obj.get_fq_name()
        self.probe_type = self.obj
        self.delay = self.obj
        self.timeout = self.obj
        self.max_retries = self.obj
        self.http_method = self.obj
        self.http_url = self.obj
        self.http_codes = self.obj

    def create(self):
        self.obj = self.orch.get_health_check(fq_name=self.fq_name)
        if self.obj:
            self.uuid = self.obj.uuid
            self.read()
        else:
            self.logger.info('Creating Health Check %s'%self.name)
            self.uuid = self.orch.create_health_check(self.fq_name,
                                  self.parent_type,
                                  enabled=self.status,
                                  monitor_type=self.probe_type,
                                  delay=self.delay,
                                  timeout=self.timeout,
                                  max_retries=self.max_retries,
                                  http_method=self.http_method,
                                  url_path=self.http_url,
                                  expected_codes=self.http_codes)
            self.obj = self.orch.get_health_check(id=self.uuid)
        self.logger.info('Health Check: %s(%s), type %s'
                         %(self.name, self.uuid, self.probe_type))

    def delete(self):
        self.logger.info('Deleting Health Check %s(%s)'%(self.name, self.uuid))
        self.orch.delete_health_check(id=self.uuid)
        if getattr(self, 'verify_is_run', False):
            assert self.verify_on_cleanup()

    def update_properties(self, enabled=None, probe_type=None, delay=None,
                          timeout=None, max_retries=None, http_method=None,
                          http_url=None, http_codes=None):
        self.status = enabled or self.status
        self.probe_type = probe_type or self.probe_type
        self.delay = delay or self.delay
        self.timeout = timeout or self.timeout
        self.max_retries = max_retries or self.max_retries
        self.http_url = http_url or self.http_url
        self.http_method = http_method or self.http_method
        self.http_codes = http_codes or self.http_codes
        self.orch.update_health_check_properties(self.uuid,
                                      enabled=self.status,
                                      monitor_type=self.probe_type,
                                      delay=self.delay,
                                      timeout=self.timeout,
                                      max_retries=self.max_retries,
                                      http_method=self.http_method,
                                      url_path=self.http_url,
                                      expected_codes=self.http_codes)

    def verify_on_setup(self):
        ret = True
        ret = ret and self.verify_in_api_server()
        self.verify_is_run = True
        self.logger.info('Health Check(%s): verify_on_setup %s'%(self.uuid,
                         'passed' if ret else 'failed'))
        return ret

    def verify_on_cleanup(self):
        ret = True
        ret = ret and self.verify_not_in_api_server()
        self.logger.info('Health Check(%s): verify_on_cleanup %s'%(self.uuid,
                         'passed' if ret else 'failed'))
        return ret

    @retry(delay=2, tries=10)
    def verify_in_api_server(self):
        api_h = self.connections.api_server_inspect
        api_obj = api_h.get_service_health_check(self.uuid)
        if self.status != api_obj.status:
            self.logger.warn('HC status didnt match. Exp: %s Act: %s'%(
                              self.status, api_obj.status))
            return False
        if self.probe_type and self.probe_type != api_obj.probe_type:
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

    @retry(delay=2, tries=10)
    def verify_not_in_api_server(self):
        api_h = self.connections.api_server_inspect
        if api_h.get_service_health_check(self.uuid, refresh=True):
            self.logger.warn('HC: %s is still found in api server'%self.uuid)
            return False
        self.logger.debug('HC: %s deleted from api server'%self.uuid)
        return True

    @retry(delay=2, tries=10)
    def verify_in_agent(self, agent):
        self.logger.info('Check HC obj %s on agent %s'%(self.uuid, agent))
        agent_h = self.connections.agent_inspect[agent]
        agent_obj = agent_h.get_health_check(self.uuid)
        if self.probe_type and self.probe_type != agent_obj.probe_type:
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
        '''
        if self.http_url and self.http_url != agent_obj.http_url:
            self.logger.warn('HC http_url didnt match. Exp: %s Act: %s'%(
                              self.http_url, agent_obj.http_url))
            return False
        '''
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

    @retry(delay=2, tries=10)
    def verify_not_in_agent(self, agent):
        agent_h = self.connections.agent_inspect[agent]
        if agent_h.get_health_check(self.uuid):
           self.logger.warn('HC: %s is still found in agent %s'%(
                            self.uuid, agent))
           return False
        return True

    def verify_probe_interval(self, agent, tap_intf):
        pass

def setup_test_infra():
    import logging
    from common.contrail_test_init import ContrailTestInit
    from common.connections import ContrailConnections
    from common.log_orig import ContrailLogger
    logging.getLogger('urllib3.connectionpool').setLevel(logging.WARN)
    logging.getLogger('paramiko.transport').setLevel(logging.WARN)
    logging.getLogger('keystoneclient.session').setLevel(logging.WARN)
    logging.getLogger('keystoneclient.httpclient').setLevel(logging.WARN)
    logging.getLogger('neutronclient.client').setLevel(logging.WARN)
    logger = ContrailLogger('event')
    logger.setUp()
    mylogger = logger.logger
    inputs = ContrailTestInit('./sanity_params.ini', logger=mylogger)
    inputs.setUp()
    connections = ContrailConnections(inputs=inputs, logger=mylogger)
    return connections

def tracefunc(frame, event, arg, indent=[0]):
      if event == "call":
          indent[0] += 2
          if frame.f_code.co_name.startswith('verify_'):
              print "-" * indent[0] + "> call function", frame.f_code.co_name
      elif event == "return":
#          if frame.f_code.co_name.startswith('verify_'):
#              print "<" + "-" * indent[0], "exit function", frame.f_code.co_name, frame.f_code.co_names
          indent[0] -= 2
      return tracefunc

if __name__ == "__main__":
    import sys
    from vn_test import VNFixture
    from vm_test import VMFixture
    from floating_ip import FloatingIPFixture
#    sys.settrace(tracefunc)
    conn = setup_test_infra()
    obj = HealthCheckFixture(connections=conn, delay=5, timeout=5, max_retries=5, probe_type='PING')
    obj.setUp()
    obj.verify_on_setup()
    vnfix = VNFixture(connections=conn)
    vnfix.setUp()
    #vm_fix = VMFixture(connections=conn, vn_obj=vnfix.obj, hc_uuids=[obj.uuid])
    vm_fix = VMFixture(connections=conn, vn_obj=vnfix.obj)
    vm_fix.setUp()
    vm_fix2 = VMFixture(connections=conn, vn_obj=vnfix.obj)
    vm_fix2.setUp()
    assert vm_fix.verify_on_setup()
    assert vm_fix2.verify_on_setup()

    '''
    fip_vn_fix = VNFixture(connections=conn, router_external=True)
    fip_vn_fix.setUp()
    fip_fix = FloatingIPFixture(connections=conn, vn_id=fip_vn_fix.get_uuid())
    fip_fix.setUp()
    assert vm_fix.verify_on_setup()

    fip_id = fip_fix.create_and_assoc_fip(vm_id=vm_fix.vm_id)
    assert fip_fix.verify_fip(fip_id, vm_fix, fip_vn_fix)

    vm_fix.assoc_health_check(obj.uuid)
    vm_fix2.assoc_health_check(obj.uuid)
    assert obj.verify_in_agent(vm_fix.vm_node_ip)
    assert vm_fix.verify_health_check_in_agent()
    assert vm_fix2.verify_health_check_in_agent()
    assert fip_fix.verify_fip(fip_id, vm_fix, fip_vn_fix)

    obj2 = HealthCheckFixture(connections=conn, delay=5, timeout=5, max_retries=5, probe_type='HTTP', http_url='http://%s/test'%vm_fix.vm_ip)
    obj2.setUp()
    obj2.verify_on_setup()

    vm_fix.assoc_health_check(obj2.uuid)
    assert obj2.verify_in_agent(vm_fix.vm_node_ip)
    import time; time.sleep(25)
    assert not vm_fix.verify_health_check_in_agent()
    import pdb; pdb.set_trace()
    vm_fix.disassoc_health_check(obj2.uuid)
    import pdb; pdb.set_trace()
    vm_fix.verify_health_check_in_agent()
    fip_fix.verify_fip(fip_id, vm_fix, fip_vn_fix)
    vm_fix.disassoc_health_check(obj2.uuid)
    vm_fix.verify_health_check_in_agent()
    fip_fix.verify_fip(fip_id, vm_fix, fip_vn_fix)

    fip_fix.disassoc_and_delete_fip(fip_id)
    fip_fix.verify_no_fip(fip_id, fip_vn_fix)
    '''

    from lbaas_fixture import LBaasFixture
    lbaas_fix = LBaasFixture(name='LB', connections=conn, network_id=vnfix.uuid,
                             members={'vms': [vm_fix.vm_id, vm_fix2.vm_id]},
                             vip_net_id=vnfix.uuid, protocol='HTTP', port='80')
    lbaas_fix.setUp()
    lbaas_fix.verify_on_setup()
    lbaas_fix.assoc_health_check(obj.uuid)
    lbaas_fix.verify_on_setup()
    import pdb; pdb.set_trace()

#    vm_fix.verify_vm_in_agent()
#    vm_fix2.verify_vm_in_agent()
#    vm_fix2.run_cmd_on_vm(as_sudo=True, cmds=['echo 1 > /proc/sys/net/ipv4/icmp_echo_ignore_all'])
#    vm_fix2.disassoc_health_check(obj.uuid)

#    fip_fix.cleanUp()
#    fip_vn_fix.cleanUp()
    lbaas_fix.cleanUp()
    vm_fix.cleanUp()
    vm_fix2.cleanUp()
    vnfix.cleanUp()
    obj.cleanUp()
