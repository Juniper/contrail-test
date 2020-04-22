from __future__ import print_function
from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import object
import os
import sys
import configparser
import socket
import requests
import warnings
from lxml import etree
from common import log_orig as contrail_logging
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
from common.contrail_services import BackupImplementedServices, \
    ServiceHttpPortMap, CONTRAIL_PODS_SERVICES_MAP

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
            resp = requests.get(url, timeout=self._timeout, verify=False, #(self._cacert)
                    cert=(self._certfile, self._keyfile))
        if resp.status_code == requests.codes.ok:
            return etree.fromstring(resp.text)
        else:
            if self._debug:
                print('URL: %s : HTTP error: %s' % (url, str(resp.status_code)))
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
                print('UVE: %s : not found' % (path))
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
            if 'element' in list(rval.keys()):
                a_list.append(rval['element'])
            elif 'list' in list(rval.keys()):
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
                if elem.tag in list(rval.keys()):
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
        f = [x for x in xp if x.text == match]
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
            print('{0}: Introspect port not found'.format(svc_name))
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
            print('{0}: NodeStatusUVE not found'.format(svc_name))
        return None, None
    node_status = [item for item in node_status if 'process_status' in item]
    if not len(node_status):
        if debug:
            print('{0}: ProcessStatus not present in NodeStatusUVE'.format(
                svc_name))
        return None, None
    process_status_info = node_status[0]['process_status']
    if len(process_status_info) == 0:
        if debug:
            print('{0}: Empty ProcessStatus in NodeStatusUVE'.format(svc_name))
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
    except requests.ConnectionError as e:
        if debug:
            print('Socket Connection error : %s' % (str(e)))
        svc_uve_status = "connection-error"
    except (requests.Timeout, socket.timeout) as te:
        if debug:
            print('Timeout error : %s' % (str(te)))
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
#    if svc_uve_description is not None and svc_uve_description is not '':
#        svc_status = svc_status + ' (' + svc_uve_description + ')'
    return svc_status, svc_uve_description
# end get_svc_uve_info

def get_container_status(container, containers):
    found = container in containers
    return 'active' if found else 'inactive'

def contrail_status(inputs=None, host=None, role=None, service=None,
                    debug=False, detail=False, timeout=30,
                    keyfile=None, certfile=None, cacert=None,
                    logger=None, refresh=False):
    status_dict = dict()
    if not inputs:
        from common import contrail_test_init
        params = os.environ.get('TEST_CONFIG_FILE') or\
            '/contrail-test/contrail_test_input.yaml'
        inputs = contrail_test_init.ContrailTestInit(params)
    logger = logger or inputs.logger
    certfile = certfile or inputs.introspect_certfile
    keyfile = keyfile or inputs.introspect_keyfile
    cacert = cacert or inputs.introspect_cafile

    if host:
        host = [host] if not isinstance(host, list) else host
    if role:
        role = [role] if not isinstance(role, list) else role
    if service:
        service = [service] if not isinstance(service, list) else service

    for node in host or inputs.host_ips:
        if refresh:
            inputs.refresh_containers(node)
        containers = inputs.get_active_containers(node)
        logger.info(node)
        status_dict[node] = dict()
        if service:
            for svc in service:
                desc = None
                status = get_container_status(
                    inputs.get_container_name(node, svc), containers)
                if status == 'active':
                    status, desc = get_svc_uve_info(node, svc, debug, detail,
                                   timeout, keyfile, certfile, cacert)
                status_dict[node][svc] = {'status': status, 'description': desc}
                logger.info('    %s:%s%s'%(svc, status, ' (%s)'%
                    desc if desc else ''))
        else:
            for r in role or inputs.get_roles(node):
                logger.info('  '+r)
                if r not in CONTRAIL_PODS_SERVICES_MAP:
                    logger.error('role '+r+' is not yet supported')
                    continue
                for svc in CONTRAIL_PODS_SERVICES_MAP[r]:
                    desc = None
                    if inputs.deployer == 'helm' and svc == 'config-rabbitmq':
                        continue
                    status = get_container_status(
                        inputs.get_container_name(node, svc), containers)
                    if status == 'active':
                        status, desc = get_svc_uve_info(node, svc,
                            debug, detail, timeout, keyfile, certfile, cacert)
                    status_dict[node][svc] = {'status': status, 'description': desc}
                    logger.info('    %s:%s%s'%(svc, status, ' (%s)'%
                        desc if desc else ''))
    return status_dict

def main():
    from common import contrail_test_init
    inputs = contrail_test_init.ContrailTestInit(sys.argv[1])
    host = sys.argv[2] if len(sys.argv) > 2 else None
    role = sys.argv[3] if len(sys.argv) > 3 else None
    service = sys.argv[4] if len(sys.argv) > 4 else None
    logger = contrail_logging.getLogger('contrail_status')
    contrail_status(inputs, host, role, service, logger=logger)

if __name__ == "__main__":
    main()
