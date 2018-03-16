import sys
import ConfigParser
import socket
import requests
import warnings
from lxml import etree
from common.contrail_test_init import ContrailTestInit
try:
    from requests.packages.urllib3.exceptions import SubjectAltNameWarning
    warnings.filterwarnings('ignore', category=SubjectAltNameWarning)
except:
    try:
        from urllib3.exceptions import SubjectAltNameWarning
        warnings.filterwarnings('ignore', category=SubjectAltNameWarning)
    except:
        pass
warnings.filterwarnings('ignore', ".*SNIMissingWarning.*")
warnings.filterwarnings('ignore', ".*InsecurePlatformWarning.*")
warnings.filterwarnings('ignore', ".*SubjectAltNameWarning.*")

# Inputs yaml file/ContrailTestInit, node, service, role
CONTRAIL_SERVICES = {'vrouter' : ['vrouter-nodemgr', 'agent'],
                     'control' : ['control-nodemgr',
                                  'control',
                                  'named',
                                  'dns'],
                     'config' : ['config-nodemgr',
                                 'api-server',
                                 'schema',
                                 'svc-monitor',
                                 'device-manager'],
                     'config-database' : ['config-cassandra',
                                          'configdb-nodemgr',
                                          'config-zookeeper',
                                          'config-rabbitmq'],
                     'analytics' : ['analytics-nodemgr',
                                    'analytics-api',
                                    'collector',
                                    'query-engine',
                                    'alarm-gen',
                                    'snmp-collector',
                                    'topology'],
                     'analytics-database' : ['analytics-cassandra',
                                             'analyticsdb-nodemgr',
                                             'analytics-zookeeper',
                                             'analytics-kafka'],
                     'webui' : ['webui', 'webui-middleware', 'redis'],
                     'kubernetes' : ['contrail-kube-manager'],
                    }
BackupImplementedServices = ["schema",
                             "svc-monitor",
                             "device-manager",
                             "contrail-kube-manager"]
ServiceHttpPortMap = {
    "agent" : 8085,
    "control" : 8083,
    "collector" : 8089,
    "query-engine" : 8091,
    "analytics-api" : 8090,
    "dns" : 8092,
    "api-server" : 8084,
    "schema" : 8087,
    "svc-monitor" : 8088,
    "device-manager" : 8096,
    "analytics-nodemgr" : 8104,
    "vrouter-nodemgr" : 8102,
    "control-nodemgr" : 8101,
    "analyticsdb-nodemgr" : 8103,
    "configdb-nodemgr" : 8100,
    "alarm-gen" : 5995,
    "snmp-collector" : 5920,
    "topology" : 5921,
    "contrail-kube-manager" : 8108,
}

class IntrospectUtil(object):
    def __init__(self, ip, port, debug, timeout, keyfile, certfile, cacert):
        self._ip = ip
        self._port = port
        self._debug = debug
        self._timeout = timeout
        self._certfile = certfile
        self._keyfile = keyfile
        self._cacert = cacert
    #end __init__

    def _mk_url_str(self, path, secure=False):
        if secure:
            return "https://%s:%d/%s" % (self._ip, self._port, path)
        return "http://%s:%d/%s" % (self._ip, self._port, path)
    #end _mk_url_str

    def _load(self, path):
        url = self._mk_url_str(path)
        try:
            resp = requests.get(url, timeout=self._timeout)
        except requests.ConnectionError:
            url = self._mk_url_str(path, True)
            resp = requests.get(url, timeout=self._timeout, verify=\
                    self._cacert, cert=(self._certfile, self._keyfile))
        if resp.status_code == requests.codes.ok:
            return etree.fromstring(resp.text)
        else:
            if self._debug:
                print 'URL: %s : HTTP error: %s' % (url, str(resp.status_code))
            return None
    #end _load

    def get_uve(self, tname):
        path = 'Snh_SandeshUVECacheReq?x=%s' % (tname)
        xpath = './/' + tname
        p = self._load(path)
        if p is not None:
            return EtreeToDict(xpath).get_all_entry(p)
        else:
            if self._debug:
                print 'UVE: %s : not found' % (path)
            return None
    #end get_uve
#end class IntrospectUtil

class EtreeToDict(object):
    """Converts the xml etree to dictionary/list of dictionary."""

    def __init__(self, xpath):
        self.xpath = xpath
    #end __init__

    def _handle_list(self, elems):
        """Handles the list object in etree."""
        a_list = []
        for elem in elems.getchildren():
            rval = self._get_one(elem, a_list)
            if 'element' in rval.keys():
                a_list.append(rval['element'])
            elif 'list' in rval.keys():
                a_list.append(rval['list'])
            else:
                a_list.append(rval)

        if not a_list:
            return None
        return a_list
    #end _handle_list

    def _get_one(self, xp, a_list=None):
        """Recrusively looks for the entry in etree and converts to dictionary.
        Returns a dictionary.
        """
        val = {}

        child = xp.getchildren()
        if not child:
            val.update({xp.tag: xp.text})
            return val

        for elem in child:
            if elem.tag == 'list':
                val.update({xp.tag: self._handle_list(elem)})
            else:
                rval = self._get_one(elem, a_list)
                if elem.tag in rval.keys():
                    val.update({elem.tag: rval[elem.tag]})
                else:
                    val.update({elem.tag: rval})
        return val
    #end _get_one

    def get_all_entry(self, path):
        """All entries in the etree is converted to the dictionary
        Returns the list of dictionary/didctionary.
        """
        xps = path.xpath(self.xpath)

        if type(xps) is not list:
            return self._get_one(xps)

        val = []
        for xp in xps:
            val.append(self._get_one(xp))
        return val
    #end get_all_entry

    def find_entry(self, path, match):
        """Looks for a particular entry in the etree.
        Returns the element looked for/None.
        """
        xp = path.xpath(self.xpath)
        f = filter(lambda x: x.text == match, xp)
        if len(f):
            return f[0].text
        return None
    #end find_entry

#end class EtreeToDict

def get_http_server_port(svc_name, debug):
    if svc_name in ServiceHttpPortMap:
        return ServiceHttpPortMap[svc_name]
    else:
        if debug:
            print '{0}: Introspect port not found'.format(svc_name)
        return -1

def get_svc_uve_status(host, svc_name, debug, timeout, keyfile, certfile, cacert):
    # Get the HTTP server (introspect) port for the service
    http_server_port = get_http_server_port(svc_name, debug)
    if http_server_port == -1:
        return 'active', None
    # Now check the NodeStatus UVE
    svc_introspect = IntrospectUtil(host, http_server_port, debug, \
                                    timeout, keyfile, certfile, cacert)
    node_status = svc_introspect.get_uve('NodeStatus')
    if node_status is None:
        if debug:
            print '{0}: NodeStatusUVE not found'.format(svc_name)
        return None, None
    node_status = [item for item in node_status if 'process_status' in item]
    if not len(node_status):
        if debug:
            print '{0}: ProcessStatus not present in NodeStatusUVE'.format(
                svc_name)
        return None, None
    process_status_info = node_status[0]['process_status']
    if len(process_status_info) == 0:
        if debug:
            print '{0}: Empty ProcessStatus in NodeStatusUVE'.format(svc_name)
        return None, None
    description = process_status_info[0]['description']
    for connection_info in process_status_info[0].get('connection_infos', []):
        if connection_info.get('type') == 'ToR':
            description = 'ToR:%s connection %s' % (connection_info['name'], connection_info['status'].lower())
    return process_status_info[0]['state'], description

def get_svc_uve_info(host, svc_name, debug, detail, timeout, keyfile, certfile, cacert):
    # Extract UVE state only for running processes
    svc_uve_description = None
    svc_status = 'active'
    try:
        svc_uve_status, svc_uve_description = \
            get_svc_uve_status(host, svc_name, debug, timeout, keyfile,\
                               certfile, cacert)
    except requests.ConnectionError, e:
        if debug:
            print 'Socket Connection error : %s' % (str(e))
        svc_uve_status = "connection-error"
    except (requests.Timeout, socket.timeout) as te:
        if debug:
            print 'Timeout error : %s' % (str(te))
        svc_uve_status = "connection-timeout"

    if svc_uve_status is not None:
        if svc_uve_status == 'Non-Functional':
            svc_status = 'initializing'
        elif svc_uve_status == 'connection-error':
            if svc_name in BackupImplementedServices:
                svc_status = 'backup'
            else:
                svc_status = 'initializing'
        elif svc_uve_status == 'connection-timeout':
            svc_status = 'timeout'
    else:
        svc_status = 'initializing'
    if svc_uve_description is not None and svc_uve_description is not '':
        svc_status = svc_status + ' (' + svc_uve_description + ')'
    return svc_status
# end get_svc_uve_info

def get_container_status(container, containers):
    found = container in containers
    return 'active' if found else 'inactive'

def contrail_status(inputs, host=None, role=None, service=None,
                    debug=False, detail=False, timeout=30,
                    keyfile=None, certfile=None, cacert=None):
    status_dict = dict()
    nodes = [host] if host else inputs.host_ips
    for node in nodes:
        containers = inputs.get_active_containers(node)
        print node
        status_dict[node] = dict()
        if service:
            status = get_container_status(inputs.get_container_name(node,
                                          service), containers)
            if status == 'active':
                status = get_svc_uve_info(node, svc, debug, detail,
                         timeout, keyfile, certfile, cacert)
            status_dict[node][service] = status
            print '    %s:%s'(service, status)
        else:
            roles = [role] if role else inputs.get_roles(node)
            for r in roles:
                print '  '+r
                if r not in CONTRAIL_SERVICES:
                    print 'role '+r+' is not yet supported'
                    continue
                status_dict[node] = dict()
                for svc in CONTRAIL_SERVICES[r]:
                    status = get_container_status(
                        inputs.get_container_name(node, svc), containers)
                    if status == 'active':
                        status = get_svc_uve_info(node, svc,
                            debug, detail, timeout, keyfile, certfile, cacert)
                    status_dict[node][svc] = status
                    print '    %s:%s'%(svc, status)
    return status_dict

def main():
    inputs = ContrailTestInit(sys.argv[1])
    host = sys.argv[2] if len(sys.argv) > 2 else None
    role = sys.argv[3] if len(sys.argv) > 3 else None
    service = sys.argv[4] if len(sys.argv) > 4 else None
    contrail_status(inputs, host, role, service)

if __name__ == "__main__":
    main()
