import fixtures
from novaclient import client as mynovaclient
from novaclient import exceptions as novaException
from fabric.context_managers import settings, hide
from fabric.api import run, local
from fabric.operations import get,put
from fabric.contrib.files import exists
from util import *
import socket
import time
import re

#from contrail_fixtures import contrail_fix_ext

#@contrail_fix_ext (ignore_verify=True, ignore_verify_on_setup=True)
class NovaFixture(fixtures.Fixture):
    def __init__(self, inputs, project_name, key='key1'):
        httpclient=None
        self.inputs= inputs
        self.username= inputs.stack_user
        self.password= inputs.stack_password
        self.project_name= project_name
        self.cfgm_ip = inputs.cfgm_ip
        self.openstack_ip = inputs.openstack_ip
        self.cfgm_host_user= inputs.username
        self.cfgm_host_passwd = inputs.password
        self.key=key
        self.obj=None
        self.auth_url='http://'+ self.openstack_ip+':5000/v2.0'
        self.logger= inputs.logger
    #end __init__

    def setUp(self):
        super(NovaFixture, self).setUp()
        self.obj=mynovaclient.Client('2', username= self.username, project_id= self.project_name,
                             api_key= self.password, auth_url=self.auth_url)
        self._create_keypair(self.key)
        self.compute_nodes= self.get_compute_host()
    #end setUp

    def cleanUp(self):
        super(NovaFixture, self).cleanUp()

    def get_handle(self):
        return self.obj
    #end get_handle
    
    def get_image(self, image_name):
        default_image = 'ubuntu-traffic'
        try:
            image=self.obj.images.find(name=image_name)
        except novaException.NotFound:
            # In the field, not all kinds of images would be available
            # Just use a default image in such a case
            if not self._install_image(image_name=image_name):
                self._install_image(image_name=default_image)
            image=self.obj.images.find(name=image_name)
        return image
    #end get_image
    
    def get_vm_if_present(self, vm_name, project_id=None):
        try:
            vm_list=self.obj.servers.list(search_opts={"all_tenants": True})
            for vm in vm_list:
                if project_id:
                    if vm.name == vm_name and vm.tenant_id == self.strip(project_id):
                        return vm
                else:
                    if vm.name == vm_name: 
                        return vm
        except novaException.NotFound :
            return None
        except Exception:
            self.logger.exception('Exception while finding a VM')
            return None
        return None
    #end get_vm_if_present
    
    def get_vm_by_id(self, vm_id, project):
        try:
            vm=None
            vm=self.obj.servers.find(id= vm_id)
            if vm : return vm
        except novaException.NotFound :
            return None
        except Exception:
            self.logger.exception('Exception while finding a VM')
            return None
    #end get_vm_by_id
   
    def _install_image(self, image_name):
        result = False
#        with hide('everything'):
        with settings(host_string= '%s@%s' %(self.cfgm_host_user, self.openstack_ip),
                    password= self.cfgm_host_passwd, warn_only=True,abort_on_prompts=False):
            #Work arround to choose build server.
            if '10.204' in self.openstack_ip:
                build_srv_ip = '10.204.216.51'
            else:
                build_srv_ip = '10.84.5.100'

            if image_name == 'cirros-0.3.0-x86_64-uec':
                run('source /etc/contrail/openstackrc')
                run('cd /tmp ; sudo rm -f /tmp/cirros-0.3.0-x86_64* ; \
            wget http://launchpad.net/cirros/trunk/0.3.0/+download/cirros-0.3.0-x86_64-uec.tar.gz')
                run('tar xvzf /tmp/cirros-0.3.0-x86_64-uec.tar.gz -C /tmp/')
                run('source /etc/contrail/openstackrc && glance add name=cirros-0.3.0-x86_64-kernel is_public=true '+
                    'container_format=aki disk_format=aki < /tmp/cirros-0.3.0-x86_64-vmlinuz')
                run('source /etc/contrail/openstackrc && glance add name=cirros-0.3.0-x86_64-ramdisk is_public=true '+
                    ' container_format=ari disk_format=ari < /tmp/cirros-0.3.0-x86_64-initrd')
                run('source /etc/contrail/openstackrc && glance add name=' + image_name + ' is_public=true '+
                    'container_format=ami disk_format=ami '+
                    '\"kernel_id=$(glance index | awk \'/cirros-0.3.0-x86_64-kernel/ {print $1}\')\" '+
                    '\"ramdisk_id=$(glance index | awk \'/cirros-0.3.0-x86_64-ramdisk/ {print $1}\')\" ' +
                    ' < <(zcat --force /tmp/cirros-0.3.0-x86_64-blank.img)')

            elif image_name == 'redmine-fe':
                image = "turnkey-redmine-12.0-squeeze-x86.vmdk.gz"
                result = self.copy_and_glance(build_srv_ip, image, image_name)
            elif image_name == 'redmine-be':
                image = "turnkey-redmine-12.0-squeeze-x86-mysql.vmdk.gz"
                result = self.copy_and_glance(build_srv_ip, image, image_name)
            elif image_name == 'ubuntu':
                image = "precise-server-cloudimg-amd64-disk1.img.gz"
                result = self.copy_and_glance(build_srv_ip, image, image_name)
            elif image_name == 'zeroshell':
                image = "ZeroShell-qemu-bridge.img.gz"
                result = self.copy_and_glance(build_srv_ip, image, image_name)
            elif image_name == 'vsrx-bridge':
                image = "vsrx/junos-vsrx-12.1-transparent.img.gz"
                result = self.copy_and_glance(build_srv_ip, image, image_name)
            elif image_name == 'vsrx':
                result = image = "vsrx/junos-vsrx-12.1-in-network.img.gz"
                result = self.copy_and_glance(build_srv_ip, image, image_name)
            elif image_name == 'ubuntu-traffic':
                image = "traffic/ubuntu-traffic.img.gz"
                result = local_name = image_name
                result = self.copy_and_glance(build_srv_ip, image, image_name)
            elif image_name == 'ubuntu-arping':
                image = "arping/ubuntu-arping.img.gz"
                result = self.copy_and_glance(build_srv_ip, image, image_name)
            elif image_name == 'ubuntu-tftp':
                image = "tftp/ubuntu-tftp.img.gz"
                result = self.copy_and_glance(build_srv_ip, image, image_name)
            elif image_name == 'redmine-web-traffic':
                image = "traffic/redmine-web-traffic.vmdk.gz"
                local_name = image_name
                result = self.copy_and_glance(build_srv_ip, image, image_name)
            elif image_name == 'redmine-db-traffic':
                image = "traffic/redmine-db-traffic.vmdk.gz"
                result = self.copy_and_glance(build_srv_ip, image, image_name)
            elif image_name == 'analyzer':
                image = "analyzer/analyzer-vm-console.qcow2.gz"
                result = self.copy_and_glance(build_srv_ip, image, image_name)
            elif image_name == 'ubuntu-netperf':
                image = "ubuntu-netperf.img.gz"
                result = self.copy_and_glance(build_srv_ip, image, image_name)
            #end if 
        return result 
    #end _install_image     
    
    def copy_and_glance(self, build_srv_ip, image_gzip_name, local_name):
        """copies the image to the host and glances.
        Requires image__gzip_name with path relative to /cs-shared/images.
        if outside of juniper intranet , Requires image_name to be 
        present in the test repo base directory
        """
        if self.inputs.is_juniper_intranet:
            run('rm -f %s' %(image_gzip_name))
            run("wget http://%s/images/%s" % (build_srv_ip, image_gzip_name))
        image_zip = image_gzip_name.split('/')[-1]
        if exists('%s' %(image_zip)):
            run("gunzip -f %s" % image_zip)
        image_name = image_zip.replace(".gz", "")
        if not exists('%s' %(image_name)):
            self.logger.error('Unable to find the image %s' %(image_name))
            return False
        run("(source /etc/contrail/openstackrc; glance add name='%s'\
              is_public=true container_format=ovf disk_format=qcow2 < %s)" % 
             (local_name, image_name))
        return True

    def _create_keypair(self, key_name):
        if key_name in [str(key.id) for  key in self.obj.keypairs.list()]:
            return
        with hide('everything'):
            with settings(host_string= '%s@%s' %(self.cfgm_host_user, self.cfgm_ip),
                        password= self.cfgm_host_passwd, warn_only=True,abort_on_prompts=False):
                rsa_pub_file=os.environ.get('HOME')+ '/.ssh/id_rsa.pub'
                rsa_pub_arg=os.environ.get('HOME')+ '/.ssh/id_rsa'
                if exists('.ssh/id_rsa.pub'):  #If file exists on remote m/c
                    get('.ssh/id_rsa.pub','/tmp/')
                else:
                    run('rm -f .ssh/id_rsa.pub')
                    run('ssh-keygen -f %s -t rsa -N \'\''  %(rsa_pub_arg))            
                    get('.ssh/id_rsa.pub','/tmp/')
                pub_key=open('/tmp/id_rsa.pub','r').read()
                self.obj.keypairs.create(key_name, public_key=pub_key)
                local('rm /tmp/id_rsa.pub')
    #end _create_keypair
    
    def create_vm(self, project_uuid, image_name, ram, vm_name, vn_ids, node_name=None, sg_ids=None, count=1,userdata = None):
        image=self.get_image(image_name=image_name)
        flavor=self.obj.flavors.find(ram=ram)
        if node_name == 'disable':
            zone = None
        elif node_name:
            zone= "nova:" + node_name
        else:
            zone= "nova:" + next(self.compute_nodes)
        if userdata:
            with open(userdata) as f:
                userdata = f.readlines()
            userdata = ''.join(userdata)
#        userdata = "#!/bin/sh\necho 'Hello World.  The time is now $(date -R)!' | tee /tmp/output.txt\n"
        nics_list= [ {'net-id': x } for x in vn_ids ]
        self.obj.servers.create(name=vm_name, image=image, 
                                security_groups=sg_ids,
                                flavor=flavor, nics=nics_list, 
                                key_name=self.key , availability_zone=zone, 
                                min_count = count,max_count=count,userdata = userdata)
        vm_objs = self.get_vm_list(name_pattern=vm_name, 
                                   project_id=project_uuid)
        [vm_obj.get() for vm_obj in vm_objs] 
        self.logger.info( "VM Object is %s" %(str(vm_objs)) )
        return vm_objs
    #end create_vm 
    
    def add_security_group(self, vm_id, secgrp):
        self.obj.servers.add_security_group(vm_id, secgrp)

    def remove_security_group(self, vm_id, secgrp):
        self.obj.servers.remove_security_group(vm_id, secgrp)

    @retry(delay=5, tries=35)
    def get_vm_detail(self, vm_obj):
        try:
            vm_obj.get()
            if vm_obj.addresses == {} or vm_obj.status == 'BUILD':
                return False
            else:
                return True
        except novaException.ClientException:
            print 'Fatal Nova Exception'
            self.logger.exception('Exception while getting vm detail')
            return False
    #end def 
    
    @retry(tries=10, delay=6)
    def is_ip_in_obj(self, vm_obj, vn_name):
        try:
            vm_obj.get()
            if  len(vm_obj.addresses[vn_name]) > 0 :
                return True
            else :
                self.logger.warn('Retrying to see if VM IP shows up in Nova ')
                return False
        except KeyError:
            self.logger.warn('Retrying to see if VM IP shows up in Nova ')
            return False
    #end is_ip_in_obj
    
    def get_vm_ip(self, vm_obj, vn_name):
        ''' Returns a list of IPs for the VM in VN.
        
        '''
#        return vm.obj[vn_name][0]['addr']
        if self.is_ip_in_obj(vm_obj, vn_name):
            try :
                    return [x['addr'] for x in vm_obj.addresses[vn_name]]
            except KeyError:
                    self.logger.error('VM does not seem to have got an IP in VN %s' %(vn_name) )
                    return []
        else :
            return []
    #end get_vm_ip
    
    def strip(self,uuid):
        return uuid.replace('-','')
    
    def get_vm_list(self, name_pattern='',project_id=None):
        ''' Returns a list of VM objects currently present.
        
        '''
        final_vm_list = []
        vm_list = self.obj.servers.list(search_opts={"all_tenants": True})
        for vm_obj in vm_list:
            match_obj = re.match( r'%s' % name_pattern, vm_obj.name, re.M|re.I)
            if project_id:
                if match_obj and vm_obj.tenant_id == self.strip(project_id):
                    final_vm_list.append(vm_obj)
            else:
                if match_obj :
                    final_vm_list.append(vm_obj)
        #end for
        return final_vm_list
            
    #end get_vm_list
    
    
    def get_nova_host_of_vm(self, vm_obj):
        return vm_obj.__dict__['OS-EXT-SRV-ATTR:host']
    #end  
     
    def delete_vm(self, vm_obj):
        vm_obj.delete()
    #end _delete_vm
    
    def put_key_file_to_host(self, host_ip):
        with hide('everything'):
            with settings(host_string='%s@%s' %(self.inputs.host_data[host_ip]['username'],
                          host_ip), password= self.inputs.host_data[host_ip]['password'],
                          warn_only=True, abort_on_prompts=False ):
                put('~/.ssh/id_rsa','/tmp/id_rsa')
                run('chmod 600 /tmp/id_rsa')
                self.tmp_key_file='/tmp/id_rsa'
    
    def get_compute_host(self):
        while(1):
            for i in self.inputs.compute_ips:
#                yield socket.gethostbyaddr(i)[0]
                yield self.inputs.host_data[i]['name']
    #end get_compute_host
    
    @retry(tries=20, delay=5)
    def wait_till_vm_is_up(self, vm_obj):
        try:
            vm_obj.get()
            if 'login:' in vm_obj.get_console_output():
                self.logger.info( 'VM has booted up..' )
                return True
            else:
                self.logger.debug( 'VM not yet booted fully .. ' )
                return False
        except novaException.NotFound:
            self.logger.debug( 'VM console log not formed yet')
            return False
        except novaException.ClientException:
            self.logger.error(  'Fatal Nova Exception while getting VM detail')
            return False
    #end wait_till_vm_is_up
    
    def get_vm_in_nova_db(self, vm_obj, node_ip):
        issue_cmd='mysql -u root --password=%s -e \'use nova; select vm_state, uuid, task_state from instances where uuid=\"%s\" ; \' ' %(self.inputs.mysql_token, vm_obj.id) 
        username= self.inputs.host_data[node_ip]['username']
        password= self.inputs.host_data[node_ip]['password']
        output=self.inputs.run_cmd_on_server( server_ip= node_ip, issue_cmd= issue_cmd, username= username, password= password ) 
        return output 
    #end get_vm_in_nova_db
    
    @retry(tries=10, delay=5)
    def is_vm_deleted_in_nova_db(self, vm_obj, node_ip):
        output= self.get_vm_in_nova_db( vm_obj, node_ip )
        if 'deleted' in output and 'NULL' in output : 
            self.logger.info('VM %s is removed in Nova DB' %(vm_obj.name) )
            return True
        else:
            self.logger.warn('VM %s is still found in Nova DB : %s' %(vm_obj.name, output))
            return False
    #end is_vm_in_nova_db
    
#end NovaFixture
