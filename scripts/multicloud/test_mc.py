from common.k8s.base import BaseK8sTest
from tcutils.wrappers import preposttest_wrapper
import test
from mc_def import *
from tcutils.util import *
import re

class MC_test(Multicloud):

    @classmethod
    def setUpClass(cls):
        super(MC_test, cls).setUpClass()
        cls.vpc_count=list()
        cls.cloud_instances=list()
        cls.onprem_control,cls.onprem_compute=dict(),dict()

        #Getting the onPrem computes and  storing them
        for k,v in cls.inputs.host_data.items():
            if 'onprem_control' in v['roles'].keys():
                if (re.match('\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', k) != None) or (re.search('englab.juniper.net',k)):
                    continue  
                else:
                    cls.onprem_control={k:v}
            if 'onprem_compute' in v['roles'].keys():
                if (re.match('\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', k) != None) or (re.search('englab.juniper.net',k)):
                    continue  
                else:
                    cls.onprem_compute={k:v}
        #import pdb; pdb.set_trace()
        cls.cloud_instances=cls.inputs.host_names[::]
        cls.cloud_instances.remove(cls.onprem_control.keys()[0])
        cls.cloud_instances.remove(cls.onprem_compute.keys()[0])
        for instance in cls.cloud_instances:
            #self.logger.info self.inputs.host_data[instance]['roles']
            cls.logger.info('Instance {0}: belongs to provider:{1} and vpc:{2}'.format(instance,cls.inputs.host_data[instance]['roles']['provider'],cls.inputs.host_data[instance]['roles']['vpc']))
        
        
        for key,value in cls.inputs.host_data.items():
            if key in cls.cloud_instances:
                cls.vpc_count.append(value['roles']['vpc'])
        
        #Creating labels to launch pods
        labels=run_cmd_on_server("kubectl get nodes -o wide | awk {'print $1'} | head -n -1 | tail -n +2", cls.onprem_control.values()[0]['host_ip'], 'root', 'c0ntrail123')
        for label in labels.split('\r\n'):
            cmd="kubectl label node {0} location={0}".format(label)
            run_cmd_on_server(cmd, cls.onprem_control.values()[0]['host_ip'], 'root', 'c0ntrail123')
        
        #Creatin

    @classmethod
    def tearDownClass(cls):
        super(MC_test, cls).tearDownClass()

    def parallel_cleanup(self):
        parallelCleanupCandidates = ["PodFixture"]
        self.delete_in_parallel(parallelCleanupCandidates)

    @test.attr(type=['openshift_1', 'ci_contrail_go_k8s_sanity'])
    @preposttest_wrapper
    def test_Overlay_ping(self):
        '''
        1)Create pods between the cloud instance and Onprem instances
        2)Ping from Onprem cloud instances to cloud instance and ensure if its successful
        '''
        
        for count in range(1,len(set(self.vpc_count))+1):
            self.logger.info('Overlay ping test for vpc: {0}'.format(count))
            self.overlay_ping(count,self.onprem_compute.keys()[0])

    @preposttest_wrapper
    def test_Underlay_ping(self):
        '''
        Underlay ping from Onprem to Cloud instances
        '''
        underlap_ip=run_cmd_on_server("kubectl get nodes -o wide | awk {'print $6'} | tail -n +2", self.onprem_control.values()[0]['host_ip'], 'root', 'c0ntrail123')
        for ip in underlap_ip.split('\r\n'):
            assert(self.underlay_ping(ip,self.onprem_control.values()[0]['host_ip']))
    
    @preposttest_wrapper
    def test_tag_verification(self):
        '''
        Build tag verification on the gateway if they hold the appropriate contrail version
        '''
        build_tag=self.inputs.config['contrail_configuration']['CONTRAIL_CONTAINER_TAG']
        for count in range(1,len(set(self.vpc_count))+1):
            self.logger.info('Tag verification for gateway in vpc: {0}'.format(count))
            self.tag_verification(count,self.cloud_instances,build_tag)

    @preposttest_wrapper
    def test_bird_HA(self):
        '''
        This test is to ensure HA bird service work properly

        1)Identify the master GW
        2)Send traffic to ensure traffic works fine before bird FLAP
        3)Check if the bird container is up, if so bring it down
        4)Once its down, check if VRRP has made the GW as standby
        5)Ensure Traffic works fine after that
        6)Bring up the GW and ensure the mastership is regained 
        '''
        for count in range(1,len(set(self.vpc_count))+1):
            self.logger.info('Bird HA test for vpc: {0}'.format(count))
            self.HA_flap(count,self.cloud_instances,'bird_bird_1')

    @preposttest_wrapper
    def test_openvpn_HA(self):
        '''
        This test is to ensure HA openvpn service work properly

        1)Identify the master GW
        2)Send traffic to ensure traffic works fine before openvpn FLAP
        3)Check if the openvpn container is up, if so bring it down
        4)Once its down, check if VRRP has made the GW as standby
        5)Ensure Traffic works fine after that
        6)Bring up the GW and ensure the mastership is regained 
        '''
        for count in range(1,len(set(self.vpc_count))+1):
            self.logger.info('Openvpn HA test for vpc: {0}'.format(count))
            self.HA_flap(count,self.cloud_instances,'openvpn_server_1')
        

    @preposttest_wrapper
    def test_strongswan_HA(self):
        '''
        This test is to ensure HA strongswan service work properly
        
        1)Identify the master GW
        2)Send traffic to ensure traffic works fine before strongswan FLAP
        3)Check if the bird container is up, if so bring it down
        4)Once its down, check if VRRP has made the GW as standby
        5)Ensure Traffic works fine after that
        6)Bring up the GW and ensure the mastership is regained 
        '''
        for count in range(1,len(set(self.vpc_count))+1):
            self.logger.info('Strongswam HA test for vpc: {0}'.format(count))
            self.HA_flap(count,self.cloud_instances,'strongswan_strongswan_1')
    



