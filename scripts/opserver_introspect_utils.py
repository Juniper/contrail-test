import sys
vizdtestdir = sys.path[0]
sys.path.insert(1, vizdtestdir + '/../../')

import urllib2
import xmltodict
import json
import requests
import socket
from lxml import etree
from verification_util import *
from opserver_results import *
from opserver_util import OpServerUtils
from util import *


class VerificationOpsSrv (VerificationUtilBase):

    def __init__(self, ip, port=8081, logger=LOG):
        super(VerificationOpsSrv, self).__init__(ip, port, logger=logger)

#    def get_ops_vm (self, vm='default-virtual-machine'):
#        vm_dict = self.dict_get ('analytics/virtual-machine/' + vm)
#        return OpVMResult(vm_dict)
#
#    def get_ops_vn (self, vn='default-virtual-network'):
#        res = None
#        try:
#            vn_dict = self.dict_get ('analytics/virtual-network/' + vn)
#            res = OpVNResult(vn_dict)
#        except Exception as e:
#            print e
#        finally:
#            return res
#
#    def get_ops_collector(self, col = None):
#        if (col == None):
#            col = socket.gethostname()
#        res = None
#        try:
# import pdb; pdb.set_trace()
#            col_dict = self.dict_get ('analytics/collector/' + col)
#            res = OpCollectorResult(col_dict)
#        except Exception as e:
#            print e
#        finally:
#            return res
#
#    def get_ops_vrouter(self, vrouter = None):
#        if (vrouter == None):
#            vrouter = socket.gethostname()
#        res = None
#        try:
# import pdb; pdb.set_trace()
#            vrouter_dict = self.dict_get ('analytics/vrouter/' + vrouter)
#            res = OpVRouterResult(vrouter_dict)
#        except Exception as e:
#            print e
#        finally:
#            return res
#
#
#    def get_ops_bgprouter(self, bgprouter = None):
#        if (bgprouter == None):
#            bgprouter = socket.gethostname()
#        res = None
#        try:
# import pdb; pdb.set_trace()
#            bgprouter_dict = self.dict_get ('analytics/bgp-router/' + bgprouter)
#            res = OpBGPRouterResult(bgprouter_dict)
#        except Exception as e:
#            print e
#        finally:
#            return res

    def get_ops_generator(self, generator=None, moduleid=None, node_type=None, instanceid='0'):
        '''http://nodea29:8081/analytics/generator/nodea18:Control:ControlNode:0?flat'''
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

    def send_trace_to_database(self, node=None, module=None, instance_id='0', trace_buffer_name=None):
        '''http://<opserver-ip>:8081/analytics/send-tracebuffer/nodeb8/VRouterAgent/UveTrace'''
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

if __name__ == '__main__':
    vns = VerificationOpsSrv('127.0.0.1')

    vn = vns.get_ops_vn(vn='abc-corp:vn02')

    print "*** Verify VN Cfg ***"

    print vn.get_attr('Config', 'attached_policies', 'abc-default-policy')
    '''
    [{u'vnp_major': u'10', u'vnp_name': u'abc-default-policy', u'vnp_minor': u'50'}]
    '''

    print vn.get_attr('Config', 'connected_networks')
    '''
    [u'abc-corp:vn04']
    '''

    print vn.get_attr('Config', 'total_interfaces')
    '''
    10
    '''

    print vn.get_attr('Config', 'total_acl_rules')
    '''
    60
    '''

    print "*** Verify VN Agt ***"

    print vn.get_attr('Agent', 'total_acl_rules')
    '''
    55
    '''

    print vn.get_attr('Agent', 'in_tpkts')
    '''
    240
    '''

    print vn.get_attr('Agent', 'in_stats', 'abc-corp:map-reduce-02')
    '''
    [{u'bytes': u'7200', u'other_vn': u'abc-corp:map-reduce-02', u'tpkts': u'60'}]
    '''

    vm = vns.get_ops_vm(vm='abc-corp:vm-web-fe01')

    print "*** Verify VM Cfg ***"

    print vm.get_attr('Config', 'vrouter')
    '''
    rack01-host04
    '''

    print vm.get_attr('Config', 'attached_groups')
    '''
    [u'abc-grp01']
    '''

    print vm.get_attr('Config', 'interface_list', 'abc-corp:vn-fe')
    '''
    [{u'virtual_network': u'abc-corp:vn-fe', u'ip_address': u'10.1.1.2', u'floating_ips': [u'67.1.1.2', u'67.1.1.3']}]
    '''

    print "*** Verify VM Agt ***"

    print vm.get_attr('Agent', 'vrouter')
    '''
    rack01-host04
    '''

    print vm.get_attr('Agent', 'attached_groups')
    '''
    [u'abc-grp01']
    '''

    print vm.get_attr('Agent', 'interface_list')
    '''
    [{u'in_bytes': u'1000', u'out_bytes': u'10000', u'floating_ips': [u'67.1.1.2', u'67.1.1.3'], u'out_pkts': u'20', u'virtual_network': u'abc-corp:vn-fe', u'in_pkts': u'5', u'ip_address': u'10.1.1.2'}]
    '''

    col = vns.get_ops_collector()

    print col.get_attr('Analytics', 'generator_infos')
    '''
    [{u'gen_attr': {u'GeneratorInfoAttr': {u'http_port': u'8089', u'in_clear': u'false', u'pid': u'57160', u'connects': u'1', u'clears': u'1', u'resets': u'0'}}, u'source': u'sa-nc-mfg-30.static.jnpr.net', u'msgtype_stats': {u'SandeshStats': [{u'bytes': u'1318433', u'messages': u'417', u'message_type': u'CollectorInfo'}]}, u'module_id': u'Collector'}, {u'gen_attr': {u'GeneratorInfoAttr': {u'http_port': u'0', u'in_clear': u'false', u'pid': u'0', u'connects': u'1', u'clears': u'0', u'resets': u'0'}}, u'source': u'sa-nc-mfg-30.static.jnpr.net', u'msgtype_stats': {}, u'module_id': u'OpServer'}, {u'gen_attr': {u'GeneratorInfoAttr': {u'http_port': u'8091', u'in_clear': u'false', u'pid': u'57200', u'connects': u'2', u'clears': u'2', u'resets': u'1'}}, u'source': u'sa-nc-mfg-30.static.jnpr.net', u'msgtype_stats': {u'SandeshStats': [{u'bytes': u'16771', u'messages': u'66', u'message_type': u'QELog'}, {u'bytes': u'12912', u'messages': u'32', u'message_type': u'QEQueryLog'}]}, u'module_id': u'QueryEngine'}]
    '''

    print col.get_attr('Analytics', 'generator_infos', [('module_id', 'OpServer'), ('source', "sa-nc-mfg-30.static.jnpr.net")])
    '''
    [{u'gen_attr': {u'GeneratorInfoAttr': {u'http_port': u'0', u'in_clear': u'false', u'pid': u'0', u'connects': u'1', u'clears': u'0', u'resets': u'0'}}, u'source': u'sa-nc-mfg-30.static.jnpr.net', u'msgtype_stats': {}, u'module_id': u'OpServer'}]
    '''
    print col.get_attr('Analytics', 'cpu_info')
    '''
{u'CpuLoadInfo': {u'num_cpu': u'4', u'cpu_share': u'0.00416667', u'meminfo': {u'MemInfo': {u'virt': u'2559582208', u'peakvirt': u'2559582208', u'res': u'2940928'}}}}
    '''
