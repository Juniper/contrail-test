import project_test
from common.contrail_test_init import ContrailTestInit
from common.connections import ContrailConnections
import os
import fixtures
from test import BaseTestCase
import time
from floating_ip import *
from vn_test import *
from control_node import *
from common import isolated_creds
from tcutils.util import Singleton

from common import log_orig as contrail_logging


class PublicVn():
    __metaclass__ = Singleton

    def __init__(self, connections,
                       isolated_creds_obj=None,
                       public_vn=None,
                       public_tenant=None,
                       logger = None,
                       mx_rt = None,
                       fip_pool_name=None,
                       api_option='neutron',
                       ipam_fq_name=None):

        self.isolated_creds = isolated_creds_obj
        self.connections = connections
        self.inputs = connections.inputs
        self.logger = logger or contrail_logging.getLogger(__name__)
        self.public_vn = public_vn or self.inputs.public_vn
        self.public_tenant = public_tenant or self.inputs.admin_tenant
        self.fip_pool_name = fip_pool_name or self.inputs.fip_pool_name
        self.api_option = api_option
        self.ipam_fq_name = ipam_fq_name
        self.setUp()
        self.create_public_vn(mx_rt)
        self.create_floatingip_pool()
        self.configure_control_nodes()

    def setUp(self):
        if self.isolated_creds:
            self.project = self.isolated_creds.create_tenant(self.public_tenant)
            self.inputs = self.isolated_creds.get_inputs(self.project)
            self.connections = self.isolated_creds.get_connections(self.inputs)
            if self.isolated_creds.__class__.__name__ == 'AdminIsolatedCreds':
                # If AdminIsolatedCreds, one could add user to tenant
                # Else, it is assumed that the administrator has taken 
                # care 
                self.isolated_creds.create_and_attach_user_to_tenant(
                    self.project,
                    self.isolated_creds.username,
                    self.isolated_creds.password)
        else:
            self.project = ProjectFixture(connections=self.connections,
                                          auth=self.connections.auth,
                                          project_name=self.public_tenant,
                                          )
            self.project.setUp()
        self.project.set_sec_group_for_allow_all(\
                 self.public_tenant, 'default')

    # end setUp

    def create_public_vn(self,mx_rt = None):
        if (('MX_GW_TEST' in os.environ) and (
                os.environ.get('MX_GW_TEST') == '1')):
            fip_subnets = [self.inputs.fip_pool]
            if not mx_rt:
                mx_rt = self.inputs.mx_rt
            self.public_vn_fixture = VNFixture(
                    project_name=self.project.project_name,
                    connections=self.connections,
                    vn_name=self.public_vn,
                    inputs=self.inputs,
                    subnets=fip_subnets,
                    router_asn=self.inputs.router_asn,
                    rt_number=mx_rt,
                    router_external=True,
                    option=self.api_option,
                    ipam_fq_name=self.ipam_fq_name)
            self.public_vn_fixture.setUp()
            assert self.public_vn_fixture.verify_on_setup()
            self.logger.info('Created public VN:%s' % self.public_vn)
    # end createPublicVN

    def create_floatingip_pool(self):
        if (('MX_GW_TEST' in os.environ) and (
                os.environ.get('MX_GW_TEST') == '1')):
            fip_subnets = [self.inputs.fip_pool]
            self.fip_fixture = FloatingIPFixture(
                   project_name=self.public_tenant,
                   inputs=self.inputs,
                   connections=self.connections,
                   pool_name=self.fip_pool_name,
                   vn_id=self.public_vn_fixture.vn_id,
                   option=self.api_option,
                   vn_name=self.public_vn)
            self.fip_fixture.setUp()
            assert self.fip_fixture.verify_on_setup()
            self.logger.info('Created FIP Pool:%s under Project:%s' %
                                (self.fip_fixture.pool_name,
                                 self.project.project_name))
    # end create_floatingip_pool

    def configure_control_nodes(self):

        # Configuring all control nodes here
        if (('MX_GW_TEST' in os.environ) and (
                os.environ.get('MX_GW_TEST') == '1')):
            router_name = self.inputs.ext_routers[0][0]
            router_ip = self.inputs.ext_routers[0][1]
            for entry in self.inputs.bgp_ips:
                hostname = self.inputs.host_data[entry]['name']
                entry_control_ip = self.inputs.host_data[
                    entry]['host_control_ip']
                cn_fixture1 = CNFixture(
                        connections=self.connections,
                        router_name=hostname,
                        router_ip=entry_control_ip,
                        router_type='contrail',
                        inputs=self.inputs)
                cn_fixture1.setUp()
            cn_fixturemx = CNFixture(
                    connections=self.connections,
                    router_name=router_name,
                    router_ip=router_ip,
                    router_type='mx',
                    inputs=self.inputs,
                    router_asn=self.inputs.router_asn)
            cn_fixturemx.setUp()
            assert cn_fixturemx.verify_on_setup()
            # TODO Configure MX. Doing Manually For Now

