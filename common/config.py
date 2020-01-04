# Copyright 2012 OpenStack Foundation
# All Rights Reserved.
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

from __future__ import print_function

import logging as std_logging
import os

from oslo.config import cfg

from common import log as logging


def register_opt_group(conf, opt_group, options):
    conf.register_group(opt_group)
    for opt in options:
        conf.register_opt(opt, group=opt_group.name)


def register_opts():
    pass


# this should never be called outside of this class
class TestConfigPrivate(object):
    """Provides OpenStack configuration information."""

#    DEFAULT_CONFIG_DIR = os.path.join(
#        os.path.abspath(os.path.dirname(os.path.dirname(__file__))),
#        "etc")
    DEFAULT_CONFIG_DIR = '.'

    DEFAULT_CONFIG_FILE = "logging.conf"

    def _set_attrs(self):
        pass

    def __init__(self, parse_conf=True):
        """Initialize a configuration from a conf directory and conf file."""
        super(TestConfigPrivate, self).__init__()
        config_files = []
        failsafe_path = self.DEFAULT_CONFIG_FILE

        # Environment variables override defaults...
        conf_dir = os.environ.get('TEST_CONFIG_DIR',
                                  self.DEFAULT_CONFIG_DIR)
        conf_file = os.environ.get('TEST_CONFIG_FILE', self.DEFAULT_CONFIG_FILE)

        path = os.path.join(conf_dir, conf_file)

        if not os.path.isfile(path):
            path = failsafe_path

        # only parse the config file if we expect one to exist. This is needed
        # to remove an issue with the config file up to date checker.
        if parse_conf:
            config_files.append(path)

        cfg.CONF([], project='contrailtest', default_config_files=config_files)
        logging.setup('contrailtest')
        LOG = logging.getLogger('contrailtest')
        LOG.info("Using contrailtest config file %s" % path)
        register_opts()
        self._set_attrs()
        if parse_conf:
            cfg.CONF.log_opt_values(LOG, std_logging.DEBUG)


class TestConfigProxy(object):
    _config = None

    _extra_log_defaults = [
        'keystoneclient.session=WARN',
        'paramiko.transport=WARN',
        'requests.packages.urllib3.connectionpool=WARN',
        'urllib3.connectionpool=WARN',
    ]

    def _fix_log_levels(self):
        """Tweak the oslo log defaults."""
        for opt in logging.log_opts:
            if opt.dest == 'default_log_levels':
                opt.default.extend(self._extra_log_defaults)

    def __getattr__(self, attr):
        if not self._config:
            self._fix_log_levels()
            self._config = TestConfigPrivate()

        return getattr(self._config, attr)


CONF = TestConfigProxy()
