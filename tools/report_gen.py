from __future__ import print_function
from future import standard_library
standard_library.install_aliases()
from builtins import str
import os
import re
import sys
import time
import configparser
import datetime
import logging

from fabric.api import env, run, cd, local
from fabric.operations import get, put
from fabric.contrib.files import exists
from fabric.context_managers import settings, hide
from fabric.exceptions import NetworkError
from tcutils.util import *
from tcutils.custom_filehandler import *
from common import log_orig as contrail_logging
from common.contrail_test_init import TestInputs

CORE_DIR = '/var/crashes'
logging.getLogger("paramiko").setLevel(logging.WARNING)


class ContrailReportInit(TestInputs):

    def __init__(self, input_file, report_details, logger=None):
        self.input_file = input_file
        self.build_id = None
        self.bgp_stress = False
        self.logger = logger or contrail_logging.getLogger(__name__)
        self.log_scenario = 'Sanity'
        if 'EMAIL_SUBJECT' in os.environ and os.environ['EMAIL_SUBJECT'] != '':
            self.log_scenario = os.environ.get('EMAIL_SUBJECT')
        if 'EMAIL_SUBJECT_PREFIX' in os.environ:
            self.log_scenario = '%s %s' % (os.environ.get('EMAIL_SUBJECT_PREFIX'),
                                           self.log_scenario)
        cwd = os.getcwd()
        log_path = ('%s' + '/logs/') % cwd
        for file in os.listdir(log_path):
            if file.startswith("results_summary") and file.endswith(".txt"):
                self.bgp_stress = True
        self.ts = self.get_os_env('SCRIPT_TS') or \
            datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
        self.core_location = self.ts
        self.jenkins_trigger = self.get_os_env('JENKINS_TRIGGERED')
        if self.jenkins_trigger:
            self.ts = self.ts + '_' + str(time.time())
        self.report_details_file = report_details
        self.distro = None
        super(ContrailReportInit, self).__init__(input_file, self.logger)
    # end __init__

    def setUp(self):
        (self.build_id, self.sku) = self.get_build_id()
        self.setup_detail = '%s %s~%s' % (self.get_distro(), self.build_id,
                                          self.sku)
        self.build_folder = self.build_id + '_' + self.ts
        self.html_log_link = 'http://%s/%s/%s/junit-noframes.html' % (
                             self.web_server, self.web_root, self.build_folder)
        self.log_link = 'http://%s/%s/%s/logs/' % (self.web_server, self.web_root,
                                                   self.build_folder)
        self.username = self.host_data[self.cfgm_ip]['username']
        self.password = self.host_data[self.cfgm_ip]['password']
        self.sm_pkg = self.get_os_env('SERVER_MANAGER_INSTALLER')
        self.contrail_pkg = self.get_os_env('CONTRAIL_PACKAGE')
        self.puppet_pkg = self.get_os_env('PUPPET_PKG')
        self.write_report_details()
        if self.ui_browser:
            self.upload_png_files()
    # end setUp

    def upload_png_files(self):
        self.build_folder = self.build_id + '_' + self.ts
        self.web_server_path = self.web_server_log_path + \
            '/' + self.build_folder + '/'
        cwd = os.getcwd()
        log_path = ('%s' + '/logs/') % cwd
        elem = log_path + '*.png'
        try:
            with hide('everything'):
                with settings(host_string=self.web_server,
                              user=self.web_server_user,
                              password=self.web_server_password,
                              warn_only=True, abort_on_prompts=False):
                    run('mkdir -p %s' % (self.web_server_path))
                    output = put(elem, self.web_server_path)
                    put('logs', self.web_server_path)
        except Exception as e:
            print('Error occured while uploading the png files to the Web Server ', e)
            pass
    # end upload_png_files

    def _get_stress_test_summary(self):
        cwd = os.getcwd()
        log_path = ('%s' + '/logs/') % cwd
        for file in os.listdir(log_path):
            if file.startswith("results_summary") and file.endswith(".txt"):
                file_fq_name = log_path + '/' + file
                f = open(file_fq_name, 'r')
                file_contents = f.read()
                f.close()
        return file_contents
   # end _get_stress_test_summary

    def _get_phy_topology_detail(self):
        detail = ''
        compute_nodes = [self.get_node_name(x) for x in self.compute_ips]
        bgp_nodes = [self.get_node_name(x) for x in self.bgp_ips]
        collector_nodes = [self.get_node_name(x) for x in self.collector_ips]
        cfgm_nodes = [self.get_node_name(x) for x in self.cfgm_ips]
        webui_node = [self.get_node_name(x) for x in self.webui_ips]
        ext_rtr = str(self.ext_routers).strip('[()]')
        phy_dev = []
        phy_dev = list(self.physical_routers_data.keys())
        phy_dev.append(ext_rtr)
        if self.orchestrator == 'openstack':
            openstack_nodes = [self.get_node_name(x) for x in self.openstack_ips]
        database_nodes = [self.get_node_name(x) for x in self.database_ips]

        newline = '<br/>'
        detail = newline
        detail += 'DISTRO : %s %s' % (self.get_distro(), newline)
        detail += 'SKU : %s %s' % (self.sku, newline)
        detail += 'Config Nodes : %s %s' % (cfgm_nodes, newline)
        detail += 'Control Nodes : %s %s' % (bgp_nodes, newline)
        detail += 'Compute Nodes : %s %s' % (compute_nodes, newline)
        if self.orchestrator == 'openstack':
            detail += 'Openstack Node : %s %s' % (openstack_nodes, newline)
        detail += 'WebUI Node : %s %s' % (webui_node, newline)
        detail += 'Analytics Nodes : %s %s' % (collector_nodes, newline)
        detail += 'Database Nodes : %s %s' % (database_nodes, newline)
        detail += 'Physical Devices : %s %s' % (phy_dev, newline)
        if self.ui_browser:
            detail += 'Browser : %s %s' % (self.ui_browser, newline)
        return detail
    # end _get_phy_topology_detail

    def write_report_details(self):
        phy_topology = self._get_phy_topology_detail()
        details_h = open(self.report_details_file, 'w')
        config = configparser.ConfigParser()
        config.add_section('Test')
        config.set('Test', 'Build', self.build_id)
        config.set('Test', 'Distro_Sku', self.setup_detail)
        config.set('Test', 'timestamp', self.ts)
        config.set('Test', 'Report', self.html_log_link)
        config.set('Test', 'LogsLocation', self.log_link)
        config.set('Test', 'Cores', str(self.get_cores()))

        if (self.sm_pkg or self.contrail_pkg or self.puppet_pkg):
            config.set('Test', 'sm_pkg', self.sm_pkg)
            config.set('Test', 'contrail_pkg', self.contrail_pkg)
            config.set('Test', 'puppet_pkg', self.puppet_pkg)

        if self.bgp_stress:
            bgp_stress_test_summary = self._get_stress_test_summary()
            config.set('Test', 'BGP Stress Test Summary', bgp_stress_test_summary)
        config.set('Test', 'Topology', phy_topology)
        config.set('Test', 'logScenario', self.log_scenario)
        if self.ui_browser:
            config.set('Test', 'Browser', self.ui_browser)

        debug_logs_location = ''
        if self.jenkins_trigger:
            debug_logs_location = "/cs-shared/test_runs" \
                "/%s/%s" % (self.host_data[self.cfgm_ips[0]]['name'], self.core_location)
            config.set('Test', 'CoreLocation', debug_logs_location)
        config.write(details_h)
        details_h.close()
    # end

    def get_build_id(self):
        if self.build_id:
            return self.build_id
        cmd = "rpm -q --queryformat '%{VERSION}-' contrail-test; rpm -q --queryformat '%{RELEASE}' contrail-test | awk -F'.' '{print $1}'"
        build_id = self.get_os_env("BUILD_ID")
        if not build_id:
            build_id = local(cmd, capture=True)
        build_sku = self.get_os_env("SKU")
        container = None
        if not build_sku and self.orchestrator == 'openstack':
            for openstack_ip in self.openstack_ips:
                container = self.host_data[openstack_ip].get(
                            'containers', {}).get('nova')
                if container:
                    build_sku=get_build_sku(openstack_ip,self.host_data[openstack_ip]['password'],
                                            self.host_data[openstack_ip]['username'],
                                            container=container)
                    break
        if (build_id.count('.') > 3):
            build_id=re.match(r'([0-9\.-]*)\.',build_id).group(1)
        return [build_id.rstrip('\n'), build_sku]

    def get_distro(self):
        if self.distro:
            return self.distro
        cmd = '''
            if [ -f /etc/lsb-release ]; then (cat /etc/lsb-release | grep DISTRIB_DESCRIPTION | cut -d "=" -f2 )
            else
                cat /etc/redhat-release | sed s/\(Final\)//
            fi
            '''
        try:
            self.distro = self.run_cmd_on_server(self.cfgm_ips[0], cmd, container='controller')
            self.distro = self.distro.replace(')', '')
            self.distro = self.distro.replace('(', '')
        except NetworkError as e:
            self.distro = ''
        return self.distro
    # end get_distro

    def get_cores(self):
        '''Get the list of cores in all the nodes in the test setup
        '''
        self.cores = {}
        for host in self.host_ips:
            username = self.host_data[host]['username']
            password = self.host_data[host]['password']
            core = self.get_cores_node(host, username, password)
            if core:
                self.cores.update({host: core.split()})
        # end for
        return self.cores

    def get_cores_node(self, node_ip, user, password):
        """Get the list of cores in one of the nodes in the test setup.
        """
        core = ''
        cmd = 'ls %s/core.* 2>/dev/null' % (CORE_DIR)
        output = run_cmd_on_server(cmd, node_ip, user, password)
        output1 = output.replace('%s/' %(CORE_DIR), '')
        core = '%s %s' %(core, output1)
        return core

# end

def main(arg1, arg2):
    obj = ContrailReportInit(arg1, arg2)
    obj.setUp()
    obj.get_cores()

# accept sanity_params.ini and report_details.ini
if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
