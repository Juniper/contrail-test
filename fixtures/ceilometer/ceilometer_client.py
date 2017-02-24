import os
import openstack
from common.openstack_libs import ceilo_client as client

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

class CeilometerClient(object):
    '''
       Wrapper around ceilometer client library
       Optional params:
       :param auth_h: OpenstackAuth object
       :param inputs: ContrailTestInit object which has test env details
       :param logger: logger object
       :param auth_url: Identity service endpoint for authorization.
       :param username: Username for authentication.
       :param password: Password for authentication.
       :param project_name: Tenant name for tenant scoping.
       :param region_name: Region name of the endpoints.
       :param certfile: Public certificate file
       :param keyfile: Private Key file
       :param cacert: CA certificate file
       :param verify: Enable or Disable ssl cert verification
    '''
    def __init__(self, auth_h=None, **kwargs):
        if not auth_h:
            auth_h = self.get_auth_h(**kwargs)
        self.auth_h = auth_h

    def get_auth_h(self, **kwargs):
        return openstack.OpenstackAuth(**kwargs)

    def get_cclient(self):
        ceilometer_url = self.auth_h.get_endpoint('metering')
        auth_token = self.auth_h.get_token()
        self.cclient = client.Client(VERSION, endpoint=ceilometer_url, token=auth_token, insecure=True)
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
