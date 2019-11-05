from builtins import object
import requests, json
import re
requests.packages.urllib3.disable_warnings()

class AuthVRO(object):
    def __init__(self,uname,passwd):
        self.uname = uname
        self.passwd = passwd

    def get_auth(self):
        pass

class SimpleAuthVRO(AuthVRO):

    def __init__(self,uname,passwd):
        super(SimpleAuthVRO, self).__init__(uname,passwd)   

    def get_auth(self):
        auth = dict()
        auth['simple_auth'] = (self.uname,self.passwd)
        return auth

class JsonDrv(object):
    def __init__(self, uname, passd, auth_type = 'simple', verify=False):
        #super(JsonDrv, self).__init__\
        #            (self,name,template)
        self._headers = {'Content-Type':'application/json','Accept':'application/json'}
        self.uname = uname
        self.passd = passd
        self.auth_type = auth_type
        self.verify = verify
        self.auth = self._get_auth

    @property
    def _get_auth(self):
        if self.auth_type == 'simple':
            return SimpleAuthVRO(self.uname,self.passd).get_auth()
        else:
            None

    def load(self, url):
        if 'simple_auth' in self.auth:
            response =  requests.get(url,
               headers=self._headers,
               auth=self.auth['simple_auth'],
               verify=self.verify)
            if response.status_code == 200:
               return json.loads(response.text)
        return ''

    def put(self,url, payload):
        if 'simple_auth' in self.auth:
            data = json.dumps(payload)
            response =  requests.post(url,
               headers=self._headers,
               auth=self.auth['simple_auth'],
               data=data,
               verify=self.verify)
            if response.status_code == 202:
                output = ''
                if response.text:
                    output = json.loads(response.text)
                return response.headers,output
        return ''
class VroUtilBase(object):
    
    def __init__(self, ip, port, uname, passd, api_string='/vco/api/', workflow=None, template=None, drv=JsonDrv):
        self.uname = uname
        self.passd = passd
        self.ip = ip
        self.port = port
        self.api_string = api_string
        self.base_url = self.get_base_url
        self.drv = drv(uname, passd)
        
    
    @property
    def get_base_url(self):
        return 'https://' + self.ip + ':' + self.port + self.api_string
    
    def get_query_url(self, path='workflows', query_string = None):
        #make query for catalog and workflows with query condition
        self.query_string = query_string
        is_uuid = re.search(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',self.query_string)
        if is_uuid:
            condition = '/?conditions=uuid='
        else:
            condition = '/?conditions=name='
        return self.base_url + path + condition + self.query_string

    def get_execution_url(self, execution_id=None):
        #make execution query
        self.execution_string = 'workflows/' + execution_id + '/executions'
        return self.base_url + self.execution_string

    def get_workflow_Staus(self):
        status = self.drv.execute.status
        return status
    
    def dict_get(self, url):
        return self.drv.load(url)
    
    def put(self, url, payload):
        return self.drv.put(url, payload)

