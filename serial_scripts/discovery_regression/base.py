import test
from common.connections import ContrailConnections
from common import isolated_creds
import threading
import time 

class BaseDiscoveryTest(test.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(BaseDiscoveryTest, cls).setUpClass()
        cls.isolated_creds = isolated_creds.IsolatedCreds(cls.__name__, \
				cls.inputs, ini_file = cls.ini_file, \
				logger = cls.logger)
        cls.isolated_creds.setUp()
        cls.project = cls.isolated_creds.create_tenant() 
        cls.isolated_creds.create_and_attach_user_to_tenant()
        cls.inputs = cls.isolated_creds.get_inputs()
        cls.connections = cls.isolated_creds.get_conections() 
        cls.quantum_h= cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib= cls.connections.vnc_lib
        cls.agent_inspect= cls.connections.agent_inspect
        cls.cn_inspect= cls.connections.cn_inspect
        cls.analytics_obj=cls.connections.analytics_obj
        cls.ds_obj = cls.connections.ds_verification_obj
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        cls.isolated_creds.delete_tenant()
        super(BaseDiscoveryTest, cls).tearDownClass()
    #end tearDownClass 

    def publish_service_with_admin_state(
            self,
            service,
            base_ip,
            port,
            admin_state='up',
            no_of_services=1):
        self.logger.info("Publishing services with admin state down...")
        threads = []
        published_service_lst = []
        for x in range(1, no_of_services + 1):
            svc_ip = base_ip + str(x)
            svc = 'svc' + str(x)
            t = threading.Thread(target=self.ds_obj.publish_service_to_discovery, args=(
                self.inputs.cfgm_ip, service, svc_ip, port, admin_state))
            threads.append(t)
        for th in threads:
            self.logger.info("Publishing service with ip %s and port %s" %
                             (svc_ip, port))
            th.start()
        for th in threads:
            th.join()
        time.sleep(5)
    # end publish_service_with_admin_state

    def verify_service_status(self, service, base_ip, no_of_services=1, expected_status='up'):
        result = True
        self.logger.info("Verifying all services are " + expected_status + "...")
        msg = ''
        if expected_status == 'up':
            unexpected_status = 'down'
        else:
            unexpected_status = 'up'
        try:
            svc = self.ds_obj.get_all_services_by_service_name(
                self.inputs.cfgm_ip, service=service)
            for elem in svc:
                ip = elem['info']['ip-address']
                elem = (ip, elem['service_type'])
                if (ip in (base_ip + str(x) for x in range(1, no_of_services + 1))):
                    self.logger.info("%s is added to discovery service" %
                                     (elem,))
                    result = result and True
                    self.logger.info("Verifying if the service is " + expected_status)
                    svc_status = self.ds_obj.get_service_status(
                        self.inputs.cfgm_ip, service_tuple=elem)
                    if (svc_status == expected_status):
                        self.logger.info("svc is " + expected_status)
                        result = result and True
                    else:
                        result = result and False
                        self.logger.error("svc is " + unexpected_status)
                        msg = msg + ' ' + str(elem) + ' is ' + unexpected_status + \
                        ', expected is ' + expected_status
                else:
                    self.logger.error("%s is NOT added to discovery service" %
                                     (elem,))
                    result = result and False
        except Exception as e:
            self.logger.exception("Got exception %s"%(e))
            raise
        return result
    # def verify_service_status
