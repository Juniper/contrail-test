
from tcutils.vro.vro_api_utils import VroUtilBase

class VroInspectUtils(VroUtilBase):
    
    ''' pasrse vco inventory to veriy and get object realations'''
     
    def __init__(self, ip, port, user, passd, params=None):
        super(VroInspectUtils,self).__init__(ip, port, user, passd)
        #self.workflow = workflow
        #self.params = params
        
    def get_parent(self, name, type=None):
            return self.get_contrail_connection(name, type)
    
    def get_contrail_connection(self,name=None, type=None):
        path = 'catalog/Contrail/' + type
        url = self.get_query_url(path,name)
        wf_details = self.dict_get(url)
        return self.get_id(wf_details)
    
    def get_object_dunes_id(self, result):
        pass
    
    def get_project(self, name=None):
        pass
    
    def get_vn(self, name=None):
        pass
    
    def get_policy(self, name=None):
        pass
    
    def get_object_relation(self,object):
        pass
    
    def get_wf_id(self, name):
        query_url = self.get_query_url(query_string=name)
        wf_details = self.dict_get(query_url)
        return self.get_id(wf_details)
    
    def execute(self,wf_id, payload):
        url = self.get_execution_url(wf_id)
        return self.put(url, payload)
        
    def get_id(self,wf_details):
        for i  in wf_details['link'][0]['attributes']:
            if 'id' in i.values() or  'dunesId' in i.values():
                name,value = i.values()
                return value
        return ''
    def get_wf_status(self,path=None):
        result = self.dict_get(path)
        return result['value']