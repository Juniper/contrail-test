import os
import json
import pprint
import urllib2
import requests
import threading
import logging as LOG
from lxml import etree

from common import log_orig as contrail_logging

LOG.basicConfig(format='%(levelname)s: %(message)s', level=LOG.INFO)


class JsonDrv (object):
    _DEFAULT_HEADERS = {
        'Content-type': 'application/json; charset="UTF-8"',
    }
    _DEFAULT_AUTHN_URL = "/v2.0/tokens"

    def __init__(self, vub, logger=LOG, args=None, use_admin_auth=False):
        self.log = logger
        self._vub = vub
        self._headers = None
        self._args = args
        self._use_admin_auth = use_admin_auth
        msg_size = os.getenv('INTROSPECT_LOG_MAX_MSG', '10240')
        self.more_logger = contrail_logging.getLogger('introspect',
                                                      log_to_console=False,
                                                      max_message_size=msg_size)
        # Since introspect log is a single file, need locks
        self.lock = threading.Lock()

    def _auth(self):
        if self._args:
            if os.getenv('OS_AUTH_URL'):
                url = os.getenv('OS_AUTH_URL') + '/tokens'
            else:
                url = "%s://%s:%s%s" % (self._args.auth_protocol,
                                        self._args.auth_ip,
                                        self._args.auth_port,
                                        self._DEFAULT_AUTHN_URL)
            insecure = bool(os.getenv('OS_INSECURE',True))
            verify = not insecure
            self._authn_body = \
                '{"auth":{"passwordCredentials":{"username": "%s", "password": "%s"}, "tenantName":"%s"}}' % (
                    self._args.admin_username if self._use_admin_auth else self._args.stack_user,
                    self._args.admin_password if self._use_admin_auth else self._args.stack_password,
                    self._args.admin_tenant if self._use_admin_auth else self._args.project_name)
            response = requests.post(url, data=self._authn_body,
                                     headers=self._DEFAULT_HEADERS,
                                     verify=verify)
            if response.status_code == 200:
                # plan is to re-issue original request with new token
                authn_content = json.loads(response.text)
                self._auth_token = authn_content['access']['token']['id']
                self._headers = {'X-AUTH-TOKEN': self._auth_token}
                return
        raise RuntimeError('Authentication Failure')

    def load(self, url, retry=True):
        self.common_log("Requesting: %s" %(url))
        resp = requests.get(url, headers=self._headers)
        if resp.status_code == 401:
            if retry:
                self._auth()
                return self.load(url, False)
        if resp.status_code == 200:
            output = json.loads(resp.text)
            with self.lock:
                self.more_logger.debug(pprint.pformat(output))
            return output

        self.common_log("Response Code: %d" % resp.status_code)
        return None

    def common_log(self, line, mode=LOG.DEBUG):
        self.log.log(mode, line)
        with self.lock:
            self.more_logger.log(mode, line)

class XmlDrv (object):

    def __init__(self, vub, logger=LOG, args=None, use_admin_auth=False):
        self.log = logger
        self._vub = vub
        self.more_logger = contrail_logging.getLogger('introspect',
                                                      log_to_console=False)
        # Since introspect log is a single file, need locks
        self.lock = threading.Lock()
        if args:
            pass

    def load(self, url):
        try:
            self.common_log("Requesting: %s" %(url))
            resp = requests.get(url)
            output = etree.fromstring(resp.text)
            self.log_xml(self.more_logger, output)
            return output
        except requests.ConnectionError, e:
            self.log.error("Socket Connection error: %s", str(e))
            return None

    def common_log(self, line, mode=LOG.DEBUG):
        self.log.log(mode, line)
        with self.lock:
            self.more_logger.log(mode, line)

    def log_xml(self, logger, line, mode=LOG.DEBUG):
        ''' line is of type lxml.etree._Element
        '''
        logline = etree.tostring(line, pretty_print=True)
        with self.lock:
            logger.log(mode, logline)


class VerificationUtilBase (object):

    def __init__(self, ip, port, drv=JsonDrv, logger=LOG, args=None, use_admin_auth=False):
        self.log = logger
        self._ip = ip
        self._port = port
        self._drv = drv(self, logger=logger, args=args, use_admin_auth=use_admin_auth)
        self._force_refresh = False

    def get_force_refresh(self):
        return self._force_refresh

    def set_force_refresh(self, force=False):
        self._force_refresh = force
        return self.get_force_refresh()

    def _mk_url_str(self, path=''):
        if path.startswith('http:'):
            return path
        return "http://%s:%s/%s" % (self._ip, str(self._port), path)

    def dict_get(self, path='',url=''):
        try:
            if path:
                return self._drv.load(self._mk_url_str(path))
            if url:
                return self._drv.load(url)
        except urllib2.HTTPError:
            return None
    # end dict_get


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
        except KeyError, e:
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
