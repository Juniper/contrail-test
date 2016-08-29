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
from vnc_api.vnc_api import *
from vnc_api.gen.resource_xsd import *
from httplib import FOUND
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
        self.ds_port = inputs.ds_port
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
        self.logger.debug(
            "Calculated dns services as per the testbed file..%s" %
            (publisher_tuple))
        return publisher_tuple

    def get_all_api_services_by_topology(self):

        publisher_tuple = []
        self.logger.debug("Calculating api services as per the testbed file..")
        services = ['ApiServer']
        for service in services:
            for host in self.inputs.cfgm_names:
                control_ip = self.inputs.host_data[host]['host_control_ip']
                # t=(ip,service)
                t = (control_ip, service)
                publisher_tuple.append(t)
        self.logger.debug(
            "Calculated api services as per the testbed file..%s" %
            (publisher_tuple))
        return publisher_tuple

    def get_all_ifmap_services_by_topology(self):

        publisher_tuple = []
        self.logger.debug(
            "Calculating ifmap services as per the testbed file..")
        services = ['IfmapServer']
        for service in services:
            for host in self.inputs.cfgm_names:
                control_ip = self.inputs.host_data[host]['host_control_ip']
                # t=(ip,service)
                t = (control_ip, service)
                publisher_tuple.append(t)
        self.logger.debug(
            "Calculated ifmap services as per the testbed file..%s" %
            (publisher_tuple))
        return publisher_tuple

    def get_all_collector_services_by_topology(self):

        publisher_tuple = []
        self.logger.debug(
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
        self.logger.debug(
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
            self.logger.debug(e)
            raise
        finally:
            self.logger.debug(
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
            self.logger.debug(e)
        finally:
            self.logger.debug("Registered api services %s %s" %
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
            self.logger.debug(e)
            raise
        finally:
            self.logger.debug("Registered ifmap services in discovery %s %s" %
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
            self.logger.debug(e)
            raise
        finally:
            self.logger.debug("Registered dns services in discovery %s %s" %
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
            self.logger.debug(e)
            raise
        finally:
            self.logger.debug("Registered contrail-analytics-apis in discovery %s %s" %
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
            self.logger.debug(e)
            raise
        finally:
            self.logger.debug("Registered in discovery %s %s..%s" %
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
            self.logger.debug(e)
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
            self.logger.debug(str(e))
        finally:
            if resp:
                print 'resp: %s' % (resp)
                return resp
    # end update_service

    def subscribe_service_from_discovery(self, ds_ip, service=None, instances=None, client_id=None, 
        remote_addr=None, client_type=None, min_instances=0, svc_in_use_list_present= False ,
        svc_in_use_list = []):
        '''http://discovery-server-ip:5998/subscribe'''

        obj = None
        try:
            obj = self.ds_inspect[ds_ip].subscribe_service(
                service=service, instances=instances, client_id=client_id, remote_addr=remote_addr, 
                client_type=client_type, min_instances=min_instances, 
                svc_in_use_list_present = svc_in_use_list_present, svc_in_use_list = svc_in_use_list)
        except Exception as e:
            self.logger.debug(e)
            raise
        finally:
            return obj

    def cleanup_service_from_discovery(self, ds_ip):
        '''http://discovery-server-ip:5998/cleanup'''

        obj = None
        try:
            obj = self.ds_inspect[ds_ip].cleanup_service()
        except Exception as e:
            self.logger.debug(e)
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
                if ip == elem['info']['ip-address'] and elem['status'] == service_status and ignore_status ==False:
                    status = elem['service_id']
                elif ip == elem['info']['ip-address'] and ignore_status ==True:
                    status = elem['service_id']
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
                if ip == elem['info']['ip-address'] and \
                    elem['status'] == service_status and ignore_status ==False:
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
            self.logger.debug(e)
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
            self.logger.debug(e)
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
            self.logger.debug(e)
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
            self.logger.debug(e)
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
            self.logger.debug(e)
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
            d_name = get_host_domain_name(self.inputs.host_data[ds_ip])
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
                try:
                    host_name = self.get_hostname_from_hostdata_by_ip(client_ip)
                    client_id = '%s:%s' % (host_name, client_svc)
                    dct = obj.get_attr('Clients', match=('client_id', client_id))
                except socket.herror,e:
                    self.logger.debug('No hostname got for IP %s' %(client_ip))
                    self.logger.debug('Got this instead: %s' % (str(e)))

            for elem in dct:
                if service in elem['service_type']:
                    client_type = elem['client_type']
                    if re.search(client_svc, client_type):
                        service_id.append(elem['service_id'])
        except Exception as e:
            self.logger.debug(e)
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
            self.logger.debug(e)
        finally:
            return control_nodes
        
    def get_all_xmpp_servers(self, ds_ip):
        try:
            obj = self.ds_inspect[ds_ip].get_ds_clients()
            dct = obj.get_attr('Clients', match=('service_type', 'xmpp-server'))
            service_id = []
            for elem in dct:
                if ('contrail-vrouter-agent:0' == elem['client_type']):
                    t2 = elem['service_id']
                    service_id.append(t2)
        except Exception as e:
            self.logger.debug(e)
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
    
    def skip_discovery_test(self, server, min_instances, different_subnet_flag = False):
        '''
        This proc verifies that setup is capable for running multi node
        discovery test or not.
        Assumptions:
        1. Config, control and analytic operations are running on same node.
        2. Compute operations are running seperately.
        '''
        if server == "xmpp-server" or server == "dns-server":
            if len(self.inputs.bgp_ips) >= min_instances and \
                    len(self.inputs.compute_ips) >= min_instances:
                self.logger.debug("Expected number of publishers present")
                pub_ips = self.inputs.bgp_ips
                pub_control_ips = self.inputs.bgp_control_ips
                sub_control_ips = self.inputs.compute_control_ips
            else:
                self.logger.error("Expected number of publishers not present")
                skip = True
                msg = "Skipping because setup requirements are not met"
                raise testtools.TestCase.skipException(msg)
        if server == "IfmapServer" or server == "ApiServer":
            if len(self.inputs.cfgm_ips) >= min_instances:
                self.logger.debug("Expected number of publishers present")
                pub_ips = self.inputs.cfgm_ips
                pub_control_ips = self.inputs.cfgm_control_ips
                sub_control_ips = self.inputs.bgp_control_ips
            else:
                self.logger.error("Expected number of publishers not present")
                skip = True
                msg = "Skipping because setup requirements are not met"
                raise testtools.TestCase.skipException(msg)
        if server == "Collector" or server == "OpServer":
            if len(self.inputs.collector_ips) >= min_instances:
                self.logger.debug("Expected number of publishers present")
                pub_ips = self.inputs.collector_ips
                pub_control_ips = self.inputs.collector_control_ips
                sub_control_ips = self.inputs.compute_control_ips 
            else:
                self.logger.error("Expected number of publishers not present")
                skip = True
                msg = "Skipping because setup requirements are not met"
                raise testtools.TestCase.skipException(msg)  
        if different_subnet_flag == True:
            # Check for all publishers are in different network
            pub_network_ips = []
            sub_network_ips = []
            for ip in pub_control_ips:
                ip = ip.split('.')
                ip[3] = '0'
                network_ip = ".".join(ip) + "/24"
                pub_network_ips.append(network_ip)
            if any(x == pub_network_ips[0] for x in pub_network_ips[1:]):
                self.logger.error("Any 2 servers are in same network")
                skip = True
                msg = "Skipping because setup requirements are not met"
                raise testtools.TestCase.skipException(msg)
            else:
                self.logger.debug("All publishers are in different networks as expected")
            for ip in sub_control_ips:
                ip = ip.split('.')
                ip[3] = '0'
                network_ip = ".".join(ip) + "/24"
                sub_network_ips.append(network_ip)
            if any(x == sub_network_ips[0] for x in sub_network_ips[1:]):
                self.logger.error("Any 2 servers are in same network")
                skip = True
                msg = "Skipping because setup requirements are not met"
                raise testtools.TestCase.skipException(msg)
            else:
                self.logger.debug("All subscribers are in different networks as expected")
            if set(sub_network_ips) == set(pub_network_ips):
                self.logger.debug("Publisher and Subscriber pairs in same networks as expected")
            else:
                self.logger.error("Even if all publishers and subscribers are in different \
                network, a pair of publisher and subscribers lies in different network")
                skip = True
                msg = "Skipping because setup requirements are not met"
                raise testtools.TestCase.skipException(msg)
            # Check for all publishers are having mask as /24
            subnet_list = []
            for ip in pub_ips:
                output = self.inputs.run_cmd_on_server(ip, "ifconfig")
                index = pub_ips.index(ip)
                if self.inputs.get_os_version(ip) == "ubuntu":
                    subnet_string = ".*inet addr:%s.*Mask:(.*)" % \
                                pub_control_ips[index]
                else :
                    subnet_string = ".*inet %s.*netmask:(.*)" % \
                                pub_control_ips[index]
                control_ip_details = re.search(subnet_string, output)
                subnet = control_ip_details.group(1)
                subnet_list.append(subnet.strip())
            if all(x == "255.255.255.0" for x in subnet_list):
                self.logger.debug("All publishers are in /24 network as expected")
            else:
                self.logger.error("Any or all publishers not having mask as /24")
                skip = True
                msg = "Skipping because setup requirements are not met"
                raise testtools.TestCase.skipException(msg)

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
            self.logger.debug(e)
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

    def _check_missing_regd_services(self, expected, registered, service_type):
        diff = set(expected) ^ set(registered)
        if diff:
            self.logger.warn("Inconsistency in registerd services %s" % (diff))
            self.logger.warn("Expected %s services :%s" % (service_type, 
                expected))
            self.logger.warn("But observed %s services :%s" % (service_type,
                registered))
            return False
        else:
            self.logger.info("Validated %s services registered to ",
                "discovery service: %s" % (expected))        
            return True
    # end _check_missing_regd_services

    def _check_service_state(self, registered_services, service_type, ds_ip):
        self.logger.debug("Checking for %s service" % (service_type))
        for service in registered_services:
            t = {}
            service_id = self.get_service_id_by_service_end_point(
                ds_ip, service_tuple=service)
            t = self.get_service_status_by_service_id(
                ds_ip, service_id=service_id)
            self.logger.debug("Service health: %s" % (t))
            if (t['admin_state'] == 'up'and t['status'] == 'up'):
                self.logger.debug("%s service is up" % (str(service)))
                result = True
            else:
                self.logger.warn("%s service not up" % (str(service)))
                result = False
        return result
    # end _check_service_state

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
        result = result and self._check_missing_regd_services(
            expected_control_services,
            registered_control_services,
            'control')

        result = result and self._check_missing_regd_services(
            expected_collector_services,
            registered_collector_services,
            'collector')

        result = result and self._check_missing_regd_services(
            expected_api_services,
            registered_api_services,
            'api')

        result = result and self._check_missing_regd_services(
            expected_opserver,
            registered_opserver,
            'opserver')

        result = result and self._check_missing_regd_services(
            expected_dns_services,
            registered_dns_services,
            'dns')

        # Verifying the service provision state/status/admin state
        self.logger.debug("Checking for control node service")
        result = result and self._check_service_state(registered_control_services,
            'control', ds_ip)

        self.logger.debug("Checking for api service")
        result = result and self._check_service_state(registered_api_services,
            'api', ds_ip)

        self.logger.debug("Checking for ifmap service")
        result = result and self._check_service_state(registered_ifmap_services,
            'ifmap', ds_ip)

        self.logger.debug("Checking for collector service")
        result = result and self._check_service_state(registered_collector_services,
            'collector', ds_ip)

        self.logger.debug("Checking for dns service")
        result = result and self._check_service_state(registered_dns_services,
            'dns', ds_ip)

        self.logger.debug("Checking for opserver")
        result = result and self._check_service_state(registered_opserver,
            'opserver', ds_ip)

        if result:
            self.logger.info('Validated that all expected services are present',
                ', registered with discovery and are up')
        else:
            self.logger.warn('One or more service verifications failed')

        return result

    @retry(delay=1, tries=10)
    def verify_bgp_connection(self, ds_ip=None):
        return self._verify_bgp_connection(ds_ip)

    def _verify_bgp_connection(self, ds_ip=None):
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
                self.logger.debug("%s compute is subscribed to %s bgp nodes" %
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
                self.logger.debug("Actual XmppServer for %s : %s" %
                                 (host, actual_bgp_peer))
                self.logger.debug("Expected XmppServer for %s : %s" %
                                 (host, expected_bgp_peer))

                if actual_bgp_peer != expected_bgp_peer:
                    result = result and False
                    self.logger.error(
                        'All the required BGP controller are not found in agent introspect for %s' % (host))
                else:
                    self.logger.info('Validated that for Compute %s, XMPP '\
                        'sessions are as seen in discovery' %(host_ip))
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
                            self.logger.error('For control node %s, with peer %s, '
                                'peering is not Established. Current State %s ' % (
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
                                self.logger.error('For control node %s, with peer '
                                    '%s, peering is not Established. Current State %s ' % (
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
                self.logger.debug("%s bgp node subscribed by %s xmpp-clients" %
                                 (control_ip, computes))
                self.logger.debug(
                    "From control node introspect, xmpp-clients: %s" %
                    (control_node_bgp_xmpp_peer_list))
                
                if sorted(computes) != sorted(control_node_bgp_xmpp_peer_list):
                    result = result and False
                    self.logger.error(
                        'The required XMPP entry not present in control node introspect for %s' % (host))
                    self.logger.error('Xmpp clients in discovery but not in '\
                        'control node : %s' % (
                        set(computes)-set(control_node_bgp_xmpp_peer_list)))
                    self.logger.error('Xmpp clients in Control node but not '\
                        'in discovery clients list : %s' % (
                        set(control_node_bgp_xmpp_peer_list)-set(computes)))
                else:
                    self.logger.info('Validated that for Control node %s,'\
                        ' XMPP sessions are as seen in discovery service' % (
                        host))

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
                'One or more BGP/XMPP states are not correct on nodes,'
                'Please check logs')
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
                self.logger.debug(e)
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
                self.logger.debug(e)
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
                self.logger.debug(e)
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
                self.logger.debug(e)
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
            self.logger.debug(e)
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

    def modify_conf_file(self, operation, service, section, option, value):
        cmd_set = 'openstack-config ' + '--' + operation 
        conf_file = ' /etc/contrail/' + service + '.conf '
        if operation == "set":
            cmd = cmd_set + conf_file + section + ' ' + option + ' ' + '"%s"' % str(value)
        if operation == "del":
            cmd = cmd_set + conf_file + section + ' ' + option
        for ip in self.inputs.cfgm_ips:
            self.inputs.run_cmd_on_server(ip, cmd, self.inputs.host_data[ip]['username']\
                                          , self.inputs.host_data[ip]['password'])
    # end modify_conf_file
         
    def modify_discovery_conf_file_params(self, operation, **args):
        '''
        This proc is a common proc to do modification for  various paramteres
        in the contrail-discovery. conf file.
        Possible operations which can be performed by this proc are:
        1. change_ttl_short_and_hc_max_miss, Vars: ttl_short=2, hc_max_miss=3000
        2. change_min_max_ttl, Vars: ttl_min=300 , ttl_max=1800
        3. add_keystone_auth, Vars: auth="keystone", add_values = "True"
        4. delete_keystone_auth, Vars: auth="keystone"
        5. delete_white_list, Vars: publish='True', subscribe = 'True
        6. set_policy Vars: publisher_type = None , policy = "load-balance"
        7. del_policy Vars: publisher_type = None
        '''
        final_status = True
        if operation == "change_ttl_short_and_hc_max_miss":
            # Changing the hc_max_miss=3000 and verifying that the services are
            # down after 25 mins
            ttl_short = args.get('ttl_short',2)
            hc_max_miss = args.get('hc_max_miss',3000)
            self.modify_conf_file('set', 'contrail-discovery', 'DEFAULTS', \
                              'ttl_short', ttl_short)
            self.modify_conf_file('set', 'contrail-discovery', 'DEFAULTS', \
                              'hc_max_miss', hc_max_miss)
        elif operation == "change_min_max_ttl":
            # Changing the minimum and maximum TTL values
            ttl_min = args.get('ttl_min',300)
            ttl_max = args.get('ttl_max',1800)
            self.modify_conf_file('set', 'contrail-discovery', 'DEFAULTS', \
                    'ttl_min', ttl_min)
            self.modify_conf_file('set', 'contrail-discovery', 'DEFAULTS', \
                    'ttl_max', ttl_max)
        elif operation == "add_keystone_auth":
            # Enable / Disable keystone authentication
            # Adding keystone parameters can also be done
            auth = args.get('auth','keystone')
            add_values = args.get('add_values',True)
            self.modify_conf_file('set', 'contrail-discovery', 'DEFAULTS', \
                                  'auth', auth)
            if add_values == "True":
                self.modify_conf_file('set', 'contrail-discovery', 'KEYSTONE',\
                    'auth_host', self.inputs.auth_ip)
                self.modify_conf_file('set', 'contrail-discovery', 'KEYSTONE',\
                    'auth_protocol',"http" )
                self.modify_conf_file('set', 'contrail-discovery', 'KEYSTONE',\
                    'auth_port', "35357")
                self.modify_conf_file('set', 'contrail-discovery', 'KEYSTONE',\
                    'admin_user', "admin")
                self.modify_conf_file('set', 'contrail-discovery', 'KEYSTONE',\
                    'admin_password', "contrail123")
                self.modify_conf_file('set', 'contrail-discovery', 'KEYSTONE',\
                    'admin_tenant_name', "admin")
        elif operation == "delete_keystone_auth":
            # Deleting publish or subscribe white list
            auth = args.get('auth','keystone')
            self.modify_conf_file('del', 'contrail-discovery', 'DEFAULTS', \
                            'auth', auth)
            self.modify_conf_file('del', 'contrail-discovery', 'KEYSTONE', \
                                  '', '')
        elif operation == "delete_white_list":
            # Enable / Disable keystone authentication
            publish = args.get('publish',True)
            subscribe = args.get('subscribe',True)
            if publish:
                self.modify_conf_file('del', 'contrail-discovery', 'DEFAULTS',\
                                   'white_list_publish','')
            if subscribe:
                self.modify_conf_file('del', 'contrail-discovery', 'DEFAULTS', \
                                  'white_list_subscribe','')
        elif operation == "set_policy":
            # Setting policy for specific publisher
            # policy = [load-balance | round-robin | fixed]
            # publisher-type : type of service (eg: XMPP-SERVER, DNS-SERVER, OPSERVER)
            publisher_type = args.get('publisher_type',None)
            policy = args.get('policy',"load-balance")
            if not publisher_type:
                self.info.error("Publisher type not mentioned while setting policy")
                final_status = False
            else:
                self.modify_conf_file('set', 'contrail-discovery', publisher_type,\
                               'policy', policy)
        elif operation == "del_policy":
            # Resetting policy for specific publisher
            # publisher-type : type of service (eg: XMPP-SERVER, DNS-SERVER, OPSERVER)
            publisher_type = args.get('publisher_type',None)
            if not publisher_type:
                self.info.error("Publisher type not mentioned while deleting policy")
                final_status = False
            else:
                self.modify_conf_file('del', 'contrail-discovery', publisher_type,\
                              '','') 
        conf_file = '/etc/contrail/contrail-discovery.conf '
        cmd = 'cat ' + conf_file
        for ip in self.inputs.cfgm_ips:
            out_put = self.inputs.run_cmd_on_server(ip, cmd, \
                self.inputs.host_data[ip]['username'], \
                self.inputs.host_data[ip]['password'])
            self.logger.debug("%s" % (out_put))
            self.inputs.restart_service('contrail-discovery', [ip])
            status = self.inputs.confirm_service_active('contrail-discovery', ip)
            if status == False:
                self.logger.info("Discovery Service on cfgm with ip as %s did not \
                 came UP after restart" % ip)
                final_status = False
        return final_status
        time.sleep(10)
    # end modify_discovery_conf_file_params
    
    def white_list_conf_file(self, white_list_for, *ips):
        final_status = True
        count = len(ips)
        list = ''
        for x in range(0,count):
            list = list + ips[x] + " "
        if white_list_for == "publisher":
            self.logger.debug("List of white list publishers is %s" % list)
            self.modify_conf_file('set', 'contrail-discovery', 'DEFAULTS', \
                                    'white_list_publish',list)
        elif white_list_for == "subscriber":
            subscriber_count = len(ips)
            self.logger.debug("List of white list subscriber is %s" % list)
            self.modify_conf_file('set', 'contrail-discovery', 'DEFAULTS', \
                                    'white_list_subscribe',list)
        conf_file = '/etc/contrail/contrail-discovery.conf '
        cmd = 'cat ' + conf_file
        for ip in self.inputs.cfgm_ips:
            out_put = self.inputs.run_cmd_on_server(ip, cmd, \
                    self.inputs.host_data[ip]['username'], \
                    self.inputs.host_data[ip]['password'])
            self.logger.debug("%s" % (out_put))
            self.inputs.restart_service('contrail-discovery', [ip])
            status = self.inputs.confirm_service_active('contrail-discovery', ip)
            if status == False:
                self.logger.info("Discovery Service on cfgm with ip as %s did\
                 not came UP after restart" % ip)
                final_status = False
        return final_status

    def vnc_read_obj(self, vnc, obj_type, fq_name):
        method_name = obj_type.replace('-', '_')
        method = getattr(vnc, "%s_read" % (method_name))
        try:
            return method(fq_name=fq_name)
        except NoIdError:
            self.logger.error('%s %s not found!' % (obj_type, fq_name))
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
    
    def discovery_rule_config(self, operation, fq_name, publisher_prefix, \
                              publisher_type, *subscriber_prefix_type):    
        ''' This proc handles different configurations of rules.
            Rule operations which we can do using this proc are as follows:
            1. Addition of a rule - 'add_rule'
            2. Deletion of a rule - 'del_rule'
            3. Finding a rule entry - 'find_rule'
            publisher_prefix : Publisher IP with subnet in  "IP/subnet" format.
            publisher_type : Service Type to be mentioned here
            *subscriber_prefix_type : As multiple subscibers can be supported, \
            so it is expected to
            give multiple IP/subnet and client type sequentially. This will be \
            taken and processed as a list.
        '''
        configuration_status = True
        fq_name = fq_name.split(":")
        if '/' not in publisher_prefix:
            publisher_prefix += '/32'
        else:
            pass
        self.logger.debug("Publisher service type: %s" % publisher_type)
        x = publisher_prefix.split('/')
        publisher_prefix_obj = SubnetType(x[0], int(x[1]))
        subscriber_values = list(subscriber_prefix_type)
        subscriber_number = int(len(subscriber_values) / 2)
        self.logger.debug("Total number of subscribers mentioned in this rule are %d"\
                          % int(subscriber_number))
        publisher = DiscoveryPubSubEndPointType(ep_prefix = publisher_prefix_obj,\
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
            if operation == 'add_rule': 
                self.logger.info("Creating rule with following values.\
                Publisher_prefix: %s , Publisher_type: %s, Subscribers details: %s"\
                % (publisher_prefix, publisher_type, subscriber_prefix_type))
                rule_uuid = self.generateUUID()
                dsa_rule = DsaRule(name = rule_uuid, parent_obj = dsa, \
                               dsa_rule_entry = rule_entry)
                dsa_rule.set_uuid(rule_uuid)
                self.vnc_lib.dsa_rule_create(dsa_rule)
            if operation == 'del_rule' or operation == "find_rule":
                if operation == 'del_rule':
                    self.logger.info("Deleting rule with following values.\
                    Publisher_prefix: %s , Publisher_type: %s, Subscribers details: %s"
                    % (publisher_prefix, publisher_type, subscriber_prefix_type))
                elif operation == 'find_rule':
                    self.logger.info("Searching the rule with following values.\
                    Publisher_prefix: %s , Publisher_type: %s, Subscribers details: %s" 
                    % (publisher_prefix, publisher_type, subscriber_prefix_type))
                dsa_rules = dsa.get_dsa_rules()
                rule_found = False
                if dsa_rules is None:
                    self.logger.debug('Empty DSA group! Rule not found!')
                    configuration_status = False
                    obj = None
                else: 
                    for dsa_rule in dsa_rules:
                        dsa_rule_obj = self.vnc_read_obj(self.vnc_lib, 'dsa-rule',\
                                                         dsa_rule['to'])
                        entry = dsa_rule_obj.get_dsa_rule_entry()
                        if self.match_rule_entry(entry, rule_entry):
                            self.logger.debug("Specified rule found.")
                            obj = dsa_rule_obj
                            rule_found = True
                            break
                if not rule_found:
                    self.logger.debug("Searched rule not found")
                    configuration_status = False
                    obj = None
        except Exception as e:
            self.logger.error('*** %s' % str(e))
            configuration_status = False
        if operation == 'del_rule' and obj:
            self.vnc_lib.dsa_rule_delete(id = obj.uuid)
        return configuration_status
    
    
    def read_rule(self, fq_name):
        '''
        Read and print all the rules already configured on the system
        '''       
        self.logger.info("## Displaying all rules!! #")
        fq_name = fq_name.split(":")
        dsa = self.vnc_read_obj(self.vnc_lib, 'discovery-service-assignment', fq_name)
        dsa_rules = dsa.get_dsa_rules()
        if dsa_rules is None:
            self.logger.debug('Empty DSA group for fq_name %s !' % fq_name)
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
                (pub.ep_prefix.ip_prefix, pub.ep_prefix.ip_prefix_len, pub.ep_type,\
                 pub.ep_id, pub.ep_version)
                sub_str = ['%s/%d,%s,%s,%s' % \
                (sub.ep_prefix.ip_prefix, sub.ep_prefix.ip_prefix_len, sub.ep_type,\
                  sub.ep_id, sub.ep_version) for sub in subs]
                self.logger.info("Rule: %s %s %s" % ('', pub_str, sub_str))
            idx += 1
    
    def verify_client_subscription_to_expected_publisher(self, ds_ip, \
                            client_type, client_ip, service_type):
        ### It is always expected that clients and services will be in same network after the rule ####
        result = True
        if not ds_ip:
            ds_ip = self.inputs.cfgm_ip            
        svc_list = self.get_subscribed_service_id(ds_ip, (client_ip, \
                            client_type), service = service_type) ### returns list of service_id
        self.logger.debug("Testing for client %s running on %s" \
                          % (client_type,client_ip))
        if len(svc_list) == 0:
            result = False
            self.logger.error("No service ID found for mentioned client \
            details as client do not exist")
            return result
        ####### Finding subscriber netwrok ##
        expected_pub_network = client_ip.split('.')
        expected_pub_network[3] = '0'
        expected_pub_network= ".".join(expected_pub_network)
        ######## Finding Publisher netwrok ###
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
            self.logger.debug("The client (%s,%s) is subscribed to %i publisher \
            of type %s under same network" % (client_type,client_ip,\
                                len(publisher_networks),service_type))
        if result == False:
            self.logger.error("The client (%s,%s) is subscribed to %i publisher\
             of type %s which are under different networks" % (client_type,\
                                client_ip,len(publisher_networks),service_type))
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
            self.logger.debug("Service %s with IP %s is holding %i instances of subscribers" % (elem[1],elem[0],get_in_use))
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
        self.logger.debug('Service type %s, id %s' % (service_type, service_id))
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
    
    def resubscribe_with_new_ttl(self, min_ttl, max_ttl, *subscribers):
        self.logger.debug("#### Changing min and max TTL values for testing purpose ##")
        self.logger.debug("#### Changing min and max TTL values for testing purpose ##")
        result = self.modify_discovery_conf_file_params("change_min_max_ttl",\
                                                ttl_min=min_ttl, ttl_max=max_ttl)
        if result == False:
            self.logger.error("Changing TTL values failed")
            return result
        self.logger.debug("#### Restarting the required subscriber services so that TTL takes effect immediately ###")
        if "contrail-vrouter-agent" in subscribers:
            for ip in self.inputs.compute_ips:
                self.inputs.restart_service('contrail-vrouter-agent', [ip])
            for ip in self.inputs.compute_ips:
                client_status = self.inputs.confirm_service_active(\
                                    'contrail-vrouter-agent', ip)
            if client_status == False:
                self.logger.error("Some issue happened after restart of client process")
                result = False
        if "contrail-control" in subscribers:
            for ip in self.inputs.bgp_ips:
                self.inputs.restart_service('contrail-control', [ip])
            for ip in self.inputs.bgp_ips:
                client_status = self.inputs.confirm_service_active(\
                            'contrail-control', ip)
            if client_status == False:
                self.logger.error("Some issue happened after restart of client process")
                result = False
        if "supervisor-webui" in subscribers:
            for ip in self.inputs.webui_ips:
                self.inputs.restart_service('supervisor-webui', [ip])
            for ip in self.inputs.webui_ips:
                client_status = self.inputs.confirm_service_active(\
                                            'supervisor-webui', ip)
            if client_status == False:
                self.logger.error("Some issue happened after restart of client process")
                result = False
        if "contrail-topology" in subscribers:
            for ip in self.inputs.collector_ips:
                self.inputs.restart_service('contrail-topology', [ip])
            for ip in self.inputs.collector_ips:
                client_status = self.inputs.confirm_service_active(\
                                            'contrail-topology', ip)
            if client_status == False:
                self.logger.error("Some issue happened after restart of client process")
                result = False
        if "contrail-api" in subscribers:
            for ip in self.inputs.cfgm_ips:
                self.inputs.restart_service('contrail-api', [ip])
            for ip in self.inputs.cfgm_ips:
                client_status = self.inputs.confirm_service_active(\
                                            'contrail-api', ip)
            if client_status == False:
                self.logger.error("Some issue happened after restart of client process")
                result = False
        if "supervisor-control" in subscribers:
            for ip in self.inputs.bgp_ips:
                self.inputs.restart_service('supervisor-control', [ip])
            for ip in self.inputs.bgp_ips:
                client_status = self.inputs.confirm_service_active(\
                                                        'supervisor-control', ip)
            if client_status == False:
                self.logger.error("# Some issue happened after restart of client process #")
                result = False 
        return result
    
    def add_and_verify_rule(self, pub_subnet, publisher, sub_subnet, subscriber):
        result = True
        self.discovery_rule_config("add_rule", 'default-discovery-service-assignment',\
                pub_subnet, publisher, sub_subnet, subscriber)
        self.read_rule('default-discovery-service-assignment')
        result_1 = self.discovery_rule_config("find_rule", \
                'default-discovery-service-assignment', pub_subnet, publisher,\
                 sub_subnet, subscriber)
        if result_1 == False:
            self.logger.error("While searching for the configured rule, it was not found. Configuration failed")
            result = False
        return result 
        
    def delete_and_verify_rule(self, pub_subnet, publisher, sub_subnet, subscriber):
        result = True
        self.discovery_rule_config("del_rule", 'default-discovery-service-assignment',\
                pub_subnet, publisher, sub_subnet, subscriber)
        self.read_rule('default-discovery-service-assignment')
        result_1 = self.discovery_rule_config("find_rule", \
                'default-discovery-service-assignment', pub_subnet, publisher,\
                 sub_subnet, subscriber)
        if result_1 == True:
            self.logger.error("While searching for the deleted rule, it was found. Deletion failed")
            result = False
        return result
