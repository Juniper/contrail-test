import fixtures
from contrail_fixtures import *
import sys
import pdb
import json
import string
import textwrap
import tempfile
import os
import re
import fabric
import ConfigParser
import argparse
import sys
from datetime import datetime as dt
from fabric.api import settings, run
from fabric.api import hosts, env, task
from fabric.api import local, put, get
from fabric.tasks import execute
from os.path import expanduser
import imp
import fabfile.tasks.verify as verify
from fabric.state import connections
#from fabfile.utils.host import verify_sshd
from time import sleep



REIMAGE_WAIT=360
SERVER_RETRY_TIME=1000
PROVISION_TIME = 1200


class SmgrFixture(fixtures.Fixture):

    ''' Fixture to bring up a vns cluster using server manager .

    '''

    def __init__(self, inputs, testbed_py="./testbed.py", smgr_config_ini="./smgr_input.ini", test_local=False):
        self.testbed_py = testbed_py
        self.testbed = self.get_testbed()
        self.smgr_config_ini = smgr_config_ini
        self.test_local = test_local
        self.params = self.read_ini_file(smgr_config_ini)
        self.svrmgr = self.params['svrmgr']
        self.inputs = inputs
        self.logger = self.inputs.logger
    # end __init__

    def svrmgr_add_all(self):
        self.create_json()
        self.add_cluster()
        self.add_image()
        self.add_pkg()
        self.add_server()
    # end svrmgr_add_all


    def create_json(self):
        self.modify_server_json()
        self.modify_cluster_json()
    # end create_json

    def modify_server_json(self):
        params=self.params
        if not params:
            return None
        if not params.has_key('server_file'):
            return None
        server_file = params['server_file']

        timestamp = dt.now().strftime("%Y_%m_%d_%H_%M_%S")
        local('cp %s %s.org.%s' %(server_file, server_file, timestamp))

        in_file = open( server_file, 'r' )
        in_data = in_file.read()
        server_dict = json.loads(in_data)

        self.update_roles_from_testbed_py(server_dict)
        self.update_bond_from_testbed_py(server_dict)
        self.update_multi_if_from_testbed_py(server_dict)

        out_file = open(server_file, 'w')
        out_data = json.dumps(server_dict, indent=4)
        out_file.write(out_data)
        out_file.close()

        return server_dict
    # end modify_server_json

    def update_roles_from_testbed_py(self, server_dict):
        ''' This will update the dict corresponding to server.json with 
            the roles mentioned in testbed.roledefs. It will seamlessly integrate
            Server Manager with legacy method where a user has to edit testbed.py only. '''              

        testbed = self.testbed
        if not testbed.env.has_key('roledefs'):
            return server_dict
        for  node in server_dict['server']:
          roles = []
          for key in testbed.env.roledefs:
            if key == 'all' or key == 'build' :
              continue
            for  host_string in testbed.env.roledefs[key]:
              ip = getIp(host_string)
              if node['ip_address'] == ip:
                if key == 'cfgm':
                    roles.append("config")
                else:
                    roles.append(key)
          if not len(roles):
            node['roles'] = [ "compute" ]
          else:
            node['roles'] =  roles

        for  node in server_dict['server']:
           node['cluster_id'] =  self.get_pref_cluster_id()

        return server_dict
    # end update_roles_from_testbed_py

    def update_bond_from_testbed_py(self, server_dict):
        testbed = self.testbed
        if 'control_data' in dir(testbed):

          for  node in server_dict['server']:
            for  key in testbed.bond:
              ip = getIp(key)
              if node['ip_address'] == ip:
                  node['parameters']['setup_interface'] = "Yes"

                  name = testbed.bond[key]['name']
                  mode = testbed.bond[key]['mode']
                  member = testbed.bond[key]['member']
                  option = {}
                  option['miimon'] = '100'
                  option['mode'] = mode
                  option['xmit_hash_policy'] = 'layer3+4'

                  node['bond']={}
                  node['bond'][name]={}
                  node['bond'][name]['bond_options'] = "%s"%option
                  node['bond'][name]['member'] = "%s"%member
        return server_dict
    #End update_bond_from_testbed_py(server_dict):

    def update_multi_if_from_testbed_py(self, server_dict):

        testbed = self.testbed
        if 'control_data' in dir(testbed):

          for  node in server_dict['server']:
            for  key in testbed.control_data:
              ip = getIp(key)
              if node['ip_address'] == ip:
                  node['parameters']['setup_interface'] = "Yes"

                  ip = testbed.control_data[key]['ip']
                  gw = testbed.control_data[key]['gw']
                  device = testbed.control_data[key]['device']

                  node['control_data_network']={}
                  node['control_data_network'][device] = {}
                  node['control_data_network'][device]['ip_address'] = ip
                  node['control_data_network'][device]['gateway'] = gw

        return server_dict

    #End update_multi_if_from_testbed_py(server_dict):


    def get_image_id(self) :
        params=self.params
        image_file = params['image_file']

        image_file = open( image_file, 'r' )
        image_data = image_file.read()
        image_json = json.loads(image_data)
        image_id = image_json['image'][0]['id']
        image_file.close()
        return image_id
    # end get_image_id()

    def get_pkg_id(self) :
        params=self.params
        pkg_file = params['pkg_file']

        pkg_file = open( pkg_file, 'r' )
        pkg_data = pkg_file.read()
        pkg_json = json.loads(pkg_data)
        pkg_id = pkg_json['image'][0]['id']
        pkg_file.close()
        return pkg_id
    # end get_pkg_id()

    def get_cluster_id(self) :
        cluster_id = None
        params=self.params
        cluster_file = params['cluster_file']

        cluster_file = open( cluster_file, 'r' )
        cluster_data = cluster_file.read()
        cluster_json = json.loads(cluster_data)
        cluster_id = cluster_json['cluster'][0]['id']
        if  params.has_key('cluster_id'):
            cluster_id = params['cluster_id']
        cluster_file.close()
        return cluster_id
    # end get_cluster_id()


    def add_cluster(self):
        cluster_file = None
        params=self.params
        if  params.has_key('cluster_file'):
            cluster_file = params['cluster_file']

        cluster_id = self.get_pref_cluster_id()
        if not cluster_file:
            cluster_dict = self.get_cluster_with_cluster_id_from_db()
            if not len(cluster_dict['cluster']):
                cluster_dict = new_cluster()
            else:
                cluster_dict = {
                              "cluster" : [
                                  {
                                      "cluster_id" : "",
                                      "parameters" : {
    
                                          }
                                  }
                              ]
                           }

            cluster_dict['cluster'][0]['id'] = cluster_id
            self.modify_cluster_from_testbed_py(cluster_dict)
            temp_dir= expanduser("~")
            cluster_file = '%s/cluster.json' %temp_dir
            local('touch %s' %cluster_file)
            out_file = open(cluster_file, 'w')
            out_data = json.dumps(cluster_dict, indent=4)

            out_file.write(out_data)
            out_file.close()
        else :
            timestamp = dt.now().strftime("%Y_%m_%d_%H_%M_%S")
            local('cp %s %s.org.%s' %(cluster_file, cluster_file, timestamp))
            local("sed -i 's/\"id\"\s*:\s*\".*\"/\"id\":\"%s\"/'  %s" %(cluster_id,cluster_file))

        if self.test_local:
            local('server-manager add  cluster -f %s' %(cluster_file))
        else:
            svrmgr = self.svrmgr
            with settings(host_string=svrmgr, warn_only=True):
                file_name = os.path.basename(cluster_file)
                temp_dir= tempfile.mkdtemp()
                run('mkdir -p %s' % temp_dir)
                put(cluster_file, '%s/%s' % (temp_dir, file_name))

                run('server-manager add  cluster -f %s/%s' %(temp_dir, file_name) )
                run('server-manager show all | python -m json.tool')
    # end add_cluster()

    def add_server(self):
        self.add_server_using_json()
        self.update_server_in_db_with_testbed_py()
    #end add_server

    def add_image(self):
        params=self.params
        if not params:
            return None
        if not params.has_key('image_file'):
            return None
        image_file = params['image_file']

        if self.test_local:
            local('server-manager add  image -f %s' %(image_file))
            local('server-manager show all')
        else:
            svrmgr = self.svrmgr
            with settings(host_string=svrmgr, warn_only=True):
                file_name = os.path.basename(image_file)
                temp_dir = tempfile.mkdtemp()
                run('mkdir -p %s' % temp_dir)
                put(image_file, '%s/%s' % (temp_dir, file_name))

                run('server-manager add  image -f %s/%s' %(temp_dir, file_name) )
                run('server-manager show all | python -m json.tool')
    #end add_image

    def add_pkg(self):
        params=self.params
        if not params:
            return None
        if not params.has_key('pkg_file'):
            return None
        pkg_file = params['pkg_file']

        if self.test_local:
            local('server-manager add  image -f %s' %(pkg_file))
            local('server-manager show image ')
        else:
            svrmgr = self.svrmgr
            with  settings(host_string=svrmgr, warn_only=True):
                file_name = os.path.basename(pkg_file)
                temp_dir= tempfile.mkdtemp()
                run('mkdir -p %s' % temp_dir)
                put(pkg_file, '%s/%s' % (temp_dir, file_name))

                run('server-manager add  image -f %s/%s' %(temp_dir, file_name) )
                run('server-manager show all | python -m json.tool')
    #end add_pkg

    def add_server_using_json(self):
        params=self.params
        if not params:
            return None

        if not params.has_key('server_file'):
            return None
        server_file = params['server_file']

        if self.test_local:
            local('server-manager add  server -f %s' %(server_file))
            local('server-manager show server')
        else:
            svrmgr = self.svrmgr
            with  settings(host_string=svrmgr, warn_only=True):
                file_name = os.path.basename(server_file)
                temp_dir= tempfile.mkdtemp()
                run('mkdir -p %s' % temp_dir)
                put(server_file, '%s/%s' % (temp_dir, file_name))
                run('server-manager add  server -f %s/%s' %(temp_dir, file_name) )
                run('server-manager show all | python -m json.tool')
    #end add_server_using_json

    def modify_cluster_json(self):
        params=self.params
        if not params:
            return None
        if not params.has_key('cluster_file'):
            return None
        cluster_file = params['cluster_file']

        timestamp = dt.now().strftime("%Y_%m_%d_%H_%M_%S")
        local('cp %s %s.org.%s' %(cluster_file, cluster_file, timestamp))

        in_file = open( cluster_file, 'r' )
        in_data = in_file.read()
        cluster_dict = json.loads(in_data)

        self.modify_cluster_from_testbed_py(cluster_dict)

        out_file = open(cluster_file, 'w')
        out_data = json.dumps(cluster_dict, indent=4)
        out_file.write(out_data)
        out_file.close()
    #end modify_cluster_json


    def modify_cluster_from_testbed_py(self, cluster_dict):
        testbed = self.testbed
        if testbed.env.has_key('mail_to'):
            cluster_dict['cluster'][0]['email'] = testbed.env.mail_to
        if testbed.env.has_key('encap_priority'):
            cluster_dict['cluster'][0]['parameters']['encapsulation_priority'] = testbed.env.encap_priority
        if 'multi_tenancy' in dir(testbed):
            if testbed.multi_tenancy == True :
                cluster_dict['cluster'][0]['parameters']['multi_tenancy'] = "True"
            elif testbed.multi_tenancy == False :
                cluster_dict['cluster'][0]['parameters']['multi_tenancy'] = "False"
            else:
                cluster_dict['cluster'][0]['parameters']['multi_tenancy'] = "False"
        if 'os_username' in dir(testbed):
            cluster_dict['cluster'][0]['parameters']['keystone_username'] = testbed.os_username
        if 'os_password' in dir(testbed):
            cluster_dict['cluster'][0]['parameters']['keystone_password'] = testbed.os_password
        if 'os_tenant_name' in dir(testbed):
            cluster_dict['cluster'][0]['parameters']['keystone_tenant'] = testbed.os_tenant_name
        if 'router_asn' in dir(testbed):
            cluster_dict['cluster'][0]['parameters']['router_asn'] = testbed.router_asn
    #end modify_cluster_from_testbed_py


    def new_cluster(self):
        params=self.params
        cluster_id = params['cluster']
        cluster_dict = {
                      "cluster" : [
                          {
                              "id" : cluster_id,
                              "parameters" : {
                                  "router_asn": "64512",
                                  "database_dir": "/home/cassandra",
                                  "db_initial_token": "",
                                  "openstack_mgmt_ip": "",
                                  "use_certs": "False",
                                  "multi_tenancy": "False",
                                  "encap_priority": "'MPLSoUDP','MPLSoGRE','VXLAN'",
                                  "service_token": "contrail123",
                                  "keystone_user": "admin",
                                  "keystone_password": "contrail123",
                                  "keystone_tenant": "admin",
                                  "openstack_password": "contrail123",
                                  "analytics_data_ttl": "168",
                                  "subnet_mask": "255.255.255.0",
                                  "gateway": "1.1.1.254",
                                  "password": "c0ntrail123",
                                  "domain": "contrail.juniper.net",
                                  "haproxy": "disable"
                                  }
                              }
                          ]
                      }
        return cluster_dict
    # End new_cluster()

    def read_ini_file(self, config_ini):
        try:
            config = ConfigParser.SafeConfigParser()
            config.read([config_ini])
            smgr_config = dict(config.items("SERVER-MANAGER"))
            return smgr_config
        except:
            sys.exit("Error reading config file %s" %config_ini)

        return smgr_config
    #end read_ini_file


    def get_server_with_cluster_id_from_db(self):
        cluster_id = self.get_pref_cluster_id()

        temp_dir= expanduser("~")
        file_name = '%s/server_with_cluster_id_from_db.json' %(temp_dir)

        if self.test_local:
            local('server-manager show server --cluster_id %s --detail \
                         | tr -d "\n" \
                         | sed "s/[^{]*//" \
                         > %s' %(cluster_id, file_name))

        else:
            svrmgr = self.params
            with  settings(host_string=svrmgr, warn_only=True):
                temp_dir= tempfile.mkdtemp()
                run('mkdir -p %s' % temp_dir)
                file_name = '%s/server_list.json' %(temp_dir)

                run('server-manager show  server --cluster_id %s --detail \
                     | tr -d "\n" \
                     | sed \'s/[^{]*//\'  \
                     | python -m json.tool  \
                     > %s' %(cluster_id, file_name) )

                local('mkdir -p %s' % temp_dir)
                get( file_name, file_name )

        in_file = open( file_name, 'r' )
        in_data = in_file.read()
        server_dict = json.loads(in_data)
        return server_dict
    #end get_server_with_cluster_id_from_db

    def get_cluster_with_cluster_id_from_db(self):
        params=self.params
        cluster_id = params['cluster_id']

        cluster_dict = {"cluster": []}

        temp_dir= expanduser("~")

        file_name = '%s/cluster.json' %(temp_dir)

        if self.test_local:
            local('server-manager show  cluster --cluster_id %s --detail \
                         | tr -d "\n" \
                         | sed "s/[^{]*//" \
                         > %s' %(cluster_id, file_name))
        else:
            svrmgr =  self.svrmgr
            with  settings(host_string=svrmgr, warn_only=True):
                temp_dir= tempfile.mkdtemp()
                run('mkdir -p %s' % temp_dir)
                file_name = '%s/cluster.json' %(temp_dir)
                run('server-manager show  cluster --cluster_id %s --detail\
                     | tr -d "\n" \
                     | sed \'s/[^{]*//\'  \
                     | python -m json.tool  \
                     > %s' %(cluster_id, file_name) )
                local('mkdir -p %s' % temp_dir)
                get( file_name, file_name )

        in_file = open( file_name, 'r' )
        in_data = in_file.read()

        cluster_dict = json.loads(in_data)
        return cluster_dict
    #end get_cluster_with_cluster_id_from_db(self):


    def get_server_with_ip_from_db(self, ip=None):
        params=self.params

        server_dict={}
        if not ip:
            print "Please provide an ip as input arg"
            return ip

        temp_dir= expanduser("~")

        file_name = '%s/server.json' %(temp_dir)

        if self.test_local:
            local('server-manager show  server --ip %s --detail \
                         | tr -d "\n" \
                         | sed "s/[^{]*//" \
                         > %s' %(ip, file_name))
        else:
            svrmgr = self.svrmgr
            with  settings(host_string=svrmgr, warn_only=True):
                temp_dir= tempfile.mkdtemp()
                run('mkdir -p %s' % temp_dir)
                file_name = '%s/server.json' %(temp_dir)
                run('server-manager show  server --ip %s --detail \
                     | tr -d "\n" \
                     | sed \'s/[^{]*//\'  \
                     | python -m json.tool  \
                     > %s' %(ip, file_name) )
                local('mkdir -p %s' % temp_dir)
                get( file_name, file_name )

        in_file = open( file_name, 'r' )
        in_data = in_file.read()
        server_dict = json.loads(in_data)
        return server_dict
    #end get_server_with_ip_from_db(self, ip=None):

    def get_host_roles_from_testbed_py(self):
        testbed = self.testbed
        node = {}
        if not testbed.env.has_key('roledefs'):
            return node
        for key in testbed.env.roledefs:
            if key == 'all' or key == 'build':
                continue
            for  host_string in testbed.env.roledefs[key]:
                ip = getIp(host_string)
                if not node.has_key(ip):
                    node[ip] = []
                if key == 'cfgm':
                    node[ip].append('config')
                else:
                    node[ip].append(key)
        return node
    # end get_host_roles_from_testbed_py

    def update_server_in_db_with_testbed_py(self):
        cluster_id = self.get_pref_cluster_id()
        node = self.get_host_roles_from_testbed_py()
        if not node:
            return
        u_server_dict = {}
        u_server_dict['server'] = []
        for key in node:
            server_dict = {}
            server_dict = self.get_server_with_ip_from_db(key)
            if not server_dict or not server_dict['server']:
                self.logger.error("Server with ip %s not present in Server Manager" % key)
                continue
            server_id = server_dict['server'][0]['id']
            u_server = {}
            u_server['id'] = server_id
            u_server['cluster_id'] = cluster_id
            u_server['roles'] = node[key]
            u_server_dict['server'].append(u_server)

        temp_dir= expanduser("~")
        server_file = '%s/server.json' %temp_dir
        local('touch %s' %server_file)
        out_file = open(server_file, 'w')
        out_data = json.dumps(u_server_dict, indent=4)
        out_file.write(out_data)
        out_file.close()

        if self.test_local:
            local('server-manager add  server -f %s' %(server_file) )
            for u_server in u_server_dict['server']:
                local('server-manager show  server --server_id %s --detail' \
                          % u_server['id'] )
        else:
            svrmgr = self.svrmgr
            with  settings(host_string=svrmgr, warn_only=True):
                file_name = os.path.basename(server_file)
                temp_dir= tempfile.mkdtemp()
                run('mkdir -p %s' % temp_dir)
                put(server_file, '%s/%s' % (temp_dir, file_name))
                run('server-manager add  server -f %s/%s' %(temp_dir, file_name) )
                run('server-manager show  server --server_id %s --detail   | python -m json.tool' %server_id)
    #end  update_server_in_db_with_cluster_id

    def get_pref_cluster_id(self):
        cluster_id = None
        params=self.read_ini_file(self.smgr_config_ini)
        if  params.has_key('cluster_id'):
            cluster_id = params['cluster_id']
        else:
            cluster_id = self.get_cluster_id()
        return cluster_id
    #end get_pref_cluster_id(self):

    def get_svrmgr(self):
        svrmgr = None
        params=self.params
        if  params.has_key('svrmgr'):
            svrmgr = params['svrmgr']
        return params['svrmgr']
    #end get_svrmgr(self):

    def get_server_file(self):
        params=self.params
        if not params:
            return None
        if not params.has_key('server_file'):
            return None
        server_file = params['server_file']
        return server_file
    #end get_server_file(self):

    def get_testbed(self):
        filepath = self.testbed_py
        if not filepath:
            sys.exit("tesbed.py missing in args  ")
        mod_name,file_ext = os.path.splitext(os.path.split(filepath)[-1])

        if file_ext.lower() == '.py':
            py_mod = imp.load_source(mod_name, filepath)
        return py_mod
    #end get_testbed(self):

    def verify_roles(self):
        result = True
        for node in env.roledefs['database']:
            with  settings(host_string=node, warn_only=True):
                try:
                  verify.verify_database()
                except SystemExit:
                  self.logger.error('verify_database has Failed')
                  result = result and False
        for node in env.roledefs['cfgm']:
            with  settings(host_string=node, warn_only=True):
                try:
                  verify.verify_cfgm()
                except SystemExit:
                  self.logger.error('verify_cfgm has Failed')
                  result = result and False
        for node in env.roledefs['control']:
            with  settings(host_string=node, warn_only=True):
                try:
                  verify.verify_control()
                except SystemExit:
                  self.logger.error('verify_control has Failed')
                  result = result and False
        for node in env.roledefs['collector']:
            with  settings(host_string=node, warn_only=True):
                try:
                  verify.verify_collector()
                except SystemExit:
                  self.logger.error('verify_collector has Failed')
                  result = result and False
        for node in env.roledefs['webui']:
            with  settings(host_string=node, warn_only=True):
                try:
                  verify.verify_webui()
                except SystemExit:
                  self.logger.error('verify_webui has Failed')
                  result = result and False
        for node in env.roledefs['compute']:
            with  settings(host_string=node, warn_only=True):
                try:
                  verify.verify_compute()
                except SystemExit:
                  self.logger.error('verify_compute has Failed')
                  result = result and False
        for node in env.roledefs['openstack']:
            with  settings(host_string=node, warn_only=True):
                try:
                  verify.verify_openstack()
                except SystemExit:
                  self.logger.error('verify_openstack has Failed')
                  result = result and False
        return result
    #end verify_roles(self):

    def verify_contrail_status(self):
        result = True
        if not self.verify_database():
           result = result and False
        if not self.verify_cfgm():
           result = result and False
        if not self.verify_control():
           result = result and False
        if not self.verify_collector():
           result = result and False
        if not self.verify_webui():
           result = result and False
        if not self.verify_compute():
           result = result and False
        if not self.verify_openstack():
           result = result and False
        return result
    #end verify_contrail_status

    def verify_openstack(self):
        result = True
        for node in env.roledefs['openstack']:
            with  settings(host_string=node, warn_only=True):
                output = run('source /etc/contrail/keystonerc')
                output = run('openstack-status')
                pattern = ["openstack-nova-api:           active",
                           "openstack-nova-compute:       inactive (disabled on boot)",
                           "openstack-nova-network:       inactive (disabled on boot)",
                           "openstack-nova-scheduler:     active",
                           "openstack-nova-volume:        inactive (disabled on boot)",
                           "openstack-nova-conductor:     active",
                           "openstack-glance-api:         active",
                           "openstack-glance-registry:    active",
                           "openstack-keystone:           active",
                           "openstack-cinder-api:         active",
                           "openstack-cinder-scheduler:   active",
                           "openstack-cinder-volume:      inactive (disabled on boot)",
                           "mysql:                        inactive (disabled on boot)",
                           "rabbitmq-server:              active",
                           "memcached:                    inactive (disabled on boot)"]
                for line in pattern:
                  if line not in output:
                    self.logger.error('verify %s has Failed' %line)
                    result = result and False
        return result
    #end verify_openstack(self):

    def verify_compute(self):
        result = True
        for node in env.roledefs['compute']:
            with  settings(host_string=node, warn_only=True):
                output = run('contrail-status')
                pattern = ["supervisor-vrouter:           active",
                           "contrail-vrouter-agent        active",
                           "contrail-vrouter-nodemgr      active"]
                for line in pattern:
                  if line not in output:
                    self.logger.error('verify %s has Failed' %line)
                    result = result and False
        return result
    #end verify_compute(self):

    def verify_webui(self):
        result = True
        for node in env.roledefs['webui']:
            with  settings(host_string=node, warn_only=True):
                output = run('contrail-status')
                pattern = ["supervisor-webui:             active",
                           "contrail-webui                active",
                           "contrail-webui-middleware     active",
                           "redis-webui                   active"]
                for line in pattern:
                  if line not in output:
                    self.logger.error('verify %s has Failed' %line)
                    result = result and False
        return result
    #end verify_webui(self):

    def verify_collector(self):
        result = True
        for node in env.roledefs['collector']:
            with  settings(host_string=node, warn_only=True):
                output = run('contrail-status')
                pattern = ["supervisor-analytics:         active",
                           "contrail-analytics-api        active",
                           "contrail-analytics-nodemgr    active",
                           "contrail-collector            active",
                           "contrail-query-engine         active"]
                for line in pattern:
                  if line not in output:
                    self.logger.error('verify %s has Failed' %line)
                    result = result and False
        return result
    #end verify_collector(self):

    def verify_database(self):
        result = True
        for node in env.roledefs['database']:
            with  settings(host_string=node, warn_only=True):
                output = run('contrail-status')
                pattern = ["supervisord-contrail-database:active",
                           "contrail-database             active",
                           "contrail-database-nodemgr     active"]
                for line in pattern:
                  if line not in output:
                    self.logger.error('verify %s has Failed' %line)
                    result = result and False
        return result
    #end verify_database(self):

    def verify_cfgm(self):
        result = True
        for node in env.roledefs['cfgm']:
            with  settings(host_string=node, warn_only=True):
                output = run('contrail-status')
                pattern = ["supervisor-config:            active",
                           "contrail-api:0                active",
                           "contrail-config-nodemgr       active",
                           "contrail-discovery:0          active",
                           "contrail-schema               active",
                           "contrail-svc-monitor          active",
                           "ifmap                         active",
                           "rabbitmq-server               active"]

                for line in pattern:
                  if line not in output:
                    self.logger.error('verify %s has Failed' %line)
                    result = result and False
        return result
    #end verify_cfgm(self):

    def verify_control(self):
        result = True
        for node in env.roledefs['control']:
            with  settings(host_string=node, warn_only=True):
                output = run('contrail-status')
                pattern = ["supervisor-control:           active",
                           "contrail-control              active",
                           "contrail-control-nodemgr      active",
                           "contrail-dns                  active",
                           "contrail-named                active"]
                for line in pattern:
                  if line not in output:
                    self.logger.error('verify %s has Failed' %line)
                    result = result and False
        return result
    #end verify_control(self):

    def reimage(self, no_pkg=False):
        """ using svrmgr, reimage all the nodes """

        result = True
        image_id = self.get_image_id()
        pkg_id = self.get_pkg_id()
        cluster_id = self.get_cluster_id()
        svrmgr = self.get_svrmgr()

        with  settings(host_string=svrmgr, warn_only=True):
            run('server-manager show all | python -m json.tool')
            if no_pkg:
                output=run('server-manager reimage --cluster_id %s  %s' %(cluster_id,image_id))
            else:
                output=run('server-manager reimage --package_image_id %s --cluster_id %s  %s' %(pkg_id,cluster_id,image_id))
            if "reimage issued" not in output:
                self.logger.warn("Reimage command was not successfull")

        if not self.verify_server_status("reimage_issued") :
           self.logger.error("server status \"reimage_issued\" not correctly updated")
           result = result and False
        self.logger.info("Server Rebooted. Going to sleep for %d seconds...." %REIMAGE_WAIT)
        sleep(REIMAGE_WAIT)

        user = "root"
        server_state = {}

        server_file = self.get_server_file()
        in_file = open( server_file, 'r' )
        in_data = in_file.read()
        server_dict = json.loads(in_data)

        for  node in server_dict['server']:
            server_ip = node['ip_address']
            server_state[server_ip] = False

        for retry in range(SERVER_RETRY_TIME):
          for  node in server_dict['server']:
            server_ip = node['ip_address']
            if not verify_sshd(server_ip, user, env.password):
               sleep(1)
               self.logger.info("Node %s not reachable....retrying" %(server_ip))
               server_state[server_ip] = False
            else:
               self.logger.info("Node %s is UP" %(server_ip))
               if  server_state[server_ip] == False:
                   target_node = '%s@%s' %(user,server_ip)
                   with settings( host_string = target_node ):
                       connections.connect(env.host_string)
                   with settings( host_string = target_node ) :
                       output = run('uptime')
                       uptime = int(output.split()[2])
                       if uptime > 3 :
                           raise RuntimeError('Restart failed for Host (%s)' %server_ip)
                       else :
                           self.logger.info("Node %s has rebooted and UP now" %(server_ip))
                           if not no_pkg:
                               output = run('dpkg -l | grep contrail')
                               match = re.search('contrail-fabric-utils\s+(\S+)\s+', output, re.M)
                               if pkg_id not in match.group(1) :
                                   raise RuntimeError('Reimage not able to download package %s on targetNode (%s)' \
                                                  %(pkg_id, server_ip) )
                               match = re.search('contrail-install-packages\s+(\S+)\s+', output, re.M)
                               if pkg_id not in match.group(1) :
                                   raise RuntimeError('Reimage not able to download package %s on targetNode (%s)' \
                                                  %(pkg_id, server_ip) )
                           server_state[server_ip] = True

          #End for  node in server_dict['server']:

          cluster_state = True
          for key in server_state:
            cluster_state = cluster_state and server_state[key]

          if cluster_state == True:
            break
          #End for key in server:

        #End for retry in range(SERVER_RETRY_TIME):

        if not cluster_state:
            raise RuntimeError('Unable to SSH to one or more Host ' )

        if not self.verify_server_status("datacenter", "demo-dc", "reimage_completed") :
           result = result and False

        return result
    #end reimage

    def provision(self):
        """ using svrmgr, provision the cluster  """
        result = True
        image_id = self.get_image_id()
        pkg_id = self.get_pkg_id()
        cluster_id = self.get_cluster_id()
        svrmgr = self.get_svrmgr()

        with  settings(host_string=svrmgr, warn_only=True):
            output = run('server-manager provision --cluster_id %s %s' %(cluster_id,pkg_id) )
            if "provisioned" not in output:
               self.logger.error("provision command was not successfull")
               result = result and False
            run('server-manager show all | python -m json.tool')
        return result
    #end provision(self):

    def setup_cluster(self, no_reimage_pkg=False):
        result = True
        if no_reimage_pkg:
            if not self.reimage(no_pkg=True) :
               result = result and False
        else:
            if not self.reimage() :
               result = result and False
        if not self.provision() :
            result = result and False
        self.logger.info("Cluster provisioning initiated... Going to sleep for %d seconds...." %PROVISION_TIME)
        sleep(PROVISION_TIME)
        #if not self.verify_roles():
        #    result = result and False
        if not self.verify_server_status("provision_completed"):
            result = result and False
        if not self.verify_contrail_status():
            result = result and False

        return result
    #end setup_cluster

    def get_cluster_status_having_this_tag(self, tag_name="datacenter", tag_value="demo-dc"):
        params=self.params

        server_dict={}

        temp_dir= expanduser("~")

        file_name = '%s/status.json' %(temp_dir)

        if self.test_local:
            local('server-manager status server --tag %s=%s \
                         | tr -d "\n" \
                         | sed "s/[^{]*//" \
                         | python -m json.tool  \
                         > %s' %(tag_name, tag_value, file_name))
        else:
            svrmgr = self.svrmgr
            with  settings(host_string=svrmgr, warn_only=True):
                temp_dir= tempfile.mkdtemp()
                run('mkdir -p %s' % temp_dir)
                file_name = '%s/status.json' %(temp_dir)
                run('server-manager status  server --tag %s=%s  \
                     | tr -d "\n" \
                     | sed \'s/[^{]*//\'  \
                     | python -m json.tool  \
                     > %s' %(tag_name, tag_value, file_name) )
                local('mkdir -p %s' % temp_dir)
                get( file_name, file_name )

        in_file = open( file_name, 'r' )
        in_data = in_file.read()
        server_dict = json.loads(in_data)
        return server_dict
    #end get_cluster_status_having_this_tag

    def verify_server_status(self, status, tag_name="datacenter", tag_value="demo-dc"):
        """ verify status of server """
        result = True
        expected_state = {}
        actual_state = {}
        server_file = self.get_server_file()
        in_file = open( server_file, 'r' )
        in_data = in_file.read()
        in_file.close()
        server_dict = json.loads(in_data)

        for  node in server_dict['server']:
            server_ip = node['ip_address']
            expected_state[server_ip] = status

        status_dict = self.get_cluster_status_having_this_tag()

        for  node in status_dict['server']:
            server_ip = node['ip_address']
            actual_state[server_ip] = status

        if cmp(expected_state,actual_state) != 0:
           self.logger.error(
                'Cluster status \"%s\" is incorrectly updated for %s=%s ' %
                (status, tag_name, tag_value))
           result = result and False
        else:
           self.logger.info(
                'Cluster status \"%s\" is correctly updated for %s=%s ' %
                (status, tag_name, tag_value))
        return result
    #end verify_server_status

# end SmgrFixture


def getIp(string) :
   regEx = re.compile( '\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}' )
   result = regEx.search(string)
   if result:
     return result.group()
   else:
     return None
#end getIp(string) :

def verify_sshd(host, user, password):
    import paramiko
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username=user, password=password, timeout=5)
    except Exception:
        return False
    client.close()
    return True
#end verify_sshd
