import os
import json
import pprint
import urllib2
import requests
import threading
import logging as LOG
from lxml import etree
from tcutils.util import *
from common import log_orig as contrail_logging
from cfgm_common.exceptions import PermissionDenied

LOG.basicConfig(format='%(levelname)s: %(message)s', level=LOG.INFO)


class JsonDrv (object):
    _DEFAULT_HEADERS = {
        'Content-type': 'application/json; charset="UTF-8"',
    }
    _DEFAULT_AUTHN_URL = "/v2.0/tokens"

    def __init__(self, vub, logger=LOG, args=None):
        self.log = logger
        self._vub = vub
        self._headers = dict()
        self._args = args
        msg_size = os.getenv('INTROSPECT_LOG_MAX_MSG', '10240')
        self.more_logger = contrail_logging.getLogger('introspect',
                                                      log_to_console=False,
                                                      max_message_size=msg_size)
        # Since introspect log is a single file, need locks
        self.lock = threading.Lock()
        self.verify = True
        if self._args:
            self.verify = (not getattr(self._args, 'api_insecure')) \
                           and self._args.certbundle

    def _auth(self):
        if self._args:
            if os.getenv('OS_AUTH_URL'):
                if 'v3' in os.getenv('OS_AUTH_URL'):
                   url = os.getenv('OS_AUTH_URL') + '/auth/tokens'
                else:
                    url = os.getenv('OS_AUTH_URL') + '/tokens'
            elif 'v3' in self._args.auth_url:
                self._DEFAULT_AUTHN_URL = "/v3/auth/tokens"
                url = "%s://%s:%s%s" % (self._args.auth_protocol,
                                        self._args.auth_ip,
                                        self._args.auth_port,
                                        self._DEFAULT_AUTHN_URL)
            else:
                url = "%s://%s:%s%s" % (self._args.auth_protocol,
                                        self._args.auth_ip,
                                        self._args.auth_port,
                                        self._DEFAULT_AUTHN_URL)
            if self._args.insecure:
                verify = not self._args.insecure
            else:
                verify = self._args.certbundle
            if 'v3' in (os.getenv('OS_AUTH_URL') or self._args.auth_url):
                self._authn_body = \
                '{"auth": {"identity": {"methods": ["password"],"password": {"user": {"domain": {"name": "%s"},"name": "%s","password": "%s"}}},\
                    "scope": {"project": {"domain": {"name": "%s"},"name": "%s"}}}}' %(
                                          self._args.admin_domain,
                                          self._args.admin_username,
                                          self._args.admin_password,
                                          self._args.admin_domain,
                                          self._args.admin_username)
            else:
                self._authn_body = \
                    '{"auth":{"passwordCredentials":{"username": "%s", "password": "%s"}, "tenantName":"%s"}}' % (
                        self._args.stack_user,
                        self._args.stack_password,
                        self._args.project_name)
            response = requests.post(url, data=self._authn_body,
                                     headers=self._DEFAULT_HEADERS,
                                     verify=verify)
            if response.status_code == 200:
                # plan is to re-issue original request with new token
                authn_content = json.loads(response.text)
                self._auth_token = authn_content['access']['token']['id']
                self._headers = {'X-AUTH-TOKEN': self._auth_token}
                return
            elif response.status_code == 201:
                authn_content = response.headers
                self._auth_token = authn_content['X-Subject-Token']
                self._headers = {'X-AUTH-TOKEN': self._auth_token}
                return
        raise RuntimeError('Authentication Failure')

    def load(self, url, retry=True):
        self.common_log("Requesting: %s" %(url))
        if url.startswith('https:'):
            resp = requests.get(url, headers=self._headers, verify=self.verify)
        else:
            resp = requests.get(url, headers=self._headers)
        if resp.status_code in [401, 403]:
            if retry:
                self._auth()
                return self.load(url, False)
            else:
                raise PermissionDenied('Permission Denied')
        if resp.status_code == 200:
            output = json.loads(resp.text)
            with self.lock:
                self.more_logger.debug(pprint.pformat(output))
            return output

        self.common_log("Response Code: %d" % resp.status_code)
        return None

    def put(self, url, payload, retry=True):
        self.common_log("Posting: %s, payload %s"%(url, payload))
        self._headers.update({'Content-type': 'application/json; charset="UTF-8"'})
        data = json.dumps(payload)
        resp = requests.put(url, headers=self._headers, data=data)
        if resp.status_code == 401:
            if retry:
                self._auth()
                return self.put(url, payload, retry=False)
        return resp

    def common_log(self, line, mode=LOG.DEBUG):
        self.log.log(mode, line)
        with self.lock:
            self.more_logger.log(mode, line)

class XmlDrv (object):

    def __init__(self, vub, logger=LOG, args=None):
        self.log = logger
        self._vub = vub
        self.more_logger = contrail_logging.getLogger('introspect',
                                                      log_to_console=False)
        # Since introspect log is a single file, need locks
        self.lock = threading.Lock()
        self._args = args
        self.verify = True
        self.client_cert = None
        if self._args:
            self.verify = (not getattr(self._args, 'introspect_insecure', True)) \
                           and self._args.certbundle
            self.client_cert = (self._args.introspect_certfile,
                                self._args.introspect_keyfile)

    def load(self, url, raw_data=False):
        self.common_log("Requesting: %s" %(url))
        try:
            resp = requests.get(url, cert=self.client_cert,
                verify=self.verify)
            output = etree.fromstring(resp.text) if not raw_data else resp.text
            self.log_xml(self.more_logger, output)
            return output
        except requests.exceptions.SSLError, e:
            self.log.error("SSL error: %s" % (e))
            return None
        except requests.ConnectionError, e:
            self.log.error("Socket Connection error: %s", str(e))
            return None
        except:
            self.log.error("Error while getting the url: %s, error: %s" % (
                url, str(e)))
            return None

    def common_log(self, line, mode=LOG.DEBUG):
        self.log.log(mode, line)
        with self.lock:
            self.more_logger.log(mode, line)

    def log_xml(self, logger, line, mode=LOG.DEBUG):
        ''' line is of type lxml.etree._Element
        '''
        logline = etree.tostring(line, pretty_print=True) if type(line) is etree._Element else line
        with self.lock:
            logger.log(mode, logline)


class VerificationUtilBase (object):

    def __init__(self, ip, port, drv=JsonDrv, logger=LOG, args=None,
                    protocol='http'):
        self.log = logger
        self._ip = ip
        self._port = port
        self._drv = drv(self, logger=logger, args=args)
        self._force_refresh = False
        self._protocol = protocol

    def get_force_refresh(self):
        return self._force_refresh

    def set_force_refresh(self, force=False):
        self._force_refresh = force
        return self.get_force_refresh()

    def _mk_url_str(self, path=''):
        if path.startswith('http' or 'https'):
            return path
        else:
            return self._protocol + "://%s:%s/%s" % (self._ip, str(self._port), path)

    def dict_get(self, path='',url='', raw_data=False):
        try:
            if path:
                return self._drv.load(self._mk_url_str(path))
            if url:
                return self._drv.load(url, raw_data=raw_data)
        except urllib2.HTTPError:
            return None
    # end dict_get

    def put(self, payload, path='', url=''):
        try:
            if path:
                return self._drv.put(self._mk_url_str(path), payload)
            if url:
                return self._drv.put(url, payload)
        except urllib2.HTTPError:
            return None

def elem2dict(node, alist=False):
    d = list() if alist else dict()
    for e in node.iterchildren():
        #key = e.tag.split('}')[1] if '}' in e.tag else e.tag
        if e.tag == 'list':
            value = elem2dict(e, alist=True)
        else:
            value = e.text if e.text else elem2dict(e)
        if type(d) == type(list()):
            d.append(value)
        else:
            d[e.tag] = value
    return d

class Result (dict):
    def __init__(self, d={}):
        super(Result, self).__init__()
        if type(d) is not dict and hasattr(d, 'tag'):
            d = elem2dict(d)
        self.update(d)

    def xpath(self, *plist):
        ''' basic path '''
        d = self
        try:
            for p in plist:
                d = d[p]
            return d
        except (KeyError, IndexError), e:
            return None

class EtreeToDict(object):

    """Converts the xml etree to dictionary/list of dictionary."""

    def __init__(self, xpath):
        self.xpath = xpath
        self.xml_list = ['policy-rule']

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

            if elem.tag == 'data':
                # Remove CDATA; if present
                text = elem.text.replace("<![CDATA[<", "<").strip("]]>")
                nxml = etree.fromstring(text)
                rval = self._get_one(nxml, a_list)
            else:
                rval = self._get_one(elem, a_list)

            if elem.tag in self.xml_list:
                val.update({xp.tag: self._handle_list(xp)})
            if elem.tag in rval.keys():
                val.update({elem.tag: rval[elem.tag]})
            elif 'SandeshData' in elem.tag:
                val.update({xp.tag: rval})
            else:
                val.update({elem.tag: rval})
        return val

    def get_all_entry(self, path):
        """All entries in the etree is converted to the dictionary

        Returns the list of dictionary/didctionary.
        """
        xps = path.xpath(self.xpath)
        if not xps:
            # sometime ./xpath dosen't work; work around
            # should debug to find the root cause.
            xps = path.xpath(self.xpath.strip('.'))
        if type(xps) is not list:
            return self._get_one(xps)

        val = []
        for xp in xps:
            val.append(self._get_one(xp))
        if len(val) == 1:
            return val[0]
        return val

    def find_entry(self, path, match):
        """Looks for a particular entry in the etree.
    
        Returns the element looked for/None.
        """
        xp = path.xpath(self.xpath)
        f = filter(lambda x: x.text == match, xp)
        if len(f):
            return f[0].text
        return None
