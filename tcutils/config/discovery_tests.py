# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
from netaddr import IPNetwork

import fixtures
from tcutils.util import *
from netaddr import *
from time import sleep
import logging as LOG
import re
import socket
from discovery_util import DiscoveryServerUtils
import json

class DiscoveryVerification(fixtures.Fixture):

    def __init__(self, inputs, cn_inspect, agent_inspect, ops_inspect, ds_inspect, logger=LOG):

        self.inputs = inputs
        self.ops_inspect = ops_inspect
        self.agent_inspect = agent_inspect
        self.cn_inspect = cn_inspect
        self.ds_inspect = ds_inspect
        self.logger = logger
        self.ds_port = 5998
#        self.get_all_publishers_by_topology()

    def get_all_control_services_by_topology(self):

        publisher_tuple = []
        services = ['xmpp-server']
        for service in services:
            # for ip in self.inputs.bgp_ips:
            for host in self.inputs.bgp_names:
                control_ip = self.inputs.host_data[host]['host_control_ip']
                # t=(ip,service)
                t = (control_ip, service)
                publisher_tuple.append(t)
        self.logger.info(
            "Calculated control services as per the testbed file..%s" %
            (publisher_tuple))
        return publisher_tuple

    def get_all_dns_services_by_topology(self):

        publisher_tuple = []
        services = ['dns-server']
        for service in services:
            for host in self.inputs.bgp_names:
                control_ip = self.inputs.host_data[host]['host_control_ip']
                # t=(ip,service)
                t = (control_ip, service)
                publisher_tuple.append(t)
        self.logger.info(
            "Calculated dns services as per the testbed file..%s" %
            (publisher_tuple))
        return publisher_tuple

    def get_all_api_services_by_topology(self):

        publisher_tuple = []
        self.logger.info("Calculating api services as per the testbed file..")
        services = ['ApiServer']
        for service in services:
            for host in self.inputs.cfgm_names:
                control_ip = self.inputs.host_data[host]['host_control_ip']
                # t=(ip,service)
                t = (control_ip, service)
                publisher_tuple.append(t)
        self.logger.info(
            "Calculated api services as per the testbed file..%s" %
            (publisher_tuple))
        return publisher_tuple

    def get_all_ifmap_services_by_topology(self):

        publisher_tuple = []
        self.logger.info(
            "Calculating ifmap services as per the testbed file..")
        services = ['IfmapServer']
        for service in services:
            for host in self.inputs.cfgm_names:
                control_ip = self.inputs.host_data[host]['host_control_ip']
                # t=(ip,service)
                t = (control_ip, service)
                publisher_tuple.append(t)
        self.logger.info(
            "Calculated ifmap services as per the testbed file..%s" %
            (publisher_tuple))
        return publisher_tuple

    def get_all_collector_services_by_topology(self):

        publisher_tuple = []
        self.logger.info(
            "Calculating collector services as per the testbed file..")
        services = ['Collector']
        for service in services:
            for host in self.inputs.collector_names:
                control_ip = self.inputs.host_data[host]['host_control_ip']
                # t=(ip,service)
                t = (control_ip, service)
                publisher_tuple.append(t)
        self.logger.info(
            "Calculated collector services as per the testbed file..%s" %
            (publisher_tuple))
        return publisher_tuple

    def get_all_opserver_by_topology(self):

        publisher_tuple = []
        self.logger.info(
            "Calculating opserver services as per the testbed file..")
        services = ['OpServer']
        for service in services:
            for host in self.inputs.collector_names:
                control_ip = self.inputs.host_data[host]['host_control_ip']
                # t=(ip,service)
                t = (control_ip, service)
                publisher_tuple.append(t)
        self.logger.info("Calculated opserver as per the testbed file..%s" %
                         (publisher_tuple))
        return publisher_tuple

    @retry_for_value(delay=5, tries=5)
    def get_all_control_services(self, ds_ip):
        '''http://10.204.216.7:5998/services.json'''

        lst_ip_service_tuple = []
        try:
            obj = self.ds_inspect[ds_ip].get_ds_services()
            dct = obj.get_attr(
                'Service', match=('service_type', 'xmpp-server'))
            for elem in dct:
                ip = elem['info']['ip-address']
                t = (ip, 'xmpp-server')
                lst_ip_service_tuple.append(t)
        except Exception as e:
            raise
        finally:
            self.logger.info("Registered control services in discovery %s %s" %
                             (ds_ip, lst_ip_service_tuple))
            return lst_ip_service_tuple

    @retry_for_value(delay=5, tries=5)
    def get_all_collector_services(self, ds_ip):
        '''http://10.204.216.7:5998/services.json'''

        lst_ip_service_tuple = []
        try:
            obj = self.ds_inspect[ds_ip].get_ds_services()
            dct = obj.get_attr('Service', match=('service_type', 'Collector'))
            for elem in dct:
                ip = elem['info']['ip-address']
                t = (ip, 'Collector')
                lst_ip_service_tuple.append(t)
        except Exception as e:
            print e
            raise
        finally:
            self.logger.info(
                "Registered collector services in discovery %s %s" %
                (ds_ip, lst_ip_service_tuple))
            return lst_ip_service_tuple

    @retry_for_value(delay=5, tries=5)
    def get_all_api_services(self, ds_ip):
        '''http://10.204.216.7:5998/services.json'''

        lst_ip_service_tuple = []
        try:
            obj = self.ds_inspect[ds_ip].get_ds_services()
            dct = obj.get_attr('Service', match=('service_type', 'ApiServer'))
            for elem in dct:
                ip = elem['info']['ip-address']
                t = (ip, 'ApiServer')
                lst_ip_service_tuple.append(t)
        except Exception as e:
            print e
        finally:
            self.logger.info("Registered api services %s %s" %
                             (ds_ip, lst_ip_service_tuple))
            return lst_ip_service_tuple

    @retry_for_value(delay=5, tries=5)
    def get_all_ifmap_services(self, ds_ip):
        '''http://10.204.216.7:5998/services.json'''

        lst_ip_service_tuple = []
        try:
            obj = self.ds_inspect[ds_ip].get_ds_services()
            dct = obj.get_attr(
                'Service', match=('service_type', 'IfmapServer'))
            for elem in dct:
                ip = elem['info']['ip-address']
                t = (ip, 'IfmapServer')
                lst_ip_service_tuple.append(t)
        except Exception as e:
            print e
            raise
        finally:
            self.logger.info("Registered ifmap services in discovery %s %s" %
                             (ds_ip, lst_ip_service_tuple))
            return lst_ip_service_tuple

    @retry_for_value(delay=5, tries=5)
    def get_all_dns_services(self, ds_ip):
        '''http://10.204.216.7:5998/services.json'''

        lst_ip_service_tuple = []
        try:
            obj = self.ds_inspect[ds_ip].get_ds_services()
            dct = obj.get_attr('Service', match=('service_type', 'dns-server'))
            for elem in dct:
                ip = elem['info']['ip-address']
                t = (ip, 'dns-server')
                lst_ip_service_tuple.append(t)
        except Exception as e:
            print e
            raise
        finally:
            self.logger.info("Registered dns services in discovery %s %s" %
                             (ds_ip, lst_ip_service_tuple))
            return lst_ip_service_tuple

    @retry_for_value(delay=5, tries=5)
    def get_all_opserver(self, ds_ip):
        '''http://10.204.216.7:5998/services.json'''

        lst_ip_service_tuple = []
        try:
            obj = self.ds_inspect[ds_ip].get_ds_services()
            dct = obj.get_attr('Service', match=('service_type', 'OpServer'))
            for elem in dct:
                ip = elem['info']['ip-address']
                t = (ip, 'OpServer')
                lst_ip_service_tuple.append(t)
        except Exception as e:
            print e
            raise
        finally:
            self.logger.info("Registered contrail-analytics-apis in discovery %s %s" %
                             (ds_ip, lst_ip_service_tuple))
            return lst_ip_service_tuple

    def get_all_services_by_service_name(self, ds_ip, service=None):
        '''http://10.204.216.7:5998/services.json'''

        lst_ip_service_tuple = []
        dct = []
        try:
            obj = self.ds_inspect[ds_ip].get_ds_services()
            dct = obj.get_attr('Service', match=('service_type', service))
            for elem in dct:
                ip = elem['info']['ip-address']
                t = (ip, service)
                lst_ip_service_tuple.append(t)
        except Exception as e:
            print e
            raise
        finally:
            self.logger.info("Registered in discovery %s %s..%s" %
                             (ds_ip, service, lst_ip_service_tuple))
            return dct

    def publish_service_to_discovery(self, ds_ip, service=None, ip=None, port=20003, admin_state=None):
        '''http://discovery-server-ip:5998/publish'''

        obj = None
        try:
            if not admin_state:
                obj = self.ds_inspect[ds_ip].publish_service(
                    service=service, ip=ip, port=port)
            else:
                obj = self.ds_inspect[ds_ip].publish_service(
                    service=service, ip=ip, port=port, admin_state=admin_state)
        except Exception as e:
            print e
            raise
        finally:
            return obj

    def update_service(
            self,
            ds_ip,
            service=None,
            ip=None,
            admin_state=None,
            oper_state=None,
            oper_state_reason=None):
        try:
            data = {
                "service-type": service,
            }
            if oper_state:
                data['oper-state'] = oper_state
            if oper_state_reason:
                data['oper-state-reason'] = oper_state_reason
            if admin_state:
                data['admin-state'] = admin_state
            headers = {
                'Content-type': 'application/json',
            }
            service_id = self.get_service_id(ds_ip, (ip, service))
            service_id = service_id.split(':')[0]
            url = "http://%s:%s/service/%s" % (ds_ip, str(self.ds_port), service_id)
            json_body = json.dumps(data)
            resp = DiscoveryServerUtils.put_url_http(url, json_body)
        except Exception as e:
            print str(e)
        finally:
            if resp:
                print 'resp: %s' % (resp)
                return resp
    # end update_service

    def subscribe_service_from_discovery(self, ds_ip, service=None, instances=None, client_id=None):
        '''http://discovery-server-ip:5998/subscribe'''

        obj = None
        try:
            obj = self.ds_inspect[ds_ip].subscribe_service(
                service=service, instances=instances, client_id=client_id)
        except Exception as e:
            print e
            raise
        finally:
            return obj

    def cleanup_service_from_discovery(self, ds_ip):
        '''http://discovery-server-ip:5998/cleanup'''

        obj = None
        try:
            obj = self.ds_inspect[ds_ip].cleanup_service()
        except Exception as e:
            print e
            raise
        finally:
            return obj

    def get_service_status(self, ds_ip, service_tuple=()):

        ip = service_tuple[0]
        svc = service_tuple[1]
        status = None
        try:
            obj = self.ds_inspect[ds_ip].get_ds_services()
            dct = obj.get_attr('Service', match=('service_type', svc))
            for elem in dct:
                if ip in elem['info']['ip-address']:
                    status = elem['status']
                    self.logger.info("dct:%s" % (elem))
        except Exception as e:
            raise
        finally:
            return status

    def get_service_admin_state(self, ds_ip, service_tuple=()):

        ip = service_tuple[0]
        svc = service_tuple[1]
        status = None
        try:
            obj = self.ds_inspect[ds_ip].get_ds_services()
            dct = obj.get_attr('Service', match=('service_type', svc))
            for elem in dct:
                if ip in elem['info']['ip-address']:
                    status = elem['admin_state']
        except Exception as e:
            raise
        finally:
            return status

    def get_service_id(self, ds_ip, service_tuple=(), service_status='up'):

        ip = service_tuple[0]
        svc = service_tuple[1]
        status = None
        try:
            obj = self.ds_inspect[ds_ip].get_ds_services()
            dct = obj.get_attr('Service', match=('service_type', svc))
            for elem in dct:
                if ip == elem['info']['ip-address'] and elem['status'] == service_status:
                    status = elem['service_id']
        except Exception as e:
            raise
        finally:
            return status

    def get_service_in_use(self, ds_ip, service_tuple=()):

        ip = service_tuple[0]
        svc = service_tuple[1]
        status = None
        try:
            obj = self.ds_inspect[ds_ip].get_ds_services()
            dct = obj.get_attr('Service', match=('service_type', svc))
            for elem in dct:
                if ip in elem['info']['ip-address']:
                    status = elem['in_use']
        except Exception as e:
            print e
        finally:
            return status

    def get_service_prov_state(self, ds_ip, service_tuple=()):

        ip = service_tuple[0]
        svc = service_tuple[1]
        status = None
        try:
            obj = self.ds_inspect[ds_ip].get_ds_services()
            dct = obj.get_attr('Service', match=('service_type', svc))
            for elem in dct:
                if ip in elem['info']['ip-address']:
                    status = elem['prov_state']
        except Exception as e:
            print e
        finally:
            return status

    def get_service_endpoint_by_service_id(self, ds_ip, service_id=None):

        t2 = ()
        try:
            obj = self.ds_inspect[ds_ip].get_ds_services()
            dct = obj.get_attr('Service', match=('service_id', service_id))
            for elem in dct:
                t1 = (elem['info']['ip-address'], elem['info']['port'])
                t2 = (t1, elem['service_type'])
        except Exception as e:
            print e
        finally:
            return t2

    def get_service_id_by_service_end_point(self, ds_ip, service_tuple=()):
        '''Returns service id of a (service type,ip)'''

        ip = service_tuple[0]
        service = service_tuple[1]
        t2 = None
        try:
            obj = self.ds_inspect[ds_ip].get_ds_services()
            dct = obj.get_attr('Service', match=('service_type', service))
            for elem in dct:
                if (ip == elem['info']['ip-address']):
                    t2 = elem['service_id']
        except Exception as e:
            print e
        finally:
            return t2

    def get_service_status_by_service_id(self, ds_ip, service_id=None):

        t2 = {}
        try:
            obj = self.ds_inspect[ds_ip].get_ds_services()
            dct = obj.get_attr('Service', match=('service_id', service_id))
            for elem in dct:
                t1 = {}
                t1['prov_state'] = elem['prov_state']
                t2.update(t1)
                t1['admin_state'] = elem['admin_state']
                t2.update(t1)
                t1['status'] = elem['status']
                t2.update(t1)
                t1['in_use'] = elem['in_use']
                t2.update(t1)
                t1['ts_use'] = elem['ts_use']
                t2.update(t1)
        except Exception as e:
            print e
        finally:
            return t2

    def get_hostname_from_hostdata_by_ip(self, hostip):

        for elem in self.inputs.host_data.values():
            if ((elem['host_control_ip'] == hostip) | (elem['host_data_ip'] == hostip) | (elem['host_ip'] == hostip)):
                return elem['name']
        return None

    @retry_for_value(delay=5, tries=5)
    def get_subscribed_service_id(self, ds_ip, client=(), service=None , 
				instance = ''):
        '''Returns service id subscribed by a client'''

        client_ip = client[0]
        client_svc = client[1]
        service_id = []
        host_name = self.get_hostname_from_hostdata_by_ip(client_ip)
#        host_name = socket.gethostbyaddr(client_ip)[0]
        try:
            obj = self.ds_inspect[ds_ip].get_ds_clients()
            d_name = socket.gethostname().split('.')
            d_name = '.'.join(d_name[1:])
            host = host_name.split('.')[0]
            if instance:
                client_id = '%s:%s:%s' % (host, client_svc,instance)
            else:
                client_id = '%s:%s' % (host, client_svc)
            host_with_dname = host + '.' + d_name
            dct = obj.get_attr('Clients', match=('client_id', client_id))

            if not dct:
                client_id = '%s:%s:%s' % (host_with_dname, client_svc,instance)
                dct = obj.get_attr('Clients', match=('client_id', client_id))
            if not dct:
               client_id = '%s:%s' % (host, client_svc)
               dct = obj.get_attr('Clients', match=('client_id', client_id))
            if not dct:
                client_id = '%s:%s' % (host_with_dname, client_svc)
                dct = obj.get_attr('Clients', match=('client_id', client_id))
            if not dct:
                host_name = socket.gethostbyaddr(client_ip)[0]
                # nodea18.englab.juniper.net:contrail-api
                client_id = '%s:%s' % (host_name, client_svc)
                dct = obj.get_attr('Clients', match=('client_id', client_id))

            for elem in dct:
                if service in elem['service_type']:
                    client_type = elem['client_type']
                    if re.search(client_svc, client_type):
                        service_id.append(elem['service_id'])
        except Exception as e:
            print e
        finally:
            return service_id

    @retry_for_value(delay=5, tries=5)
    def get_xmpp_server_of_agent(self, ds_ip, agent_ip=None):

        control_nodes = []
        try:
            lst_service_id = self.get_subscribed_service_id(
                ds_ip, client=(agent_ip, 'contrail-vrouter-agent'), service='xmpp-server',instance = '0')
            for id in lst_service_id:
                node = self.get_service_endpoint_by_service_id(
                    ds_ip, service_id=id)
                control_nodes.append(node)
        except Exception as e:
            print e
        finally:
            return control_nodes

    def get_client_names_subscribed_to_a_service(self, ds_ip, service_tuple=()):
        return self._get_clients_subscribed_to_a_service(ds_ip, service_tuple, 
            return_type='name')

    def get_all_clients_subscribed_to_a_service(self, ds_ip, service_tuple=()):
        return self._get_clients_subscribed_to_a_service(ds_ip, service_tuple, 
            return_type='ip')

    @retry_for_value(delay=5, tries=5)
    def _get_clients_subscribed_to_a_service(self, ds_ip, service_tuple=(),
        return_type='ip'):

        clients = []
        client_names = []
        ip = service_tuple[0]
        service = service_tuple[1]
        try:
            service_id = self.get_service_id(
                ds_ip, service_tuple=service_tuple)
            obj = self.ds_inspect[ds_ip].get_ds_clients()
            dct = obj.get_attr('Clients', match=('service_id', service_id))
            for elem in dct:
                client = elem['client_id']
                cl = client.split(':')
                hostname = cl[0]
                client_names.append(client)
                client_ip = self.inputs.host_data[hostname]['host_control_ip']
                clients.append(client_ip)
        except Exception as e:
            self.logger.exception(e)
        finally:
            if return_type == 'ip':
                return clients
            else:
                return client_names
    # end 

    @retry_for_value(delay=5, tries=5)
    def get_all_client_dict_by_service_subscribed_to_a_service(self, ds_ip, subscriber_service, subscribed_service):

        ret = []
        try:
            obj = self.ds_inspect[ds_ip].get_ds_clients()
            dct = obj.get_attr(
                'Clients', match=('client_type', subscriber_service))
            for elem in dct:
                if (elem['service_type'] == subscribed_service):
                    ret.append(elem)
        except Exception as e:
            print e
        finally:
            return ret

    def dict_match(self, args_dict={}):

        for k, v in args_dict.items():
            tmp = v
            tmp_key = k
            break

        result = True
        try:
            for k, v in args_dict.items():
                if (tmp == v):
                    result = result and True
                else:
                    result = result and False
                    for elem in tmp:
                        for el in v:
                            if (elem == el):
                                tmp.remove(elem)
                                v.remove(el)
                                break
                            else:
                                self.logger.warn("Mismatch : \n%s\n\n\n %s" %
                                                 (tmp, v))
        except Exception as e:
            self.logger.warn("Got exception as %s" % (e))
            result = result and False
        finally:
            return result

    def verify_registered_services_to_discovery_service(self, ds_ip=None):

        result = True
        if not ds_ip:
            ds_ip = self.inputs.cfgm_ip

        expected_control_services = self.get_all_control_services_by_topology()
        expected_collector_services = self.get_all_collector_services_by_topology(
        )
        expected_api_services = self.get_all_api_services_by_topology()
        expected_ifmap_services = self.get_all_ifmap_services_by_topology()
        expected_opserver = self.get_all_opserver_by_topology()
        expected_dns_services = self.get_all_dns_services_by_topology()
        registered_control_services = self.get_all_control_services(ds_ip)
        registered_api_services = self.get_all_api_services(ds_ip)
        registered_ifmap_services = self.get_all_ifmap_services(ds_ip)
        registered_collector_services = self.get_all_collector_services(ds_ip)
        registered_opserver = self.get_all_opserver(ds_ip)
        registered_dns_services = self.get_all_dns_services(ds_ip)
        # checking for missing registered service
        diff = set(expected_control_services) ^ set(
            registered_control_services)
        if diff:
            self.logger.warn("Inconsistency in registerd services %s" % (diff))
            result = result and False
        else:
            self.logger.info("%s registered to discover service" %
                             (expected_control_services))
            result = result and True
        # checking for missing registered service
        diff = set(expected_collector_services) ^ set(
            registered_collector_services)
        if diff:
            self.logger.warn("Inconsistency in registerd services %s" % (diff))
            result = result and False
        else:
            self.logger.info("%s registered to discover service" %
                             (expected_collector_services))
            result = result and True
        # checking for missing registered service
        diff = set(expected_api_services) ^ set(registered_api_services)
        if diff:
            self.logger.warn("Inconsistency in registerd services %s" % (diff))
            result = result and False
        else:
            self.logger.info("%s registered to discover service" %
                             (expected_api_services))
            result = result and True
        # checking for missing registered service
        diff = set(expected_ifmap_services) ^ set(registered_ifmap_services)
        if diff:
            self.logger.warn("Inconsistency in registerd services %s" % (diff))
            result = result and False
        else:
            self.logger.info("%s registered to discover service" %
                             (expected_ifmap_services))
            result = result and True

        # checking for missing registered service
        diff = set(expected_opserver) ^ set(registered_opserver)
        if diff:
            self.logger.warn("Inconsistency in registerd services %s" % (diff))
            result = result and False
        else:
            self.logger.info("%s registered to discover service" %
                             (registered_opserver))
            result = result and True

        # checking for missing registered service
        diff = set(expected_dns_services) ^ set(registered_dns_services)
        if diff:
            self.logger.warn("Inconsistency in registerd services %s" % (diff))
            result = result and False
        else:
            self.logger.info("%s registered to discover service" %
                             (registered_dns_services))
            result = result and True

        # Verifying the service provision state/status/admin state
        self.logger.info("Checking for control node service")
        for service in registered_control_services:
            t = {}
            service_id = self.get_service_id_by_service_end_point(
                ds_ip, service_tuple=service)
            t = self.get_service_status_by_service_id(
                ds_ip, service_id=service_id)
            self.logger.info("Service health: %s" % (t))
            if (t['admin_state'] == 'up'and t['status'] == 'up'):
                self.logger.info("%s service is up" % (service,))
                result = result and True
            else:
                self.logger.warn("%s service not up" % (service,))
                result = result and False

        self.logger.info("Checking for api service")
        for service in registered_api_services:
            t = {}
            service_id = self.get_service_id_by_service_end_point(
                ds_ip, service_tuple=service)
            t = self.get_service_status_by_service_id(
                ds_ip, service_id=service_id)
            self.logger.info("Service health: %s" % (t))
            if (t['admin_state'] == 'up'and t['status'] == 'up'):
                self.logger.info("%s service is up" % (service,))
                result = result and True
            else:
                self.logger.warn("%s service not up" % (service,))
                result = result and False

        self.logger.info("Checking for ifmap service")
        for service in registered_ifmap_services:
            t = {}
            service_id = self.get_service_id_by_service_end_point(
                ds_ip, service_tuple=service)
            t = self.get_service_status_by_service_id(
                ds_ip, service_id=service_id)
            self.logger.info("Service health: %s" % (t))
            if (t['admin_state'] == 'up'and t['status'] == 'up'):
                self.logger.info("%s service is up" % (service,))
                result = result and True
            else:
                self.logger.warn("%s service not up" % (service,))
                result = result and False

        self.logger.info("Checking for collector service")
        for service in registered_collector_services:
            t = {}
            service_id = self.get_service_id_by_service_end_point(
                ds_ip, service_tuple=service)
            t = self.get_service_status_by_service_id(
                ds_ip, service_id=service_id)
            self.logger.info("Service health: %s" % (t))
            if (t['admin_state'] == 'up'and t['status'] == 'up'):
                self.logger.info("%s service is up" % (service,))
                result = result and True
            else:
                self.logger.warn("%s service not up" % (service,))
                result = result and False

        self.logger.info("Checking for dns service")
        for service in registered_dns_services:
            t = {}
            service_id = self.get_service_id_by_service_end_point(
                ds_ip, service_tuple=service)
            t = self.get_service_status_by_service_id(
                ds_ip, service_id=service_id)
            self.logger.info("Service health: %s" % (t))
            if (t['admin_state'] == 'up'and t['status'] == 'up'):
                self.logger.info("%s service is up" % (service,))
                result = result and True
            else:
                self.logger.warn("%s service not up" % (service,))
                result = result and False

        self.logger.info("Checking for opserver")
        for service in registered_opserver:
            t = {}
            service_id = self.get_service_id_by_service_end_point(
                ds_ip, service_tuple=service)
            t = self.get_service_status_by_service_id(
                ds_ip, service_id=service_id)
            self.logger.info("Service health: %s" % (t))
            if (t['admin_state'] == 'up'and t['status'] == 'up'):
                self.logger.info("%s service is up" % (service,))
                result = result and True
            else:
                self.logger.warn("%s service not up" % (service,))
                result = result and False

        return result

    @retry(delay=1, tries=10)
    def verify_bgp_connection(self, ds_ip=None):

        result = True
        if not ds_ip:
            ds_ip = self.inputs.cfgm_ip
        for host in self.inputs.host_names:
            control_ip = self.inputs.host_data[host]['host_control_ip']
            username = self.inputs.host_data[host]['username']
            password = self.inputs.host_data[host]['password']
            if host in self.inputs.compute_names:
                host_ip = self.inputs.host_data[host]['host_ip']
                # Verify the connection between compute to all control nodes
                inspect_h = self.agent_inspect[host_ip]
                agent_xmpp_status = inspect_h.get_vna_xmpp_connection_status()

                # Calculating the the expected list of bgp peer
                expected_bgp_peer = []
                if (len(self.inputs.bgp_control_ips) <= 2):
                    expected_bgp_peer = self.inputs.bgp_control_ips[:]
                else:
                    bgp_peer_tuple_from_discovery = self.get_xmpp_server_of_agent(
                                                     ds_ip, agent_ip=control_ip)
                    for t in bgp_peer_tuple_from_discovery:
                        ip = t[0][0]
                        expected_bgp_peer.append(ip)
                self.logger.info("%s compute is subscribed to %s bgp nodes" %
                                 (host, expected_bgp_peer))
                expected_bgp_peer_by_addr = []
                actual_bgp_peer = []
#
                # Get the actual list of controller IP
                for i in xrange(len(agent_xmpp_status)):
                    actual_bgp_peer.append(
                        agent_xmpp_status[i]['controller_ip'])

                # Matching the expected and actual bgp contreoller
                # sort the value for list match
                actual_bgp_peer.sort()
                expected_bgp_peer.sort()
                self.logger.info("Actual XmppServer for %s : %s" %
                                 (host, actual_bgp_peer))
                self.logger.info("Expected XmppServer for %s : %s" %
                                 (host, expected_bgp_peer))

                if actual_bgp_peer != expected_bgp_peer:
                    result = result and False
                    self.logger.error(
                        'All the required BGP controller has not found in agent introspect for %s' % (host))
                for entry in agent_xmpp_status:
                    if entry['state'] != 'Established':
                        result = result and False
                        self.logger.error(
                            'From agent %s connection to control node %s is not Established' %
                            (host, entry['controller_ip']))
            if host in self.inputs.bgp_names:
                host_ip = self.inputs.host_data[host]['host_ip']
                # Verify the connection between all control nodes
                cn_bgp_entry = self.cn_inspect[
                    host_ip].get_cn_bgp_neigh_entry()
                control_node_bgp_peer_list = []
                control_node_bgp_xmpp_peer_list = []
                if type(cn_bgp_entry) == type(dict()):
                    if cn_bgp_entry['peer'] in self.inputs.bgp_names:
                        if cn_bgp_entry['state'] != 'Established':
                            self.logger.error('For control node %s, with peer %s peering is not Established. Current State %s ' % (
                                host, cn_bgp_entry['peer'], cn_bgp_entry['state']))
                    if cn_bgp_entry['encoding'] == 'BGP':
                        control_node_bgp_peer_list = [
                            cn_bgp_entry['peer']]
                    else:
                        control_node_bgp_xmpp_peer_list = [
                            cn_bgp_entry['peer']]
                else:
                    for entry in cn_bgp_entry:
                        if entry['peer'] in self.inputs.bgp_names:
                            if entry['state'] != 'Established':
                                result = result and False
                                self.logger.error('For control node %s, with peer %s peering is not Established. Current State %s ' % (
                                    host, entry['peer'], entry['state']))
                        if entry['encoding'] == 'BGP':
                            control_node_bgp_peer_list.append(
                                entry['peer'])
                        else:
                            control_node_bgp_xmpp_peer_list.append(
                                entry['peer'])

                # Verify all required xmpp entry is present in control node
                # Get computes subscribed to this control node
                computes = self.get_client_names_subscribed_to_a_service(
                    ds_ip, service_tuple=(control_ip, 'xmpp-server'))
                computes = self._get_short_client_names(computes)
                self.logger.info("%s bgp node subscribed by %s xmpp-clients" %
                                 (control_ip, computes))
                self.logger.info(
                    "From control node introspect, xmpp-clients: %s" %
                    (control_node_bgp_xmpp_peer_list))
                
                if computes != control_node_bgp_xmpp_peer_list:
                    result = result and False
                    self.logger.error(
                        'The required XMPP entry not present in control node introspect for %s' % (host))
                    self.logger.error('Xmpp clients in discovery but not in '\
                        'control node : %s' % (
                        set(computes)-set(control_node_bgp_xmpp_peer_list)))
                    self.logger.error('Xmpp clients in Control node but not '\
                        'in discovery clients list : %s' % (
                        set(control_node_bgp_xmpp_peer_list)-set(computes)))
                # Verify all required BGP entry is present in control node
                control_node_bgp_peer_list.append(host)

                # sort the value for list match
                control_node_bgp_peer_list.sort()
                self.inputs.bgp_names.sort()
                if not set(self.inputs.bgp_names).issubset(control_node_bgp_peer_list):
                    result = result and False
                    self.logger.error(
                        'Expected BGP peers for %s:(%s), Got : (%s)' % (host,
                        self.inputs.bgp_names, control_node_bgp_peer_list))
        if not result:
            self.logger.error(
                'One or more process-states are not correct on nodes')
        return result
    # end verify_control_connection

    def _get_short_client_names(self, client_names_list):
        disc_list = []
        for item in client_names_list:
            # Remove 'contrail-tor-agent' or 'contrail-vrouter-agent'
            # client id for vrouter is of format nodek2:contrail-vrouter-agent:0
            item = item.split(':')
            if 'contrail-tor-agent' in item:
                val = '%s-%s' % (item[0], item[2])
            else:
                val = '%s' % (item[0])

            disc_list.append(val)
            disc_list.sort()
        return disc_list 
    # end _get_short_client_names
        

    def verify_agents_connected_to_dns_service(self, ds_ip=None):
        '''Verifies that agents connected to dns service'''

        result = True
        if not ds_ip:
            ds_ip = self.inputs.cfgm_ip
        for ip in self.inputs.compute_ips:
            dns_nodes = []
            try:
                lst_service_id = self.get_subscribed_service_id(
                    ds_ip, client=(ip, 'contrail-vrouter-agent'), service='dns-server',instance = '0')
                for id in lst_service_id:
                    node = self.get_service_endpoint_by_service_id(
                        ds_ip, service_id=id)
                    dns_nodes.append(node)
            except Exception as e:
                print e
            if dns_nodes:
                self.logger.info("Agent %s connected to dns-service %s" %
                                 (ip, dns_nodes))
                result = result and True
            else:
                self.logger.warn(
                    "Agent %s not connected to any dns-service" % (ip))
                return False
            self.logger.info(
                "Verifying that dns-servers belongs to this test bed")
            dns_ips = []
            for t in dns_nodes:
                dns_ip = t[0][0]
                dns_ips.append(dns_ip)
            dns_ips.sort()
            self.inputs.bgp_ips.sort()
            if (set(dns_ips).issubset(self.inputs.bgp_control_ips)):
                self.logger.info(
                    "Agent %s is connected to proper dns-servers %s" %
                    (ip, dns_ips))
                result = result and True
            else:
                self.logger.warn(
                    "Agent %s is not connected to proper dns-servers %s" % (ip, dns_ips))
                self.logger.info("Proper dns servers should be %s" %
                                 (self.inputs.bgp_ips))
                result = result and False
        return result

    def verify_agents_connected_to_collector_service(self, ds_ip=None):
        '''Verifies that agents connected to collector service'''

        result = True
        if not ds_ip:
            ds_ip = self.inputs.cfgm_ip
        for ip in self.inputs.compute_control_ips:
            collector_nodes = []
            try:
                lst_service_id = self.get_subscribed_service_id(
                    ds_ip, client=(ip, 'contrail-vrouter-agent'), service='Collector',instance = '0')
                for id in lst_service_id:
                    node = self.get_service_endpoint_by_service_id(
                        ds_ip, service_id=id)
                    collector_nodes.append(node)
            except Exception as e:
                print e
            if collector_nodes:
                self.logger.info("Agent %s connected to collector-service %s" %
                                 (ip, collector_nodes))
                result = result and True
            else:
                self.logger.warn(
                    "Agent %s not connected to any collector-service" % (ip))
                return False
            self.logger.info(
                "Verifying that collectors belongs to this test bed")
            collector_ips = []
            for t in collector_nodes:
                collector_ip = t[0][0]
                collector_ips.append(collector_ip)
            collector_ips.sort()
            self.inputs.collector_control_ips.sort()
            if (set(collector_ips).issubset(self.inputs.collector_control_ips)):
                self.logger.info(
                    "Agent %s is connected to proper collectors %s" %
                    (ip, collector_ips))
                result = result and True
            else:
                self.logger.warn(
                    "Agent %s is not connected to proper collectors %s" %
                    (ip, collector_ips))
                self.logger.info("Proper collectors should be %s" %
                                 (self.inputs.collector_ips))
                result = result and False
        return result

    def verify_dns_agent_connected_to_collector_service(self, ds_ip=None):
        '''Verifies that dns agents connected to collector service'''

        result = True
        if not ds_ip:
            ds_ip = self.inputs.cfgm_ip
        for ip in self.inputs.bgp_control_ips:
            collector_nodes = []
            try:
                lst_service_id = self.get_subscribed_service_id(
                    ds_ip, client=(ip, 'contrail-dns'), service='Collector')
                for id in lst_service_id:
                    node = self.get_service_endpoint_by_service_id(
                        ds_ip, service_id=id)
                    collector_nodes.append(node)
            except Exception as e:
                print e
            if collector_nodes:
                self.logger.info(
                    "contrail-dns %s connected to collector-service %s" %
                    (ip, collector_nodes))
                result = result and True
            else:
                self.logger.warn(
                    "contrail-dns %s not connected to any collector-service" % (ip))
                return False
            self.logger.info(
                "Verifying that collectors belongs to this test bed")
            collector_ips = []
            for t in collector_nodes:
                collector_ip = t[0][0]
                collector_ips.append(collector_ip)
            collector_ips.sort()
            self.inputs.collector_control_ips.sort()
            if (set(collector_ips).issubset(self.inputs.collector_control_ips)):
                self.logger.info(
                    "contrail-dns %s is connected to proper collectors %s" %
                    (ip, collector_ips))
                result = result and True
            else:
                self.logger.warn(
                    "contrail-dns %s is not connected to proper collectors %s" %
                    (ip, collector_ips))
                self.logger.info("Proper collectors should be %s" %
                                 (self.inputs.collector_ips))
                result = result and False
        return result

    def verify_control_nodes_connected_to_collector_service(self, ds_ip=None):
        '''Verifies that dns agents connected to collector service'''

        result = True
        if not ds_ip:
            ds_ip = self.inputs.cfgm_ip
        for ip in self.inputs.bgp_control_ips:
            collector_nodes = []
            try:
                lst_service_id = self.get_subscribed_service_id(
                    ds_ip, client=(ip, 'contrail-control'), service='Collector')
                for id in lst_service_id:
                    node = self.get_service_endpoint_by_service_id(
                        ds_ip, service_id=id)
                    collector_nodes.append(node)
            except Exception as e:
                print e
            if collector_nodes:
                self.logger.info(
                    "contrail-control %s connected to collector-service %s" %
                    (ip, collector_nodes))
                result = result and True
            else:
                self.logger.warn(
                    "contrail-control %s not connected to any collector-servicet" % (ip))
                return False
            self.logger.info(
                "Verifying that collectors belongs to this test bed")
            collector_ips = []
            for t in collector_nodes:
                collector_ip = t[0][0]
                collector_ips.append(collector_ip)
            collector_ips.sort()
            self.inputs.collector_control_ips.sort()
            if (set(collector_ips).issubset(self.inputs.collector_control_ips)):
                self.logger.info(
                    "contrail-control %s is connected to proper collectors %s" %
                    (ip, collector_ips))
                result = result and True
            else:
                self.logger.warn(
                    "contrail-control %s is not connected to proper collectors %s" % (ip, collector_ips))
                self.logger.info("Proper collectors should be %s" %
                                 (self.inputs.collector_ips))
                result = result and False
        return result

    def verify_control_nodes_subscribed_to_ifmap_service(self, ds_ip=None):
        '''Verifies that control nodes subscribed to ifmap service'''

        result = True
        if not ds_ip:
            ds_ip = self.inputs.cfgm_ip
        for host in self.inputs.bgp_names:
            host_ip = self.inputs.host_data[host]['host_ip']
            control_ip = self.inputs.host_data[host]['host_control_ip']
            subscribed_ifmap_nodes_from_discovery = []
            subscribed_ifmap_nodes_from_cn_introspect = []
            try:
                lst_service_id = self.get_subscribed_service_id(
                    ds_ip, client=(control_ip, 'contrail-control'), service='IfmapServer')
                for id in lst_service_id:
#                    uid = (id,'IfmapServer')
                    endpoint = self.get_service_endpoint_by_service_id(
                        ds_ip, service_id=id)
                    node = endpoint
                    subscribed_ifmap_nodes_from_discovery.append(node)
                l = self.cn_inspect[host_ip].get_if_map_peer_server_info(
                    match='ds_peer_info')
                for elem in subscribed_ifmap_nodes_from_discovery:
                    result1 = True
                    for elem1 in l['IFMapDSPeerInfo']['ds_peer_list']:
                        if (elem[0][0] == elem1['host'] and elem[0][1] == elem1['port']):
                            self.logger.info(
                                "contrail-control %s connected to ifmapservice %s" % (control_ip, elem1))
                            result = result and True
                            result1 = True
                            break
                        else:
                            result1 = False
                            continue
                    if not result1:
                        self.logger.warn(
                            "contrail-control %s not connected to any ifmapservice" % (control_ip))
                        result = result and False
            except Exception as e:
                result = result and False
                self.logger.warn("Got exception as %s" % e)
        return result

    def verify_dns_agent_subscribed_to_ifmap_service(self, ds_ip=None):
        '''Verifies that dns agent subscribed to ifmap service'''

        if not ds_ip:
            ds_ip = self.inputs.cfgm_ip
        result = True
        result1 = True
        for ip in self.inputs.bgp_control_ips:
            subscribed_ifmap_nodes_from_discovery = []
            subscribed_ifmap_nodes_from_cn_introspect = []
            try:
                lst_service_id = self.get_subscribed_service_id(
                    ds_ip, client=(ip, 'contrail-dns'), service='IfmapServer')
                for id in lst_service_id:
                    node = self.get_service_endpoint_by_service_id(
                        ds_ip, service_id=id)
                    subscribed_ifmap_nodes_from_discovery.append(node)
                for elem in subscribed_ifmap_nodes_from_discovery:
                    # if (self.inputs.cfgm_control_ip in elem[0][0]):
                    if (elem[0][0] in self.inputs.cfgm_control_ips):
                        self.logger.info(
                            "Dns agent %s connected to ifmapservice %s" %
                            (ip, subscribed_ifmap_nodes_from_discovery))
                        result = result and True
                        result1 = True
                        break
                    else:
                        result1 = False
                if not result1:
                    self.logger.warn(
                        "Dns agent %s not connected to any ifmapservice" % (ip))
                    result = result and False

            except Exception as e:
                self.logger.warn("Got exception as %s" % (e))
                result = result and False
        return result

    def verify_ApiServer_subscribed_to_collector_service(self, ds_ip=None):
        '''Verifies that ApiServer subscribed to collector service'''

        result = True
        if not ds_ip:
            ds_ip = self.inputs.cfgm_ip
        ip = self.inputs.cfgm_control_ip
        collector_nodes = []
        try:
            lst_service_id = self.get_subscribed_service_id(
                ds_ip, client=(ip, 'contrail-api'), service='Collector')
            for id in lst_service_id:
                node = self.get_service_endpoint_by_service_id(
                    ds_ip, service_id=id)
                collector_nodes.append(node)
        except Exception as e:
            print e
        if collector_nodes:
            self.logger.info("contrail-api %s connected to collector-service %s" %
                             (ip, collector_nodes))
            result = result and True
        else:
            self.logger.warn(
                "contrail-api %s not connected to any collector-servicet" % (ip))
            return False
        self.logger.info("Verifying that collectors belongs to this test bed")
        collector_ips = []
        for t in collector_nodes:
            collector_ip = t[0][0]
            collector_ips.append(collector_ip)
        collector_ips.sort()
        self.inputs.collector_control_ips.sort()
        if (set(collector_ips).issubset(self.inputs.collector_control_ips)):
            self.logger.info(
                "contrail-api %s is connected to proper collectors %s" %
                (ip, collector_ips))
            result = result and True
        else:
            self.logger.warn(
                "contrail-api %s is not connected to proper collectors %s" %
                (ip, collector_ips))
            self.logger.info("Proper collectors should be %s" %
                             (self.inputs.collector_ips))
            result = result and False
        return result


    def verify_daemon_subscribed_to_discovery_service(self, daemon_name, disc_svc_name):
        '''Verifies that daemon is subscribed to discovery service'''

        result = True
        dct = []
        for ip in self.inputs.cfgm_ips:
            try:
                dct = self.get_all_client_dict_by_service_subscribed_to_a_service(
                    ip, daemon_name, disc_svc_name)
                if not dct:
                    self.logger.error(
                        "No %s connected to %s  as per discovery %s" % (daemon_name, disc_svc_name, ip))
                    result = result and False
                else:
                    for elem in dct:
                        svc_id = elem['service_id']
                        node = self.get_service_endpoint_by_service_id(
                            ip, service_id=svc_id)
                        self.logger.info(
                            "%s is connected to %s as per discovery %s" %
                            (elem['client_id'], node, ip))
                        result = result and True
            except Exception as e:
                self.logger.warn(
                    "Got exception in verify_daemon_subscribed_to_discovery_service (%s, %s, %s) as %s" % (daemon_name, disc_svc_name, ip, e))
        return result

    def verify_Schema_subscribed_to_collector_service(self):
        '''Verifies that Schema subscribed to collector service'''

        return self.verify_daemon_subscribed_to_discovery_service('contrail-schema', 'Collector')

    def verify_ServiceMonitor_subscribed_to_collector_service(self):
        '''Verifies that ServiceMonitor subscribed to collector service'''

        return self.verify_daemon_subscribed_to_discovery_service('contrail-svc-monitor', 'Collector')

    def verify_webui_subscribed_to_opserver_service(self):
        '''Verifies that WebUI subscribed to OpServer service'''

        return self.verify_daemon_subscribed_to_discovery_service('ContrailWebUI', 'OpServer')

    def verify_webui_subscribed_to_apiserver_service(self):
        '''Verifies that WebUI subscribed to ApiServer service'''

        return self.verify_daemon_subscribed_to_discovery_service('ContrailWebUI', 'ApiServer')

    def cross_verification_objects_in_all_discovery(self):

        result = True
        svc_obj_lst = []
        obj = {}
        service_list = ['OpServer', 'dns-server', 'IfmapServer',
                        'ApiServer', 'xmpp-server', 'Collector']
        for svc in service_list:
            for ip in self.inputs.cfgm_ips:
                client_obj_lst = []
                dct = self.get_all_services_by_service_name(ip, service=svc)
                svc_obj_lst.append(dct)
                obj[ip] = dct
            try:
                assert self.dict_match(obj)
            except Exception as e:
                result = result and False
        return result

    def get_zookeeper_status(self, ip=None):

        zoo_keeper_status = {}
        ips = []
        if not ip:
            ips = self.inputs.cfgm_ips[:]
        else:
            ips = [ip]
        for ds_ip in ips:
            command = self.inputs.run_cmd_on_server(
                ds_ip, '/usr/lib/zookeeper/bin/zkServer.sh status', password='c0ntrail123')
            status = command.split(":")[-1]
            zoo_keeper_status[ds_ip] = status
        return zoo_keeper_status

    def modify_conf_file(self, service, section, option, value, username, password):
        cmd_set = 'openstack-config --set '
        conf_file = '/etc/contrail/' + service + '.conf '
        cmd = cmd_set + conf_file + section + ' ' + option + ' ' + str(value)
        for ip in self.inputs.cfgm_ips:
            self.inputs.run_cmd_on_server(ip, cmd, username, password)
    # end modify_conf_file
         
    def change_ttl_short_and_hc_max_miss(self, ttl_short=2, hc_max_miss=3000):
        # Changing the hc_max_miss=3000 and verifying that the services are
        # down after 25 mins
        username = self.inputs.host_data[self.inputs.cfgm_ip]['username']
        password = self.inputs.host_data[self.inputs.cfgm_ip]['password']
        self.modify_conf_file('contrail-discovery', 'DEFAULTS', 'hc_max_miss', hc_max_miss, username, password)
        self.modify_conf_file('contrail-discovery', 'DEFAULTS', 'ttl_short', ttl_short, username, password)
        conf_file = '/etc/contrail/contrail-discovery.conf '
        cmd = 'cat ' + conf_file
        for ip in self.inputs.cfgm_ips:
            out_put = self.inputs.run_cmd_on_server(ip, cmd, username, password)
            self.logger.info("%s" % (out_put))
            self.inputs.restart_service('contrail-discovery', [ip])
        time.sleep(10)
    # end change_ttl_short_and_hc_max_miss
