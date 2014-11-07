import sys
vizdtestdir = sys.path[0]
sys.path.insert(1, vizdtestdir + '/../../')

import urllib2
import xmltodict
import json
import requests
import socket
from lxml import etree
from tcutils.verification_util import *
from opserver_results import *
from opserver_util import OpServerUtils
from tcutils.util import *


class VerificationOpsSrv (VerificationUtilBase):

    def __init__(self, ip, port=8081, logger=LOG):
        super(VerificationOpsSrv, self).__init__(ip, port, logger=logger)


    def get_ops_generator(self, generator=None, moduleid=None, node_type=None, instanceid='0'):
        '''http://nodea29:8081/analytics/generator/nodea18:Control:Contrail-Control:0?flat'''
        if (generator == None):
            generator = socket.gethostname()
        if (moduleid == None):
            self.logger.info("module id not passed")
            return None
        if instanceid == None:
            instanceid = 0
        if node_type == None:
            self.logger.info("node type is not passed")
            return None
        res = None
        try:
            #import pdb; pdb.set_trace()
            generator_dict = self.dict_get(
                'analytics/generator/' + generator + ':' + node_type + ':' + moduleid + ':' + instanceid + '?flat')
            res = OpGeneratorResult(generator_dict)
        except Exception as e:
            print e
        finally:
            return res

    def get_ops_vrouter(self, vrouter=None):
        if (vrouter == None):
            vrouter = socket.gethostname()
        res = None
        try:
            #import pdb; pdb.set_trace()
            vrouter_dict = self.dict_get(
                'analytics/vrouter/' + vrouter + '?flat')
            res = OpVRouterResult(vrouter_dict)
        except Exception as e:
            print e
        finally:
            return res

    def get_ops_bgprouter(self, bgprouter=None):
        if (bgprouter == None):
            bgprouter = socket.gethostname()
        res = None
        try:
            #import pdb; pdb.set_trace()
            bgprouter_dict = self.dict_get(
                'analytics/uves/control-node/' + bgprouter + '?flat')
            res = OpBGPRouterResult(bgprouter_dict)
        except Exception as e:
            print e
        finally:
            return res

    def get_ops_vn(self, vn_fq_name='default-virtual-network'):
        res = None
        try:
            vn_dict = self.dict_get(
                'analytics/virtual-network/' + vn_fq_name + '?flat')
            res = OpVNResult(vn_dict)
        except Exception as e:
            print e
        finally:
            return res

    def get_ops_vm(self, vm='default-virtual-machine'):
        res = None
        try:
            vm_dict = self.dict_get(
                'analytics/virtual-machine/' + vm + '?flat')
            #import pdb;pdb.set_trace()
            res = OpVMResult(vm_dict)
        except Exception as e:
            print e
        finally:
            return res

    def get_ops_svc_instance(self, project='admin', svc_instance=None):
        '''analytics/uves/service-instance/default-domain:admin:svc-instance1?flat'''
        res = None
        try:
            si_dict = self.dict_get(
                'analytics/service-instance/' + svc_instance + '?flat')
            #import pdb;pdb.set_trace()
            res = OpSIResult(si_dict)
        except Exception as e:
            print e
        finally:
            return res

    def get_ops_svc_template(self, left_vn=None, right_vn=None):
        '''analytics/uves/service-chain/sc:default-domain:admin:vn1:default-domain:admin:fip_vn?flat'''
        res = None
        try:
            st_dict = self.dict_get(
                'analytics/service-chain/sc:' + left_vn + ':' + right_vn + '?flat')
            #import pdb;pdb.set_trace()
            res = OpSTResult(st_dict)
        except Exception as e:
            print e
        finally:
            return res

    def get_hrefs_to_all_UVEs_of_a_given_UVE_type(self, uveType=None):
        '''Get all hrefs for a uve type'''
        dct = self.dict_get('analytics/uves/' + uveType)
        ret_value = []
        for elem in dct:
            self.ame = OpHrefResult(elem)
            ret_value.append(self.ame)
        return ret_value
    
    def get_hrefs_to_all_tables(self, uveType=None):
        '''Get all hrefs for a uve type'''
        dct = self.dict_get('analytics/' + uveType)
        ret_value = []
        for elem in dct:
            self.tme = OpHrefTableResult(elem)
            ret_value.append(self.tme)
        return ret_value

    def send_trace_to_database(self, node=None, module=None, instance_id='0', trace_buffer_name=None):
        '''http://<opserver-ip>:8081/analytics/send-tracebuffer/nodeb8/Contrail-Vrouter-Agent/UveTrace'''
        res = None
        try:
            res = self.dict_get('analytics/send-tracebuffer/' + node +
                                '/' + module + '/' + instance_id + '/' + trace_buffer_name)
            #import pdb;pdb.set_trace()
        except Exception as e:
            print e
        finally:
            return res

    def get_ops_bgp_peer(self, peer_toupe=None):
        '''http://nodea18:8081/analytics/uves/bgp-peer/default-domain:default-project:ip-fabric:__default__:nodea19:default-domain:default-project:ip-fabric:__default__:nodea18?flat'''
        res = None

        try:
            bgp_node = peer_toupe[0]
            peer = peer_toupe[1]
            dct = self.dict_get('analytics/uves/bgp-peer/default-domain:default-project:ip-fabric:__default__:' +
                                bgp_node + ':' + 'default-domain:default-project:ip-fabric:__default__:' + peer + '?flat')
            res = OpBGPPeerResult(dct)
        except Exception as e:
            print e
        finally:
            return res

    def get_ops_bgp_xmpp_peer(self, peer_toupe=None):
        '''http://nodea29.englab.juniper.net:8081/analytics/uves/xmpp-peer/nodea29:10.204.216.15?flat'''
        res = None

        try:
            bgp_node = peer_toupe[0]
            peer = peer_toupe[1]
            dct = self.dict_get(
                'analytics/uves/xmpp-peer/' + bgp_node + ':' + peer + '?flat')
            res = OpBGPXmppPeerResult(dct)
        except Exception as e:
            print e
        finally:
            return res

    def get_ops_collector(self, collector=None):
        '''http://nodea18:8081/analytics/uves/analytics-node/nodea29?flat'''
        res = None
        try:
            c_dict = self.dict_get(
                'analytics/uves/analytics-node/' + collector + '?flat')
            #import pdb;pdb.set_trace()
            res = OpCollectorResult(c_dict)
        except Exception as e:
            print e
        finally:
            return res

    def get_ops_config(self, config=None):
        '''http://nodea18:8081/analytics/uves/config-node/nodea11?flat'''
        res = None
        try:
            c_dict = self.dict_get(
                'analytics/config-node/' + config + '?flat')
            #import pdb;pdb.set_trace()
            res = OpConfigResult(c_dict)
        except Exception as e:
            print e
        finally:
            return res

#    @timeout(600, os.strerror(errno.ETIMEDOUT))
    def post_query(self, table, start_time=None, end_time=None,
                   select_fields=None,
                   where_clause='',
                   sort_fields=None, sort=None, limit=None, filter=None, dir=None):
        res = None
        try:
            flows_url = OpServerUtils.opserver_query_url(
                self._ip, str(self._port))
            print flows_url
            query_dict = OpServerUtils.get_query_dict(
                table, start_time, end_time,
                select_fields,
                where_clause,
                sort_fields, sort, limit, filter, dir)

            print json.dumps(query_dict)
            res = []
            resp = OpServerUtils.post_url_http(
                flows_url, json.dumps(query_dict))
            if resp is not None:
                resp = json.loads(resp)
                qid = resp['href'].rsplit('/', 1)[1]
                result = OpServerUtils.get_query_result(
                    self._ip, str(self._port), qid)
                for item in result:
                    res.append(item)
        except Exception as e:
            print str(e)
        finally:
            return res

class VerificationOpsSrvIntrospect (VerificationUtilBase):

    def __init__(self, ip, port, logger=LOG):
        super(VerificationOpsSrvIntrospect, self).__init__(ip, port,drv=XmlDrv, logger=logger)

    def get_collector_connectivity(self):
        connaction_status = dict()
        try:
            c_dict = self.dict_get(
                'Snh_CollectorInfoRequest?')
            ip = c_dict.xpath('ip')[0].text
            port = c_dict.xpath('port')[0].text
            status = c_dict.xpath('status')[0].text
            connaction_status['ip']= ip
            connaction_status['port']= port
            connaction_status['status']= status
        except Exception as e:
            print e
        finally:
            return connaction_status

if __name__ == '__main__':
    vns = VerificationOpsSrvIntrospect('127.0.0.1',8090)
    intr = vns.get_collector_connectivity()

