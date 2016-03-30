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
import requests
from uuid import uuid4
from tcutils.contrail_status_check import ContrailStatusChecker

from vnc_api.vnc_api import *
from vnc_api.gen.resource_xsd import *
from httplib import FOUND

from multiprocessing import Process
from OpenSSL.rand import status

class DiscoveryVerification(fixtures.Fixture):

    def __init__(self, inputs, cn_inspect, agent_inspect, ops_inspect, ds_inspect, vnc_lib, logger=LOG):

        self.inputs = inputs
        self.ops_inspect = ops_inspect
        self.agent_inspect = agent_inspect
        self.cn_inspect = cn_inspect
        self.ds_inspect = ds_inspect
        self.logger = logger
        self.vnc_lib = vnc_lib
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
            service_id = self.get_service_id(ds_ip, (ip, service), ignore_status=True)
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

    def subscribe_service_from_discovery(self, ds_ip, service=None, instances=None, client_id=None, remote_addr=None, client_type=None, min_instances=0, svc_in_use_list_present= False ,svc_in_use_list = []):
        '''http://discovery-server-ip:5998/subscribe'''

        obj = None
        try:
            obj = self.ds_inspect[ds_ip].subscribe_service(
                service=service, instances=instances, client_id=client_id, remote_addr=remote_addr, client_type=client_type, min_instances=min_instances, svc_in_use_list_present = svc_in_use_list_present, svc_in_use_list = svc_in_use_list)
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

    def get_service_id(self, ds_ip, service_tuple=(), service_status='up', ignore_status = False):

        ip = service_tuple[0]
        svc = service_tuple[1]
        status = None
        try:
            obj = self.ds_inspect[ds_ip].get_ds_services()
            dct = obj.get_attr('Service', match=('service_type', svc))
            for elem in dct:
                if ip == elem['info']['ip-address'] and elem['status'] == service_status and ignore_status ==False:
                    status = elem['service_id']
                elif ip == elem['info']['ip-address'] and ignore_status ==True:
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
    
    def get_all_xmpp_server_of_vrouter_agent(self, ds_ip):
        try:
            obj = self.ds_inspect[ds_ip].get_ds_clients()
            dct = obj.get_attr('Clients', match=('service_type', 'xmpp-server'))
            service_id = []
            for elem in dct:
                if ('contrail-vrouter-agent:0' == elem['client_type']):
                    t2 = elem['service_id']
                    service_id.append(t2)
        except Exception as e:
            print e
        finally:
            return service_id
            
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

    def modify_conf_file(self, operation, service, section, option, value, username, password):
        cmd_set = 'openstack-config ' + '--' + operation 
        conf_file = ' /etc/contrail/' + service + '.conf '
        if operation == "set":
            cmd = cmd_set + conf_file + section + ' ' + option + ' ' + '"%s"' % str(value)
        if operation == "del":
            cmd = cmd_set + conf_file + section + ' ' + option
        for ip in self.inputs.cfgm_ips:
            self.inputs.run_cmd_on_server(ip, cmd, username, password)
            
    # end modify_conf_file
         
    def change_ttl_short_and_hc_max_miss(self, ttl_short=2, hc_max_miss=3000):
        # Changing the hc_max_miss=3000 and verifying that the services are
        # down after 25 mins
        username = self.inputs.host_data[self.inputs.cfgm_ip]['username']
        password = self.inputs.host_data[self.inputs.cfgm_ip]['password']
        self.modify_conf_file('set', 'contrail-discovery', 'DEFAULTS', \
                              'ttl_short', ttl_short, username, password)
        conf_file = '/etc/contrail/contrail-discovery.conf '
        cmd = 'cat ' + conf_file
        for ip in self.inputs.cfgm_ips:
            out_put = self.inputs.run_cmd_on_server(ip, cmd, username, password)
            self.logger.info("%s" % (out_put))
            self.inputs.restart_service('contrail-discovery', [ip])
        time.sleep(10)
        
    def change_min_max_ttl(self, ttl_min=300, ttl_max=1800):
        final_status = True
        username = self.inputs.host_data[self.inputs.cfgm_ip]['username']
        password = self.inputs.host_data[self.inputs.cfgm_ip]['password']
        self.modify_conf_file('set', 'contrail-discovery', 'DEFAULTS', 'ttl_min',\
                               ttl_min, username, password)
        self.modify_conf_file('set', 'contrail-discovery', 'DEFAULTS', 'ttl_max',\
                              ttl_max, username, password)
        conf_file = '/etc/contrail/contrail-discovery.conf '
        cmd = 'cat ' + conf_file
        for ip in self.inputs.cfgm_ips:
            out_put = self.inputs.run_cmd_on_server(ip, cmd, username, password)
            self.logger.info("%s" % (out_put))
            self.inputs.restart_service('contrail-discovery', [ip])
            status = self.inputs.confirm_service_active('contrail-discovery', ip)
            if status == False:
                self.logger.info("Discovery Service on cfgm with ip as %s did not \
                 came UP after restart" % ip)
                final_status = False
        return final_status
            
        
    def add_keystone_auth_conf_file(self, auth="keystone", add_values = "True"):
        final_status = True
        username = self.inputs.host_data[self.inputs.cfgm_ip]['username']
        password = self.inputs.host_data[self.inputs.cfgm_ip]['password']
        self.modify_conf_file('set', 'contrail-discovery', 'DEFAULTS', 'auth', auth, username, password)
        ####Creating a new Section
        if add_values == "True":
            self.modify_conf_file('set', 'contrail-discovery', 'KEYSTONE', 'auth_host',\
                                   self.inputs.auth_ip , username, password)
            self.modify_conf_file('set', 'contrail-discovery', 'KEYSTONE', 'auth_protocol',\
                                   "http" , username, password)
            self.modify_conf_file('set', 'contrail-discovery', 'KEYSTONE', 'auth_port', \
                                  "35357" , username, password)
            self.modify_conf_file('set', 'contrail-discovery', 'KEYSTONE', 'admin_user', \
                                  "admin" , username, password)
            self.modify_conf_file('set', 'contrail-discovery', 'KEYSTONE', 'admin_password', \
                                  "contrail123", username, password)
            self.modify_conf_file('set', 'contrail-discovery', 'KEYSTONE', 'admin_tenant_name',\
                                   "admin" , username, password)
        conf_file = '/etc/contrail/contrail-discovery.conf '
        cmd = 'cat ' + conf_file
        for ip in self.inputs.cfgm_ips:
            out_put = self.inputs.run_cmd_on_server(ip, cmd, username, password)
            self.logger.info("%s" % (out_put))
            self.inputs.restart_service('contrail-discovery', [ip])
            status = self.inputs.confirm_service_active('contrail-discovery', ip)
            if status == False:
                self.logger.info("Discovery Service on cfgm with ip as %s did not came UP after restart" % ip)
                final_status = False
        return final_status
     
    def delete_keystone_auth_conf_file(self, auth="keystone"):
        final_status = True
        username = self.inputs.host_data[self.inputs.cfgm_ip]['username']
        password = self.inputs.host_data[self.inputs.cfgm_ip]['password']
        self.modify_conf_file('del', 'contrail-discovery', 'DEFAULTS', 'auth', \
                              auth, username, password)
        self.modify_conf_file('del', 'contrail-discovery', 'KEYSTONE', '', '', \
                              username, password)
        conf_file = '/etc/contrail/contrail-discovery.conf '
        cmd = 'cat ' + conf_file
        for ip in self.inputs.cfgm_ips:
            out_put = self.inputs.run_cmd_on_server(ip, cmd, username, password)
            self.logger.info("%s" % (out_put))
            self.inputs.restart_service('contrail-discovery', [ip])
            status = self.inputs.confirm_service_active('contrail-discovery', ip)
            if status == False:
                self.logger.info("Discovery Service on cfgm with ip as %s did not came UP after restart" % ip)
                final_status = False
        return final_status     
        
    def white_list_publishers_conf_file(self, *publisher_ips):
        final_status = True
        username = self.inputs.host_data[self.inputs.cfgm_ip]['username']
        password = self.inputs.host_data[self.inputs.cfgm_ip]['password']
        publisher_count = len(publisher_ips)
        publisher_list = ''
        for x in range(0,publisher_count):
            publisher_list = publisher_list + publisher_ips[x] + " "
        print "List of white list publishers is %s" % publisher_list
        self.modify_conf_file('set', 'contrail-discovery', 'DEFAULTS', \
                              'white_list_publish',publisher_list, username, password)
        conf_file = '/etc/contrail/contrail-discovery.conf '
        cmd = 'cat ' + conf_file
        for ip in self.inputs.cfgm_ips:
            out_put = self.inputs.run_cmd_on_server(ip, cmd, username, password)
            self.logger.info("%s" % (out_put))
            self.inputs.restart_service('contrail-discovery', [ip])
            status = self.inputs.confirm_service_active('contrail-discovery', ip)
            if status == False:
                self.logger.info("Discovery Service on cfgm with ip as %s did not came UP after restart" % ip)
                final_status = False
        return final_status
        
    def white_list_subscribers_conf_file(self, *subscriber_ips):
        final_status = True
        username = self.inputs.host_data[self.inputs.cfgm_ip]['username']
        password = self.inputs.host_data[self.inputs.cfgm_ip]['password']
        subscriber_count = len(subscriber_ips)
        subscriber_list = ''
        for x in range(0,subscriber_count):
            subscriber_list = subscriber_list + subscriber_ips[x] + " "
        print "List of white list subscribers is %s" % subscriber_list
        self.modify_conf_file('set', 'contrail-discovery', 'DEFAULTS', \
                              'white_list_subscribe',subscriber_list, username, password)
        conf_file = '/etc/contrail/contrail-discovery.conf '
        cmd = 'cat ' + conf_file
        for ip in self.inputs.cfgm_ips:
            out_put = self.inputs.run_cmd_on_server(ip, cmd, username, password)
            self.logger.info("%s" % (out_put))
            self.inputs.restart_service('contrail-discovery', [ip])
            status = self.inputs.confirm_service_active('contrail-discovery', ip)
            if status == False:
                self.logger.info("Discovery Service on cfgm with ip as %s did not came UP after restart" % ip)
                final_status = False
        return final_status     
    
    def delete_white_list(self, publish=True, subscribe=True):
        final_status = True
        username = self.inputs.host_data[self.inputs.cfgm_ip]['username']
        password = self.inputs.host_data[self.inputs.cfgm_ip]['password']
        if publish:
            self.modify_conf_file('del', 'contrail-discovery', 'DEFAULTS',\
                                   'white_list_publish','', username, password)
        if subscribe:
            self.modify_conf_file('del', 'contrail-discovery', 'DEFAULTS', \
                                  'white_list_subscribe','', username, password)
        conf_file = '/etc/contrail/contrail-discovery.conf '
        cmd = 'cat ' + conf_file
        for ip in self.inputs.cfgm_ips:
            out_put = self.inputs.run_cmd_on_server(ip, cmd, username, password)
            self.logger.info("%s" % (out_put))
            self.inputs.restart_service('contrail-discovery', [ip])
            status = self.inputs.confirm_service_active('contrail-discovery', ip)
            if status == False:
                self.logger.info("Discovery Service on cfgm with ip as %s did not came UP after restart" % ip)
                final_status = False
        return final_status
    
    def set_auto_load_balance(self, publisher_type, load_balance_flag):
        '''
        publisher-type : type of service (eg: XMPP-SERVER, DNS-SERVER, OPSERVER)
        load_balance_flag : TRUE/FALSE
        '''
        final_status = True
        username = self.inputs.host_data[self.inputs.cfgm_ip]['username']
        password = self.inputs.host_data[self.inputs.cfgm_ip]['password']
        self.modify_conf_file('set', 'contrail-discovery', publisher_type, \
                              'load-balance', load_balance_flag, username, password)
        conf_file = '/etc/contrail/contrail-discovery.conf '
        cmd = 'cat ' + conf_file
        for ip in self.inputs.cfgm_ips:
            out_put = self.inputs.run_cmd_on_server(ip, cmd, username, password)
            self.logger.info("%s" % (out_put))
            self.inputs.restart_service('contrail-discovery', [ip])
            status = self.inputs.confirm_service_active('contrail-discovery', ip)
            if status == False:
                self.logger.info("Discovery Service on cfgm with ip as %s did not came UP after restart" % ip)
                final_status = False
        return final_status
    
    def set_policy(self, publisher_type, policy):
        '''
        publisher-type : type of service (eg: XMPP-SERVER, DNS-SERVER, OPSERVER)
        policy = [load-balance | round-robin | fixed]
        '''
        final_status = True
        username = self.inputs.host_data[self.inputs.cfgm_ip]['username']
        password = self.inputs.host_data[self.inputs.cfgm_ip]['password']
        self.modify_conf_file('set', 'contrail-discovery', publisher_type,\
                               'policy', policy, username, password)
        conf_file = '/etc/contrail/contrail-discovery.conf '
        cmd = 'cat ' + conf_file
        for ip in self.inputs.cfgm_ips:
            out_put = self.inputs.run_cmd_on_server(ip, cmd, username, password)
            self.logger.info("%s" % (out_put))
            self.inputs.restart_service('contrail-discovery', [ip])
            status = self.inputs.confirm_service_active('contrail-discovery', ip)
            if status == False:
                self.logger.info("Discovery Service on cfgm with ip as %s did not came UP after restart" % ip)
                final_status = False
        return final_status
        
    def del_policy(self, publisher_type):
        '''
        publisher-type : type of service (eg: XMPP-SERVER, DNS-SERVER, OPSERVER)
        '''
        final_status = True
        username = self.inputs.host_data[self.inputs.cfgm_ip]['username']
        password = self.inputs.host_data[self.inputs.cfgm_ip]['password']
        self.modify_conf_file('del', 'contrail-discovery', publisher_type,\
                              '','', username, password)   
        conf_file = '/etc/contrail/contrail-discovery.conf '
        cmd = 'cat ' + conf_file
        for ip in self.inputs.cfgm_ips:
            out_put = self.inputs.run_cmd_on_server(ip, cmd, username, password)
            self.logger.info("%s" % (out_put))
            self.inputs.restart_service('contrail-discovery', [ip])
            status = self.inputs.confirm_service_active('contrail-discovery', ip)
            if status == False:
                self.logger.info("Discovery Service on cfgm with ip as %s did not came UP after restart" % ip)
                final_status = False
        return final_status
        
    def vnc_read_obj(self, vnc, obj_type, fq_name):
        method_name = obj_type.replace('-', '_')
        method = getattr(vnc, "%s_read" % (method_name))
        try:
            return method(fq_name=fq_name)
        except NoIdError:
            print '%s %s not found!' % (obj_type, fq_name)
        return None
    
    def match_pubsub_ep(self, ep1, ep2):
        if ep1.ep_prefix.ip_prefix != ep2.ep_prefix.ip_prefix:
            return False
        if ep1.ep_prefix.ip_prefix_len != ep2.ep_prefix.ip_prefix_len:
            return False
        if ep1.ep_type != ep2.ep_type:
            return False
        if ep1.ep_id != ep2.ep_id:
            return False
        if ep1.ep_version != ep2.ep_version:
            return False
        return True
    
    def generateUUID(self):
        return str(uuid4())
# match two rules (type DiscoveryServiceAssignmentType)
    def match_rule_entry(self, r1, r2):
        if not self.match_pubsub_ep(r1.get_publisher(), r2.get_publisher()):
            return False
        sub1 = r1.get_subscriber()
        sub2 = r2.get_subscriber()
        if len(sub1) != len(sub2):
            return False
        for i in range(len(sub1)):
            if not self.match_pubsub_ep(sub1[i], sub2[i]):
                return False
        return True
    
    def create_rule(self, fq_name, publisher_prefix, publisher_type, *subscriber_prefix_type):    
        '''Configure a rule entry to restrict the subscription
            publisher_prefix : Publisher IP with subnet in  "IP/subnet" format.
            publisher_type : Service Type to be mentioned here
            *subscriber_prefix_type : As multiple subscibers can be supported, so it is expected to
            give multiple IP/subnet and client type sequentially. This will be taken and processed as a list.
        '''
        self.logger.info("Creating rule with following values.\
            Publisher_prefix: %s , Publisher_type: %s, Subscribers details: %s"\
             % (publisher_prefix, publisher_type, subscriber_prefix_type))
        fq_name = fq_name.split(":")
        if '/' not in publisher_prefix:
            publisher_prefix += '/32'
        else:
            pass
        self.logger.debug("Publisher service type: %s" % publisher_type)
        x = publisher_prefix.split('/')
        publisher_prefix = SubnetType(x[0], int(x[1]))
        subscriber_values = list(subscriber_prefix_type)
        subscriber_number = int(len(subscriber_values) / 2)
        self.logger.info("Total number of subscribers mentioned in this rule are %d"\
                          % int(subscriber_number))
        publisher = DiscoveryPubSubEndPointType(ep_prefix = publisher_prefix,\
                                                 ep_type = publisher_type, \
                                                 ep_id = '', ep_version = '')
        subscriber_list = []
        for i in range(1,len(subscriber_values),2):
            subscriber_prefix = subscriber_values[i-1]
            subscriber_type = subscriber_values[i]
            if '/' not in subscriber_prefix:
                subscriber_prefix += '/32'
            else:
                pass
            self.logger.info("Subscriber client type: %s" % subscriber_type)
            y = subscriber_prefix.split('/')
            subscriber_prefix = SubnetType(y[0], int(y[1]))
            subscriber = DiscoveryPubSubEndPointType(ep_prefix = subscriber_prefix,\
                                                      ep_type = subscriber_type, \
                                                      ep_id = '', ep_version = '')
            subscriber_list.append(subscriber)
        try:
            rule_entry = DiscoveryServiceAssignmentType(publisher, subscriber_list)
            dsa = self.vnc_lib.discovery_service_assignment_read(fq_name = fq_name)
            rule_uuid = self.generateUUID()
            dsa_rule = DsaRule(name = rule_uuid, parent_obj = dsa, dsa_rule_entry = rule_entry)
            dsa_rule.set_uuid(rule_uuid)
            self.vnc_lib.dsa_rule_create(dsa_rule)
        except Exception as e:
            print '*** %s' % str(e)          
    
    def delete_rule(self, fq_name, publisher_prefix, publisher_type, *subscriber_prefix_type):    
        '''Delete a rule entry to free the subscriber to subscribe to any publisher in the network.
            publisher_prefix : Publisher IP with subnet in  "IP/subnet" format.
            publisher_type : Service Type to be mentioned here
            *subscriber_prefix_type : As multiple subscibers can be supported, so it is expected to
            give multiple IP/subnet and client type sequentially. This will be taken and processed as a list.
        '''
        self.logger.info("Deleting rule with following values.\
            Publisher_prefix: %s , Publisher_type: %s, Subscribers details: %s"\
             % (publisher_prefix, publisher_type, subscriber_prefix_type))
        fq_name = fq_name.split(":")
        if '/' not in publisher_prefix:
            publisher_prefix += '/32'
        else:
            pass
        self.logger.debug("Publisher service type: %s" % publisher_type)
        x = publisher_prefix.split('/')
        publisher_prefix = SubnetType(x[0], int(x[1]))
        subscriber_values = list(subscriber_prefix_type)
        subscriber_number = int(len(subscriber_values) / 2)
        self.logger.info("Total number of subscribers mentioned in this rule are %d"\
                          % int(subscriber_number))
        publisher = DiscoveryPubSubEndPointType(ep_prefix = publisher_prefix, \
                                                ep_type = publisher_type, \
                                                ep_id = '', ep_version = '')
        subscriber_list = []
        for i in range(1,len(subscriber_values),2):
            subscriber_prefix = subscriber_values[i-1]
            subscriber_type = subscriber_values[i]
            if '/' not in subscriber_prefix:
                subscriber_prefix += '/32'
            else:
                pass
            self.logger.debug("Subscriber client type: %s" % subscriber_type)
            y = subscriber_prefix.split('/')
            subscriber_prefix = SubnetType(y[0], int(y[1]))
            subscriber = DiscoveryPubSubEndPointType(ep_prefix = subscriber_prefix,\
                                                      ep_type = subscriber_type, \
                                                      ep_id = '', ep_version = '')
            subscriber_list.append(subscriber)
        try:
            rule_entry = DiscoveryServiceAssignmentType(publisher, subscriber_list)
            dsa = self.vnc_lib.discovery_service_assignment_read(fq_name = fq_name)
            dsa_rules = dsa.get_dsa_rules()
            if dsa_rules is None:
                self.logger.info('Empty DSA group!')
            for dsa_rule in dsa_rules:
                dsa_rule_obj = self.vnc_read_obj(self.vnc_lib, 'dsa-rule', dsa_rule['to'])
                entry = dsa_rule_obj.get_dsa_rule_entry()
                if self.match_rule_entry(entry, rule_entry):
                    obj = dsa_rule_obj
                    break
                else:
                    obj = None
        except Exception as e:
            print '*** %s' % str(e)
        if not obj:
                self.logger.info('Rule not found. Unchanged')       
        else:
            self.logger.info('Rule found! Deleting that rule')
            self.vnc_lib.dsa_rule_delete(id = obj.uuid)  
    
    def read_rule(self, fq_name):
        '''
        Read and print all the rules already configured on the system
        '''       
        self.logger.info("##Reading all rules!! #")
        fq_name = fq_name.split(":")
        dsa = self.vnc_read_obj(self.vnc_lib, 'discovery-service-assignment', fq_name)
        dsa_rules = dsa.get_dsa_rules()
        if dsa_rules is None:
            self.logger.info('Empty DSA group!')
            self.logger.warning("No rule configured at all")
            return
        self.logger.info('Rules (%d):' % len(dsa_rules))
        self.logger.info('----------')
        idx = 1
        for rule in dsa_rules:
            dsa_rule = self.vnc_read_obj(self.vnc_lib, 'dsa-rule', rule['to'])
            entry = dsa_rule.get_dsa_rule_entry()
            if entry:
                pub = entry.get_publisher()
                subs = entry.get_subscriber()
                self.logger.info("Total subscribers mentioned in the rule are %d" \
                                 % len(subs))
                pub_str = '%s/%d,%s,%s,%s' % \
                (pub.ep_prefix.ip_prefix, pub.ep_prefix.ip_prefix_len, pub.ep_type, \
                 pub.ep_id, pub.ep_version)
                sub_str = ['%s/%d,%s,%s,%s' % \
                (sub.ep_prefix.ip_prefix, sub.ep_prefix.ip_prefix_len, sub.ep_type,\
                  sub.ep_id, sub.ep_version) for sub in subs]
                self.logger.info("Rule: %s %s %s" % ('', pub_str, sub_str))
            idx += 1
    
    def find_rule(self, fq_name, publisher_prefix, publisher_type, *subscriber_prefix_type):
        '''
            Find a rule entry and verify if rule already exist or not in the present list.
            publisher_prefix : Publisher IP with subnet in  "IP/subnet" format.
            publisher_type : Service Type to be mentioned here
            *subscriber_prefix_type : As multiple subscibers can be supported, so it is expected to
            give multiple IP/subnet and client type sequentially. This will be taken and processed as a list.
        '''
        self.logger.info("Searching the rule with following values.\
        Publisher_prefix: %s , Publisher_type: %s, Subscribers details: %s" % \
        (publisher_prefix, publisher_type, subscriber_prefix_type))
        rule_found = False        
        fq_name = fq_name.split(":")
        if '/' not in publisher_prefix:
            publisher_prefix += '/32'
        x = publisher_prefix.split('/')
        publisher_prefix = SubnetType(x[0], int(x[1]))
        subscriber_values = list(subscriber_prefix_type)
        subscriber_number = int(len(subscriber_values) / 2)
        publisher = DiscoveryPubSubEndPointType(ep_prefix = publisher_prefix, \
                                                ep_type = publisher_type, \
                                                ep_id = '', ep_version = '')
        subscriber_list = []
        for i in range(1,len(subscriber_values),2):
            subscriber_prefix = subscriber_values[i-1]
            subscriber_type = subscriber_values[i]
            if '/' not in subscriber_prefix:
                subscriber_prefix += '/32'
            y = subscriber_prefix.split('/')
            subscriber_prefix = SubnetType(y[0], int(y[1]))
            subscriber = DiscoveryPubSubEndPointType(ep_prefix = subscriber_prefix,\
                                                      ep_type = subscriber_type, \
                                                      ep_id = '', ep_version = '')
            subscriber_list.append(subscriber)
        try:
            rule_entry = DiscoveryServiceAssignmentType(publisher, subscriber_list)
            dsa = self.vnc_lib.discovery_service_assignment_read(fq_name = fq_name)
            dsa_rules = dsa.get_dsa_rules()
        except Exception as e:
            print '*** %s' % str(e)
        dsa_rules = dsa.get_dsa_rules()
        if dsa_rules is None:
            self.logger.info('Empty DSA group!')
            return rule_found
        for dsa_rule in dsa_rules:
            dsa_rule_obj = self.vnc_read_obj(self.vnc_lib, 'dsa-rule', dsa_rule['to'])
            entry = dsa_rule_obj.get_dsa_rule_entry()
            if self.match_rule_entry(entry, rule_entry):
                self.logger.info("Searched rule found.")
                rule_found = True
        if rule_found == False:
            self.logger.info("Searched rule not found")
        return rule_found
    
    def verify_client_subscription_to_expected_publisher(self, ds_ip, client_type,\
                                                          client_ip, service_type):
        ### It is always expected that clients and services will be in same network after the rule ####
        result = True
        if not ds_ip:
            ds_ip = self.inputs.cfgm_ip            
        svc_list = self.get_subscribed_service_id(ds_ip, (client_ip, client_type),\
                                                   service = service_type) ### returns list of service_id
        self.logger.debug("Testing for client %s running on %s" % (client_type,client_ip))
        if len(svc_list) == 0:
            result = False
            self.logger.error("No service ID found for mentioned client details as client do not exist")
            return result
        ####### Finding subscriber netwrok ##
        expected_pub_network = client_ip.split('.')
        expected_pub_network[3] = '0'
        expected_pub_network= ".".join(expected_pub_network)
        ######## Finding Publisher netwrok ###
        print expected_pub_network
        publisher_nodes = []
        for elem in svc_list:
            node = self.get_service_endpoint_by_service_id(ds_ip, service_id=elem)
            publisher_nodes.append(node)
        publisher_node_ips = []
        for i in range(0,len(publisher_nodes)):
            ip = publisher_nodes[i][0][0]
            publisher_node_ips.append(ip)
        publisher_networks = []
        for elem in publisher_node_ips:
            publisher_net = elem.split('.')
            publisher_net[3] = '0'
            publisher_net = ".".join(publisher_net)
            publisher_networks.append(publisher_net)
            if publisher_net != expected_pub_network:
                self.logger.error("# Client not subscribed to expected subscriber ##")
                result = False
        self.logger.debug("Expected publisher was from network : %s " \
                          % expected_pub_network)
        self.logger.debug("Actual publishers were from network : %s" \
                          % publisher_networks)
        if result == True:
            self.logger.info("The client (%s,%s) is subscribed to %i publisher of type %s under same network" % (client_type,client_ip,len(publisher_networks),service_type))
        if result == False:
            self.logger.error("The client (%s,%s) is subscribed to %i publisher of type %s which are under different networks" % (client_type,client_ip,len(publisher_networks),service_type))
        return result
    
    def check_load_balance(self, ds_ip, service_type):
        if not ds_ip:
            ds_ip = self.inputs.cfgm_ip
        result=True
        if service_type == "IfmapServer":
            all_service_list = self.get_all_ifmap_services(ds_ip)
        elif service_type == "xmpp-server":
            all_service_list = self.get_all_control_services(ds_ip)
        elif service_type == "dns-server":
            all_service_list = self.get_all_dns_services(ds_ip)
        elif service_type == "Collector":
            all_service_list = self.get_all_collector_services(ds_ip)
        elif service_type == "ApiServer":
            all_service_list = self.get_all_api_services(ds_ip)
        elif service_type == "OpServer":
            all_service_list = self.get_all_opserver(ds_ip)
        else:
            all_service_list = None
            self.logger.warn("No such publisher exist. Cannot verify for load balance")
            result == False
            return result
        list_in_use_all_pub = []
        for elem in all_service_list:
            get_in_use = int(self.get_service_in_use(ds_ip, (elem[0],elem[1])))
            list_in_use_all_pub.append(get_in_use)
            self.logger.debug("Service %s with IP %s is holding %i instances of subscribers" \
                              % (elem[1],elem[0],get_in_use))
        sum_of_in_use = sum(list_in_use_all_pub)
        avg_in_use = sum_of_in_use / len(list_in_use_all_pub)
        for elem in list_in_use_all_pub:
            if elem == avg_in_use or elem == avg_in_use+1 or elem == avg_in_use-1:
                pass
            else:
                self.logger.error("The load is not balanced")
                self.logger.error("The average load on server based on total number of in use subscribers is %d but load on a specific server is %s" % (avg_in_use,elem))
                result = False
                return result
        self.logger.info("The load is balanced")
        return result
        
    def publish_requests_with_keystone(self, ds_ip, operation, service_type, \
                                       service_id, operation_status = "up" ):
        DEFAULT_HEADERS = {'Content-type': 'application/json; charset="UTF-8"'}
        headers = DEFAULT_HEADERS.copy()
        headers['X-AUTH-TOKEN'] = self.vnc_lib.get_auth_token()    
        print 'Service type %s, id %s' % (service_type, service_id)
        data = {}
        data["service-type"]= service_type
        if operation == "oper-state":
            data['oper-state'] = operation_status
        if operation == "oper-state-reason":
            data['oper-state-reason'] = operation_status
        if operation == "admin-state":
            data['admin-state'] = operation_status
        if operation != "load-balance":
            url = "http://%s:%s/service/%s" % (ds_ip, '5998', service_id)
            r = requests.put(url, data=json.dumps(data), headers=headers)
        elif operation == "load-balance":
            url = "http://%s:%s/load-balance/%s" % (ds_ip, '5998', service_type)
            r = requests.post(url, headers=headers)
        if r.status_code != 200:
            print "Request Fail!! Operation status %d" % r.status_code
        return r.status_code
            
    def verify_rule_creation_delete_read(self, ds_ip=None):
        result = True
        if not ds_ip:
            ds_ip = self.inputs.cfgm_ip
        if len(self.inputs.cfgm_control_ip) > 0:
            self.logger.info("Creating rules corresponding to xmpp-server and dns-server running on all config nodes for vrouter agent running in same subnets")
        for i in range(0,len(self.inputs.cfgm_control_ips)):
            cfgm_control_ip = self.inputs.cfgm_control_ips[i].split('.')
            cfgm_control_ip[3] = '0'
            cfgm_control_ip = ".".join(cfgm_control_ip) + "/24"
            self.create_rule('default-discovery-service-assignment', cfgm_control_ip,\
                              'xmpp-server', cfgm_control_ip, 'contrail-vrouter-agent:0')
            self.create_rule('default-discovery-service-assignment', cfgm_control_ip,\
                              'dns-server', cfgm_control_ip, 'contrail-vrouter-agent:0')
        self.read_rule('default-discovery-service-assignment')
        for i in range(0,len(self.inputs.cfgm_control_ips)): 
            cfgm_control_ip = self.inputs.cfgm_control_ips[i].split('.')
            cfgm_control_ip[3] = '0'
            cfgm_control_ip = ".".join(cfgm_control_ip) + "/24"
            result1 = self.find_rule('default-discovery-service-assignment', \
                                     cfgm_control_ip, 'xmpp-server', cfgm_control_ip, 'contrail-vrouter-agent:0')
            if result1 == False:
                self.logger.error("While searching for the configured rule, it was not found. Configuration failed")
                result = False
            result2 = self.find_rule('default-discovery-service-assignment', \
                                     cfgm_control_ip, 'dns-server', cfgm_control_ip, 'contrail-vrouter-agent:0')
            if result2 == False:
                self.logger.error("While searching for the configured rule, it was not found. Configuration failed")
                result = False
        for i in range(0,len(self.inputs.cfgm_control_ips)): 
            cfgm_control_ip = self.inputs.cfgm_control_ips[i].split('.')
            cfgm_control_ip[3] = '0'
            cfgm_control_ip = ".".join(cfgm_control_ip) + "/24"
            self.delete_rule('default-discovery-service-assignment', \
                             cfgm_control_ip, 'xmpp-server', cfgm_control_ip, 'contrail-vrouter-agent:0')
            self.delete_rule('default-discovery-service-assignment', \
                             cfgm_control_ip, 'dns-server', cfgm_control_ip, 'contrail-vrouter-agent:0')
        self.read_rule("default-discovery-service-assignment")
        for i in range(0,len(self.inputs.cfgm_control_ips)): 
            cfgm_control_ip = self.inputs.cfgm_control_ips[i].split('.')
            cfgm_control_ip[3] = '0'
            cfgm_control_ip = ".".join(cfgm_control_ip) + "/24"
            result1 = self.find_rule('default-discovery-service-assignment',\
                                      cfgm_control_ip, 'xmpp-server', cfgm_control_ip, 'contrail-vrouter-agent:0')
            if result1 == True:
                self.logger.error("While searching for the deleted rule, it was found. Deletion failed")
                result = False
            result2 = self.find_rule('default-discovery-service-assignment',\
                                      cfgm_control_ip, 'dns-server', cfgm_control_ip, 'contrail-vrouter-agent:0')
            if result2 == True:
                self.logger.error("While searching for the deleted rule, it was found. Deletion failed")
                result = False  
        return result
    
    def verify_rule_xmpp_server_vrouter_agent(self, ds_ip=None):
        result = True
        if not ds_ip:
            ds_ip = self.inputs.cfgm_ip
        self.logger.debug("#### Changing min and max TTL values for testing purpose ##")
        self.change_min_max_ttl(ttl_min=60, ttl_max=60)
        self.logger.info("#### Restarting the required subscriber services so that TTL takes effect immediately ###")
        for ip in self.inputs.compute_ips:
            self.inputs.restart_service('contrail-vrouter-agent', [ip])
        for ip in self.inputs.compute_ips:
            client_status = self.inputs.confirm_service_active('contrail-vrouter-agent', ip)
            if client_status == False:
                self.logger.error("Some issue happened after restart of client process")
                result = False
                return result     
        if len(self.inputs.bgp_control_ips) > 0:
            self.logger.info("Creating rules corresponding to *xmpp-server* running on all config nodes for *vrouter agent* running in same subnets")
        for i in range(0,len(self.inputs.bgp_control_ips)):
            bgp_control_ip = self.inputs.bgp_control_ips[i].split('.')
            bgp_control_ip[3] = '0'
            bgp_control_ip = ".".join(bgp_control_ip) + "/24"
            self.create_rule('default-discovery-service-assignment', bgp_control_ip,\
                              'xmpp-server', bgp_control_ip, 'contrail-vrouter-agent:0')
        self.read_rule('default-discovery-service-assignment')
        for i in range(0,len(self.inputs.bgp_control_ips)): 
            bgp_control_ip = self.inputs.bgp_control_ips[i].split('.')
            bgp_control_ip[3] = '0'
            bgp_control_ip = ".".join(bgp_control_ip) + "/24"
            result1 = self.find_rule('default-discovery-service-assignment', bgp_control_ip,\
                                      'xmpp-server', bgp_control_ip, 'contrail-vrouter-agent:0')
            if result1 == False:
                self.logger.error("While searching for the configured rule, it was not found. Configuration failed")
                result = False
        self.logger.info("#### Waiting for 60 seconds so that TTL expiry for all subscriber happens ###")
        sleep (60)
        self.logger.debug("#### Verifying clients subscribed to publishers ###")
        try:
            for i in range(0,len(self.inputs.compute_control_ips)):
                verification = self.verify_client_subscription_to_expected_publisher\
                (ds_ip, 'contrail-vrouter-agent:0', self.inputs.compute_control_ips[i], 'xmpp-server')
                if verification == False:
                    result = False
        except Exception as e:
            print '*** %s' % str(e)          
        for i in range(0,len(self.inputs.bgp_control_ips)): 
            bgp_control_ip = self.inputs.bgp_control_ips[i].split('.')
            bgp_control_ip[3] = '0'
            bgp_control_ip = ".".join(bgp_control_ip) + "/24"
            self.delete_rule('default-discovery-service-assignment', bgp_control_ip,\
                              'xmpp-server', bgp_control_ip, 'contrail-vrouter-agent:0')
        self.read_rule("default-discovery-service-assignment")
        for i in range(0,len(self.inputs.bgp_control_ips)): 
            bgp_control_ip = self.inputs.bgp_control_ips[i].split('.')
            bgp_control_ip[3] = '0'
            bgp_control_ip = ".".join(bgp_control_ip) + "/24"
            result1 = self.find_rule('default-discovery-service-assignment', bgp_control_ip,\
                                      'xmpp-server', bgp_control_ip, 'contrail-vrouter-agent:0')
            if result1 == True:
                self.logger.error("While searching for the deleted rule, it was found. Deletion failed")
                result = False
        self.logger.debug("#### Changing min and max TTL values to default after test completion ##")
        self.change_min_max_ttl()
        return result
         
    def verify_rule_dns_server_vrouter_agent(self, ds_ip=None):
        result = True
        if not ds_ip:
            ds_ip = self.inputs.cfgm_ip
        self.logger.debug("#### Changing min and max TTL values for testing purpose ##")
        self.change_min_max_ttl(ttl_min=60, ttl_max=60)
        self.logger.info("#### Restarting the required subscriber services so that TTL takes effect immediately ###")
        for ip in self.inputs.compute_ips:
            self.inputs.restart_service('contrail-vrouter-agent', [ip])
        for ip in self.inputs.compute_ips:
            client_status = self.inputs.confirm_service_active('contrail-vrouter-agent', ip)
            if client_status == False:
                self.logger.error("Some issue happened after restart of client process")
                result = False
                return result    
        if len(self.inputs.bgp_control_ips) > 0:
            self.logger.info("Creating rules corresponding to *dns-server* running on all config nodes for *vrouter agent* running in same subnets")
        for i in range(0,len(self.inputs.bgp_control_ips)):
            bgp_control_ip = self.inputs.bgp_control_ips[i].split('.')
            bgp_control_ip[3] = '0'
            bgp_control_ip = ".".join(bgp_control_ip) + "/24"
            self.create_rule('default-discovery-service-assignment', bgp_control_ip, \
                             'dns-server', bgp_control_ip, 'contrail-vrouter-agent:0')
        self.read_rule('default-discovery-service-assignment')
        for i in range(0,len(self.inputs.bgp_control_ips)): 
            bgp_control_ip = self.inputs.bgp_control_ips[i].split('.')
            bgp_control_ip[3] = '0'
            bgp_control_ip = ".".join(bgp_control_ip) + "/24"
            result1 = self.find_rule('default-discovery-service-assignment', bgp_control_ip,\
                                      'dns-server', bgp_control_ip, 'contrail-vrouter-agent:0')
            if result1 == False:
                self.logger.error("While searching for the configured rule, it was not found. Configuration failed")
                result = False
        self.logger.info("#### Waiting for 60 seconds so that TTL expiry for all subscriber happens ###")
        sleep (60)
        self.logger.debug("#### Verifying clients subscribed to publishers ###")
        try:
            for i in range(0,len(self.inputs.compute_control_ips)):
                verification = self.verify_client_subscription_to_expected_publisher\
                (ds_ip, 'contrail-vrouter-agent:0', self.inputs.compute_control_ips[i], 'dns-server')
                if verification == False:
                    result = False
        except Exception as e:
            print '*** %s' % str(e)           
        for i in range(0,len(self.inputs.bgp_control_ips)): 
            bgp_control_ip = self.inputs.bgp_control_ips[i].split('.')
            bgp_control_ip[3] = '0'
            bgp_control_ip = ".".join(bgp_control_ip) + "/24"
            self.delete_rule('default-discovery-service-assignment', bgp_control_ip, \
                             'dns-server', bgp_control_ip, 'contrail-vrouter-agent:0')
        self.read_rule("default-discovery-service-assignment")
        for i in range(0,len(self.inputs.bgp_control_ips)): 
            bgp_control_ip = self.inputs.bgp_control_ips[i].split('.')
            bgp_control_ip[3] = '0'
            bgp_control_ip = ".".join(bgp_control_ip) + "/24"
            result1 = self.find_rule('default-discovery-service-assignment', bgp_control_ip,\
                                      'dns-server', bgp_control_ip, 'contrail-vrouter-agent:0')
            if result1 == True:
                self.logger.error("While searching for the deleted rule, it was found. Deletion failed")
                result = False
        self.logger.debug("#### Changing min and max TTL values to default after test completion ##")
        self.change_min_max_ttl()
        return result
    
    def verify_rule_ifmap_server_control_client(self, ds_ip=None):
        result = True
        if not ds_ip:
            ds_ip = self.inputs.cfgm_ip
        self.logger.debug("#### Changing min and max TTL values for testing purpose ##")
        self.change_min_max_ttl(ttl_min=60, ttl_max=60)  
        self.logger.info("#### Restarting the required subscriber services so that TTL takes effect immediately ###")
        for ip in self.inputs.bgp_ips:
            self.inputs.restart_service('contrail-control', [ip])
        for ip in self.inputs.bgp_ips:
            client_status = self.inputs.confirm_service_active('contrail-control', ip)
            if client_status == False:
                self.logger.error("Some issue happened after restart of client process")
                result = False
                return result    
        if len(self.inputs.cfgm_control_ips) > 0:
            self.logger.info("Creating rules corresponding to *IfmapServer* running on all control nodes for *contrail-control* running in same subnets")
        for i in range(0,len(self.inputs.cfgm_control_ips)):
            cfgm_control_ip = self.inputs.cfgm_control_ips[i].split('.')
            cfgm_control_ip[3] = '0'
            cfgm_control_ip = ".".join(cfgm_control_ip) + "/24"
            self.create_rule('default-discovery-service-assignment', cfgm_control_ip, \
                             'IfmapServer', cfgm_control_ip, 'contrail-control')
        self.read_rule('default-discovery-service-assignment')
        for i in range(0,len(self.inputs.cfgm_control_ips)): 
            cfgm_control_ip = self.inputs.cfgm_control_ips[i].split('.')
            cfgm_control_ip[3] = '0'
            cfgm_control_ip = ".".join(cfgm_control_ip) + "/24"
            result1 = self.find_rule('default-discovery-service-assignment', cfgm_control_ip,\
                                      'IfmapServer', cfgm_control_ip, 'contrail-control')
            if result1 == False:
                self.logger.error("While searching for the configured rule, it was not found. Configuration failed")
                result = False
        self.logger.info("#### Waiting for 60 seconds so that TTL expiry for all subscriber happens ###")
        sleep (60)
        self.logger.debug("#### Verifying clients subscribed to publishers ###")
        try:
            for i in range(0,len(self.inputs.bgp_control_ips)):
                verification = self.verify_client_subscription_to_expected_publisher\
                (ds_ip, 'contrail-control', self.inputs.bgp_control_ips[i], 'IfmapServer')
                if verification == False:
                    self.logger.error("Rule not behaving as expected")
                    result = False
        except Exception as e:
            print '*** %s' % str(e)            
        for i in range(0,len(self.inputs.cfgm_control_ips)): 
            cfgm_control_ip = self.inputs.cfgm_control_ips[i].split('.')
            cfgm_control_ip[3] = '0'
            cfgm_control_ip = ".".join(cfgm_control_ip) + "/24"
            self.delete_rule('default-discovery-service-assignment', cfgm_control_ip, \
                             'IfmapServer', cfgm_control_ip, 'contrail-control')
        self.read_rule("default-discovery-service-assignment")
        for i in range(0,len(self.inputs.cfgm_control_ips)): 
            cfgm_control_ip = self.inputs.cfgm_control_ips[i].split('.')
            cfgm_control_ip[3] = '0'
            cfgm_control_ip = ".".join(cfgm_control_ip) + "/24"
            result1 = self.find_rule('default-discovery-service-assignment', cfgm_control_ip, \
                                     'IfmapServer', cfgm_control_ip, 'contrail-control')
            if result1 == True:
                self.logger.error("While searching for the deleted rule, it was found. Deletion failed")
                result = False
        self.logger.debug("#### Changing min and max TTL values to default after test completion ##")
        self.change_min_max_ttl()
        return result
    
         
    def verify_rule_op_server_webui_client(self, ds_ip=None):
        result = True
        if not ds_ip:
            ds_ip = self.inputs.cfgm_ip
        self.logger.debug("#### Changing min and max TTL values for testing purpose ##")
        self.change_min_max_ttl(ttl_min=60, ttl_max=60)        
        self.logger.info("#### Restarting the required subscriber services so that TTL takes effect immediately ###")
        for ip in self.inputs.webui_ips:
            self.inputs.restart_service('supervisor-webui', [ip])
        for ip in self.inputs.webui_ips:
            client_status = self.inputs.confirm_service_active('supervisor-webui', ip)
            if client_status == False:
                self.logger.error("Some issue happened after restart of client process")
                result = False
                return result    
        if len(self.inputs.collector_control_ips) > 0:
            self.logger.info("Creating rules corresponding to *OpServer* running on all control nodes for *contrailWebUI* running in same subnets")
        for i in range(0,len(self.inputs.collector_control_ips)):
            collector_control_ip = self.inputs.collector_control_ips[i].split('.')
            collector_control_ip[3] = '0'
            collector_control_ip = ".".join(collector_control_ip) + "/24"
            self.create_rule('default-discovery-service-assignment', collector_control_ip,\
                              'OpServer', collector_control_ip, 'contrailWebUI')
        self.read_rule('default-discovery-service-assignment')
        for i in range(0,len(self.inputs.collector_control_ips)): 
            collector_control_ip = self.inputs.collector_control_ips[i].split('.')
            collector_control_ip[3] = '0'
            collector_control_ip = ".".join(collector_control_ip) + "/24"
            result1 = self.find_rule('default-discovery-service-assignment', \
                                     collector_control_ip, 'OpServer', collector_control_ip, 'contrailWebUI')
            if result1 == False:
                self.logger.error("While searching for the configured rule, it was not found. Configuration failed")
                result = False       
        self.logger.info("#### Waiting for 60 seconds so that TTL expiry for all subscriber happens ###")
        sleep (60)
        self.logger.debug("#### Verifying clients subscribed to publishers ###")
        try:
            for i in range(0,len(self.inputs.webui_control_ips)):
                verification = self.verify_client_subscription_to_expected_publisher\
                (ds_ip, 'contrailWebUI', self.inputs.webui_control_ips[i], 'OpServer')
                if verification == False:
                    self.logger.error("Rule not behaving as expected")
                    result = False
        except Exception as e:
            print '*** %s' % str(e)           
        for i in range(0,len(self.inputs.collector_control_ips)): 
            collector_control_ip = self.inputs.collector_control_ips[i].split('.')
            collector_control_ip[3] = '0'
            collector_control_ip = ".".join(collector_control_ip) + "/24"
            self.delete_rule('default-discovery-service-assignment', collector_control_ip,\
                              'OpServer', collector_control_ip, 'contrailWebUI')
        self.read_rule("default-discovery-service-assignment")
        for i in range(0,len(self.inputs.collector_control_ips)): 
            collector_control_ip = self.inputs.collector_control_ips[i].split('.')
            collector_control_ip[3] = '0'
            collector_control_ip = ".".join(collector_control_ip) + "/24"
            result1 = self.find_rule('default-discovery-service-assignment', \
                                     collector_control_ip, 'OpServer', collector_control_ip, 'contrailWebUI')
            if result1 == True:
                self.logger.error("While searching for the deleted rule, it was found. Deletion failed")
                result = False
        self.logger.debug("#### Changing min and max TTL values to default after test completion ##")
        self.change_min_max_ttl()
        return result
    
    def verify_rule_api_server_webui_client(self, ds_ip=None):
        result = True
        if not ds_ip:
            ds_ip = self.inputs.cfgm_ip
        self.logger.debug("#### Changing min and max TTL values for testing purpose ##")
        self.change_min_max_ttl(ttl_min=60, ttl_max=60)        
        self.logger.info("#### Restarting the required subscriber services so that TTL takes effect immediately ###")
        for ip in self.inputs.webui_ips:
            self.inputs.restart_service('supervisor-webui', [ip])
        for ip in self.inputs.webui_ips:
            client_status = self.inputs.confirm_service_active('supervisor-webui', ip)
            if client_status == False:
                self.logger.error("Some issue happened after restart of client process")
                result = False
                return result    
        if len(self.inputs.cfgm_control_ips) > 0:
            self.logger.info("Creating rules corresponding to *ApiServer* running on all control nodes for *contrailWebUI* running in same subnets")
        for i in range(0,len(self.inputs.cfgm_control_ips)):
            cfgm_control_ip = self.inputs.cfgm_control_ips[i].split('.')
            cfgm_control_ip[3] = '0'
            cfgm_control_ip = ".".join(cfgm_control_ip) + "/24"
            self.create_rule('default-discovery-service-assignment', cfgm_control_ip,\
                              'ApiServer', cfgm_control_ip, 'contrailWebUI')
        self.read_rule('default-discovery-service-assignment')
        for i in range(0,len(self.inputs.cfgm_control_ips)): 
            cfgm_control_ip = self.inputs.cfgm_control_ips[i].split('.')
            cfgm_control_ip[3] = '0'
            cfgm_control_ip = ".".join(cfgm_control_ip) + "/24"
            result1 = self.find_rule('default-discovery-service-assignment', cfgm_control_ip,\
                                      'ApiServer', cfgm_control_ip, 'contrailWebUI')
            if result1 == False:
                self.logger.error("While searching for the configured rule, it was not found. Configuration failed")
                result = False      
        self.logger.info("#### Waiting for 60 seconds so that TTL expiry for all subscriber happens ###")
        sleep (60)
        self.logger.debug("#### Verifying clients subscribed to publishers ###")
        try:
            for i in range(0,len(self.inputs.webui_control_ips)):
                verification = self.verify_client_subscription_to_expected_publisher\
                (ds_ip, 'contrailWebUI', self.inputs.webui_control_ips[i], 'ApiServer')
                if verification == False:
                    self.logger.error("Rule not behaving as expected")
                    result = False
        except Exception as e:
            print '*** %s' % str(e)            
        for i in range(0,len(self.inputs.cfgm_control_ips)): 
            cfgm_control_ip = self.inputs.cfgm_control_ips[i].split('.')
            cfgm_control_ip[3] = '0'
            cfgm_control_ip = ".".join(cfgm_control_ip) + "/24"
            self.delete_rule('default-discovery-service-assignment', cfgm_control_ip, \
                             'ApiServer', cfgm_control_ip, 'contrailWebUI')
        self.read_rule("default-discovery-service-assignment")
        for i in range(0,len(self.inputs.cfgm_control_ips)): 
            cfgm_control_ip = self.inputs.cfgm_control_ips[i].split('.')
            cfgm_control_ip[3] = '0'
            cfgm_control_ip = ".".join(cfgm_control_ip) + "/24"
            result1 = self.find_rule('default-discovery-service-assignment', cfgm_control_ip, \
                                     'ApiServer', cfgm_control_ip, 'contrailWebUI')
            if result1 == True:
                self.logger.error("While searching for the deleted rule, it was found. Deletion failed")
                result = False
        self.logger.debug("#### Changing min and max TTL values to default after test completion ##")
        self.change_min_max_ttl()
        return result
    
    def verify_rule_collector_vrouter_agent_client(self, ds_ip=None):
        result = True
        if not ds_ip:
            ds_ip = self.inputs.cfgm_ip
        self.logger.debug("#### Changing min and max TTL values for testing purpose ##")
        self.change_min_max_ttl(ttl_min=60, ttl_max=60)        
        self.logger.info("#### Restarting the required subscriber services so that TTL takes effect immediately ###")
        for ip in self.inputs.compute_ips:
            self.inputs.restart_service('contrail-vrouter-agent', [ip])
        for ip in self.inputs.compute_ips:
            client_status = self.inputs.confirm_service_active('contrail-vrouter-agent', ip)
            if client_status == False:
                self.logger.error("Some issue happened after restart of client process")
                result = False
                return result    
        if len(self.inputs.collector_control_ips) > 0:
            self.logger.info("Creating rules corresponding to *Collector* running on all control nodes for *contrail-vrouter-agent* running in same subnets")
        for i in range(0,len(self.inputs.collector_control_ips)):
            collector_control_ip = self.inputs.collector_control_ips[i].split('.')
            collector_control_ip[3] = '0'
            collector_control_ip = ".".join(collector_control_ip) + "/24"
            self.create_rule('default-discovery-service-assignment', collector_control_ip, \
                             'Collector', collector_control_ip, 'contrail-vrouter-agent:0')
        self.read_rule('default-discovery-service-assignment')
        for i in range(0,len(self.inputs.collector_control_ips)): 
            collector_control_ip = self.inputs.collector_control_ips[i].split('.')
            collector_control_ip[3] = '0'
            collector_control_ip = ".".join(collector_control_ip) + "/24"
            result1 = self.find_rule('default-discovery-service-assignment', collector_control_ip,\
                                      'Collector', collector_control_ip, 'contrail-vrouter-agent:0')
            if result1 == False:
                self.logger.error("While searching for the configured rule, it was not found. Configuration failed")
                result = False    
        self.logger.info("#### Waiting for 60 seconds so that TTL expiry for all subscriber happens ###")
        sleep (60)
        self.logger.debug("#### Verifying clients subscribed to publishers ###") 
        try:
            for i in range(0,len(self.inputs.compute_control_ips)):
                verification = self.verify_client_subscription_to_expected_publisher\
                (ds_ip, 'contrail-vrouter-agent:0', self.inputs.compute_control_ips[i], 'Collector')
                if verification == False:
                    self.logger.error("Rule not behaving as expected")
                    result = False
        except Exception as e:
            print '*** %s' % str(e)            
        for i in range(0,len(self.inputs.collector_control_ips)): 
            collector_control_ip = self.inputs.collector_control_ips[i].split('.')
            collector_control_ip[3] = '0'
            collector_control_ip = ".".join(collector_control_ip) + "/24"
            self.delete_rule('default-discovery-service-assignment', collector_control_ip, \
                             'Collector', collector_control_ip, 'contrail-vrouter-agent:0')
        self.read_rule("default-discovery-service-assignment")
        for i in range(0,len(self.inputs.collector_control_ips)): 
            collector_control_ip = self.inputs.collector_control_ips[i].split('.')
            collector_control_ip[3] = '0'
            collector_control_ip = ".".join(collector_control_ip) + "/24"
            result1 = self.find_rule('default-discovery-service-assignment', collector_control_ip,\
                                      'Collector', collector_control_ip, 'contrail-vrouter-agent:0')
            if result1 == True:
                self.logger.error("While searching for the deleted rule, it was found. Deletion failed")
                result = False
        self.logger.debug("#### Changing min and max TTL values to default after test completion ##")
        self.change_min_max_ttl()
        return result
    
    def verify_rule_collector_multiple_clients(self, ds_ip=None):
        result = True
        if not ds_ip:
            ds_ip = self.inputs.cfgm_ip
        self.logger.debug("#### Changing min and max TTL values for testing purpose ##")
        self.change_min_max_ttl(ttl_min=60, ttl_max=60)        
        self.logger.info("#### Restarting the required subscriber services so that TTL takes effect immediately ###")
        for ip in self.inputs.compute_ips:
            self.inputs.restart_service('contrail-vrouter-agent', [ip])    
        for ip in self.inputs.collector_ips:
            self.inputs.restart_service('contrail-topology', [ip])
        for ip in self.inputs.bgp_ips:
            self.inputs.restart_service('contrail-control', [ip])
        for ip in self.inputs.cfgm_ips:
            self.inputs.restart_service('contrail-api', [ip])
        for ip in self.inputs.compute_ips:
            client_status = self.inputs.confirm_service_active('contrail-vrouter-agent', ip)
            if client_status == False:
                self.logger.error("# Some issue happened after restart of client process #")
                result = False
                return result
        for ip in self.inputs.collector_ips:
            client_status = self.inputs.confirm_service_active('contrail-topology', ip)
            if client_status == False:
                self.logger.error("# Some issue happened after restart of client process #")
                result = False
                return result
        for ip in self.inputs.bgp_ips:
            client_status = self.inputs.confirm_service_active('contrail-control', ip)
            if client_status == False:
                self.logger.error("# Some issue happened after restart of client process #")
                result = False
                return result
        for ip in self.inputs.cfgm_ips:
            client_status = self.inputs.confirm_service_active('contrail-api', ip)
            if client_status == False:
                self.logger.error("# Some issue happened after restart of client process #")
                result = False
                return result        
        if len(self.inputs.collector_control_ips) > 0:
            self.logger.info("# Creating rules corresponding to *Collector* running on all control nodes for multiple clients running in same subnets #")
        for i in range(0,len(self.inputs.collector_control_ips)):    
            collector_control_ip = self.inputs.collector_control_ips[i].split('.')
            collector_control_ip[3] = '0'
            collector_control_ip = ".".join(collector_control_ip) + "/24"
            self.create_rule('default-discovery-service-assignment', collector_control_ip,\
                              'Collector', collector_control_ip, 'contrail-vrouter-agent:0',\
                               collector_control_ip, 'contrail-topology', collector_control_ip,\
                                'contrail-control', collector_control_ip, 'contrail-api')
        self.read_rule('default-discovery-service-assignment')
        for i in range(0,len(self.inputs.collector_control_ips)): 
            collector_control_ip = self.inputs.collector_control_ips[i].split('.')
            collector_control_ip[3] = '0'
            collector_control_ip = ".".join(collector_control_ip) + "/24"
            result1 = self.find_rule('default-discovery-service-assignment', collector_control_ip,\
                                      'Collector', collector_control_ip, 'contrail-vrouter-agent:0',\
                                       collector_control_ip, 'contrail-topology', collector_control_ip,\
                                        'contrail-control', collector_control_ip, 'contrail-api')
            if result1 == False:
                self.logger.error("# While searching for the configured rule, it was not found. Configuration failed #")
                result = False    
        self.logger.info("#### Waiting for 60 seconds so that TTL expiry for all subscriber happens ###")
        sleep (60)
        self.logger.debug("#### Verifying clients subscribed to publishers ###") 
        try:
            for i in range(0,len(self.inputs.compute_control_ips)):
                verification = self.verify_client_subscription_to_expected_publisher\
                (ds_ip, 'contrail-vrouter-agent:0', self.inputs.compute_control_ips[i], 'Collector')
                if verification == False:
                    self.logger.error("# Rule not behaving as expected #")
                    result = False
            for i in range(0,len(self.inputs.bgp_control_ips)):
                verification = self.verify_client_subscription_to_expected_publisher\
                (ds_ip, 'contrail-control', self.inputs.bgp_control_ips[i], 'Collector')
                if verification == False:
                    self.logger.error("# Rule not behaving as expected #")
                    result = False
            for i in range(0,len(self.inputs.collector_control_ips)):
                verification = self.verify_client_subscription_to_expected_publisher\
                (ds_ip, 'contrail-topology', self.inputs.collector_control_ips[i], 'Collector')
                if verification == False:
                    self.logger.error("# Rule not behaving as expected #")
                    result = False
            for i in range(0,len(self.inputs.cfgm_control_ips)):
                verification = self.verify_client_subscription_to_expected_publisher\
                (ds_ip, 'contrail-api', self.inputs.cfgm_control_ips[i], 'Collector')
                if verification == False:
                    self.logger.error("# Rule not behaving as expected #")
                    result = False
        except Exception as e:
            print '*** %s' % str(e)            
        for i in range(0,len(self.inputs.collector_control_ips)): 
            collector_control_ip = self.inputs.collector_control_ips[i].split('.')
            collector_control_ip[3] = '0'
            collector_control_ip = ".".join(collector_control_ip) + "/24"
            self.delete_rule('default-discovery-service-assignment', collector_control_ip,\
                              'Collector', collector_control_ip, 'contrail-vrouter-agent:0',\
                               collector_control_ip, 'contrail-topology', collector_control_ip,\
                                'contrail-control', collector_control_ip, 'contrail-api')
        self.read_rule("default-discovery-service-assignment")
        for i in range(0,len(self.inputs.collector_control_ips)): 
            collector_control_ip = self.inputs.collector_control_ips[i].split('.')
            collector_control_ip[3] = '0'
            collector_control_ip = ".".join(collector_control_ip) + "/24"
            result1 = self.find_rule('default-discovery-service-assignment', collector_control_ip,\
                                      'Collector', collector_control_ip, 'contrail-vrouter-agent:0',\
                                       collector_control_ip, 'contrail-topology', collector_control_ip,\
                                        'contrail-control', collector_control_ip, 'contrail-api')
            if result1 == True:
                self.logger.error("# While searching for the deleted rule, it was found. Deletion failed #")
                result = False
        self.logger.debug("#### Changing min and max TTL values to default after test completion ##")
        self.change_min_max_ttl()
        return result
    
    def verify_subscribe_request_with_diff_instances_rules(self, ds_ip=None):
        result = True
        if not ds_ip:
            ds_ip = self.inputs.cfgm_ip
        self.logger.debug("#### Changing min and max TTL values for testing purpose ##")
        self.change_min_max_ttl(ttl_min=60, ttl_max=60)        
        try:
            self.logger.info("#### Sending a dummy client request with instance value as 3 to subscribe to IfmapServer #####")
            self.subscribe_service_from_discovery(ds_ip, service="IfmapServer", \
                                                  instances="3", min_instances="0",\
                                                   client_id=self.inputs.compute_names[0]+":TestClient",\
                                                    remote_addr= self.inputs.compute_control_ips[0], \
                                                    client_type= "TestClient")
            sleep(2)
            self.logger.debug("# Verifying the number of instances of publishers granted to the client #")
            ifmap_server_count = len(self.inputs.cfgm_control_ips)
            client_subscribed_service_id = self.get_subscribed_service_id\
            (ds_ip, client=(self.inputs.compute_control_ips[0],"TestClient"), service="IfmapServer")
            instances_allocated = len(client_subscribed_service_id)
            self.logger.debug("# The instances of publishers allocated to TestClient by the discovery server are %d #" \
                              % instances_allocated)
            self.logger.debug("# The total number of publishers running of such types are %d #" \
                              % len(self.inputs.cfgm_control_ips))
            if ifmap_server_count == instances_allocated or (ifmap_server_count > 3 and instances_allocated == 3):
                self.logger.info("# Instance field working as expected #")
            else:
                self.logger.error("# Instance field not working as expected. #")
                result = False
        except Exception as e:
            print '*** %s' % str(e)
        try:
            self.logger.info("# Now creating a rule to verify that even if multiple instances are requested but if a rule is present, it will limit the instances #")
            self.create_rule('default-discovery-service-assignment', \
                             self.inputs.cfgm_control_ips[0], 'IfmapServer', \
                             self.inputs.compute_control_ips[0], 'TestClient')
            self.read_rule('default-discovery-service-assignment')
            result1 = self.find_rule('default-discovery-service-assignment', \
                                     self.inputs.cfgm_control_ips[0], 'IfmapServer',\
                                      self.inputs.compute_control_ips[0], 'TestClient')
            if result1 == False:
                self.logger.error("# While searching for the configured rule, it was not found. Configuration failed #")
                result = False
        except Exception as e:
            print '*** %s' % str(e)
        self.logger.debug("#### Waiting for 60 seconds so that TTL expiry for all subscriber happens ###")
        sleep (60)    
        try:
            self.logger.info("#### Sending a dummy client request with instance value as 3 to subscribe to IfmapServer #####")
            self.subscribe_service_from_discovery(ds_ip, service="IfmapServer", \
                                                  instances="3", min_instances="0", \
                                                  client_id=self.inputs.compute_names[0]+":TestClient", \
                                                  remote_addr= self.inputs.compute_control_ips[0], \
                                                  client_type= "TestClient")
            sleep(2)
            self.logger.debug("# Verifying the number of instances of publishers granted to the client #")      
            client_subscribed_service_id = self.get_subscribed_service_id\
            (ds_ip, client=(self.inputs.compute_control_ips[0],"TestClient"), service="IfmapServer")
            instances_allocated = len(client_subscribed_service_id)
            service_IPs = []
            for i in range (0,instances_allocated):
                service_endpoint = self.get_service_endpoint_by_service_id\
                (ds_ip,client_subscribed_service_id[i])
                service_IPs.append(service_endpoint[0][0])
            self.logger.debug("# Number of instances of Publishers used by TestClient are %d and IPs of those publishers are %s #" % (instances_allocated,service_IPs))
            if instances_allocated==1 and service_IPs[0]==self.inputs.cfgm_control_ips[0]:
                self.logger.info("# As expected, TestClient is subscribed to only 1 instance of IfmapServer even if it is requesting for 3 instances. This happened because of rule present #")
                pass
            else:
                result = False
                self.logger.error("# TestClient is subscribed to less/more than 1 instance of IfmapServer. Something went wrong. Expectedly, rules are not working.#")
        except Exception as e:
            print '*** %s' % str(e)
        try:
            self.logger.info("# Now deleting a rule to verify that after rule is deleted, instances requested are granted without any restriction #")
            self.delete_rule('default-discovery-service-assignment', self.inputs.cfgm_control_ips[0],\
                              'IfmapServer', self.inputs.compute_control_ips[0], 'TestClient')
            self.read_rule('default-discovery-service-assignment')
            result1 = self.find_rule('default-discovery-service-assignment', \
                                     self.inputs.cfgm_control_ips[0], 'IfmapServer',\
                                      self.inputs.compute_control_ips[0], 'TestClient')
            if result1 == True:
                self.logger.error("# While searching for the deleted rule, it was found. Deletion failed #")
                result = False
        except Exception as e:
            print '*** %s' % str(e)
        self.logger.debug("#### Waiting for 60 seconds so that TTL expiry for all subscriber happens ###")
        sleep (60)    
        try:
            self.logger.info("#### Sending a dummy client request with instance value as 3 to subscribe to IfmapServer #####")
            self.subscribe_service_from_discovery(ds_ip, service="IfmapServer",\
                                                   instances="3", min_instances="0",\
                                                    client_id=self.inputs.compute_names[0]+":TestClient",\
                                                     remote_addr= self.inputs.compute_control_ips[0],\
                                                      client_type= "TestClient")
            sleep(2)
            self.logger.debug("# Verifying the number of instances of publishers granted to the client #")
            ifmap_server_count = len(self.inputs.cfgm_control_ips)
            client_subscribed_service_id = self.get_subscribed_service_id\
            (ds_ip, client=(self.inputs.compute_control_ips[0],"TestClient"), service="IfmapServer")
            instances_allocated = len(client_subscribed_service_id)
            self.logger.debug("# The instances of publishers allocated to TestClient by the discovery server are %d #" \
                              % instances_allocated)
            self.logger.debug("# The total number of publishers running of such types are %d #"\
                               % instances_allocated)
            if ifmap_server_count == instances_allocated or (ifmap_server_count > 3 and instances_allocated == 3):
                self.logger.info("# Instance field working as expected #")
            else:
                self.logger.error(" # Instance field not working as expected.#")
                result = False
        except Exception as e:
            print '*** %s' % str(e)
        self.logger.debug("#### Changing min and max TTL values to default after test completion ##")
        self.change_min_max_ttl()
        return result
    
    def verify_rule_when_service_admin_down(self, ds_ip=None):
        result = True
        if not ds_ip:
            ds_ip = self.inputs.cfgm_ip
        self.logger.debug("#### Changing min and max TTL values for testing purpose ##")
        self.change_min_max_ttl(ttl_min=60, ttl_max=60)
        for ip in self.inputs.compute_ips:
            self.inputs.restart_service('contrail-vrouter-agent', [ip])
        for ip in self.inputs.compute_ips:
            client_status = self.inputs.confirm_service_active('contrail-vrouter-agent', ip)
            if client_status == False:
                self.logger.error("Some issue happened after restart of client process")
                result = False
                return result 
        try:
            self.logger.info("# Create a rule for Dns-Server running on control node and subscriber as contrail-vrouter-agent   #")
            self.create_rule('default-discovery-service-assignment', \
                             self.inputs.bgp_control_ips[0], 'dns-server', \
                             self.inputs.compute_control_ips[0], 'contrail-vrouter-agent:0')
            self.read_rule('default-discovery-service-assignment')
            result1 = self.find_rule('default-discovery-service-assignment', \
                                     self.inputs.bgp_control_ips[0], 'dns-server', \
                                     self.inputs.compute_control_ips[0], 'contrail-vrouter-agent:0')
            if result1 == False:
                self.logger.error("# While searching for the configured rule, it was not found. Configuration failed #")
                result = False
            self.logger.info("# Making the admin state of dsn-server as *down*# ")
            self.update_service(ds_ip,service="dns-server",ip=self.inputs.bgp_control_ips[0],admin_state="down")
        except Exception as e:
            print '*** %s' % str(e)   
        self.logger.debug("#### Waiting for 90 seconds so that TTL expiry for all subscriber happens ###")
        sleep (90)
        try:
            self.logger.debug("# Verifying that as publisher is admin down, the mentioned subscriber in rule do not get any instance of Publisher #")      
            client_subscribed_service_id = self.get_subscribed_service_id\
            (ds_ip, client=(self.inputs.compute_control_ips[0],"contrail-vrouter-agent:0"), service="dns-server")
            instances_allocated = len(client_subscribed_service_id)
            if instances_allocated==0:
                self.logger.info("# As expected, contrail-vrouter-agent running on %s is not subscribed to any dns-server as the rule is restricting it to do that and publisher mentioned in rule is admin *down*. #" % self.inputs.compute_control_ips[0])
                pass
            else:
                result = False
                self.logger.error("# Even if rule is present and publisher in rule is admin *down*, some publisher got assigned to the subscriber contrail-vrouter-agent running on %s .#", self.inputs.compute_control_ips[0])
                service_IPs = []
                for i in range (0,instances_allocated):
                    service_endpoint = self.get_service_endpoint_by_service_id\
                    (ds_ip,client_subscribed_service_id[i])
                    service_IPs.append(service_endpoint[0][0])
                self.logger.warn("# The publisher assigned to the client are running at following IPs: %s ###" % service_IPs)
            self.logger.info("# Making the admin state of dsn-server as *up*# ")
            self.update_service(ds_ip,service="dns-server",ip=self.inputs.bgp_control_ips[0],admin_state="up")
            self.logger.debug("#### Waiting for 5 seconds so that the client subscribe to the new subscriber as soon as it comes administratively up ###")
            sleep(5)
            self.logger.debug("# Verifying that as publisher is admin up, the mentioned subscriber in rule gets the same instance of Publisher as mentione din rule #")      
            client_subscribed_service_id = self.get_subscribed_service_id\
            (ds_ip, client=(self.inputs.compute_control_ips[0],"contrail-vrouter-agent:0"), service="dns-server")
            instances_allocated = len(client_subscribed_service_id)
            service_IPs = []
            for i in range (0,instances_allocated):
                service_endpoint = self.get_service_endpoint_by_service_id\
                (ds_ip,client_subscribed_service_id[i])
                service_IPs.append(service_endpoint[0][0])
            if instances_allocated==1 and service_IPs[0]==self.inputs.bgp_control_ips[0]:
                self.logger.info("# As expected, contrail-vrouter-agent running on %s is subscribed to single dns-server as the rule is restricting it to do that. #" % self.inputs.compute_control_ips[0])
                pass
            else:
                result = False
                self.logger.error("# Even if rule is present and publisher in rule is admin *up*, some different publishers or no publisher got assigned to the subscriber contrail-vrouter-agent running on %s .#", self.inputs.compute_control_ips[0])
                self.logger.error("# The publisher assigned to the client are running at following IPs: %s###" % service_IPs)
        except Exception as e:
            print '*** %s' % str(e)
        try:
            self.logger.info("# Now deleting the rule before starting new test case #")
            self.delete_rule('default-discovery-service-assignment',  self.inputs.bgp_control_ips[0], \
                             'dns-server', self.inputs.compute_control_ips[0], 'contrail-vrouter-agent:0')
            self.read_rule('default-discovery-service-assignment')
            result1 = self.find_rule('default-discovery-service-assignment',  self.inputs.bgp_control_ips[0],\
                                      'dns-server', self.inputs.compute_control_ips[0], 'contrail-vrouter-agent:0')
            if result1 == True:
                self.logger.error("# While searching for the deleted rule, it was found. Deletion failed #")
                result = False
        except Exception as e:
            print '*** %s' % str(e)   
        self.logger.debug("#### Changing min and max TTL values to default after test completion ##")
        self.change_min_max_ttl()
        return result
    
    def verify_multiple_rule_same_subscriber(self, ds_ip=None):
        result = True
        if not ds_ip:
            ds_ip = self.inputs.cfgm_ip
        self.logger.debug("#### Changing min and max TTL values for testing purpose ##")
        self.change_min_max_ttl(ttl_min=60, ttl_max=60)
        for ip in self.inputs.compute_ips:
            self.inputs.restart_service('contrail-vrouter-agent', [ip])
        for ip in self.inputs.compute_ips:
            client_status = self.inputs.confirm_service_active('contrail-vrouter-agent', ip)
            if client_status == False:
                self.logger.error("Some issue happened after restart of client process")
                result = False
                return result 
        try:
            self.logger.info("# Create a rule for xmpp-server running on control node and subscriber as contrail-vrouter-agent   #")
            self.create_rule('default-discovery-service-assignment', self.inputs.bgp_control_ips[0],\
                              'xmpp-server', self.inputs.compute_control_ips[0], 'contrail-vrouter-agent:0')
            self.read_rule('default-discovery-service-assignment')
            result1 = self.find_rule('default-discovery-service-assignment', self.inputs.bgp_control_ips[0],\
                                      'xmpp-server', self.inputs.compute_control_ips[0], 'contrail-vrouter-agent:0')
            if result1 == False:
                self.logger.error("# While searching for the configured rule, it was not found. Configuration failed #")
                result = False
        except Exception as e:
            print '*** %s' % str(e)  
        self.logger.debug("#### Waiting for 60 seconds so that TTL expiry for all subscriber happens ###")
        sleep (60)
        try:
            self.logger.debug("# Verifying that client is only subscribed to mentioned Publisher in the rule #")      
            client_subscribed_service_id = self.get_subscribed_service_id\
            (ds_ip, client=(self.inputs.compute_control_ips[0],"contrail-vrouter-agent:0"), service="xmpp-server")
            instances_allocated = len(client_subscribed_service_id)
            service_IPs=[]
            for i in range (0,instances_allocated):
                    service_endpoint = self.get_service_endpoint_by_service_id\
                    (ds_ip,client_subscribed_service_id[i])
                    service_IPs.append(service_endpoint[0][0])
            if instances_allocated==1 and service_IPs[0]==self.inputs.bgp_control_ips[0]:
                self.logger.info("# Client contrail-vrouter-agent running on %s is subscribed to expected xmpp-server as the rule is restricting it to do that #" % self.inputs.compute_control_ips[0])
                pass
            else:
                result = False
                self.logger.error("# Even if rule is present, subscription not happening as expected for contrail-vrouter-agent running on %s .#", self.inputs.compute_control_ips[0])
                self.logger.error("# The publisher assigned to the client are running at following IPs: %s ###" % service_IPs)
                self.logger.error("# Expected was that client will subscribe only to xmpp-server running on %s node" % self.inputs.bgp_control_ips[0])
        except Exception as e:
            print '*** %s' % str(e)
        try:
            self.logger.info("# Create another rule for xmpp-server running on control node and subscriber as contrail-vrouter-agent so that 2nd instance of xmpp-server gets a Publisher  #")
            self.create_rule('default-discovery-service-assignment', self.inputs.bgp_control_ips[1],\
                              'xmpp-server', self.inputs.compute_control_ips[0], 'contrail-vrouter-agent:0')
            self.read_rule('default-discovery-service-assignment')
            result1 = self.find_rule('default-discovery-service-assignment', self.inputs.bgp_control_ips[1],\
                                      'xmpp-server', self.inputs.compute_control_ips[0], 'contrail-vrouter-agent:0')
            if result1 == False:
                self.logger.error("# While searching for the configured rule, it was not found. Configuration failed #")
                result = False
        except Exception as e:
            print '*** %s' % str(e)   
        self.logger.debug("#### Waiting for 60 seconds so that TTL expiry for all subscriber happens ###")
        sleep (60)
        try:
            self.logger.debug("# Verifying that 2nd instance of the client is subscribed to mentioned Publisher in the rule #")      
            client_subscribed_service_id = self.get_subscribed_service_id\
            (ds_ip, client=(self.inputs.compute_control_ips[0],"contrail-vrouter-agent:0"),\
              service="xmpp-server")
            instances_allocated = len(client_subscribed_service_id)
            service_IPs=[]
            for i in range (0,instances_allocated):
                    service_endpoint = self.get_service_endpoint_by_service_id\
                    (ds_ip,client_subscribed_service_id[i])
                    service_IPs.append(service_endpoint[0][0])
            if instances_allocated==2 and service_IPs[0] in self.inputs.bgp_control_ips and\
             service_IPs[1] in self.inputs.bgp_control_ips:
                self.logger.info("# Client contrail-vrouter-agent running on %s is subscribed to expected xmpp-server as the rule is restricting it to do that #" % self.inputs.compute_control_ips[0])
                pass
            else:
                result = False
                self.logger.error("# Even if 2 rules are present, subscription not happening as expected for contrail-vrouter-agent running on %s .#", self.inputs.compute_control_ips[0])
                self.logger.error("# The publisher assigned to the client are running at following IPs: %s ###" % service_IPs)
                self.logger.error("# Expected was that client will subscribe to xmpp-server running on %s and %s node" % (self.inputs.bgp_control_ips[0],self.inputs.bgp_control_ips[1]))
        except Exception as e:
            print '*** %s' % str(e)    
        try:
            self.logger.info("# Now deleting the rule before starting new test case #")
            self.delete_rule('default-discovery-service-assignment',  self.inputs.bgp_control_ips[0],\
                              'xmpp-server', self.inputs.compute_control_ips[0], 'contrail-vrouter-agent:0')
            self.delete_rule('default-discovery-service-assignment',  self.inputs.bgp_control_ips[1],\
                              'xmpp-server', self.inputs.compute_control_ips[0], 'contrail-vrouter-agent:0')
            self.read_rule('default-discovery-service-assignment')
            result1 = self.find_rule('default-discovery-service-assignment',  self.inputs.bgp_control_ips[0],\
                                      'xmpp-server', self.inputs.compute_control_ips[0], 'contrail-vrouter-agent:0')
            result1 = self.find_rule('default-discovery-service-assignment',  self.inputs.bgp_control_ips[1],\
                                      'xmpp-server', self.inputs.compute_control_ips[0], 'contrail-vrouter-agent:0')
            if result1 == True:
                self.logger.error("# While searching for the deleted rule, it was found. Deletion failed #")
                result = False
        except Exception as e:
            print '*** %s' % str(e)   
        self.logger.debug("#### Changing min and max TTL values to default after test completion ##")
        self.change_min_max_ttl()
        return result
    
    def verify_rule_on_xmpp_do_not_impact_dns(self, ds_ip=None):
        result = True
        if not ds_ip:
            ds_ip = self.inputs.cfgm_ip
        self.logger.debug("#### Changing min and max TTL values for testing purpose ##")
        self.change_min_max_ttl(ttl_min=60, ttl_max=60)
        for ip in self.inputs.compute_ips:
            self.inputs.restart_service('contrail-vrouter-agent', [ip])
        for ip in self.inputs.compute_ips:
            client_status = self.inputs.confirm_service_active('contrail-vrouter-agent', ip)
            if client_status == False:
                self.logger.error("Some issue happened after restart of client process")
                result = False
                return result 
        try:
            self.logger.info("# Create 2 rules for xmpp-server and dns-server running on control node and subscriber as contrail-vrouter-agent   #")
            self.create_rule('default-discovery-service-assignment', self.inputs.bgp_control_ips[0],\
                              'xmpp-server', self.inputs.compute_control_ips[0], 'contrail-vrouter-agent:0')
            self.create_rule('default-discovery-service-assignment', self.inputs.bgp_control_ips[0],\
                              'dns-server', self.inputs.compute_control_ips[0], 'contrail-vrouter-agent:0')
            self.read_rule('default-discovery-service-assignment')
            result1 = self.find_rule('default-discovery-service-assignment', self.inputs.bgp_control_ips[0],\
                                      'xmpp-server', self.inputs.compute_control_ips[0], 'contrail-vrouter-agent:0')
            if result1 == False:
                self.logger.error("# While searching for the configured rule, it was not found. Configuration failed #")
                result = False
            result2 = self.find_rule('default-discovery-service-assignment', self.inputs.bgp_control_ips[0],\
                                      'dns-server', self.inputs.compute_control_ips[0], 'contrail-vrouter-agent:0')
            if result1 == False:
                self.logger.error("# While searching for the configured rule, it was not found. Configuration failed #")
                result = False
        except Exception as e:
            print '*** %s' % str(e)
        self.logger.debug("#### Waiting for 70 seconds so that TTL expiry for all subscriber happens ###")
        sleep (70)
        try:
            self.logger.debug("# Verifying that client is only subscribed to mentioned Publishers in the rule #")      
            client_subscribed_xmpp_service_id = self.get_subscribed_service_id\
            (ds_ip, client=(self.inputs.compute_control_ips[0],"contrail-vrouter-agent:0"), service="xmpp-server")
            client_subscribed_dns_service_id = self.get_subscribed_service_id\
            (ds_ip, client=(self.inputs.compute_control_ips[0],"contrail-vrouter-agent:0"), service="dns-server")
            instances_allocated_xmpp = len(client_subscribed_xmpp_service_id)
            instances_allocated_dns = len(client_subscribed_dns_service_id)
            service_IPs_xmpp=[]
            service_IPs_dns=[]
            for i in range (0,instances_allocated_xmpp):
                    service_endpoint_xmpp = self.get_service_endpoint_by_service_id\
                    (ds_ip,client_subscribed_xmpp_service_id[i])
                    service_IPs_xmpp.append(service_endpoint_xmpp[0][0])
            for i in range (0,instances_allocated_dns):
                    service_endpoint_dns = self.get_service_endpoint_by_service_id\
                    (ds_ip,client_subscribed_dns_service_id[i])
                    service_IPs_dns.append(service_endpoint_dns[0][0])
            if instances_allocated_xmpp==1 and service_IPs_xmpp[0]==self.inputs.bgp_control_ips[0]:
                self.logger.info("# Client contrail-vrouter-agent running on %s is subscribed to expected xmpp-server as the rule is restricting it to do that #" % self.inputs.compute_control_ips[0])
                pass
            else:
                result = False
                self.logger.error("# Even if rule is present, subscription not happening as expected for contrail-vrouter-agent running on %s .#", self.inputs.compute_control_ips[0])
                self.logger.debug("# The publisher assigned to the client are running at following IPs: %s ###" % service_IPs_xmpp)
                self.logger.debug("# Expected was that client will subscribe only to xmpp-server running on %s node" % self.inputs.bgp_control_ips[0])
            if instances_allocated_dns==1 and service_IPs_dns[0]==self.inputs.bgp_control_ips[0]:
                self.logger.info("# Client contrail-vrouter-agent running on %s is subscribed to expected dns-server as the rule is restricting it to do that #" % self.inputs.compute_control_ips[0])
                pass
            else:
                result = False
                self.logger.error("# Even if rule is present, subscription not happening as expected for contrail-vrouter-agent running on %s .#", self.inputs.compute_control_ips[0])
                self.logger.debug("# The publisher assigned to the client are running at following IPs: %s ###" % service_IPs_xmpp)
                self.logger.debug("# Expected was that client will subscribe only to dns-server running on %s node" % self.inputs.bgp_control_ips[0])
        except Exception as e:
            print '*** %s' % str(e)
        try:
            self.logger.info("# Now deleting the rule before starting new test case #")
            self.delete_rule('default-discovery-service-assignment',  self.inputs.bgp_control_ips[0],\
                              'xmpp-server', self.inputs.compute_control_ips[0], 'contrail-vrouter-agent:0')
            self.delete_rule('default-discovery-service-assignment',  self.inputs.bgp_control_ips[0],\
                              'dns-server', self.inputs.compute_control_ips[0], 'contrail-vrouter-agent:0')
            self.read_rule('default-discovery-service-assignment')
            result1 = self.find_rule('default-discovery-service-assignment',  self.inputs.bgp_control_ips[0],\
                                      'xmpp-server', self.inputs.compute_control_ips[0], 'contrail-vrouter-agent:0')
            result2 = self.find_rule('default-discovery-service-assignment',  self.inputs.bgp_control_ips[0],\
                                      'dns-server', self.inputs.compute_control_ips[0], 'contrail-vrouter-agent:0')
            if result1 == True:
                self.logger.error("# While searching for the deleted rule, it was found. Deletion failed #")
                result = False
            if result2 == True:
                self.logger.error("# While searching for the deleted rule, it was found. Deletion failed #")
                result = False
        except Exception as e:
            print '*** %s' % str(e)   
        self.logger.debug("#### Changing min and max TTL values to default after test completion ##")
        self.change_min_max_ttl()
        return result
    
    def verify_rule_with_vrouter_agent_do_not_impact_other_subscriptions(self, ds_ip=None):
        result = True
        if not ds_ip:
            ds_ip = self.inputs.cfgm_ip
        self.logger.debug("#### Changing min and max TTL values for testing purpose ##")
        self.change_min_max_ttl(ttl_min=60, ttl_max=60)
        for ip in self.inputs.compute_ips:
            self.inputs.restart_service('contrail-vrouter-agent', [ip])
        for ip in self.inputs.compute_ips:
            client_status = self.inputs.confirm_service_active('contrail-vrouter-agent', ip)
            if client_status == False:
                self.logger.error("Some issue happened after restart of client process")
                result = False
                return result
        try:
            self.logger.info("# Find the instances of subscription of contrail-vrouter-agent  to the xmpp-server server #")
            xmpp_vrouter_subscription_list = self.get_all_xmpp_server_of_vrouter_agent(ds_ip)
            self.logger.info("# Create a rule for dns-server running on control node and subscriber as contrail-vrouter-agent   #")
            compute_control_ip = self.inputs.compute_control_ips[0].split('.')
            compute_control_ip[2:4] = '0','0'
            compute_control_ip = ".".join(compute_control_ip) + "/16"
            self.create_rule('default-discovery-service-assignment', self.inputs.bgp_control_ips[0],\
                              'dns-server', compute_control_ip, 'contrail-vrouter-agent:0')
            self.read_rule('default-discovery-service-assignment')
            result1 = self.find_rule('default-discovery-service-assignment', self.inputs.bgp_control_ips[0],\
                                      'dns-server', compute_control_ip, 'contrail-vrouter-agent:0')
            if result1 == False:
                self.logger.error("# While searching for the configured rule, it was not found. Configuration failed #")
                result = False
            self.logger.debug("# Verify that subscription of vrouter-agent to xmpp-server is not impacted due to the above rule for 90 seconds #")
            for i in range(1,90):
                new_xmpp_vrouter_subscription_list = self.get_all_xmpp_server_of_vrouter_agent(ds_ip)
                sleep(1)
                if xmpp_vrouter_subscription_list == new_xmpp_vrouter_subscription_list:
                    pass
                else:
                    self.logger.warn("#### Some assignment change has happened for vrouter agent subscription to xmpp-server #####")
                    self.logger.warn("#### Earlier service IDs in use were %s and after waiting for %i seconds, the service ID has changed to %s #####" % (xmpp_vrouter_subscription_list,i,new_xmpp_vrouter_subscription_list))
                    result = False
                    break
        except Exception as e:
            print '*** %s' % str(e)
        try:
            self.logger.info("# Now deleting the rule before starting new test case #")
            self.delete_rule('default-discovery-service-assignment',  self.inputs.bgp_control_ips[0],\
                              'dns-server', compute_control_ip, 'contrail-vrouter-agent:0')
            self.read_rule('default-discovery-service-assignment')
            result1 = self.find_rule('default-discovery-service-assignment',  self.inputs.bgp_control_ips[0],\
                                      'dns-server', compute_control_ip, 'contrail-vrouter-agent:0')
            if result1 == True:
                self.logger.error("# While searching for the deleted rule, it was found. Deletion failed #")
                result = False
        except Exception as e:
            print '*** %s' % str(e)  
        self.logger.debug("#### Changing min and max TTL values to default after test completion ##")
        self.change_min_max_ttl()
        return result
    
    def verify_discovery_server_restart_rule_present(self, ds_ip=None):
        result = True
        if not ds_ip:
            ds_ip = self.inputs.cfgm_ip
        self.logger.debug("#### Changing min and max TTL values for testing purpose ##")
        self.change_min_max_ttl(ttl_min=60, ttl_max=60)  
        self.logger.info("#### Restarting the required subscriber services so that TTL takes effect immediately ###")
        for ip in self.inputs.bgp_ips:
            self.inputs.restart_service('contrail-control', [ip])
        for ip in self.inputs.bgp_ips:
            client_status = self.inputs.confirm_service_active('contrail-control', ip)
            if client_status == False:
                self.logger.error("Some issue happened after restart of client process")
                result = False
                return result    
        if len(self.inputs.bgp_control_ips) > 0:
            self.logger.info("Creating rules corresponding to *IfmapServer* running on all control nodes for *contrail-control* running in same subnets")
        for i in range(0,len(self.inputs.bgp_control_ips)):
            bgp_control_ip = self.inputs.cfgm_control_ips[i].split('.')
            bgp_control_ip[3] = '0'
            bgp_control_ip = ".".join(bgp_control_ip) + "/24"
            self.create_rule('default-discovery-service-assignment', bgp_control_ip, \
                             'IfmapServer', bgp_control_ip, 'contrail-control')
        self.read_rule('default-discovery-service-assignment')
        for i in range(0,len(self.inputs.bgp_control_ips)): 
            bgp_control_ip = self.inputs.bgp_control_ips[i].split('.')
            bgp_control_ip[3] = '0'
            bgp_control_ip = ".".join(bgp_control_ip) + "/24"
            result1 = self.find_rule('default-discovery-service-assignment', bgp_control_ip,\
                                      'IfmapServer', bgp_control_ip, 'contrail-control')
            if result1 == False:
                self.logger.error("While searching for the configured rule, it was not found. Configuration failed")
                result = False
        self.logger.debug("#### Waiting for 60 seconds so that TTL expiry for all subscriber happens ###")
        sleep (60)
        try:
            self.logger.debug("#### Verifying clients subscribed to publishers ###")
            for i in range(0,len(self.inputs.bgp_control_ips)):
                verification = self.verify_client_subscription_to_expected_publisher\
                (ds_ip, 'contrail-control', self.inputs.bgp_control_ips[i], 'IfmapServer')
                if verification == False:
                    self.logger.error("Rule not behaving as expected")
                    result = False
            self.logger.debug("#### Stopping the discovery server process on all nodes ###")
            for ip in self.inputs.cfgm_ips:
                self.inputs.stop_service('contrail-discovery', [ip])
            self.logger.debug("#### Waiting for 90 seconds so that all clients again try to resubscribe when discovery server is down ###")
            sleep(90)
            self.logger.debug("#### Starting the discovery server process on all nodes ###")
            for ip in self.inputs.cfgm_ips:
                self.inputs.start_service('contrail-discovery', [ip])
            for ip in self.inputs.cfgm_ips:
                client_status = self.inputs.confirm_service_active('contrail-discovery', ip)
                if client_status == False:
                    self.logger.error("Some issue happened after restart of client process")
                    result = False
                    return result
            sleep(5)
            self.logger.debug("#### Verifying clients subscribed to publishers as per rules, after discovery server restart ###")
            for i in range(0,len(self.inputs.bgp_control_ips)):
                verification = self.verify_client_subscription_to_expected_publisher\
                (ds_ip, 'contrail-control', self.inputs.bgp_control_ips[i], 'IfmapServer')
                if verification == False:
                    self.logger.error("Rule not behaving as expected")
                    result = False
        except Exception as e:
            print '*** %s' % str(e)
        try:    
            self.logger.info("#### Stopping the discovery server process on all nodes ###")            
            for i in range(0,len(self.inputs.bgp_control_ips)): 
                bgp_control_ip = self.inputs.bgp_control_ips[i].split('.')
                bgp_control_ip[3] = '0'
                bgp_control_ip = ".".join(bgp_control_ip) + "/24"
                self.delete_rule('default-discovery-service-assignment', bgp_control_ip,\
                                  'IfmapServer', bgp_control_ip, 'contrail-control')
            self.read_rule("default-discovery-service-assignment")
            for i in range(0,len(self.inputs.bgp_control_ips)): 
                bgp_control_ip = self.inputs.bgp_control_ips[i].split('.')
                bgp_control_ip[3] = '0'
                bgp_control_ip = ".".join(bgp_control_ip) + "/24"
                result1 = self.find_rule('default-discovery-service-assignment', bgp_control_ip,\
                                          'IfmapServer', bgp_control_ip, 'contrail-control')
                if result1 == True:
                    self.logger.error("While searching for the deleted rule, it was found. Deletion failed")
                    result = False
        except Exception as e:
            print '*** %s' % str(e)
        self.logger.debug("#### Changing min and max TTL values to default after test completion ##")
        self.change_min_max_ttl()
        return result
    
    def verify_publisher_restart_rule_present(self, ds_ip=None):
        result = True
        if not ds_ip:
            ds_ip = self.inputs.cfgm_ip
        self.logger.debug("#### Changing min and max TTL values for testing purpose ##")
        self.change_min_max_ttl(ttl_min=60, ttl_max=60)  
        self.logger.info("#### Restarting the required subscriber services so that TTL takes effect immediately ###")
        for ip in self.inputs.compute_ips:
            self.inputs.restart_service('contrail-vrouter-agent', [ip])
        for ip in self.inputs.compute_ips:
            client_status = self.inputs.confirm_service_active('contrail-vrouter-agent', ip)
            if client_status == False:
                self.logger.error("Some issue happened after restart of client process")
                result = False
                return result    
        self.logger.info("Creating rules corresponding to *xmpp-server*, *dns-server* and *Collector* running on all control nodes for *contrail-vrouter-agent* running in same subnets")
        for i in range(0,len(self.inputs.bgp_control_ips)):
            bgp_control_ip = self.inputs.bgp_control_ips[i].split('.')
            bgp_control_ip[3] = '0'
            bgp_control_ip = ".".join(bgp_control_ip) + "/24"
            self.create_rule('default-discovery-service-assignment', bgp_control_ip, \
                             'xmpp-server', bgp_control_ip, 'contrail-vrouter-agent:0')
            self.create_rule('default-discovery-service-assignment', bgp_control_ip,\
                              'dns-server', bgp_control_ip, 'contrail-vrouter-agent:0')
        for i in range(0,len(self.inputs.collector_control_ips)):
            collector_control_ip = self.inputs.collector_control_ips[i].split('.')
            collector_control_ip[3] = '0'
            collector_control_ip = ".".join(collector_control_ip) + "/24"
            self.create_rule('default-discovery-service-assignment', collector_control_ip,\
                              'Collector', collector_control_ip, 'contrail-vrouter-agent:0')
        self.read_rule('default-discovery-service-assignment')
        self.logger.debug("#### Waiting for 60 seconds so that TTL expiry for all subscriber happens ###")
        sleep (60)
        try:
            self.logger.debug("#### Verifying clients subscribed to publishers ###")
            for i in range(0,len(self.inputs.compute_control_ips)):
                verification = self.verify_client_subscription_to_expected_publisher\
                (ds_ip, 'contrail-vrouter-agent:0', self.inputs.compute_control_ips[i], 'xmpp-server')
                if verification == False:
                    self.logger.error("Rule not behaving as expected")
                    result = False
            for i in range(0,len(self.inputs.compute_control_ips)):
                verification = self.verify_client_subscription_to_expected_publisher\
                (ds_ip, 'contrail-vrouter-agent:0', self.inputs.compute_control_ips[i], 'dns-server')
                if verification == False:
                    self.logger.error("Rule not behaving as expected")
                    result = False
            for i in range(0,len(self.inputs.compute_control_ips)):
                verification = self.verify_client_subscription_to_expected_publisher\
                (ds_ip, 'contrail-vrouter-agent:0', self.inputs.compute_control_ips[i], 'Collector')
                if verification == False:
                    self.logger.error("Rule not behaving as expected")
                    result = False
            self.logger.info("#### Restarting the xmpp, dns and Collector server process on all nodes ###")
            for ip in self.inputs.collector_ips:
                self.inputs.restart_service('contrail-collector', [ip])
            for ip in self.inputs.bgp_ips:
                self.inputs.restart_service('contrail-control', [ip])
                self.inputs.restart_service('contrail-dns', [ip])
            for ip in self.inputs.collector_ips:
                client_status = self.inputs.confirm_service_active('contrail-collector', ip)
                if client_status == False:
                    self.logger.error("Some issue happened after restart of server process")
                    result = False
                    return result
            for ip in self.inputs.bgp_ips:
                client_status = self.inputs.confirm_service_active('contrail-control', ip)
                if client_status == False:
                    self.logger.error("Some issue happened after restart of server process")
                    result = False
                    return result
            for ip in self.inputs.bgp_ips:
                client_status = self.inputs.confirm_service_active('contrail-dns', ip)
                if client_status == False:
                    self.logger.error("Some issue happened after restart of server process")
                    result = False
                    return result
            self.logger.debug("#### Waiting for 60 seconds so that all clients again try to resubscribe when discovery server is down ###")
            sleep(60)
            self.logger.debug("#### Verifying clients subscribed to publishers should follow rules even after publisher process restart ###")
            for i in range(0,len(self.inputs.compute_control_ips)):
                verification = self.verify_client_subscription_to_expected_publisher\
                (ds_ip, 'contrail-vrouter-agent:0', self.inputs.compute_control_ips[i], 'xmpp-server')
                if verification == False:
                    self.logger.error("Rule not behaving as expected")
                    result = False
            for i in range(0,len(self.inputs.compute_control_ips)):
                verification = self.verify_client_subscription_to_expected_publisher\
                (ds_ip, 'contrail-vrouter-agent:0', self.inputs.compute_control_ips[i], 'dns-server')
                if verification == False:
                    self.logger.error("Rule not behaving as expected")
                    result = False
            for i in range(0,len(self.inputs.compute_control_ips)):
                verification = self.verify_client_subscription_to_expected_publisher\
                (ds_ip, 'contrail-vrouter-agent:0', self.inputs.compute_control_ips[i], 'Collector')
                if verification == False:
                    self.logger.error("Rule not behaving as expected")
                    result = False
        except Exception as e:
            print '*** %s' % str(e)
        try:    
            self.logger.info("#### Deleting the rules at end of test acse ###")          
            for i in range(0,len(self.inputs.bgp_control_ips)):
                bgp_control_ip = self.inputs.bgp_control_ips[i].split('.')
                bgp_control_ip[3] = '0'
                bgp_control_ip = ".".join(bgp_control_ip) + "/24"
                self.delete_rule('default-discovery-service-assignment', bgp_control_ip,\
                                  'xmpp-server', bgp_control_ip, 'contrail-vrouter-agent:0')
                self.delete_rule('default-discovery-service-assignment', bgp_control_ip,\
                                  'dns-server', bgp_control_ip, 'contrail-vrouter-agent:0')
            for i in range(0,len(self.inputs.collector_control_ips)):
                collector_control_ip = self.inputs.collector_control_ips[i].split('.')
                collector_control_ip[3] = '0'
                collector_control_ip = ".".join(collector_control_ip) + "/24"
                self.delete_rule('default-discovery-service-assignment', collector_control_ip,\
                                  'Collector', collector_control_ip, 'contrail-vrouter-agent:0')
                self.read_rule('default-discovery-service-assignment')
        except Exception as e:
            print '*** %s' % str(e)
        self.logger.debug("#### Changing min and max TTL values to default after test completion ##")
        self.change_min_max_ttl()
        return result
        
    def verify_auto_load_balance_Ifmap(self, ds_ip=None):
        result = True
        if not ds_ip:
            ds_ip = self.inputs.cfgm_ip
        self.logger.debug("#### Changing min and max TTL values for testing purpose ##")
        self.change_min_max_ttl(ttl_min=60, ttl_max=60)
        self.logger.info("#### Restarting the required subscriber services so that TTL takes effect immediately ###")
        for ip in self.inputs.bgp_ips:
            self.inputs.restart_service('supervisor-control', [ip])
        for ip in self.inputs.bgp_ips:
            client_status = self.inputs.confirm_service_active('supervisor-control', ip)
            if client_status == False:
                self.logger.error("# Some issue happened after restart of client process #")
                result = False
                return result
        try:
            self.logger.debug("# Verifying that discovery server is properly load balancing for 'IfmapServer' at start of test # ")
            load_balance = self.check_load_balance(ds_ip, 'IfmapServer')
            if load_balance == False:
                result=False
        except Exception as e:
            print '*** %s' % str(e)        
        self.logger.info("# Setting auto load balance to true in contrail-discovery.conf file #")  
        self.set_auto_load_balance('IFMAPSERVER','TRUE')
        try:
            self.logger.debug("# Verifying that discovery server auto load balance for 'IfmapServer' #")
            self.logger.info("# Stopping the IfmapServer on one of the config node until it looses all subscribers #")
            self.inputs.stop_service('supervisor-config',host_ips=[self.inputs.cfgm_ips[0]])
            self.logger.debug("# Waiting for 100 seconds to wait for server to lose all subscriptions #")
            sleep(100)
            count = self.get_service_in_use(ds_ip, (self.inputs.cfgm_control_ips[0],'IfmapServer'))
            if count == 0:
                pass
            else:
                self.logger.error("# Even if Server is not running, it still has %d *in use* subscription. Something is wrong #" % count)
                result = False
            self.logger.info("# Starting the IfmapServer on one of the config node expecting that subscriptions will happen again #")
            self.inputs.start_service('supervisor-config',host_ips=[self.inputs.cfgm_ips[0]])
            client_status = self.inputs.confirm_service_active('supervisor-config',self.inputs.cfgm_ips[0])
            if client_status == False:
                self.logger.error("# Some issue happened after restart of config server #")
                result = False
                return result
            self.logger.debug("# Waiting for 60 seconds to wait for restarted server to again get all subscriptions #")
            sleep(60)
            self.logger.debug("# Verifying that auto load balance worked properly or not after service restart #")    
            load_balance = self.check_load_balance(ds_ip, 'IfmapServer')
            if load_balance == False:
                result=False
        except Exception as e:
            print '*** %s' % str(e) 
        self.logger.info("# Setting auto load balance to False in contrail-discovery.conf file #")  
        self.set_auto_load_balance('IFMAPSERVER','False')
        try:
            self.logger.debug("# Verifying that discovery server do not do auto load balance for *IfmapServer* as it is set to False #")
            self.logger.info("# Stopping the IfmapServer on one of the config node until it looses all subscribers #")
            self.inputs.stop_service('supervisor-config',host_ips=[self.inputs.cfgm_ips[0]])
            self.logger.debug("# Waiting for 100 seconds to wait for server to lose all subscriptions #")
            sleep(100)
            count = self.get_service_in_use(ds_ip, (self.inputs.cfgm_control_ips[0],'IfmapServer'))
            if count == 0:
                pass
            else:
                self.logger.error("# Even if Server is not running, it still has %d *in use* subscription. Something is wrong #" % count)
                result = False
            self.logger.info("# Starting the IfmapServer on one of the config node expecting that re-subscription will not happen again as auto load balance is off #")
            self.inputs.start_service('supervisor-config',host_ips=[self.inputs.cfgm_ips[0]])
            client_status = self.inputs.confirm_service_active('supervisor-config',self.inputs.cfgm_ips[0])
            if client_status == False:
                self.logger.error("# Some issue happened after restart of config server #")
                result = False
                return result
            self.logger.debug("# Waiting for 60 seconds to wait for restarted server to give time in case any client subscribes to this server. Not expecting this to happen #")
            sleep(60)
            self.logger.debug("# Verifying that as auto load balance was off, the restarted service is not used by any subscriber #")    
            count = self.get_service_in_use(ds_ip, (self.inputs.cfgm_control_ips[0],'IfmapServer'))
            if count == 0:
                pass
            else:
                self.logger.error("# Even if Server has just restarted and auto load balance is off, it has got new subscriptions. Something is wrong #")
                self.logger.error("# Total subscribers which got attached to restarted service are %d #" % count)
                result = False
        except Exception as e:
            print '*** %s' % str(e)  
        self.logger.debug("#### Changing min and max TTL values to default after test completion ##")
        self.change_min_max_ttl()
        return result   
    
    def verify_auto_load_balance_xmpp(self, ds_ip=None):
        result = True
        if not ds_ip:
            ds_ip = self.inputs.cfgm_ip
        self.logger.debug("#### Changing min and max TTL values for testing purpose ##")
        self.change_min_max_ttl(ttl_min=60, ttl_max=60)
        self.logger.info("#### Restarting the required subscriber services so that TTL takes effect immediately ###")
        for ip in self.inputs.compute_ips:
            self.inputs.restart_service('contrail-vrouter-agent', [ip])
        for ip in self.inputs.compute_ips:
            client_status = self.inputs.confirm_service_active('contrail-vrouter-agent', ip)
            if client_status == False:
                self.logger.error("# Some issue happened after restart of client process #")
                result = False
                return result
        try:
            self.logger.debug("# Verifying that discovery server is properly load balancing for 'XmppServer' at start of test #")
            load_balance = self.check_load_balance(ds_ip, 'xmpp-server')
            if load_balance == False:
                result=False
        except Exception as e:
            print '*** %s' % str(e)         
        self.logger.info("# Setting auto load balance to true in contrail-discovery.conf file #")  
        self.set_auto_load_balance('XMPP-SERVER','True')
        try:
            self.logger.debug("# Verifying that discovery server auto load balance for 'XmppServer' #")
            self.logger.info("# Stopping the XmppServer on one of the control node until it looses all subscribers #")
            self.inputs.stop_service('contrail-control',host_ips=[self.inputs.bgp_ips[0]])
            self.logger.debug("# Waiting for 20 seconds to wait for server to lose all subscriptions #")
            sleep(20)
            count = self.get_service_in_use(ds_ip, (self.inputs.bgp_control_ips[0],'xmpp-server'))
            if count == 0:
                self.logger.info("## After XMPP server is made down, it looses all subscriptions within 20 seconds")
                pass
            else:
                self.logger.error("# Even if Server is not running, it still has %d *in use* subscription. Something is wrong #" % count)
                result = False
            self.logger.info("# Starting the XmppServer on one of the control node expecting that subscriptions will happen again #")
            self.inputs.start_service('contrail-control',host_ips=[self.inputs.bgp_ips[0]])
            client_status = self.inputs.confirm_service_active('contrail-control',self.inputs.bgp_ips[0])
            if client_status == False:
                self.logger.error("# Some issue happened after restart of config server #")
                result = False
                return result
            self.logger.debug("# Waiting for 60 seconds to wait for restarted server to again get all subscriptions #")
            sleep(60)
            self.logger.debug("# Verifying that auto load balance worked properly or not after service restart #")    
            load_balance = self.check_load_balance(ds_ip, 'xmpp-server')
            if load_balance == False:
                result=False
        except Exception as e:
            print '*** %s' % str(e)
        self.logger.info("# Setting auto load balance to False in contrail-discovery.conf file #")  
        self.set_auto_load_balance('XMPP-SERVER','False')
        try:
            self.logger.debug("# Verifying that discovery server do not do auto load balance for *XmppServer* as it is set to False #")
            self.logger.info("# Stopping the XmppServer on one of the control node until it looses all subscribers #")
            self.inputs.stop_service('contrail-control',host_ips=[self.inputs.bgp_ips[0]])
            self.logger.debug("# Waiting for 20 seconds to wait for server to lose all subscriptions #")
            sleep(20)
            count = self.get_service_in_use(ds_ip, (self.inputs.bgp_control_ips[0],'xmpp-server'))
            if count == 0:
                self.logger.info("## After XMPP server is made down, it looses all subscriptions within 20 seconds")
                pass
            else:
                self.logger.error("# Even if Server is not running, it still has %d *in use* subscription. Something is wrong #" % count)
                result = False
            self.logger.info("# Starting the XmppServer on one of the control node expecting that re-subscription will not happen again as auto load balance is off #")
            self.inputs.start_service('contrail-control',host_ips=[self.inputs.bgp_ips[0]])
            client_status = self.inputs.confirm_service_active('contrail-control',self.inputs.bgp_ips[0])
            if client_status == False:
                self.logger.error("# Some issue happened after restart of config server #")
                result = False
                return result
            self.logger.debug("# Waiting for 60 seconds to wait for restarted server to give time in case any client subscribes to this server. Not expecting this to happen# ")
            sleep(60)
            self.logger.debug("# Verifying that as auto load balance was off, the restarted service is not used by any subscriber #")    
            count = self.get_service_in_use(ds_ip, (self.inputs.bgp_control_ips[0],'xmpp-server'))
            if count == 0:
                pass
            else:
                self.logger.error("# Even if Server has just restarted and auto load balance is off, it has got new subscriptions. Something is wrong #")
                self.logger.error("# Total subscribers which got attached to restarted service are %d #" % count)
                result = False
        except Exception as e:
            print '*** %s' % str(e)
        self.logger.debug("#### Changing min and max TTL values to default after test completion ##")
        self.change_min_max_ttl()
        return result
    
    def verify_auto_load_balance_collector(self, ds_ip=None):
        result = True
        if not ds_ip:
            ds_ip = self.inputs.cfgm_ip
        self.logger.debug("#### Changing min and max TTL values for testing purpose ##")
        self.change_min_max_ttl(ttl_min=60, ttl_max=60)
        self.logger.info("#### Restarting the required subscriber services so that TTL takes effect immediately ###")
        for ip in self.inputs.collector_ips:
            self.inputs.restart_service('supervisor-analytics', [ip])
        for ip in self.inputs.compute_ips:
            self.inputs.restart_service('supervisor-vrouter', [ip])
        for ip in self.inputs.bgp_ips:
            self.inputs.restart_service('supervisor-control', [ip])
        for ip in self.inputs.cfgm_ips:
            self.inputs.restart_service('supervisor-config', [ip])
        for ip in self.inputs.webui_ips:
            self.inputs.restart_service('supervisor-webui', [ip])
        for ip in self.inputs.database_ips:
            self.inputs.restart_service('contrail-database', [ip])
            self.inputs.restart_service('contrail-database-nodemgr', [ip])
        client_status = ContrailStatusChecker()
        client_status.wait_till_contrail_cluster_stable(self.inputs.host_ips)      
        self.logger.info("# Setting auto load balance to true in contrail-discovery.conf file #")  
        self.set_auto_load_balance('COLLECTOR','True')
        try:
            self.logger.debug("# Verifying that discovery server auto load balance for 'Collector'#")
            self.logger.info("# Stopping the Collector on one of the Analytic node until it looses all subscribers #")
            self.inputs.stop_service('contrail-collector',host_ips=[self.inputs.collector_ips[0]])
            self.logger.debug("# Waiting for 100 seconds to wait for server to lose all subscriptions #")
            sleep(100)
            count = self.get_service_in_use(ds_ip, (self.inputs.collector_control_ips[0],'Collector'))
            if count == 0:
                pass
            else:
                self.logger.error("# Even if Server is not running, it still has %d *in use* subscription. Something is wrong #" % count)
                result = False
            self.logger.info("# Starting the Collector on one of the Analytic node expecting that subscriptions will happen again #")
            self.inputs.start_service('contrail-collector',host_ips=[self.inputs.collector_ips[0]])
            client_status = self.inputs.confirm_service_active('contrail-collector',self.inputs.collector_ips[0])
            if client_status == False:
                self.logger.error("# Some issue happened after restart of config server#")
                result = False
                return result
            self.logger.debug("# Waiting for 60 seconds to wait for restarted server to again get all subscriptions #")
            sleep(60)
            self.logger.debug("# Verifying that auto load balance worked properly or not after service restart #")    
            load_balance = self.check_load_balance(ds_ip, 'Collector')
            if load_balance == False:
                result=False
        except Exception as e:
            print '*** %s' % str(e)  
        self.logger.info("# Setting auto load balance to False in contrail-discovery.conf file #")  
        self.set_auto_load_balance('COLLECTOR','False')
        try:
            self.logger.debug("# Verifying that discovery server do not do auto load balance for *Collector* as it is set to False #")
            self.logger.info("# Stopping the Collector on one of the Analytic node until it looses all subscribers #")
            self.inputs.stop_service('contrail-collector',host_ips=[self.inputs.collector_ips[0]])
            self.logger.debug("# Waiting for 100 seconds to wait for server to lose all subscriptions #")
            sleep(100)
            count = self.get_service_in_use(ds_ip, (self.inputs.collector_control_ips[0],'Collector'))
            if count == 0:
                pass
            else:
                self.logger.error("# Even if Server is not running, it still has %d *in use* subscription. Something is wrong #" % count)
                result = False
            self.logger.info("# Starting the Collector on one of the Analytic node expecting that re-subscription will not happen again as auto load balance is off # ")
            self.inputs.start_service('contrail-collector',host_ips=[self.inputs.collector_ips[0]])
            client_status = self.inputs.confirm_service_active('contrail-collector',self.inputs.collector_ips[0])
            if client_status == False:
                self.logger.error("# Some issue happened after restart of config server #")
                result = False
                return result
            self.logger.debug("# Waiting for 60 seconds to wait for restarted server to give time in case any client subscribes to this server. Not expecting this to happen #")
            sleep(60)
            self.logger.debug("# Verifying that as auto load balance was off, the restarted service is not used by any subscriber #")    
            count = self.get_service_in_use(ds_ip, (self.inputs.collector_control_ips[0],'Collector'))
            if count == 0:
                pass
            else:
                self.logger.error("# Even if Server has just restarted and auto load balance is off, it has got new subscriptions. Something is wrong #" )
                self.logger.error("# Total subscribers which got attached to restarted service are %d #" % count)
                result = False
        except Exception as e:
            print '*** %s' % str(e)  
        self.logger.debug("#### Changing min and max TTL values to default after test completion ##")
        self.change_min_max_ttl()
        return result  
    
    def verify_rules_preferred_over_auto_load_balance(self, ds_ip=None):
        result = True
        if not ds_ip:
            ds_ip = self.inputs.cfgm_ip
        self.logger.debug("#### Changing min and max TTL values for testing purpose ##")
        self.change_min_max_ttl(ttl_min=60, ttl_max=60)
        self.logger.info("#### Restarting the required subscriber services so that TTL takes effect immediately ###")
        for ip in self.inputs.compute_ips:
            self.inputs.restart_service('contrail-vrouter-agent', [ip])
        for ip in self.inputs.compute_ips:
            client_status = self.inputs.confirm_service_active('contrail-vrouter-agent', ip)
            if client_status == False:
                self.logger.error("# Some issue happened after restart of client process# ")
                result = False
                return result
        self.logger.info("# Setting auto load balance to true in contrail-discovery.conf file #")  
        self.set_auto_load_balance('XMPP-SERVER','True')
        self.logger.debug("# Waiting for 60 seconds to wait for auto load balance to happen #")
        sleep(60)
        try:
            self.logger.info("# Verifying that discovery server is properly load balancing for 'XmppServer' # ")
            load_balance = self.check_load_balance(ds_ip, 'xmpp-server')
            if load_balance == False:
                result=False
        except Exception as e:
            print '*** %s' % str(e)         
        if len(self.inputs.bgp_control_ips) > 0:
            self.logger.info("# Creating rules corresponding to *xmpp-server* so that all *contrail-vrouter-agent* on any network connects to *xmpp-server* running on cfgm0 #")
        for i in range(0,len(self.inputs.compute_control_ips)):
            self.create_rule('default-discovery-service-assignment', self.inputs.bgp_control_ips[0],\
                              'xmpp-server', self.inputs.compute_control_ips[i], 'contrail-vrouter-agent:0')
        self.read_rule('default-discovery-service-assignment')
        for i in range(0,len(self.inputs.compute_control_ips)): 
            result1 = self.find_rule('default-discovery-service-assignment', self.inputs.bgp_control_ips[0],\
                                      'xmpp-server', self.inputs.compute_control_ips[i], 'contrail-vrouter-agent:0')
            if result1 == False:
                self.logger.error("# While searching for the configured rule, it was not found. Configuration failed #")
                result = False
        self.logger.info("#### Waiting for 60 seconds so that TTL expiry for all subscriber happens ###")
        sleep (65)
        self.logger.info("#### Verifying that all vrouter-agents subscribe to control node xmpp-server only ###")
        try:
            in_use_list = []
            for i in range(0,len(self.inputs.bgp_control_ips)): 
                in_use_list_elem = self.get_service_in_use\
                (ds_ip, (self.inputs.bgp_control_ips[i],'xmpp-server'))
                in_use_list.append(in_use_list_elem)
            if in_use_list[0] > 0 and sum(in_use_list[1:len(in_use_list)]) == 0:
                self.logger.info("# Rule working as expected. All clients subscribed only to cfgm0 xmpp-server #")
                self.logger.info("# Even if Auto load balance is *True*, rule is taking the priority #")
                pass
            else:
                self.logger.error("# Even if rule is applied, rule is not working as expected. May be auto load balance being *True* is creating issue #")
                self.logger.error("# It was expected that only cfgm0 xmpp-server will have subscriptions and rest of the xmpp-servers will not have any subscriptions #")
                self.logger.error("# The *in-use* list for various xmpp-servers is coming out to be %s# " % in_use_list)
                result = False
        except Exception as e:
            print '*** %s' % str(e) 
        for i in range(0,len(self.inputs.compute_control_ips)): 
            self.delete_rule('default-discovery-service-assignment', self.inputs.bgp_control_ips[0],\
                              'xmpp-server', self.inputs.compute_control_ips[i], 'contrail-vrouter-agent:0')
        self.read_rule("default-discovery-service-assignment")
        for i in range(0,len(self.inputs.compute_control_ips)): 
            result1 = self.find_rule('default-discovery-service-assignment', self.inputs.bgp_control_ips[0],\
                                      'xmpp-server', self.inputs.compute_control_ips[i], 'contrail-vrouter-agent:0')
            if result1 == True:
                self.logger.error("# While searching for the deleted rule, it was found. Deletion failed #")
                result = False
        try:
            self.logger.info("# Waiting for 120 seconds(2 TTL cycles) to wait for re-subscription and load-balancing to happen after deleting rules #")
            sleep(120)   
            self.logger.info("# Verifying that discovery server auto load balance for 'XmppServer' as soon as rules are deleted #")
            load_balance = self.check_load_balance(ds_ip, 'xmpp-server')
            if load_balance == False:
                result=False
        except Exception as e:
            print '*** %s' % str(e)
        self.logger.info(" # Setting auto load balance to False in contrail-discovery.conf file #")  
        self.set_auto_load_balance('XMPP-SERVER','False')
        self.logger.debug("#### Changing min and max TTL values to default after test completion ##")
        self.change_min_max_ttl()
        return result


    def verify_service_in_use_list(self, ds_ip=None):
        result = True
        if not ds_ip:
            ds_ip = self.inputs.cfgm_ip
        try:
            self.logger.debug("#### Changing min and max TTL values for testing purpose ##")
            self.change_min_max_ttl(ttl_min=60, ttl_max=60)
            self.logger.info("# Verifying that if a subscriber has a service in use list, same publishers are assigned to it as mentioned in the list.# ")
            self.logger.info("#### Getting the in-use count of all Ifmap Servers before sending dummy subscribe request ###")
            in_use_list = []
            for i in range(0,len(self.inputs.cfgm_control_ips)): 
                in_use_list_elem = self.get_service_in_use(ds_ip, (self.inputs.cfgm_control_ips[i],'IfmapServer'))
                in_use_list.append(in_use_list_elem)
            sum_in_use_bfr_subscribe_request = sum(in_use_list)
            self.logger.info("#### Total in-use clients subscribed to IfmapServer are %d #####" % sum_in_use_bfr_subscribe_request)
            self.logger.info("#### Sending a dummy client request with instance value as 0 to subscribe to IfmapServer #####")
            self.logger.info("#### The dummy request will have a service-in-use-list containing IPs of all Ifmap Server present in the network #####")
            self.subscribe_service_from_discovery\
            (ds_ip, service="IfmapServer", instances="0", min_instances=len(self.inputs.cfgm_control_ips), \
             client_id=self.inputs.compute_names[0]+":TestClient", \
             remote_addr= self.inputs.compute_control_ips[0], client_type= "TestClient", \
             svc_in_use_list_present =True, svc_in_use_list=self.inputs.cfgm_control_ips)
            sleep(2)
            self.logger.info("#### Getting the in-use count of all Ifmap Servers after sending dummy subscribe request ###")
            in_use_list = []
            for i in range(0,len(self.inputs.cfgm_control_ips)): 
                in_use_list_elem = self.get_service_in_use(ds_ip, (self.inputs.cfgm_control_ips[i],'IfmapServer'))
                in_use_list.append(in_use_list_elem)
            sum_in_use_aftr_subscribe_request = sum(in_use_list)
            self.logger.info("#### Total in-use clients subscribed to IfmapServer after dummy request are %d #####" % sum_in_use_aftr_subscribe_request)
            client_subscribed_service_id = self.get_subscribed_service_id\
            (ds_ip, client=(self.inputs.compute_control_ips[0],"TestClient"), service="IfmapServer")
            instances_allocated = len(client_subscribed_service_id)
            service_IPs=[]
            for i in range (0,instances_allocated):
                    service_endpoint = self.get_service_endpoint_by_service_id(ds_ip,client_subscribed_service_id[i])
                    service_IPs.append(service_endpoint[0][0])
            self.logger.info("# The publishers mentioned in service-in-use list are %s and the client is actually subscribed to following publishers %s.######## " % (self.inputs.cfgm_control_ips,service_IPs))
            if instances_allocated == len(self.inputs.cfgm_control_ips) and \
            sum_in_use_aftr_subscribe_request > sum_in_use_bfr_subscribe_request:
                self.logger.info("# The subscribe request with instance as 0 and service-in-use list has subscribed to expected publishers.######## ")
            else:
                self.logger.info("# Something went wrong. Expected Publishers not assigned to the dummy client request having service in use list ######## ")
                result=False
            self.logger.info("##### Waiting for 60 seconds so that dummy client request ages out and do not interfere with other test cases ######")
            sleep(60)    
        except Exception as e:
            print '*** %s' % str(e)
        self.logger.debug("#### Changing min and max TTL values to default after test completion ##")
        self.change_min_max_ttl()         
        return result
    
    def verify_white_list_security(self, ds_ip=None):
        result = True
        if not ds_ip:
            ds_ip = self.inputs.cfgm_ip
        try:
            self.logger.debug("#### Changing min and max TTL values for testing purpose ##")
            self.change_min_max_ttl(ttl_min=60, ttl_max=60)
            self.logger.info("# Configure white list for publishers and subscriber in contrail-discovery.conf file # ")
            self.white_list_publishers_conf_file('1.1.1.0/24', '2.2.2.0/24')
            self.white_list_subscribers_conf_file('1.1.1.0/24', '2.2.2.0/24')
            DiscoveryServerUtils.POST_HEADERS = {'Content-type': 'application/json'\
                                                  , 'X-Forwarded-For': "1.1.1.1"}
            self.logger.info("#### Sending a synthetic publish request to verify publishers white list  ###")
            response = self.publish_service_to_discovery(ds_ip,service="Test_Pub_1",ip="1.1.1.1", port ="123")
            if self.get_all_services_by_service_name(ds_ip, service="Test_Pub_1") == []:
                result = False
                self.logger.error("#### Failure!! The requested publish request not accepted by discovery server even if the IP was present in Publisher white list  ###")
            else:
                self.logger.info("#### Success!! The requested publish request accepted by discovery server as IP was present in Publisher white list  ###")
            sleep(2)
            DiscoveryServerUtils.POST_HEADERS = {'Content-type': 'application/json' , 'X-Forwarded-For': "3.3.3.3"}
            response = self.publish_service_to_discovery(ds_ip,service="Test_Pub_2",ip="3.3.3.3", port ="123")
            if self.get_all_services_by_service_name(ds_ip, service="Test_Pub_2") == []:
                 self.logger.info("#### Success!! The requested publish request not accepted by discovery as IP was not present in Publisher white list  ###")
            else:
                result = False
                self.logger.error("#### Failure!! The requested publish request accepted by discovery server even if the IP was not present in Publisher white list  ###")
            self.logger.info("#### Sending a synthetic subscribe request to verify subscribers white list  ###")
            DiscoveryServerUtils.POST_HEADERS = {'Content-type': 'application/json' , 'X-Forwarded-For': "2.2.2.2"}
            self.subscribe_service_from_discovery(ds_ip, service="IfmapServer", instances="2", \
                                                  client_id=self.inputs.compute_names[0]+":TestClient_1", \
                                                  remote_addr= self.inputs.compute_control_ips[0],\
                                                   client_type= "TestClient_1")
            if self.get_subscribed_service_id(ds_ip, client=(self.inputs.compute_control_ips[0],\
                                                             "TestClient_1"), service="IfmapServer") == []:
                result = False
                self.logger.error("#### Failure!! The requested subscribe request not accepted by discovery server even if the IP was present in Subscriber white list  ###")
            else:
                self.logger.info("#### Success!! The requested subscribe request accepted by discovery server as IP was present in Subscriber white list  ###") 
            DiscoveryServerUtils.POST_HEADERS = {'Content-type': 'application/json' , \
                                                 'X-Forwarded-For': "3.3.3.3"}
            self.subscribe_service_from_discovery(ds_ip, service="IfmapServer",\
                                                   instances="2", \
                                                   client_id=self.inputs.compute_names[0]+":TestClient_2", \
                                                   remote_addr= self.inputs.compute_control_ips[0], \
                                                   client_type= "TestClient_2")
            if self.get_subscribed_service_id(ds_ip, client=(self.inputs.compute_control_ips[0],\
                                                             "TestClient_2"), service="IfmapServer") == []:
                self.logger.info("#### Success!! The requested subscribe request not accepted by discovery server as IP was not present in Subscriber white list  ###") 
            else:
                result = False
                self.logger.error("#### Failure!! The requested subscribe request accepted by discovery server even if the IP was not present in Subscriber white list  ###")
            self.logger.info("# Deleting the configurations of white list to clean up for next test case # ")
            self.delete_white_list(publish=True, subscribe=True)
            self.logger.info("# Verify that when white list is deleted, then X-Forwarded-Header does not hold relevance and all requests are accepted # ")
            response = self.publish_service_to_discovery(ds_ip,service="Test_Pub_2",ip="3.3.3.3", port ="123")
            if self.get_all_services_by_service_name(ds_ip, service="Test_Pub_2") == []:
                result = False
                self.logger.error("#### Failure!! The requested publish request not accepted by discovery server even after deleting publish white list  ###")   
            else:
                self.logger.info("#### Success!! The requested publish request accepted by discovery server as Publisher white list has been deleted ###")
            self.subscribe_service_from_discovery(ds_ip, service="IfmapServer", instances="2",\
                                                   client_id=self.inputs.compute_names[0]+":TestClient_2", \
                                                   remote_addr= self.inputs.compute_control_ips[0], \
                                                   client_type= "TestClient_2")
            if self.get_subscribed_service_id(ds_ip, client=(self.inputs.compute_control_ips[0],\
                                                             "TestClient_2"), service="IfmapServer") == []: 
                result = False
                self.logger.error("#### Failure!! The requested subscribe request not accepted by discovery server even if Subscriber white list has been deleted  ###")
            else:
                self.logger.info("#### Success!! The requested subscribe request accepted by discovery server as Subscriber white list has been deleted  ###")
            self.logger.info("##### Waiting for 60 seconds so that dummy client request ages out and do not interfere with other test cases ######")
            sleep(60)
        except Exception as e:
            print '*** %s' % str(e)
        DiscoveryServerUtils.POST_HEADERS = {'Content-type': 'application/json'}
        self.logger.debug("#### Changing min and max TTL values to default after test completion ##")
        self.change_min_max_ttl()         
        return result
    
    def verify_keystone_auth_security(self, ds_ip=None):
        result = True
        if not ds_ip:
            ds_ip = self.inputs.cfgm_ip
        try:
            self.logger.info("# Configure authentication as *True* in contrail-discovery.conf file # ")
            self.add_keystone_auth_conf_file(auth="keystone", add_values = "False")
            self.logger.debug("# Verify that all requests fails if Auth is True and credentials are not mentioned # ")
            response = self.publish_requests_with_keystone(ds_ip,operation="oper-state", \
                                                           operation_status="up", service_id=self.inputs.cfgm_names[0],\
                                                            service_type="IfmapServer")
            if response != 200:
                self.logger.info("Success!! As authetication is True and credentials are not configured, the oper-state change request has failed")
            else:
                self.logger.error("Failure!! Even if authetication is True and credentials are not configured, the oper-state change request is successful")
                result = False
            response = self.publish_requests_with_keystone(ds_ip,operation="admin-state", \
                                                           operation_status="up", service_id=self.inputs.cfgm_names[0],\
                                                            service_type="IfmapServer")
            if response != 200:
                self.logger.info("Success!! As authetication is True and credentials are not configured, the admin-state change request has failed")
            else:
                self.logger.error("Failure!! Even if authetication is True and credentials are not configured, the admin-state change request is successful")
                result = False
            response = self.publish_requests_with_keystone(ds_ip,operation="load-balance", \
                                                           service_id=self.inputs.cfgm_names[0],\
                                                            service_type="IfmapServer")
            if response != 200:
                self.logger.info("Success!! As authetication is True and credentials are not configured, the load-balance request has failed")
            else:
                self.logger.error("Failure!! Even if authetication is True and credentials are not configured, the load-balance request is successful")
                result = False
            self.logger.info("# Configure authentication as *True* as well as configuring all the required credentials in contrail-discovery.conf file # ")
            self.add_keystone_auth_conf_file(auth="keystone", add_values = "True")
            self.logger.info("# Verify that all requests are passed if Auth is True and credentials are mentioned # ")
            response = self.publish_requests_with_keystone(ds_ip,operation="oper-state", \
                                                           operation_status="up", service_id=self.inputs.cfgm_names[0],\
                                                            service_type="IfmapServer")
            if response == 200:
                self.logger.info("Success!! As authetication is True and credentials are configured, the oper-state change request has been processed successfully")
            else:
                self.logger.error("Failure!! Even if authetication is True and credentials are configured, the oper-state change request has failed")
                result = False
            response = self.publish_requests_with_keystone(ds_ip,operation="admin-state",\
                                                            operation_status="up", service_id=self.inputs.cfgm_names[0],\
                                                             service_type="IfmapServer")
            if response == 200:
                self.logger.info("Success!! As authetication is True and credentials are configured, the admin-state change request has been processed successfully")
            else:
                self.logger.error("Failure!! Even if authetication is True and credentials are  configured, the admin-state change request has failed")
                result = False
            response = self.publish_requests_with_keystone(ds_ip,operation="load-balance", \
                                                           service_id=self.inputs.cfgm_names[0], \
                                                           service_type="IfmapServer")
            if response == 200:
                self.logger.info("Success!! As authetication is True and credentials are configured, the load-balance request has been processed successfully")
            else:
                self.logger.error("Failure!! Even if authetication is True and credentials are configured, the load-balance request has failed")
                result = False
        except Exception as e:
            print '*** %s' % str(e)
        self.logger.debug("# Deleting the auth configurations from contrail-discovery.conf file # ")
        self.delete_keystone_auth_conf_file(auth="keystone")       
        return result
    
    def verify_policy_fixed(self, ds_ip=None):
        result = True
        if not ds_ip:
            ds_ip = self.inputs.cfgm_ip
        try:
            self.logger.debug("#### Changing min and max TTL values for testing purpose ##")
            self.change_min_max_ttl(ttl_min=60, ttl_max=60)
            self.logger.info("#### Making policy as *fixed* for test publisher  ##")
            self.set_policy("TEST_PUB",'fixed')
            self.logger.info("#### Sending 3 synthetic publish requests of same Publisher type  ###")
            def publish_request():
                for i in range(0,100):
                    response_1 = self.publish_service_to_discovery(ds_ip,service="TEST_PUB",\
                                                                   ip="1.1.1.1", port ="123")
                    response_2 = self.publish_service_to_discovery(ds_ip,service="TEST_PUB",\
                                                                   ip="2.2.2.2", port ="123")
                    response_3 = self.publish_service_to_discovery(ds_ip,service="TEST_PUB",\
                                                                   ip="3.3.3.3", port ="123")
                    sleep(5)
            obj_1 = Process(target=publish_request)
            obj_1.start()
            sleep(1)
            if self.get_service_status(ds_ip,service_tuple=("1.1.1.1","TEST_PUB")) == "up" \
            and self.get_service_status(ds_ip,service_tuple=("2.2.2.2","TEST_PUB")) == "up" \
            and self.get_service_status(ds_ip,service_tuple=("3.3.3.3","TEST_PUB")) == "up":
                self.logger.info("#### All publishers have registered to discovery server successfully.###")
            else:
                self.logger.error("#### Either or all Publishers have not registered to discovery server. No sense of proceeding the test case. Exiting. ###")
                result = False
                return result
            self.logger.info("#### Sending 3 synthetic subscribe requests with instance value 2 to subscribe to Publisher *TEST_PUB*  ###")
            self.subscribe_service_from_discovery(ds_ip, service="TEST_PUB", instances="2", \
                                                  client_id="1.1.1.1:TestClient", remote_addr= "1.1.1.1", \
                                                  client_type= "TestClient")
            self.subscribe_service_from_discovery(ds_ip, service="TEST_PUB", instances="2", \
                                                  client_id="2.2.2.2:TestClient", remote_addr= "2.2.2.2", \
                                                  client_type= "TestClient")
            self.subscribe_service_from_discovery(ds_ip, service="TEST_PUB", instances="2", \
                                                  client_id="3.3.3.3:TestClient", remote_addr= "3.3.3.3", \
                                                  client_type= "TestClient")
            self.logger.debug("#### Verifying the in use count of publishers are subscribe request ###")
            p1_in_use_count = self.get_service_in_use(ds_ip,("1.1.1.1","TEST_PUB"))
            p2_in_use_count = self.get_service_in_use(ds_ip,("2.2.2.2","TEST_PUB"))
            p3_in_use_count = self.get_service_in_use(ds_ip,("3.3.3.3","TEST_PUB"))
            publisher_in_use_list = [p1_in_use_count, p2_in_use_count, p3_in_use_count]
            if sum(publisher_in_use_list) == 6 and 0 in publisher_in_use_list:
                self.logger.info("#### Clients subscribed successfully to publishers and policy as *fixed* working as expected ##")
            else:
                self.logger.error("#### Subscription not as expected. The in use list looks like %s  ##" % publisher_in_use_list)
                result = False
            self.logger.debug("#### Stopping one of the in use Publisher for extended period (> 15 seconds) to decrease it's priority ##")
            obj_1.terminate()
            index_first_pub_used = publisher_in_use_list.index(3)
            def new_publish_request():
                for i in range(0,100):
                    if index_first_pub_used == 0:
                        response_2 = self.publish_service_to_discovery(ds_ip,service="TEST_PUB",\
                                                                       ip="2.2.2.2", port ="123")
                        response_3 = self.publish_service_to_discovery(ds_ip,service="TEST_PUB",\
                                                                       ip="3.3.3.3", port ="123")
                    elif index_first_pub_used == 1:
                        response_1 = self.publish_service_to_discovery(ds_ip,service="TEST_PUB",\
                                                                       ip="1.1.1.1", port ="123")
                        response_3 = self.publish_service_to_discovery(ds_ip,service="TEST_PUB",\
                                                                       ip="3.3.3.3", port ="123")
                    sleep(5)
            new_obj=Process(target =new_publish_request)
            new_obj.start()
            self.logger.debug("#### Waiting for 90 seconds so that all subscriptions are lost ##")
            sleep(90)
            self.logger.debug("#### Again starting the stopped publishers and hoping that its priority has been reduced and it will not be used by the clients any more##")
            new_obj.terminate()
            obj_2 = Process(target=publish_request)
            obj_2.start()
            sleep(1)
            self.logger.info("#### Again sending 3 synthetic subscribe requests with instance value 2 to subscribe to Publisher *TEST_PUB*  ###")
            self.subscribe_service_from_discovery(ds_ip, service="TEST_PUB", instances="2", \
                                                  client_id="1.1.1.1:TestClient", remote_addr= "1.1.1.1",\
                                                   client_type= "TestClient")
            self.subscribe_service_from_discovery(ds_ip, service="TEST_PUB", instances="2", \
                                                  client_id="2.2.2.2:TestClient", remote_addr= "2.2.2.2",\
                                                   client_type= "TestClient")
            self.subscribe_service_from_discovery(ds_ip, service="TEST_PUB", instances="2", \
                                                  client_id="3.3.3.3:TestClient", remote_addr= "3.3.3.3",\
                                                   client_type= "TestClient")
            self.logger.debug("#### Verifying the in use count of publishers are subscribe request ###")
            p1_in_use_count = self.get_service_in_use(ds_ip,("1.1.1.1","TEST_PUB"))
            p2_in_use_count = self.get_service_in_use(ds_ip,("2.2.2.2","TEST_PUB"))
            p3_in_use_count = self.get_service_in_use(ds_ip,("3.3.3.3","TEST_PUB"))
            publisher_in_use_list = [p1_in_use_count, p2_in_use_count, p3_in_use_count]
            if sum(publisher_in_use_list) == 6 and publisher_in_use_list.index(index_first_pub_used) == 0:
                self.logger.info("#### Clients subscribed successfully to publishers and policy as *fixed* working as expected ##")
                self.logger.info("#### Clients not subscribed to publisher which went down for time more than extended perios as it's priority has been decreased ##")
            else:
                self.logger.error("#### Subscription not as expected. The in use list looks like %s  ##" % publisher_in_use_list)
                self.logger.error("#### Clients might have subscribed to publisher which went down. this means priority of that publisher was not decreased ##")
                result = False
            obj_2.terminate()
            self.logger.info("#### Deleting the policy configurations from .conf file ##")
            self.del_policy("TEST_PUB")
            self.logger.debug("#### Changing min and max TTL values to default after test completion ##")
            self.change_min_max_ttl()
            self.logger.debug("#### Waiting for dummy Publish and subscribe requests to expire  ##")
            sleep(60)
            self.cleanup_service_from_discovery(ds_ip)
        except Exception as e:
            print '*** %s' % str(e)   
        return result

    def verify_rule_do_not_affect_other_dns_subscriptions(self, ds_ip=None):
        result = True
        if not ds_ip:
            ds_ip = self.inputs.cfgm_ip
        self.logger.debug("#### Changing min and max TTL values for testing purpose ##")
        self.change_min_max_ttl(ttl_min=60, ttl_max=60)
        self.logger.info("#### Restarting the required subscriber services so that TTL takes effect immediately ###")
        for ip in self.inputs.compute_ips:
            self.inputs.restart_service('contrail-vrouter-agent', [ip])
        for ip in self.inputs.compute_ips:
            client_status = self.inputs.confirm_service_active('contrail-vrouter-agent', ip)
            if client_status == False:
                self.logger.error("Some issue happened after restart of client process")
                result = False
                return result
        self.logger.info("# Finding the subscriptions of all vrouter-agents to DNS-server before creating a rule# ")
        all_vrouter_pub_IPs_bfr_rule = []
        for i in range(0,len(self.inputs.compute_control_ips)):  
            client_subscribed_service_id = self.get_subscribed_service_id\
            (ds_ip, client=(self.inputs.compute_control_ips[i],"contrail-vrouter-agent:0"),\
              service="dns-server")
            instances_allocated = len(client_subscribed_service_id)
            service_IPs = []
            for k in range (0,instances_allocated):
                service_endpoint = self.get_service_endpoint_by_service_id\
                (ds_ip,client_subscribed_service_id[k])
                service_IPs.append(service_endpoint[0][0])
            self.logger.debug("Contrail-vrouter-agent running on %s is subscribed to DNS-server running at %s" % (self.inputs.compute_control_ips[i],service_IPs))
            all_vrouter_pub_IPs_bfr_rule.append(service_IPs)
        self.logger.info("## Creating a rule for 1 of the vrouter-agent subscriber")
        self.create_rule('default-discovery-service-assignment', self.inputs.bgp_control_ips[0], \
                        'dns-server', self.inputs.compute_control_ips[0], 'contrail-vrouter-agent:0')
        self.read_rule('default-discovery-service-assignment')
        result1 = self.find_rule('default-discovery-service-assignment', self.inputs.bgp_control_ips[0],
                                 'dns-server', self.inputs.compute_control_ips[0], 'contrail-vrouter-agent:0')
        if result1 == False:
            self.logger.error("While searching for the configured rule, it was not found. Configuration failed")
            result = False
        self.logger.info("#### Waiting for 60+10 seconds so that TTL expiry for all subscriber happens and 10 seconds for all other re-subscriptions (bug) ###")
        sleep (70)
        self.logger.info("# Finding the subscriptions of all vrouter-agents to DNS-server after creating a rule# ")
        all_vrouter_pub_IPs_aftr_rule = []
        for i in range(0,len(self.inputs.compute_control_ips)):  
            client_subscribed_service_id = self.get_subscribed_service_id\
            (ds_ip, client=(self.inputs.compute_control_ips[i],"contrail-vrouter-agent:0"), \
             service="dns-server")
            instances_allocated = len(client_subscribed_service_id)
            service_IPs = []
            for k in range (0,instances_allocated):
                service_endpoint = self.get_service_endpoint_by_service_id\
                (ds_ip,client_subscribed_service_id[k])
                service_IPs.append(service_endpoint[0][0])
            self.logger.debug("Contrail-vrouter-agent running on %s is subscribed to DNS-server running at %s" % (self.inputs.compute_control_ips[i],service_IPs))
            all_vrouter_pub_IPs_aftr_rule.append(service_IPs)
        if all_vrouter_pub_IPs_aftr_rule[0][0] == self.inputs.bgp_control_ips[0] and len(all_vrouter_pub_IPs_aftr_rule[0]) == 1:
            self.logger.debug("The rule has worked properly")
            for i in range(1,len(all_vrouter_pub_IPs_aftr_rule)):
                if  all_vrouter_pub_IPs_aftr_rule[i] ==  all_vrouter_pub_IPs_bfr_rule[i]:
                    self.logger.debug("No change has happened in other subscriptions due to rule.")
                else:
                    result = False
                    self.logger.error("The publisher assigned to contrail-vrouter agent running on %s were %s and has changed to %s" % (self.inputs.compute_control_ips[i],all_vrouter_pub_IPs_bfr_rule[i],all_vrouter_pub_IPs_aftr_rule[i])) 
        else:
            self.logger.error("Rule has not worked as expected")
            self.logger.debug("Subscriber %s has subscribed to %s Publisher instead of subscribing only to %s" % (self.inputs.compute_control_ips[i],all_vrouter_pub_IPs_aftr_rule[0],self.inputs.bgp_control_ips[0]) )
            result = False
        self.logger.info("# Deleting the rule after the test is complete # ")
        self.delete_rule('default-discovery-service-assignment', self.inputs.bgp_control_ips[0], \
                             'dns-server', self.inputs.compute_control_ips[0], 'contrail-vrouter-agent:0')
        result1 = self.find_rule('default-discovery-service-assignment', self.inputs.bgp_control_ips[0],\
                          'dns-server', self.inputs.compute_control_ips[0], 'contrail-vrouter-agent:0')
        if result1 == True:
            self.logger.error("While searching for the deleted rule, it was found. Deletion failed")
            result = False
        self.logger.debug("#### Changing min and max TTL values to default after test completion ##")
        self.change_min_max_ttl()
        return result
    
