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

    def get_obj_from_catalog(self, obj, obj_name=None):
        path = 'catalog/Contrail/' + obj
        query_url = self.get_query_url(path=path, query_string=obj_name)
        results = self.dict_get(query_url)
        results = results['link']
        obj_catalog = []
        for result in results:
            temp = {}
            if not obj_name:
                obj_name = self.get_obj_name_from_catalog(result['attributes'])
            obj_ref = self.dict_get(result['href'])
            temp[obj_name] = obj_ref['attributes']
            obj_catalog.append(temp)
            obj_name = None
        return obj_catalog
    
    def get_obj_entry_from_catalog(self, obj, obj_name, obj_entry):
        catalog = self.get_obj_from_catalog(obj, obj_name)
        for entry in catalog[0][obj_name]:
            if entry['name'] == obj_entry:
                return entry['value']
        return None
    
    def get_obj_name_from_catalog(self, res):
        for entry in res:
            if entry['name'] == 'name':
                return entry['value']
        return None
    
    def parse_wf_object(self, obj):
        pass

    def get_object_dunes_id(self, result):
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
            if 'id' in list(i.values()) or  'dunesId' in list(i.values()):
                name,value = list(i.values())
                return value
        return ''
    def get_wf_status(self,path=None):
        result = self.dict_get(path)
        return result['value']
    
    def get_wf_output(self,path=None):
        result = self.dict_get(path)
        result = result.get('output-parameters')
        return result[0] if result else None
