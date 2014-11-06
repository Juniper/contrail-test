# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# Copyright (c) 2010 Citrix Systems, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
A fake (in-memory) hypervisor+api.

Allows nova testing w/o a hypervisor.  This module also documents the
semantics of real hypervisor connections.

"""

from nova.openstack.common.gettextutils import _

from oslo.config import cfg
CONF = cfg.CONF
from nova.virt import fake
from nova.virt import virtapi
from nova.openstack.common import importutils
CONF.import_opt('libvirt_vif_driver', 'nova.virt.libvirt')

_FAKE_NODES = None

class FakeTestDriver(fake.FakeDriver):
    def __init__(self, virtapi, read_only=False):
        super(FakeTestDriver, self).__init__(virtapi)

        vif_class = importutils.import_class(CONF.libvirt_vif_driver)
        self.vif_driver = vif_class(None)

    def plug_vifs(self, instance, network_info):
        """Plug VIFs into networks."""
        for vif in network_info:
            self.vif_driver.plug(instance, vif)

    def unplug_vifs(self, instance, network_info):
        """Unplug VIFs from networks."""
        for vif in network_info:
            self.vif_driver.unplug(instance, vif)

    def spawn(self, context, instance, image_meta, injected_files,
              admin_password, network_info=None, block_device_info=None):
        super(FakeTestDriver, self).spawn(context, instance, image_meta,
                                    injected_files, admin_password,
                                    network_info=None, block_device_info=None)
        self.plug_vifs(instance, network_info)

    def destroy(self, instance, network_info, block_device_info=None,
                destroy_disks=True, context=None):
        super(FakeTestDriver, self).destroy(instance, network_info,
                                            block_device_info=None,
                                            destroy_disks=True, context=None)
        self.unplug_vifs(instance, network_info)
