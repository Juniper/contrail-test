from rally import consts
from rally.task import validation
from rally.task import types
from rally.task import atomic
from rally.common import log as logging
from rally import exceptions
from rally.task import scenario
from vnc_api.vnc_api import VncApi


class ContrailScenario(scenario.Scenario):
    def __init__(self, context):
        scenario.Scenario.__init__(self, context)
        self.vnc = VncApi(api_server_host='10.204.217.88',
                          username='admin',
                          password='secret123',
                          tenant_name='admin')

