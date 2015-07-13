import os
from common.openstack_libs import ks_auth_identity_v2 as v2
from common.openstack_libs import ks_session as session
from common.openstack_libs import ceilo_client as client
from common.structure import DynamicArgs

VERSION = 2

def make_query(user_id=None, tenant_id=None, resource_id=None,
               user_ids=None, tenant_ids=None, resource_ids=None):
    """Returns query built from given parameters.
    This query can be then used for querying resources, meters and
    statistics.
    :Parameters:
      - `user_id`: user_id, has a priority over list of ids
      - `tenant_id`: tenant_id, has a priority over list of ids
      - `resource_id`: resource_id, has a priority over list of ids
      - `user_ids`: list of user_ids
      - `tenant_ids`: list of tenant_ids
      - `resource_ids`: list of resource_ids
    """
    user_ids = user_ids or []
    tenant_ids = tenant_ids or []
    resource_ids = resource_ids or []

    query = []
    if user_id:
        user_ids = [user_id]
    for u_id in user_ids:
        query.append({"field": "user_id", "op": "eq", "value": u_id})

    if tenant_id:
        tenant_ids = [tenant_id]
    for t_id in tenant_ids:
        query.append({"field": "project_id", "op": "eq", "value": t_id})

    if resource_id:
        resource_ids = [resource_id]
    for r_id in resource_ids:
        query.append({"field": "resource_id", "op": "eq", "value": r_id})

    return query


class AuthToken(DynamicArgs):
    """Returns auth_token
    :Parameters:
      - `username`: user_id
      - `tenant_id`: tenant_id
      - `password`: password
      - `auth_url`: auth url
    """

    _fields = ['auth_url', 'username', 'password', 'tenant_id', 'insecure']
                    
    def get_token(self):
        '''Return auth token'''
        auth=v2.Password(auth_url=self.auth_url
                        ,username=self.username, 
                        password=self.password, 
                        tenant_id=self.tenant_id)

        sess = session.Session(auth=auth,verify=False)         
        self.token = auth.get_token(sess)
        return self.token

class CeilometerClient(DynamicArgs):
    """Returns ceilometer clent  
    :Parameters:
      - `username`: user_id
      - `tenant_id`: tenant_id
      - `password`: password
      - `auth_url`: auth url
      - `ceilometer_url`: ceilometer url
    """
    _fields = ['auth_url', 'username', 'password', 'tenant_name',
                'ceilometer_url']

    def get_cclient(self):

        #TO DO - working with auth token
        #auth_client = AuthToken(self.auth_url,
        #                        username = self.username,
        #                        password = self.password,
        #                        tenant_id = self.tenant_name)
        #token = auth_client.get_token()
        self.cclient = client.get_client(VERSION, os_username = self.username,
                                        os_password = self.password,
                                        os_auth_url = self.auth_url,
                                        os_tenant_name = self.tenant_name,
                                        insecure = True)
        return self.cclient

class Meter:
    """Represents one Ceilometer meter."""

    def __init__(self, meter):
        self.meter = meter

    @property
    def user_id(self):
        return self.meter.user_id
    
    @property
    def name(self):
        return self.meter.name
    
    @property
    def resource_id(self):
        return self.meter.resource_id
    
    @property
    def source(self):
        return self.meter.source
    
    @property
    def meter_id(self):
        return self.meter.meter_id
    
    @property
    def project_id(self):
        return self.meter.project_id

    @property
    def type(self):
        return self.meter.type
    
    @property
    def unit(self):
        return self.meter.unit
    
class Resource:

    """Represents one Ceilometer resource."""
    
    def __init__(self, resource,ceilometer_usage=None):
        self.resource = resource

    @property
    def user_id(self):
        return self.resource.user_id

    @property
    def project_id(self):
        return self.resource.project_id

    @property
    def resource_id(self):
        return self.resource.resource_id

    @property
    def source(self):
        return self.resource.source

class Sample:
    """Represents one Ceilometer sample."""

    def __init__(self,sample):
        self.sample = sample

    @property
    def user_id(self):
        return self.sample.user_id

    @property
    def project_id(self):
        return self.sample.project_id

    @property
    def resource_id(self):
        return self.sample.resource_id
    
    @property
    def counter_unit(self):
        return self.sample.counter_unit
    
    @property
    def resource_metadata(self):
        return self.sample.resource_metadata
    
    @property
    def counter_volume(self):
        return self.sample.counter_volume
    
    @property
    def counter_name(self):
        return self.sample.counter_name
    
    @property
    def counter_type(self):
        return self.sample.counter_type

class Statistic:
    """Represents one Ceilometer statistic."""
    def __init__(self,stat):
        self.stat = stat

def resource_list(cclient, query=None, ceilometer_usage_object=None):
    """List the resources."""
    resources = cclient.resources.list(q=query)
    return [Resource(r, ceilometer_usage_object) for r in resources]


def sample_list(cclient, meter_name, query=None, limit=None):
    """List the samples for this meters."""
    samples = cclient.samples.list(meter_name=meter_name,
                                       q=query, limit=limit)
    return [Sample(s) for s in samples]


def meter_list(cclient, query=None):
    """List the user's meters."""
    meters = cclient.meters.list(query)
    return [Meter(m) for m in meters]


def statistic_list(cclient, meter_name, query=None, period=None):
    """List of statistics."""
    statistics = cclient.\
        statistics.list(meter_name=meter_name, q=query, period=period)
    return [Statistic(s) for s in statistics]
   
    
def main():
    auth_url = os.getenv('OS_AUTH_URL') or \
                'http://10.204.216.7:5000/v2.0'
    username = os.getenv('OS_USERNAME') or \
                'admin'
    password = os.getenv('OS_PASSWORD') or \
                'contrail123'
    tenant_name = os.getenv('OS_TENANT_NAME') or \
                'admin'
    c_url = os.getenv('OS_TELEMETRY_URL') or \
                'http://10.204.216.7:8777/'
    cclient = CeilometerClient(auth_url, username,
                                 password,
                                 tenant_name,
                                 c_url,insecure = True) 
    cclient = cclient.get_cclient()
    #q = make_query(user_id='ffe9ce8cac3a4d3088bff11d34f7c09b', tenant_id='a4faf2a1d086459b89ec1b776ddf42dd')
    #q = make_query(tenant_id='a4faf2a1d086459b89ec1b776ddf42dd')
    q = make_query(tenant_id='3c07b22cfabb4ba8b9387749250e3ed8')
    #abc = statistic_list(cclient,'cpu_util',query=q,period = '5')
    #abc = statistic_list(cclient,'cpu_util',query=q)
    #abc = statistic_list(cclient,'cpu_util')
    #abc = statistic_list(cclient,'ip.floating.receive.packets',period='5')
    #abc = statistic_list(cclient,'ip.floating.receive.bytes')
    abc = resource_list(cclient,query=q)
    #abc = sample_list(cclient,'ip.floating')
    print q
    print abc

if __name__ == "__main__":
    main()           
