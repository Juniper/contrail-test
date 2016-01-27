import time

import paramiko
import fixtures
from fabric.api import run, hide, settings

from vn_test import VNFixture
from vm_test import VMFixture
from policy_test import PolicyFixture
from common.policy.config import ConfigPolicy
from common.connections import ContrailConnections
from security_group import SecurityGroupFixture


class ConfigSecGroup(ConfigPolicy):

    def config_sec_group(self, name, secgrpid=None, entries=None):
        secgrp_fixture = self.useFixture(SecurityGroupFixture(self.inputs,
                                                              self.connections, self.inputs.domain_name, self.inputs.project_name,
                                                              secgrp_name=name, uuid=secgrpid, secgrp_entries=entries))
        result, msg = secgrp_fixture.verify_on_setup()
        assert result, msg
        return secgrp_fixture

    def delete_sec_group(self, secgrp_fix):
        secgrp_fix.cleanUp()
        self.remove_from_cleanups(secgrp_fix)

    def remove_from_cleanups(self, fix):
        for cleanup in self._cleanups:
            if fix.cleanUp in cleanup:
                self._cleanups.remove(cleanup)
                break
