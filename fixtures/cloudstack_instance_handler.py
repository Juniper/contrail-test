from cloudclient import CloudClient
from cloudauth import *
from instance_handler import InstanceHandler
import os
from time import sleep
from util import retry
import subprocess
import tempfile

TEMPLATE_SCRIPT_PATH='/root/ctrlplane/tools/provisioning/cloudstack'

class CloudstackInstanceHandler(InstanceHandler):
    def __init__(self, username, password, connections, cfgm_ip):
        super( CloudstackInstanceHandler, self).__init__( username, password, connections, cfgm_ip )
        self.client= CloudClient( cfgm_ip, username, password )
        self.cfgm_ip= cfgm_ip
        self.username= username
        self.password= password
        self.connections= connections
        self.inputs= connections.inputs
        self.compute_nodes= self.get_compute_host()
        self.vnc_lib_h = self.connections.vnc_lib
        # Time for VMs to get removed
        self.set_expunge_time('30')
        self.set_keys()

    # image_name is template name
    # flavor is serviceoffering
    def create_vm(self, image_name, flavor , vm_name, vn_ids, node_name=None, project_id=None, affinity_group_ids=None):
        #TODO
        #Let current template be CentOS only
        image_name= 'CentOS'
        template_id=self.get_image_id(image_name=image_name)
        if template_id is None:
            self.logger.error(' Unable to find out the template id for image %s' %(image_name) )
            return False
        vnid_str= ','.join(vn_ids)
        flavors={'small':'Small Instance', 'medium': 'Medium Instance'}
        zone_id= self.get_zone()
        serviceoffering_id= self.get_serviceoffering_id( flavors[flavor] )
        try:
            args={'name': vm_name, 'templateid':template_id,
                 'serviceofferingid': serviceoffering_id,
                 'networkids':vnid_str, 'zoneid': zone_id }
            project_fq_name = self.vnc_lib_h.id_to_fq_name(project_id)
            if not 'default-project' in project_fq_name :
                args['projectid'] = project_id
            if node_name:
                args['hostid'] = self.get_node_id_from_name(node_name)
            #else:
            #    node_id= self.get_node_id_from_name( next(self.compute_nodes) )
            if affinity_group_ids:
                args['affinitygroupids'] = affinity_group_ids
            response = self.client.request('deployVirtualMachine', args)
        except CloudClient.Error,e:
            self.logger.exception("Exception while creating VM %s" %(vm_name) )
            return None

        if response['queryasyncjobresultresponse']['jobprocstatus'] != 0 :
            self.logger.error('VM %s creation failed. Response : %s' %(vm_name, response) )
            return None
        vm_obj= response['queryasyncjobresultresponse']['jobresult']['virtualmachine']

        # Stop vncterm if its running so that console access issues are not hit
        host_ip_of_vm= self.inputs.host_data[ self.get_host_of_vm( vm_obj ) ]['host_ip']
        domain_id= self.get_domain_id_of_vm( host_ip_of_vm, vm_obj )
        self.stop_vncterm(  host_ip_of_vm, domain_id )
        return vm_obj
    #end create_vm

    def delete_vm_by_id(self, vm_id ) :
        #Until the HTTP432 error is resolved
        cmd= [ 'cloudmonkey', 'destroyVirtualMachine' , 'id='+ vm_id ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (output, err) = proc.communicate()
        self.logger.debug('Response to destory VM ' + output + err )
        if None:
            try:
                response= self.client.request('destoryVirtualMachine',{'id': vm_id } )
                response= response['queryasyncjobresultresponse']
            except CloudClient.Error,e:
                self.logger.exception("Exception while deleting VM %s" %( vm_id ) )
                return None
            if response['jobprocstatus'] != 0 :
                self.logger.error('VM %s deletion failed. Response : %s' %(vm_name, response) )
                return None
            state=response['jobresult']['virtual-machine']['state']
            if state !='Destroyed':
                self.logger.error('VM state( %s ) is not Destroyed upon deletion ' %( state) )
                return None
        #end if None
        if not self.wait_for_vm_removal( vm_id ):
            self.logger.error('Timed out waiting for VM %s to be expunged' %( vm_id ))
            return None
        #return response['jobresult']['virtual-machine']
        return True
    #end delete_vm_by_id

    def delete_vm(self, vm_obj):
        return self.delete_vm_by_id(vm_obj['id'])
    #end delete_vm

    def getApiKey(self, hostname, username, password):
        keys={}
        tmp_cookie = tempfile.mkstemp(suffix=".cookie")
        tmp_name = tmp_cookie[1]
        loginresp = cloudLogin(hostname, username, password, tmp_name)
        urlParam = '&response=json&id=' + loginresp['userid'] + '&sessionkey=' + encodeURIComponent(loginresp['sessionkey'])
        cmd = ['curl',
               '-v',
               '-H', 'Content-Type: application/json',
               '-b', tmp_name,
              '-X', 'POST',
               'http://' + hostname + ':8080/client/api/?command=registerUserKeys' + urlParam]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (output, err) = proc.communicate()
        response = json.loads(output)
        logging.debug(response)
        os.remove(tmp_name)
        keys = response['registeruserkeysresponse']
        if not 'userkeys' in keys:
            return None
        return keys['userkeys']['apikey'], keys['userkeys']['secretkey']
    #end getApiKey

    def set_keys(self):
        if not self.isApiKeySet():
            print 'Retrieve apikey....'
            keys = self.getApiKey( self.cfgm_ip, self.username, self.password)
            self.setKeys(keys)

    def isApiKeySet( self ):
        import ConfigParser
        config_file = os.path.expanduser('~/.cloudmonkey/config')
        if not os.path.exists(config_file):
            return False
        cfg = open(config_file, 'r')
        config = ConfigParser.ConfigParser()
        config.readfp(cfg)
        return config.get('user', 'apikey')

    def setKeys(self, keys):
        proc = subprocess.Popen(['cloudmonkey'], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        commands = [
            'set apikey ' + keys[0],
            'set secretkey ' + keys[1],
            'quit'
            ]
        (output, err) = proc.communicate('\n'.join(commands))
    #end setKeys

    @retry(delay=10, tries=12)
    def wait_for_vm_removal( self, vm_id ):
        try:
            result= self.client.request('listVirtualMachines',{'id': vm_id })
            if result['listvirtualmachinesresponse']:
                self.logger.warn('VM %s is still seen in Cloudstack VM list' %( vm_id ) )
                return False
            else:
                self.logger.debug('VM %s is not seen in Cloudstack VM list' %( vm_id ) )
                return True
        except CloudClient.Error,e:
            self.logger.exception("Exception while querying for VM %s" %(vm_id) )
            return None
    #end wait_for_vm_removal

    def get_node_id_from_name( self, name):
        response= self.client.request('listHosts', {'name':name} )
        return response['listhostsresponse']['host'][0]['id']

    def get_serviceoffering_id(self, name):
        obj= self.client.request('listServiceOfferings',{'name': name} )
        print obj
        return obj['listserviceofferingsresponse']['serviceoffering'][0]['id']

    def get_vm_if_present(self, vm_name , project_id=None):
        args={}
        if project_id and ( 'default-project' not in self.vnc_lib_h.id_to_fq_name(project_id)) :
            args['projectid']=project_id
        result= self.client.request('listVirtualMachines',args)
        if result['listvirtualmachinesresponse']:
            vms= result['listvirtualmachinesresponse']['virtualmachine']
            for  vm in vms:
                if vm['name'] == vm_name and vm['state'] != 'Destroyed':
                    return vm
        return None

    def get_vm_detail(self, vm_obj):
        result= self.client.request('listVirtualMachines', {'id': vm_obj['id']} )
        return result['listvirtualmachinesresponse']['virtualmachine'][0]

    def get_vm_id(self, vm_obj):
        return vm_obj['id']

    def get_vm_instancename(self, vm_obj):
        return vm_obj['instancename']

    def get_host_of_vm(self, vm_obj):
        return vm_obj['hostname']

    def get_vm_ip(self, vm_obj, vn_name):
        for nic in vm_obj['nic']:
            if nic['networkname'] == vn_name:
                return nic['ipaddress']
        return None
    #end get_vm_ip

    def put_key_file_to_host(self, vm_node_ip ):
        self.logger.warn( ' Putting keyfiel to host is not possible here' )
        return None

    def get_vm_state(self, vm_obj):
        return vm_obj['state']

    def get_vm_status(self, vm_obj):
        if vm_obj['state'] == 'Running':
            return 'ACTIVE'

    def reset_state( self, vm_obj, state ):
        print "Not implemented"
        pass

    def get_vm_template_name( self, vm_obj):
        return vm_obj['templatename']

    def get_image_id(self, image_name):
        image_id= None
        image_id=self.find_image(name=image_name)
        if image_id is None:
            self.install_image(image_name=image_name)
            image_id=self.find_image(name=image_name)
        return image_id
    #end get_image

    def find_image(self, name):
        image= self.client.request('listTemplates', {'name': name , 'templatefilter':'executable' } )
        if image['listtemplatesresponse']:
            for template in image['listtemplatesresponse']['template'] :
                if template['name'] == name:
                    return template['id']
        return None
    #end find_image

    def install_image( self, image_name ):
        if image_name == "CentOS":
            cmd= 'sh -x ' + TEMPLATE_SCRIPT_PATH +'/vm-template-install.sh -t http://10.204.216.51/cloudstack/vm_templates/centos56-x86_64-xen.vhd.bz2 -n %s -u cloud -p cloud -d cloud -s 10.204.216.49:/cs-attic -i %s' %(image_name, self.inputs.cfgm_ip)
            cmd= cmd.split(' ')
            proc = subprocess.Popen( cmd,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            (output, err) = proc.communicate()
            self.logger.debug('Installing template...: ' + output )
    #end install_image

    def get_zone(self, name='default'):
        resp= self.client.request('listZones', {'name': name} )
        id= resp['listzonesresponse']['zone'][0]['id']
        return id
    #end get_zone

    def get_fq_name (self, obj):
        return ':'.join(['default-domain','default-project', obj['name']] )

    def get_default_gateway(self, vm_obj, vn_fq_name):
        for nic in vm_obj['nic']:
            vn_name= vn_fq_name.split(':')[-1]
            if nic['networkname'] == vn_name:
                return nic['gateway']
        self.logger.warn('No default gateway entry found for VM %s in VN %s' %( vm_obj['name'], vn_name) )
        return None
    #get_default_gateway

    def stop_vncterm(self, server_ip, domain_id):
        cmd= 'ps aux | grep vncterm | grep "/%s/"|awk \'{print $2}\' |xargs kill >/dev/null 2>/dev/null' %( domain_id)
        self.inputs.run_cmd_on_server( server_ip, cmd, username=self.inputs.host_data[ server_ip ]['username'], password=self.inputs.host_data[ server_ip ]['password'] )

    def set_expunge_time(self, time):
        result= self.client.request('listConfigurations', {'name': 'expunge.interval' } )
        print result;
        if result['listconfigurationsresponse']['configuration'][0]['value'] != time :
            result= self.client.request('updateConfiguration', {'name': 'expunge.interval', 'value': time } )
            result1= self.client.request('updateConfiguration', {'name': 'expunge.delay', 'value': time } )
            self.inputs.run_cmd_on_server( self.inputs.cfgm_ip, "/etc/init.d/cloudstack-management restart",
                                           username=self.inputs.host_data[ self.inputs.cfgm_ip ]['username'],
                                           password=self.inputs.host_data[ self.inputs.cfgm_ip ]['password'])
            sleep(60)
    #end set_expunge_time

    def stop_vm(self, vm_obj):
        try:
            result = self.client.request('stopVirtualMachine',{ 'id': vm_obj['id'] } )
            self.logger.debug('Result of stopping VM %s: %s' %( vm_obj['id'], result ))
            sleep(5)
        except CloudClient.Error,e:
            self.logger.exception("Exception while stopping  VM %s" %(vm_obj['id']) )
            return None
    #end stop_vm

    def start_vm(self, vm_obj):
        try:
            response = self.client.request('startVirtualMachine', { 'id': vm_obj['id'] } )
            self.logger.debug('Result of starting VM %s: %s' %( vm_obj['id'], response ))

            if response['queryasyncjobresultresponse']['jobprocstatus'] != 0 :
                self.logger.error('Starting VM %s failed. Response : %s' %(vm_name, response) )
                return None
            vm_obj= response['queryasyncjobresultresponse']['jobresult']['virtualmachine']

            # Stop vncterm if its running so that console access issues are not hit
            host_ip_of_vm= self.inputs.host_data[ self.get_host_of_vm( vm_obj ) ]['host_ip']
            domain_id= self.get_domain_id_of_vm( host_ip_of_vm, vm_obj )
            self.stop_vncterm(  host_ip_of_vm, domain_id )
            return vm_obj
        except CloudClient.Error,e:
            self.logger.exception("Exception while starting  VM %s" %(vm_obj['id']) )
            return None
    #end start_vm

    def migrate_vm(self, vm_obj, node_name):
        try:
            node_id = self.get_node_id_from_name(node_name)
            response = self.client.request('migrateVirtualMachine', {'hostid': node_id, 'virtualmachineid': vm_obj['id']})
            self.logger.debug('Result of migrating VM %s: %s' %( vm_obj['id'], response ))

            if response['queryasyncjobresultresponse']['jobprocstatus'] != 0 :
                self.logger.error('Migrating VM %s failed. Response : %s' %(vm_name, response) )
                return None
            vm_obj= response['queryasyncjobresultresponse']['jobresult']['virtualmachine']

            # Stop vncterm if its running so that console access issues are not hit
            host_ip_of_vm= self.inputs.host_data[ self.get_host_of_vm( vm_obj ) ]['host_ip']
            domain_id= self.get_domain_id_of_vm( host_ip_of_vm, vm_obj )
            self.stop_vncterm(  host_ip_of_vm, domain_id )
            return vm_obj
        except CloudClient.Error,e:
            self.logger.exception("Exception while migrating VM %s" %(vm_obj['id']) )
            return None
    #end start_vm


if __name__ == "__main__":
    from connections import ContrailConnections
    from contrail_test_init import *
    if 'PARAMS_FILE' in os.environ :
        ini_file= os.environ.get('PARAMS_FILE')
    else:
        ini_file= 'params.ini'
    x= ContrailTestInit( ini_file)
    x.setUp()
    connections= ContrailConnections(x)
    cs_obj= CloudstackInstanceHandler( 'admin', 'password',connections, x.cfgm_ip)
    cs_obj.create_vm('CentOS', 'small', 'vm33', '7ed0f83f-b745-4df2-a8e4-64cd4f3adf33' )
#    cs_obj.create_vm('vn1',['10.1.1.0/24'], None)
    import pdb; pdb.set_trace()


