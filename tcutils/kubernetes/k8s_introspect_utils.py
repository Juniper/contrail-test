from __future__ import print_function
import logging as LOG
from lxml import etree
import re

from tcutils.verification_util import *


LOG.basicConfig(format='%(levelname)s: %(message)s', level=LOG.DEBUG)

class KubeManagerInspect(VerificationUtilBase):

    def __init__(self, ip, port=8108, logger=LOG, args=None, protocol='http'):
        super(KubeManagerInspect, self).__init__(ip, port, XmlDrv,
                                                 logger=logger, args=args, protocol=protocol)
        self.ip = ip

    def _join(self, *args):
        """Joins the args with ':'"""
        return ':'.join(args)

    def get_pod_list(self):
        '''
        Return List of all User created Pods.

        Return Info format:
        [{'nodename': 'nodec61', 'name': 'ctest-nginx-pod-92002975', 'phase': 'Running', 'ip': '10.204.217.101',
        'labels': {'map': {'element': 'ctest-namespace-02645930'}}, 'uuid': '456fad44-5d86-11e8-8b98-002590c55f6a'},
        {'nodename': 'nodec60', 'name': 'ctest-nginx-pod-25952679', 'phase': 'Running', 'ip': '10.204.217.100',
        'labels': {'map': {'element': 'ctest-namespace-02645930'}}, 'uuid': '456b97e5-5d86-11e8-8b98-002590c55f6a'},
        {'phase': 'Running', 'ip': '10.204.217.100', 'nodename': 'nodec60', 'uuid': '457330fe-5d86-11e8-8b98-002590c55f6a',
         'name': 'ctest-busybox-pod-87380339'}, {'nodename': 'nodec61', 'name': 'kube-dns-6f4fd4bdf-hbjss', 
         phase': 'Running', 'ip': '10.204.217.101',  'labels': {'map': {'element': 'kube-system'}}, 'uuid': '6b8eee9a-5d2f-11e8-b80b-002590c55f6a'}]
        
        Sample URL:
        http://10.204.217.71:8108/Snh_PodDatabaseList?
        '''
        pod_list = None
        try:
            p = self.dict_get('Snh_PodDatabaseList?')
            xpath = './PodDatabaseListResp/pods' 
            podsInstances = EtreeToDict(xpath).get_all_entry(p)
            pod_list = podsInstances.get('pods', [])
        except Exception as e:
            print(e)
        finally:
            return pod_list

    def get_pod_info(self ,pod_uuid):
        '''
        Return detailed info about Pod
        
        Return Info format :
        {'pod_node': 'nodec61', 'vm_interfaces': [{'vmi_uuid': '4611175a-5d86-11e8-9bc9-002590c55f6a'}],
        'pod_labels': {'map': {'element': 'ctest-namespace-02645930'}}, 'uuid': '456fad44-5d86-11e8-8b98-002590c55f6a',
        'node_ip': '10.204.217.101', 'owner': 'k8s', 'vrouter_uuid': {'VRUuid': {'vr_uuid': 'c140acf4-adab-40d4-ac0d-8a06c6f2e192'}},
        'pod_namespace': 'ctest-namespace-02645930', 'annotations': {'map': {'element': '456fad44-5d86-11e8-8b98-002590c55f6a'}},
        'name': 'ctest-nginx-pod-92002975__456fad44-5d86-11e8-8b98-002590c55f6a'}
        
        Sample URL:
        http://10.204.217.71:8108/Snh_VirtualMachineDatabaseList?x=456fad44-5d86-11e8-8b98-002590c55f6a
        '''
        podsInfo = None
        try:
            pod_req = 'Snh_VirtualMachineDatabaseList?x=%s' % pod_uuid
            p = self.dict_get(pod_req)
            xpath = './VirtualMachineDatabaseListResp/vms/list/VirtualMachineInstance' 
            podsInfo = EtreeToDict(xpath).get_all_entry(p)
        except Exception as e:
            print(e)
        finally:
            return podsInfo

    def get_namespace_list(self):
        '''
        Return list of all namespaces.
        
        Return Info format:
        [{'phase': 'Active', 'isolated': 'false', 'labels': {'map': None}, 'uuid': '693cb9d2-5d2f-11e8-b80b-002590c55f6a',
        'name': 'contrail'}, {'phase': 'Active', 'isolated': 'false', 'labels': {'map': None},
        'uuid': '65da2d5f-5d2f-11e8-b80b-002590c55f6a', 'name': 'kube-public'},
        'phase': 'Active', 'isolated': 'false', 'labels': {'map': {'element': 'default'}},
        'uuid': '6376554d-5d2f-11e8-b80b-002590c55f6a', 'name': 'default'},
        {'phase': 'Active', 'isolated': 'false', 'labels': {'map': None}, 'uuid': '64080bdd-5d2f-11e8-b80b-002590c55f6a',
        'name': 'kube-system'}, {'phase': 'Active', 'isolated': 'false', 'labels': {'map': None},
        'uuid': '439df569-5d86-11e8-8b98-002590c55f6a', 'name': 'ctest-namespace-02645930'}]
        
        Sample URL:
        http://10.204.217.71:8108/Snh_NamespaceDatabaseList?namespace_uuid=
        '''
        ns_list = None
        try:
            p = self.dict_get('Snh_NamespaceDatabaseList?namespace_uuid=')
            xpath = './NamespaceDatabaseListResp/namespaces' 
            nsInstances = EtreeToDict(xpath).get_all_entry(p)
            ns_list = nsInstances.get('namespaces', [])
        except Exception as e:
            print(e)
        finally:
            return ns_list
    
    def get_namespace_info(self, ns_uuid):
        '''
        Return detailed info about Namespace
        
        Return Info format :
        {'phase': 'Active', 'isolated': 'false', 'labels': {'map': {'element': 'default'}},
        'uuid': '6376554d-5d2f-11e8-b80b-002590c55f6a', 'name': 'default'}
        
        Sample URL:
        http://10.204.217.71:8108/Snh_NamespaceDatabaseList?namespace_uuid=6376554d-5d2f-11e8-b80b-002590c55f6a
        '''
        nsInfo = None
        try:
            ns_req = 'Snh_NamespaceDatabaseList?namespace_uuid=%s' % ns_uuid
            p = self.dict_get(ns_req)
            xpath = './NamespaceDatabaseListResp/namespaces/list/NamespaceInstance' 
            nsInfo = EtreeToDict(xpath).get_all_entry(p)
        except Exception as e:
            print(e)
        finally:
            return nsInfo
    
    def get_svc_or_ingress_lb_info(self, uuid):
        '''
        Return detailed info about Service
        
        Return Info format :
        {'uuid_to_service': '4569ec7e-5d86-11e8-8b98-002590c55f6a', 
        'lb_listeners': [{'lb_listener_uuid': '30ad28ed-43ae-4755-a2df-833ce8562906'}],
        'vm_interfaces': [{'vmi_uuid': '0f7128a9-705a-41d7-8aa0-50d618d20dfa'}],
        'fq_name': ['default-domain', 'ctest-namespace-02645930', 'ctest-nginx-svc-48573694__4569ec7e-5d86-11e8-8b98-002590c55f6a'],
        'name': 'ctest-nginx-svc-48573694__4569ec7e-5d86-11e8-8b98-002590c55f6a', 
        'external_ip': 'None', 'annotations': {'map': {'element': 'k8s'}}, 'selectors': None}
        
        Sample URL:
        http://10.204.217.71:8108/Snh_LoadbalancerDatabaseList?x=4569ec7e-5d86-11e8-8b98-002590c55f6a
        '''
        lbInfo = None
        try:
            lb_req = 'Snh_LoadbalancerDatabaseList?x=%s' % uuid
            p = self.dict_get(lb_req)
            xpath = './LoadbalancerDatabaseListResp/lbs/list/LoadbalancerInstance' 
            lbInfo = EtreeToDict(xpath).get_all_entry(p)
        except Exception as e:
            print(e)
        finally:
            return lbInfo

    def get_network_policy_info(self, np_uuid):
        '''
        Return detailed info about Network Policy
        
        Return Info format :
        {'name_space': 'default', 'uuid': '3855b8f9-5da1-11e8-8b98-002590c55f6a', 
        'spec_string': "{u'policyTypes': [u'Egress'], u'egress': [{u'ports': [{u'protocol': u'TCP', u'port': 80}]}],
         u'podSelector': {u'matchLabels': {u'app': u'client1_ns1'}}}",
        'spec': {'NetworkPolicySpec': {'ingress': None, 'egress': [{'toPolicy': None, 'ports': [{'protocol': 'TCP', 'port': '80'}]}],
        'podSelector': {'NetworkPolicyLabelSelectors': {'matchLabels': {'map': {'element': 'client1_ns1'}}}}}}, 
        'vnc_firewall_policy_fqname': 'default-policy-management:default-egress-ports-pod', 'name': 'egress-ports-pod'}
        
        Sample URL:
        http://10.204.217.52:8108/Snh_NetworkPolicyDatabaseList?network_policy_uuid=42735572-5d9d-11e8-8b98-002590c55f6a
        '''
        npInstance = None
        try:
            np_req = 'Snh_NetworkPolicyDatabaseList?network_policy_uuid=%s' % np_uuid
            p = self.dict_get(np_req)
            xpath = './NetworkPolicyDatabaseListResp/network_policies/list/NetworkPolicyInstance' 
            npInstance = EtreeToDict(xpath).get_all_entry(p)
        except Exception as e:
            print(e)
        finally:
            return npInstance
        
if __name__ == '__main__':
    k8s = KubeManagerInspect('10.204.217.52')
    import pdb; pdb.set_trace()
    v = k8s.get_pod_list()
    #y = k8s.get_pod_info(pod_uuid = "456fad44-5d86-11e8-8b98-002590c55f6a")
    z = k8s.get_namespace_list()
    #zz = k8s.get_namespace_info( ns_uuid = "6376554d-5d2f-11e8-b80b-002590c55f6a")
    #vv = k8s.get_svc_or_ingress_lb_info(svc_uuid = "4088278e-5d9d-11e8-8b98-002590c55f6a")
    p = k8s.get_network_policy_info(np_uuid ="3855b8f9-5da1-11e8-8b98-002590c55f6a")
