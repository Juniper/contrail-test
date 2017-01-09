class Openstack(object):

  def __init__(self,auth_url,username,password,tenant,auth_token=None):

     print "User:",auth_url,username,password,tenant,auth_token
     self.keystone_client = kclient.Client(username=username,
                                   password=password,
                                   tenant_name=tenant,
                                   auth_url=auth_url)

     if not auth_token:
       auth_token = self.keystone_client.auth_token

     self.nova_client = nova_client.Client('2',  auth_url=auth_url,
                                       username=username,
                                       api_key=password,
                                       project_id=tenant,
                                       auth_token=auth_token,
                                       insecure=True)
     ''' Get neutron client handle '''
     self.neutron_client = neutron_client.Client('2.0',
                                             auth_url=auth_url,
                                             username=username,
                                             password=password,
                                             tenant_name=tenant,
                                             insecure=True)


