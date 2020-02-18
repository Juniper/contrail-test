import json
import time
import fixtures
from kubernetes.client.rest import ApiException
from vnc_api.vnc_api import NoIdError
from vnc_api import *
from vnc_api.vnc_api import Project
from vnc_api.vnc_api import VirtualNetwork
from vnc_api.vnc_api import HostBasedService
from common import log_orig as contrail_logging
from tcutils.util import get_random_name, retry
from vnc_api.gen.resource_xsd import QuotaType
from k8s.network_attachment import NetworkAttachmentFixture
from k8s.daemonset import DaemonSetFixture
import pprint

class HbsFixture(fixtures.Fixture):
    '''
     Fixture to imaplecwments HBF object creation and deletion and reading of the hbs objcts 
      -Tags the compute nodes
      -create a daemon set for csrx with a given version based on the compute node tagging 
      -configure the csrx for HBF
    '''

    def __init__(self,
                 connections,
                 name=None,
                 namespace='default',
                 csrx_version = '19.2R1.8',
                 csrx_path = 'hub.juniper.net/security/csrx',
                 node_label = None,
                 pod_label = None,
                 match_label = None,
                 fqname=None):
        self.logger = connections.logger or contrail_logging.getLogger(
            __name__)
        self.inputs = connections.inputs
        self.name = name or get_random_name('hbs')
        self.namespace = namespace
        self.k8s_client = connections.k8s_client
        self.annotations = None
        self.ds_name = None
        self.hbs_created = False
        self.node_label = node_label or {"type":"hbf"}
        self.match_label = match_label or {"type":"hbf"}
        self.pod_label = pod_label or {"type":"hbf"}
        self.csrx_version = csrx_version
        self.csrx_path = csrx_path
        self.already_exists = None
        self.leftnad  = None
        self.rightnad  = None
        self.connections = connections
        self.vnc_lib = connections.get_vnc_lib_h()
        self.agent_inspect = connections.agent_inspect
        self.username = "root"
        self.password = "c0ntrail123"
    # end __init__

    def setUp(self):
        super(HbsFixture, self).setUp()
        self.create()
        self.create_hbs_nads()
        self.create_hbs_ds()
        self.configure_hbs_on_pods()

    def verify_on_setup(self):
        if not self.verify_hbs_obj_in_contrail_api():
            self.logger.error('HBS %s not seen in Contrail API'
                              % (self.name))
            return False
        self.logger.info('HBS %s verification passed' % (self.name))
        return True
    # end verify_on_setup

    def cleanUp(self):
        self.delete()
        super(HbsFixture, self).cleanUp()

    def read(self):
        try:
            self.project = self.project_read(fq_name=[self.domain_name, 'k8s-'+self.namespace])
            self.hbs_created =  True
            return self.hbs_created 
        except ApiException as e:
            self.logger.debug('hbs object %s not present' % (self.name))
            self.hbs_created =  False
            return self.hbs_created
    # end read

    def create(self):
        try:
           self.project=self.vnc_lib.project_read(fq_name=['default-domain', 'k8s-'+self.namespace])
           self.project.set_quota(QuotaType(host_based_service=1))
           self.vnc_lib.project_update(self.project)
        except NoIdError:
           self.project = Project(name="k8s-"+self.namespace)
           self.puuid = self.vnc_lib.project_create(self.project)
           self.project = self.vnc_lib.project_read(fq_name=['default-domain', self.name])
        try:
           self.hbs = self.vnc_lib.host_based_service_read(fq_name=self.project.fq_name + [self.name])
           self.hbs_created =  False
        except NoIdError:
           self.hbs = HostBasedService(self.name, parent_obj=self.project)
           self.hbs_created = True
        if self.hbs_created:
           self.vnc_lib.host_based_service_create(self.hbs)
        else:
           self.vnc_lib.host_based_service_update(self.hbs)
        return self.hbs_created 
    # end create

    def delete(self):
        try:
           self.k8s_client.delete_daemonset(self.ds_name,namespace=self.namespace)
           self.k8s_client.delete_custom_resource_object(name=self.leftnad.name, namespace=self.namespace)
           self.k8s_client.delete_custom_resource_object(name=self.rightnad.name, namespace=self.namespace)
        except NoIdError:
           self.logger.info('Deletion of the Custom resources failed')
           return False
        time.sleep(10)
        if self.hbs_created :
            resp = self.vnc_lib.host_based_service_delete(fq_name=self.project.fq_name + [self.name])
            assert self.verify_on_cleanup()
    # end delete

    def verify_on_cleanup(self):
        assert self.verify_hbs_obj_not_in_contrail_api(), ('Hbs %s cleanup checks'
                                                       ' in contrail-api failed' % (self.name))
        return True
        self.logger.info('Verifications on hbs %s cleanup passed')
    # end verify_on_cleanup
    def verify_hbs_obj_in_contrail_api(self):
        try:
           self.project=self.vnc_lib.project_read(fq_name=['default-domain', 'k8s-'+self.namespace])
           self.logger.info('Project exists')
        except NoIdError:
           self.logger.info('Project doesnt exists')
           return False
        try:
           self.hbs = self.vnc_lib.host_based_service_read(fq_name=self.project.fq_name + [self.name])
           return True 
        except NoIdError: 
           self.logger.info('hbs object doesnt exist in config API')
           return False
        
    def verify_hbs_obj_not_in_contrail_api(self):
        try:
           self.hbs = self.vnc_lib.host_based_service_read(fq_name=self.project.fq_name + [self.name])
           self.logger.info('hbs object still exist in config API')
           return False
        except NoIdError:
           self.logger.info('hbs object doesnt exist in config API')
           return True
    # end verify_hbs_obj_not_in_contrail_api
    def create_hbs_nads(self):
        ''' Creates network attachment definitions 
            -left and
            -right
        '''
        spec = { "config":  '{ "cniVersion": "0.3.0", "type": "contrail-k8s-cni" }' }
        metadata =  {}
        metadata1 =  {}
        metadata["annotations"]={}
        metadata["name"] = "leftnet"
        self.annotate= {'domain':'default-domain',
                        'project':'k8s-%s'%self.namespace,
                        'name':'__%s-hbf-left__' %self.name} 
        self.annotate=json.dumps(self.annotate)
        metadata["annotations"]["opencontrail.org/network"] = self.annotate
        self.leftnad=self.useFixture(NetworkAttachmentFixture(
                              connections=self.connections,
                              namespace=self.namespace,
                              metadata=metadata,
                              spec=spec))
        self.annotate1= {'domain':'default-domain',
                        'project':'k8s-%s'%self.namespace,
                        'name':'__%s-hbf-right__' %self.name} 
        metadata1["annotations"]={}
        self.annotate1=json.dumps(self.annotate1)
        metadata1["name"]="rightnet"
        metadata1["annotations"]["opencontrail.org/network"] = self.annotate1
        self.rightnad= self.useFixture(NetworkAttachmentFixture(
                              connections=self.connections,
                              namespace=self.namespace,
                              metadata=metadata1,
                              spec=spec))
    def create_hbs_ds(self):
        '''
          Create hbs Daemon set 
        '''
        self.ds_name = get_random_name('hbs-ds')
        template_metadata = {}
        metadata = {}
        metadata['labels'] = {}
        metadata['name'] = self.ds_name
        spec = {}
        pod_label = self.pod_label
        metadata['labels'].update(pod_label)
        template_metadata['annotations'] = {}
        template_metadata["annotations"]["k8s.v1.cni.cncf.io/networks"] = {}
        #template_metadata["labels"]= {'type': 'hbf'}
        template_metadata["labels"]= self.pod_label 
        left_net = {"name": self.leftnad.metadata["name"]}
        right_net = {"name": self.rightnad.metadata["name"]}
        nets = [left_net, right_net]
        template_metadata["annotations"]["k8s.v1.cni.cncf.io/networks"] = nets
        template_metadata['annotations']['k8s.v1.cni.cncf.io/networks'] = \
                json.dumps(template_metadata['annotations']['k8s.v1.cni.cncf.io/networks'])
        pullsecret = 'secretcsrx'
        self.username = self.inputs.host_data[self.inputs.cfgm_ip]['username']
        self.password = self.inputs.host_data[self.inputs.cfgm_ip]['password']
        docker_username = 'JNPR-CSRXFieldUser12'
        docker_password = 'd2VbRJ8xPhSUAwzo7Lym'

        crsx_container_image = self.csrx_path+':'+self.csrx_version
        cmd = "kubectl create secret docker-registry %s " \
              "--docker-server=hub.juniper.net/security " \
              "--docker-username=%s --docker-password=%s" \
              " -n%s" %(pullsecret , docker_username ,docker_password, self.namespace)

        secretoutput = self.inputs.run_cmd_on_server(self.inputs.cfgm_ip, cmd, self.username, self.password,
                                                   as_sudo=True)
        getsecret = "kubectl get secret -n %s" %self.namespace
        secretkey = self.inputs.run_cmd_on_server(self.inputs.k8s_master_ip,\
                                                  getsecret, self.username, self.password, as_sudo=True)
        if pullsecret not in secretkey:
            self.logger.warn("Pull secret can't be created")
            return False

        template_spec =  {
            'containers': [
                {'image': self.csrx_path+':'+self.csrx_version,
                 'image_pull_policy': 'IfNotPresent',
                 'stdin': True,
                 'tty': False,
                 'env': [{
                        "name": "CSRX_FORWARD_MODE",
                        "value": "wire" }],
                 'name':'csrx',
                 'security_context': {"privileged": True} 
                 }
            ],
            "image_pull_secrets": [{ "name": pullsecret}],
            'restart_policy': 'Always',
            "node_selector":  self.node_label 
        }
        spec= {"selector" :self.match_label
              }
        spec.update({
            'template': {
                'metadata': template_metadata,
                'spec': template_spec
            }
        })

        ds=self.useFixture(DaemonSetFixture(
                              connections=self.connections,
                              namespace=self.namespace,
                              metadata=metadata,
                              spec=spec))
        assert ds.verify_on_setup()

    def  configure_hbs_on_pods(self):
        '''
          configuring the csrx pod for the hbf support
        '''
        podslist=[] 
        cmd = "kubectl get pods --selector type=hbf -n %s | awk '{print $1}'" %self.namespace 
        podslist=self.inputs.run_cmd_on_server(self.inputs.k8s_master_ip,\
                                                  cmd, self.username, self.password, as_sudo=True)  
        if len(podslist) != 0:
              podslist = podslist.split("\r\n")
              podslist.remove('NAME')
              cmd='edit'
              cmd+=';set interfaces ge-0/0/1.0'
              cmd+=';set interfaces ge-0/0/0.0' 
              cmd+=';set security policies default-policy permit-all'
              cmd+=';set security zones security-zone trust interfaces ge-0/0/0.0'
              cmd+=';set security zones security-zone untrust interfaces ge-0/0/1.0'
              cmd+=';commit'
              for pod in podslist:
                 kubectl_command = 'kubectl exec %s  --namespace=%s -i -t -- %s "%s"' % (pod, self.namespace, '/usr/sbin/cli -c', cmd)
                 resp = self.inputs.run_cmd_on_server(self.inputs.k8s_master_ip,kubectl_command)
