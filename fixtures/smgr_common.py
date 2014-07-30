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
from fabric.api import env
from fabric.api import hosts, run, task
from fabric.api import local, put, get
from fabric.tasks import execute
from os.path import expanduser
import imp
import fabfile.tasks.verify as verify


class SmgrFixture(fixtures.Fixture):

    ''' Fixture to bring up a vns cluster using server manager .

    '''

    def __init__(self, testbed_py="./testbed.py", smgr_config_ini="./smgr_input.ini", test_local=False):
        self.testbed_py = testbed_py
        self.testbed = self.get_testbed()
        self.smgr_config_ini = smgr_config_ini
        self.test_local = test_local
        self.params = self.read_ini_file(smgr_config_ini)
        self.svrmgr = self.params['svrmgr']
    # end __init__

    def svrmgr_add_all(self):
        self.create_json()
        self.add_vns()
        self.add_image()
        self.add_pkg()
        self.add_server()


    def create_json(self):
        self.modify_server_json()
        self.modify_vns_json()

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

    def update_roles_from_testbed_py(self, server_dict):
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
              if node['ip'] == ip:
                if key == 'cfgm':
                    roles.append("config")
                else:
                    roles.append(key)
          if not len(roles):
            node['roles'] = [ "compute" ]
          else:
            node['roles'] =  roles

        for  node in server_dict['server']:
           node['vns_id'] =  self.get_pref_vns_id()

        return server_dict
    # end update_roles_from_testbed_py

    def update_bond_from_testbed_py(self, server_dict):
        testbed = self.testbed
        if 'control_data' in dir(testbed):

          for  node in server_dict['server']:
            for  key in testbed.bond:
              ip = getIp(key)
              if node['ip'] == ip:
                  node['server_params']['setup_interface'] = "Yes"
                  node['server_params']['compute_non_mgmt_ip'] = ""
                  node['server_params']['compute_non_mgmt_gw'] = ""

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
              if node['ip'] == ip:
                  node['server_params']['setup_interface'] = "Yes"
                  node['server_params']['compute_non_mgmt_ip'] = ""
                  node['server_params']['compute_non_mgmt_gway'] = ""

                  ip = testbed.control_data[key]['ip']
                  gw = testbed.control_data[key]['gw']
                  device = testbed.control_data[key]['device']

                  node['control']={}
                  node['control'][device] = {}
                  node['control'][device]['ip'] = ip
                  node['control'][device]['gw'] = gw

        return server_dict

    #End update_multi_if_from_testbed_py(server_dict):


    def get_image_id(self) :
        params=self.params
        image_file = params['image_file']

        image_file = open( image_file, 'r' )
        image_data = image_file.read()
        image_json = json.loads(image_data)
        image_id = image_json['image'][0]['image_id']
        image_file.close()
        return image_id
    # end get_image_id()

    def get_pkg_id(self) :
        params=self.params
        pkg_file = params['pkg_file']

        pkg_file = open( pkg_file, 'r' )
        pkg_data = pkg_file.read()
        pkg_json = json.loads(pkg_data)
        pkg_id = pkg_json['image'][0]['image_id']
        pkg_file.close()
        return pkg_id
    # end get_pkg_id()

    def get_vns_id(self) :
        vns_id = None
        params=self.params
        vns_file = params['vns_file']

        vns_file = open( vns_file, 'r' )
        vns_data = vns_file.read()
        vns_json = json.loads(vns_data)
        vns_id = vns_json['vns'][0]['vns_id']
        if  params.has_key('vns_id'):
            vns_id = params['vns_id']
        vns_file.close()
        return vns_id

    # end get_vns_id()


    def add_vns(self):
        vns_file = None
        params=self.params
        if  params.has_key('vns_file'):
            vns_file = params['vns_file']

        vns_id = self.get_pref_vns_id()
        if not vns_file:
            vns_dict = self.get_vns_with_vns_id_from_db()
            if not len(vns_dict['vns']):
                vns_dict = new_vns()
            else:
                vns_dict = {
                              "vns" : [
                                  {
                                      "vns_id" : "",
                                      "vns_params" : {
    
                                          }
                                  }
                              ]
                           }

            vns_dict['vns'][0]['vns_id'] = vns_id
            self.modify_vns_from_testbed_py(vns_dict)
            temp_dir= expanduser("~")
            vns_file = '%s/vns.json' %temp_dir
            local('touch %s' %vns_file)
            out_file = open(vns_file, 'w')
            out_data = json.dumps(vns_dict, indent=4)

            out_file.write(out_data)
            out_file.close()
        else :
            timestamp = dt.now().strftime("%Y_%m_%d_%H_%M_%S")
            local('cp %s %s.org.%s' %(vns_file, vns_file, timestamp))
            local("sed -i 's/\"vns_id\".*,/\"vns_id\":\"%s\",/'  %s" %(vns_id,vns_file))
            local("sed -i 's/\"vns_id\".*/\"vns_id\":\"%s\"/'  %s" %(vns_id,vns_file))

        if self.test_local:
            local('server-manager add  vns -f %s' %(vns_file))
        else:
            #svrmgr = get_svrmgr()
            svrmgr = self.svrmgr
            with settings(host_string=svrmgr, warn_only=True):
                file_name = os.path.basename(vns_file)
                temp_dir= tempfile.mkdtemp()
                run('mkdir -p %s' % temp_dir)
                put(vns_file, '%s/%s' % (temp_dir, file_name))

                run('server-manager add  vns -f %s/%s' %(temp_dir, file_name) )
                run('server-manager show all | python -m json.tool')


    # end add_vns()

    def add_server(self):
        self.add_server_using_json()
        self.update_server_in_db_with_testbed_py()

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


    def modify_vns_json(self):
        params=self.params
        if not params:
            return None
        if not params.has_key('vns_file'):
            return None
        vns_file = params['vns_file']

        timestamp = dt.now().strftime("%Y_%m_%d_%H_%M_%S")
        local('cp %s %s.org.%s' %(vns_file, vns_file, timestamp))

        in_file = open( vns_file, 'r' )
        in_data = in_file.read()
        vns_dict = json.loads(in_data)

        self.modify_vns_from_testbed_py(vns_dict)

        out_file = open(vns_file, 'w')
        out_data = json.dumps(vns_dict, indent=4)
        out_file.write(out_data)
        out_file.close()


    def modify_vns_from_testbed_py(self, vns_dict):
        testbed = self.testbed
        if testbed.env.has_key('mail_to'):
            vns_dict['vns'][0]['email'] = testbed.env.mail_to
        if testbed.env.has_key('encap_priority'):
            vns_dict['vns'][0]['vns_params']['encap_priority'] = testbed.env.encap_priority
        if 'multi_tenancy' in dir(testbed):
            vns_dict['vns'][0]['vns_params']['multi_tenancy'] = testbed.multi_tenancy
        if 'os_username' in dir(testbed):
            vns_dict['vns'][0]['vns_params']['ks_user'] = testbed.os_username
        if 'os_password' in dir(testbed):
            vns_dict['vns'][0]['vns_params']['ks_passwd'] = testbed.os_password
        if 'os_tenant_name' in dir(testbed):
            vns_dict['vns'][0]['vns_params']['ks_tenant'] = testbed.os_tenant_name
        if 'router_asn' in dir(testbed):
            vns_dict['vns'][0]['vns_params']['router_asn'] = testbed.router_asn


    def new_vns(self):
        params=self.params
        vns_id = params['vns_id']
        vns_dict = {
                      "vns" : [
                          {
                              "vns_id" : vns_id,
                              "vns_params" : {
                                  "router_asn": "64512",
                                  "database_dir": "/home/cassandra",
                                  "db_initial_token": "",
                                  "openstack_mgmt_ip": "",
                                  "use_certs": "False",
                                  "multi_tenancy": "False",
                                  "encap_priority": "'MPLSoUDP','MPLSoGRE','VXLAN'",
                                  "service_token": "contrail123",
                                  "ks_user": "admin",
                                  "ks_passwd": "contrail123",
                                  "ks_tenant": "admin",
                                  "openstack_passwd": "contrail123",
                                  "analytics_data_ttl": "168",
                                  "mask": "255.255.255.0",
                                  "gway": "1.1.1.254",
                                  "passwd": "c0ntrail123",
                                  "domain": "contrail.juniper.net",
                                  "haproxy": "disable"
                                  }
                              }
                          ]
                      }
        return vns_dict



    # End new_vns()


    def read_ini_file(self, config_ini):
        try:
            config = ConfigParser.SafeConfigParser()
            config.read([config_ini])
            smgr_config = dict(config.items("SERVER-MANAGER"))
            return smgr_config
        except:
            sys.exit("Error reading config file %s" %config_ini)

        return smgr_config

    # End read_ini_file


    def get_server_with_vns_id_from_db(self):
        vns_id = self.get_pref_vns_id()

        temp_dir= expanduser("~")
        file_name = '%s/server_with_vns_id_from_db.json' %(temp_dir)

        if self.test_local:
            local('server-manager show --detail server --vns_id %s \
                         | tr -d "\n" \
                         | sed "s/[^{]*//" \
                         > %s' %(vns_id, file_name))

        else:
            svrmgr = self.params
            with  settings(host_string=svrmgr, warn_only=True):
                temp_dir= tempfile.mkdtemp()
                run('mkdir -p %s' % temp_dir)
                file_name = '%s/server_list.json' %(temp_dir)

                run('server-manager show --detail server --vns_id %s \
                     | tr -d "\n" \
                     | sed \'s/[^{]*//\'  \
                     | python -m json.tool  \
                     > %s' %(vns_id, file_name) )

                local('mkdir -p %s' % temp_dir)
                get( file_name, file_name )

        in_file = open( file_name, 'r' )
        in_data = in_file.read()
        server_dict = json.loads(in_data)
        return server_dict

    def get_vns_with_vns_id_from_db(self):
        params=self.params
        vns_id = params['vns_id']

        vns_dict = {"vns": []}

        temp_dir= expanduser("~")

        file_name = '%s/vns.json' %(temp_dir)

        if self.test_local:
            local('server-manager show --detail vns --vns_id %s \
                         | tr -d "\n" \
                         | sed "s/[^{]*//" \
                         > %s' %(vns_id, file_name))
        else:
            svrmgr =  self.svrmgr
            with  settings(host_string=svrmgr, warn_only=True):
                temp_dir= tempfile.mkdtemp()
                run('mkdir -p %s' % temp_dir)
                file_name = '%s/vns.json' %(temp_dir)
                run('server-manager show --detail vns --vns_id %s \
                     | tr -d "\n" \
                     | sed \'s/[^{]*//\'  \
                     | python -m json.tool  \
                     > %s' %(vns_id, file_name) )
                local('mkdir -p %s' % temp_dir)
                get( file_name, file_name )

        in_file = open( file_name, 'r' )
        in_data = in_file.read()

        vns_dict = json.loads(in_data)
        return vns_dict


    def get_server_with_ip_from_db(self, ip=None):
        params=self.params

        server_dict={}
        if not ip:
            print "Please provide an ip as input arg"
            return ip

        temp_dir= expanduser("~")

        file_name = '%s/server.json' %(temp_dir)

        if self.test_local:
            local('server-manager show --detail server --ip %s \
                         | tr -d "\n" \
                         | sed "s/[^{]*//" \
                         > %s' %(ip, file_name))
        else:
            svrmgr = self.svrmgr
            with  settings(host_string=svrmgr, warn_only=True):
                temp_dir= tempfile.mkdtemp()
                run('mkdir -p %s' % temp_dir)
                file_name = '%s/server.json' %(temp_dir)
                run('server-manager show --detail server --ip %s \
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
        vns_id = self.get_pref_vns_id()
        node = self.get_host_roles_from_testbed_py()
        if not node:
            return
        u_server_dict = {}
        u_server_dict['server'] = []
        for key in node:
            server_dict = {}
            server_dict = self.get_server_with_ip_from_db(key)
            if not server_dict or not server_dict['server']:
                print ("ERROR: Server with ip %s not present in Server Manager" % key)
                continue
            server_id = server_dict['server'][0]['server_id']
            u_server = {}
            u_server['server_id'] = server_id
            u_server['vns_id'] = vns_id
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
                local('server-manager show --detail server --server_id %s' \
                          % u_server['server_id'] )
        else:
            svrmgr = self.svrmgr
            with  settings(host_string=svrmgr, warn_only=True):
                file_name = os.path.basename(server_file)
                temp_dir= tempfile.mkdtemp()
                run('mkdir -p %s' % temp_dir)
                put(server_file, '%s/%s' % (temp_dir, file_name))
                run('server-manager add  server -f %s/%s' %(temp_dir, file_name) )
                run('server-manager show --detail server --server_id %s   | python -m json.tool' %server_id)

    #End  update_server_in_db_with_vns_id


    def get_pref_vns_id(self):
        vns_id = None
        params=self.read_ini_file(self.smgr_config_ini)
        if  params.has_key('vns_id'):
            vns_id = params['vns_id']
        else:
            vns_id = self.get_vns_id()

        return vns_id

    def get_svrmgr(self):
        svrmgr = None
        params=self.params
        if  params.has_key('svrmgr'):
            svrmgr = params['svrmgr']
        return params['svrmgr']

    def get_server_file(self):
        params=self.params
        if not params:
            return None
        if not params.has_key('server_file'):
            return None
        server_file = params['server_file']
        return server_file

    def get_testbed(self):
        filepath = self.testbed_py
        if not filepath:
            sys.exit("tesbed.py missing in args  ")
        mod_name,file_ext = os.path.splitext(os.path.split(filepath)[-1])

        if file_ext.lower() == '.py':
            py_mod = imp.load_source(mod_name, filepath)

        return py_mod

    def verify_roles(self):
        pdb.set_trace()
        with  settings(host_string=env.roledefs['database'], warn_only=True):
            verify.verify_database()
        with  settings(host_string=env.roledefs['cfgm'], warn_only=True):
            verify.verify_cfgm()
        with  settings(host_string=env.roledefs['control'], warn_only=True):
            verify.verify_control()
        with  settings(host_string=env.roledefs['collector'], warn_only=True):
            verify.verify_collector()
        with  settings(host_string=env.roledefs['webui'], warn_only=True):
            verify.verify_webui()
        with  settings(host_string=env.roledefs['compute'], warn_only=True):
            verify.verify_compute()
        with  settings(host_string=env.roledefs['openstack'], warn_only=True):
            verify.verify_openstack()


# end SmgrFixture

def getIp(string) :
   regEx = re.compile( '\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}' )
   result = regEx.search(string)

   if result:
     return result.group()
   else:
     return None
