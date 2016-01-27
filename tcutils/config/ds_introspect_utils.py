import sys
import urllib2
import xmltodict
import json
import requests
import socket
from lxml import etree
from tcutils.verification_util import *
from ds_results import *
from discovery_util import DiscoveryServerUtils


class VerificationDsSrv (VerificationUtilBase):

    def __init__(self, ip, port=5998, logger=LOG):
        super(VerificationDsSrv, self).__init__(ip, port, logger=logger)

    def get_ds_services(self):
        '''http://10.204.216.7:5998/services'''
        res = None
        try:
            services_dict = self.dict_get('services.json')
            res = DsServicesResult(services_dict)
        except Exception as e:
            print e
        finally:
            return res

    def get_ds_clients(self):
        '''http://10.204.216.7:5998/clients'''
        res = None
        try:
            #import pdb; pdb.set_trace()
            clients_dict = self.dict_get('clients.json')
            res = DsClientsResult(clients_dict)
        except Exception as e:
            print e
        finally:
            return res

    def get_ds_stats(self):
        '''http://10.204.216.7:5998/stats'''
        res = None
        try:
            #import pdb; pdb.set_trace()
            stats_dict = self.dict_get('stats')
            res = DsStatsResult(stats_dict)
        except Exception as e:
            print e
        finally:
            return res

    def get_ds_config(self):
        '''http://10.204.216.7:5998/config'''
        res = None
        try:
            config_dict = self.dict_get('config')
            res = DsConfigResult(config_dict)
        except Exception as e:
            print e
        finally:
            return res

    def publish_service(self, service='foo', ip=None, port=None, admin_state=None):
        '''Used to publish service from test { "control-node": {"ip_addr": "192.168.2.0", "port":1682 }}'''
        resp = None
        try:
            service_url = DiscoveryServerUtils.discovery_publish_service_url(
                self._ip, str(self._port))
            print 'url: %s' % service_url
            if not admin_state:
                json_body = '{' + '"' + service + '"' + \
                    ': {' + '"ip-address":' + '"' + \
                    ip + '"' + ',"port":' + str(port) + '}}'
            else:
                json_body = '{' + '"' + service + '"' + \
                    ': {' + '"ip-address":' + '"' + \
                    ip + '"' + ',"port":' + str(port) + \
                    '}, "service-type":' + '"' + service + \
                    '",' + '"admin-state":' + '"' + \
                    admin_state + '"' + '}'
            print 'json_body: %s' % json_body
            resp = DiscoveryServerUtils.post_url_http(service_url, json_body)
            if resp:
                resp = json.loads(resp)
        except Exception as e:
            print str(e)
        finally:
            print 'resp: %s' % (resp)
            return resp

    def subscribe_service(self, service='foo', instances=None, client_id=None):
        '''POST http://discovery-server-ip:5998/subscribe
            Content-Type: application/json or application/xml
            Body: Service type, instance count, client ID
            JSON: { "service": "control-node", "instances": 1, "client": "6c3f48bf-1098-46e8-8117-5cc745b45983"}
            XML:   <control-node><instances>1</instances><client>UUID</client></control-node>

            Response: TTL, List of <service type, Blob>
            JSON: {"Apiservice": [{"ip_addr": "10.84.13.34", "port": "8082"}], "ttl": 357}
            XML: <response><ttl>300</ttl><control-node><ip_addr>192.168.2.0</ip_addr><port>1682</port></control-node>'''
        resp = None
        try:
            service_url = DiscoveryServerUtils.discovery_subscribe_service_url(
                self._ip, str(self._port))
            print 'url: %s' % service_url
            json_body = '{' + '"service": ' + '"' + service + '"' + \
                ', "instances": ' + \
                str(instances) + ', ' + '"client": "' + client_id + '"}'
            print 'json_body: %s' % json_body
            resp = DiscoveryServerUtils.post_url_http(service_url, json_body)
            if resp:
                resp = json.loads(resp)
        except Exception as e:
            print str(e)
        finally:
            print 'resp: %s' % (resp)
            return resp

    def cleanup_service(self):
        '''GET http://discovery-server-ip:5998/cleanup'''
        resp = None
        try:
            service_url = DiscoveryServerUtils.discovery_cleanup_service_url(
                self._ip, str(self._port))
            print 'url: %s' % service_url
            resp = DiscoveryServerUtils.get_url_http(service_url)
            if resp:
                resp = json.loads(resp)
        except Exception as e:
            print str(e)
        finally:
            print 'resp: %s' % (resp)
            return resp

if __name__ == '__main__':
    vns = VerificationDsSrv('127.0.0.1')
