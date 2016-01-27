import re
from tcutils.verification_util import *

class CsSvcInstance (Result):

    def fqname(self):
        return self.xpath('name')

    def get_vrouter_name(self, ha_state):
        vrouter = 'none'
        for vm in self.xpath('vm_list', 'list') or []:
            if ha_state in vm['ha']:
                vrouter = vm['vr_name']
                break
        return None if vrouter.lower() == 'none' else vrouter

    def active_vrouter(self):
        return self.get_vrouter_name('active')

    def standby_vrouter(self):
        return self.get_vrouter_name('standby')
 
    def is_launched(self):
        return self.xpath('si_state') == 'active'

