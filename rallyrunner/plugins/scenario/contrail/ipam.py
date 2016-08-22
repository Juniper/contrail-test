from rally import consts
from rally.task import validation
from rally.task import types
from rally.task import atomic
from rally.common import log as logging
from rally import exceptions
from rally.task import scenario
from vnc import ContrailScenario
from vnc_api.vnc_api import *


LOG = logging.getLogger(__name__)

class ContrailIpam(ContrailScenario):
    """IPAM scenarios"""

    @atomic.action_timer("list_ipams")
    def _list_ipams(self):
        """Sample of usage clients - list flavors

        You can use self.context, self.admin_clients and self.clients which are
        initialized on scenario instance creation"""
        self.vnc.network_ipams_list()

    @scenario.configure()
    def list_ipams(self):
        """List ipams."""
        self._list_ipams()

    @scenario.configure()
    def create_and_list_ipams(self, do_delete=True):
        ipam = self._create_ipam()
        self.list_ipams()
        if do_delete:
            self.vnc.network_ipam_delete(id=ipam)

    @scenario.configure()
    def create_and_delete_ipams(self):
        ipam = self._create_ipam()
        self._delete_ipam(ipam)


    @atomic.action_timer("contrail.create_ipam")
    def _create_ipam(self):
        ipam_name = self.generate_random_name()
        ipam_def = NetworkIpam(name=ipam_name,
                               parent_type='project',
                               network_ipam_mgmt=IpamType('dhcp'))
        return self.vnc.network_ipam_create(ipam_def)

    @atomic.action_timer("contrail.delete_ipam")
    def _delete_ipam(self, id):
        return self.vnc.network_ipam_delete(id=id)
