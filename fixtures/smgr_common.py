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
from fabric.state import connections
from time import sleep
from common.contrail_test_init import ContrailTestInit

from common import log_orig as logging
import logging as std_logging
import time



REIMAGE_WAIT=700
SERVER_RETRY_TIME=150
PROVISION_TIME = 1800
RESTART_WAIT=300
RESTART_MESSAGE = "IPMI reboot operation initiated"
RESTART_OK = "restart issued"
REIMAGE_OK = "reimage queued"
PROVISION_OK = "provision issued"




class SmgrFixture(fixtures.Fixture):

    ''' Fixture to bring up a vns cluster using server manager .

    '''

    def __init__(self, inputs, testbed_py="./testbed.py",
	 smgr_config_ini="./smgr_input.ini", 
	test_local=False,logger = None):
        self.testbed_py = testbed_py
        self.testbed = self.get_testbed()
        self.smgr_config_ini = smgr_config_ini
        self.test_local = test_local
        self.params = self.read_ini_file(smgr_config_ini)
        self.svrmgr = self.params['svrmgr']
        self.svrmgr_password = self.params['smgr_password']
        self.logger = logger
    # end __init__

    def svrmgr_add_all(self):
        self.add_cluster()
        self.add_image()
        self.add_pkg()
        self.add_server()
        self.add_tags()
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

    def get_compute_node_from_testbed_py(self):
        testbed = self.testbed
        if not testbed.env.has_key('roledefs'):
            return None
        return testbed.env.roledefs['compute']
    # end get_compute_node_from_testbed_py

    def get_remaining_node_from_testbed_py(self, test_node):
        testbed = self.testbed
        remaining_node = ' '
        for node in testbed.env.roledefs['all']:
            if node not in test_node:
                remaining_node += node
        return remaining_node 
    # end get_remaining_node_from_testbed_py

    def delete_cluster_id_based(self, test_cluster_id=None):
        if test_cluster_id is None:
            return False
        if self.test_local:
            local('server-manager delete cluster --cluster_id %s' %test_cluster_id)
        else:
            with settings(host_string=self.svrmgr, password=self.svrmgr_password, warn_only=True):
                run('server-manager delete cluster --cluster_id %s' %test_cluster_id)
                run('server-manager show server')
    #end delete_cluster_id_based

    def delete_server_id_based(self, test_node_id=None):
        if test_node_id is None:
            return False
        if self.test_local:
            local('server-manager delete server --server_id %s' %test_node_id)
        else:
            with settings(host_string=self.svrmgr, password=self.svrmgr_password, warn_only=True):
                run('server-manager delete server --server_id %s' %test_node_id)
                run('server-manager show server')
    #end delete_server_id_based

    def delete_server(self, test_node):
        ip = test_node.split('@')[1]
        server_dict = self.get_server_with_ip_from_db(ip)
        server_id = server_dict['server'][0]['id']
        self.delete_server_id_based(server_id)
        
    # end delete_server

    def provision_server(self, node):
        result = True
        svrmgr = self.get_svrmgr()
        svrmgr_password = self.svrmgr_password
        ip = node.split('@')[1]
        server_dict = self.get_server_with_ip_from_db(ip)
        server_id = server_dict['server'][0]['id']
        pkg_id = self.get_pkg_id()
        with  settings(host_string=svrmgr, password=svrmgr_password, warn_only=True):
            output = run('server-manager provision -F --server_id %s %s' %(server_id,pkg_id) )
            if PROVISION_OK not in output:
               self.logger.error("provision command was not successfull")
               result = result and False
            run('server-manager status server --server_id %s' %server_id)
        return result
        
    # end provision_server

    def delete_compute_node(self):
        cn_list = self.get_compute_node_from_testbed_py()
        if cn_list == None:
            return None
        if len(cn_list) == 1:
            return None
        if len(cn_list) > 1:
            test_node = cn_list[-1]

        self.delete_server(test_node)
        return test_node
    # end delete_compute_node

    
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
                                      "id" : "",
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
            with open(cluster_file, 'r') as clf: data=json.load(clf)
            clf.close()
            data['cluster'][0]['id'] = cluster_id
            with open(cluster_file, 'w') as clf: json.dump(data, clf)
            clf.close()

        if self.test_local:
            local('server-manager add  cluster -f %s' %(cluster_file))
        else:
            svrmgr = self.svrmgr
            svrmgr_password = self.svrmgr_password
            with settings(host_string=svrmgr, password=svrmgr_password, warn_only=True):
                file_name = os.path.basename(cluster_file)
                temp_dir= tempfile.mkdtemp()
                run('mkdir -p %s' % temp_dir)
                put(cluster_file, '%s/%s' % (temp_dir, file_name))
                run('server-manager add  cluster -f %s/%s' %(temp_dir, file_name) )
                run('server-manager show cluster')
    # end add_cluster()

    def add_server(self):
        self.add_server_using_json()
        self.update_server_in_db_with_testbed_py()
    #end add_server

    def add_tags(self):
        params=self.params
        if not params:
            return None

        if not params.has_key('tags_file'):
            return None
        tags_file = params['tags_file']

        if self.test_local:
            local('server-manager add tag -f %s' %(tags_file))
            local('server-manager show tag')
        else:
            svrmgr = self.svrmgr
            svrmgr_password = self.svrmgr_password
            with  settings(host_string=svrmgr, password=svrmgr_password, warn_only=True):
                file_name = os.path.basename(tags_file)
                temp_dir= tempfile.mkdtemp()
                run('mkdir -p %s' % temp_dir)
                put(tags_file, '%s/%s' % (temp_dir, file_name))
                run('server-manager add tag -f %s/%s' %(temp_dir, file_name) )
                run('server-manager show tag')
    #end add_tags

    def add_image(self):
        params=self.params
        if not params:
            return None
        if not params.has_key('image_file'):
            return None
        image_file = params['image_file']

        if self.test_local:
            local('server-manager add  image -f %s' %(image_file))
            local('server-manager show image')
        else:
            svrmgr = self.svrmgr
            svrmgr_password = self.svrmgr_password
            with settings(host_string=svrmgr, password=svrmgr_password, warn_only=True):
                file_name = os.path.basename(image_file)
                temp_dir = tempfile.mkdtemp()
                run('mkdir -p %s' % temp_dir)
                put(image_file, '%s/%s' % (temp_dir, file_name))

                run('server-manager add  image -f %s/%s' %(temp_dir, file_name) )
                run('server-manager show image')
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
            svrmgr_password = self.svrmgr_password
            with  settings(host_string=svrmgr, password=svrmgr_password, warn_only=True):
                file_name = os.path.basename(pkg_file)
                temp_dir= tempfile.mkdtemp()
                run('mkdir -p %s' % temp_dir)
                put(pkg_file, '%s/%s' % (temp_dir, file_name))

                run('server-manager add  image -f %s/%s' %(temp_dir, file_name) )
                run('server-manager show image')
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
            svrmgr_password = self.svrmgr_password
            with  settings(host_string=svrmgr, password=svrmgr_password, warn_only=True):
                file_name = os.path.basename(server_file)
                temp_dir= tempfile.mkdtemp()
                run('mkdir -p %s' % temp_dir)
                put(server_file, '%s/%s' % (temp_dir, file_name))
                run('server-manager add  server -f %s/%s' %(temp_dir, file_name) )
                run('server-manager show server')
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
                                  "encapsulation_priority": "'MPLSoUDP','MPLSoGRE','VXLAN'",
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
            svrmgr_password = self.svrmgr_password
            with  settings(host_string=svrmgr, password=svrmgr_password, warn_only=True):
                temp_dir= tempfile.mkdtemp()
                run('mkdir -p %s' % temp_dir)
                file_name = '%s/server_list.json' %(temp_dir)

                run('server-manager show  server --cluster_id %s --detail \
                     | tr -d "\n" \
                     | sed \'s/[^{]*//\'  \
                     > %s' %(cluster_id, file_name) )

                local('mkdir -p %s' % temp_dir)

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
            svrmgr_password = self.svrmgr_password
            with  settings(host_string=svrmgr, password=svrmgr_password, warn_only=True):
                temp_dir= tempfile.mkdtemp()
                run('mkdir -p %s' % temp_dir)
                file_name = '%s/cluster.json' %(temp_dir)
                run('server-manager show  cluster --cluster_id %s --detail\
                     | tr -d "\n" \
                     | sed \'s/[^{]*//\'  \
                     > %s' %(cluster_id, file_name) )
                local('mkdir -p %s' % temp_dir)

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
            svrmgr_password = self.svrmgr_password
            with  settings(host_string=svrmgr, password=svrmgr_password, warn_only=True):
                temp_dir= tempfile.mkdtemp()
                run('mkdir -p %s' % temp_dir)
                file_name = '%s/server.json' %(temp_dir)
                run('server-manager show  server --ip %s --detail \
                     | tr -d "\n" \
                     | sed \'s/[^{]*//\'  \
                     > %s' %(ip, file_name) )
                local('mkdir -p %s' % temp_dir)

        in_file = open( file_name, 'r' )
        in_data = in_file.read()
        server_dict = json.loads(in_data)
        return server_dict
    #end get_server_with_ip_from_db(self, ip=None):

    def get_ip_using_server_id(self, node_name=None):
        if node_name is None:
            return False
        local('server-manager-client display server --server_id %s --select "ip_address" --json > host_ip.txt' % node_name)
        fd=open('host_ip.txt','r')
        data=json.load(fd)
        fd.close()
        local('rm -rf host_ip.txt')
        return data['server'][0]['ip_address']
    #end get_ip_using_server_id

    def get_pswd_using_server_id(self, node_name=None):
        if node_name is None:
            return False
        local('server-manager-client display server --server_id %s --select "password" --json > host_pswd.txt' % node_name)
        fd=open('host_pswd.txt','r')
        data=json.load(fd)
        fd.close()
        local('rm -rf host_pswd.txt')
        return data['server'][0]['password']
    #end get_pswd_using_server_id

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
            svrmgr_password = self.svrmgr_password
            with  settings(host_string=svrmgr, password=svrmgr_password, warn_only=True):
                file_name = os.path.basename(server_file)
                temp_dir= tempfile.mkdtemp()
                run('mkdir -p %s' % temp_dir)
                put(server_file, '%s/%s' % (temp_dir, file_name))
                run('server-manager add  server -f %s/%s' %(temp_dir, file_name) )
                run('server-manager show  server --server_id %s --detail' %server_id)
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

    def verify_contrail_status(self, skip_node=None):
        result = True
        if not self.verify_database(skip_node):
           result = result and False
        if not self.verify_cfgm(skip_node):
           result = result and False
        if not self.verify_control(skip_node):
           result = result and False
        if not self.verify_collector(skip_node):
           result = result and False
        if not self.verify_webui(skip_node):
           result = result and False
        if not self.verify_compute(skip_node):
           result = result and False
        if not self.verify_openstack(skip_node):
           result = result and False
        return result
    #end verify_contrail_status

    def verify_openstack(self, skip_node):
        result = True
        for node in env.roledefs['openstack']:
            if skip_node:
                if node in skip_node:
                    continue
            with settings(host_string=node, warn_only=True):
                output = run('source /etc/contrail/keystonerc')
                output = run('openstack-status')
                pattern = ["openstack-nova-api:           active",
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

    def verify_compute(self, skip_node):
        result = True
        for node in env.roledefs['compute']:
            if skip_node:
                if node in skip_node:
                    continue
            with settings(host_string=node, warn_only=True):
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

    def verify_webui(self, skip_node):
        result = True
        for node in env.roledefs['webui']:
            if skip_node:
                if node in skip_node:
                    continue
            with settings(host_string=node, warn_only=True):
                output = run('contrail-status')
                pattern = ["supervisor-webui:             active",
                           "contrail-webui                active",
                           "contrail-webui-middleware     active"]
                for line in pattern:
                  if line not in output:
                    self.logger.error('verify %s has Failed' %line)
                    result = result and False
        return result
    #end verify_webui(self):

    def verify_collector(self, skip_node=None):
        result = True
        for node in env.roledefs['collector']:
            if skip_node:
                if node in skip_node:
                    continue
            with settings(host_string=node, warn_only=True):
                output = run('contrail-status')
                pattern = ["supervisor-analytics:         active",
                           "contrail-analytics-api        active",
                           "contrail-analytics-nodemgr    active",
                           "contrail-collector            active",
                           "contrail-query-engine         active",
                           "contrail-snmp-collector       active",
                           "contrail-topology             active"]
                for line in pattern:
                  if line not in output:
                    self.logger.error('verify %s has Failed' %line)
                    result = result and False
        return result
    #end verify_collector(self):

    def verify_database(self, skip_node=None):
        result = True
        for node in env.roledefs['database']:
            if skip_node:
                if node in skip_node:
                    continue
            with settings(host_string=node, warn_only=True):
                output = run('contrail-status')
                pattern = ["supervisor-database:          active",
                           "contrail-database             active",
                           "contrail-database-nodemgr     active"]
                for line in pattern:
                  if line not in output:
                    self.logger.error('verify %s has Failed' %line)
                    result = result and False
        return result
    #end verify_database(self):

    def verify_cfgm(self, skip_node=None):
        result = True
        for node in env.roledefs['cfgm']:
            if skip_node:
                if node in skip_node:
                    continue
            with settings(host_string=node, warn_only=True):
                output = run('contrail-status')
                pattern = ["supervisor-config:            active",
                           "contrail-api:0                active",
                           "contrail-config-nodemgr       active",
                           "contrail-discovery:0          active",
                           "ifmap                         active",
                           "supervisor-support-service:   active",
                           "rabbitmq-server               active"]

                for line in pattern:
                  if line not in output:
                    self.logger.error('verify %s has Failed' %line)
                    result = result and False
        return result
    #end verify_cfgm(self):

    def verify_control(self, skip_node=None):
        result = True
        for node in env.roledefs['control']:
            if skip_node:
                if node in skip_node:
                    continue
            with settings(host_string=node, warn_only=True):
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

    def check_server_status_with_tag(self, tag=None, tag_server_ids=None):
        if ((tag is not None) and (tag_server_ids is not None)):
            flag_reimage_started=0
            for index in range(30):
                sleep(10)
                with settings(host_string=self.svrmgr, password=self.svrmgr_password, warn_only=True):
                    states=run('server-manager status server --tag %s | grep status' % tag)
                if len(states.splitlines()) == len(tag_server_ids):
                    flag_reimage_started=len(tag_server_ids)
                    for each_state in states.splitlines():
                        if (('restart_issued' in each_state.split(':')[1])
                            or ('reimage_started' in each_state.split(':')[1])):
                            flag_reimage_started=flag_reimage_started-1
                    if flag_reimage_started == 0:
                        self.logger.info('All the servers with tag %s have started reimaging' % tag)
                        flag_reimage_started='true'
                        break
                else:
                    self.logger.error('No of servers with tag %s and servers listed are not matching.' % tag)

            if flag_reimage_started == 'true':
                for index in range(24):
                    sleep(10)
                    with settings(host_string=self.svrmgr, password=self.svrmgr_password, warn_only=True):
                        states=run('server-manager status server --tag %s | grep status' % tag)
                    if len(states.splitlines()) == len(tag_server_ids):
                        flag_reimage_started=len(tag_server_ids)
                        for each_state in states.splitlines():
                            if ('reimage_completed' in each_state.split(':')[1]):
                                flag_reimage_started=flag_reimage_started-1
                        if flag_reimage_started == 0:
                            self.logger.info('All the servers with tag %s have reimaged successfully' % tag)
                            return True
                    else:
                        self.logger.error('No of servers with tag %s and servers listed are not matching.' % tag)
            else:
                self.logger.error('The servers did not move through restart_issued and reimage_started stares')
                return False
        else:
            self.logger.error("A tag in form of tag_index=tag_value and a list of tagged server id's is not provided.")
            return False
        return False
    #end check_server_status_with_tag

    def reimage(self, no_pkg=False, skip_node=None, restart_only=False, tag=None, tag_server_ids=None):
        """ using svrmgr, reimage all the nodes """

        result = True
        image_id = self.get_image_id()
        pkg_id = self.get_pkg_id()
        cluster_id = self.get_cluster_id()
        svrmgr = self.get_svrmgr()
        svrmgr_password = self.svrmgr_password
        server_file = self.get_server_file()
        in_file = open( server_file, 'r' )
        in_data = in_file.read()
        server_dict = json.loads(in_data)

        #Reimage and check status with tag.
        if ((tag is not None) and (tag_server_ids is not None)):
            with settings(host_string=svrmgr, password=svrmgr_password, warn_only=True):
                reimage_command_failed = 0
                server_ids=run('server-manager reimage -F --tag %s %s | grep id' % (tag, image_id))
                for each_node in tag_server_ids:
                    if each_node not in server_ids:
                        reimage_command_failed = 1
                if reimage_command_failed == 0:
                    self.logger.info("Reimage command was successfull")
                else:
                    self.logger.error("Reimage command FAILED")
                    return False
            sleep(30)
            result=self.check_server_status_with_tag(tag, tag_server_ids)
            return result

        with  settings(host_string=svrmgr, password=svrmgr_password, warn_only=True):
            run('server-manager show all')
            if no_pkg:
                if skip_node == None:
                  if restart_only:
                    output=run('server-manager restart --cluster_id %s -F' %(cluster_id))
                    if RESTART_MESSAGE not in output:
                        self.logger.warn("Restart command was not successfull")
                  else:
                    output=run('server-manager reimage --cluster_id %s -F  %s' %(cluster_id,image_id))
                    if REIMAGE_OK not in output:
                        self.logger.warn("Reimage command was not successfull")
                else:
                  for  node in server_dict['server']:
                    server_ip = node['ip_address']
                    if server_ip in skip_node:
                        continue
                    server_id = node['id']
                    sleep (5)
                    output=run('server-manager reimage -F --server_id %s %s' %(server_id,image_id))
            else:
                if skip_node == None:
                  output=run('server-manager reimage --package_image_id %s --cluster_id %s  %s -F' \
                                                                    %(pkg_id,cluster_id,image_id))
                else:
                  for  node in server_dict['server']:
                    server_ip = node['ip_address']
                    if server_ip in skip_node:
                        continue
                    output=run('server-manager reimage --server_id %s -F  %s' %(server_id,image_id))
            if not(restart_only):
                if "reimage queued" not in output:
                    self.logger.error("Reimage command was not successfull")
            
        if restart_only:
            expected_status = "restart_issued"
            expected_wait = RESTART_WAIT
        else:
            expected_status = "restart_issued"
            expected_wait = REIMAGE_WAIT
        if not self.verify_server_status(expected_status, skip_node) :
           self.logger.error("server status \"%s\" not correctly updated", expected_status)
           result = result and False

        self.logger.info("Server Rebooted. Going to sleep for %d seconds...." %expected_wait)
        sleep(expected_wait)

        user = "root"
        server_state = {}

        for  node in server_dict['server']:
            server_ip = node['ip_address']
            if skip_node:
                if server_ip in skip_node:
                    continue
            server_state[server_ip] = False

        home_dir= expanduser("~")
        local('rm -rf %s/.ssh/known_hosts' %home_dir)
        for retry in range(SERVER_RETRY_TIME):
          for  node in server_dict['server']:
            server_ip = node['ip_address']
            if skip_node:
                if server_ip in skip_node:
                    continue
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
                       uptime_string = output.split()[2]
                       if ':' in uptime_string:
                          uptime = int(uptime_string.split(':')[0])
                       else:
                          uptime = int(uptime_string)
                       if uptime > 9 :
                           raise RuntimeError('Restart failed for Host (%s)' %server_ip)
                       else :
                           self.logger.info("Node %s has rebooted and UP now" %(server_ip))
                           if not no_pkg:
                               output = run('dpkg -l | grep contrail')
                               match = re.search('contrail-fabric-utils\s+\S+-(\S+)\s+', output, re.M)
                               if match.group(1) not in pkg_id :
                                   raise RuntimeError('Reimage not able to download package %s on targetNode (%s)' \
                                                  %(pkg_id, server_ip) )
                               match = re.search('contrail-install-packages\s+\S+~(\S+)\s+', output, re.M)
                               if match.group(1) not in pkg_id :
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

        if  restart_only:
            expected_status = "restart_issued"
        else:
            expected_status = "reimage_completed"

        if not self.verify_server_status(expected_status, skip_node) :
            result = result and False

        return result
    #end reimage

    def provision(self, tag=None):
        """ using svrmgr, provision the cluster  """
        result = True
        image_id = self.get_image_id()
        pkg_id = self.get_pkg_id()
        cluster_id = self.get_cluster_id()
        svrmgr = self.get_svrmgr()
        svrmgr_password = self.svrmgr_password
        with settings(host_string=svrmgr, password=svrmgr_password, warn_only=True):
            if tag is not None:
                output = run('server-manager provision -F --tag %s %s' %(tag,pkg_id) )
                self.logger.info("Issued provision command with %s tag, %s package_id." % (tag, pkg_id))
            else:
                output = run('server-manager provision -F --cluster_id %s %s' %(cluster_id,pkg_id) )
                self.logger.info("Issued provision command with %s cluster_id, %s package_id." % (cluster_id, pkg_id))
            if PROVISION_OK not in output:
                self.logger.error("provision command was not successfull")
                result = result and False
            run('server-manager show all')
        return result
    #end provision(self):

    def setup_cluster(self, no_reimage_pkg=False, provision_only=False):
        result = True
        if not provision_only:
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
        if not self.verify_server_status("provision_completed"):
            result = result and False
        for node in env.roledefs['all']:
            try:
                with settings(host_string=node, warn_only=True):
                    output = run('contrail-version')
            except:
                continue
        if not self.verify_contrail_status():
            result = result and False

        return result
    #end setup_cluster

    def verify_node_add_delete(self, no_reimage_pkg=False):
        result = True
        test_node = self.delete_compute_node()
        if test_node == None:
            self.logger.info("Not enough nodes to perform this test")
            return None
        global nodethatisdeleted
        nodethatisdeleted = test_node
        if no_reimage_pkg:
            if not self.reimage(no_pkg=True, skip_node=test_node) :
               result = result and False
        else:
            if not self.reimage(skip_node=test_node) :
               result = result and False
        if not self.provision() :
            result = result and False
        self.logger.info("Cluster provisioning initiated... Going to sleep for %d seconds...." %PROVISION_TIME)
        sleep(PROVISION_TIME)
        if not self.verify_server_status("provision_completed", skip_node=test_node):
            result = result and False
        if not self.verify_contrail_status(skip_node=test_node):
            result = result and False

        #restoring all will re-add compute node 
        self.add_server()
        remaining_node = self.get_remaining_node_from_testbed_py(test_node)
        if no_reimage_pkg:
            if not self.reimage(no_pkg=True, skip_node=remaining_node) :
               result = result and False
        else:
            if not self.reimage(skip_node=remaining_node) :
               result = result and False
        if not self.provision_server(test_node) :
            result = result and False
        self.logger.info("Cluster provisioning initiated... Going to sleep for %d seconds...." %PROVISION_TIME)
        sleep(PROVISION_TIME)
        if not self.verify_server_status("provision_completed", skip_node=remaining_node):
            result = result and False
        if not self.verify_contrail_status():
            result = result and False

        return result
    #end setup_cluster

    def get_cluster_status_having_this_tag(self):
        params=self.params

        server_dict={}
        cluster_id = self.get_cluster_id()

        temp_dir= expanduser("~")

        file_name = '%s/status.json' %(temp_dir)

        if self.test_local:
            local('server-manager status server --cluster_id %s \
                         | tr -d "\n" \
                         | sed "s/[^{]*//" \
                         > %s' %(cluster_id, file_name))
        else:
            svrmgr = self.svrmgr
            svrmgr_password = self.svrmgr_password
            with  settings(host_string=svrmgr, password=svrmgr_password, warn_only=True):
                temp_dir= tempfile.mkdtemp()
                run('mkdir -p %s' % temp_dir)
                file_name = '%s/status.json' %(temp_dir)
                run('server-manager status  server --cluster_id %s  \
                     | tr -d "\n" \
                     | sed \'s/[^{]*//\'  \
                     > %s' %(cluster_id, file_name) )
                local('mkdir -p %s' % temp_dir)

        in_file = open( file_name, 'r' )
        in_data = in_file.read()
        server_dict = json.loads(in_data)
        return server_dict
    #end get_cluster_status_having_this_tag

    def verify_server_status(self, status, skip_node=None):
        """ verify status of server """
        result = True
        cluster_id = self.get_cluster_id()
        expected_state = {}
        actual_state = {}
        server_file = self.get_server_file()
        in_file = open( server_file, 'r' )
        in_data = in_file.read()
        in_file.close()
        server_dict = json.loads(in_data)
        for  node in server_dict['server']:
            server_ip = node['ip_address']
            if skip_node:
                if server_ip in skip_node:
                    continue
            expected_state[server_ip] = status

        status_dict = self.get_cluster_status_having_this_tag()

        for  node in status_dict['server']:
            server_ip = node['ip_address']
            if skip_node:
                if server_ip in skip_node:
                    continue
            actual_state[server_ip] = status

        if cmp(expected_state,actual_state) != 0:
           self.logger.error(
                'Cluster status \"%s\" is incorrectly updated for %s ' %
                (status, cluster_id))
           result = result and False
        else:
           self.logger.info(
                'Cluster status \"%s\" is correctly updated for %s ' %
                (status, cluster_id))
        return result
    #end verify_server_status

    # Install server manager and start the service provided the SM 
    # installer file path is specified.
    def install_sm(self, SM_installer_file_path=None):
        """Install Server Manager Server and verify it's running."""
        self.logger.info("Running install_sm...")
        result=False
        if SM_installer_file_path is None:
            self.logger.error("No installer file specified for SM")
            return False

        self.logger.info("Verify server manager install.")
        self.logger.info("Installer :: %s" % SM_installer_file_path)

        with settings(host_string=self.svrmgr, password=self.svrmgr_password, warn_only=True):
            run('dpkg -i %s' % SM_installer_file_path)
            run('cd /opt/contrail/contrail_server_manager/; ./setup.sh --all')
            run('rm -rf /etc/contrail_smgr/role_sequence.json')
            run('cp /contrail-smgr-save/dhcp.template /etc/cobbler/dhcp.template; cp /contrail-smgr-save/named.template /etc/cobbler/named.template')
            run('cp /contrail-smgr-save/settings /etc/cobbler/settings; cp /contrail-smgr-save/zone.template /etc/cobbler/zone.template')
            run('cp -r /contrail-smgr-save/zone_templates /etc/cobbler/; cp /contrail-smgr-save/named.conf.options /etc/bind/')
            run('service contrail-server-manager start')
            time.sleep(30)
            SM_port=run('netstat -nap | grep 9001')
            if '9001' in SM_port:
                result=True
        return result
    #end install_sm

    # Uninstall Server Manager and delete trailing directories.
    def uninstall_sm(self):
        """Uninstall Server Manager Server and cleanup."""
        self.logger.info("Running uninstall_sm...")

        with settings(host_string=self.svrmgr, password=self.svrmgr_password, warn_only=True):
            run('mkdir -p /contrail-smgr-save/; cp /etc/cobbler/named.template /contrail-smgr-save')
            run('cp /etc/cobbler/settings /contrail-smgr-save; cp /etc/cobbler/zone.template /contrail-smgr-save')
            run('cp /etc/cobbler/dhcp.template /contrail-smgr-save')
            run('cp -r /etc/cobbler/zone_templates /contrail-smgr-save; cp /etc/bind/named.conf.options /contrail-smgr-save')
            run('service contrail-server-manager stop')
            run('dpkg -r contrail-server-manager-installer')
            run('dpkg -P contrail-server-manager')
            run('dpkg -P contrail-server-manager-client')
            run('dpkg -P contrail-server-manager-monitoring')
            run('dpkg -P contrail-web-server-manager')
            run('dpkg -P contrail-web-core')
            run('dpkg -P python-contrail')
            run('rm -rf /opt/contrail/contrail_server_manager/; rm -rf /opt/contrail/server-manager')
        return True
    #end uninstall_sm

    # Back-up or save a file with extn _back_up.
    def backup_file(self, file_path=None):
        result = False
        self.logger.info("Running backup_file...")
        if file_path is None:
            self.logger.error("No file path passed to the function")
            return result
        bkup_file=file_path + "_back_up"
        with settings(host_string=self.svrmgr, password=self.svrmgr_password, warn_only=True):
            run('cp -rf %s %s' % (file_path, bkup_file))
            run('ls -lrt %s' % bkup_file)
            result=True
        return result
    #end backup_file

    # Restore a file provided a file with extn _back_up exists in the same path.
    def restore_file(self, file_path=None):
        self.logger.info("Running restore_file...")
        return True
    #end restore_file

    def add_tag_to_server(self, server_ip, tag_index, tag_value):
        server_dict = self.get_server_with_ip_from_db(server_ip)
        server_id = server_dict['server'][0]['id']
        server_file = '/tmp/tempserver.json'
        with settings(host_string=self.svrmgr, password=self.svrmgr_password, warn_only=True):
            run('server-manager show server --server_id %s -d > %s' % (server_id, server_file))
            with open(server_file, 'r') as svf:
                data=json.load(svf)
            svf.close()
            data['server'][0]['tag'][tag_index]=tag_value
            with open(server_file, 'w') as svf:
                json.dump(data, svf)
            svf.close()
            run('server-manager add server -f %s' % server_file)
        return server_id
    #end add_tag_to_server

    def delete_tag_from_server(self, server_ip, tag_index=None, all_tags=False):
        server_dict = self.get_server_with_ip_from_db(server_ip)
        server_id = server_dict['server'][0]['id']
        server_file = '/tmp/tempserver.json'
        if (all_tags == True) or (tag_index == None):
            with settings(host_string=self.svrmgr, password=self.svrmgr_password, warn_only=True):
                run('server-manager show server --server_id %s -d > %s' % (server_id, server_file))
                with open(server_file, 'r') as svf:
                    data=json.load(svf)
                svf.close()
                data['server'][0]['tag']['datacenter']=''
                data['server'][0]['tag']['floor']=''
                data['server'][0]['tag']['hall']=''
                data['server'][0]['tag']['rack']=''
                data['server'][0]['tag']['user_tag']=''
                with open(server_file, 'w') as svf:
                    json.dump(data, svf)
                svf.close()
                run('server-manager add server -f %s' % server_file)
        else:
            with settings(host_string=self.svrmgr, password=self.svrmgr_password, warn_only=True):
                run('server-manager show server --server_id %s -d > %s' % (server_id, server_file))
                with open(server_file, 'r') as svf:
                    data=json.load(svf)
                svf.close()
                data['server'][0]['tag'][tag_index]=''
                with open(server_file, 'w') as svf:
                    json.dump(data, svf)
                svf.close()
                run('server-manager add server -f %s' % server_file)
        return True
    #end delete_tag_from_server

    def add_tag_and_verify_server_listing(self, server_list=None, tag_ind=None, tag_val=None):
        if (server_list is None) or (tag_ind is None) or (tag_val is None):
            self.logger.error("No server_list or tag_ind or tag_val was provided to add_and_list_tag.")

        # Configure tag on servers.
        server_id_list = []
        for node in server_list:
            server_id_list.append(self.add_tag_to_server(server_ip=node.split('@')[1],
                tag_index=tag_ind, tag_value=tag_val))
        # Check listing servers with tag.
        with settings(host_string=self.svrmgr, password=self.svrmgr_password, warn_only=True):
            no_of_servers=run("server-manager show server --tag %s='%s' | grep id | wc -l" % (tag_ind, tag_val))
            server_ids=run("server-manager show server --tag %s='%s' | grep id" % (tag_ind, tag_val))
        if (len(server_list) != int(no_of_servers)):
            self.logger.error("All the nodes with tag %s='%s' were not listed" % (tag_ind, tag_val))
            return False
        fail_flag=0
        for server_id in server_id_list:
            if server_id in server_ids:
                self.logger.info("Server %s listed with tag %s='%s'" % (server_id, tag_ind, tag_val))
            else:
                self.logger.error("Server %s not listed with tag %s='%s'" % (server_id, tag_ind, tag_val))
                fail_flag=1
        if fail_flag == 1:
            self.logger.error("Test test_list_servers_using_tag FAILED")
            return False
        return True
    #end add_tag_and_verify_server_listing 

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

