import test
from common.introspect.base import *
from tcutils.agent.vna_introspect_utils import *
import unittest
from tcutils.wrappers import preposttest_wrapper
from compute_node_test import ComputeNodeFixture
from tcutils.ssl_certs_utils import SslCert
from tcutils.collector.opserver_introspect_utils import VerificationOpsSrvIntrospect

class IntrospectSslTest(BaseIntrospectSsl):

    @classmethod
    def setUpClass(cls):
        super(IntrospectSslTest, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(IntrospectSslTest, cls).tearDownClass()

    @preposttest_wrapper
    def test_agent_introspect(self):
        """
        Description: Test agent introspect with ssl
        Steps:
            1. create the ssl certificates for client as well as for agent
            2. enable the ssl, set the certs path in config file and restart the agent
            3. get the url with https using client certs, should succeed
            4. get the url with http, should fail
            5. match the https output with http output(with ssl disabled), both should be same
        """
        #Create the CA
        self.create_ca_cert()
        #Create client certs
        key, csr, cert = self.create_cert(subject='/CN=%s' % self.connections.project_name)

        self.set_ssl_config_in_inputs(key=key, cert=cert, ca_cert=self.ca_cert)

        host_name = self.inputs.compute_names[0]
        host_ip = self.inputs.compute_info[host_name]
        port = self.inputs.agent_port
        host_fqname = self.inputs.host_data[host_ip]['fqname']
        agent_inspect = AgentInspect(host_ip, port, self.logger,
            inputs=self.inputs)

        url_http = 'http://%s:%s' % (host_name, port)
        output_http = self.get_url_and_verify(url_http, agent_inspect)

        assert self.create_agent_certs_and_update_on_compute(host_name,
            subject='/CN=%s' % host_name, ssl_enable='true')

        url = 'https://%s:%s' % (host_name, port)
        self.get_url_and_verify(url, agent_inspect, exp_out=output_http)

        url = 'https://%s:%s' % (host_fqname, port)
        output = agent_inspect.dict_get(url=url)
        assert (output == None)

        url = 'https://%s:%s' % (host_ip, port)
        output = agent_inspect.dict_get(url=url)
        assert (output == None)

        output = agent_inspect.dict_get(url=url_http)
        assert (output == None)
    #end test_agent_introspect

    @preposttest_wrapper
    def test_introspect_cert_without_cn(self):
        """
        Description: Test introspect with ssl cert without common name
        Steps:
            1. create the ssl certificates for client as well as for agent
            2. enable the ssl, set the certs path in config file and restart the agent
            3. agent should not come up
        """
        #Create the CA
        self.create_ca_cert()
        #Create client certs
        key, csr, cert = self.create_cert(subject='/CN=%s' % self.connections.project_name)

        self.set_ssl_config_in_inputs(key=key, cert=cert, ca_cert=self.ca_cert)

        host_name = self.inputs.compute_names[0]
        host_ip = self.inputs.compute_info[host_name]
        port = self.inputs.agent_port
        host_fqname = self.inputs.host_data[host_ip]['fqname']
        agent_inspect = AgentInspect(host_ip, port, self.logger,
            inputs=self.inputs)

        url_http = 'http://%s:%s' % (host_name, port)
        output_http = self.get_url_and_verify(url_http, agent_inspect)

        assert (self.create_agent_certs_and_update_on_compute(host_ip,
            subject='/', ssl_enable='true') == False)

        subjectAltName = 'IP:%s,DNS:%s,DNS:%s' % (host_ip, host_fqname, host_name)
        assert self.create_agent_certs_and_update_on_compute(host_ip,
            subject='/', ssl_enable='true',
            subjectAltName=subjectAltName, verify_in_cleanup=False)

        url = 'https://%s:%s' % (host_name, port)
        self.get_url_and_verify(url, agent_inspect, exp_out=output_http)
    #end test_introspect_cert_without_cn

    @test.attr(type=['cb_sanity'])
    @preposttest_wrapper
    def test_agent_introspect_with_alt_names(self):
        """
        Description: Test agent introspect with ssl certificates with subjectAltName
        Steps:
            1. create the ssl certificates for client as well as for agent
            2. enable the ssl, set the certs path in config file and restart the agent
            3. get the url with https using client certs, should succeed
            4. get the url with http, should fail
            5. match the https output with http output(with ssl disabled), both should be same
        """
        #Create the CA
        self.create_ca_cert()
        #Create client certs
        key, csr, cert = self.create_cert(subject='/CN=%s' % self.connections.project_name)

        self.set_ssl_config_in_inputs(key=key, cert=cert, ca_cert=self.ca_cert)

        host_name = self.inputs.compute_names[0]
        host_ip = self.inputs.compute_info[host_name]
        port = self.inputs.agent_port
        host_fqname = self.inputs.host_data[host_ip]['fqname']
        agent_inspect = AgentInspect(host_ip, port, self.logger,
            inputs=self.inputs)

        url_http = 'http://%s:%s' % (host_name, port)
        output_http = self.get_url_and_verify(url_http, agent_inspect)

        subjectAltName = 'IP:%s,DNS:%s,DNS:%s' % (host_ip, host_fqname, host_name)
        assert self.create_agent_certs_and_update_on_compute(host_ip,
            subject='/CN=%s' % host_name, ssl_enable='true',
            subjectAltName=subjectAltName)

        url = 'https://%s:%s' % (host_name, port)
        self.get_url_and_verify(url, agent_inspect, output_http)

        url = 'https://%s:%s' % (host_fqname, port)
        self.get_url_and_verify(url, agent_inspect, output_http)

        url = 'https://%s:%s' % (host_ip, port)
        self.get_url_and_verify(url, agent_inspect, output_http)

        output = agent_inspect.dict_get(url=url_http)
        assert (output == None)
    #end test_agent_introspect_with_alt_names

    @preposttest_wrapper
    def test_introspect_single_set_certs(self):
        """
        Description: Test agent introspect with same certs for client and server
        Steps:
            1. create single set of ssl certificates
            2. enable the ssl, set the certs path in config file and restart the agent
            3. get the url with https, should succeed
            4. get the url with http, should fail
            5. match the https output with http output(with ssl disabled), both should be same
        """
        #Create the CA
        self.create_ca_cert()

        host_name = self.inputs.compute_names[0]
        host_ip = self.inputs.compute_info[host_name]
        port = self.inputs.agent_port
        host_fqname = self.inputs.host_data[host_ip]['fqname']
        agent_inspect = AgentInspect(host_ip, port, self.logger,
            inputs=self.inputs)
        service = 'contrail-vrouter-agent'
        container = self.inputs.get_container_name(host_ip, 'agent')

        url_http = 'http://%s:%s' % (host_name, port)
        output_http = self.get_url_and_verify(url_http, agent_inspect)

        subject = '/CN=%s' % host_name
        ssl_enable = 'true'
        key, csr, cert = self.create_cert(subject=subject)

        cntr = CONTRAIL_SERVICE_CONTAINER[service]
        self.inputs.copy_file_to_server(host_ip, key, self.cert_location,
            key.split('/')[-1], container=cntr)
        self.inputs.copy_file_to_server(host_ip, cert, self.cert_location,
            cert.split('/')[-1], container=cntr)
        self.inputs.copy_file_to_server(host_ip, self.ca_cert, self.cert_location,
            self.ca_cert.split('/')[-1], container=cntr)

        #Add to cleanup to delete the certs
        self.addCleanup(self.delete_cert_file, host_ip,
            self.cert_location+key.split('/')[-1], cntr)
        self.addCleanup(self.delete_cert_file, host_ip,
            self.cert_location+cert.split('/')[-1], cntr)
        self.addCleanup(self.delete_cert_file, host_ip,
            self.cert_location+self.ca_cert.split('/')[-1], cntr)

        assert self.update_config_file_and_restart_service(host_name,
            CONTRAIL_CONF_FILES[service], ssl_enable, key,
            cert, self.ca_cert, service, container, verify_service=True)

        self.set_ssl_config_in_inputs(key=key, cert=cert, ca_cert=self.ca_cert)
        agent_inspect = AgentInspect(host_ip, port, self.logger,
            inputs=self.inputs)

        url = 'https://%s:%s' % (host_name, port)
        self.get_url_and_verify(url, agent_inspect, exp_out=output_http)

        url = 'https://%s:%s' % (host_fqname, port)
        output = agent_inspect.dict_get(url=url)
        assert (output == None)

        url = 'https://%s:%s' % (host_ip, port)
        output = agent_inspect.dict_get(url=url)
        assert (output == None)

        output = agent_inspect.dict_get(url=url_http)
        assert (output == None)
    #end test_introspect_single_set_certs

    @preposttest_wrapper
    def test_introspect_self_signed_cert(self):
        """
        Description: Test agent introspect with self signed certificates
        Steps:
            1. create the ssl certificates for client as well as for agent
            2. enable the ssl, set the certs path in config file and restart the agent
            3. get the url with https using client certs, should succeed
            4. get the url with http, should fail
            5. match the https output with http output(with ssl disabled), both should be same
        """
        host_name = self.inputs.compute_names[0]
        host_ip = self.inputs.compute_info[host_name]
        port = self.inputs.agent_port
        host_fqname = self.inputs.host_data[host_ip]['fqname']
        service = 'contrail-vrouter-agent'
        container = self.inputs.get_container_name(host_ip, 'agent')
        ssl_enable = 'true'

        #Create self signed certs
        key = self.cert_location + get_random_name(self.connections.project_name) + '-privkey.pem'
        cert = self.cert_location + get_random_name(self.connections.project_name) + '-self-signed-cert.pem'
        SslCert.generate_private_key(key)
        self.check_file_dir_exists(key)
        SslCert.generate_cert(cert, key, self_signed=True, subj='/CN=%s' % host_name)
        self.check_file_dir_exists(cert)

        self.set_ssl_config_in_inputs(key=key, cert=cert, ca_cert=cert)

        agent_inspect = AgentInspect(host_ip, port, self.logger,
            inputs=self.inputs)

        cntr = CONTRAIL_SERVICE_CONTAINER[service]
        self.inputs.copy_file_to_server(host_ip, key, self.cert_location,
            key.split('/')[-1], container=cntr)
        self.inputs.copy_file_to_server(host_ip, cert, self.cert_location,
            cert.split('/')[-1], container=cntr)

        #Add to cleanup to delete the certs
        self.addCleanup(self.delete_cert_file, host_ip,
            self.cert_location+key.split('/')[-1], cntr)
        self.addCleanup(self.delete_cert_file, host_ip,
            self.cert_location+cert.split('/')[-1], cntr)

        url_http = 'http://%s:%s' % (host_name, port)
        output_http = self.get_url_and_verify(url_http, agent_inspect)

        assert self.update_config_file_and_restart_service(host_name,
            CONTRAIL_CONF_FILES[service], ssl_enable, key,
            cert, cert, service, container, verify_service=True)

        url = 'https://%s:%s' % (host_name, port)
        self.get_url_and_verify(url, agent_inspect, exp_out=output_http)

        url = 'https://%s:%s' % (host_fqname, port)
        output = agent_inspect.dict_get(url=url)
        assert (output == None)

        url = 'https://%s:%s' % (host_ip, port)
        output = agent_inspect.dict_get(url=url)
        assert (output == None)

        output = agent_inspect.dict_get(url=url_http)
        assert (output == None)
    #end test_introspect_self_signed_cert

    @preposttest_wrapper
    def test_analytics_introspect(self):
        """
        Description: Test analytics services introspect with ssl with subaltnames
        Steps:
            1. create the ssl certificates for client as well as for analytics
            2. enable the ssl, set the certs path in config file and restart the QE
            3. get the url with https using client certs, should succeed
        """
        #Create the CA
        self.create_ca_cert()
        #Create client certs
        key, csr, cert = self.create_cert(subject='/CN=%s' % self.connections.project_name)

        self.set_ssl_config_in_inputs(key=key, cert=cert, ca_cert=self.ca_cert)

        host_name = self.inputs.collector_names[0]
        host_ip = self.inputs.host_data[host_name]['host_ip']
        port = CONTRAIL_INTROSPECT_PORTS['contrail-collector']
        host_fqname = self.inputs.host_data[host_ip]['fqname']
        inspect = VerificationOpsSrvIntrospect(host_ip, port, self.logger,
            inputs=self.inputs)

        subject = '/CN=%s' % host_name
        subjectAltName = 'IP:%s,DNS:%s,DNS:%s' % (host_ip, host_fqname, host_name)
        ssl_enable = 'true'

        server_key, server_csr, server_cert = self.create_cert(
            subject=subject, subjectAltName=subjectAltName)

        services = ['contrail-query-engine', 'contrail-analytics-api', 'contrail-collector']
        for service in services:
            port = CONTRAIL_INTROSPECT_PORTS[service]
            url_http = 'http://%s:%s' % (host_name, port)
            output_http = self.get_url_and_verify(url_http, inspect)

            cntr = CONTRAIL_SERVICE_CONTAINER[service]
            container = self.inputs.get_container_name(host_ip, cntr)

            self.copy_certs_on_node(host_ip, [server_key, server_cert, self.ca_cert],
                container=cntr)
            assert self.update_config_file_and_restart_service(host_ip,
                CONTRAIL_CONF_FILES[service], ssl_enable, server_key,
                server_cert, self.ca_cert, service, container)

            url = 'https://%s:%s' % (host_name, port)
            self.get_url_and_verify(url, inspect, output_http)

            url = 'https://%s:%s' % (host_fqname, port)
            self.get_url_and_verify(url, inspect, output_http)

            url = 'https://%s:%s' % (host_ip, port)
            self.get_url_and_verify(url, inspect, output_http)
    #end test_analytics_introspect

    @preposttest_wrapper
    def test_introspect_ssl(self):
        """
        Description: Test introspect with ssl for various services
        Steps:
            1. create the ssl certificates for client as well as for server
            2. enable the ssl, set the certs path in config file and restart the service
            3. get the url with https using client certs, should succeed
            4. get the url with http, should fail
            5. match the https output with http output(with ssl disabled), both should be same
        """
        #Create the CA
        self.create_ca_cert()
        #Create client certs
        key, csr, cert = self.create_cert(subject='/CN=%s' % self.connections.project_name)

        self.set_ssl_config_in_inputs(key=key, cert=cert, ca_cert=self.ca_cert)

        service = 'contrail-svc-monitor'
        host_name = self.inputs.cfgm_names[0]
        host_ip = self.inputs.host_data[host_name]['host_ip']
        port = CONTRAIL_INTROSPECT_PORTS[service]
        host_fqname = self.inputs.host_data[host_ip]['fqname']

        subject = '/CN=%s' % host_name
        subjectAltName = 'IP:%s,DNS:%s,DNS:%s' % (host_ip, host_fqname, host_name)
        ssl_enable = 'true'

        server_key, server_csr, server_cert = self.create_cert(
            subject=subject, subjectAltName=subjectAltName)

        services = ['contrail-api', 'contrail-schema', 'contrail-svc-monitor',
            'contrail-control', 'contrail-dns']
        for service in services:
            inspect = self.get_introspect_for_service(service, host_ip)
            cntr = CONTRAIL_SERVICE_CONTAINER[service]
            container = self.inputs.get_container_name(host_ip, cntr)
            port = CONTRAIL_INTROSPECT_PORTS[service]

            url_http = 'http://%s:%s' % (host_name, port)
            output_http = inspect.dict_get(url=url_http, raw_data=True)

            cntr = CONTRAIL_SERVICE_CONTAINER[service]
            self.copy_certs_on_node(host_ip, [server_key, server_cert, self.ca_cert],
                container=cntr)
            assert self.update_config_file_and_restart_service(host_ip,
                CONTRAIL_CONF_FILES[service], ssl_enable, server_key,
                server_cert, self.ca_cert, service, container)

            url = 'https://%s:%s' % (host_name, port)
            self.get_url_and_verify(url, inspect, exp_out=output_http)

            url = 'https://%s:%s' % (host_fqname, port)
            self.get_url_and_verify(url, inspect, exp_out=output_http)

            url = 'https://%s:%s' % (host_ip, port)
            self.get_url_and_verify(url, inspect, exp_out=output_http)

            url_http = 'http://%s:%s' % (host_name, port)
            output = inspect.dict_get(url=url_http)
            assert (output == None)
    #end test_introspect_ssl

    @preposttest_wrapper
    def test_introspect_ssl_negative_cases(self):
        """
        Test negative cases for introspect with ssl
        """
        #Create the CA
        _, ca1 = self.create_ca_cert()
        #Create client certs
        key, csr, cert = self.create_cert(subject='/CN=%s' % self.connections.project_name)
        self.set_ssl_config_in_inputs(key=key, cert=cert, ca_cert=self.ca_cert)

        service = 'contrail-analytics-api'
        host_name = self.inputs.collector_names[0]
        host_ip = self.inputs.host_data[host_name]['host_ip']
        host_fqname = self.inputs.host_data[host_ip]['fqname']
        inspect = self.get_introspect_for_service(service, host_ip)
        container = self.inputs.get_container_name(host_ip, 'analytics-api')
        port = CONTRAIL_INTROSPECT_PORTS[service]

        ssl_enable = 'true'
        #case 1. Non-existent certs path
        server_cert = '/tmp/' + DEFAULT_CERT.split('/')[-1]
        server_key = '/tmp/' + DEFAULT_PRIV_KEY.split('/')[-1]
        ca_cert = '/tmp/' + DEFAULT_CA.split('/')[-1]
        assert not self.update_config_file_and_restart_service(host_ip,
            CONTRAIL_CONF_FILES[service], ssl_enable, server_key,
            server_cert, ca_cert, service, container, tries=3, delay=2)

        url = 'http://%s:%s' % (host_name, port)
        output_http = inspect.dict_get(url=url, raw_data=True)
        assert (output_http == None)
        url = 'https://%s:%s' % (host_name, port)
        output_http = inspect.dict_get(url=url, raw_data=True)
        assert (output_http == None)

        #Case 2. client cert not signed by provided CA list, https query should fail
        subject = '/CN=%s' % host_name
        subjectAltName = 'IP:%s,DNS:%s,DNS:%s' % (host_ip, host_fqname, host_name)

        #Create new CA and certs for service
        _, ca2 = self.create_ca_cert()
        server_key, server_csr, server_cert = self.create_cert(
            subject=subject, subjectAltName=subjectAltName, ca_cert=ca2)

        cntr = CONTRAIL_SERVICE_CONTAINER[service]
        self.copy_certs_on_node(host_ip, [server_key, server_cert, ca2],
            container=cntr)
        assert self.update_config_file_and_restart_service(host_ip,
            CONTRAIL_CONF_FILES[service], ssl_enable, server_key,
            server_cert, ca2, service, container, verify_in_cleanup=False)

        url_http = 'http://%s:%s' % (host_name, port)
        output_http = inspect.dict_get(url=url_http, raw_data=True)
        assert (output_http == None)
        url_http = 'https://%s:%s' % (host_name, port)
        output_http = inspect.dict_get(url=url_http, raw_data=True)
        assert (output_http == None)

        #Create client certs signed by ca2, https query should pass
        key, csr, cert = self.create_cert(subject='/CN=%s' % self.connections.project_name,
            ca_cert=ca2)
        self.set_ssl_config_in_inputs(key=key, cert=cert, ca_cert=ca2)
        inspect = self.get_introspect_for_service(service, host_ip)

        url = 'https://%s:%s' % (host_name, port)
        self.get_url_and_verify(url, inspect)
    #end test_introspect_ssl_negative_cases
