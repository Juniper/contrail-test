import fixtures
from vnc_api.vnc_api import *
#from contrail_fixtures import contrail_fix_ext

#@contrail_fix_ext (ignore_verify=True, ignore_verify_on_setup=True)
class VncLibFixture(fixtures.Fixture):
    def __init__(self, domain, project, cfgm_ip, api_port, inputs , username='admin', password='contrail123' ):
        self.username= username
        self.password= password
        self.project= project
        self.domain = domain
        self.api_server_port= api_port
        self.cfgm_ip = cfgm_ip
        self.inputs= inputs
        self.logger= inputs.logger
        self.obj=None
    #end __init__

    def setUp(self):
        super(VncLibFixture, self).setUp()
        self.obj = VncApi(username=self.username, password= self.password, tenant_name= self.project,
                    api_server_host= self.cfgm_ip, api_server_port= self.api_server_port)
    #end setUp

    def cleanUp(self):
        super(VncLibFixture, self).cleanUp()

    def get_handle(self):
        return self.obj
    #end get_handle

#end VncLibFixture
